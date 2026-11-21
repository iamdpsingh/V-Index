"""Restore drill using disposable local PostgreSQL databases and synthetic data only."""

import argparse
import json
import os
import time
import uuid
from datetime import timedelta
from pathlib import Path

import psycopg
from alembic import command
from alembic.config import Config
from cryptography.exceptions import InvalidTag
from cryptography.fernet import Fernet
from psycopg import sql
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from vindex.accounts.models import Account, AccountSession, Profile, Resume
from vindex.db import Source, now
from vindex.ingest import ingest
from vindex.schemas import Enumeration, JobInput

from scripts.backup_database import backup, connect, database_env, restore


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin", type=Path, default=Path("/usr/bin"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = make_url(os.environ["TEST_DATABASE_URL"])
    if root.host not in {"localhost", "127.0.0.1", "::1"}:
        parser.error("Run the drill against a dedicated local PostgreSQL instance")
    os.environ["RESUME_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    os.environ["BACKUP_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    source_name, target_name = ["rolewisp_drill_" + uuid.uuid4().hex for _ in range(2)]
    os.environ["DATABASE_URL"] = root.set(database=source_name).render_as_string(
        hide_password=False
    )
    os.environ["RESTORE_DATABASE_URL"] = root.set(database=target_name).render_as_string(
        hide_password=False
    )
    admin_env = database_env("TEST_DATABASE_URL")
    created = []
    started = time.monotonic()
    cipher = Fernet(os.environ["RESUME_ENCRYPTION_KEY"].encode())
    private = b"SYNTHETIC_RESTORE_CANARY_NOT_A_PERSONAL_RESUME"
    engines = []
    try:
        with connect(admin_env) as admin:
            admin.autocommit = True
            for name in (source_name, target_name):
                admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
                created.append(name)
        source_engine = create_engine(os.environ["DATABASE_URL"])
        engines.append(source_engine)
        with source_engine.begin() as connection:
            config = Config("alembic.ini")
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        with Session(source_engine) as session:
            account = Account(email="restore-drill@example.org", password_hash="synthetic-unusable")
            session.add(account)
            source = Source(
                provider="ashby",
                slug="restore-example",
                company="Reviewer Example",
                url="https://jobs.ashbyhq.com/restore-example",
            )
            session.add(source)
            session.flush()
            account_id = account.id
            account.email_code_hash = "synthetic-expired-by-recovery"
            account.password_reset_hash = "synthetic-expired-by-recovery"
            session.add(
                AccountSession(
                    token_hash="synthetic-session-from-snapshot",
                    account_id=account.id,
                    expires_at=now() + timedelta(days=1),
                )
            )
            session.add(
                Profile(
                    account_id=account.id,
                    data={"headline": "Synthetic restore check"},
                    photo_ciphertext=cipher.encrypt(private),
                )
            )
            session.add(
                Resume(
                    account_id=account.id,
                    filename="synthetic.txt",
                    media_type="text/plain",
                    size_bytes=len(private),
                    file_ciphertext=cipher.encrypt(private),
                )
            )
            job = JobInput(
                external_id="1",
                title="Reviewer role",
                company="Reviewer Example",
                description="Synthetic restoration fixture",
                location="London",
                source_url="https://example.org/jobs/1",
                application_url="https://example.org/apply/1",
            )
            ingest(session, source, Enumeration(jobs=[job], complete=True))
            session.commit()
        backed_up = backup(Path(".cache/release-finalization/backups"), args.pg_bin)
        archive = Path(backed_up["archive"])
        assert private not in archive.read_bytes()
        corrupt = archive.with_name("tampered.rwbackup")
        damaged = bytearray(archive.read_bytes())
        damaged[-1] ^= 1
        corrupt.write_bytes(damaged)
        corrupt.chmod(0o600)
        try:
            restore(corrupt, args.pg_bin)
            raise AssertionError("Tampered backup unexpectedly accepted")
        except InvalidTag:
            pass
        restored_at = time.monotonic()
        result = restore(archive, args.pg_bin)
        restore_seconds = time.monotonic() - restored_at
        target_engine = create_engine(os.environ["RESTORE_DATABASE_URL"])
        engines.append(target_engine)
        with Session(target_engine) as session:
            resumed = session.get(Resume, account_id)
            profile = session.get(Profile, account_id)
            assert cipher.decrypt(resumed.file_ciphertext) == private
            assert cipher.decrypt(profile.photo_ciphertext) == private
            assert session.scalar(select(Source)).slug == "restore-example"
            assert session.scalar(select(AccountSession)) is None
            restored_account = session.get(Account, account_id)
            assert restored_account.email_code_hash is None
            assert restored_account.password_reset_hash is None
        with Session(source_engine) as session:
            assert session.get(AccountSession, "synthetic-session-from-snapshot") is not None
            assert session.get(Account, account_id).email_code_hash is not None
        try:
            restore(archive, args.pg_bin)
            raise AssertionError("Nonempty restore target accepted")
        except ValueError as error:
            assert "empty" in str(error)
        original_target = os.environ["RESTORE_DATABASE_URL"]
        os.environ["RESTORE_DATABASE_URL"] = os.environ["DATABASE_URL"]
        try:
            restore(archive, args.pg_bin)
            raise AssertionError("Same-database restore accepted")
        except ValueError as error:
            assert "separate" in str(error)
        finally:
            os.environ["RESTORE_DATABASE_URL"] = original_target
        report = {
            "scope": "Disposable local PostgreSQL databases; synthetic accounts and resume only",
            "table_counts_match": result["table_counts_match"],
            "restored_authentication_revoked": result["authentication_revoked"],
            "source_authentication_untouched": True,
            "tables": result["tables"],
            "private_resume_and_photo_decrypt": True,
            "tampering_rejected": True,
            "nonempty_target_refused": True,
            "same_database_refused": True,
            "plaintext_canary_absent_from_archive": True,
            "archive_mode": oct(archive.stat().st_mode & 0o777),
            "encrypted_bytes": backed_up["encrypted_bytes"],
            "archive_sha256": backed_up["sha256"],
            "source_snapshot_at": result["source_snapshot_at"],
            "restore_seconds": round(restore_seconds, 3),
            "total_drill_seconds": round(time.monotonic() - started, 3),
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report))
    finally:
        for engine in engines:
            engine.dispose()
        with connect(admin_env) as admin:
            admin.autocommit = True
            for name in created:
                admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


if __name__ == "__main__":
    try:
        main()
    except (psycopg.Error, RuntimeError) as error:
        print(json.dumps({"status": "failed", "error_kind": type(error).__name__}))
        raise SystemExit(1) from None

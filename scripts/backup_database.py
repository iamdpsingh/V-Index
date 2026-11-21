"""Encrypted PostgreSQL backups and restores into an empty, separate database.

Credentials are read from environment, never command arguments or evidence.
Backup and resume encryption keys must be retained separately from the archive.
"""

import argparse
import base64
import hashlib
import json
import os
import struct
import subprocess
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from psycopg import sql
from sqlalchemy.engine import make_url

MAGIC = b"ROLEWISPBK1"
CHUNK = 64 * 1024


def encryption_key() -> bytes:
    raw = os.environ.get("BACKUP_ENCRYPTION_KEY", "")
    try:
        key = base64.b64decode(raw.encode(), altchars=b"-_", validate=True)
    except (ValueError, UnicodeError) as error:
        raise ValueError("Configure a private base64 backup key") from error
    if len(key) != 32 or raw == os.environ.get("RESUME_ENCRYPTION_KEY"):
        raise ValueError("Use a separate 32-byte backup encryption key")
    return key


def database_env(variable: str) -> dict[str, str]:
    url = make_url(os.environ[variable])
    if url.get_backend_name() != "postgresql" or not url.host or not url.database:
        raise ValueError("A dedicated PostgreSQL database URL is required")
    # pg_dump needs database/TLS configuration, not application encryption,
    # OAuth or mail secrets from the parent process.
    allowed = {
        "PATH",
        "HOME",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "TZ",
        "PGSSLMODE",
        "PGSSLROOTCERT",
        "PGCHANNELBINDING",
        "PGSSLCERT",
        "PGSSLKEY",
        "PGSSLCRL",
        "SSL_CERT_FILE",
        "PGPASSFILE",
    }
    env = {key: value for key, value in os.environ.items() if key in allowed}
    for name in ("PGSERVICE", "PGSERVICEFILE", "PGOPTIONS"):
        env.pop(name, None)
    env.update(
        PGHOST=url.host,
        PGPORT=str(url.port or 5432),
        PGDATABASE=url.database,
        PGUSER=url.username or "",
        PGPASSWORD=url.password or "",
        PGCONNECT_TIMEOUT="10",
    )
    for option, value in url.query.items():
        if option in {"sslmode", "sslrootcert", "channel_binding"} and isinstance(value, str):
            env["PG" + option.upper().replace("_", "")] = value
    return env


def connect(env):
    tls = {}
    if env.get("PGSSLROOTCERT"):
        tls["sslrootcert"] = env["PGSSLROOTCERT"]
    if env.get("PGCHANNELBINDING"):
        tls["channel_binding"] = env["PGCHANNELBINDING"]
    return psycopg.connect(
        host=env["PGHOST"],
        port=env["PGPORT"],
        dbname=env["PGDATABASE"],
        user=env["PGUSER"],
        password=env["PGPASSWORD"],
        connect_timeout=10,
        sslmode=env.get("PGSSLMODE", "prefer"),
        **tls,
    )


def counts(connection) -> dict[str, int]:
    tables = connection.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
    ).fetchall()
    return {
        name: connection.execute(
            sql.SQL("SELECT count(*) FROM public.{}").format(sql.Identifier(name))
        ).fetchone()[0]
        for (name,) in tables
    }


def run_pg(binary: Path, args: list[str], env: dict) -> None:
    try:
        result = subprocess.run([str(binary), *args], env=env, capture_output=True, timeout=900)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"{binary.name} exceeded the operator time budget") from None
    if result.returncode:
        # pg error text can contain connection or database details. Keep it private.
        raise RuntimeError(f"{binary.name} failed (exit {result.returncode})")


def encrypt(source: Path, target: Path, manifest: dict, key: bytes) -> None:
    metadata = json.dumps(manifest, sort_keys=True).encode()
    if len(metadata) > 65536:
        raise ValueError("Oversized backup manifest")
    nonce = os.urandom(12)
    header = MAGIC + struct.pack(">I", len(metadata)) + metadata + nonce
    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()
    cipher.authenticate_additional_data(header)
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as output, source.open("rb") as input_file:
            output.write(header)
            while chunk := input_file.read(CHUNK):
                output.write(cipher.update(chunk))
            output.write(cipher.finalize())
            output.write(cipher.tag)
            output.flush()
            os.fsync(output.fileno())
    except BaseException:
        target.unlink(missing_ok=True)
        raise


def decrypt(source: Path, target: Path, key: bytes) -> dict:
    with source.open("rb") as input_file:
        if input_file.read(len(MAGIC)) != MAGIC:
            raise ValueError("Unrecognized backup format")
        length_bytes = input_file.read(4)
        if len(length_bytes) != 4:
            raise ValueError("Truncated backup")
        length = struct.unpack(">I", length_bytes)[0]
        if length > 65536:
            raise ValueError("Oversized backup manifest")
        metadata = input_file.read(length)
        nonce = input_file.read(12)
        header = MAGIC + length_bytes + metadata + nonce
        remaining = source.stat().st_size - len(header) - 16
        if remaining < 0:
            raise ValueError("Truncated backup")
        cipher = Cipher(algorithms.AES(key), modes.GCM(nonce)).decryptor()
        cipher.authenticate_additional_data(header)
        with target.open("xb") as output:
            target.chmod(0o600)
            while remaining:
                chunk = input_file.read(min(CHUNK, remaining))
                if not chunk:
                    raise ValueError("Truncated ciphertext")
                remaining -= len(chunk)
                output.write(cipher.update(chunk))
            output.write(cipher.finalize_with_tag(input_file.read(16)))
    return json.loads(metadata)


def backup(directory: Path, pg_bin: Path) -> dict:
    key, env = encryption_key(), database_env("DATABASE_URL")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    at = datetime.now(UTC)
    target = directory / (
        "rolewisp-" + at.strftime("%Y%m%dT%H%M%SZ-") + os.urandom(4).hex() + ".rwbackup"
    )
    with tempfile.TemporaryDirectory(prefix="rolewisp-backup-") as temporary:
        dump = Path(temporary) / "database.dump"
        with connect(env) as connection:
            connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            snapshot = connection.execute("SELECT pg_export_snapshot()").fetchone()[0]
            table_counts = counts(connection)
            manifest = {"created_at": at.isoformat(), "tables": table_counts, "format": 1}
            if "sources" not in table_counts or "alembic_version" not in table_counts:
                raise ValueError("The source is not a migrated Rolewisp database")
            run_pg(
                pg_bin / "pg_dump",
                [
                    "--format=custom",
                    "--no-owner",
                    "--no-privileges",
                    "--snapshot=" + snapshot,
                    "--file=" + str(dump),
                ],
                env,
            )
        encrypt(dump, target, manifest, key)
    with target.open("rb") as encrypted:
        digest = hashlib.file_digest(encrypted, "sha256").hexdigest()
    return {
        "archive": str(target),
        "encrypted_bytes": target.stat().st_size,
        "sha256": digest,
        "manifest": manifest,
    }


def revoke_restored_authentication(connection) -> None:
    """Invalidate snapshot credentials only in the separate recovery target."""
    connection.execute("DELETE FROM public.account_sessions")
    connection.execute(
        "UPDATE public.accounts SET email_code_hash=NULL, email_code_expires_at=NULL, "
        "password_reset_hash=NULL, password_reset_expires_at=NULL"
    )


def restore(archive: Path, pg_bin: Path) -> dict:
    key, env = encryption_key(), database_env("RESTORE_DATABASE_URL")
    source = make_url(os.environ["DATABASE_URL"])
    target = make_url(os.environ["RESTORE_DATABASE_URL"])
    if (source.host, source.port or 5432, source.database) == (
        target.host,
        target.port or 5432,
        target.database,
    ):
        raise ValueError("Restore must use a separate database")
    with tempfile.TemporaryDirectory(prefix="rolewisp-restore-") as temporary:
        dump = Path(temporary) / "verified.dump"
        manifest = decrypt(archive, dump, key)  # Authenticate before any restore mutation.
        with connect(env) as connection:
            objects = connection.execute(
                "SELECT count(*) FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog','information_schema')"
            ).fetchone()[0]
            if objects:
                raise ValueError("Restore target must be empty; existing data is never replaced")
        run_pg(
            pg_bin / "pg_restore",
            [
                "--exit-on-error",
                "--single-transaction",
                "--no-owner",
                "--no-privileges",
                "--dbname=" + env["PGDATABASE"],
                str(dump),
            ],
            env,
        )
        with connect(env) as connection:
            actual = counts(connection)
        if actual != manifest["tables"]:
            raise ValueError("Restored table counts do not match the exported snapshot")
        with connect(env) as connection:
            revoke_restored_authentication(connection)
    return {
        "restored_at": datetime.now(UTC).isoformat(),
        "table_counts_match": True,
        "tables": actual,
        "source_snapshot_at": manifest["created_at"],
        "authentication_revoked": True,
        "post_snapshot_deletion_reconciliation_required": True,
    }


def prune(directory: Path) -> int:
    threshold = datetime.now(UTC) - timedelta(days=30)
    removed = 0
    for archive in directory.glob("rolewisp-*.rwbackup"):
        if (
            archive.is_symlink()
            or not archive.is_file()
            or datetime.fromtimestamp(archive.stat().st_mtime, UTC) >= threshold
        ):
            continue
        with archive.open("rb") as handle:
            if handle.read(len(MAGIC)) != MAGIC:
                continue
        archive.unlink()
        removed += 1
    return removed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["backup", "restore", "prune"])
    parser.add_argument("--directory", type=Path, default=Path(".cache/backups"))
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--pg-bin", type=Path, default=Path("/usr/bin"))
    args = parser.parse_args()
    try:
        if args.action == "backup":
            result = backup(args.directory, args.pg_bin)
        elif args.action == "restore" and args.archive:
            result = restore(args.archive, args.pg_bin)
        elif args.action == "prune":
            result = {"removed": prune(args.directory), "retention_days": 30}
        else:
            parser.error("Restore requires --archive")
        print(json.dumps(result))
    except Exception as error:
        print(json.dumps({"status": "failed", "error_kind": type(error).__name__}))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()

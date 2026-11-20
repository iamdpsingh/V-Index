"""Authenticated encrypted snapshots to a dedicated private Blob store."""

import os
import pwd
import re
import secrets
import socket
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx2
from vercel.api import session as blob_session
from vercel.blob import sync as blob

from scripts.backup_database import backup, restore, run_pg

PREFIX = "rolewisp-backups/"
OWN_ARCHIVE = re.compile(r"rolewisp-backups/rolewisp-\d{8}T\d{6}Z-[a-f0-9]{8}\.rwbackup\Z")
MAX_ARCHIVE = 128 * 1024 * 1024
MAX_STORED = 512 * 1024 * 1024


def enforce_ttl(request):
    # Python SDK 0.6 lacks ttl_days. These are the exact wire headers used by
    # the official @vercel/blob 2.9.0 SDK for provider-enforced expiry.
    if (
        request.method == "PUT"
        and request.url.host == "vercel.com"
        and request.url.path.startswith("/api/blob")
    ):
        request.headers["x-ttl-days"] = "7"
        request.headers["x-api-version"] = "13"


def verify_ttl(response):
    if response.request.method == "PUT" and 200 <= response.status_code < 300:
        response.read()
        expires = response.json().get("expiresAt")
        if not isinstance(expires, str):
            raise ValueError("Provider did not confirm backup expiry")
        expiry = datetime.fromisoformat(expires.replace("Z", "+00:00"))
        if (
            not datetime.now(UTC) + timedelta(days=6)
            < expiry
            <= datetime.now(UTC) + timedelta(days=8)
        ):
            raise ValueError("Provider returned an unexpected retention period")


def storage_session():
    def credentials():
        return blob.BlobCredentials(
            token=os.environ["BLOB_READ_WRITE_TOKEN"], store_id=os.environ["BLOB_STORE_ID"]
        )

    return blob_session(
        service_options=[
            blob.SyncBlobServiceOptions(
                base_url="https://vercel.com/api/blob", credentials_factory=credentials
            )
        ],
        httpx_client_factory=lambda: httpx2.Client(
            trust_env=False,
            follow_redirects=False,
            timeout=60,
            event_hooks={"request": [enforce_ttl], "response": [verify_ttl]},
        ),
    )


def publish_report(path: str, report: dict) -> None:
    import json

    if path not in {
        "operations/latest.json",
        "operations/release-review.json",
        "operations/backup-latest.json",
    }:
        raise ValueError("Unknown operator report")
    with storage_session():
        blob.put_blob(
            path,
            json.dumps(report).encode(),
            access="private",
            content_type="application/json",
            allow_overwrite=True,
            cache_control_max_age=60,
        )


def verify_restore(archive: Path, pg_bin: Path) -> dict:
    """Restore only into a disposable loopback PostgreSQL instance, never the source."""
    from sqlalchemy.engine import URL

    with tempfile.TemporaryDirectory(prefix="rw-recovery-", dir="/tmp") as directory:
        root = Path(directory)
        password = secrets.token_urlsafe(32)
        password_file = root / "password"
        password_file.write_text(password)
        password_file.chmod(0o600)
        username = pwd.getpwuid(os.getuid()).pw_name
        env = {
            key: value
            for key, value in os.environ.items()
            if key in {"PATH", "HOME", "LANG", "LC_ALL", "TZ"}
        }
        data = root / "data"
        run_pg(
            pg_bin / "initdb",
            [
                "-D",
                str(data),
                "--no-locale",
                "--encoding=UTF8",
                "--auth-host=scram-sha-256",
                "--auth-local=trust",
                "--username=" + username,
                "--pwfile=" + str(password_file),
            ],
            env,
        )
        password_file.unlink()
        with socket.socket() as reserved:
            reserved.bind(("127.0.0.1", 0))
            port = reserved.getsockname()[1]
        started = False
        previous = os.environ.get("RESTORE_DATABASE_URL")
        try:
            run_pg(
                pg_bin / "pg_ctl",
                [
                    "-D",
                    str(data),
                    "-l",
                    str(root / "server.log"),
                    "-w",
                    "-t",
                    "30",
                    "-o",
                    f"-h 127.0.0.1 -p {port} -k {directory} -c shared_buffers=16MB -c max_connections=10",
                    "start",
                ],
                env,
            )
            started = True
            os.environ["RESTORE_DATABASE_URL"] = URL.create(
                "postgresql+psycopg",
                username=username,
                password=password,
                host="127.0.0.1",
                port=port,
                database="postgres",
                query={"sslmode": "disable"},
            ).render_as_string(hide_password=False)
            result = restore(archive, pg_bin)
            return {
                "table_counts_match": result["table_counts_match"],
                "tables": result["tables"],
                "isolated_loopback_target": True,
            }
        finally:
            if previous is None:
                os.environ.pop("RESTORE_DATABASE_URL", None)
            else:
                os.environ["RESTORE_DATABASE_URL"] = previous
            if started:
                run_pg(pg_bin / "pg_ctl", ["-D", str(data), "-m", "fast", "-w", "stop"], env)


def create_cloud_backup() -> dict:
    pg_bin = Path(os.getenv("PG_BIN", "/usr/lib/postgresql/18/bin"))
    with tempfile.TemporaryDirectory(prefix="rolewisp-encrypted-") as directory:
        result = backup(Path(directory), pg_bin)
        archive = Path(result["archive"])
        if result["encrypted_bytes"] > MAX_ARCHIVE:
            raise ValueError("Backup exceeds free-tier archive budget")
        recovery = verify_restore(archive, pg_bin)
        pathname = PREFIX + archive.name
        with storage_session():
            with archive.open("rb") as file:
                blob.put_blob(
                    pathname,
                    file,
                    access="private",
                    content_type="application/octet-stream",
                    content_length=result["encrypted_bytes"],
                    cache_control_max_age=60,
                )
            if blob.head_blob(pathname).size != result["encrypted_bytes"]:
                raise ValueError("Uploaded archive size mismatch")
            # Delete only this application's immutable encrypted archive names,
            # and only after a new snapshot has passed a full restore and upload.
            archives: list[blob.ListBlob] = []
            for item in blob.query_blobs(prefix=PREFIX, page_size=100):
                if len(archives) >= 500:
                    raise ValueError("Backup inventory exceeds cleanup budget")
                if OWN_ARCHIVE.fullmatch(item.pathname):
                    archives.append(item)
            archives.sort(key=lambda item: item.uploaded_at, reverse=True)
            retained, purged = 0, 0
            cutoff = datetime.now(UTC) - timedelta(days=7)
            for item in archives:
                if item.pathname != pathname and (
                    item.uploaded_at < cutoff or retained + item.size > MAX_STORED
                ):
                    blob.delete_blob(item.pathname)
                    purged += 1
                else:
                    retained += item.size
        report = {
            "status": "success",
            "at": datetime.now(UTC).isoformat(),
            "pathname": pathname,
            "encrypted_bytes": result["encrypted_bytes"],
            "sha256": result["sha256"],
            "restore": recovery,
            "retained_bytes": retained,
            "archives_pruned": purged,
            "retention_days": 7,
            "provider_expiry_verified": True,
            "storage_access": "private",
        }
        publish_report("operations/backup-latest.json", report)
        return report

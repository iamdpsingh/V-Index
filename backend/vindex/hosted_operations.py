"""Independent production monitoring and encrypted offsite backup supervision."""

import asyncio
import json
import os
import time
from datetime import UTC, datetime

from vindex.accounts.security import redis_client
from vindex.db import Session
from vindex.operations import log_event, snapshot


async def monitor() -> None:
    from scripts.cloud_backup import publish_report

    await asyncio.sleep(20)  # Allow the independent worker heartbeat to start.
    previous = None
    last_publish = -1800.0
    while True:
        try:

            def collect():
                with Session() as session:
                    report = snapshot(session)
                redis = redis_client()
                backup = redis.get("vindex:backup:last-result")
                if isinstance(backup, (bytes, str)) and backup:
                    report["backup"] = json.loads(backup)
                    if report["backup"].get("status") == "failed":
                        report["alerts"].append("backup_failed")
                redis.setex("vindex:operations:latest", 180, json.dumps(report))
                return report

            report = await asyncio.to_thread(collect)
            state = (
                tuple(report["alerts"]),
                report["counts"]["failing"],
                report["counts"]["stale"],
            )
            if state != previous:
                log_event(
                    "operations_health",
                    alerts=report["alerts"],
                    counts=report["counts"],
                    live_workers=report["workers"]["live"],
                )
                if report["alerts"]:
                    redis = redis_client()
                    alert = json.dumps(
                        {
                            "at": report["checked_at"],
                            "alerts": report["alerts"],
                            "counts": report["counts"],
                        }
                    )
                    redis.lpush("vindex:operations:alerts", alert)
                    redis.ltrim("vindex:operations:alerts", 0, 49)
                    redis.expire("vindex:operations:alerts", 7 * 86400)
                previous = state
            if os.getenv("BLOB_READ_WRITE_TOKEN") and time.monotonic() - last_publish >= 1800:
                await asyncio.to_thread(publish_report, "operations/latest.json", report)
                last_publish = time.monotonic()
        except Exception as error:
            log_event("operations_monitor_failed", error_kind=type(error).__name__)
        await asyncio.sleep(60)


async def backups() -> None:
    from scripts.cloud_backup import create_cloud_backup, publish_report

    while True:
        try:
            if not os.getenv("BACKUP_ENCRYPTION_KEY") or not os.getenv("BLOB_READ_WRITE_TOKEN"):
                await asyncio.sleep(300)
                continue

            def once():
                redis = redis_client()
                previous = redis.get("vindex:backup:last-success-time")
                if isinstance(previous, (bytes, str)) and time.time() - float(previous) < 86400:
                    return
                with redis.lock("vindex:encrypted-backup", timeout=1800, blocking_timeout=1):
                    # A rolling deployment may have just completed the snapshot.
                    stamp = redis.get("vindex:backup:last-success-time")
                    if isinstance(stamp, (bytes, str)) and time.time() - float(stamp) < 86400:
                        return
                    try:
                        report = create_cloud_backup()
                        redis.set("vindex:backup:last-success-time", str(time.time()))
                        redis.set("vindex:backup:last-result", json.dumps(report))
                        log_event(
                            "backup_success",
                            encrypted_bytes=report["encrypted_bytes"],
                            tables_restored=len(report["restore"]["tables"]),
                        )
                    except Exception as error:
                        redis.set(
                            "vindex:backup:last-result",
                            json.dumps(
                                {
                                    "status": "failed",
                                    "at": datetime.now(UTC).isoformat(),
                                    "error_kind": type(error).__name__,
                                }
                            ),
                        )
                        publish_report(
                            "operations/backup-latest.json",
                            {
                                "status": "failed",
                                "at": datetime.now(UTC).isoformat(),
                                "error_kind": type(error).__name__,
                            },
                        )
                        raise

            await asyncio.to_thread(once)
        except Exception as error:
            log_event("backup_failed", error_kind=type(error).__name__)
        await asyncio.sleep(3600)


async def release_review() -> None:
    from scripts.production_review import run_review

    review_id = os.getenv("RELEASE_REVIEW_ID", "")
    if not review_id:
        return
    await asyncio.sleep(45)
    try:

        def once():
            redis = redis_client()
            key = "vindex:release-review:" + review_id
            with redis.lock(key + ":lock", timeout=600, blocking_timeout=1):
                if redis.exists(key):
                    return
                result = run_review()
                redis.setex(key, 7 * 86400, result["status"])
                log_event("production_review", status=result["status"], checks=result["checks"])

        await asyncio.to_thread(once)
    except Exception as error:
        log_event("production_review_failed", error_kind=type(error).__name__)

"""Operator-only source health and expiring, independent worker heartbeats."""

import asyncio
import json
import logging
import uuid
from datetime import timedelta

from redis.exceptions import RedisError
from sqlalchemy import func, select

from vindex.accounts.security import redis_client
from vindex.db import Run, Source, now
from vindex.ingest import aware

log = logging.getLogger("vindex.operations")
HEARTBEAT_PREFIX = "vindex:worker-heartbeat:"


def status_record(value) -> dict:
    if not isinstance(value, (bytes, str)):
        return {}
    try:
        decoded = json.loads(value)
        return decoded if isinstance(decoded, dict) else {}
    except (ValueError, UnicodeError):
        return {}


async def heartbeat() -> None:
    key = HEARTBEAT_PREFIX + uuid.uuid4().hex
    redis = redis_client()
    try:
        while True:
            try:
                redis.setex(key, 90, now().isoformat())
            except RedisError:
                log_event("worker_heartbeat_unavailable")
            await asyncio.sleep(15)
    finally:
        try:
            redis.delete(key)
        except RedisError:
            pass


def source_health(session, checked=None) -> dict:
    checked = checked or now()
    successes = dict(
        session.execute(
            select(Run.source_id, func.max(Run.finished_at))
            .where(Run.status == "success")
            .group_by(Run.source_id)
        ).all()
    )
    latest_ids = select(func.max(Run.id)).group_by(Run.source_id)
    latest = {
        row.source_id: row for row in session.scalars(select(Run).where(Run.id.in_(latest_ids)))
    }
    abandoned_sources = set(
        session.scalars(
            select(Run.source_id).where(
                Run.status == "running", Run.started_at < checked - timedelta(hours=1)
            )
        )
    )
    rows = []
    for source in session.scalars(select(Source).where(Source.provider != "employer_posting")):
        run = latest.get(source.id)
        success = successes.get(source.id)
        age = (checked - aware(success)).total_seconds() if success else None
        stale = age is not None and age > max(7200, source.refresh_minutes * 120)
        abandoned = source.id in abandoned_sources
        rows.append(
            {
                "source_id": source.id,
                "provider": source.provider,
                "initial_index_complete": success is not None,
                "last_success_at": aware(success).isoformat() if success else None,
                "success_age_seconds": int(age) if age is not None else None,
                "next_check_at": aware(source.next_check).isoformat(),
                "last_attempt_status": run.status if run else "not_started",
                "last_attempt_count": run.count if run else None,
                "failure_kind": run.error.split(":", 1)[0][:80] if run and run.error else None,
                "consecutive_failures": source.failures,
                "stale": stale,
                "abandoned_run": abandoned,
            }
        )
    return {
        "checked_at": checked.isoformat(),
        "sources": rows,
        "counts": {
            "sources": len(rows),
            "initial_index_complete": sum(row["initial_index_complete"] for row in rows),
            "initial_index_pending": sum(not row["initial_index_complete"] for row in rows),
            "failing": sum(row["consecutive_failures"] > 0 for row in rows),
            "stale": sum(row["stale"] for row in rows),
            "abandoned_runs": sum(row["abandoned_run"] for row in rows),
        },
    }


def snapshot(session) -> dict:
    result = source_health(session)
    try:
        redis = redis_client()
        workers: list[str] = []
        for key in redis.scan_iter(match=HEARTBEAT_PREFIX + "*", count=100):
            if len(workers) >= 100:
                break
            stamp = redis.get(key)
            if isinstance(stamp, (bytes, str)) and stamp:
                workers.append(stamp.decode() if isinstance(stamp, bytes) else stamp)
        result.update(redis_available=True, workers={"live": len(workers), "heartbeats": workers})
        violations: dict[str, int] = {}
        for key in redis.scan_iter(match="vindex:csp:*", count=100):
            if len(violations) >= 100:
                break
            name = key.decode() if isinstance(key, bytes) else key
            count = redis.get(key)
            violations[name.removeprefix("vindex:csp:")] = (
                int(count) if isinstance(count, (str, bytes, int)) else 0
            )
        result["csp_violations"] = violations
        backup = redis.get("vindex:backup:last-result")
        if isinstance(backup, (bytes, str)) and backup:
            result["backup"] = status_record(backup)
        latest = redis.get("vindex:operations:latest")
        if isinstance(latest, (bytes, str)) and latest:
            result["monitor"] = {"last_checked_at": status_record(latest).get("checked_at")}
    except RedisError:
        result.update(redis_available=False, workers={"live": 0, "heartbeats": []})
    counts = result["counts"]
    result["alerts"] = [name for name in ("failing", "stale", "abandoned_runs") if counts[name]]
    if not result["redis_available"]:
        result["alerts"].append("redis_unavailable")
    if not result["workers"]["live"]:
        result["alerts"].append("worker_missing")
    return result


def log_event(event: str, **fields) -> None:
    log.info(json.dumps({"event": event, "at": now().isoformat(), **fields}, sort_keys=True))

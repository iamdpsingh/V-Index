"""Redis leases serialize refreshes. DB commits index changes atomically."""

import asyncio
import logging
import os
from datetime import timedelta

import httpx
from redis import Redis
from sqlalchemy import select

from vindex.connectors.jobiqo import STAGED_HOSTS as STAGED_JOBIQO_HOSTS
from vindex.connectors.registry import create_connector
from vindex.db import Run, Session, Source, now
from vindex.ingest import aware, ingest
from vindex.jobiqo_refresh import advance_jobiqo_refresh
from vindex.madgex_refresh import advance_madgex_refresh

log = logging.getLogger("vindex.worker")


async def refresh(source_id: int, *, only_if_due: bool = False) -> int | None:
    redis = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    # 15-minute lease exceeds the bounded 10-minute refresh timeout.
    with redis.lock(f"vindex:source:{source_id}", timeout=900, blocking_timeout=1):
        with Session() as session:
            source = session.get(Source, source_id)
            if source is None:
                raise ValueError("Source not found")
            if only_if_due and aware(source.next_check) > now():
                return None
            run = Run(source_id=source_id)
            session.add(run)
            session.commit()
            run_id = run.id
            try:
                async with asyncio.timeout(600):
                    async with httpx.AsyncClient(
                        timeout=30,
                        trust_env=False,
                        headers={
                            "User-Agent": "V-Index/0.1 public-job-indexer",
                            "Accept": "application/json",
                        },
                    ) as client:
                        if source.provider == "wileymadgex":
                            batch = await advance_madgex_refresh(session, source, client)
                        elif source.provider == "jobiqo" and source.slug in STAGED_JOBIQO_HOSTS:
                            batch = await advance_jobiqo_refresh(session, source, client)
                        else:
                            batch = await create_connector(
                                source.provider, source.slug, source.company, client
                            ).discover()
                if batch is None:
                    run.status, run.finished_at = "in_progress", now()
                    source.next_check = now()
                    session.commit()
                    return run_id
                # Lock source during reconciliation, preventing concurrent DB writers.
                session.scalar(select(Source).where(Source.id == source_id).with_for_update())
                ingest(session, source, batch)
                run.status, run.count = "success", len(batch.jobs)
                run.finished_at, source.failures = now(), 0
                source.next_check = now() + timedelta(minutes=source.refresh_minutes)
                session.commit()
                log.info("refresh_success source=%s run=%s count=%s", source_id, run_id, run.count)
            except Exception as error:
                session.rollback()
                failed_run = session.get(Run, run_id)
                source = session.get(Source, source_id)
                assert failed_run is not None and source is not None
                failed_run.status, failed_run.error = (
                    "failed",
                    f"{type(error).__name__}: {str(error)[:500]}",
                )
                failed_run.finished_at = now()
                source.failures += 1
                # Persistent backoff/circuit cooldown; no closures on failure.
                source.next_check = now() + timedelta(
                    minutes=min(1440, 15 * 2 ** min(source.failures, 7))
                )
                session.commit()
                log.warning(
                    "refresh_failed source=%s run=%s error=%s", source_id, run_id, failed_run.error
                )
            return run_id


async def serve() -> None:
    logging.basicConfig(level=logging.INFO)
    # Public source URLs can include browser read tokens. Keep transport URLs out of logs.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    while True:
        with Session() as session:
            ids = list(
                session.scalars(
                    select(Source.id)
                    .where(Source.next_check <= now())
                    .order_by(Source.next_check)
                    .limit(20)
                )
            )
        for source_id in ids:
            try:
                await refresh(source_id, only_if_due=True)
            except Exception:
                log.exception("Worker infrastructure failure source=%s", source_id)
        await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(serve())

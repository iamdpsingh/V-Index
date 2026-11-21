"""Register reviewed public sources once and run the persistent index worker."""

import asyncio
import logging
import os
from urllib.parse import urlsplit

from redis import Redis


def requeue_repaired_hireology(session) -> list[int]:
    """Retry only obsolete parser failures; never override policy/429 cooldowns."""
    from sqlalchemy import func, select
    from vindex.db import Run, Source, now

    latest = select(func.max(Run.id)).group_by(Run.source_id)
    sources = list(
        session.scalars(
            select(Source)
            .join(Run, Run.source_id == Source.id)
            .where(
                Source.provider == "hireology",
                Run.id.in_(latest),
                Run.status == "failed",
                Run.error == "ValueError: Missing unique Hireology public career bootstrap",
            )
        )
    )
    for source in sources:
        source.next_check = now()
    session.commit()
    return [source.id for source in sources]


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    log = logging.getLogger("vindex.bootstrap")
    database = os.getenv("DATABASE_URL", "")
    redis_url = os.getenv("REDIS_URL", "")
    if urlsplit(database).scheme != "postgresql+psycopg" or urlsplit(redis_url).scheme not in {
        "redis",
        "rediss",
    }:
        log.error("Production worker requires PostgreSQL and Redis connection variables")
        return 1
    try:
        # The shared image starts no HTTP server or migrations in this process.
        os.environ.setdefault("WORKER_CONCURRENCY", "2")
        os.environ.setdefault("HOSTED_OPERATIONS_ENABLED", "true")
        from vindex.db import Session
        from vindex.worker import serve

        from scripts.register_verified_sources import register_sources

        with Redis.from_url(redis_url, socket_connect_timeout=5, socket_timeout=5) as redis:
            # Rolling deployments may overlap. Serialize only the idempotent registration.
            with redis.lock(
                "vindex:reviewed-source-registration", timeout=120, blocking_timeout=30
            ):
                result = register_sources(apply=True)
                repair_key = "vindex:repair:hireology-ssr-v1"
                if not redis.exists(repair_key):
                    with Session() as session:
                        repaired = requeue_repaired_hireology(session)
                    redis.setex(repair_key, 7 * 86400, "scheduled")
                    log.info("Repaired Hireology sources scheduled: count=%s", len(repaired))
        log.info(
            "Reviewed sources registered: platforms=%s sources=%s new=%s",
            result["verified_platforms"],
            result["reviewed_examples"],
            result["new_sources"],
        )
        asyncio.run(serve())
    except Exception as error:
        # Drivers can include URLs and credentials in exception messages.
        log.error("Production worker stopped: error_kind=%s", type(error).__name__)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Register reviewed public sources once and run the persistent index worker."""

import asyncio
import logging
import os
from urllib.parse import urlsplit

from redis import Redis


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
        from vindex.worker import serve

        from scripts.register_verified_sources import register_sources

        with Redis.from_url(redis_url, socket_connect_timeout=5, socket_timeout=5) as redis:
            # Rolling deployments may overlap. Serialize only the idempotent registration.
            with redis.lock(
                "vindex:reviewed-source-registration", timeout=120, blocking_timeout=30
            ):
                result = register_sources(apply=True)
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

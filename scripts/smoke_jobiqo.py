"""Run the production Jobiqo checkpoint path using an isolated local database."""

import argparse
import asyncio
import hashlib
import json
import subprocess
from pathlib import Path

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from vindex.connectors.jobiqo import BOARDS, STAGED_HOSTS
from vindex.db import JobiqoRefresh, Source, now
from vindex.jobiqo_refresh import advance_jobiqo_refresh


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--host", choices=sorted(STAGED_HOSTS), default="careers.unitedway.org")
    args = parser.parse_args()
    host = args.host
    url = f"https://{host}{BOARDS[host][0]}"
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    args.checkpoint.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    args.checkpoint.touch(mode=0o600, exist_ok=True)
    engine = create_engine(f"sqlite:///{args.checkpoint}")
    try:
        Source.__table__.create(engine, checkfirst=True)
        JobiqoRefresh.__table__.create(engine, checkfirst=True)
        sessions = sessionmaker(engine, expire_on_commit=False)
        async with httpx.AsyncClient(
            trust_env=False,
            timeout=30,
            headers={"User-Agent": "V-Index/0.1 public-job-indexer"},
        ) as client:
            while True:
                with sessions() as session:
                    source = session.get(Source, 1)
                    if source is None:
                        source = Source(id=1, provider="jobiqo", slug=host, company=host, url=url)
                        session.add(source)
                        session.commit()
                    if source.slug != host:
                        raise ValueError("Checkpoint belongs to a different board")
                    async with asyncio.timeout(600):
                        batch = await advance_jobiqo_refresh(session, source, client)
                    session.commit()
                    if batch is not None:
                        print(
                            json.dumps(
                                {
                                    "url": url,
                                    "finished_at": now().isoformat(),
                                    "revision": revision,
                                    "count": len(batch.jobs),
                                    "complete": batch.complete,
                                    "payload_sha256": hashlib.sha256(
                                        batch.model_dump_json().encode()
                                    ).hexdigest(),
                                }
                            ),
                            flush=True,
                        )
                        return
                    stage = session.get(JobiqoRefresh, 1)
                    assert stage is not None
                    print(f"{len(stage.jobs)}/{len(stage.roster)} staged", flush=True)
    finally:
        engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

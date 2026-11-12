"""Run the staged Madgex refresh against isolated local checkpoint databases."""

import argparse
import asyncio
import hashlib
import json
import subprocess
from pathlib import Path

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from vindex.connectors.wileymadgex import BOARDS
from vindex.db import MadgexRefresh, Source, now
from vindex.madgex_refresh import advance_madgex_refresh


async def verify(host: str, directory: Path) -> dict:
    checkpoint = directory / (host + ".sqlite")
    checkpoint.touch(mode=0o600, exist_ok=True)
    engine = create_engine(f"sqlite:///{checkpoint}")
    try:
        Source.__table__.create(engine, checkfirst=True)
        MadgexRefresh.__table__.create(engine, checkfirst=True)
        sessions = sessionmaker(engine, expire_on_commit=False)
        url = f"https://{host}{BOARDS[host]}/jobs/"
        started = now()
        async with httpx.AsyncClient(
            trust_env=False,
            timeout=30,
            headers={"User-Agent": "V-Index/0.1 public-job-indexer", "Accept": "application/json"},
        ) as client:
            while True:
                with sessions() as session:
                    source = session.get(Source, 1)
                    if source is None:
                        source = Source(
                            id=1, provider="wileymadgex", slug=host, company=host, url=url
                        )
                        session.add(source)
                        session.commit()
                    stage = session.get(MadgexRefresh, 1)
                    if stage is not None:
                        started = stage.started_at
                    async with asyncio.timeout(600):
                        batch = await advance_madgex_refresh(session, source, client)
                    session.commit()
                    if batch is not None:
                        return {
                            "url": url,
                            "count": len(batch.jobs),
                            "complete": batch.complete,
                            "checkpoint_started_at": started.isoformat(),
                            "finished_at": now().isoformat(),
                            "payload_sha256": hashlib.sha256(
                                batch.model_dump_json().encode()
                            ).hexdigest(),
                        }
                    stage = session.get(MadgexRefresh, 1)
                    assert stage is not None
                    started = stage.started_at
                    print(
                        f"{host}: {len(stage.jobs)}/{len(stage.roster)} details staged",
                        flush=True,
                    )
    finally:
        engine.dispose()


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--checkpoint-directory",
        type=Path,
        required=True,
        help="An ignored local directory for temporary SQLite job snapshots.",
    )
    parser.add_argument("--host", action="append", choices=BOARDS)
    args = parser.parse_args()
    args.checkpoint_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip())
    hosts = args.host or list(BOARDS)
    results = await asyncio.gather(
        *(verify(host, args.checkpoint_directory) for host in hosts), return_exceptions=True
    )
    for host, result in zip(hosts, results, strict=True):
        if isinstance(result, BaseException):
            result = {"host": host, "complete": False, "error": str(result)[:500]}
        print(json.dumps({"revision": revision, "dirty": dirty, **result}), flush=True)
    if any(isinstance(result, BaseException) for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())

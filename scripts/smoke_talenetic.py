"""Run resumable Talenetic verification through the real worker on an isolated DB.

Set DATABASE_URL to a dedicated validation database and REDIS_URL to a running
Redis, migrate that database, then run with --batches N. No fixture data is used.
Repeated invocations resume successful detail reads within the snapshot window.
"""

import argparse
import asyncio
import hashlib
import json
import os
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select
from vindex.connectors.talenetic import HOSTS
from vindex.db import Observation, Run, Session, Source, TaleneticDetail, TaleneticRefresh
from vindex.worker import refresh

ROOT = Path(__file__).resolve().parents[1]


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", choices=sorted(HOSTS), action="append")
    parser.add_argument("--batches", type=int, default=1)
    args = parser.parse_args()
    if not os.getenv("DATABASE_URL"):
        parser.error("Set DATABASE_URL to a dedicated validation database before running")
    if not 1 <= args.batches <= 1_000:
        parser.error("batches must be between 1 and 1000")
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    code = hashlib.sha256()
    for file in sorted((ROOT / "backend/vindex").rglob("*.py")):
        code.update(str(file.relative_to(ROOT)).encode())
        code.update(file.read_bytes())
    results = []
    for host in args.host or sorted(HOSTS):
        with Session() as session:
            source = session.scalar(
                select(Source).where(Source.provider == "talenetic", Source.slug == host)
            )
            if source is None:
                source = Source(
                    provider="talenetic", slug=host, company=host, url="https://" + host + "/"
                )
                session.add(source)
                session.commit()
            source_id = source.id
        result = {
            "provider": "Talenetic",
            "url": "https://" + host + "/",
            "revision": revision,
            "code_sha256": code.hexdigest(),
            "at": datetime.now(UTC).isoformat(),
        }
        for _ in range(args.batches):
            run_id = await refresh(source_id)
            with Session() as session:
                run = session.get(Run, run_id)
                assert run is not None
                stage = session.get(TaleneticRefresh, source_id)
                saved = session.scalar(
                    select(func.count())
                    .select_from(TaleneticDetail)
                    .where(TaleneticDetail.source_id == source_id)
                )
                result.update(
                    status=run.status,
                    complete=run.status == "success",
                    count=run.count,
                    staged_details=saved,
                    roster_count=len(stage.roster) if stage else result.get("roster_count"),
                    finished_at=datetime.now(UTC).isoformat(),
                    error_kind=(run.error or "").split(":", 1)[0] or None,
                )
                if stage:
                    result["roster_sha256"] = hashlib.sha256(
                        json.dumps(stage.roster, sort_keys=True).encode()
                    ).hexdigest()
                    expired = session.scalar(
                        select(func.count())
                        .select_from(TaleneticDetail)
                        .where(
                            TaleneticDetail.source_id == source_id,
                            TaleneticDetail.data["expired"].as_boolean().is_(True),
                        )
                    )
                    result.update(active_details=saved - expired, expired_details=expired)
                model = Observation if run.status == "success" else TaleneticDetail
                # Read only the tiny flag arrays, never every staged HTML description.
                flags = session.scalars(
                    select(model.data["quality_flags"]).where(model.source_id == source_id)
                )
                result["quality_flag_counts"] = dict(
                    Counter(flag for values in flags for flag in (values or []))
                )
                if run.status == "success":
                    result["active_details"] = run.count
                    if result.get("roster_count") is not None:
                        result["expired_details"] = result["roster_count"] - run.count
            print(json.dumps(result), flush=True)
            if result["status"] != "in_progress":
                break
        results.append(result)
    path = (
        ROOT
        / "evidence"
        / (datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-talenetic-worker.json")
    )
    path.write_text(json.dumps(results, indent=2) + "\n")
    print("Evidence: " + str(path.relative_to(ROOT)), flush=True)
    if any(result["status"] == "failed" for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())

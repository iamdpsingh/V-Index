"""Read-only local release measurements. No account/profile/resume tables are read."""

import argparse
import json
import statistics
import time
from pathlib import Path

import httpx
from sqlalchemy import func, select, text
from vindex.db import Observation, Run, Session, Source
from vindex.ingest import aware
from vindex.operations import snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with Session() as session:
        health = snapshot(session)
        jobs = session.scalar(
            select(func.count(func.distinct(Observation.job_id))).where(
                Observation.status == "open"
            )
        )
        observations = session.scalar(
            select(func.count()).select_from(Observation).where(Observation.status == "open")
        )
        db_kind = session.get_bind().dialect.name
        if db_kind == "sqlite":
            size = session.scalar(text("PRAGMA page_count")) * session.scalar(
                text("PRAGMA page_size")
            )
        else:
            size = session.scalar(text("SELECT pg_database_size(current_database())"))
        refreshed = session.scalar(
            select(Source)
            .join(Run, Run.source_id == Source.id)
            .where(Source.provider == "ashby", Run.status == "success")
            .group_by(Source.id)
            .having(func.count(Run.id) >= 2)
            .limit(1)
        )
        repeat = []
        if refreshed:
            for run in session.scalars(
                select(Run)
                .where(Run.source_id == refreshed.id, Run.status == "success")
                .order_by(Run.id.desc())
                .limit(2)
            ):
                repeat.append(
                    {
                        "run_id": run.id,
                        "provider": refreshed.provider,
                        "source_url": refreshed.url,
                        "count": run.count,
                        "started_at": aware(run.started_at).isoformat(),
                        "finished_at": aware(run.finished_at).isoformat(),
                    }
                )
    timings, sizes, statuses = [], [], []
    with httpx.Client(trust_env=False, follow_redirects=False, timeout=10) as client:
        for _ in range(10):
            started = time.perf_counter()
            result = client.get(
                "http://localhost:3000/api/v1/jobs", params={"view": "summary", "limit": 25}
            )
            timings.append((time.perf_counter() - started) * 1000)
            sizes.append(len(result.content))
            statuses.append(result.status_code)
    report = {
        "recorded_at": health["checked_at"],
        "scope": "Local production web build and running local index; not hosted performance or billing",
        "index": {
            "canonical_open_jobs": jobs,
            "open_observations": observations,
            "database_kind": db_kind,
            "database_allocated_bytes": size,
        },
        "operations": {
            "counts": health["counts"],
            "alerts": health["alerts"],
            "live_workers": health["workers"]["live"],
        },
        "source_failures": [
            row
            for row in health["sources"]
            if row["consecutive_failures"] or not row["initial_index_complete"]
        ],
        "repeat_refreshes": repeat,
        "search_measurement": {
            "samples": len(timings),
            "statuses": statuses,
            "median_ms": round(statistics.median(timings), 2),
            "maximum_ms": round(max(timings), 2),
            "median_response_bytes": statistics.median(sizes),
            "limit": 25,
            "view": "summary",
        },
        "cost_measurement": {
            "new_paid_services_provisioned": False,
            "new_service_charges_usd": 0,
            "hosted_operating_cost_measured": False,
            "excluded": "Existing computer, electricity and internet are not metered; hosting is paused",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                "index": report["index"],
                "operations": report["operations"],
                "search_measurement": report["search_measurement"],
            }
        )
    )


if __name__ == "__main__":
    main()

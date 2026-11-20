"""Deterministic deduplication/lifecycle walkthrough, isolated from all real data."""

import argparse
import json
import tempfile
from datetime import timedelta
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from vindex.db import Base, Job, Observation, Source, now
from vindex.ingest import ingest
from vindex.records import public_job
from vindex.schemas import Enumeration, JobInput


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="rolewisp-reviewer-") as temporary:
        engine = create_engine("sqlite:///" + str(Path(temporary) / "replay.sqlite"))
        Base.metadata.create_all(engine)
        start = now() - timedelta(days=2)
        with Session(engine) as session:
            sources = [
                Source(
                    provider="ashby",
                    slug="reviewer-a",
                    company="Reviewer Example",
                    url="https://jobs.ashbyhq.com/reviewer-a",
                ),
                Source(
                    provider="lever",
                    slug="reviewer-b",
                    company="Reviewer Example",
                    url="https://jobs.lever.co/reviewer-b",
                ),
            ]
            session.add_all(sources)
            session.flush()
            job = JobInput(
                external_id="1",
                title="Engineer",
                company="Reviewer Example",
                description="Synthetic reviewer role",
                salary={"min": 90000, "currency": "GBP", "period": "year"},
                location="London",
                source_url="https://example.org/source-a/1",
                application_url="https://example.org/apply/1?utm_source=a",
            )
            distinct = job.model_copy(
                update={"external_id": "2", "application_url": "https://example.org/apply/2"}
            )
            paris = job.model_copy(update={"external_id": "3", "location": "Paris"})
            batch = Enumeration(jobs=[job, distinct, paris], complete=True)
            ingest(session, sources[0], batch, start)
            mirror = job.model_copy(
                update={
                    "external_id": "other-id",
                    "source_url": "https://example.org/source-b/1",
                    "application_url": "https://example.org/apply/1?utm_source=b",
                    "description": "",
                    "salary": None,
                    "quality_flags": ["description_missing"],
                }
            )
            ingest(session, sources[1], Enumeration(jobs=[mirror], complete=True), start)
            session.commit()
            observations = list(session.scalars(select(Observation).order_by(Observation.id)))
            assert observations[0].job_id == observations[-1].job_id
            assert len({row.job_id for row in observations}) == 3
            canonical = session.get(Job, observations[0].job_id)
            merged = public_job(canonical, observations)
            assert len(merged["sources"]) == 2
            assert merged["description"] == job.description and merged["salary"]["min"] == 90000
            assert {s["source_url"] for s in merged["sources"]} == {
                job.source_url,
                mirror.source_url,
            }
            rejected = False
            try:
                ingest(
                    session,
                    sources[0],
                    Enumeration(jobs=[], complete=False),
                    start + timedelta(hours=1),
                )
            except ValueError:
                rejected = True
            assert rejected and all(
                row.status == "open" and row.missing_count == 0 for row in observations
            )
            changed = job.model_copy(update={"description": "Updated synthetic responsibilities"})
            ingest(
                session,
                sources[0],
                Enumeration(jobs=[changed, distinct, paris], complete=True),
                start + timedelta(hours=2),
            )
            session.commit()
            assert session.get(Job, canonical.id).data["description"] == changed.description
            report = {
                "scope": "Deterministic synthetic reviewer replay; not live coverage or an upstream duplicate claim",
                "observations": len(observations),
                "canonical_jobs": 3,
                "merged_sources": merged["sources"],
                "duplicate_tracking_variants_merged": True,
                "different_requisition_kept_separate": observations[0].job_id
                != observations[1].job_id,
                "different_location_kept_separate": observations[0].job_id
                != observations[2].job_id,
                "partial_snapshot_rejected_without_closures": rejected,
                "changed_description_visible": True,
                "richer_active_metadata_preserved": True,
                "borrowed_field_sources": merged["field_sources"],
            }
        engine.dispose()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps(report, default=str))


if __name__ == "__main__":
    main()

"""Read-only job-record contract audit. Never reads private account/profile tables."""

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select
from vindex.db import Job, Observation, Session, Source
from vindex.records import public_job, public_record, utc
from vindex.schemas import JobInput, JobOut

REQUIRED = ("title", "company", "description", "location", "source_url", "application_url")
OPTIONAL = ("salary", "employment_type", "remote_status", "published_at")


def audit(session) -> dict[str, Any]:
    captured_from = datetime.now(UTC).isoformat()

    def detached(row):
        fields = (
            "id",
            "job_id",
            "source_id",
            "first_seen",
            "last_changed",
            "last_checked",
            "status",
            "missing_count",
        )
        return SimpleNamespace(
            **{name: getattr(row, name, None) for name in fields},
            data={k: v for k, v in row.data.items() if k != "raw"},
        )

    # Capture only job tables, discard raw transport payloads, then release the
    # database transaction before expensive validation. No account copies and
    # no per-job query loop that holds up the running indexer.
    records = [
        (detached(row), provider)
        for row, provider in session.execute(
            select(Observation, Source.provider)
            .join(Source, Source.id == Observation.source_id)
            .where(Observation.status == "open")
            .execution_options(yield_per=200)
        )
    ]
    canonical = {row.job_id for row, _ in records}
    by_job = defaultdict(list)
    for row, _ in records:
        by_job[row.job_id].append(row)
    jobs = {}
    identifiers = sorted(canonical)
    for offset in range(0, len(identifiers), 500):
        selected = identifiers[offset : offset + 500]
        for row in session.scalars(select(Job).where(Job.id.in_(selected))):
            jobs[row.id] = detached(row)
        for row in session.scalars(
            select(Observation).where(
                Observation.job_id.in_(selected), Observation.status != "open"
            )
        ):
            if row.id not in {existing.id for existing in by_job[row.job_id]}:
                by_job[row.job_id].append(detached(row))
    orphan_sources = (
        session.scalar(
            select(func.count())
            .select_from(Observation)
            .outerjoin(Source, Source.id == Observation.source_id)
            .where(Source.id.is_(None))
        )
        or 0
    )
    duplicates = (
        select(Observation.source_id, Observation.external_id)
        .group_by(Observation.source_id, Observation.external_id)
        .having(func.count() > 1)
        .subquery()
    )
    duplicate_count = session.scalar(select(func.count()).select_from(duplicates)) or 0
    session.rollback()
    captured_until = datetime.now(UTC).isoformat()
    counts: Counter = Counter()
    flags: Counter = Counter()
    failures: Counter = Counter()
    segments: dict[str, Counter] = defaultdict(Counter)
    for observation, provider in records:
        counts["open_observations"] += 1
        if observation.missing_count:
            counts["open_observations_pending_closure"] += 1
        canonical.add(observation.job_id)
        segment = segments[provider]
        segment["records"] += 1
        data = observation.data
        try:
            JobInput.model_validate(data)
        except ValidationError as error:
            for issue in error.errors(
                include_input=False, include_context=False, include_url=False
            ):
                field = str(issue["loc"][0])
                failures["source_contract:" + field] += 1
                segment["invalid:" + field] += 1
        try:
            normalized = public_record(data)
        except (ValueError, TypeError, KeyError, AttributeError):
            failures["normalization_failed"] += 1
            segment["normalization_failed"] += 1
            continue
        missing = [
            field
            for field in REQUIRED
            if not isinstance(normalized.get(field), str) or not normalized[field].strip()
        ]
        for field in missing:
            counts["missing:" + field] += 1
            segment["missing:" + field] += 1
        for field in OPTIONAL:
            if data.get(field) not in (None, "", {}, []):
                counts["source_optional:" + field] += 1
                segment["source_optional:" + field] += 1
            if normalized.get(field) not in (None, "", {}, []):
                counts["normalized_optional:" + field] += 1
            elif data.get(field) not in (None, "", {}, []):
                failures["optional_value_lost:" + field] += 1
        record_flags = normalized["quality_flags"]
        flags.update(record_flags)
        if not missing and "publisher_supplied_company_label" not in record_flags:
            counts["required_fields_present_without_publisher_company_label"] += 1
        if (
            utc(observation.first_seen) > utc(observation.last_checked)
            or utc(observation.last_changed) > utc(observation.last_checked)
            or utc(observation.first_seen) > utc(observation.last_changed)
        ):
            failures["observation_timestamp_order"] += 1
    # Audit public canonical records separately: multiple observations per job are
    # provenance, not duplicate jobs. Keep this denominator separate.
    for job_id in sorted(canonical):
        job = jobs.get(job_id)
        if job is None:
            failures["missing_canonical_job"] += 1
            continue
        observations = by_job[job_id]
        try:
            payload = public_job(job, observations)
            JobOut.model_validate(payload)
            if payload["first_seen_at"] > payload["last_changed_at"]:
                failures["canonical_timestamp_order"] += 1
            if "raw" in payload:
                failures["public_raw_field"] += 1
        except (ValidationError, ValueError, TypeError, KeyError, AttributeError):
            failures["public_contract"] += 1
    counts["active_canonical_jobs"] = len(canonical)
    failures["orphan_sources"] = orphan_sources
    failures["duplicate_source_identifiers"] = duplicate_count
    failures = Counter({key: value for key, value in failures.items() if value})
    total = counts["open_observations"]
    return {
        "recorded_at": datetime.now(UTC).isoformat(),
        "capture_started_at": captured_from,
        "capture_finished_at": captured_until,
        "grain": "Open source observations; active canonical jobs audited separately",
        "read_only": True,
        "scope": "Current database snapshot, not all historical platform smoke runs",
        "url_check": "HTTPS syntax and local/private literal restrictions; not a live reachability audit",
        "counts": dict(counts),
        "missing_required_rates": {
            field: counts["missing:" + field] / total if total else None for field in REQUIRED
        },
        "contract_failures": dict(failures),
        "quality_flags": dict(flags),
        "by_connector": {name: dict(value) for name, value in sorted(segments.items())},
        "strict_required_field_pass": bool(total)
        and not failures
        and not any(counts["missing:" + field] for field in REQUIRED)
        and not flags["publisher_supplied_company_label"],
        "limitations": [
            "Blank source fields are reported, never invented or silently removed",
            "Open observations include last-known records retained while closure confirmation is pending",
            "Optional-field absence is not a required-field failure",
            "The audit does not prove upstream completeness, source freshness SLAs or every employer identity",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    with Session() as session:
        report = audit(session)
        session.rollback()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "counts": report["counts"],
                "contract_failures": report["contract_failures"],
                "strict_required_field_pass": report["strict_required_field_pass"],
            }
        )
    )
    if args.strict and not report["strict_required_field_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

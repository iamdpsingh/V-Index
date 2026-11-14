import hashlib
import json
from datetime import UTC, timedelta
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from vindex.db import Event, Job, Observation, Source, now
from vindex.schemas import Enumeration, JobInput


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def identity(job: JobInput) -> str:
    p = urlsplit(job.application_url)
    # Remove only known attribution; retain identifiers and all unknown query parameters.
    query = [
        (k, v)
        for k, v in parse_qsl(p.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in {"gh_src"}
    ]
    link = urlunsplit((p.scheme, p.netloc.lower(), p.path, urlencode(sorted(query)), ""))
    return digest(
        [
            link,
            job.company.strip().casefold(),
            job.title.strip().casefold(),
            job.location.strip().casefold(),
        ]
    )


def aware(value):
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def ingest(session: Session, source: Source, batch: Enumeration, checked=None) -> None:
    if not batch.complete:
        raise ValueError("Incomplete enumeration cannot alter index")
    checked = checked or now()
    ids = [j.external_id for j in batch.jobs]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate external identifiers")
    existing = {
        o.external_id: o
        for o in session.scalars(select(Observation).where(Observation.source_id == source.id))
    }
    for item in batch.jobs:
        data = item.model_dump(mode="json")
        fingerprint = digest(
            {k: v for k, v in data.items() if k != "raw" and not (k == "quality_flags" and not v)}
        )
        obs = existing.get(item.external_id)
        key = (
            digest([source.provider, source.slug])
            if source.provider == "employer_posting"
            else identity(item)
        )
        canonical = session.scalar(select(Job).where(Job.identity == key))
        if canonical is None:
            canonical = Job(identity=key, data=data, first_seen=checked, last_changed=checked)
            session.add(canonical)
            session.flush()
        if obs is None:
            obs = Observation(
                source_id=source.id,
                external_id=item.external_id,
                job_id=canonical.id,
                data=data,
                fingerprint=fingerprint,
                first_seen=checked,
                last_checked=checked,
                last_changed=checked,
            )
            session.add(obs)
            session.flush()
            session.add(Event(observation_id=obs.id, kind="created", occurred_at=checked))
        else:
            kind = (
                "reopened"
                if obs.status == "closed"
                else ("updated" if obs.fingerprint != fingerprint else None)
            )
            obs.job_id = canonical.id
            obs.data, obs.fingerprint = data, fingerprint
            if kind:
                obs.last_changed = checked
                session.add(Event(observation_id=obs.id, kind=kind, occurred_at=checked))
            obs.last_checked, obs.status = checked, "open"
            obs.missing_count, obs.missing_since = 0, None
        canonical.data, canonical.last_changed = data, obs.last_changed
    for external_id, obs in existing.items():
        if external_id in ids or obs.status == "closed":
            continue
        obs.last_checked = checked
        obs.missing_count += 1
        if obs.missing_since is None:
            obs.missing_since = checked
        if obs.missing_count >= 2 and checked - aware(obs.missing_since) >= timedelta(hours=24):
            obs.status, obs.last_changed = "closed", checked
            session.add(Event(observation_id=obs.id, kind="closed", occurred_at=checked))

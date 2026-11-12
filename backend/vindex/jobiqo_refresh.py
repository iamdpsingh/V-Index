"""Resume United Way detail extraction within the worker's refresh lease."""

from datetime import timedelta

import httpx
from sqlalchemy.orm import Session

from vindex.connectors.jobiqo import JobiqoConnector
from vindex.connectors.robots import RobotsPolicy
from vindex.db import JobiqoRefresh, Source, now
from vindex.ingest import aware
from vindex.schemas import Enumeration, JobInput

BATCH_SIZE = 8
SNAPSHOT_TTL = timedelta(hours=6)


async def advance_jobiqo_refresh(
    session: Session, source: Source, client: httpx.AsyncClient
) -> Enumeration | None:
    connector = JobiqoConnector(source.slug, client)
    policy = await RobotsPolicy.load(connector.http, connector.origin)
    stage = session.get(JobiqoRefresh, source.id)
    if stage is not None and now() - aware(stage.started_at) >= SNAPSHOT_TTL:
        session.delete(stage)
        session.commit()
        stage = None
    if stage is None:
        stage = JobiqoRefresh(source_id=source.id, roster=await connector.roster(policy), jobs=[])
        session.add(stage)
        session.commit()

    roster = stage.roster
    jobs = [JobInput.model_validate(record) for record in stage.jobs]
    completed = {job.external_id: job.source_url for job in jobs}
    if len(completed) != len(jobs) or any(roster.get(key) != url for key, url in completed.items()):
        raise ValueError("Invalid United Way refresh checkpoint")

    pending = [identifier for identifier in roster if identifier not in completed]
    for identifier in pending[:BATCH_SIZE]:
        job = await connector.read_job(identifier, roster[identifier], policy)
        jobs.append(job)
        stage.jobs = [*stage.jobs, job.model_dump(mode="json")]
        session.commit()
    if len(jobs) != len(roster):
        return None

    final_roster = await connector.roster(policy)
    if final_roster != roster or now() - aware(stage.started_at) >= SNAPSHOT_TTL:
        session.delete(stage)
        session.commit()
        raise ValueError("United Way roster changed or expired during refresh")

    # The worker commits deletion together with ingestion.
    session.delete(stage)
    return Enumeration(jobs=jobs, complete=True)

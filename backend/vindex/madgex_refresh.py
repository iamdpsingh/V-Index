"""Stage a bounded portion of a large Madgex crawl under the source refresh lease."""

from datetime import timedelta

import httpx
from sqlalchemy.orm import Session

from vindex.connectors.robots import RobotsPolicy
from vindex.connectors.wileymadgex import WileyMadgexConnector
from vindex.db import MadgexRefresh, Source, now
from vindex.ingest import aware
from vindex.schemas import Enumeration, JobInput

BATCH_SIZE = 40
CHECKPOINT_SIZE = 10
SNAPSHOT_TTL = timedelta(hours=6)


async def advance_madgex_refresh(
    session: Session, source: Source, client: httpx.AsyncClient
) -> Enumeration | None:
    connector = WileyMadgexConnector(source.slug, client)
    policy = await RobotsPolicy.load(connector.http, connector.origin)
    stage = session.get(MadgexRefresh, source.id)
    if stage is not None and now() - aware(stage.started_at) >= SNAPSHOT_TTL:
        session.delete(stage)
        session.commit()
        stage = None
    if stage is None:
        rows = await connector.roster(policy)
        stage = MadgexRefresh(
            source_id=source.id,
            roster={identifier: list(row) for identifier, row in rows.items()},
            jobs=[],
        )
        session.add(stage)
        session.commit()

    roster = {identifier: (row[0], row[1]) for identifier, row in stage.roster.items()}
    jobs = [JobInput.model_validate(record) for record in stage.jobs]
    complete_ids = {job.external_id for job in jobs}
    if len(complete_ids) != len(jobs) or not complete_ids <= roster.keys():
        raise ValueError("Invalid Madgex refresh checkpoint")

    pending = [identifier for identifier in roster if identifier not in complete_ids]
    checkpoint = []
    for identifier in pending[:BATCH_SIZE]:
        url, title = roster[identifier]
        job = connector.parse_detail(identifier, url, title, await connector.read(url, policy))
        jobs.append(job)
        checkpoint.append(job.model_dump(mode="json"))
        if len(checkpoint) == CHECKPOINT_SIZE:
            stage.jobs = stage.jobs + checkpoint
            session.commit()
            checkpoint.clear()
    if checkpoint:
        stage.jobs = stage.jobs + checkpoint
        session.commit()

    if len(jobs) != len(roster):
        return None
    if now() - aware(stage.started_at) >= SNAPSHOT_TTL or await connector.roster(policy) != roster:
        session.delete(stage)
        session.commit()
        raise ValueError("Madgex roster changed or expired during the refresh")
    # Reconciliation and stage deletion are committed together by the worker.
    session.delete(stage)
    return Enumeration(jobs=jobs, complete=True)

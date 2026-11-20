"""Resume Talenetic boards without reconciling partial snapshots."""

import asyncio
from datetime import timedelta
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from vindex.connectors.http import UpstreamStatusError
from vindex.connectors.robots import RobotsPolicy
from vindex.connectors.talenetic import TaleneticConnector
from vindex.db import Source, TaleneticDetail, TaleneticRefresh, now
from vindex.ingest import aware
from vindex.schemas import Enumeration, JobInput

BATCH_SIZE = 50
SNAPSHOT_TTL = timedelta(hours=6)


async def advance_talenetic_refresh(
    session: Session, source: Source, client: httpx.AsyncClient
) -> Enumeration | None:
    connector = TaleneticConnector(source.slug, client)
    policy = await RobotsPolicy.load(connector.http, connector.origin)
    stage = session.get(TaleneticRefresh, source.id)
    if stage is not None and now() - aware(stage.started_at) >= SNAPSHOT_TTL:
        session.delete(stage)
        session.commit()
        stage = None
    if stage is None:
        stage = TaleneticRefresh(source_id=source.id, roster=await connector.roster(policy))
        session.add(stage)
        session.commit()
    roster = stage.roster
    for identifier, url in roster.items():
        if connector.identifier(url) != identifier:
            raise ValueError("Invalid Talenetic checkpoint identity")
    completed = set(
        session.scalars(
            select(TaleneticDetail.external_id).where(TaleneticDetail.source_id == source.id)
        )
    )
    if not completed <= roster.keys():
        raise ValueError("Invalid Talenetic checkpoint detail set")
    pending = [key for key in roster if key not in completed]
    semaphore = asyncio.Semaphore(4)

    async def detail(identifier: str) -> tuple[str, dict[str, Any]]:
        url = roster[identifier]
        async with semaphore:
            body = await connector.read(url, policy)
        try:
            parsed = connector.parse((url, body))
        except ValueError as error:
            # Identify a failing public posting without logging its response or apply query.
            raise ValueError(
                f"Talenetic detail {identifier}: {str(error).splitlines()[0]}"
            ) from error
        data = (
            parsed[0].model_dump(mode="json")
            if parsed
            else {"expired": True, "external_id": identifier, "source_url": url}
        )
        return identifier, data

    tasks = [asyncio.create_task(detail(key)) for key in pending[:BATCH_SIZE]]
    try:
        for task in asyncio.as_completed(tasks):
            identifier, data = await task
            session.add(TaleneticDetail(source_id=source.id, external_id=identifier, data=data))
            session.commit()
            completed.add(identifier)
    except UpstreamStatusError as error:
        if error.status_code == 404 and await connector.roster(policy) != roster:
            session.delete(stage)
            session.commit()
        raise
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    if len(completed) != len(roster):
        return None
    if now() - aware(stage.started_at) >= SNAPSHOT_TTL or await connector.roster(policy) != roster:
        session.delete(stage)
        session.commit()
        raise ValueError("Talenetic roster changed or expired during extraction")
    records: list[dict[str, Any]] = list(
        session.scalars(select(TaleneticDetail.data).where(TaleneticDetail.source_id == source.id))
    )
    if any(roster[record["external_id"]] != record["source_url"] for record in records):
        raise ValueError("Talenetic checkpoint posting URL mismatch")
    jobs = [JobInput.model_validate(record) for record in records if not record.get("expired")]
    if any(roster[job.external_id] != job.source_url for job in jobs):
        raise ValueError("Talenetic checkpoint posting URL mismatch")
    session.delete(stage)
    return Enumeration(jobs=jobs, complete=True)

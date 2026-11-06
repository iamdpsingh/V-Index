"""Opt-in Redis + SQL transaction tests. Uses no public network or fixture job claims."""

import asyncio
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock

import pytest
from sqlalchemy import func, select
from test_lifecycle import posting
from vindex import worker
from vindex.db import Job, Observation, Run, Source
from vindex.ingest import ingest
from vindex.schemas import Enumeration

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_REDIS_URL"), reason="Set TEST_REDIS_URL for real lease tests"
)


@pytest.fixture
def services(database, monkeypatch):
    monkeypatch.setattr(worker, "Session", database)
    monkeypatch.setenv("REDIS_URL", os.environ["TEST_REDIS_URL"])


def test_real_redis_prevents_replay_from_stale_due_selection(
    database, source, services, monkeypatch
):
    started = threading.Event()
    calls = []

    async def discovery():
        calls.append(1)
        started.set()
        await asyncio.sleep(0.3)
        return Enumeration(jobs=[posting()], complete=True)

    monkeypatch.setattr(worker, "create_connector", lambda *args: Mock(discover=discovery))
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(lambda: asyncio.run(worker.refresh(source.id, only_if_due=True)))
        assert started.wait(5), "First worker did not reach enumeration"
        second = pool.submit(lambda: asyncio.run(worker.refresh(source.id, only_if_due=True)))
        assert first.result(timeout=10) is not None
        assert second.result(timeout=10) is None
    assert len(calls) == 1
    with database() as session:
        assert session.scalar(select(func.count()).select_from(Run)) == 1
        assert session.scalar(select(Run.status)) == "success"


def test_reconciliation_error_rolls_back_index_and_records_failure(
    database, source, services, monkeypatch
):
    with database() as session:
        ingest(session, source, Enumeration(jobs=[posting()], complete=True))
        session.commit()

    async def discovery():
        return Enumeration(
            jobs=[
                posting(description="Must roll back"),
                posting(external_id="new", application_url="https://example.com/new"),
            ],
            complete=True,
        )

    def fail_after_writes(session, source, batch):
        ingest(session, source, batch)
        session.flush()
        raise RuntimeError("Injected reconciliation failure after writes")

    monkeypatch.setattr(worker, "create_connector", lambda *args: Mock(discover=discovery))
    monkeypatch.setattr(worker, "ingest", fail_after_writes)
    run_id = asyncio.run(worker.refresh(source.id))
    with database() as session:
        assert session.scalar(select(func.count()).select_from(Job)) == 1
        observation = session.scalar(select(Observation))
        assert observation.data["description"] == "Build useful things"
        assert observation.status == "open" and observation.missing_count == 0
        assert session.get(Run, run_id).status == "failed"
        assert session.get(Source, source.id).failures == 1

import asyncio
from contextlib import nullcontext
from unittest.mock import Mock

import pytest
from sqlalchemy import select
from test_lifecycle import posting
from vindex import worker
from vindex.connectors.http import SnapshotChangedError
from vindex.db import Observation, Run, Source
from vindex.ingest import aware, ingest
from vindex.schemas import Enumeration

from scripts.start_production_worker import requeue_recovered_lpjc


@pytest.mark.parametrize("churn,minutes", [(True, 2), (False, 30)])
def test_snapshot_churn_retries_sooner_without_publishing_or_closing(
    database, source, monkeypatch, churn, minutes
):
    with database() as session:
        ingest(session, source, Enumeration(jobs=[posting()], complete=True))
        session.commit()
    redis = Mock()
    redis.lock.return_value = nullcontext()
    monkeypatch.setattr(worker, "Session", database)
    monkeypatch.setattr(worker.Redis, "from_url", lambda *args, **kwargs: redis)

    async def failed():
        if churn:
            raise SnapshotChangedError("Job Board Fire search and sitemap do not agree")
        raise ValueError("Career page robots policy disallows this request")

    monkeypatch.setattr(worker, "create_connector", lambda *args: Mock(discover=failed))
    run_id = asyncio.run(worker.refresh(source.id))
    with database() as session:
        run = session.get(Run, run_id)
        stored = session.get(Source, source.id)
        observation = session.scalar(select(Observation))
        assert run.status == "failed" and stored.failures == 1
        assert (
            abs((aware(stored.next_check) - aware(run.finished_at)).total_seconds() - minutes * 60)
            < 1
        )
        assert observation.status == "open" and observation.missing_count == 0


@pytest.mark.parametrize(
    "error,expected",
    [
        ("ValueError: Job Board Fire search and sitemap do not agree", True),
        ("HTTPStatusError: 429 Too Many Requests", False),
        ("ValueError: Career page robots policy disallows this request", False),
    ],
)
def test_lpjc_recovery_never_requeues_policy_or_rate_limit_failures(
    database, source, error, expected
):
    with database() as session:
        stored = session.get(Source, source.id)
        stored.provider = "jobboardfire"
        stored.slug = "lpjc.jobboardfire.com"
        session.add(Run(source_id=source.id, status="failed", error=error))
        session.commit()
        assert requeue_recovered_lpjc(session) == ([source.id] if expected else [])

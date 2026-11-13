import asyncio

import httpx
import pytest
from vindex import jobiqo_refresh
from vindex.connectors.jobiqo import JobiqoConnector
from vindex.db import JobiqoRefresh
from vindex.schemas import JobInput

ROSTER = {str(i): f"https://careers.unitedway.org/job/engineer-{i}" for i in (1, 2)}


@pytest.mark.parametrize("roster_changes", [False, True])
def test_jobiqo_resumes_and_reconfirms_before_publishing(
    database, source, monkeypatch, roster_changes
):
    rosters = [ROSTER, {"1": ROSTER["1"]} if roster_changes else ROSTER]
    reads = []

    async def roster(self, policy):
        return rosters.pop(0)

    async def read_job(self, identifier, url, policy):
        reads.append(identifier)
        return JobInput(
            external_id=identifier,
            title="Engineer",
            company="Employer",
            description="Job description",
            source_url=url,
            application_url=url,
        )

    async def load(*args):
        return object()

    monkeypatch.setattr(JobiqoConnector, "roster", roster)
    monkeypatch.setattr(JobiqoConnector, "read_job", read_job)
    monkeypatch.setattr(jobiqo_refresh.RobotsPolicy, "load", load)
    monkeypatch.setattr(jobiqo_refresh, "BATCH_SIZE", 1)

    with database() as session:
        item = session.get(type(source), source.id)
        item.slug = "careers.unitedway.org"
        session.commit()

    async def refresh():
        async with httpx.AsyncClient() as client:
            with database() as session:
                item = session.get(type(source), source.id)
                result = await jobiqo_refresh.advance_jobiqo_refresh(session, item, client)
                session.commit()
                return result

    assert asyncio.run(refresh()) is None
    with database() as session:
        assert len(session.get(JobiqoRefresh, source.id).jobs) == 1

    if roster_changes:
        with pytest.raises(ValueError, match="roster changed"):
            asyncio.run(refresh())
    else:
        result = asyncio.run(refresh())
        assert result.complete
        assert [job.external_id for job in result.jobs] == ["1", "2"]

    with database() as session:
        assert session.get(JobiqoRefresh, source.id) is None
    assert reads == ["1", "2"]


@pytest.mark.parametrize("removed", [False, True])
def test_jobiqo_detail_404_requires_confirmed_roster_change(database, source, monkeypatch, removed):
    from vindex.connectors.http import UpstreamStatusError

    rosters = [ROSTER, {"2": ROSTER["2"]} if removed else ROSTER]

    async def roster(self, policy):
        return rosters.pop(0)

    async def read_job(self, identifier, url, policy):
        raise UpstreamStatusError(404)

    async def load(*args):
        return object()

    monkeypatch.setattr(JobiqoConnector, "roster", roster)
    monkeypatch.setattr(JobiqoConnector, "read_job", read_job)
    monkeypatch.setattr(jobiqo_refresh.RobotsPolicy, "load", load)

    async def refresh():
        async with httpx.AsyncClient() as client:
            with database() as session:
                item = session.get(type(source), source.id)
                item.slug = "careers.unitedway.org"
                await jobiqo_refresh.advance_jobiqo_refresh(session, item, client)

    with pytest.raises(ValueError, match="roster changed" if removed else "HTTP 404"):
        asyncio.run(refresh())

    with database() as session:
        stage = session.get(JobiqoRefresh, source.id)
        if removed:
            assert stage is None
        else:
            assert stage is not None
            assert stage.roster == ROSTER
            assert stage.jobs == []

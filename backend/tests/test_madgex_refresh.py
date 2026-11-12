import asyncio

import httpx
from vindex import madgex_refresh
from vindex.connectors.wileymadgex import WileyMadgexConnector
from vindex.db import MadgexRefresh
from vindex.schemas import JobInput

ROSTER = {
    str(i): (f"https://jobs.sciencecareers.org/job/{i}/engineer/", "Engineer") for i in (1, 2, 3)
}


def test_madgex_refresh_resumes_and_requires_roster_reconfirmation(database, source, monkeypatch):
    rosters = [ROSTER, ROSTER]
    reads = []

    async def roster(self, policy):
        return rosters.pop(0)

    async def read(self, url, policy):
        reads.append(url)
        return b"detail"

    def parse(self, identifier, url, title, body):
        return JobInput(
            external_id=identifier,
            title=title,
            company="Example",
            description="Example job",
            source_url=url,
            application_url=url,
        )

    async def policy(*args):
        return object()

    monkeypatch.setattr(WileyMadgexConnector, "roster", roster)
    monkeypatch.setattr(WileyMadgexConnector, "read", read)
    monkeypatch.setattr(WileyMadgexConnector, "parse_detail", parse)
    monkeypatch.setattr(madgex_refresh.RobotsPolicy, "load", policy)
    monkeypatch.setattr(madgex_refresh, "BATCH_SIZE", 2)
    monkeypatch.setattr(madgex_refresh, "CHECKPOINT_SIZE", 1)

    async def refresh():
        async with httpx.AsyncClient() as client:
            with database() as session:
                item = session.get(type(source), source.id)
                return await madgex_refresh.advance_madgex_refresh(session, item, client)

    with database() as session:
        item = session.get(type(source), source.id)
        item.slug = "jobs.sciencecareers.org"
        session.commit()

    assert asyncio.run(refresh()) is None
    with database() as session:
        assert len(session.get(MadgexRefresh, source.id).jobs) == 2
    result = asyncio.run(refresh())
    assert result.complete
    assert [job.external_id for job in result.jobs] == ["1", "2", "3"]
    assert reads == [url for url, _ in ROSTER.values()]
    assert rosters == []

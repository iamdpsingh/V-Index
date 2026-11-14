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


def test_madgex_accepts_canonical_slug_alias_for_same_posting():
    import pytest

    listing_url = "https://jobs.sciencecareers.org/job/1/biologist-%ce%b2/"
    canonical_url = "https://jobs.sciencecareers.org/job/1/biologist/"
    body = f"""
      <html><head>
      <link rel="canonical" href="{canonical_url}">
      <script type="application/ld+json">{{
        "@type": "JobPosting", "title": "Biologist", "description": "Research",
        "hiringOrganization": {{"name": "Example"}}
      }}</script>
      </head><body>
      <h1 class="mds-font-s6">Biologist</h1>
      <a href="/apply/1/biologist/">Apply</a>
      </body></html>
    """
    async def check():
        async with httpx.AsyncClient() as as_client:
            connector = WileyMadgexConnector("jobs.sciencecareers.org", as_client)
            job = connector.parse_detail("1", listing_url, "Biologist", body.encode())
            assert job.source_url == canonical_url
            assert job.application_url == "https://jobs.sciencecareers.org/apply/1/biologist/"
            with pytest.raises(ValueError, match="visible posting mismatch"):
                connector.parse_detail(
                    "1", listing_url, "Biologist", body.replace("/job/1/", "/job/2/").encode()
                )

    asyncio.run(check())

import asyncio
import json

import httpx
import pytest
from sqlalchemy import func, select
from vindex import talenetic_refresh
from vindex.connectors.registry import create_connector, detect
from vindex.connectors.talenetic import TaleneticConnector
from vindex.db import TaleneticDetail, TaleneticRefresh
from vindex.schemas import JobInput

HOST = "jobs.medicalupdateonline.com"
URL = f"https://{HOST}/job-detail/1/engineer/"


def detail() -> bytes:
    row = {
        "@type": "jobPosting",
        "title": "Engineer",
        "description": "&lt;p&gt;Build things.&lt;/p&gt;",
        "hiringOrganization": {"name": "Example"},
        "jobLocation": {"address": {"addressLocality": "London"}},
        "datePosted": "2026-11-19",
    }
    return f"""<html><script type="application/ld+json">{json.dumps(row)}</script>
    <h2 itemprop="title">Engineer</h2><div class="job_description_hold">Build things.</div>
    <input id="externaljobtitle" value="Engineer">
    <input id="externalcompanyname" value="Example">
    <input id="externalurl" value="https://example.org/apply/1">
    <input id="directurl" value=""><a id="shortlist1">Apply now</a>
    <footer>Talenetic Job Board Software</footer></html>""".encode()


def test_talenetic_identity_fields_and_safe_detection():
    client = httpx.AsyncClient()
    connector = create_connector("talenetic", HOST, "Board", client)
    job = connector.parse((URL, detail()))[0]
    assert job.title == "Engineer" and job.description == "Build things."
    assert job.application_url == "https://example.org/apply/1"
    assert job.location == "London"
    assert detect(f"https://{HOST}/") == ("talenetic", HOST)
    for bad in [f"https://{HOST}/?filter=1", "https://localhost/", f"http://{HOST}/"]:
        with pytest.raises(ValueError):
            detect(bad)
    for old, new in [
        (b'id="shortlist1"', b'id="shortlist2"'),
        (b">Engineer</h2>", b">Other role</h2>"),
        (b"https://example.org/apply/1", b"javascript:alert(1)"),
        (b"Build things.</div>", b"Incomplete.</div>"),
    ]:
        with pytest.raises(ValueError):
            connector.parse((URL, detail().replace(old, new)))


def test_talenetic_sitemap_rejects_duplicates_and_entities():
    connector = TaleneticConnector(HOST, httpx.AsyncClient())
    xml = f"""<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url><loc>{URL}</loc></url></urlset>""".encode()
    assert connector.xml_urls(xml, index=False) == [URL]
    for invalid in [
        xml.replace(b"</urlset>", f"<url><loc>{URL}</loc></url></urlset>".encode()),
        xml.replace(HOST.encode(), b"localhost"),
        xml[:-5],
        b'<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><urlset>&e;</urlset>',
    ]:
        with pytest.raises(ValueError):
            connector.xml_urls(invalid, index=False)


def test_talenetic_native_employment_preserved_when_structured_field_is_absent():
    connector = TaleneticConnector(HOST, httpx.AsyncClient())
    native = b'<dd itemprop="employmentType"><a href="/search/permanent">Permanent</a></dd>'
    body = detail().replace(b"</html>", native + b"</html>")
    job = connector.parse((URL, body))[0]
    assert job.employment_type == "Permanent"
    assert 'itemprop="employmentType"' in job.raw["native_employment_html"]
    assert "employmentType" not in job.raw["job_posting"]
    with pytest.raises(ValueError, match="Ambiguous"):
        connector.parse((URL, body.replace(b"</html>", native + b"</html>")))


def test_talenetic_expired_pages_require_explicit_identity():
    connector = TaleneticConnector(HOST, httpx.AsyncClient())
    body = b"""<html><h1 class="expired-title">This job has <span>expired</span></h1>
    <h2 class="job-title">Engineer</h2><input id="externalvacncyid" value="1">
    <script type="application/ld+json">{"@type":"jobPosting","title":"Engineer"}</script>
    <footer>Talenetic Job Board Software</footer></html>"""
    assert connector.parse((URL, body)) == []
    with pytest.raises(ValueError, match="expired posting"):
        connector.parse((URL, body.replace(b'value="1"', b'value="2"')))


@pytest.mark.parametrize("change_roster", [False, True])
def test_talenetic_resume_and_no_partial_reconciliation(
    database, source, monkeypatch, change_roster
):
    roster = {str(i): URL.replace("/1/", f"/{i}/") for i in (1, 2, 3)}
    calls = []
    fail = True
    roster_calls = 0

    async def get_roster(self, policy):
        nonlocal roster_calls
        roster_calls += 1
        return {} if change_roster and roster_calls > 1 else roster

    async def policy(*args):
        return object()

    async def read(self, url, policy):
        nonlocal fail
        calls.append(url)
        if url == roster["2"] and fail:
            fail = False
            raise TimeoutError("Temporary test failure")
        return b"detail"

    def parse(self, payload):
        url, _ = payload
        return [
            JobInput(
                external_id=self.identifier(url),
                title="Engineer",
                company="Example",
                description="Build things.",
                source_url=url,
                application_url=url,
            )
        ]

    monkeypatch.setattr(TaleneticConnector, "roster", get_roster)
    monkeypatch.setattr(TaleneticConnector, "read", read)
    monkeypatch.setattr(TaleneticConnector, "parse", parse)
    monkeypatch.setattr(talenetic_refresh.RobotsPolicy, "load", policy)
    monkeypatch.setattr(talenetic_refresh, "BATCH_SIZE", 2)
    with database() as session:
        item = session.get(type(source), source.id)
        item.provider, item.slug = "talenetic", HOST
        session.commit()

    async def advance():
        async with httpx.AsyncClient() as client:
            with database() as session:
                item = session.get(type(source), source.id)
                result = await talenetic_refresh.advance_talenetic_refresh(session, item, client)
                session.commit()
                return result

    with pytest.raises(TimeoutError):
        asyncio.run(advance())
    with database() as session:
        assert session.scalar(select(func.count()).select_from(TaleneticDetail)) == 1
    if change_roster:
        with pytest.raises(ValueError, match="roster changed"):
            asyncio.run(advance())
    else:
        result = asyncio.run(advance())
        assert result.complete and len(result.jobs) == 3
        assert calls.count(roster["1"]) == 1
    with database() as session:
        assert session.get(TaleneticRefresh, source.id) is None
        assert session.scalar(select(func.count()).select_from(TaleneticDetail)) == 0

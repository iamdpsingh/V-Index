"""Tests for Nodex public connector."""

import asyncio
import json

import httpx
import pytest
from vindex.connectors.nodex import HOSTS, NodexConnector
from vindex.connectors.registry import create_connector, detect
from vindex.schemas import Enumeration, JobInput

SAMPLE_ROSTER_HTML = b"""<!DOCTYPE html>
<html>
<head><title>Job Search</title></head>
<body>
<h1>2 jobs found</h1>
<div class="job-list">
  <a href="/job/group-quality-manager-south-darenth-kent/846">Group Quality Manager</a>
  <a href="/job/senior-product-compliance-engineer-south-darenth-kent/844">Senior Product Compliance Engineer</a>
</div>
</body>
</html>
"""

SAMPLE_DETAIL_SCHEMA = {
    "@context": "http://schema.org",
    "@type": "JobPosting",
    "title": "Group Quality Manager",
    "identifier": {"@type": "PropertyValue", "value": 1393},
    "url": "https://www.emotivtech.co.uk/job/group-quality-manager-south-darenth-kent/846",
    "datePosted": "2026-10-14T16:55:50+01:00",
    "validThrough": "2027-01-17T06:11:28+00:00",
    "employmentType": "Part time",
    "description": "Lead the compliance and management of quality systems.",
    "hiringOrganization": {
        "@type": "http://schema.org/Organization",
        "name": "Emotiv Recruitment",
    },
    "jobLocation": [
        {
            "@type": "Place",
            "address": {
                "@type": "PostalAddress",
                "addressLocality": "South Darenth, Kent",
                "addressRegion": "Kent",
            },
        }
    ],
}

SAMPLE_DETAIL_HTML = f"""<!DOCTYPE html>
<html>
<head><title>Group Quality Manager</title></head>
<body>
<h1>Group Quality Manager</h1>
<script type="application/ld+json">{json.dumps(SAMPLE_DETAIL_SCHEMA)}</script>
</body>
</html>
""".encode()


def test_nodex_rejects_unreviewed_origin():
    client = httpx.AsyncClient()
    with pytest.raises(ValueError, match="Unreviewed Nodex origin"):
        NodexConnector("unreviewed.example.com", client)


@pytest.mark.parametrize("host", sorted(HOSTS))
def test_nodex_detection(host):
    for path in ("", "/", "/search", "/search/"):
        assert detect(f"https://{host}{path}") == ("nodex", host)
    with pytest.raises(ValueError, match="Expected an unfiltered reviewed"):
        detect(f"https://{host}/search?q=engineer")
    with pytest.raises(ValueError, match="Expected an unfiltered reviewed"):
        detect(f"https://{host}/unrelated-path")


def test_nodex_create_connector():
    client = httpx.AsyncClient()
    connector = create_connector("nodex", "www.emotivtech.co.uk", "Emotiv", client)
    assert isinstance(connector, NodexConnector)
    assert connector.host == "www.emotivtech.co.uk"


def test_nodex_roster_parsing():
    client = httpx.AsyncClient()
    connector = NodexConnector("www.emotivtech.co.uk", client)

    roster = connector.roster(SAMPLE_ROSTER_HTML)
    assert len(roster) == 2
    assert (
        roster["846"]
        == "https://www.emotivtech.co.uk/job/group-quality-manager-south-darenth-kent/846"
    )
    assert (
        roster["844"]
        == "https://www.emotivtech.co.uk/job/senior-product-compliance-engineer-south-darenth-kent/844"
    )

    with pytest.raises(ValueError, match="No links found on Nodex search page"):
        connector.roster(b"<html><body><p>No jobs</p></body></html>")

    with pytest.raises(ValueError, match="No matching job links found on Nodex search page"):
        connector.roster(b'<html><body><a href="/unrelated">Link</a></body></html>')


def test_nodex_detail_parsing():
    client = httpx.AsyncClient()
    connector = NodexConnector("www.emotivtech.co.uk", client)

    job = connector.parse_detail(
        "846",
        "https://www.emotivtech.co.uk/job/group-quality-manager-south-darenth-kent/846",
        SAMPLE_DETAIL_HTML,
    )
    assert isinstance(job, JobInput)
    assert job.external_id == "846"
    assert job.title == "Group Quality Manager"
    assert job.company == "Emotiv Recruitment"
    assert job.description == "Lead the compliance and management of quality systems."
    assert job.location == "South Darenth, Kent, Kent"
    assert job.employment_type == "Part time"
    assert (
        job.application_url
        == "https://www.emotivtech.co.uk/job/group-quality-manager-south-darenth-kent/846"
    )
    assert job.quality_flags == []
    assert job.published_at is not None

    missing_schema = b"<html><body>No schema</body></html>"
    with pytest.raises(ValueError, match="Missing JobPosting schema"):
        connector.parse_detail("846", "https://www.emotivtech.co.uk/job/test/846", missing_schema)


def test_nodex_discover_success():
    host = "www.emotivtech.co.uk"
    search_url = f"https://{host}/search"
    detail_url = f"https://{host}/job/group-quality-manager-south-darenth-kent/846"
    single_job_roster_html = b"""<!DOCTYPE html>
    <html><body>
    <h1>1 job found</h1>
    <a href="/job/group-quality-manager-south-darenth-kent/846">Group Quality Manager</a>
    </body></html>"""

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url == f"https://{host}/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        if url == search_url:
            return httpx.Response(200, content=single_job_roster_html)
        if url == detail_url:
            return httpx.Response(200, content=SAMPLE_DETAIL_HTML)
        raise RuntimeError(f"Unexpected URL: {url}")

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            connector = NodexConnector(host, client)
            enumeration = await connector.discover()
            assert isinstance(enumeration, Enumeration)
            assert enumeration.complete is True
            assert len(enumeration.jobs) == 1
            assert enumeration.jobs[0].title == "Group Quality Manager"

    asyncio.run(run())


def test_nodex_discover_drift_failure():
    host = "www.emotivtech.co.uk"
    search_url = f"https://{host}/search"
    detail_url = f"https://{host}/job/group-quality-manager-south-darenth-kent/846"
    call_count = 0

    html1 = b"""<!DOCTYPE html><html><body>
    <h1>1 job found</h1>
    <a href="/job/group-quality-manager-south-darenth-kent/846">Group Quality Manager</a>
    </body></html>"""

    html2 = b"""<!DOCTYPE html><html><body>
    <h1>1 job found</h1>
    <a href="/job/senior-engineer/844">Senior Engineer</a>
    </body></html>"""

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        url = str(request.url)
        if url == f"https://{host}/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        if url == search_url:
            return httpx.Response(200, content=html1 if call_count <= 2 else html2)
        if url == detail_url:
            return httpx.Response(200, content=SAMPLE_DETAIL_HTML)
        raise RuntimeError(f"Unexpected URL: {url}")

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            connector = NodexConnector(host, client)
            with pytest.raises(ValueError, match="roster changed during enumeration"):
                await connector.discover()

    asyncio.run(run())


def test_nodex_rejects_first_page_without_the_advertised_next_page(monkeypatch):
    async def no_delay(_):
        pass

    monkeypatch.setattr("vindex.connectors.nodex.asyncio.sleep", no_delay)
    host = "www.emotivtech.co.uk"
    links = "".join(f'<a href="/job/role-{n}/{n}">Role</a>' for n in range(1, 11))
    body = f'<html><h1>11 jobs found</h1><p class="hz-rs-pageof">Page 1 of 2</p>{links}</html>'

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        assert request.url.path == "/search"
        return httpx.Response(200, text=body)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(ValueError, match="Missing or ambiguous Nodex next page"):
                await NodexConnector(host, client).discover()

    asyncio.run(run())

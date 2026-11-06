"""Controlled safety tests, not live coverage evidence."""

import asyncio
import copy
import json
from html import escape

import httpx
import pytest
from vindex.connectors.registry import create_connector, detect

UUID = "d7e33392-4056-46ba-9166-97472ed0a75c"
TT = "https://example.teamtailor.com"
BR = "https://example.breezy.hr"
JOB = f"{TT}/jobs/123-engineer"
BJOB = f"{BR}/p/123456abcdef-engineer"


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.teamtailor.asyncio.sleep", no_wait)


def feed():
    return {
        "version": "https://jsonfeed.org/version/1.1",
        "home_page_url": f"{TT}/jobs",
        "feed_url": f"{TT}/jobs.json",
        "items": [
            {
                "id": UUID,
                "title": "Engineer",
                "url": JOB,
                "date_published": "2026-11-01T10:00:00Z",
                "content_html": "<p>Build systems</p>",
                "_jobposting": {
                    "@type": "JobPosting",
                    "title": "Engineer",
                    "employmentType": ["FULL_TIME"],
                    "hiringOrganization": {"name": "Example"},
                    "baseSalary": {"currency": "GBP", "value": {"minValue": 50000}},
                },
            }
        ],
    }


def rss(identifier=UUID, link=JOB):
    return f"""<rss xmlns:tt="https://teamtailor.com/locations"><channel>
    <link>{TT}/jobs</link><item><guid>{identifier}</guid><link>{link}</link>
    <remoteStatus>hybrid</remoteStatus><tt:locations><tt:location><tt:name>London</tt:name>
    <tt:city>London</tt:city><tt:country>UK</tt:country></tt:location></tt:locations>
    </item></channel></rss>"""


def breezy_row():
    return {
        "id": "123456abcdef",
        "friendly_id": "123456abcdef-engineer",
        "name": "Engineer",
        "url": BJOB,
        "published_date": "2026-11-01T10:00:00Z",
        "type": {"name": "Full-Time"},
        "salary": "£50,000 – £60,000 / year",
        "company": {"name": "Example"},
        "locations": [{"name": "London", "remote_details": {"label": "Hybrid"}}],
    }


def detail(url=BJOB, application=True):
    schema = {
        "@type": "JobPosting",
        "url": url + "?source=GoogleJobs",
        "description": "Build systems",
    }
    return (
        '<script type="application/ld+json">' + json.dumps(schema) + "</script>"
        '<div class="description">Build <b>systems</b></div>'
        + (f'<a href="{escape(BJOB)}/apply">Apply</a>' if application else "")
    )


def run(provider, handler):
    async def discover():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await create_connector(provider, "example", "Example", client).discover()

    return asyncio.run(discover())


def tt_handler(payload=None, rss_body=None, confirm=None, robots="User-agent: *\nAllow: /"):
    calls = 0

    def handle(request):
        nonlocal calls
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=robots)
        if request.url.path == "/jobs.rss":
            return httpx.Response(200, text=rss_body if rss_body is not None else rss())
        assert request.url.path == "/jobs.json"
        calls += 1
        return httpx.Response(
            200,
            json=(
                confirm
                if calls > 1 and confirm is not None
                else payload
                if payload is not None
                else feed()
            ),
        )

    return handle


def test_teamtailor_preserves_source_metadata():
    batch = run("teamtailor", tt_handler())
    job = batch.jobs[0]
    assert batch.complete and job.description == "Build systems"
    assert job.remote_status == "hybrid" and job.location == "London, UK"
    assert job.employment_type == "FULL_TIME" and job.salary["currency"] == "GBP"
    assert job.published_at.year == 2026 and job.application_url == JOB
    assert "rss_item" in job.raw


@pytest.mark.parametrize(
    "mutation",
    [
        lambda p: p.update(next_url=TT + "/jobs.json?page=2"),
        lambda p: p.update(items=p["items"] * 100),
        lambda p: p["items"].append(copy.deepcopy(p["items"][0])),
        lambda p: p.update(home_page_url="https://evil.com/jobs"),
        lambda p: p["items"][0].update(url="https://evil.com/jobs/123-engineer"),
        lambda p: p["items"][0]["_jobposting"].update(title="Different job"),
        lambda p: p["items"][0].update(id="not-a-uuid"),
        lambda p: p.update(items={}),
    ],
)
def test_teamtailor_incomplete_or_malformed_rejected(mutation):
    payload = feed()
    mutation(payload)
    with pytest.raises((ValueError, KeyError, TypeError)):
        run("teamtailor", tt_handler(payload))


def test_teamtailor_join_and_confirmation_fail_closed():
    for handler in (
        tt_handler(rss_body=rss(identifier="different")),
        tt_handler(rss_body=rss(link="https://evil.com")),
        tt_handler(confirm={**feed(), "items": []}),
    ):
        with pytest.raises(ValueError):
            run("teamtailor", handler)


def test_teamtailor_robots_denial_stops_before_feed():
    with pytest.raises(ValueError, match="robots"):
        run("teamtailor", tt_handler(robots="User-agent: *\nDisallow: /jobs.json"))


def br_handler(rows=None, body=None, board=None, confirmation=None, status=200):
    calls = 0

    def handle(request):
        nonlocal calls
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        if request.url.path == "/json":
            calls += 1
            result = confirmation if calls > 1 and confirmation is not None else rows
            return httpx.Response(200, json=result if result is not None else [breezy_row()])
        if request.url.path == "/":
            return httpx.Response(
                200, text=board if board is not None else f'<a href="{BJOB}">Job</a>'
            )
        assert str(request.url) == BJOB
        return httpx.Response(status, text=body if body is not None else detail())

    return handle


def test_breezy_preserves_description_apply_and_salary():
    batch = run("breezy", br_handler())
    job = batch.jobs[0]
    assert batch.complete and job.description == "Build systems"
    assert job.application_url == BJOB + "/apply"
    assert job.location == "London" and job.remote_status == "Hybrid"
    assert job.salary["source_text"] == breezy_row()["salary"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"rows": {}},
        {"rows": []},
        {"rows": [breezy_row()] * 2},
        {"rows": [breezy_row()] * 401},
        {"board": "<html>Unavailable</html>"},
        {"body": detail(url="https://evil.com/p/job")},
        {"body": detail(application=False)},
        {"body": "<html>Unavailable</html>"},
        {"status": 404},
        {"confirmation": []},
    ],
)
def test_breezy_partial_and_failed_enumeration_rejected(kwargs):
    with pytest.raises((ValueError, KeyError, TypeError)):
        run("breezy", br_handler(**kwargs))


@pytest.mark.parametrize(
    "url,expected",
    [
        (TT + "/jobs", ("teamtailor", "example")),
        (BR + "/p/123456abcdef-engineer", ("breezy", "example")),
    ],
)
def test_cohort4_detection(url, expected):
    assert detect(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://foo.bar.teamtailor.com/jobs",
        "https://example.breezy.hr.evil.com/",
        "https://user@example.breezy.hr/",
        "https://example.teamtailor.com:444/jobs",
        "http://example.breezy.hr/",
        "https://example.teamtailor.com.evil.com/jobs",
    ],
)
def test_cohort4_rejects_unsafe_hosts(url):
    with pytest.raises(ValueError):
        detect(url)

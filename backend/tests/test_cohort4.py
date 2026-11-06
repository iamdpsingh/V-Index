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


def workable_payload():
    return {
        "name": "Example",
        "jobs": [
            {
                "shortcode": "A12B34",
                "title": "Engineer",
                "description": "<p>Build systems</p>",
                "requirements": "<p>Python</p>",
                "benefits": "<p>Leave</p>",
                "url": "https://apply.workable.com/j/A12B34",
                "application_url": "https://apply.workable.com/j/A12B34/apply",
                "published_on": "2026-11-01",
                "created_at": "2025-01-01",
                "employment_type": "Full-time",
                "workplace_type": "hybrid",
                "locations": [
                    {"city": "London", "country": "UK"},
                    {"city": "Paris", "country": "France"},
                ],
                "salary": {"salary_from": 50000, "salary_currency": "GBP"},
            }
        ],
    }


def workable_handler(payload=None, confirmation=None, status=200):
    calls = 0

    def handle(request):
        nonlocal calls
        assert request.url.host == "apply.workable.com"
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        assert (
            str(request.url)
            == "https://apply.workable.com/api/v1/widget/accounts/example?details=true"
        )
        calls += 1
        data = confirmation if calls > 1 and confirmation is not None else payload
        return httpx.Response(status, json=data if data is not None else workable_payload())

    return handle


def test_workable_public_collection_preserves_fields():
    batch = run("workable", workable_handler())
    job = batch.jobs[0]
    assert batch.complete and job.description == "Build systems\n\nPython\n\nLeave"
    assert job.location == "London, UK; Paris, France"
    assert job.remote_status == "hybrid" and job.salary["salary_currency"] == "GBP"
    assert job.published_at.year == 2026 and job.raw["created_at"] == "2025-01-01"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda p: p.pop("jobs"),
        lambda p: p.update(jobs={}),
        lambda p: p.update(name=""),
        lambda p: p.update(next_url="https://evil.com"),
        lambda p: p["jobs"].append(copy.deepcopy(p["jobs"][0])),
        lambda p: p["jobs"][0].pop("description"),
        lambda p: p["jobs"][0].update(application_url="javascript:alert(1)"),
        lambda p: p["jobs"][0].update(shortcode="../bad"),
    ],
)
def test_workable_malformed_and_partial_rejected(mutation):
    payload = workable_payload()
    mutation(payload)
    with pytest.raises((ValueError, KeyError, TypeError)):
        run("workable", workable_handler(payload))


def test_workable_changed_collection_or_failed_request_not_empty_success():
    for handler in (
        workable_handler(confirmation={"name": "Example", "jobs": []}),
        workable_handler(status=403),
    ):
        with pytest.raises(ValueError):
            run("workable", handler)


def test_workable_explicit_empty_named_collection():
    batch = run("workable", workable_handler({"name": "Example", "jobs": []}))
    assert batch.complete and batch.jobs == []


def test_workable_url_detection():
    assert detect("https://apply.workable.com/learnworlds/j/A12B34/") == ("workable", "learnworlds")
    for url in (
        "https://apply.workable.com/j/A12B34",
        "https://apply.workable.com/api/",
        "https://apply.workable.com.evil.com/learnworlds/",
    ):
        with pytest.raises(ValueError):
            detect(url)


def test_workable_multilocation_variants_merge_without_losing_observations():
    payload = workable_payload()
    second = copy.deepcopy(payload["jobs"][0])
    payload["jobs"][0]["locations"] = [{"city": "London", "country": "UK"}]
    second["locations"] = [{"city": "Paris", "country": "France"}]
    payload["jobs"].append(second)
    batch = run("workable", workable_handler(payload))
    assert len(batch.jobs) == 1
    assert batch.jobs[0].location == "London, UK; Paris, France"
    assert len(batch.jobs[0].raw["location_variants"]) == 2
    second["title"] = "Different opening"
    with pytest.raises(ValueError, match="conflicting"):
        run("workable", workable_handler(payload))


def test_workable_location_loss_during_confirmation_fails():
    confirmation = workable_payload()
    confirmation["jobs"][0]["locations"] = [{"city": "London", "country": "UK"}]
    with pytest.raises(ValueError, match="changed"):
        run("workable", workable_handler(confirmation=confirmation))


def test_breezy_talent_pool_html_identity_without_jobposting_schema():
    body = (
        f'<link rel="canonical" href="{BJOB}"><meta property="og:url" content="{BJOB}">'
        f'<h1>Engineer</h1><div class="description">Build systems</div>'
        f'<a href="{BJOB}/apply">Apply</a>'
    )
    job = run("breezy", br_handler(body=body)).jobs[0]
    assert job.description == "Build systems" and job.application_url == BJOB + "/apply"
    assert job.quality_flags == ["jobposting_schema_missing"]
    assert "description_html" in job.raw
    for invalid in (
        body.replace("<h1>Engineer</h1>", "<h1>Different job</h1>"),
        body.replace('property="og:url"', 'property="unrelated"'),
        body.replace('rel="canonical"', 'rel="unrelated"'),
    ):
        with pytest.raises(ValueError, match="identity"):
            run("breezy", br_handler(body=invalid))


def bamboo_row():
    return {"id": "12", "jobOpeningName": "Engineer", "isRemote": None}


def bamboo_detail():
    return {
        "result": {
            "jobOpening": {
                "jobOpeningShareUrl": "https://example.bamboohr.com/careers/12",
                "jobOpeningName": "Engineer",
                "jobOpeningStatus": "Open",
                "description": "<p>Build</p>",
                "location": {"city": "London", "state": "England", "addressCountry": "UK"},
                "locationType": "2",
                "employmentStatusLabel": "Full-Time",
                "datePosted": "2026-11-01",
                "compensation": "£50,000 per year",
            },
            "formFields": {"not_saved": "application form configuration"},
        }
    }


def bamboo_handler(payload=None, detail_payload=None, confirmation=None, detail_status=200):
    calls = 0

    def handle(request):
        nonlocal calls
        assert request.url.host == "example.bamboohr.com"
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        if request.url.path == "/careers/list":
            calls += 1
            data = confirmation if calls > 1 and confirmation is not None else payload
            return httpx.Response(
                200,
                json=data
                if data is not None
                else {"meta": {"totalCount": 1}, "result": [bamboo_row()]},
            )
        assert request.url.path == "/careers/12/detail"
        return httpx.Response(
            detail_status, json=detail_payload if detail_payload is not None else bamboo_detail()
        )

    return handle


def test_bamboo_preserves_details_without_guessing_workplace_enums():
    batch = run("bamboohr", bamboo_handler())
    job = batch.jobs[0]
    assert batch.complete and job.description == "Build"
    assert job.location == "London, England, UK" and job.employment_type == "Full-Time"
    assert job.salary["source_text"] == "£50,000 per year" and job.published_at.year == 2026
    assert job.remote_status is None and job.quality_flags == ["workplace_type_unmapped"]
    assert job.raw["jobOpening"]["locationType"] == "2" and "formFields" not in job.raw
    assert job.source_url == job.application_url == "https://example.bamboohr.com/careers/12"


@pytest.mark.parametrize(
    "payload",
    [
        {"meta": {"totalCount": True}, "result": [bamboo_row()]},
        {"meta": {"totalCount": 2}, "result": [bamboo_row()]},
        {"meta": {"totalCount": 2}, "result": [bamboo_row(), bamboo_row()]},
        {"meta": {"totalCount": 0}, "result": []},
        {"meta": {"totalCount": 401}, "result": [bamboo_row()] * 401},
        {"meta": {}, "result": []},
        {"meta": {"totalCount": 1}, "result": {}},
        {"meta": {"totalCount": 1}, "result": [{**bamboo_row(), "id": "../12"}]},
    ],
)
def test_bamboo_partial_or_invalid_lists_rejected(payload):
    with pytest.raises((ValueError, KeyError, TypeError)):
        run("bamboohr", bamboo_handler(payload=payload))


@pytest.mark.parametrize(
    "mutation",
    [
        lambda j: j.update(jobOpeningStatus="Closed"),
        lambda j: j.update(jobOpeningShareUrl="https://evil.com/careers/12"),
        lambda j: j.update(jobOpeningName="Other"),
        lambda j: j.pop("description"),
    ],
)
def test_bamboo_invalid_or_closed_detail_fails(mutation):
    d = bamboo_detail()
    mutation(d["result"]["jobOpening"])
    with pytest.raises((ValueError, KeyError)):
        run("bamboohr", bamboo_handler(detail_payload=d))


def test_bamboo_failed_detail_and_changed_listing_fail():
    for handler in (
        bamboo_handler(detail_status=404),
        bamboo_handler(confirmation={"meta": {"totalCount": 0}, "result": []}),
    ):
        with pytest.raises(ValueError):
            run("bamboohr", handler)


def test_bamboo_url_detection():
    assert detect("https://anaergia.bamboohr.com/careers/367") == ("bamboohr", "anaergia")
    for url in (
        "https://anaergia.bamboohr.com.evil.com/careers",
        "https://a.b.bamboohr.com/careers",
    ):
        with pytest.raises(ValueError):
            detect(url)

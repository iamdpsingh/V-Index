"""Paylocity public state, full descriptions, native application and lifecycle safeguards."""

import asyncio
import json

import httpx
import pytest
from vindex.connectors.registry import create_connector, detect

SLUG = "a387d706-ac6f-4e58-b47b-be05001923ea"
ROOT = "/Recruiting/Jobs/All/" + SLUG
PATH = "/Recruiting/Jobs/Details/12"
LOGO = "/Recruiting/Jobs/GetLogoFileById?logoFileStoreId=1&moduleId=7"
ORIGIN = "https://recruiting.paylocity.com"


def row():
    return {
        "JobId": 12,
        "JobTitle": "Engineer",
        "LocationName": "London",
        "ShouldDisplayLocation": True,
        "PublishedDate": "2026-11-01T10:00:00-05:00",
        "Description": "Build sys...",
        "IsInternal": False,
        "HiringDepartment": "Engineering",
        "IsRemote": True,
        "IndeedRemoteType": 2,
        "JobLocation": {"ModuleId": 7, "City": "London", "Country": "UK"},
    }


def state():
    return {
        "ModuleId": "7",
        "ModuleTitle": "Example",
        "ShowInternal": False,
        "LeadJoinUrl": "/Recruiting/PublicLeads/New/" + SLUG,
        "LogoUrl": LOGO,
        "Jobs": [row()],
        "TrackingPixels": ["MUST_NOT_RETAIN"],
    }


def page(d, html):
    return "<html><script>window.pageData = " + json.dumps(d) + ";</script>" + html + "</html>"


def board(d=None):
    return page(d or state(), "<title>Example - Job Opportunities</title>")


def detail():
    return page(
        {"jobTitle": "Engineer", "moduleName": "Example"},
        f'''<title>Example - Engineer</title>
    <meta property="og:url" content="{ORIGIN + PATH}"><img src="{LOGO}">
    <span class="job-preview-title">Engineer</span><div class="preview-location">Fully Remote • London</div>
    <a class="apply-link-marker" href="/Recruiting/Jobs/Apply/12">Apply</a>
    <div class="job-preview-details"><div class="vertical-padding"><div class="job-listing-header">Job Type</div><span>Full-time</span></div>
    <div class="job-listing-header">Description</div><div><p>Build reliable systems</p></div>
    <div class="job-listing-header">Requirements</div><div><p>Know Python</p></div>
    <div class="job-listing-header">Salary Description</div><div>GBP 50,000 a year</div>
    <div><a class="apply-link-marker" href="/Recruiting/Jobs/Apply/12">Apply</a></div></div>''',
    )


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.paylocity.asyncio.sleep", no_wait)


def run(html=None, body=None, confirm=None, status=200, robots="User-agent: *\nAllow: /"):
    calls = 0

    async def discover():
        def handle(request):
            nonlocal calls
            assert request.url.host == "recruiting.paylocity.com" and not request.url.query
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text=robots)
            if request.url.path == ROOT:
                calls += 1
                return httpx.Response(
                    200, text=confirm if calls > 1 and confirm is not None else html or board()
                )
            assert request.url.path == PATH
            return httpx.Response(status, text=body or detail())

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await create_connector("paylocity", SLUG, "Configured", client).discover()

    return asyncio.run(discover())


def test_full_description_and_requirements_are_not_preview_or_application_chrome():
    b = run()
    j = b.jobs[0]
    assert b.complete and j.title == "Engineer" and j.company == "Example"
    assert j.description == "Build reliable systems\n\nKnow Python" and "Apply" not in j.description
    assert j.salary == {"text": "GBP 50,000 a year"} and j.employment_type == "Full-time"
    assert (
        j.remote_status == "Fully Remote" and j.published_at.utcoffset().total_seconds() == -18000
    )
    assert j.application_url == ORIGIN + "/Recruiting/Jobs/Apply/12"
    assert "MUST_NOT_RETAIN" not in j.model_dump_json()
    assert detect(ORIGIN + ROOT) == ("paylocity", SLUG)


@pytest.mark.parametrize(
    "key,value",
    [
        ("ShowInternal", True),
        ("Jobs", []),
        ("ModuleId", "0"),
        ("ModuleTitle", "Other"),
        ("LeadJoinUrl", "https://evil.com"),
        ("LogoUrl", "https://evil.com"),
    ],
)
def test_empty_internal_or_mismatched_board_aborts(key, value):
    d = state()
    d[key] = value
    with pytest.raises(ValueError):
        run(html=board(d))


@pytest.mark.parametrize(
    "key,value",
    [("IsInternal", True), ("JobId", True), ("JobLocation", {"ModuleId": 8}), ("IsRemote", None)],
)
def test_invalid_public_row_aborts(key, value):
    d = state()
    d["Jobs"][0][key] = value
    with pytest.raises(ValueError):
        run(html=board(d))


@pytest.mark.parametrize(
    "replacement",
    [
        ('"moduleName": "Example"', '"moduleName": "Other"'),
        ('"jobTitle": "Engineer"', '"jobTitle": "Other"'),
        ("/Recruiting/Jobs/Apply/12", "https://evil.com/apply"),
        ("moduleId=7", "moduleId=8"),
        ('class="job-preview-title">Engineer', 'class="job-preview-title">Other'),
        ('class="job-listing-header">Description', 'class="job-listing-header">Unsupported'),
        ("Fully Remote •", "Unknown •"),
        ("</html>", ""),
    ],
)
def test_inconsistent_or_incomplete_detail_aborts(replacement):
    with pytest.raises(ValueError):
        run(body=detail().replace(*replacement))


def test_changed_roster_aborts():
    with pytest.raises(ValueError):
        run(confirm=board().replace("Build sys...", "Changed"))


def test_failed_request_is_not_empty_success():
    with pytest.raises(httpx.HTTPStatusError):
        run(status=503)


def test_robots_denial_aborts():
    with pytest.raises(ValueError):
        run(robots="User-agent: *\nDisallow: /Recruiting/Jobs/Details/")

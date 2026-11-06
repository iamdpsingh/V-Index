"""TriNet table completeness, public identity, native form and failure cases."""

import asyncio

import httpx
import pytest
from vindex.connectors.registry import create_connector, detect

SLUG = "7-example"
ROOT = f"/companies/{SLUG}/jobs"
PATH = ROOT + "/12-engineer"
ORIGIN = "https://app.trinethire.com"


def board():
    return f'''<html><title>Careers at Example</title><a href="{ROOT}">Jobs</a>
    <table class="job-list"><thead><tr><th>Role</th><th>Type</th><th>Location</th></tr></thead>
    <tbody><tr class="job"><td><a href="{PATH}">Engineer</a></td><td class="type">Full-time</td><td class="location">Remote</td></tr></tbody></table></html>'''


def detail():
    return f'''<html><meta property="og:site_name" content="TriNet Applicant Tracking">
    <meta property="og:title" content="Example | Engineer"><meta property="og:url" content="{ORIGIN + PATH}?source=Our+Job+Board">
    <a href="{ROOT}">Jobs at Example</a><h3 class="job-name">Engineer</h3>
    <ul class="job-meta"><li><span class="map-pin-icon"></span>London</li><li><strong>Type:</strong> Full-time</li><li>Salary: GBP 50,000</li></ul>
    <div class="job-descr content"><p>Build systems</p></div>
    <form id="new_applicant" action="{PATH}" method="post"><input id="job_id" name="job_id" value="12"></form></html>'''


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.trinet.asyncio.sleep", no_wait)


def run(html=None, body=None, confirm=None, status=200, robots="User-agent: *\nAllow: /"):
    calls = 0

    async def discover():
        def handle(request):
            nonlocal calls
            assert request.url.host == "app.trinethire.com" and not request.url.query
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
            return await create_connector("trinet", SLUG, "Configured", client).discover()

    return asyncio.run(discover())


def test_complete_table_and_native_application_preserve_location_observations():
    batch = run()
    j = batch.jobs[0]
    assert batch.complete and j.external_id == "12" and j.company == "Example"
    assert j.location == "Remote; London" and j.remote_status == "Remote"
    assert j.description == "Build systems" and j.salary == {"text": "Salary: GBP 50,000"}
    assert j.employment_type == "Full-time" and j.published_at is None
    assert j.application_url == ORIGIN + PATH
    assert detect(ORIGIN + ROOT) == ("trinet", SLUG)


@pytest.mark.parametrize(
    "replacement",
    [
        ("Careers at Example", "Unknown"),
        ("</html>", ""),
        ("<th>Type</th>", "<th>Other</th>"),
        ('class="job"', 'class="hidden"'),
        ('class="type"', 'class="other"'),
        (f'href="{PATH}"', 'href="https://evil.com/jobs/12"'),
        ("</table>", '</table><a rel="next" href="?page=2">Next</a>'),
        ("</table>", f'</table><a href="{ROOT}/13-other">Other</a>'),
    ],
)
def test_malformed_partial_or_paginated_roster_aborts(replacement):
    with pytest.raises(ValueError):
        run(html=board().replace(*replacement))


@pytest.mark.parametrize(
    "replacement",
    [
        ("Example | Engineer", "Confidential Company | Engineer"),
        ('value="12"', 'value="13"'),
        ("Type:</strong> Full-time", "Type:</strong> Part-time"),
        ('class="job-name">Engineer', 'class="job-name">Other'),
        (f'action="{PATH}"', 'action="https://evil.com"'),
        ('class="job-descr content"', 'class="other"'),
        (
            "app.trinethire.com/companies/7-example/jobs/12-engineer?source",
            "evil.com/companies/7-example/jobs/12-engineer?source",
        ),
    ],
)
def test_identity_confidential_or_application_mismatch_aborts(replacement):
    with pytest.raises(ValueError):
        run(body=detail().replace(*replacement))


def test_changed_roster_aborts():
    with pytest.raises(ValueError):
        run(confirm=board().replace(">Remote<", ">London<"))


def test_failed_fetch_is_not_empty_success():
    with pytest.raises(httpx.HTTPStatusError):
        run(status=503)


def test_robots_denial_aborts():
    with pytest.raises(ValueError):
        run(robots=f"User-agent: *\nDisallow: {PATH}")

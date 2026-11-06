"""CareerPlug schema ceiling, source identity and application checks."""

import asyncio
import json

import httpx
import pytest
from vindex.connectors.registry import create_connector, detect


def job():
    return {
        "@type": "JobPosting",
        "title": "Engineer",
        "description": "&lt;p&gt;Build software&lt;/p&gt;",
        "identifier": {"name": "CareerPlug Job ID", "value": "12"},
        "hiringOrganization": {"name": "Example"},
        "directApply": True,
        "datePosted": "2026-11-01T10:00:00Z",
        "employmentType": "FULL_TIME",
        "jobLocation": {"address": {"addressLocality": "London", "addressCountry": "UK"}},
    }


def board(count=1, rows=None):
    value = {
        "@type": "ItemList",
        "numberOfItems": count,
        "itemListElement": rows
        if rows is not None
        else [{"@type": "ListItem", "position": 1, "item": job()}],
    }
    return f"""<html><title>Example</title><h1>Example</h1>
    <script type="application/ld+json">{json.dumps(value)}</script>
    <div id="job_filters"><form action="/jobs?id=7#job_filters" method="get">
    <select id="job_filter_n"><option value=""></option><option value="Engineer">Engineer</option></select></form></div></html>"""


def detail(value=None):
    return f"""<html><title>Engineer | Example</title><script type="application/ld+json">{json.dumps(value or job())}</script>
    <h1>Example</h1><h1>Engineer</h1><form id="new_app" action="/jobs/12/apps" method="post"></form></html>"""


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.careerplug.asyncio.sleep", no_wait)


def run(html=None, body=None, confirm=None, status=200, robots="User-agent: *\nAllow: /"):
    calls = 0

    async def discover():
        def handler(request):
            nonlocal calls
            assert request.url.host == "app.careerplug.com" and not request.url.query
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text=robots)
            if request.url.path == "/accounts/7":
                calls += 1
                return httpx.Response(
                    200, text=confirm if calls > 1 and confirm is not None else html or board()
                )
            assert request.url.path == "/jobs/12/apps/new"
            return httpx.Response(status, text=body or detail())

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await create_connector("careerplug", "7", "Configured", client).discover()

    return asyncio.run(discover())


def test_complete_schema_with_native_application_preserves_source_fields():
    result = run()
    j = result.jobs[0]
    assert result.complete and j.company == "Example" and j.external_id == "12"
    assert j.description == "Build software" and j.location == "London, UK"
    assert j.application_url == "https://app.careerplug.com/jobs/12/apps/new"
    assert j.employment_type == "FULL_TIME" and j.published_at.year == 2026
    assert detect("https://app.careerplug.com/accounts/7") == ("careerplug", "7")


@pytest.mark.parametrize("count", [0, 2, 30, 31, True])
def test_empty_partial_or_ceiling_list_aborts(count):
    with pytest.raises(ValueError):
        run(html=board(count))


@pytest.mark.parametrize(
    "replacement",
    [
        ('"position": 1', '"position": 2'),
        ('"value": "12"', '"value": "https://evil.com"'),
        ('"directApply": true', '"directApply": false'),
        ("id=7#", "id=8#"),
        ('value="Engineer"', 'value="Other"'),
        ("</html>", ""),
    ],
)
def test_malformed_or_mismatched_board_aborts(replacement):
    with pytest.raises(ValueError):
        run(html=board().replace(*replacement))


@pytest.mark.parametrize(
    "replacement",
    [
        ('action="/jobs/12/apps"', 'action="https://evil.com"'),
        ('"name": "Example"', '"name": "Other"'),
        ('"value": "12"', '"value": "13"'),
        ('"title": "Engineer"', '"title": "Other"'),
    ],
)
def test_mismatched_details_abort(replacement):
    with pytest.raises(ValueError):
        run(body=detail().replace(*replacement))


def test_changed_collection_aborts():
    with pytest.raises(ValueError):
        run(confirm=board().replace("Build software", "Changed role"))


def test_fetch_failure_is_not_empty_success():
    with pytest.raises(httpx.HTTPStatusError):
        run(status=503)


def test_robots_denial_aborts():
    with pytest.raises(ValueError):
        run(robots="User-agent: *\nDisallow: /jobs/")

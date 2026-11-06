"""Controlled Trakstar explicit totals, metadata, ID and application regressions."""

import asyncio
import copy
import json

import httpx
import pytest
from vindex.connectors.registry import create_connector, detect

ORIGIN = "https://example.hire.trakstar.com"
PATH = "/jobs/fk12345/"


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.trakstar.asyncio.sleep", no_wait)


def board(total=1):
    return f'''<html><title>Example jobs | Example openings | Example careers</title><body>
    <p>View {total} Openings</p><a href="{PATH}"><h3 class="js-job-list-opening-name">Engineer's Role</h3>
    <div class="js-job-list-opening-meta">Full-time | Hybrid</div></a></body></html>'''


def schema():
    return {
        "@type": "JobPosting",
        "title": "Engineer's Role",
        "identifier": {"value": "fk12345"},
        "hiringOrganization": {"name": "Example"},
        "description": "&lt;p&gt;Build systems&lt;/p&gt;",
        "employmentType": "FULL_TIME",
        "datePosted": "2026-11-01",
        "jobLocation": {"address": {"addressLocality": "London", "addressCountry": "UK"}},
    }


def detail(value=None):
    return f'''<html><title>Engineer's Role at Example</title><head><meta property="og:url" content="{ORIGIN + PATH}">
    <script type="application/ld+json">{json.dumps(value or schema())}</script></head><body>
    <a href="?apply=true">Apply</a><form id="job_application_form" action="{PATH.rstrip("/")}" method="post"></form></body></html>'''


def run(html=None, job=None, confirm=None, body=None, status=200, robots="User-agent: *\nAllow: /"):
    calls = 0

    async def discover():
        def handler(request):
            nonlocal calls
            assert request.url.host == "example.hire.trakstar.com"
            assert not request.url.query
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text=robots)
            if request.url.path == "/":
                calls += 1
                value = confirm if calls > 1 and confirm is not None else html
                return httpx.Response(200, text=value if value is not None else board())
            assert request.url.path == PATH
            return httpx.Response(status, text=body if body is not None else detail(job))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await create_connector("trakstar", "example", "Configured", client).discover()

    return asyncio.run(discover())


def test_explicit_total_and_matching_public_role_preserve_fields():
    batch = run()
    job = batch.jobs[0]
    assert batch.complete and job.external_id == "fk12345" and job.company == "Example"
    assert job.description == "Build systems" and job.location == "London, UK"
    assert job.remote_status == "Hybrid" and job.employment_type == "FULL_TIME"
    assert job.application_url == ORIGIN + PATH + "?apply=true" and job.published_at.year == 2026


@pytest.mark.parametrize(
    "html",
    [
        board(0),
        board(2),
        board(401),
        board().replace("</html>", ""),
        board().replace(PATH, "https://evil.com" + PATH),
    ],
)
def test_missing_partial_oversized_or_unsafe_roster_aborts(html):
    with pytest.raises(ValueError):
        run(html=html)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d.update(title="Other"),
        lambda d: d["identifier"].update(value="different"),
        lambda d: d["hiringOrganization"].update(name="Other"),
        lambda d: d.pop("description"),
    ],
)
def test_wrong_or_incomplete_detail_aborts(mutation):
    value = copy.deepcopy(schema())
    mutation(value)
    with pytest.raises((ValueError, KeyError)):
        run(job=value)


def test_application_identity_failed_request_and_changed_list_abort():
    for kwargs in (
        {"body": detail().replace('action="/jobs/fk12345"', 'action="/jobs/other123"')},
        {"status": 404},
        {"confirm": board().replace("Hybrid", "Remote")},
        {"robots": "User-agent: *\nDisallow: /"},
    ):
        with pytest.raises(ValueError):
            run(**kwargs)


def test_encoded_title_and_host_boundaries():
    value = schema()
    value["title"] = "Engineer's Role".replace("'", "&#x27;")
    assert run(job=value).jobs[0].title == "Engineer's Role"
    assert detect(ORIGIN + PATH) == ("trakstar", "example")
    for url in ("https://a.b.hire.trakstar.com/", "https://example.hire.trakstar.com.evil.com/"):
        with pytest.raises(ValueError):
            detect(url)


def test_observed_literal_newlines_in_legacy_description_are_preserved():
    payload = schema()
    payload["description"] = "&lt;p&gt;Build\nsystems&lt;/p&gt;"
    body = detail(payload).replace("\\n", "\n")
    job = run(body=body).jobs[0]
    assert "Build" in job.description and "systems" in job.description
    assert "jsonld_literal_whitespace" in job.quality_flags
    assert job.raw["legacy_jsonld_scripts"]


@pytest.mark.parametrize("literal", ["\x00", "\x01", "\x1f"])
def test_unexpected_literal_control_characters_still_abort(literal):
    payload = schema()
    payload["description"] = "Build\nsystems"
    body = detail(payload).replace("\\n", literal)
    with pytest.raises((ValueError, json.JSONDecodeError)):
        run(body=body)

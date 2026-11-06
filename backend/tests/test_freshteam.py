"""Controlled Freshteam HTML identity, application, encoding and freshness boundaries."""

import asyncio
import copy
import json

import httpx
import pytest
from vindex.connectors.registry import create_connector, detect

ORIGIN = "https://example.freshteam.com"
KEY = "ABcd1234EFgh"
PATH = f"/jobs/{KEY}/engineer"


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.freshteam.asyncio.sleep", no_wait)


def board():
    return f'''<html><title>Careers @ Example</title><body><div class="job-role-list">
    <a class="heading" href="{PATH}" data-portal-remote-location="true" data-portal-location="London, UK" data-portal-job-type="1">
    <div class="job-title">Engineer</div><div class="job-desc text">Truncated...</div></a></div></body></html>'''


def schema():
    return {
        "@type": "JobPosting",
        "title": "Engineer",
        "url": f"{ORIGIN}/jobs/{KEY}/Engineer%20Role",
        "description": "&lt;p&gt;Build &lt;strong&gt;systems&lt;/strong&gt;&lt;/p&gt;",
        "datePosted": "2026-11-01 09:00:00 UTC",
        "remote": "true",
        "employmentType": "FULL_TIME",
        "hiringOrganization": {"name": "Example"},
    }


def detail(value=None):
    return f"""<html><title>Careers @ Example</title><body><script type="application/ld+json">{json.dumps(value or schema())}</script>
    <form action="/jobs/{KEY}/applicants" method="post"></form></body></html>"""


def run(
    html=None,
    job=None,
    confirm=None,
    status=200,
    detail_html=None,
    robots="User-agent: *\nAllow: /",
):
    calls = 0

    async def discover():
        def handler(request):
            nonlocal calls
            assert request.url.host == "example.freshteam.com"
            assert not request.url.query
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text=robots)
            if request.url.path == "/jobs":
                calls += 1
                body = confirm if calls > 1 and confirm is not None else html
                return httpx.Response(200, text=body if body is not None else board())
            assert request.url.path == PATH
            return httpx.Response(
                status, text=detail_html if detail_html is not None else detail(job)
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await create_connector("freshteam", "example", "Configured", client).discover()

    return asyncio.run(discover())


def test_full_detail_decodes_source_html_entities_and_explicit_utc():
    batch = run()
    job = batch.jobs[0]
    assert batch.complete and job.external_id == KEY and job.company == "Example"
    assert job.description == "Build systems" and job.location == "London, UK"
    assert job.remote_status == "Remote" and job.employment_type == "FULL_TIME"
    assert job.published_at.isoformat() == "2026-11-01T09:00:00+00:00"
    assert job.source_url == job.application_url == ORIGIN + PATH
    assert "&lt;p&gt;" in job.raw["jobposting"]["description"]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda j: j.update(title="Other"),
        lambda j: j.update(url="https://evil.com/jobs/ABcd1234EFgh/engineer"),
        lambda j: j.update(url=ORIGIN + "/jobs/OTHER1234567/engineer"),
        lambda j: j.update(remote="false"),
        lambda j: j.pop("description"),
        lambda j: j.update(datePosted="not a timestamp"),
    ],
)
def test_wrong_or_malformed_detail_aborts(mutation):
    job = copy.deepcopy(schema())
    mutation(job)
    with pytest.raises((ValueError, KeyError)):
        run(job=job)


@pytest.mark.parametrize(
    "replacement",
    [
        (PATH, "https://evil.com" + PATH),
        ("job-role-list", "other-list"),
        ("job-title", "other-title"),
        ("</html>", ""),
        ("</body>", '<a rel="next" href="?page=2">Next</a></body>'),
    ],
)
def test_unsafe_or_partial_career_lists_abort(replacement):
    with pytest.raises(ValueError):
        run(html=board().replace(*replacement))


def test_closed_missing_application_request_failure_and_changed_list_abort():
    for kwargs in (
        {
            "detail_html": detail().replace(
                f"/jobs/{KEY}/applicants", "/jobs/OTHER1234567/applicants"
            )
        },
        {"status": 404},
        {"confirm": board().replace("London, UK", "Paris, France")},
        {"robots": "User-agent: *\nDisallow: /"},
    ):
        with pytest.raises(ValueError):
            run(**kwargs)


def test_validated_tenant_detection():
    assert detect(ORIGIN + PATH) == ("freshteam", "example")
    for url in ("https://a.b.freshteam.com/jobs", "https://example.freshteam.com.evil.com/jobs"):
        with pytest.raises(ValueError):
            detect(url)


def test_source_title_padding_is_normalized_but_preserved_raw():
    payload = schema()
    payload["title"] = " Engineer "
    job = run(job=payload).jobs[0]
    assert job.title == "Engineer" and job.raw["jobposting"]["title"] == " Engineer "

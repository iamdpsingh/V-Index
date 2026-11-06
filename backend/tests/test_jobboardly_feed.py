"""Documented XML feed boundaries and full HTML roster cross-check regressions."""

import asyncio
from xml.sax.saxutils import escape

import httpx
import pytest
from defusedxml.common import DefusedXmlException
from vindex.connectors.registry import create_connector

ORIGIN = "https://example.jobboardly.com"
PATH = "/jobs/engineer-aaaaaaaa"


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.jobboardly.asyncio.sleep", no_wait)


def feed(**overrides):
    fields = dict(
        guid="1-engineer-aaaaaaaa",
        id="1",
        url=ORIGIN + PATH,
        application_link="https://employer.example/apply",
        title="Engineer",
        arrangement="fulltime",
        location_type="remote",
        location="UK",
        published_at="2026-11-01T09:00:00+00:00",
        expires_at="2026-12-01T09:00:00+00:00",
        html_description="<p>Build systems</p>",
        company_name="Example",
        salary_minimum="50000",
        salary_maximum="60000",
        salary_schedule="yearly",
        salary_currency="GBP",
    )
    fields.update(overrides)
    return (
        "<jobs><job>"
        + "".join(f"<{k}>{escape(v)}</{k}>" for k, v in fields.items())
        + "</job></jobs>"
    )


def page(path=PATH):
    return f'<p>Showing <span>1</span> to <span>1</span></p><nav aria-label="Pagination"><span aria-disabled="true">Next</span></nav><a href="{path}">Engineer</a>'


def run(body=None, confirm=None, html=None, status=200):
    calls = 0

    async def discover():
        def handler(request):
            nonlocal calls
            assert request.url.host == "example.jobboardly.com"
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text="User-agent: *\nAllow: /")
            if request.url.path == "/jobs.xml":
                calls += 1
                return httpx.Response(
                    status,
                    text=confirm
                    if calls > 1 and confirm is not None
                    else body
                    if body is not None
                    else feed(),
                )
            assert (
                request.url.path == "/jobs"
            )  # Full descriptions come from the public feed, no detail/external requests.
            return httpx.Response(200, text=html if html is not None else page())

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await create_connector("jobboardly", "example", "Board", client).discover()

    return asyncio.run(discover())


def test_documented_xml_job_fields_and_application_preserved():
    batch = run()
    job = batch.jobs[0]
    assert batch.complete and job.external_id == "1" and job.company == "Example"
    assert job.description == "Build systems" and job.remote_status == "remote"
    assert job.salary == {
        "minimum": "50000",
        "maximum": "60000",
        "currency": "GBP",
        "schedule": "yearly",
    }
    assert job.published_at.hour == 9 and job.application_url == "https://employer.example/apply"
    assert "<expires_at>" in job.raw["xml"]


@pytest.mark.parametrize(
    "changes",
    [
        {"id": "-1"},
        {"id": "1.5"},
        {"guid": "2-engineer-aaaaaaaa"},
        {"url": "https://evil.com" + PATH},
        {"application_link": "http://employer.example/apply"},
        {"application_link": "https://user:pass@employer.example/apply"},
        {"published_at": ""},
    ],
)
def test_invalid_feed_identity_and_destinations_fail(changes):
    with pytest.raises(ValueError):
        run(body=feed(**changes))


def test_feed_mismatch_and_final_content_change_fail():
    for kwargs in (
        {"html": page("/jobs/other-bbbbbbbb")},
        {"confirm": feed(title="Changed")},
        {"body": "<jobs/>"},
        {"status": 403},
    ):
        with pytest.raises(ValueError):
            run(**kwargs)


def test_duplicate_jobs_duplicate_fields_and_xml_entities_fail():
    value = feed()
    for bad in (
        value.replace("</jobs>", value.removeprefix("<jobs>")),
        value.replace("</job>", "<title>Again</title></job>"),
        '<!DOCTYPE jobs [<!ENTITY x "bad">]>' + value,
    ):
        with pytest.raises((ValueError, DefusedXmlException)):
            run(body=bad)


def test_email_application_preserves_mailto_and_original_https_entry():
    job = run(body=feed(application_link="mailto:jobs@example.org")).jobs[0]
    assert job.application_url == job.source_url == ORIGIN + PATH
    assert (
        "application_by_email" in job.quality_flags and "mailto:jobs@example.org" in job.raw["xml"]
    )

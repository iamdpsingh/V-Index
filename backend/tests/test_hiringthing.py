"""Controlled HiringThing independent roster/feed/detail safety regressions."""

import asyncio
import copy
import html
import json
from xml.sax.saxutils import escape

import httpx
import pytest
from vindex.connectors.registry import create_connector, detect

ORIGIN = "https://example.hiringthing.com"
PATH = "/job/123/engineer"


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.hiringthing.asyncio.sleep", no_wait)


def board():
    return f'<html><title>Example Career Opportunities</title><body><h1>Career Opportunities</h1><a href="{PATH}">Engineer</a><a href="{PATH}">Learn more</a></body></html>'


def feed(title="Engineer", link=None):
    return (
        '<rss xmlns:media="http://search.yahoo.com/mrss/"><channel><title>Example Jobs</title><link>https://example.hiringthing.com</link><item><title>'
        + title
        + "</title><link>"
        + escape(link or ORIGIN + PATH)
        + '</link><location>London, UK</location><media:description type="html">'
        + escape("<p>Build</p>")
        + "</media:description></item></channel></rss>"
    )


def job():
    return dict(
        id=123,
        company_id=1,
        company_name="Example",
        title="Engineer",
        url=PATH,
        joblink_url=ORIGIN + PATH,
        html_description="<p>Build</p>",
        location="London, UK",
        remote=True,
        min_salary={"amount": "50000", "currency": "GBP"},
        max_salary={"amount": "60000", "currency": "GBP"},
        pay_frequency="annually",
        posted_at="2026-11-01T09:00:00Z",
        questions=[{"private_form": "exclude"}],
        **{"hidden?": False},
    )


def detail(data=None):
    value = html.escape(json.dumps({"jobObj": {"table": data or job()}}), quote=True)
    schema = {
        "@type": "JobPosting",
        "title": "Engineer",
        "hiringOrganization": {"name": "Example"},
        "employmentType": "FULL_TIME",
    }
    return f'''<html><head><link rel="canonical" href="{ORIGIN + PATH}"><meta property="og:url" content="{ORIGIN + PATH}"><script type="application/ld+json">{json.dumps(schema)}</script></head><body><div class="job-title-container"><h2>Engineer</h2></div><div data-react-class="HiringThing.Components.ApplyButtonGroup" data-react-props="{value}"></div></body></html>'''


def run(
    rss=None,
    data=None,
    confirm=None,
    roster=None,
    status=200,
    robots="User-agent: *\nAllow: /",
    detail_alias=None,
):
    calls = 0

    async def discover():
        def handler(request):
            nonlocal calls
            assert request.url.host == "example.hiringthing.com"
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text=robots)
            if request.url.path == "/":
                return httpx.Response(200, text=roster if roster is not None else board())
            if request.url.path == "/api/rss.xml":
                calls += 1
                value = confirm if calls > 1 and confirm is not None else rss
                return httpx.Response(200, text=value if value is not None else feed())
            assert request.url.path == PATH
            body = detail(data)
            if detail_alias:
                body = body.replace(ORIGIN, detail_alias)
            return httpx.Response(status, text=body)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await create_connector("hiringthing", "example", "Configured", client).discover()

    return asyncio.run(discover())


def test_rss_full_roster_and_sanitized_source_job_preserve_fields():
    batch = run()
    j = batch.jobs[0]
    assert (
        batch.complete
        and j.company == "Example"
        and j.description == "Build"
        and j.remote_status == "Remote"
    )
    assert j.application_url == j.source_url == ORIGIN + PATH and j.employment_type == "FULL_TIME"
    assert j.salary["min_salary"]["amount"] == "50000" and j.published_at.hour == 9
    assert "questions" not in json.dumps(j.raw)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d.update(id=True),
        lambda d: d.update(id=124),
        lambda d: d.update(company_name="Other"),
        lambda d: d.update(title="Other"),
        lambda d: d.update(joblink_url="https://evil.com/"),
        lambda d: d.update(html_description="<p>Changed</p>"),
        lambda d: d.update(**{"hidden?": True}),
    ],
)
def test_mismatched_hidden_or_changed_details_abort(mutation):
    value = copy.deepcopy(job())
    mutation(value)
    with pytest.raises(ValueError):
        run(data=value)


def test_partial_mismatched_changed_and_failed_sources_abort():
    for kwargs in (
        {"rss": feed(title="Other")},
        {"rss": feed(link="https://evil.com" + PATH)},
        {"confirm": feed().replace("Build", "Changed")},
        {"status": 404},
        {"robots": "User-agent: *\nDisallow: /api/"},
        {"roster": board().replace("</body>", '<a rel="next" href="?page=2">Next</a></body>')},
    ):
        with pytest.raises(ValueError):
            run(**kwargs)


def test_distinct_numeric_ids_are_required_and_detection_is_host_bounded():
    assert detect(ORIGIN + PATH) == ("hiringthing", "example")
    for url in ("https://a.b.hiringthing.com/", "https://example.hiringthing.com.evil.com/"):
        with pytest.raises(ValueError):
            detect(url)


def test_same_tenant_oasis_metadata_alias_never_becomes_a_request_host():
    alias = "https://example.oasisrecruit.com"
    data = job()
    data["joblink_url"] = alias + PATH
    observed = run(rss=feed().replace(ORIGIN, alias), data=data, detail_alias=alias).jobs[0]
    assert observed.source_url == observed.application_url == ORIGIN + PATH
    assert observed.raw["rss"]["source_url"] == alias + PATH

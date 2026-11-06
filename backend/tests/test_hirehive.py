"""Public HireHive completeness regressions; controlled data is not live evidence."""

import asyncio
import copy
import json

import httpx
import pytest
from vindex.connectors.registry import create_connector, detect

ORIGIN = "https://example.hirehive.com"
PATH = "/engineer-london-abc123"


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.hirehive.asyncio.sleep", no_wait)


def page(data, canonical=None):
    return (
        "<html><head>"
        + (f'<link rel="canonical" href="{canonical}">' if canonical else "")
        + '<script type="application/ld+json">'
        + json.dumps(data)
        + "</script></head></html>"
    )


def listing(single=False):
    row = {
        "@type": "ListItem",
        "name": "Engineer",
        "url": ORIGIN + PATH + "?source=google_jobs_apply",
        "position": 1,
    }
    return {
        "@type": "ItemList",
        "name": "Open jobs for Example",
        "numberOfItems": 1,
        "itemListElement": row if single else [row],
    }


def detail():
    return {
        "@type": "JobPosting",
        "title": "Engineer",
        "identifier": {"value": 123.0},
        "url": ORIGIN + PATH + "?source=google_jobs_apply",
        "description": "<p>Build</p>",
        "employmentType": "FULL_TIME",
        "hiringOrganization": {"name": "Example"},
        "jobLocation": {"address": {"addressLocality": "Remote", "addressCountry": "UK"}},
        "datePosted": "2026-11-01",
        "baseSalary": {"currency": "GBP"},
    }


def run(board=None, job=None, confirm=None, status=200, robots="User-agent: *\nAllow: /"):
    calls = 0

    async def discover():
        def handler(request):
            nonlocal calls
            assert request.url.host == "example.hirehive.com"
            assert not request.url.query
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text=robots)
            if request.url.path == "/":
                calls += 1
                data = confirm if calls > 1 and confirm is not None else board
                return httpx.Response(200, text=page(data if data is not None else listing()))
            assert request.url.path == PATH
            return httpx.Response(
                status, text=page(job if job is not None else detail(), ORIGIN + PATH)
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await create_connector("hirehive", "example", "Configured", client).discover()

    return asyncio.run(discover())


@pytest.mark.parametrize("single", [True, False])
def test_full_public_list_and_detail_preserve_source_fields(single):
    batch = run(board=listing(single))
    job = batch.jobs[0]
    assert batch.complete and job.external_id == "123" and job.title == "Engineer"
    assert job.company == "Example" and job.description == "Build" and job.location == "Remote, UK"
    assert job.remote_status == "Remote" and job.salary["currency"] == "GBP"
    assert job.published_at.year == 2026 and job.source_url == job.application_url == ORIGIN + PATH
    assert "source=google_jobs_apply" in job.raw["url"]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda p: p.update(numberOfItems=True),
        lambda p: p.update(numberOfItems=2),
        lambda p: p.update(numberOfItems=401),
        lambda p: p.update(itemListElement=[]),
        lambda p: p.update(name=""),
        lambda p: p.update(name="Open jobs for "),
        lambda p: p["itemListElement"][0].update(position=2),
        lambda p: p["itemListElement"][0].update(url="https://evil.com/engineer-abc123"),
        lambda p: p["itemListElement"][0].update(url=ORIGIN + "/%2e%2e-abc123"),
    ],
)
def test_invalid_or_partial_list_fails(mutation):
    payload = listing()
    mutation(payload)
    with pytest.raises(ValueError):
        run(board=payload)


def test_duplicate_listing_fails():
    payload = listing()
    second = copy.deepcopy(payload["itemListElement"][0])
    second["position"] = 2
    payload["itemListElement"].append(second)
    payload["numberOfItems"] = 2
    with pytest.raises(ValueError, match="Duplicate"):
        run(board=payload)


def test_explicit_empty_named_collection_is_complete_but_not_live_coverage():
    payload = listing()
    payload.update(numberOfItems=0, itemListElement=[])
    batch = run(board=payload)
    assert batch.complete and batch.jobs == []


@pytest.mark.parametrize(
    "mutation",
    [
        lambda j: j.update(title="Other opening"),
        lambda j: j.update(url=ORIGIN + "/other-role-def456"),
        lambda j: j["identifier"].update(value=True),
        lambda j: j["identifier"].update(value=123.5),
        lambda j: j["identifier"].update(value=-1),
        lambda j: j.pop("description"),
    ],
)
def test_detail_mismatch_and_missing_fields_fail(mutation):
    payload = detail()
    mutation(payload)
    with pytest.raises((ValueError, KeyError)):
        run(job=payload)


def test_failed_detail_changed_list_and_robots_denial_fail():
    changed = listing()
    changed["itemListElement"][0]["name"] = "Changed"
    for kwargs in ({"status": 404}, {"confirm": changed}, {"robots": "User-agent: *\nDisallow: /"}):
        with pytest.raises(ValueError):
            run(**kwargs)


def test_hirehive_host_validation():
    assert detect(ORIGIN + PATH) == ("hirehive", "example")
    for url in ("https://a.b.hirehive.com/", "https://example.hirehive.com.evil.com/"):
        with pytest.raises(ValueError):
            detect(url)

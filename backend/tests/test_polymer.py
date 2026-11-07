"""Controlled Polymer API completeness boundaries; not live provider evidence."""

import asyncio
import copy
import json

import httpx
import pytest
from vindex.connectors.registry import create_connector, detect

URL = "https://jobs.polymer.co/example/123"
API = "/v1/hire/organizations/example/jobs"


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.polymer.asyncio.sleep", no_wait)


def collection():
    return dict(
        items=[
            dict(
                id=123,
                job_id=123,
                hash_id="ABC123",
                title="Engineer",
                organization_name="Example",
                job_post_url=URL,
                kind_pretty="Full-time",
                display_location="London, UK",
                remoteness_pretty="Hybrid",
                published_at="2026-11-01T09:00:00Z",
                salary_pretty="50K GBP a year",
                published_at_time_ago_short="5d",
            )
        ],
        meta=dict(
            total=1,
            count=1,
            page=1,
            is_first=True,
            is_last=True,
            next_page=None,
            organization_name="Example",
        ),
    )


def detail():
    return dict(
        **collection()["items"][0],
        archived_at=None,
        description="<p>Build</p>",
        job_application_description_url=URL,
        questions=[{"field": "resume"}],
        settings={"phone": "required"},
    )


def run(feed=None, job=None, confirm=None, status=200, robots="User-agent: *\nAllow: /"):
    calls = 0

    async def discover():
        def handler(request):
            nonlocal calls
            assert request.url.host == "api.polymer.co"
            assert not request.url.query and "authorization" not in request.headers
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text=robots)
            if request.url.path == API:
                calls += 1
                data = confirm if calls > 1 and confirm is not None else feed
                return httpx.Response(200, json=data if data is not None else collection())
            assert request.url.path == API + "/123"
            return httpx.Response(status, json=job if job is not None else detail())

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await create_connector("polymer", "example", "Configured", client).discover()

    return asyncio.run(discover())


def test_complete_public_api_and_original_fields_excluding_form_configuration():
    changed = copy.deepcopy(collection())
    changed["items"][0]["published_at_time_ago_short"] = "6d"
    batch = run(confirm=changed)
    job = batch.jobs[0]
    assert batch.complete and len(batch.jobs) == 1
    assert job.company == "Example" and job.description == "Build" and job.location == "London, UK"
    assert job.source_url == job.application_url == URL and job.remote_status == "Hybrid"
    assert job.salary == {"source_text": "50K GBP a year"} and job.published_at.hour == 9
    assert job.raw["listing"]["published_at_time_ago_short"] == "5d"
    assert "questions" not in json.dumps(job.raw) and "settings" not in json.dumps(job.raw)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda p: p["meta"].update(is_last=False),
        lambda p: p["meta"].update(is_last=1),
        lambda p: p["meta"].update(total=2),
        lambda p: p["meta"].update(page=True),
        lambda p: p["meta"].update(count=2),
        lambda p: p["meta"].update(next_page=2),
        lambda p: p["meta"].update(organization_name=""),
        lambda p: p.update(items=[]),
        lambda p: p["items"][0].update(id=True),
        lambda p: p["items"][0].update(job_id=124),
        lambda p: p["items"][0].update(organization_name="Other"),
        lambda p: p["items"][0].update(job_post_url="https://evil.com/example/123"),
    ],
)
def test_partial_unsafe_or_unidentified_collection_aborts(mutation):
    feed = collection()
    mutation(feed)
    with pytest.raises(ValueError):
        run(feed=feed)


def test_duplicate_ids_and_detail_budget_abort_before_details():
    for count in (2, 401):
        feed = collection()
        feed["items"] *= count
        feed["meta"]["count"] = count
        with pytest.raises(ValueError):
            run(feed=feed)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda p: p.update(id=True),
        lambda p: p.update(hash_id="Different"),
        lambda p: p.update(title="Other"),
        lambda p: p.update(organization_name="Other"),
        lambda p: p.update(job_application_description_url="https://evil.com/"),
        lambda p: p.update(archived_at="2026-11-01T00:00:00Z"),
        lambda p: p.update(closed_at="2026-11-01T00:00:00Z"),
        lambda p: p.pop("archived_at"),
        lambda p: p.pop("description"),
    ],
)
def test_mismatched_closed_or_malformed_detail_aborts(mutation):
    job = detail()
    mutation(job)
    with pytest.raises((ValueError, KeyError)):
        run(job=job)


def test_failures_and_changed_final_collection_abort():
    changed = collection()
    changed["items"][0]["title"] = "Changed"
    for kwargs in ({"status": 404}, {"confirm": changed}, {"robots": "User-agent: *\nDisallow: /"}):
        with pytest.raises(ValueError):
            run(**kwargs)


def test_detection_fixed_host_and_slug():
    assert detect(URL) == ("polymer", "example")
    for url in (
        "https://jobs.polymer.co/",
        "https://jobs.polymer.co.evil.com/example",
        "https://jobs.polymer.co/%2e%2e",
    ):
        with pytest.raises(ValueError):
            detect(url)

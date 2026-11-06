"""Hireology public endpoint boundaries, complete counts, metadata and failure regressions."""

import asyncio
import json

import httpx
import pytest
from vindex.connectors.registry import create_connector, detect

ORIGIN = "https://careers.hireology.com"
API = "https://api.hireology.com"


def board():
    d = {
        "apiUrl": API + "/v2",
        "appUrl": ORIGIN,
        "careersPath": "example",
        "page": None,
        "pageSize": None,
        "filters": {"location": [{"label": "London", "value": "London"}]},
        "apiToken": "MUST_NOT_USE_OR_RETAIN",
    }
    return (
        "<html><title>Jobs for Example</title><script>var startingData = "
        + json.dumps(d)
        + ";</script></html>"
    )


def row():
    return {
        "id": 12,
        "name": "Engineer",
        "created_at": "2026-11-01T10:00:00Z",
        "status": "Open",
        "employment_status": "Full Time - salary",
        "job_description": "<p>Build systems</p>",
        "locations": [{"city": "London", "state": "England", "address": "One Street"}],
        "remote": True,
        "blind_posted": False,
        "job_family": {"id": 1, "name": "Engineering"},
        "career_site_url": ORIGIN + "/example/12/description",
        "career_site_path": "/example/12/description",
        "application_path": "/careers/12/application",
        "organization": {"id": 7, "name": "Example", "type": "Company"},
        "compensation": {
            "is_comp_range": False,
            "comp_single_amount": "50000.0",
            "comp_range_min": "0.0",
            "comp_range_max": "0.0",
            "comp_period": "year",
            "comp_frequency": "monthly",
        },
        "third_party_service_data": {"indeed_apply": {"token": "DO_NOT_RETAIN"}},
    }


def collection(r=None):
    return {"data": [r or row()], "count": 1, "page": 1, "page_size": 10}


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.hireology.asyncio.sleep", no_wait)


def run(html=None, data=None, detail=None, confirm=None, status=200, deny=False):
    calls = 0

    async def discover():
        def handle(request):
            nonlocal calls
            assert "authorization" not in request.headers
            assert not request.url.query
            if request.url.path == "/robots.txt":
                return httpx.Response(
                    200,
                    text="User-agent: *\nDisallow: /v2/public/"
                    if deny and request.url.host == "api.hireology.com"
                    else "User-agent: *\nAllow: /",
                )
            if request.url.host == "careers.hireology.com":
                assert request.url.path == "/example"
                return httpx.Response(200, text=html or board())
            assert request.url.host == "api.hireology.com"
            assert request.url.path.startswith("/v2/public/careers/")
            if request.url.path == "/v2/public/careers/example":
                calls += 1
                return httpx.Response(
                    200, json=confirm if calls > 1 and confirm is not None else data or collection()
                )
            assert request.url.path == "/v2/public/careers/jobs/12"
            return httpx.Response(status, json={"data": detail or row()})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await create_connector("hireology", "example", "Configured", client).discover()

    return asyncio.run(discover())


def test_complete_public_endpoints_need_no_token_and_keep_source_metadata():
    batch = run()
    j = batch.jobs[0]
    assert batch.complete and j.company == "Example" and j.external_id == "12"
    assert j.description == "Build systems" and j.location == "One Street, London, England"
    assert j.remote_status == "remote" and j.employment_type == "Full Time - salary"
    assert j.published_at is None and j.raw["job"]["created_at"] == "2026-11-01T10:00:00Z"
    assert j.salary["source_compensation"]["comp_period"] == "year"
    assert "DO_NOT_RETAIN" not in j.model_dump_json() and "MUST_NOT_USE" not in j.model_dump_json()
    assert j.application_url == ORIGIN + "/example/12/description"
    assert detect(ORIGIN + "/example") == ("hireology", "example")


@pytest.mark.parametrize(
    "key,value", [("count", 0), ("count", 2), ("count", True), ("page", 2), ("page_size", 20)]
)
def test_partial_empty_or_unsupported_pagination_aborts(key, value):
    d = collection()
    d[key] = value
    with pytest.raises(ValueError):
        run(data=d)


@pytest.mark.parametrize(
    "key,value",
    [
        ("status", "Closed"),
        ("blind_posted", True),
        ("id", True),
        ("career_site_url", "https://evil.com/job"),
        ("application_path", "https://evil.com/apply"),
        ("organization", {"id": 8, "name": "Other"}),
    ],
)
def test_public_lifecycle_employer_and_links_must_match(key, value):
    r = row()
    r[key] = value
    with pytest.raises(ValueError):
        run(data=collection(r))


def test_complete_list_and_detail_must_agree():
    r = row()
    r["job_description"] = "<p>Changed</p>"
    with pytest.raises(ValueError):
        run(detail=r)


def test_changed_collection_aborts():
    r = row()
    r["locations"][0]["city"] = "Other"
    with pytest.raises(ValueError):
        run(confirm=collection(r))


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1", "not a number"])
def test_malformed_compensation_is_not_normalized(value):
    r = row()
    r["compensation"]["comp_single_amount"] = value
    with pytest.raises(ValueError):
        run(data=collection(r), detail=r)


def test_zero_compensation_and_false_remote_do_not_invent_pay_or_workplace():
    r = row()
    r["compensation"]["comp_single_amount"] = "0.0"
    r["remote"] = False
    j = run(data=collection(r), detail=r).jobs[0]
    assert j.salary is None and j.remote_status is None and j.raw["job"]["remote"] is False


def test_fetch_failure_is_not_empty_success():
    with pytest.raises(httpx.HTTPStatusError):
        run(status=503)


def test_robots_denial_aborts():
    with pytest.raises(ValueError):
        run(deny=True)


@pytest.mark.parametrize(
    "replacement",
    [
        ("https://api.hireology.com/v2", "https://evil.com/v2"),
        ('"page": null', '"page": 2'),
        ("Jobs for Example", "Unknown"),
        ("</html>", ""),
    ],
)
def test_bootstrap_must_match_named_native_unfiltered_site(replacement):
    with pytest.raises(ValueError):
        run(html=board().replace(*replacement))

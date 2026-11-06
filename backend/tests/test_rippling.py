"""Controlled Rippling complete public SSR and sanitized detail regressions."""

import asyncio
import copy
import json

import httpx
import pytest
from vindex.connectors.registry import create_connector, detect

KEY = "35d7cc5b-e7cf-4cab-94e5-28d7e6ec1c97"
ORIGIN = "https://ats.rippling.com"
PATH = f"/example/jobs/{KEY}"


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.rippling.asyncio.sleep", no_wait)


def board():
    return {
        "boardType": "RIPPLING",
        "slug": "example",
        "title": "Example Jobs",
        "boardURL": ORIGIN + "/example/jobs",
        "companyName": "Example",
        "isTest": False,
        "logo": {"url": "signed-asset-excluded"},
    }


def item():
    return {
        "id": KEY,
        "name": "Engineer ",
        "url": ORIGIN + PATH,
        "locations": [{"name": "London, UK", "workplaceType": "REMOTE"}],
    }


def listing_state():
    params = {
        "searchQuery": "",
        "departments": [],
        "workplaceType": None,
        "country": "",
        "state": "",
        "city": "",
        "page": 0,
        "pageSize": 20,
    }
    return {
        "apiData": {"jobBoard": board(), "jobBoardSlug": "example"},
        "dehydratedState": {
            "queries": [
                {
                    "queryKey": ["board", "example", "job-posts", True, params],
                    "state": {
                        "data": {
                            "items": [item()],
                            "page": 0,
                            "pageSize": 20,
                            "totalItems": 1,
                            "totalPages": 1,
                        }
                    },
                }
            ]
        },
    }


def detail_state():
    post = {
        "uuid": KEY,
        "name": "Engineer ",
        "url": ORIGIN + PATH,
        "companyName": "Example",
        "unlistedFromSearch": False,
        "board": board(),
        "description": {"company": "<p>About us</p>", "role": "<p>Build systems</p>"},
        "workLocations": ["London, UK"],
        "payRangeDetails": [],
        "employmentType": {"id": "Salaried, full-time", "label": "SALARIED_FT"},
        "createdOn": "2026-10-01T09:00:00Z",
        "jsonLd": None,
        "applicationConfirmationTemplate": "excluded-form-config",
    }
    return {"apiData": {"jobBoard": board(), "jobPost": post}}


def page(data):
    return (
        '<html><body><a href="'
        + PATH
        + '">Engineer</a><button>Apply now</button><script id="__NEXT_DATA__" type="application/json">'
        + json.dumps({"props": {"pageProps": data}})
        + "</script></body></html>"
    )


def run(listing=None, detail=None, confirm=None, status=200, robots="User-agent: *\nAllow: /"):
    calls = 0

    async def discover():
        def handler(request):
            nonlocal calls
            assert request.url.host == "ats.rippling.com" and not request.url.query
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text=robots)
            if request.url.path == "/example/jobs":
                calls += 1
                value = confirm if calls > 1 and confirm is not None else listing
                return httpx.Response(
                    200, text=page(value if value is not None else listing_state())
                )
            assert request.url.path == PATH
            return httpx.Response(
                status, text=page(detail if detail is not None else detail_state())
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await create_connector("rippling", "example", "Configured", client).discover()

    return asyncio.run(discover())


def test_complete_public_ssr_preserves_role_without_signed_assets_or_form_settings():
    batch = run()
    job = batch.jobs[0]
    assert (
        batch.complete
        and job.title == "Engineer"
        and job.external_id == KEY
        and job.company == "Example"
    )
    assert "Build systems" in job.description and "About us" in job.description
    assert job.location == "London, UK" and job.remote_status == "REMOTE"
    assert job.source_url == job.application_url == ORIGIN + PATH
    assert job.published_at is None and job.raw["job"]["createdOn"] == "2026-10-01T09:00:00Z"
    assert "logo" not in json.dumps(
        job.raw
    ) and "applicationConfirmationTemplate" not in json.dumps(job.raw)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d["apiData"]["jobBoard"].update(isTest=True),
        lambda d: d["apiData"]["jobBoard"].update(slug="other"),
        lambda d: d["dehydratedState"]["queries"][0]["state"]["data"].update(totalPages=2),
        lambda d: d["dehydratedState"]["queries"][0]["state"]["data"].update(totalItems=2),
        lambda d: d["dehydratedState"]["queries"][0]["state"]["data"].update(items=[]),
        lambda d: d["dehydratedState"]["queries"][0]["queryKey"][4].update(searchQuery="filtered"),
        lambda d: d["dehydratedState"]["queries"][0]["state"]["data"]["items"][0].update(
            url="https://evil.com/"
        ),
    ],
)
def test_partial_filtered_test_or_unsafe_collections_abort(mutation):
    value = copy.deepcopy(listing_state())
    mutation(value)
    with pytest.raises(ValueError):
        run(listing=value)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d["apiData"]["jobPost"].update(uuid="other"),
        lambda d: d["apiData"]["jobPost"].update(unlistedFromSearch=True),
        lambda d: d["apiData"]["jobPost"].update(companyName="Other"),
        lambda d: d["apiData"]["jobPost"].update(workLocations=["Paris"]),
        lambda d: d["apiData"]["jobPost"].update(description={"role": {"unknown": "shape"}}),
    ],
)
def test_wrong_unlisted_changed_or_partial_details_abort(mutation):
    value = copy.deepcopy(detail_state())
    mutation(value)
    with pytest.raises(ValueError):
        run(detail=value)


def test_changed_full_collection_request_failure_and_robots_denial_abort():
    changed = listing_state()
    changed["dehydratedState"]["queries"][0]["state"]["data"]["items"][0]["locations"][0][
        "workplaceType"
    ] = "HYBRID"
    for kwargs in ({"confirm": changed}, {"status": 404}, {"robots": "User-agent: *\nDisallow: /"}):
        with pytest.raises(ValueError):
            run(**kwargs)


def test_only_actual_source_posting_date_is_promoted():
    value = detail_state()
    value["apiData"]["jobPost"]["jsonLd"] = {"datePosted": "2026-11-01T09:00:00Z"}
    assert run(detail=value).jobs[0].published_at.month == 11
    assert detect(ORIGIN + PATH) == ("rippling", "example")
    for url in (ORIGIN + "/", "https://ats.rippling.com.evil.com/example/jobs"):
        with pytest.raises(ValueError):
            detect(url)

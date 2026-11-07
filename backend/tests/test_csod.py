"""CSOD anonymous sessions, full advertisements and complete native pagination."""

import asyncio
import json

import httpx
import pytest
from vindex.connectors.http import PublicHTTP, UpstreamStatusError
from vindex.connectors.registry import create_connector, detect

ORIGIN = "https://example.csod.com"
BASE = ORIGIN + "/ux/ats/careersite/1/home"
TOKEN = "public-browser-read-token-test"


def context():
    return {
        "corp": "example",
        "user": -100,
        "cultureName": "en-GB",
        "cultureID": 2,
        "serviceBase": "/",
        "applicationBase": "/",
        "token": TOKEN,
        "tracking": "EXCLUDED_TRACKING",
    }


def shell(ctx=None):
    return (
        "<html><script>if(!csod.context || !csod.context.token) csod.context="
        + json.dumps(ctx or context())
        + ";</script></html>"
    )


def wrapper(data, status=200):
    return {"status": status, "data": data}


def config():
    return wrapper(
        {
            "id": 1,
            "active": True,
            "anonymousUserId": -100,
            "currentLanguage": {"cultureId": 2, "cultureName": "en-GB"},
            "gtmContainerId": "EXCLUDED_TRACKING",
        }
    )


def listing(identifier=1):
    return {
        "requisitionId": identifier,
        "displayJobTitle": "Engineer",
        "postingEffectiveDate": "06/11/2026",
        "locations": [{"city": "London", "country": "GB"}],
    }


def search(total=1, page=1):
    return wrapper(
        {
            "totalCount": total,
            "requisitions": [listing(i + 1) for i in range((page - 1) * 25, min(page * 25, total))],
        }
    )


def detail(identifier=1):
    return wrapper(
        {
            "displayTitle": "Engineer",
            "externalDescription": "default",
            "ref": f"req{identifier}",
            "requisitionStatusId": 2,
            "allowApply": True,
            "primaryLocation": {"title": "London", "city": "London", "country": "GB"},
            "additionalLocations": [{"title": "Paris", "city": "Paris", "country": "FR"}],
            "companyApplyUrl": BASE + f"/requisition/{identifier}?c=example",
            "hiringManagerId": "EXCLUDED_PERSON",
            "owners": ["EXCLUDED_PERSON"],
            "reviewers": ["EXCLUDED_PERSON"],
        }
    )


def ad(identifier=1):
    return wrapper(
        [
            {
                "items": [
                    {
                        "fields": {
                            "id": identifier,
                            "reqId": f"req{identifier}",
                            "title": "Engineer",
                            "location": "London",
                            "ad": "<h2>Role</h2><p>Build systems</p><h2>Requirements</h2><p>Know Python</p><h2>Pay and benefits</h2><p>GBP 40000 a year</p>",
                            "description": "default",
                        },
                        "actions": ["EXCLUDED_ACTION"],
                    }
                ]
            }
        ]
    )


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.csod.asyncio.sleep", no_wait)


def run(
    total=1,
    ctx=None,
    site=None,
    page=None,
    record=None,
    advertisement=None,
    changed=False,
    status=200,
    robots="User-agent: *\nAllow: /",
):
    calls = 0

    async def discover():
        def handle(request):
            nonlocal calls
            assert request.url.host == "example.csod.com"
            path = request.url.path
            if path == "/robots.txt":
                assert "authorization" not in request.headers
                return httpx.Response(200, text=robots)
            if path == "/ux/ats/careersite/1/home":
                assert request.method == "GET" and "authorization" not in request.headers
                return httpx.Response(200, text=shell(ctx))
            assert request.headers["authorization"] == "Bearer " + TOKEN
            if path == "/services/x/career-site/v1/careersites/1":
                return httpx.Response(200, json=site or config())
            if path == "/services/x/career-site/v1/search":
                assert request.method == "POST"
                body = json.loads(request.content)
                assert body["searchText"] == "" and body["states"] == [] and body["pageSize"] == 25
                assert body["careerSiteId"] == 1 and body["cultureId"] == 2
                calls += 1
                data = page or search(total, body["pageNumber"])
                if changed and calls > 1:
                    data["data"]["requisitions"][0]["displayJobTitle"] = "Changed"
                return httpx.Response(200, json=data)
            if path.startswith("/services/x/job-requisition/v2/requisitions/"):
                identifier = int(path.split("/")[-2])
                assert identifier <= total and request.url.params["cultureId"] == "2"
                return httpx.Response(status, json=record or detail(identifier))
            assert path.startswith("/Services/API/ATS/CareerSite/1/JobRequisitions/")
            identifier = int(path.split("/")[-1])
            assert identifier <= total and request.url.params["useMobileAd"] == "false"
            return httpx.Response(200, json=advertisement or ad(identifier))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await create_connector(
                "csod", "example~1", "Configured Example", client
            ).discover()

    return asyncio.run(discover())


def test_full_ad_replaces_default_description_and_excludes_tokens_and_people_fields():
    result = run()
    assert result.complete and len(result.jobs) == 1
    job = result.jobs[0]
    assert "Know Python" in job.description and "GBP 40000 a year" in job.description
    assert job.description != "default" and job.title == "Engineer"
    assert job.company == "Configured Example" and job.quality_flags == [
        "company_from_source_configuration"
    ]
    assert job.location == "London, GB; Paris, FR" and job.published_at.month == 11
    assert job.application_url == BASE + "/requisition/1?c=example"
    assert TOKEN not in job.model_dump_json() and "EXCLUDED" not in job.model_dump_json()
    assert detect(BASE + "?c=example") == ("csod", "example~1")


def test_all_native_pages_and_both_success_envelopes():
    site = config()
    site["status"] = 0
    result = run(total=26, site=site)
    assert result.complete and len(result.jobs) == 26 and result.jobs[25].external_id == "26"


@pytest.mark.parametrize(
    "key,value",
    [
        ("user", 123),
        ("corp", "other"),
        ("serviceBase", "https://evil.test/"),
        ("applicationBase", "https://evil.test/"),
        ("token", ""),
        ("cultureName", "xx-XX"),
    ],
)
def test_nonanonymous_or_unbound_context_aborts(key, value):
    with pytest.raises(ValueError):
        run(ctx={**context(), key: value})


@pytest.mark.parametrize("key,value", [("active", False), ("id", 2), ("anonymousUserId", 123)])
def test_inactive_or_mismatched_site_fails(key, value):
    site = config()
    site["data"][key] = value
    with pytest.raises(ValueError):
        run(site=site)


@pytest.mark.parametrize("total", [0, 201, True])
def test_empty_or_oversized_count_aborts(total):
    with pytest.raises(ValueError):
        run(page=wrapper({"totalCount": total, "requisitions": []}))


def test_partial_duplicate_and_changed_enumerations_abort():
    data = search(2)
    data["data"]["requisitions"].pop()
    with pytest.raises(ValueError):
        run(page=data)
    data = search(2)
    data["data"]["requisitions"][1]["requisitionId"] = 1
    with pytest.raises(ValueError):
        run(total=2, page=data)
    with pytest.raises(ValueError):
        run(changed=True)


@pytest.mark.parametrize(
    "key,value",
    [
        ("displayTitle", "Other"),
        ("ref", "req2"),
        ("allowApply", False),
        ("companyApplyUrl", "https://evil.test/apply"),
        ("primaryLocation", {"city": "Other", "country": "FR"}),
        ("additionalLocations", None),
    ],
)
def test_required_public_details_abort_on_failure_or_mismatch(key, value):
    data = detail()
    data["data"][key] = value
    with pytest.raises(ValueError):
        run(record=data)


@pytest.mark.parametrize("key,value", [("id", 2), ("title", "Other"), ("ad", "")])
def test_full_native_ad_is_mandatory_and_identity_bound(key, value):
    data = ad()
    data["data"][0]["items"][0]["fields"][key] = value
    with pytest.raises(ValueError):
        run(advertisement=data)


def test_failed_mandatory_fetch_and_policy_denial_abort():
    with pytest.raises(UpstreamStatusError):
        run(status=404)
    with pytest.raises(ValueError):
        run(robots="User-agent: *\nDisallow: /services/")


@pytest.mark.parametrize(
    "url",
    [
        BASE + "?c=other",
        BASE + "?keyword=Engineer",
        BASE + "/requisition/1",
        BASE.replace("example.csod.com", "example.csod.com.evil.test"),
    ],
)
def test_registration_disallows_other_tenants_filters_and_job_urls(url):
    with pytest.raises(ValueError):
        detect(url)


def test_provider_header_is_request_scoped_and_cannot_override_host_or_escape_allowlist():
    async def check():
        requests = []

        def handle(request):
            requests.append(request)
            return httpx.Response(200, json={})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            http = PublicHTTP(client, {"example.csod.com"})
            await http.json(ORIGIN + "/public", headers={"Authorization": "Bearer " + TOKEN})
            await http.json(ORIGIN + "/robots.txt")
            with pytest.raises(ValueError):
                await http.json(
                    "https://evil.test/public", headers={"Authorization": "Bearer " + TOKEN}
                )
            with pytest.raises(ValueError):
                await http.json(ORIGIN + "/public", headers={"Host": "evil.test"})
        assert requests[0].headers["authorization"] == "Bearer " + TOKEN
        assert "authorization" not in requests[1].headers and len(requests) == 2

    asyncio.run(check())


def test_site_confirms_other_negative_anonymous_identity():
    ctx = {**context(), "user": -1}
    site = config()
    site["data"]["anonymousUserId"] = -1
    assert run(ctx=ctx, site=site).complete


def test_same_tenant_application_can_target_another_public_career_site_for_same_job():
    data = detail()
    url = ORIGIN + "/ux/ats/careersite/2/home/requisition/1?c=example"
    data["data"]["companyApplyUrl"] = url
    job = run(record=data).jobs[0]
    assert job.source_url == BASE + "/requisition/1?c=example" and job.application_url == url
    data["data"]["companyApplyUrl"] = url.replace("requisition/1", "requisition/2")
    with pytest.raises(ValueError):
        run(record=data)

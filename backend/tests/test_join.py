"""JOIN complete SSR pagination, stable IDs, public state and application checks."""

import asyncio
import json

import httpx
import pytest
from vindex.connectors.registry import create_connector, detect

ORIGIN = "https://join.com"
ROOT = "/companies/example"
SLUG = "90-engineer"
PATH = ROOT + "/" + SLUG


def company():
    return {"id": 7, "domain": "example", "name": "Example", "isPublic": True, "inReview": False}


def listing():
    return {
        "id": 12,
        "idParam": SLUG,
        "title": "Engineer",
        "createdAt": "2026-11-01T10:00:00Z",
        "workplaceType": "REMOTE",
        "city": {"cityName": "London", "countryName": "UK"},
        "employmentType": {"name": "Employee"},
        "country": {"iso3166": "GB"},
    }


def state():
    return {
        "company": company(),
        "jobs": {
            "items": [listing()],
            "filters": {},
            "pagination": {"page": 1, "pageCount": 1, "pageSize": 5, "perPage": 5, "total": 1},
        },
    }


def job():
    return {
        "id": 12,
        "idParam": SLUG,
        "companyId": 7,
        "company": company(),
        "title": "Engineer",
        "status": "ONLINE",
        "closedAt": None,
        "workplaceType": "REMOTE",
        "description": "<p>Build systems</p>",
        "contactName": "excluded",
    }


def schema():
    return {
        "@type": "JobPosting",
        "title": "Engineer",
        "description": "<p>Build systems</p>",
        "hiringOrganization": {"name": "Example", "url": ORIGIN + ROOT},
        "url": ORIGIN + PATH,
        "directApply": True,
        "employmentType": "FULL_TIME",
        "datePosted": "2026-11-01T10:00:00Z",
        "jobLocation": {"address": {"addressLocality": "London"}},
    }


def page(data, elements):
    value = {"props": {"pageProps": {"pageData": data}}}
    return (
        '<html><script id="__NEXT_DATA__" type="application/json">'
        + json.dumps(value)
        + "</script>"
        + elements
        + "</html>"
    )


def board(data=None):
    return page(data or state(), f'<h1>Example</h1><a href="{ORIGIN + PATH}">Engineer</a>')


def detail(data=None, ld=None):
    return page(
        data or {"company": company(), "job": job()},
        f'<h1>Engineer</h1><link rel="canonical" href="{ORIGIN + PATH}"><script type="application/ld+json">{json.dumps(ld or schema())}</script><button data-testid="ApplyButton">Apply now</button>',
    )


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.join.asyncio.sleep", no_wait)


def run(html=None, body=None, confirm=None, status=200, robots="User-agent: *\nAllow: /"):
    calls = 0

    async def discover():
        def handler(request):
            nonlocal calls
            assert request.url.host == "join.com"
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text=robots)
            if request.url.path == ROOT:
                assert request.url.query == b"page=1"
                calls += 1
                return httpx.Response(
                    200, text=confirm if calls > 1 and confirm is not None else html or board()
                )
            assert request.url.path == PATH and not request.url.query
            return httpx.Response(status, text=body or detail())

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await create_connector("join", "example", "Configured", client).discover()

    return asyncio.run(discover())


def test_complete_public_snapshot_uses_stable_job_id_not_rotating_ad_id():
    batch = run()
    j = batch.jobs[0]
    assert batch.complete and j.external_id == "12" and j.company == "Example"
    assert j.application_url == ORIGIN + PATH and j.title == "Engineer"
    assert j.description == "Build systems" and j.remote_status == "REMOTE"
    assert j.employment_type == "FULL_TIME" and j.published_at.year == 2026
    assert "contactName" not in j.model_dump_json()
    assert detect(ORIGIN + ROOT) == ("join", "example")


@pytest.mark.parametrize(
    "key,value",
    [
        ("page", 2),
        ("pageCount", 2),
        ("total", 0),
        ("total", 2),
        ("total", True),
        ("perPage", 10),
        ("pageSize", 0),
    ],
)
def test_incomplete_or_unsupported_pagination_aborts(key, value):
    s = state()
    s["jobs"]["pagination"][key] = value
    with pytest.raises(ValueError):
        run(html=board(s))


@pytest.mark.parametrize(
    "key,value", [("isPublic", False), ("inReview", True), ("domain", "other"), ("id", True)]
)
def test_company_public_identity_required(key, value):
    s = state()
    s["company"][key] = value
    with pytest.raises(ValueError):
        run(html=board(s))


@pytest.mark.parametrize(
    "key,value",
    [
        ("status", "OFFLINE"),
        ("closedAt", "2026-11-01"),
        ("id", 90),
        ("companyId", 8),
        ("idParam", "91-other"),
        ("title", "Other"),
        ("workplaceType", "ONSITE"),
    ],
)
def test_detail_lifecycle_or_identity_mismatch_aborts(key, value):
    j = job()
    j[key] = value
    with pytest.raises(ValueError):
        run(body=detail({"company": company(), "job": j}))


@pytest.mark.parametrize(
    "replacement",
    [
        ('data-testid="ApplyButton"', 'data-testid="Other"'),
        ('rel="canonical" href="https://join.com', 'rel="canonical" href="https://evil.com'),
        ("</html>", ""),
    ],
)
def test_missing_application_or_malformed_detail_aborts(replacement):
    with pytest.raises(ValueError):
        run(body=detail().replace(*replacement))


def test_changed_collection_aborts():
    with pytest.raises(ValueError):
        run(confirm=board().replace("REMOTE", "HYBRID"))


def test_request_failure_is_not_empty_success():
    with pytest.raises(httpx.HTTPStatusError):
        run(status=503)


def test_robots_denial_aborts():
    with pytest.raises(ValueError):
        run(robots="User-agent: *\nDisallow: /companies/example/90-engineer")


def test_detail_has_its_own_public_company_when_page_level_company_is_null():
    batch = run(body=detail({"company": None, "job": job()}))
    assert batch.complete and batch.jobs[0].company == "Example"

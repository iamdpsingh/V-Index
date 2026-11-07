"""Oracle anonymous published-job scope, complete pagination and external-only retention."""

import asyncio
from copy import deepcopy

import httpx
import pytest
from vindex.connectors.http import UpstreamStatusError
from vindex.connectors.oracle import OracleConnector
from vindex.connectors.registry import create_connector, detect

HOST = "example.fa.us2.oraclecloud.com"
ORIGIN = "https://" + HOST
BASE = ORIGIN + "/hcmUI/CandidateExperience/en/sites/CX"
API = "/hcmRestApi/resources/11.13.18.05/"
SHELL = '<html><script src="https://static.oracle.com/cdn/fa/oj-hcm-ce/version/js/main-minimal.js"></script></html>'


def sites():
    return {
        "hasMore": False,
        "count": 1,
        "items": [
            {
                "SiteName": "Example Careers",
                "SiteNumber": "CX",
                "SiteURLName": None,
                "StatusCode": "ORA_ACTIVE",
                "SeoOrganizationName": None,
            }
        ],
    }


def listing(identifier="1"):
    return {
        "Id": identifier,
        "Title": "Engineer",
        "PostedDate": "2026-10-01",
        "PrimaryLocation": "London",
        "PrimaryLocationCountry": "UK",
        "WorkplaceType": "Hybrid",
        "JobSchedule": None,
        "Language": "US",
    }


def search(total=1, offset=0):
    return {
        "hasMore": False,
        "count": 1,
        "items": [
            {
                "SiteNumber": "CX",
                "TotalJobsCount": total,
                "Offset": offset,
                "Limit": 100,
                "Keyword": None,
                "SelectedLocationsFacet": None,
                "requisitionList": [
                    listing(str(i + 1)) for i in range(offset, min(offset + 100, total))
                ],
            }
        ],
    }


def detail(identifier="1"):
    return {
        "hasMore": False,
        "count": 1,
        "items": [
            {
                **listing(identifier),
                "ExternalPostedStartDate": "2026-10-01T10:00:00Z",
                "JobSchedule": "Full time",
                "ApplyWhenNotPostedFlag": True,
                "ExternalDescriptionStr": "<p>Build systems. Salary GBP 40000.</p>",
                "ExternalQualificationsStr": "<p>Know Python</p>",
                "CorporateDescriptionStr": "<p>Benefits</p>",
                "secondaryLocations": [{"Name": "Paris"}],
                "workLocation": [{"TownOrCity": "London"}],
                "requisitionFlexFields": [],
                "InternalQualificationsStr": "EXCLUDED_INTERNAL",
                "InternalResponsibilitiesStr": "EXCLUDED_INTERNAL",
                "HiringManager": "EXCLUDED_CONTACT",
                "ExternalContactEmail": "EXCLUDED_CONTACT",
            }
        ],
    }


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.oracle.asyncio.sleep", no_wait)


def run(
    total=1,
    page=None,
    record=None,
    site=None,
    changed=False,
    status=200,
    robots="User-agent: *\nAllow: /",
):
    calls = 0

    async def discover():
        def handle(request):
            nonlocal calls
            assert request.url.host == HOST and request.method == "GET"
            assert "authorization" not in request.headers and "cookie" not in request.headers
            path = request.url.path
            if path == "/robots.txt":
                return httpx.Response(200, text=robots)
            if path == "/hcmUI/CandidateExperience/en/sites/CX/jobs":
                return httpx.Response(200, text=SHELL)
            if path == API + "recruitingCESites":
                return httpx.Response(200, json=site or sites())
            if path == API + "recruitingCEJobRequisitions":
                calls += 1
                offset = int(request.url.params["finder"].rsplit("=", 1)[1])
                data = deepcopy(page or search(total, offset))
                if changed and calls > 1:
                    data["items"][0]["requisitionList"][0]["Title"] = "Changed"
                return httpx.Response(200, json=data)
            assert path == API + "recruitingCEJobRequisitionDetails"
            assert request.url.params["expand"] == "all"
            finder = request.url.params["finder"]
            identifier = finder.split('"')[1]
            assert identifier in [str(i + 1) for i in range(total)]
            assert finder == f'ById;Id="{identifier}",siteNumber=CX'
            return httpx.Response(status, json=record or detail(identifier))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await create_connector(
                "oracle", HOST + "~CX", "Configured Example", client
            ).discover()

    return asyncio.run(discover())


def test_complete_published_roster_uses_full_external_only_details_and_configured_company():
    result = run()
    assert result.complete and len(result.jobs) == 1
    job = result.jobs[0]
    assert job.company == "Configured Example" and job.quality_flags == [
        "company_from_source_configuration"
    ]
    assert job.description == "Build systems. Salary GBP 40000.\n\nKnow Python\n\nBenefits"
    assert job.remote_status == "Hybrid" and job.employment_type == "Full time"
    assert job.location == "London; Paris" and job.published_at.year == 2026
    assert job.application_url == BASE + "/job/1" and job.source_url == job.application_url
    assert "EXCLUDED" not in job.model_dump_json()
    assert detect(BASE + "/jobs") == ("oracle", HOST + "~CX")


def test_complete_multi_page_collection_and_native_employer_metadata():
    site = sites()
    site["items"][0]["SeoOrganizationName"] = "Native Employer"
    result = run(total=101, site=site)
    assert result.complete and len(result.jobs) == 101
    assert result.jobs[100].external_id == "101" and result.jobs[0].company == "Native Employer"
    assert result.jobs[0].quality_flags == []


@pytest.mark.parametrize(
    "key,value",
    [
        ("TotalJobsCount", 0),
        ("TotalJobsCount", 401),
        ("TotalJobsCount", True),
        ("TotalJobsCount", 2),
        ("Offset", 100),
        ("Limit", 10),
        ("SiteNumber", "PRIVATE"),
        ("SelectedLocationsFacet", "123"),
        ("Keyword", "Engineer"),
    ],
)
def test_incomplete_or_filtered_search_aborts(key, value):
    page = search()
    page["items"][0][key] = value
    with pytest.raises(ValueError):
        run(page=page)


def test_duplicate_ids_partial_wrapper_and_changed_final_roster_abort():
    page = search(2)
    page["items"][0]["requisitionList"][1]["Id"] = "1"
    with pytest.raises(ValueError):
        run(total=2, page=page)
    with pytest.raises(ValueError):
        run(page={**search(), "hasMore": True})
    with pytest.raises(ValueError):
        run(changed=True)


@pytest.mark.parametrize(
    "key,value",
    [
        ("Title", "Other"),
        ("PrimaryLocation", "Paris"),
        ("Id", "2"),
        ("ExternalPostedStartDate", "2026-09-01T00:00:00Z"),
        ("secondaryLocations", None),
        ("ExternalDescriptionStr", 7),
    ],
)
def test_missing_or_mismatched_full_public_details_abort(key, value):
    data = detail()
    data["items"][0][key] = value
    with pytest.raises(ValueError):
        run(record=data)


@pytest.mark.parametrize("key,value", [("StatusCode", "ORA_INACTIVE"), ("SiteNumber", "OTHER")])
def test_inactive_or_unbound_sites_abort(key, value):
    data = sites()
    data["items"][0][key] = value
    with pytest.raises(ValueError):
        run(site=data)


def test_failed_detail_and_robots_denial_never_reconcile_empty_jobs():
    with pytest.raises(UpstreamStatusError):
        run(status=404)
    with pytest.raises(ValueError):
        run(robots="User-agent: *\nDisallow: /hcmRestApi/")


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.com/hcmUI/CandidateExperience/en/sites/CX",
        BASE + "?keyword=x",
        BASE + "/job/1",
        BASE.replace("/en/", "/fr/"),
        BASE.replace(HOST, "localhost"),
        BASE.replace(".oraclecloud.com", ".oraclecloud.com.evil.test"),
    ],
)
def test_source_hosts_and_paths_bound_to_public_native_english_site(url):
    with pytest.raises(ValueError):
        detect(url)


def test_constructor_rejects_private_hosts_and_site_parameter_injection():
    with pytest.raises(ValueError):
        OracleConnector("oracle", "localhost~CX", "Example", httpx.AsyncClient())
    with pytest.raises(ValueError):
        OracleConnector("oracle", HOST + "~CX,keyword=private", "Example", httpx.AsyncClient())

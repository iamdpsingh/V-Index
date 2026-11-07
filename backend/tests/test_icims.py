"""Classic iCIMS public pagination, full text and application-entry safeguards."""

import asyncio
import json

import httpx
import pytest
from vindex.connectors.http import UpstreamStatusError
from vindex.connectors.registry import create_connector, detect

ORIGIN = "https://careers-example.icims.com"


def url(identifier=1):
    return ORIGIN + f"/jobs/{identifier}/engineer/job"


def fields():
    return '<dl><div class="iCIMS_JobHeaderTag"><dt class="iCIMS_JobHeaderField">Work Site</dt><dd class="iCIMS_JobHeaderData">Remote</dd></div></dl>'


def card(identifier=1):
    return (
        '<li class="iCIMS_JobCardItem"><div class="row"><div class="title"><a href="'
        + url(identifier)
        + '?in_iframe=1" title="'
        + str(identifier)
        + ' - Engineer"><h3>Engineer</h3></a></div>'
        + fields()
        + "</div></li>"
    )


def board(page=0, pages=1, identifiers=None):
    ids = identifiers if identifiers is not None else [1]
    return (
        f'<html><title>Job Listings at Example</title><h1 class="iCIMS_Header">Job Listings</h1><h2 class="iCIMS_SubHeader_Jobs">Search Results Page {page + 1} of {pages}</h2><ul class="iCIMS_JobsTable">'
        + "".join(card(i) for i in ids)
        + "</ul></html>"
    )


def sections():
    return '<div class="iCIMS_InfoMsg_Job"><h2>Responsibilities</h2><div class="iCIMS_Expandable_Text">Build systems</div></div><div class="iCIMS_InfoMsg_Job"><h2>Qualifications</h2><div class="iCIMS_Expandable_Text">Know Python</div></div><div class="iCIMS_InfoMsg_Job"><h2>Pay Range</h2><div class="iCIMS_Expandable_Text">GBP 40000 - 50000 a year</div></div>'


def posting(identifier=1):
    return {
        "@type": "JobPosting",
        "title": "Engineer",
        "url": url(identifier),
        "description": sections(),
        "hiringOrganization": {"name": "Example Ltd"},
        "jobLocation": [
            {
                "address": {
                    "addressLocality": "London",
                    "addressRegion": "UNAVAILABLE",
                    "postalCode": "UNAVAILABLE",
                    "addressCountry": "GB",
                }
            }
        ],
        "employmentType": "FULL_TIME",
        "datePosted": "2026-11-01T10:00:00Z",
    }


def detail(identifier=1, row=None):
    return (
        '<html><link rel="canonical" href="'
        + url(identifier)
        + '"><script type="application/ld+json">'
        + json.dumps(row or posting(identifier))
        + '</script><h1 class="iCIMS_Header">Engineer</h1><div class="iCIMS_JobContent">'
        + fields()
        + sections()
        + '</div><a href="'
        + url(identifier)
        + '?mode=apply&amp;apply=yes&amp;in_iframe=1&amp;hashed=ROTATING_VALUE">Apply for this job</a></html>'
    )


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.icims.asyncio.sleep", no_wait)


def run(
    listing=None, page=None, confirm=None, total=1, status=200, robots="User-agent: *\nAllow: /"
):
    calls = 0

    async def discover():
        def handle(request):
            nonlocal calls
            assert request.url.host == "careers-example.icims.com" and request.method == "GET"
            assert "authorization" not in request.headers
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text=robots)
            if request.url.path == "/jobs/search":
                calls += 1
                p = int(request.url.params["pr"])
                assert dict(request.url.params) == {
                    "pr": str(p),
                    "in_iframe": "1",
                    "searchRelation": "keyword_all",
                }
                ids = list(range(p * 50 + 1, min(total, (p + 1) * 50) + 1))
                text = (
                    confirm
                    if calls > 1 and confirm is not None
                    else listing or board(p, (total + 49) // 50, ids)
                )
                return httpx.Response(200, text=text)
            identifier = int(request.url.path.split("/")[2])
            assert 1 <= identifier <= total and dict(request.url.params) == {"in_iframe": "1"}
            return httpx.Response(status, text=page or detail(identifier))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await create_connector(
                "icims", "careers-example", "Configured", client
            ).discover()

    return asyncio.run(discover())


def test_full_public_native_details_locations_salary_workplace_and_stable_apply_entry():
    result = run()
    assert result.complete and len(result.jobs) == 1
    job = result.jobs[0]
    assert (
        job.company == "Example Ltd"
        and job.description
        == "Responsibilities Build systems Qualifications Know Python Pay Range GBP 40000 - 50000 a year"
    )
    assert job.salary == {"text": "GBP 40000 - 50000 a year"} and job.remote_status == "Remote"
    assert job.employment_type == "FULL_TIME" and job.location == "London, GB"
    assert job.source_url == url() and job.application_url == url()
    assert job.published_at.year == 2026 and "ROTATING_VALUE" not in job.model_dump_json()
    assert detect(ORIGIN + "/jobs/search?ss=1") == ("icims", "careers-example")


def test_all_fifty_item_pages_required():
    result = run(total=51)
    assert result.complete and len(result.jobs) == 51 and result.jobs[-1].external_id == "51"


@pytest.mark.parametrize(
    "old,new",
    [
        ("Page 1 of 1", "Page 2 of 1"),
        ("Page 1 of 1", "Page 1 of 9"),
        ("</html>", ""),
        ("Job Listings at Example", "Other"),
        ("Job Listings</h1>", "Other</h1>"),
        (url(), "https://evil.test/jobs/1/engineer/job"),
        ("/engineer/job", "/%2f..%2fprivate/job"),
    ],
)
def test_unsupported_partial_or_unsafe_listings_fail(old, new):
    with pytest.raises(ValueError):
        run(listing=board().replace(old, new))


def test_incomplete_nonfinal_page_duplicates_and_changed_roster_fail():
    with pytest.raises(ValueError):
        run(total=51, listing=board(0, 2, [1]))
    with pytest.raises(ValueError):
        run(listing=board(identifiers=[1, 1]))
    with pytest.raises(ValueError):
        run(confirm=board().replace("Engineer", "Changed"))


@pytest.mark.parametrize(
    "key,value",
    [
        ("title", "Other"),
        ("url", "https://evil.test/job"),
        ("description", "Partial"),
        ("hiringOrganization", {"name": ""}),
        ("jobLocation", []),
    ],
)
def test_mandatory_structured_identity_full_text_and_locations_fail(key, value):
    with pytest.raises(ValueError):
        run(page=detail(row={**posting(), key: value}))


@pytest.mark.parametrize(
    "old,new",
    [
        ('rel="canonical"', 'rel="other"'),
        ('class="iCIMS_Header">Engineer', 'class="iCIMS_Header">Other'),
        ("mode=apply", "mode=other"),
        (
            'Work Site</dt><dd class="iCIMS_JobHeaderData">Remote',
            'Work Site</dt><dd class="iCIMS_JobHeaderData">Hybrid',
        ),
    ],
)
def test_canonical_apply_and_native_field_validation(old, new):
    with pytest.raises(ValueError):
        run(page=detail().replace(old, new))


def test_failed_required_detail_and_robots_denial_abort():
    with pytest.raises(UpstreamStatusError):
        run(status=404)
    with pytest.raises(ValueError):
        run(robots="User-agent: *\nDisallow: /jobs/")


@pytest.mark.parametrize(
    "url",
    [
        ORIGIN + "/jobs/search?keyword=Engineer",
        ORIGIN + "/jobs/search?in_iframe=1",
        ORIGIN + "/jobs/login",
        ORIGIN + "/jobs/1/engineer/job",
        ORIGIN.replace(".icims.com", ".icims.com.evil.test") + "/jobs/search",
    ],
)
def test_registration_does_not_accept_filters_auth_job_urls_or_foreign_hosts(url):
    with pytest.raises(ValueError):
        detect(url)


def test_native_sibling_section_headings_are_preserved_with_their_full_text():
    original = detail()
    native = original.replace('<div class="iCIMS_InfoMsg_Job"><h2>', "<h2>").replace(
        '</h2><div class="iCIMS_Expandable_Text">',
        '</h2><div class="iCIMS_InfoMsg_Job"><div class="iCIMS_Expandable_Text">',
    )
    job = run(page=native).jobs[0]
    assert "Qualifications Know Python" in job.description and job.salary["text"].startswith("GBP")


def test_structured_schema_may_join_adjacent_blocks_but_native_text_is_complete():
    row = posting()
    row["description"] = (
        "ResponsibilitiesBuild systemsQualificationsKnow PythonPay RangeGBP 40000 - 50000 a year"
    )
    assert "Qualifications Know Python" in run(page=detail(row=row)).jobs[0].description


def test_explicit_practice_posting_is_validated_but_not_counted_as_employment():
    from vindex.connectors.icims import ICIMSConnector

    native = (
        detail()
        .replace("Engineer", "PRACTICE: Resume review")
        .replace("Build systems", "It is not a real job opening and no one will be hired from it.")
    )
    connector = ICIMSConnector("icims", "careers-example", "", httpx.AsyncClient())
    result = connector.parse(
        (
            "1",
            {"title": "PRACTICE: Resume review", "url": url() + "?in_iframe=1", "fields": {}},
            "Example",
            native.encode(),
        )
    )
    assert result == []


def test_rich_text_subheading_does_not_replace_the_native_sibling_field_heading():
    from vindex.connectors.icims import ICIMSConnector

    native_sections = '<h2>Overview</h2><div class="iCIMS_InfoMsg_Job"><div class="iCIMS_Expandable_Text"><h2>About us</h2><p>Build systems</p></div></div>'
    row = posting()
    row["description"] = "Overview About us Build systems"
    page = detail(row=row).replace(sections(), native_sections)
    connector = ICIMSConnector("icims", "careers-example", "", httpx.AsyncClient())
    job = connector.parse(
        (
            "1",
            {"url": url() + "?in_iframe=1", "title": "Engineer", "fields": {}},
            "Example",
            page.encode(),
        )
    )[0]
    assert job.description == "Overview About us Build systems"

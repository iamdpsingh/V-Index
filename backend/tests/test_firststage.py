"""FirstStage full-count SSR enumeration and native detail identity regressions."""

import asyncio
import json

import httpx
import pytest
from vindex.connectors.http import UpstreamStatusError
from vindex.connectors.registry import create_connector, detect

BASE = "https://example.firststage.co/jobs"
NATIVE = BASE + "/abcdefgh12/view"
URL = NATIVE + "?layout=list"


def metadata(url):
    return (
        f'<meta property="og:url" content="{url}"><meta property="og:site_name" content="Example">'
    )


def badges():
    return '<span><svg class="lucide-map-pin"></svg>London</span><span><svg class="lucide-briefcase"></svg>full time</span><span><svg class="lucide-building-2"></svg>hybrid</span>'


def link():
    return f'<a href="{URL}"><span>Engineer</span><span>{badges()}</span></a>'


def board():
    return (
        "<html>"
        + metadata(BASE)
        + "<h1>Jobs at Example</h1><h2>1 job open</h2>"
        + link()
        + link()
        + "</html>"
    )


def posting():
    return {
        "@type": "JobPosting",
        "title": "Engineer",
        "description": "<p>Build systems</p>",
        "directApply": NATIVE,
        "datePosted": "2026-10-01T00:00:00Z",
        "hiringOrganization": {"name": "Example"},
        "jobLocation": {"address": "London"},
        "baseSalary": {"currency": "GBP", "value": {"minValue": 40000}},
        "incentiveCompensation": "Stock",
    }


def page(row=None):
    return (
        "<html>"
        + metadata(NATIVE + "?")
        + '<script type="application/ld+json">'
        + json.dumps(row or posting())
        + "</script><h1><div>Apply for</div><div>Engineer</div><div>"
        + badges()
        + '</div></h1><div class="prose"><p>Build systems</p></div><a href="#apply">Apply Now</a><div id="apply"><input type="file" name="candidate-secret"><button>Choose file</button></div></html>'
    )


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.firststage.asyncio.sleep", no_wait)


def run(listing=None, detail=None, confirm=None, status=200, robots="User-agent: *\nAllow: /"):
    calls = 0

    async def discover():
        def handle(request):
            nonlocal calls
            assert request.url.host == "example.firststage.co" and request.method == "GET"
            assert "authorization" not in request.headers
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text=robots)
            if str(request.url) == BASE:
                calls += 1
                return httpx.Response(
                    200, text=confirm if calls > 1 and confirm is not None else listing or board()
                )
            assert str(request.url) == URL
            return httpx.Response(status, text=detail or page())

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await create_connector("firststage", "example", "Configured", client).discover()

    return asyncio.run(discover())


def test_exact_repeated_group_ids_are_one_job_with_original_links_and_metadata():
    result = run()
    assert result.complete and len(result.jobs) == 1
    job = result.jobs[0]
    assert job.title == "Engineer" and job.company == "Example"
    assert job.description == "Build systems" and job.location == "London"
    assert job.remote_status == "hybrid" and job.employment_type == "full time"
    assert job.source_url == URL and job.application_url == NATIVE + "#apply"
    assert (
        job.salary["structured"]["currency"] == "GBP"
        and job.salary["incentiveCompensation"] == "Stock"
    )
    assert job.published_at.year == 2026
    assert "candidate-secret" not in job.model_dump_json()
    assert detect(BASE) == ("firststage", "example")


@pytest.mark.parametrize(
    "old,new",
    [
        ("1 job open", "2 jobs open"),
        ("1 job open", "0 jobs open"),
        ("Jobs at Example", "Jobs at Other"),
        ("</html>", ""),
        (URL, "https://evil.test/jobs/abcdefgh12/view?layout=list"),
        ("</html>", '<a rel="next" href="?page=2">Next</a></html>'),
        (BASE + '"><meta', 'https://evil.test"><meta'),
    ],
)
def test_incomplete_unbound_or_unsafe_board_rejected(old, new):
    with pytest.raises(ValueError):
        run(listing=board().replace(old, new))


def test_conflicting_grouped_observation_rejected():
    with pytest.raises(ValueError):
        run(listing=board().replace(link(), link().replace("Engineer", "Other"), 1))


@pytest.mark.parametrize(
    "key,value",
    [
        ("title", "Other"),
        ("hiringOrganization", {"name": "Other"}),
        ("directApply", "https://evil.test/apply"),
        ("description", "Different"),
        ("jobLocation", {"address": "Paris"}),
    ],
)
def test_mismatched_mandatory_detail_rejected(key, value):
    with pytest.raises(ValueError):
        run(detail=page({**posting(), key: value}))


@pytest.mark.parametrize(
    "old,new",
    [
        ('id="apply"', 'id="other"'),
        ('type="file"', 'type="text"'),
        ('href="#apply"', 'href="#other"'),
        ('class="prose"', 'class="other"'),
        ("<div>Engineer</div>", "<div>Other</div>"),
        ('og:site_name" content="Example', 'og:site_name" content="Other'),
    ],
)
def test_missing_public_application_or_full_detail_aborts(old, new):
    with pytest.raises(ValueError):
        run(detail=page().replace(old, new))


def test_changed_board_failed_detail_and_policy_denial_abort():
    with pytest.raises(ValueError):
        run(confirm=board().replace("Engineer", "Changed"))
    with pytest.raises(UpstreamStatusError):
        run(status=404)
    with pytest.raises(ValueError):
        run(robots="User-agent: *\nDisallow: /jobs")


@pytest.mark.parametrize(
    "url",
    [
        BASE + "?location=London",
        BASE + "/abcdefgh12/view",
        BASE + "#jobs",
        "https://example.firststage.co:444/jobs",
    ],
)
def test_source_registration_disallows_filters_detail_urls_and_ports(url):
    with pytest.raises(ValueError):
        detect(url)


def test_multiple_locations_preserved_and_grouped_listing_confirmed():
    extra = '<span><svg class="lucide-map-pin"></svg>Paris</span>'
    listing = board().replace(badges(), badges() + extra)
    row = {**posting(), "jobLocation": {"address": "London, Paris"}}
    detail = page(row).replace(badges(), badges() + extra)
    job = run(listing=listing, detail=detail).jobs[0]
    assert (
        job.location == "London; Paris"
        and job.raw["jobposting"]["jobLocation"]["address"] == "London, Paris"
    )

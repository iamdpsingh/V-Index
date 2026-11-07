"""Native PageUp remaining counters, complete pagination and scoped application links."""

import asyncio

import httpx
import pytest
from vindex.connectors.http import UpstreamStatusError
from vindex.connectors.registry import create_connector, detect

ORIGIN = "https://careers.pageuppeople.com"
BASE = ORIGIN + "/123/cw/en"


def url(identifier=1):
    return BASE + f"/job/{identifier}/engineer"


def row(identifier=1):
    return f'<tr><td><a class="job-link" href="/123/cw/en/job/{identifier}/engineer">Engineer</a></td><td><span class="location">London</span></td><td><span class="close-date"><time datetime="2026-12-01T00:00:00Z">1 Dec</time></span></td></tr>'


def board(page=1, total=1):
    rows = "".join(row(i + 1) for i in range((page - 1) * 20, min(page * 20, total)))
    remaining = max(0, total - page * 20)
    more = (
        f'<a class="more-link" data-page="{page + 1}" data-page-items="20" href="/123/cw/en/listing/?page={page + 1}&amp;page-items=20">More Jobs <span class="count">{remaining}</span></a>'
        if remaining
        else ""
    )
    content = "<table>" + rows + "</table>" + more
    return (
        '<html><title>Current Opportunities - Example</title><div id="recent-jobs">'
        + content
        + '</div><div id="search-results">'
        + content
        + "</div></html>"
    )


def detail(identifier=1):
    apply = f"https://secure.dc2.pageuppeople.com/apply/123/gateway/default.aspx?c=apply&amp;lJobID={identifier}&amp;lJobSourceTypeID=796&amp;sLanguage=en"
    return (
        '<html><link rel="canonical" href="'
        + url(identifier)
        + '"><meta property="og:title" content="Engineer"><div id="job-content"><h2>Engineer</h2><span class="job-externalJobNo">'
        + str(identifier)
        + '</span><span class="location">London</span><span class="work-type">Permanent - Full-time</span><div id="job-details"><p>Build systems</p><p>Know Python</p><ul><li>Salary Range: GBP 40000 - 50000 a year</li></ul></div><span class="open-date"><time datetime="2026-11-01T10:00:00Z">1 Nov</time></span><span class="close-date"><time datetime="2026-12-01T00:00:00Z">1 Dec</time></span><a class="apply-link" href="'
        + apply
        + '">Apply now</a></div></html>'
    )


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.pageup.asyncio.sleep", no_wait)


def run(
    total=1, listing=None, content=None, changed=False, status=200, robots="User-agent: *\nAllow: /"
):
    calls = 0

    async def discover():
        def handle(request):
            nonlocal calls
            assert request.url.host == "careers.pageuppeople.com" and request.method == "GET"
            assert "authorization" not in request.headers
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text=robots)
            if request.url.path == "/123/cw/en/listing/":
                calls += 1
                page = int(request.url.params.get("page", "1"))
                assert (
                    not request.url.query
                    if page == 1
                    else dict(request.url.params) == {"page": str(page), "page-items": "20"}
                )
                text = listing or board(page, total)
                if changed and calls > 1:
                    text = text.replace("Engineer", "Changed")
                return httpx.Response(200, text=text)
            identifier = int(request.url.path.split("/")[-2])
            assert 1 <= identifier <= total
            return httpx.Response(status, text=content or detail(identifier))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await create_connector("pageup", "123~en", "Example", client).discover()

    return asyncio.run(discover())


def test_native_full_details_and_original_salary_dates_employment_and_apply_link():
    result = run()
    assert result.complete and len(result.jobs) == 1
    job = result.jobs[0]
    assert job.description == "Build systems Know Python Salary Range: GBP 40000 - 50000 a year"
    assert job.salary == {"text": "Salary Range: GBP 40000 - 50000 a year"}
    assert job.title == "Engineer" and job.company == "Example" and job.location == "London"
    assert job.employment_type == "Permanent - Full-time" and job.remote_status is None
    assert job.published_at.year == 2026 and job.source_url == url()
    assert job.application_url.startswith("https://secure.dc2.pageuppeople.com/apply/123/")
    assert job.quality_flags == ["company_from_source_configuration"]
    assert detect(BASE + "/listing/") == ("pageup", "123~en")


def test_every_page_matches_explicit_remaining_counter_and_duplicate_widget_is_not_counted_twice():
    result = run(total=21)
    assert result.complete and len(result.jobs) == 21 and result.jobs[-1].external_id == "21"


@pytest.mark.parametrize(
    "old,new",
    [
        ("</html>", ""),
        ('id="recent-jobs"', 'id="other"'),
        ('id="search-results"', 'id="other"'),
        ("/123/cw/en/job/1/engineer", "/999/cw/en/job/1/engineer"),
        ('class="location"', 'class="other"'),
    ],
)
def test_unsupported_or_unbound_native_listing_fails(old, new):
    with pytest.raises(ValueError):
        run(listing=board().replace(old, new))


def test_duplicate_disagreeing_widget_and_partial_pagination_fail():
    listing = board().replace(
        'id="search-results"><table>' + row(),
        'id="search-results"><table>' + row().replace("Engineer", "Other"),
    )
    with pytest.raises(ValueError):
        run(listing=listing)
    with pytest.raises(ValueError):
        run(listing=board().replace(row(), row() + row()))
    with pytest.raises(ValueError):
        run(listing=board(total=21).replace('data-page="2"', 'data-page="3"'))
    with pytest.raises(ValueError):
        run(listing=board(total=21).replace(row(1), ""))
    with pytest.raises(ValueError):
        run(listing=board(total=201))


@pytest.mark.parametrize(
    "old,new",
    [
        (url(), "https://evil.test/job"),
        ('og:title" content="Engineer', 'og:title" content="Other'),
        ("<h2>Engineer</h2>", "<h2>Other</h2>"),
        ('job-externalJobNo">1', 'job-externalJobNo">'),
        ('location">London', 'location">Paris'),
        ('id="job-details"', 'id="other"'),
        ("work-type", "other"),
        ("2026-12-01", "2026-12-02"),
        ("secure.dc2.pageuppeople.com", "evil.test"),
        ("/apply/123/", "/apply/999/"),
        ("lJobID=1", "lJobID=2"),
        ('class="apply-link"', 'class="other"'),
    ],
)
def test_required_detail_metadata_full_description_and_apply_scope_fail(old, new):
    with pytest.raises(ValueError):
        run(content=detail().replace(old, new))


def test_failed_fetch_policy_denial_and_changed_final_roster_abort():
    with pytest.raises(UpstreamStatusError):
        run(status=404)
    with pytest.raises(ValueError):
        run(robots="User-agent: *\nDisallow: /123/")
    with pytest.raises(ValueError):
        run(changed=True)


@pytest.mark.parametrize(
    "url",
    [
        BASE + "/listing/?page=2",
        BASE + "/search/?search-keyword=Engineer",
        BASE + "/job/1/engineer",
        BASE.replace("/cw/", "/internal/") + "/listing/",
        BASE.replace("careers.pageuppeople.com", "careers.pageuppeople.com.evil.test")
        + "/listing/",
    ],
)
def test_registration_rejects_filters_details_nonpublic_site_paths_and_foreign_host(url):
    with pytest.raises(ValueError):
        detect(url)


def test_external_requisition_number_is_distinct_from_native_job_url_id():
    job = run(content=detail().replace('job-externalJobNo">1', 'job-externalJobNo">H1')).jobs[0]
    assert job.external_id == "1" and job.raw["external_job_number"] == "H1"
    assert job.source_url == url()

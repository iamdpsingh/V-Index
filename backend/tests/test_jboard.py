"""Native JBoard pages must fully agree with sitemaps; partial/error data never completes."""

import asyncio
import json

import httpx
import pytest
from vindex.connectors.jboard import JBoardConnector
from vindex.connectors.registry import create_connector, detect

HOST = "jobs.aame.org"
ORIGIN = "https://" + HOST
NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


def url(i):
    return ORIGIN + f"/jobs/{i}-engineer"


def index():
    return f'<sitemapindex xmlns="{NS}"><sitemap><loc>{ORIGIN}/sitemap-jobs-1.xml</loc></sitemap><sitemap><loc>{ORIGIN}/sitemap-companies-1.xml</loc></sitemap></sitemapindex>'


def jobmap(ids):
    return (
        f'<urlset xmlns="{NS}">'
        + "".join("<url><loc>" + url(i) + "</loc></url>" for i in ids)
        + "</urlset>"
    )


def card(i):
    return f'<div class="job-listings-item" data-jobid="{i}"><a class="job-details-link" href="/jobs/{i}-engineer">Engineer {i}</a><a class="job-info-link-item" href="/companies/employer-{i}">Employer {i}</a><a class="job-info-link-item" href="/jobs/in-hamilton">Hamilton</a><div class="job-tags"><a>Full-time</a></div><a href="/jobs/{i}/apply">Apply</a></div>'


def board(ids, next_page=None):
    more = f'<a rel="next" href="/jobs?page={next_page}">Next</a>' if next_page else ""
    return "<html>" + "".join(card(i) for i in ids) + more + "</html>"


def detail(i, **change):
    native_html = change.pop("native_html", "<p>Build reliable systems.</p>")
    row = {
        "@type": "JobPosting",
        "title": f"Engineer {i}",
        "identifier": {"value": str(i)},
        "hiringOrganization": {"name": f"Employer {i}"},
        "description": native_html,
        "jobLocation": {"address": {"addressCountry": "Bermuda", "addressRegion": "Hamilton"}},
        "datePosted": "2026-11-01T00:00:00Z",
        "validThrough": "2027-01-01T00:00:00Z",
        "employmentType": "FULL_TIME",
        "jobLocationType": "TELECOMMUTE",
        "baseSalary": {"currency": "USD", "value": {"minValue": "100000", "unitText": "YEAR"}},
    }
    row.update(change)
    return (
        '<html><link rel="canonical" href="'
        + url(i)
        + '"><script type="application/ld+json">'
        + json.dumps(row)
        + f'</script><aside class="job-inner-left"><h1>Engineer {i}</h1><a href="/companies/employer-{i}">Employer {i}</a><div id="quill-container-with-job-details">{native_html}</div></aside><div class="job-inner-btn-box"><a href="/jobs/{i}/apply">Apply for this job</a></div></html>'
    )


def run(total=1, change=None):
    maps = 0

    async def main():
        def handler(request):
            nonlocal maps
            assert request.url.host == HOST and request.method == "GET"
            path = request.url.path
            assert (
                not path.endswith("/apply")
                and "/api/" not in path
                and "Authorization" not in request.headers
            )
            if path == "/robots.txt":
                return httpx.Response(
                    200, text="User-agent: *\nAllow: /\nSitemap: " + ORIGIN + "/sitemap.xml"
                )
            if path == "/sitemap.xml":
                return httpx.Response(200, text=index())
            if path == "/sitemap-jobs-1.xml":
                maps += 1
                ids = list(range(1, total + 1))
                if change == "map_mismatch" or change == "changed" and maps > 1:
                    ids.append(999)
                body = jobmap(ids)
                if change == "broken_xml":
                    body = body[:-10]
                if change == "cross_host":
                    body = body.replace(HOST, "private.invalid")
                return httpx.Response(200, text=body)
            if path == "/jobs":
                page = int(request.url.params.get("page", "1"))
                ids = list(range((page - 1) * 30 + 1, min(page * 30, total) + 1))
                nxt = page + 1 if page * 30 < total else None
                if change == "skip_page":
                    nxt = 3
                if change == "repeat_page" and page == 2:
                    ids = [1]
                body = board(ids, nxt)
                if change == "truncated":
                    body = body.replace("</html>", "")
                if change == "missing_apply":
                    body = body.replace("/jobs/1/apply", "/jobs/2/apply")
                return httpx.Response(200, text=body)
            i = int(path.split("/")[2].split("-")[0])
            assert 1 <= i <= total
            if change == "fetch_failure":
                return httpx.Response(403)
            if change == "redirect":
                return httpx.Response(302, headers={"Location": "https://private.invalid"})
            fields = {}
            if change == "wrong_title":
                fields["title"] = "Another role"
            if change == "wrong_company":
                fields["hiringOrganization"] = {"name": "Other employer"}
            if change == "wrong_id":
                fields["identifier"] = {"value": "other"}
            if change == "thin_description":
                fields["description"] = "Preview only"
            if change == "expired":
                fields["validThrough"] = "2020-01-01T00:00:00Z"
            body = detail(i, **fields)
            if change == "wrong_canonical":
                body = body.replace(
                    'rel="canonical" href="' + url(i),
                    'rel="canonical" href="https://evil.invalid/jobs/1-engineer',
                )
            if change == "missing_native_description":
                body = body.replace('id="quill-container-with-job-details"', 'id="missing"')
            return httpx.Response(200, text=body)

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), trust_env=False
        ) as client:
            return await create_connector(
                "jboard", HOST, "Do not replace employers", client
            ).discover()

    return asyncio.run(main())


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.jboard.asyncio.sleep", no_wait)


def test_complete_mixed_employers_and_pagination():
    result = run(31)
    assert result.complete and len(result.jobs) == 31
    assert result.jobs[0].company == "Employer 1" and result.jobs[-1].company == "Employer 31"
    job = result.jobs[0]
    assert (
        job.location == "Hamilton"
        and job.raw["jobposting"]["jobLocation"]["address"]["addressCountry"] == "Bermuda"
    )
    assert job.salary["currency"] == "USD" and job.remote_status == "TELECOMMUTE"
    assert job.employment_type == "FULL_TIME" and job.published_at.year == 2026
    assert job.application_url == ORIGIN + "/jobs/1/apply"


@pytest.mark.parametrize(
    "change",
    [
        "map_mismatch",
        "changed",
        "broken_xml",
        "cross_host",
        "skip_page",
        "truncated",
        "missing_apply",
        "fetch_failure",
        "redirect",
        "wrong_title",
        "wrong_company",
        "wrong_id",
        "thin_description",
        "wrong_canonical",
        "missing_native_description",
    ],
)
def test_failure_is_not_complete(change):
    with pytest.raises(ValueError):
        run(change=change)


def test_repeated_page_rejected():
    with pytest.raises(ValueError):
        run(31, "repeat_page")


def test_expiry_conflict_is_preserved_not_assumed_closed():
    result = run(change="expired")
    assert result.complete and len(result.jobs) == 1
    assert "source_expiry_elapsed_while_listed" in result.jobs[0].quality_flags


@pytest.mark.parametrize("url", [ORIGIN, ORIGIN + "/jobs", "https://jobs.cisontario.ca/"])
def test_source_detection(url):
    assert detect(url) == ("jboard", url.split("/")[2])


@pytest.mark.parametrize(
    "url",
    [
        ORIGIN + "/jobs?page=2",
        ORIGIN + "#x",
        ORIGIN + "/jobs/1-engineer",
        "http://" + HOST,
        "https://" + HOST + ".evil.invalid",
        "https://127.0.0.1/jobs",
        "https://user@" + HOST,
        "https://example.jboard.io/jobs",
    ],
)
def test_unreviewed_or_filtered_sources_rejected(url):
    with pytest.raises(ValueError):
        detect(url)


def test_rejected_constructor_and_unsafe_urls():
    c = JBoardConnector("jboard", HOST, "Board", httpx.AsyncClient())
    assert c.identifier(ORIGIN + "/jobs/1-engineer!") == "1"
    for path in ["/jobs/1-engineer%2fsecret", "/jobs/1-engineer/other", "/jobs/1-engineer?token=x"]:
        with pytest.raises(ValueError):
            c.identifier(ORIGIN + path)
    with pytest.raises(ValueError):
        JBoardConnector("jobboardio", HOST, "Board", httpx.AsyncClient())
    with pytest.raises(ValueError):
        JBoardConnector("jboard", "127.0.0.1", "Board", httpx.AsyncClient())


def test_unsafe_xml_and_unknown_job_map_rejected():
    connector = JBoardConnector("jboard", HOST, "Board", httpx.AsyncClient())
    payload = f'<!DOCTYPE urlset [<!ENTITY x SYSTEM "file:///etc/passwd">]><urlset xmlns="{NS}"><url><loc>&x;</loc></url></urlset>'
    with pytest.raises(ValueError):
        connector.sitemap(payload.encode(), index=False)
    with pytest.raises(ValueError):
        connector.sitemap(
            index().replace("sitemap-jobs-1.xml", "sitemap-jobs-new.xml").encode(), index=True
        )
    maps = connector.sitemap(
        index()
        .replace("sitemap-companies-1.xml", "sitemap-category-224941-job-types.xml")
        .encode(),
        index=True,
    )
    assert len(maps) == 1  # Public profiles, employers and categories are not job maps.


def test_description_headings_and_links_are_not_native_header_identity():
    c = JBoardConnector("jboard", HOST, "Board", httpx.AsyncClient())
    native = '<h1>Engineer 1</h1><p>Build reliable systems. <a href="/companies/another">Our partner</a></p>'
    rows, _ = c.listings(board([1]).encode(), 1)
    result = c.parse(("1", rows["1"], detail(1, native_html=native).encode()))
    assert result[0].title == "Engineer 1" and "Our partner" in result[0].description
    assert result[0].company == "Employer 1"

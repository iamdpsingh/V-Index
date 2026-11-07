"""Public published sitemap coverage and complete details, without private/search requests."""

import asyncio
import json

import httpx
import pytest
from vindex.connectors.jobboardio import MAP, JobBoardIOConnector
from vindex.connectors.registry import create_connector, detect

HOST = "www.nifajobs.com"
ORIGIN = "https://" + HOST
NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
APPLY = "https://careers.example.org/role/123?source=board"


def url(i):
    return ORIGIN + f"/jobs/{i}-role-at-employer"


def index():
    return f'<sitemapindex xmlns="{NS}"><sitemap><loc>{ORIGIN}{MAP}?finish_id=2&amp;start_id=1</loc></sitemap><sitemap><loc>{ORIGIN}/sitemaps/pages/page_sitemap_details.xml</loc></sitemap></sitemapindex>'


def jobmap(ids):
    return (
        f'<urlset xmlns="{NS}"><url><loc>{ORIGIN}</loc></url>'
        + "".join(f"<url><loc>{url(i)}</loc></url>" for i in ids)
        + "</urlset>"
    )


def board():
    return f'<html><form action="/jobs/search" method="get"></form><a href="{url(1)}">Real role</a></html>'


def detail(i, change):
    ld = {
        "@type": "JobPosting",
        "title": "Researcher",
        "hiringOrganization": {"name": "Actual employer"},
        "description": "<p>Develop real research.</p>",
        "datePosted": "2026-11-05",
        "validThrough": "2027-01-01T00:00:00Z",
        "employmentType": ["FULL_TIME"],
        "jobLocationType": "TELECOMMUTE",
        "baseSalary": {"currency": "USD", "value": {"minValue": 45000}},
    }
    if change == "wrong_title":
        ld["title"] = "Other title"
    if change == "wrong_employer":
        ld["hiringOrganization"]["name"] = "Other employer"
    if change == "partial_text":
        ld["description"] = "Preview"
    if change == "expired":
        ld["validThrough"] = "2020-01-01T00:00:00Z"
    native = "<p>Develop real research.</p>"
    if change in {"protected", "protected_mismatch"}:
        ld["description"] = "<p>Develop real research. Contact contact@example.invalid.</p>"
        native = (
            "<p>Develop real research. Contact "
            '<span class="__cf_email__" data-cfemail="hidden-token">[email&nbsp;protected]</span>.</p>'
        )
        if change == "protected_mismatch":
            native = native.replace("research", "marketing")
    link = APPLY if change != "unsafe_apply" else "https://user:password@careers.example.org/role"
    if change == "http_apply":
        link = APPLY.replace("https:", "http:")
    c = url(i) if change != "wrong_canonical" else url(i + 1)
    jobid = i if change != "wrong_apply_id" else 99
    controls = f'<a class="apply-button external_apply" id="apply_button_job-details-bottom" data-job-id="{jobid}" href="{link}">Apply</a>'
    if change == "missing_apply":
        controls = ""
    if change == "conflicting_apply":
        controls += controls.replace(APPLY, "https://different.example.org/role")
    if change in {"modal_apply", "wrong_modal_id"}:
        modal_id = i if change == "modal_apply" else 99
        controls = (
            f'<a class="apply-button modal_apply" id="apply_button_job-details-bottom" '
            f'data-job-id="{i}" href="/applicants/new?id={modal_id}&amp;modal=true" '
            'data-toggle="modal" data-target="#applyModal">Apply</a><div id="applyModal"></div>'
        )
    structured = f'<script type="application/ld+json">{json.dumps(ld)}</script>'
    if change in {"native_only", "undated_native_only"}:
        structured = ""
    date = (
        '<div class="panel-body"><div class="text-muted"><span>Posted November 05, 2026</span></div></div>'
        if change == "native_only"
        else ""
    )
    return (
        f'<html><link rel="canonical" href="{c}">'
        + structured
        + '<div class="jobDetail-headerIntro"><h1>Researcher</h1><div class="text-primary text-large">Actual employer</div><i class="fa-map-marker-alt"></i><span>Paris</span><i class="fa-wifi"></i><span>Remote</span><i class="fa-running"></i><span>Freelance</span></div>'
        + f'<div class="job-body">{native}</div>'
        + date
        + controls
        + "</html>"
    )


def run(change=None):
    passes = 0

    async def main():
        def handle(request):
            nonlocal passes
            assert request.url.host == HOST and request.method == "GET"
            path = request.url.path
            assert (
                path != "/jobs/search"
                and "/api/" not in path
                and "Authorization" not in request.headers
            )
            if path == "/robots.txt":
                return httpx.Response(
                    200, text="User-agent: *\nAllow: /\nSitemap: " + ORIGIN + "/sitemap.xml"
                )
            if path == "/":
                return httpx.Response(200, text=board())
            if path == "/sitemap.xml":
                return httpx.Response(200, text=index())
            if path == MAP:
                passes += 1
                ids = [1, 2]
                if change == "missing_preview":
                    ids = [2]
                if change == "changed" and passes > 1:
                    ids = [1]
                if change == "out_of_range":
                    ids = [1, 3]
                if change == "duplicate":
                    ids = [1, 1]
                body = jobmap(ids)
                if change == "malformed":
                    body = body[:-8]
                if change == "cross_host":
                    body = body.replace(HOST, "private.invalid")
                return httpx.Response(200, text=body)
            assert path.startswith("/jobs/")
            i = int(path.split("/")[2].split("-")[0])
            if change == "fetch_failure":
                return httpx.Response(403)
            if change == "redirect":
                return httpx.Response(302, headers={"Location": "https://private.invalid"})
            return httpx.Response(200, text=detail(i, change))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle), trust_env=False) as c:
            return await create_connector("jobboardio", HOST, "Board label", c).discover()

    return asyncio.run(main())


@pytest.fixture(autouse=True)
def pacing(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.jobboardio.asyncio.sleep", no_wait)


def test_full_sitemap_includes_jobs_beyond_home_preview():
    batch = run()
    assert batch.complete and len(batch.jobs) == 2
    job = batch.jobs[0]
    assert (
        job.company == "Actual employer"
        and job.application_url == APPLY
        and job.location == "Paris"
    )
    assert (
        job.quality_flags == ["publication_date_only"]
        and job.raw["published_at_original"] == "2026-11-05"
    )
    assert (
        job.salary["currency"] == "USD"
        and job.remote_status == "TELECOMMUTE"
        and job.employment_type == "FULL_TIME"
    )


@pytest.mark.parametrize(
    "change",
    [
        "missing_preview",
        "changed",
        "out_of_range",
        "duplicate",
        "malformed",
        "cross_host",
        "fetch_failure",
        "redirect",
        "wrong_title",
        "wrong_employer",
        "partial_text",
        "unsafe_apply",
        "wrong_canonical",
        "wrong_apply_id",
        "missing_apply",
        "conflicting_apply",
        "protected_mismatch",
        "wrong_modal_id",
        "undated_native_only",
    ],
)
def test_reject_incomplete_or_unsafe_data(change):
    with pytest.raises(ValueError):
        run(change)


def test_source_expiry_conflict_preserved():
    assert "source_expiry_elapsed_while_listed" in run("expired").jobs[0].quality_flags


def test_masked_source_contact_never_persisted():
    job = run("protected").jobs[0]
    assert (
        "[email protected]" in job.description and "source_contact_protected" in job.quality_flags
    )
    assert "original_description_sha256" in job.raw
    assert "contact@example.invalid" not in job.model_dump_json()
    assert "hidden-token" not in job.model_dump_json()


@pytest.mark.parametrize("change", ["modal_apply", "http_apply"])
def test_public_posting_is_safe_application_entry(change):
    job = run(change).jobs[0]
    assert job.application_url == job.source_url == url(1)
    if change == "http_apply":
        assert job.raw["application_url_original"] == APPLY.replace("https:", "http:")
        assert "application_http_source" in job.quality_flags


def test_native_detail_preserves_visible_metadata_without_structured_posting():
    job = run("native_only").jobs[0]
    assert job.published_at.date().isoformat() == "2026-11-05"
    assert job.employment_type == "Freelance" and job.remote_status == "Remote"
    assert "structured_posting_missing" in job.quality_flags


@pytest.mark.parametrize(
    "url",
    [
        ORIGIN + "/jobs/search",
        ORIGIN + "/?search=x",
        ORIGIN + "#x",
        "https://@" + HOST,
        "https://" + HOST + ".evil",
        "http://" + HOST,
        "https://127.0.0.1",
    ],
)
def test_detection_rejects_unreviewed_or_filtered_sources(url):
    with pytest.raises(ValueError):
        detect(url)


def test_exact_platform_is_distinct_and_ranges_are_validated():
    assert detect(ORIGIN) == ("jobboardio", HOST)
    assert detect("https://jobs.aame.org") == ("jboard", "jobs.aame.org")
    c = JobBoardIOConnector("jobboardio", HOST, "Board", httpx.AsyncClient())
    with pytest.raises(ValueError):
        c.maps(index().replace("finish_id=2", "finish_id=0").encode())
    with pytest.raises(ValueError):
        c.maps(index().replace("start_id=1", "start_id=3").encode())
    with pytest.raises(ValueError):
        c.maps(index().replace("start_id=1", "start_id=1&amp;token=x").encode())
    with pytest.raises(ValueError):
        c.identifier(url(1) + "%2fprivate")

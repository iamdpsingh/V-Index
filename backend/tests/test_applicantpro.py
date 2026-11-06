"""Distinct ApplicantPro/iSolvedHire host and completeness regressions; controlled data."""

import asyncio
import json

import httpx
import pytest
from vindex.connectors.registry import create_connector, detect


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.applicantpro.asyncio.sleep", no_wait)


def listing(suffix):
    return dict(
        id=123,
        title="Engineer",
        siteId=10,
        subdomain="example",
        domainName=suffix,
        jobUrl=f"https://example.{suffix}/jobs/123",
        jobLocation="London, UK",
        employmentType="Full Time",
        workplaceType="Fully remote",
    )


def board(suffix):
    return f'''<html><head><title>Job Listings - Example Jobs</title></head><body><script>
    ['JobListings']; organizationId: 1, domainId: 10, domainName: "{suffix}", subdomainName: "example";
    </script></body></html>'''


def schema(suffix):
    return {
        "@type": "JobPosting",
        "title": "Engineer",
        "url": f"https://example.{suffix}/jobs/123.html",
        "identifier": {"sameAs": "123"},
        "description": "<p>Build</p>",
        "hiringOrganization": {"name": "Example"},
        "datePosted": "2026-11-01 00:00:00",
        "baseSalary": {
            "currency": "GBP",
            "value": {"minValue": "50000", "maxValue": "60000", "unitText": "YEAR"},
        },
    }


def detail(suffix, data=None, canonical=None):
    return f'''<html><head><link rel="canonical" href="{canonical or f"https://example.{suffix}/jobs/123.html"}">
    <title>Engineer - London - Example Jobs</title><script type="application/ld+json">{json.dumps(data or schema(suffix))}</script></head><body><script>
    ['JobDetail']; ['InlineAuth']; organizationId: 1, domainId: 10, jobListingId: 123;
    </script></body></html>'''


def run(
    provider="applicantpro",
    data=None,
    job=None,
    confirm=None,
    canonical=None,
    status=200,
    html=None,
    core=None,
    omit_schema=False,
):
    suffix = {"applicantpro": "applicantpro.com", "isolvedhire": "isolvedhire.com"}[provider]
    calls = 0

    async def discover():
        def handler(request):
            nonlocal calls
            assert request.url.host == "example." + suffix
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text="User-agent: *\nAllow: /")
            if request.url.path == "/jobs/":
                return httpx.Response(200, text=html or board(suffix))
            if request.url.path == "/core/jobs/10":
                assert dict(request.url.params) == {"getParams": '{"isInternal":0}'}
                calls += 1
                value = confirm if calls > 1 and confirm is not None else data
                return httpx.Response(
                    200,
                    json=value
                    if value is not None
                    else {"success": True, "data": {"jobs": [listing(suffix)], "jobCount": 1}},
                )
            if request.url.path == "/core/jobs/10/123/job-details":
                return httpx.Response(
                    200,
                    json=core
                    if core is not None
                    else {
                        "success": True,
                        "data": {
                            "id": 123,
                            "siteId": 10,
                            "title": "Engineer",
                            "description": "<p>Build</p>",
                            "benefits": "",
                            "jobDescriptionFile": "",
                        },
                    },
                )
            assert request.url.path == "/jobs/123"
            body = detail(suffix, job, canonical)
            if omit_schema:
                import re

                body = re.sub(r'<script type="application/ld\+json">.*?</script>', "", body)
            return httpx.Response(status, text=body)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await create_connector(provider, "example", "Configured", client).discover()

    return asyncio.run(discover())


@pytest.mark.parametrize("provider", ["applicantpro", "isolvedhire"])
def test_distinct_platform_hosts_and_complete_matching_details(provider):
    batch = run(provider)
    job = batch.jobs[0]
    assert batch.complete and job.external_id == "123" and job.company == "Example"
    assert job.description == "Build" and job.application_url == job.source_url
    assert job.remote_status == "Fully remote" and job.salary["currency"] == "GBP"
    assert job.published_at.year == 2026
    assert job.raw["board"]["domain_id"] == 10
    assert "csrfToken" not in json.dumps(job.raw)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d.update(success=False),
        lambda d: d["data"].update(jobCount=True),
        lambda d: d["data"].update(jobCount=2),
        lambda d: d["data"].update(jobs=[]),
        lambda d: d["data"]["jobs"][0].update(id=True),
        lambda d: d["data"]["jobs"][0].update(siteId=20),
        lambda d: d["data"]["jobs"][0].update(domainName="isolvedhire.com"),
        lambda d: d["data"]["jobs"][0].update(jobUrl="https://evil.com/jobs/123"),
    ],
)
def test_partial_or_wrong_site_collection_aborts(mutation):
    data = {"success": True, "data": {"jobs": [listing("applicantpro.com")], "jobCount": 1}}
    mutation(data)
    with pytest.raises(ValueError):
        run(data=data)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda j: j.update(title="Other"),
        lambda j: j["identifier"].update(sameAs="124"),
        lambda j: j.update(url="https://evil.com/jobs/123.html"),
        lambda j: j.pop("description"),
    ],
)
def test_mismatched_details_abort(mutation):
    job = schema("applicantpro.com")
    mutation(job)
    with pytest.raises((ValueError, KeyError)):
        run(job=job)


def test_shared_canonical_supported_but_other_tenants_rejected():
    assert run(
        canonical="https://www.applicantpro.com/openings/example/jobs/123/UK/London/Engineer"
    ).complete
    for url in (
        "https://www.applicantpro.com/openings/other/jobs/123",
        "https://evil.com/openings/example/jobs/123",
    ):
        with pytest.raises(ValueError):
            run(canonical=url)


def test_empty_salary_schema_remains_raw_without_invented_pay():
    job = schema("applicantpro.com")
    job["baseSalary"]["value"] = {"value": "", "unitText": ""}
    normalized = run(job=job).jobs[0]
    assert (
        normalized.salary is None
        and normalized.raw["jobposting"]["baseSalary"]["currency"] == "GBP"
    )


def test_failed_request_changed_collection_and_wrong_board_abort():
    changed = {"success": True, "data": {"jobs": [listing("applicantpro.com")], "jobCount": 1}}
    changed["data"]["jobs"][0]["title"] = "Other"
    for kwargs in (
        {"status": 404},
        {"confirm": changed},
        {
            "html": board("applicantpro.com").replace(
                'subdomainName: "example"', 'subdomainName: "other"'
            )
        },
    ):
        with pytest.raises(ValueError):
            run(**kwargs)


def test_platform_names_and_hosts_remain_distinct():
    assert detect("https://example.applicantpro.com/jobs/") == ("applicantpro", "example")
    assert detect("https://example.isolvedhire.com/jobs/") == ("isolvedhire", "example")
    for url in (
        "https://a.b.isolvedhire.com/jobs/",
        "https://example.applicantpro.com.evil.com/jobs/",
    ):
        with pytest.raises(ValueError):
            detect(url)


def test_public_detail_fills_real_jsonld_omission_without_inventing_schema():
    job = run(provider="isolvedhire", omit_schema=True).jobs[0]
    assert job.description == "Build" and job.raw["jobposting"] is None
    assert "jobposting_schema_missing" in job.quality_flags and job.published_at is None
    assert job.raw["public_job_detail"]["id"] == 123


@pytest.mark.parametrize(
    "changes",
    [
        {"id": True},
        {"siteId": 20},
        {"title": "Other"},
        {"description": None},
        {"jobDescriptionFile": "attachment.pdf"},
    ],
)
def test_public_detail_malformed_identity_and_unhandled_attachment_abort(changes):
    data = {
        "id": 123,
        "siteId": 10,
        "title": "Engineer",
        "description": "<p>Build</p>",
        "jobDescriptionFile": "",
    }
    data.update(changes)
    with pytest.raises(ValueError):
        run(core={"success": True, "data": data})


def test_public_detail_failure_is_not_empty_snapshot():
    with pytest.raises(ValueError):
        run(core={"success": False})

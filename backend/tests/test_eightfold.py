"""Eightfold public advertised sitemaps without private/candidate or versioned API access."""

import asyncio
import json
from xml.etree.ElementTree import ParseError

import httpx
import pytest
from vindex.connectors.registry import create_connector, detect

ORIGIN = "https://example.eightfold.ai"
INDEX = ORIGIN + "/careers/sitemap_index.xml?domain=old.example.com"
MAP = ORIGIN + "/careers/sitemap.xml?domain=old.example.com"
NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"


def url(identifier=1):
    return ORIGIN + f"/careers/job/{identifier}-engineer?domain=example.com"


def board(legacy=False, count=1):
    data = {"domain": "old.example.com"}
    if legacy:
        data.update(
            {
                "isUserAuthenticated": False,
                "excludePrivatePositions": True,
                "branding": {"companyName": "Example"},
                "count": count,
                "positions": [{"id": i + 1, "isPrivate": False} for i in range(min(10, count))],
                "candidate": "EXCLUDED_CANDIDATE",
                "user": "EXCLUDED_USER",
            }
        )
        name = "smartApplyData"
    else:
        data["configs"] = {
            "pcsxConfig": {
                "searchConfig": {"excludePrivatePositions": True},
                "branding": {"companyName": "Example"},
            }
        }
        data["onboardingData"] = "EXCLUDED_CANDIDATE"
        name = "pcsx-data"
    return '<html><code id="' + name + '">' + json.dumps(data) + "</code></html>"


def index():
    return (
        '<sitemapindex xmlns="'
        + NAMESPACE
        + '"><sitemap><loc>'
        + MAP.replace("&", "&amp;")
        + "</loc></sitemap><sitemap><loc>"
        + ORIGIN
        + "/careers/sitemap_cat.xml?domain=old.example.com</loc></sitemap></sitemapindex>"
    )


def jobmap(total=1):
    urls = [ORIGIN + "/careers?domain=example.com"] + [url(i + 1) for i in range(total)]
    return (
        '<urlset xmlns="'
        + NAMESPACE
        + '">'
        + "".join("<url><loc>" + u + "</loc></url>" for u in urls)
        + "</urlset>"
    )


def posting(identifier=1):
    return {
        "@type": "JobPosting",
        "title": "Engineer",
        "url": url(identifier),
        "hiringOrganization": {"name": "Example"},
        "description": "<p>Build systems and know Python.</p>",
        "datePosted": "2026-11-01T10:00:00",
        "employmentType": "FULL_TIME",
        "jobLocationType": "TELECOMMUTE",
        "jobLocation": {"address": {"addressLocality": "London", "addressCountry": {"name": "GB"}}},
        "baseSalary": {"currency": "GBP", "value": 40000},
    }


def detail(identifier=1, row=None):
    return (
        '<html><script type="application/ld+json">'
        + json.dumps(row or posting(identifier))
        + "</script></html>"
    )


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.eightfold.asyncio.sleep", no_wait)


def run(total=1, legacy=False, shell=None, map_body=None, content=None, changed=False, status=200):
    calls = 0

    async def discover():
        def handle(request):
            nonlocal calls
            assert (
                request.url.host == "example.eightfold.ai"
                and request.method == "GET"
                and "authorization" not in request.headers
            )
            assert "/api/" not in request.url.path and "/apply" not in request.url.path
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text="User-agent: *\nAllow: /\nSitemap: " + INDEX)
            if request.url.path == "/careers":
                assert not request.url.query
                return httpx.Response(200, text=shell or board(legacy, total))
            if request.url.path == "/careers/sitemap_index.xml":
                return httpx.Response(200, text=index())
            if request.url.path == "/careers/sitemap.xml":
                calls += 1
                body = map_body or jobmap(total)
                if changed and calls > 1:
                    body = body.replace("-engineer", "-changed")
                return httpx.Response(200, text=body)
            assert "/sitemap_cat.xml" not in request.url.path
            identifier = int(request.url.path.split("/")[-1].split("-")[0])
            assert 1 <= identifier <= total
            return httpx.Response(status, text=content or detail(identifier))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await create_connector("eightfold", "example", "Configured", client).discover()

    return asyncio.run(discover())


@pytest.mark.parametrize("legacy", [True, False])
def test_complete_public_sitemaps_and_native_details_preserve_source_data_without_user_state(
    legacy,
):
    result = run(legacy=legacy)
    job = result.jobs[0]
    assert result.complete and job.company == "Example" and job.title == "Engineer"
    assert job.description == "Build systems and know Python." and job.location == "London, GB"
    assert job.source_url == url() and job.application_url == url()
    assert (
        job.salary["currency"] == "GBP"
        and job.remote_status == "TELECOMMUTE"
        and job.employment_type == "FULL_TIME"
    )
    assert job.published_at.tzinfo is None and job.quality_flags == [
        "publication_timezone_unspecified"
    ]
    assert "EXCLUDED" not in job.model_dump_json()
    assert (
        job.raw["board"]["domain"] == "old.example.com"
    )  # Canonical namespace alias remains original.
    assert detect(ORIGIN + "/careers") == ("eightfold", "example")


def test_all_sitemap_jobs_and_legacy_public_total_agree():
    assert len(run(total=11, legacy=True).jobs) == 11
    with pytest.raises(ValueError):
        run(legacy=True, shell=board(True, 2))


@pytest.mark.parametrize(
    "old,new",
    [
        ("</html>", ""),
        ('"excludePrivatePositions": true', '"excludePrivatePositions": false'),
        ('"companyName": "Example"', '"companyName": ""'),
    ],
)
def test_missing_source_privacy_or_named_employer_fails(old, new):
    with pytest.raises(ValueError):
        run(shell=board().replace(old, new))


def test_legacy_authenticated_or_private_seed_is_never_indexed():
    with pytest.raises(ValueError):
        run(
            legacy=True,
            shell=board(True).replace(
                '"isUserAuthenticated": false', '"isUserAuthenticated": true'
            ),
        )
    with pytest.raises(ValueError):
        run(legacy=True, shell=board(True).replace('"isPrivate": false', '"isPrivate": true'))


@pytest.mark.parametrize(
    "old,new",
    [
        (ORIGIN, "https://evil.test"),
        ("domain=example.com", "domain=other.example"),
        ("</urlset>", ""),
        ("/1-engineer", "/1-%2fprivate"),
    ],
)
def test_unscoped_or_truncated_job_maps_fail(old, new):
    # Changing every namespace consistently is a genuine alias; change one job only instead.
    body = jobmap().replace(old, new, 1 if old == "domain=example.com" else -1)
    with pytest.raises((ValueError, ParseError)):
        run(map_body=body)


def test_empty_duplicate_or_oversized_native_sitemaps_fail():
    with pytest.raises(ValueError):
        run(map_body=jobmap(0))
    with pytest.raises(ValueError):
        run(map_body=jobmap(2).replace(url(2), url(1)))
    with pytest.raises(ValueError):
        run(map_body=jobmap(201))


@pytest.mark.parametrize(
    "key,value",
    [
        ("url", url(2)),
        ("title", ""),
        ("hiringOrganization", {"name": "Other"}),
        ("description", ""),
    ],
)
def test_mandatory_job_identity_full_body_and_employer_fail(key, value):
    with pytest.raises(ValueError):
        run(content=detail(row={**posting(), key: value}))


def test_failed_detail_or_changed_roster_aborts_not_empty_success():
    with pytest.raises(ValueError):
        run(status=404)
    with pytest.raises(ValueError):
        run(changed=True)


@pytest.mark.parametrize(
    "url",
    [
        ORIGIN + "/careers?query=Engineer",
        ORIGIN + "/careers/profile",
        ORIGIN + "/careers/apply?pid=1",
        ORIGIN.replace(".eightfold.ai", ".eightfold.ai.evil.test") + "/careers",
    ],
)
def test_registration_only_accepts_unfiltered_native_public_roots(url):
    with pytest.raises(ValueError):
        detect(url)

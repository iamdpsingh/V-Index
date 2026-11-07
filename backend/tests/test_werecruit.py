"""Complete native sitemap, full text and mandatory application detail regressions."""

import asyncio
import json

import httpx
import pytest
from vindex.connectors.http import UpstreamStatusError
from vindex.connectors.registry import create_connector, detect

ORIGIN = "https://careers.werecruit.io"
BASE = ORIGIN + "/fr/example"
URL = BASE + "/offres/engineer-abc123"
POOL = BASE + "/offres/candidature-spontanee-123def"


def org():
    return {"@type": "Organization", "name": "Example", "url": BASE}


def schema(data):
    return '<script type="application/ld+json">' + json.dumps(data) + "</script>"


def sitemap(links=None):
    return (
        "<html><head><title>Plan du site</title></head><body>"
        + schema(org())
        + "<h2>Offres</h2><ul>"
        + (
            links
            if links is not None
            else f'<li><a href="{URL}">Engineer</a></li><li><a href="{POOL}">Candidature spontanée</a></li><li><a href="/fr/redirectToPage/123">Other</a></li>'
        )
        + "</ul></body></html>"
    )


def posting():
    return {
        "@type": "JobPosting",
        "title": "Engineer",
        "description": "<p>Build systems</p>",
        "hiringOrganization": {"name": "Example branch"},
        "jobLocation": [{"address": {"addressLocality": "Paris", "addressCountry": "FR"}}],
        "baseSalary": {"currency": "EUR", "value": {"minValue": 3000, "unitText": "MONTH"}},
        "employmentType": ["FULL_TIME"],
        "datePosted": "2026-10-01T10:00:00Z",
    }


def detail(row=None):
    return (
        '<html><head><link rel="canonical" href="'
        + URL
        + '"></head><body>'
        + schema(org())
        + schema(row or posting())
        + '<h1>Engineer</h1><div class="description rich-text"><h2>Company</h2><p>About us</p><h2>Role</h2><p>Build systems</p><h2>Profile</h2><p>Know Python</p><h2>Benefits</h2><p>Health insurance</p></div>'
        + '<form id="form" method="post" action="'
        + URL
        + '"><input name="private-form-data"><button id="submit-button" type="submit">Apply</button></form></body></html>'
    )


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.werecruit.asyncio.sleep", no_wait)


def run(board=None, page=None, confirm=None, status=200, robots="User-agent: *\nAllow: /"):
    calls = 0

    async def discover():
        def handle(request):
            nonlocal calls
            assert request.url.host == "careers.werecruit.io" and request.method == "GET"
            assert not request.url.query and "authorization" not in request.headers
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text=robots)
            if str(request.url) == BASE + "/site-map":
                calls += 1
                return httpx.Response(
                    200, text=confirm if calls > 1 and confirm is not None else board or sitemap()
                )
            assert str(request.url) == URL  # No pool, redirects or application submissions.
            return httpx.Response(status, text=page or detail())

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await create_connector("werecruit", "example", "Configured", client).discover()

    return asyncio.run(discover())


def test_full_sitemap_skips_only_explicit_pool_and_preserves_full_profile_and_benefits():
    result = run()
    assert result.complete and len(result.jobs) == 1
    job = result.jobs[0]
    assert job.external_id == "abc123" and job.company == "Example branch"
    assert "Know Python" in job.description and "Health insurance" in job.description
    assert job.raw["board"]["excluded_spontaneous_applications"] == {POOL: "Candidature spontanée"}
    assert "private-form-data" not in job.model_dump_json()
    assert job.application_url == URL and job.salary["currency"] == "EUR"
    assert job.location == "Paris, FR" and job.remote_status is None
    assert job.published_at.year == 2026 and job.employment_type == "FULL_TIME"
    assert detect(BASE) == ("werecruit", "example")
    assert detect(BASE + "/offres") == ("werecruit", "example")


@pytest.mark.parametrize(
    "replace,value",
    [
        ("Plan du site", "Other"),
        ("<h2>Offres</h2>", "<h2>Other</h2>"),
        ("</html>", ""),
        (URL, "https://evil.test/offres/engineer-abc123"),
        ("/fr/redirectToPage/123", "/fr/redirectToPage/private"),
        ('"url": "' + BASE + '"', '"url": "https://evil.test"'),
        ("</body>", '<a rel="next" href="?page=2">Next</a></body>'),
    ],
)
def test_partial_or_mismatched_sitemap_fails(replace, value):
    with pytest.raises(ValueError):
        run(board=sitemap().replace(replace, value))


def test_duplicate_or_empty_offer_roster_fails():
    for links in [
        "",
        f'<a href="{URL}">Engineer</a><a href="{URL}">Engineer</a>',
        f'<a href="{POOL}">Candidature spontanée</a>',
    ]:
        with pytest.raises(ValueError):
            run(board=sitemap(links))


@pytest.mark.parametrize(
    "replace,value",
    [
        ("<h1>Engineer</h1>", "<h1>Other</h1>"),
        ('rel="canonical"', 'rel="other"'),
        ('id="form"', 'id="other"'),
        ('method="post"', 'method="get"'),
        ('id="submit-button"', 'id="other"'),
        ('class="description rich-text"', 'class="other"'),
        ("Know Python", ""),
    ],
)
def test_required_detail_validation(replace, value):
    # A missing profile is allowed by the source; it must not erase a structured role.
    if replace == "Know Python":
        assert "Build systems" in run(page=detail().replace(replace, value)).jobs[0].description
    else:
        with pytest.raises(ValueError):
            run(page=detail().replace(replace, value))


def test_structured_role_disagreement_and_changed_roster_abort():
    with pytest.raises(ValueError):
        run(page=detail({**posting(), "description": "Different role"}))
    with pytest.raises(ValueError):
        run(confirm=sitemap().replace("Engineer", "Changed"))


def test_failed_detail_and_robots_denial_never_become_empty_success():
    with pytest.raises(UpstreamStatusError):
        run(status=404)
    with pytest.raises(ValueError):
        run(robots="User-agent: *\nDisallow: /fr/")

"""Job-board pagination and HTML safety regressions; no live coverage claims."""

import asyncio
import json

import httpx
import pytest
from vindex.connectors.registry import create_connector, detect

ORIGIN = "https://example.jobboardly.com"
ONE = "/jobs/engineer-aaaaaaaa"
TWO = "/jobs/analyst-bbbbbbbb"


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.jobboardly.asyncio.sleep", no_wait)


def page(paths, start=1, next_page=None):
    control = (
        f'<a href="/jobs?page={next_page}"><span>Next</span></a>'
        if next_page
        else '<span aria-disabled="true"><span>Next</span></span>'
    )
    return (
        f"<p>Showing <span>{start}</span> to <span>{start + len(paths) - 1}</span></p>"
        '<nav aria-label="Pagination">'
        + control
        + "</nav>"
        + "".join(f'<a href="{path}">Job</a>' for path in paths)
    )


def detail(path=ONE, identifier=1, *, schema=True, apply=True, canonical=True):
    row = {
        "@type": "JobPosting",
        "url": ORIGIN + path,
        "identifier": {"value": identifier},
        "title": "Engineer",
        "hiringOrganization": {"name": "Example"},
        "description": "<p>Build systems</p>",
        "datePosted": "2026-11-01",
        "employmentType": "FULL_TIME",
        "baseSalary": {"currency": "GBP"},
        "jobLocation": {"address": {"addressLocality": "London", "addressCountry": "UK"}},
    }
    return (
        (f'<script type="application/ld+json">{json.dumps(row)}</script>' if schema else "")
        + (f'<link rel="canonical" href="{ORIGIN}{path}">' if canonical else "")
        + '<div class="flex items-center text-sm">On-site</div>'
        + (
            '<a href="https://employer.example.org/jobs/engineer/apply">Apply now</a>'
            if apply
            else ""
        )
    )


def run(
    pages=None, bodies=None, confirmation=None, robots="User-agent: *\nAllow: /", requests_out=None
):
    calls = 0
    requests = requests_out if requests_out is not None else []

    async def discover():
        def handler(request):
            nonlocal calls
            requests.append(str(request.url))
            assert request.url.host == "example.jobboardly.com"
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text=robots)
            if request.url.path == "/jobs":
                calls += 1
                number = int(request.url.params.get("page", "1"))
                body = (
                    (confirmation if confirmation is not None else (pages or {1: page([ONE])})[1])
                    if number == 1 and calls > 1
                    else (pages or {1: page([ONE])})[number]
                )
                return httpx.Response(200, text=body)
            return httpx.Response(200, text=(bodies or {ONE: detail()})[request.url.path])

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await create_connector("jobboardly", "example", "Board", client).discover()

    return asyncio.run(discover()), requests


def test_public_board_preserves_real_employer_application_and_workplace():
    batch, requests = run()
    job = batch.jobs[0]
    assert batch.complete and job.company == "Example" and job.description == "Build systems"
    assert job.remote_status == "On-site" and job.location == "London, UK"
    assert job.salary["currency"] == "GBP" and job.published_at.year == 2026
    assert job.application_url == "https://employer.example.org/jobs/engineer/apply"
    assert all("employer.example.org" not in request for request in requests)


def test_email_only_application_keeps_original_destination_and_https_entry():
    body = detail().replace(
        "https://employer.example.org/jobs/engineer/apply", "mailto:jobs@example.org"
    )
    batch, _ = run(bodies={ONE: body})
    job = batch.jobs[0]
    assert job.application_url == job.source_url == ORIGIN + ONE
    assert job.raw["application_url"] == "mailto:jobs@example.org"
    assert job.quality_flags == ["application_by_email"]


def test_html_only_posting_requires_independent_identity_and_preserves_missing_fields():
    body = (
        '<main><div><h1>Engineer</h1><a href="https://employer.example.org">Example</a></div>'
        '<div class="rich-text">Build systems</div>'
        '<div class="flex items-center text-sm" id="job-posted-at">14 days ago</div>'
        '<div class="flex items-center text-sm">Remote</div>'
        '<div class="flex items-center text-sm">Full-time</div>'
        '<div class="flex items-center text-sm">£50,000 yearly</div></main>'
        f'<link rel="canonical" href="{ORIGIN}{ONE}">'
        f'<meta property="og:url" content="{ORIGIN}{ONE}">'
        '<meta property="og:title" content="Engineer">'
        f'<meta property="og:image" content="{ORIGIN}/og/jobs/1/123.jpg">'
        '<a href="https://employer.example.org/apply">Apply now</a>'
    )
    batch, _ = run(bodies={ONE: body})
    job = batch.jobs[0]
    assert job.external_id == "1" and job.remote_status == "Remote" and job.location == ""
    assert job.salary == {"source_text": "£50,000 yearly"} and job.published_at is None
    assert job.raw["jobposting"] is None and job.raw["html_observation"]["description_html"]
    assert job.quality_flags == ["jobposting_schema_missing"]
    for bad in (
        body.replace('property="og:title"', 'property="unrelated"'),
        body.replace('property="og:url"', 'property="unrelated"'),
        body.replace("/og/jobs/1/123.jpg", "/other/image.jpg"),
        body.replace('class="rich-text"', 'class="other"'),
    ):
        with pytest.raises(ValueError):
            run(bodies={ONE: bad})


def test_multiple_pages_require_correct_ranges_and_terminal_control():
    batch, requests = run(
        pages={1: page([ONE], next_page=2), 2: page([TWO], start=2)},
        bodies={ONE: detail(), TWO: detail(TWO, 2)},
    )
    assert batch.complete and len(batch.jobs) == 2
    assert any("page=2" in request for request in requests)


@pytest.mark.parametrize(
    "bad_page",
    [
        "<html>Unavailable</html>",
        page([]),
        page([ONE], start=2),
        page([ONE]).replace('aria-disabled="true"', 'aria-disabled="false"'),
        page([ONE], next_page=2).replace("/jobs?page=2", "https://evil.com/jobs?page=2"),
        page([ONE], next_page=3),
        page([ONE]).replace("<span>1</span>", "<span>3</span>"),
    ],
)
def test_incomplete_or_malformed_pagination_fails(bad_page):
    with pytest.raises((ValueError, KeyError)):
        run(pages={1: bad_page})


def test_repeated_pages_wrong_detail_ids_and_changed_first_page_fail():
    cases = [
        {"pages": {1: page([ONE], next_page=2), 2: page([ONE], start=2)}},
        {
            "pages": {1: page([ONE], next_page=2), 2: page([TWO], start=2)},
            "bodies": {ONE: detail(), TWO: detail(TWO, 1)},
        },
        {"confirmation": page([TWO])},
    ]
    for kwargs in cases:
        with pytest.raises(ValueError):
            run(**kwargs)


@pytest.mark.parametrize(
    "body",
    [
        detail(schema=False),
        detail(apply=False),
        detail(canonical=False),
        detail().replace("https://employer.example.org/jobs/engineer/apply", "javascript:alert(1)"),
        detail().replace('rel="canonical"', 'rel="unrelated"'),
        detail() + '<div class="flex items-center text-sm">Remote</div>',
    ],
)
def test_missing_private_or_ambiguous_details_rejected(body):
    with pytest.raises(ValueError):
        run(bodies={ONE: body})


def test_robots_disallow_is_respected():
    with pytest.raises(ValueError, match="robots"):
        run(robots="User-agent: *\nDisallow: /jobs")


def test_over_budget_roster_fails_before_any_detail_fetch(monkeypatch):
    monkeypatch.setattr("vindex.connectors.jobboardly.MAX_DETAILS", 1)
    requests = []
    with pytest.raises(ValueError, match="detail budget"):
        run(pages={1: page([ONE], next_page=2), 2: page([TWO], start=2)}, requests_out=requests)
    assert requests == [ORIGIN + "/robots.txt", ORIGIN + "/jobs", ORIGIN + "/jobs?page=2"]


def test_changes_on_later_page_are_reconfirmed_even_when_first_page_stays_same():
    async def check():
        counts = {1: 0, 2: 0}

        def handler(request):
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text="User-agent: *\nAllow: /")
            if request.url.path == "/jobs":
                number = int(request.url.params.get("page", "1"))
                counts[number] += 1
                body = (
                    page([ONE], next_page=2)
                    if number == 1
                    else page([TWO if counts[2] == 1 else "/jobs/changed-cccccccc"], start=2)
                )
                return httpx.Response(200, text=body)
            return httpx.Response(
                200, text=detail(ONE, 1) if request.url.path == ONE else detail(TWO, 2)
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await create_connector("jobboardly", "example", "Board", client).discover()

    with pytest.raises(ValueError, match="listing changed"):
        asyncio.run(check())


def test_hosted_board_detection_and_unsafe_suffix_rejection():
    assert detect(ORIGIN + ONE) == ("jobboardly", "example")
    for url in ("https://a.b.jobboardly.com/jobs", "https://example.jobboardly.com.evil.com/jobs"):
        with pytest.raises(ValueError):
            detect(url)

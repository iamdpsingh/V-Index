"""Controlled Recooty public-state identity/completeness regressions."""

import asyncio
import copy
import json

import httpx
import pytest
from vindex.connectors.registry import create_connector, detect

PATH = "/example/engineer-ex144"
TEAM = {"id": 1, "name": "Example", "slug": "example"}


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.recooty.asyncio.sleep", no_wait)


def listing():
    return dict(
        id=123,
        title="Engineer",
        slug="engineer-ex144",
        url=PATH,
        location="London, UK",
        employment_type="Full Time",
        location_type="Remote",
        created_at="2026-10-01",
    )


def detail():
    return dict(
        team=TEAM,
        job=dict(
            id=123,
            ulid="PUBLIC123",
            title="Engineer",
            slug="engineer-ex144",
            type="JOB_POST",
            status="OPEN",
            job_board_status="APPROVED",
            description_html="<p>Build</p>",
            employment_type_label="Full Time",
            location_type_label="Remote",
            location={"display": "London, UK"},
            pay={"min": 50000, "max": 60000, "currency": "GBP", "interval": "YEAR"},
            published_at_iso="2026-11-01T09:00:00Z",
        ),
        json_ld={
            "@type": "JobPosting",
            "title": "Engineer",
            "url": "https://careerspage.io" + PATH,
            "hiringOrganization": {"name": "Example"},
            "identifier": {"value": "PUBLIC123"},
        },
        seo={"canonical_url": "https://careerspage.io" + PATH},
    )


def page(component, props, total=1):
    return (
        "<html><body>"
        + f'<p>{total} open positions</p><a href="{PATH}">Engineer</a><a href="{PATH}/apply">Apply</a><script>'
        + json.dumps({"component": component, "props": props}, separators=(",", ":"))
        + "</script></body></html>"
    )


def run(board=None, job=None, confirm=None, total=1, status=200, robots="User-agent: *\nAllow: /"):
    calls = 0

    async def discover():
        def handler(request):
            nonlocal calls
            assert request.url.host == "careerspage.io"
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text=robots)
            if request.url.path == "/example":
                calls += 1
                props = confirm if calls > 1 and confirm is not None else board
                return httpx.Response(
                    200,
                    text=page(
                        "CareersPage/Index",
                        props if props is not None else {"team": TEAM, "job_posts": [listing()]},
                        total,
                    ),
                )
            assert request.url.path == PATH
            return httpx.Response(
                status,
                text=page("CareersPage/JobDescription", job if job is not None else detail()),
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await create_connector("recooty", "example", "Configured", client).discover()

    return asyncio.run(discover())


def test_public_state_preserves_complete_job_and_actual_publication():
    batch = run()
    job = batch.jobs[0]
    assert batch.complete and job.external_id == "123" and job.company == "Example"
    assert (
        job.description == "Build"
        and job.location == "London, UK"
        and job.remote_status == "Remote"
    )
    assert job.application_url == job.source_url + "/apply" and job.salary["currency"] == "GBP"
    assert job.published_at.month == 11 and job.raw["listing"]["created_at"] == "2026-10-01"
    assert job.raw["team"] == TEAM and "auth" not in job.raw


@pytest.mark.parametrize(
    "mutation",
    [
        lambda b: b.update(job_posts=[]),
        lambda b: b["team"].update(slug="other"),
        lambda b: b["job_posts"][0].update(id=True),
        lambda b: b["job_posts"][0].update(url="https://evil.com/"),
        lambda b: b["job_posts"][0].update(url="/example/../private"),
        lambda b: b["job_posts"][0].update(title="Other"),
    ],
)
def test_unsafe_or_unidentified_collection_aborts(mutation):
    board = copy.deepcopy({"team": TEAM, "job_posts": [listing()]})
    mutation(board)
    with pytest.raises(ValueError):
        run(board=board)


def test_partial_count_and_duplicate_jobs_abort():
    for board, total in ((None, 2), ({"team": TEAM, "job_posts": [listing(), listing()]}, 2)):
        with pytest.raises(ValueError):
            run(board=board, total=total)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d["job"].update(id=True),
        lambda d: d["job"].update(status="CLOSED"),
        lambda d: d["job"].update(job_board_status="REJECTED"),
        lambda d: d["job"].update(title="Other"),
        lambda d: d["json_ld"]["identifier"].update(value="Different"),
        lambda d: d["json_ld"]["hiringOrganization"].update(name="Other"),
        lambda d: d["seo"].update(canonical_url="https://evil.com/"),
        lambda d: d["job"].update(location_type_label="On Site"),
        lambda d: d["job"].pop("description_html"),
    ],
)
def test_mismatched_closed_or_incomplete_detail_aborts(mutation):
    job = copy.deepcopy(detail())
    mutation(job)
    with pytest.raises((ValueError, KeyError)):
        run(job=job)


def test_request_failure_robots_and_changed_full_roster_abort():
    changed = {"team": TEAM, "job_posts": [listing()]}
    changed["job_posts"][0]["created_at"] = "2026-10-02"
    for kwargs in ({"status": 404}, {"robots": "User-agent: *\nDisallow: /"}, {"confirm": changed}):
        with pytest.raises(ValueError):
            run(**kwargs)


def test_recooty_host_detection():
    assert detect("https://careerspage.io" + PATH) == ("recooty", "example")
    for url in (
        "https://careerspage.io/",
        "https://careerspage.io.evil.com/example",
        "https://careerspage.io/%2e%2e",
    ):
        with pytest.raises(ValueError):
            detect(url)

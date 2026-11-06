"""Controlled GoHire failure/completeness cases; not live coverage evidence."""

import asyncio
import copy
import json

import httpx
import pytest
from vindex.connectors.registry import create_connector, detect

SLUG = "example-abcd1234"
BOARD = f"https://jobs.gohire.io/{SLUG}/"
LINK = BOARD + "engineer-123/"


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.gohire.asyncio.sleep", no_wait)


def board(total=1, key="aBcD1234"):
    return f'''<html><head><title>Jobs at Example</title>
    <script src="https://widget.gohire.io/widget/{key}"></script></head>
    <body><p>{total} Job openings</p><a class="gohire-job" href="{LINK}">
    <h3 class="job-title">Engineer</h3></a></body></html>'''


def collection():
    return dict(
        generalApplication=1,
        generalPoolID=999,
        template=None,
        colour="#000000",
        language="en",
        jobs=[
            dict(
                id=123,
                title="Engineer",
                description="",
                location="Remote, UK",
                salary="50000 GBP Per annum",
                type="Permanent",
                date="04 November, 2026",
                link=LINK,
            )
        ],
    )


def detail():
    return dict(
        id=123,
        title="Engineer",
        client=dict(id=99, name="Example", uploadFields="exclude"),
        description="<p>Build systems</p>",
        type=dict(id=1, name="Permanent"),
        city="Remote",
        county="",
        postcode="",
        country=dict(name="UK"),
        salary="50000 GBP Per annum",
        isGeneralPool=0,
        questions=[{"private_form_configuration": True}],
    )


def run(feed=None, job=None, html=None, confirm=None, status=200, deny_host=None):
    calls = 0

    async def discover():
        def handler(request):
            nonlocal calls
            if request.url.path == "/robots.txt":
                return httpx.Response(
                    200,
                    text="User-agent: *\n"
                    + ("Disallow: /" if request.url.host == deny_host else "Allow: /"),
                )
            if request.url.host == "jobs.gohire.io":
                assert str(request.url) == BOARD
                return httpx.Response(200, text=html if html is not None else board())
            if request.url.host == "api2.gohire.io":
                assert request.url.path == "/widget-jobs/aBcD1234"
                assert not request.url.query
                calls += 1
                value = confirm if calls > 1 and confirm is not None else feed
                return httpx.Response(200, json=value if value is not None else collection())
            assert request.url.host == "api.gohire.io"
            assert dict(request.url.params) == {"clientHash": "aBcD1234", "jobId": "123"}
            return httpx.Response(status, json=job if job is not None else detail())

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await create_connector("gohire", SLUG, "Configured", client).discover()

    return asyncio.run(discover())


def test_total_collection_detail_and_sanitized_original_fields():
    batch = run()
    job = batch.jobs[0]
    assert batch.complete and len(batch.jobs) == 1
    assert job.company == "Example" and job.description == "Build systems"
    assert job.source_url == job.application_url == LINK
    assert job.remote_status == "Remote" and job.published_at.day == 4
    assert job.salary == {"source_text": "50000 GBP Per annum"}
    assert job.raw["listing"] == collection()["jobs"][0]
    assert job.raw["detail"]["client"] == {"id": 99, "name": "Example"}
    assert "questions" not in json.dumps(job.raw) and "uploadFields" not in json.dumps(job.raw)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda p: p.update(jobs=[]),
        lambda p: p.update(language="fr"),
        lambda p: p.update(next="/page2"),
        lambda p: p["jobs"][0].update(id=True),
        lambda p: p["jobs"][0].update(link="https://evil.com/engineer-123/"),
        lambda p: p["jobs"][0].update(link=BOARD + "engineer-124/"),
        lambda p: p["jobs"][0].update(title="Different"),
    ],
)
def test_partial_or_mismatched_feed_aborts(mutation):
    feed = collection()
    mutation(feed)
    with pytest.raises(ValueError):
        run(feed=feed)


@pytest.mark.parametrize(
    "html",
    [
        board(0),
        board(401),
        board(2),
        board(key="zzzz1234"),
        board().replace("</html>", ""),
        board().replace("Job openings", "results"),
    ],
)
def test_invalid_board_aborts(html):
    with pytest.raises(ValueError):
        run(html=html)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d.update(id=True),
        lambda d: d.update(title="Other"),
        lambda d: d.update(isGeneralPool=1),
        lambda d: d["client"].update(name="Other"),
        lambda d: d.update(salary="60000 GBP Per annum"),
        lambda d: d.pop("description"),
    ],
)
def test_wrong_or_changed_detail_aborts(mutation):
    job = detail()
    mutation(job)
    with pytest.raises((ValueError, KeyError)):
        run(job=job)


def test_failed_detail_changed_collection_and_robots_denial():
    changed = copy.deepcopy(collection())
    changed["jobs"][0]["date"] = "05 November, 2026"
    for kwargs in (
        {"status": 404},
        {"confirm": changed},
        *({"deny_host": h} for h in ("jobs.gohire.io", "api.gohire.io", "api2.gohire.io")),
    ):
        with pytest.raises(ValueError):
            run(**kwargs)


def test_detection_and_host_path_restrictions():
    assert detect(LINK) == ("gohire", SLUG)
    for url in (
        "https://jobs.gohire.io/",
        "https://jobs.gohire.io/example/",
        "https://jobs.gohire.io.evil.com/" + SLUG,
    ):
        with pytest.raises(ValueError):
            detect(url)

"""JazzHR public hosted template safety tests, not live coverage evidence."""

import asyncio
import json

import httpx
import pytest
from vindex.connectors.registry import create_connector, detect

ORIGIN = "https://example.applytojob.com"
URL = ORIGIN + "/apply/44S77f7QPr/Engineer"


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.jazzhr.asyncio.sleep", no_wait)


def document(body):
    return "<!DOCTYPE html><html><body>" + body + "</body></html>"


def listings(url=URL, title="Engineer"):
    return document(
        '<div class="jobs-list"><h2>Current Openings</h2><ul class="list-group">'
        f'<li><h3 class="list-group-item-heading"><a href="{url}">{title}</a></h3></li>'
        "</ul></div>"
    )


def detail():
    return document(
        f'<link rel="canonical" href="{URL}">'
        '<div class="job-header"><h2>Engineer</h2><div title="Location">Remote</div>'
        '<div id="resumator-job-employment">Full Time</div></div>'
        '<div id="job-description"><p>Build systems</p></div>'
        f'<form id="form_submit_new_resume" method="POST" action="{URL}">'
        '<input name="private_form_token" value="must-not-be-stored"></form>'
        '<script type="application/ld+json">'
        + json.dumps({"@type": "Organization", "name": "Example"})
        + "</script>"
    )


def run(board=None, body=None, confirmation=None, status=200, robots="User-agent: *\nAllow: /"):
    calls = 0
    requests = []

    async def discover():
        def handler(request):
            nonlocal calls
            assert request.method == "GET"
            requests.append(str(request.url))
            assert request.url.host == "example.applytojob.com"
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text=robots)
            if request.url.path == "/apply":
                calls += 1
                content = confirmation if calls > 1 and confirmation is not None else board
                return httpx.Response(200, text=content if content is not None else listings())
            assert str(request.url) == URL
            return httpx.Response(status, text=body if body is not None else detail())

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await create_connector("jazzhr", "example", "Configured name", client).discover()

    return asyncio.run(discover()), requests


def test_jazzhr_public_native_application_and_original_description():
    batch, requests = run()
    job = batch.jobs[0]
    assert batch.complete and job.external_id == "44S77f7QPr" and job.company == "Example"
    assert job.description == "Build systems" and job.location == "Remote"
    assert job.remote_status == "Remote" and job.employment_type == "Full Time"
    assert job.published_at is None and job.source_url == job.application_url == URL
    assert "private_form_token" not in json.dumps(job.raw)
    assert len(requests) == 4


@pytest.mark.parametrize(
    "board",
    [
        "<html>Truncated",
        document("<div>Unavailable</div>"),
        listings().replace("Current Openings", "Other"),
        listings(url="https://evil.com/apply/44S77f7QPr/Engineer"),
        listings(url=ORIGIN + "/apply/44S77f7QPr/%2e%2e"),
        listings().replace("</ul>", '<li class="pagination">More</li></ul>'),
        listings().replace(
            "</ul>", f'<li class="list-group-item-heading"><a href="{URL}">Engineer</a></li></ul>'
        ),
    ],
)
def test_malformed_partial_or_duplicate_current_openings_fails(board):
    with pytest.raises((ValueError, KeyError)):
        run(board=board)


@pytest.mark.parametrize(
    "body",
    [
        detail().replace("</html>", ""),
        detail().replace('rel="canonical"', 'rel="unrelated"'),
        detail().replace("<h2>Engineer</h2>", "<h2>Different opening</h2>"),
        detail().replace('id="job-description"', 'id="unrelated"'),
        detail().replace('method="POST"', 'method="GET"'),
        detail().replace('id="form_submit_new_resume"', 'id="unrelated"'),
        detail().replace('"@type": "Organization"', '"@type": "Other"'),
    ],
)
def test_incomplete_or_wrong_detail_fails(body):
    with pytest.raises(ValueError):
        run(body=body)


def test_changed_board_failed_detail_and_robots_denial_fail():
    for kwargs in (
        {"confirmation": listings(title="Changed")},
        {"status": 404},
        {"robots": "User-agent: *\nDisallow: /apply"},
    ):
        with pytest.raises(ValueError):
            run(**kwargs)


def test_jazzhr_hosted_detection_and_suffix_rejection():
    assert detect(URL) == ("jazzhr", "example")
    for url in (
        "https://example.applytojob.com.evil.com/apply",
        "https://a.b.applytojob.com/apply",
    ):
        with pytest.raises(ValueError):
            detect(url)

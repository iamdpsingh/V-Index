"""Controlled hosted Jobvite full-table and identity regressions; not live evidence."""

import asyncio

import httpx
import pytest
from vindex.connectors.registry import create_connector, detect

PATH = "/example/job/Ab123456"


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.jobvite.asyncio.sleep", no_wait)


def board():
    return f'''<html><head><title>Example Careers</title></head><body><h2>Open Positions</h2>
    <table class="jv-job-list"><td class="jv-job-list-name"><a href="{PATH}">Engineer</a></td></table>
    <script>careersiteName: 'example'</script></body></html>'''


def detail():
    return f'''<html><head><title>Example Careers - Engineer</title></head><body><h2 class="jv-header">Engineer</h2>
    <p class="jv-job-detail-meta">Engineering<span></span>London, UK<span></span>Remote, UK</p>
    <div class="jv-job-detail-description"><p>Build systems</p></div><a href="{PATH}/apply">Apply</a>
    <script>jobId: 'Ab123456', jobCategoryName: 'Engineering'</script></body></html>'''


def run(html=None, job=None, confirm=None, status=200, robots="User-agent: *\nAllow: /"):
    calls = 0

    async def discover():
        def handler(request):
            nonlocal calls
            assert request.url.host == "jobs.jobvite.com"
            assert not request.url.query
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text=robots)
            if request.url.path == "/example/jobs":
                calls += 1
                value = confirm if calls > 1 and confirm is not None else html
                return httpx.Response(200, text=value if value is not None else board())
            assert request.url.path == PATH
            return httpx.Response(status, text=job if job is not None else detail())

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await create_connector("jobvite", "example", "Configured", client).discover()

    return asyncio.run(discover())


def test_full_table_and_matching_detail_preserve_multiple_locations():
    batch = run()
    job = batch.jobs[0]
    assert batch.complete and job.external_id == "Ab123456" and job.company == "Example"
    assert job.location == "London, UK; Remote, UK" and job.remote_status == "Remote"
    assert job.description == "Build systems" and job.application_url == job.source_url + "/apply"
    assert job.published_at is None and job.salary is None and job.employment_type is None
    assert job.raw["category"] == "Engineering"


@pytest.mark.parametrize(
    "replacement",
    [
        ("Open Positions", "Results"),
        ("careersiteName: 'example'", "careersiteName: 'other'"),
        (PATH, "https://evil.com" + PATH),
        ("jv-job-list-name", "unknown"),
        ("</html>", ""),
        ("</body>", '<a rel="next" href="?page=2">Next</a></body>'),
    ],
)
def test_incomplete_or_unsafe_list_aborts(replacement):
    with pytest.raises(ValueError):
        run(html=board().replace(*replacement))


@pytest.mark.parametrize(
    "replacement",
    [
        ("jobId: 'Ab123456'", "jobId: 'Cd123456'"),
        ("Example Careers - Engineer", "Other Careers - Engineer"),
        ("jv-header", "other-header"),
        ("jv-job-detail-description", "other-description"),
        (PATH + "/apply", "/example/job/Cd123456/apply"),
        ("jobCategoryName: 'Engineering'", "jobCategoryName: 'Sales'"),
        ("</html>", ""),
    ],
)
def test_mismatched_or_closed_detail_aborts(replacement):
    with pytest.raises(ValueError):
        run(job=detail().replace(*replacement))


def test_duplicate_list_and_failed_requests_do_not_complete():
    duplicate = board().replace(
        "</table>", f'<td class="jv-job-list-name"><a href="{PATH}">Engineer</a></td></table>'
    )
    for kwargs in (
        {"html": duplicate},
        {"status": 404},
        {"robots": "User-agent: *\nDisallow: /"},
        {"confirm": board().replace("Engineer", "Other")},
    ):
        with pytest.raises(ValueError):
            run(**kwargs)


def test_host_validation():
    assert detect("https://jobs.jobvite.com" + PATH) == ("jobvite", "example")
    for url in (
        "https://jobs.jobvite.com/",
        "https://jobs.jobvite.com.evil.com/example",
        "https://jobs.jobvite.com/%2e%2e",
    ):
        with pytest.raises(ValueError):
            detect(url)

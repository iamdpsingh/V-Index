"""HireBridge public location totals, customer identity and application link checks."""

import asyncio

import httpx
import pytest
from vindex.connectors.registry import create_connector, detect

ORIGIN = "https://recruit.hirebridge.com"
LIST = "/v3/Jobs/list.aspx?cid=7"
PATH = "/v3/Jobs/JobDetails.aspx?cid=7&jid=12"
APPLY = ORIGIN + "/v3/applicationv2/JobApplylogin.aspx?cid=7&jid=12"
LOGO = ORIGIN + "/v3/xFiles/7/MyLibrary/logo.png"


def board():
    return f'''<html><title>Example Career Center</title><img src="{LOGO}">
    <form id="aspnetForm" action="./list.aspx?cid=7"><h1>Open Positions</h1>
    <select id="public_jobloc"><option value="">All Locations</option><option value="1">Remote - UK (1)</option></select>
    <h2>Remote - UK</h2><ul class="jobs"><li><span class="job"><a href="{PATH}">Engineer</a></span><span class="department">Engineering</span></li></ul></form></html>'''


def detail():
    return f'''<html><img src="{LOGO}"><form id="aspnetForm" action="./JobDetails.aspx?cid=7&jid=12">
    <h1>Engineer</h1><h2>Remote - UK</h2><a href="javascript:popUp('{APPLY}')">Apply</a>
    <span id="public_jobdesc"><p>Build systems</p></span><span id="public_skilldesc"><p>Python</p></span></form></html>'''


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.hirebridge.asyncio.sleep", no_wait)


def run(html=None, body=None, confirm=None, status=200, robots="User-agent: *\nAllow: /"):
    calls = 0

    async def discover():
        def handle(request):
            nonlocal calls
            assert request.url.host == "recruit.hirebridge.com"
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text=robots)
            if request.url.path == "/v3/Jobs/list.aspx":
                assert str(request.url) == ORIGIN + LIST
                calls += 1
                return httpx.Response(
                    200, text=confirm if calls > 1 and confirm is not None else html or board()
                )
            assert str(request.url) == ORIGIN + PATH
            return httpx.Response(status, text=body or detail())

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await create_connector("hirebridge", "7", "Configured", client).discover()

    return asyncio.run(discover())


def test_complete_location_counted_public_list_preserves_all_description_sections():
    batch = run()
    j = batch.jobs[0]
    assert batch.complete and j.company == "Example" and j.external_id == "12"
    assert j.description == "Build systems\n\nPython" and j.location == "Remote - UK"
    assert j.remote_status == "Remote - UK" and j.application_url == APPLY
    assert j.published_at is None and j.employment_type is None
    assert detect(ORIGIN + LIST) == ("hirebridge", "7")


@pytest.mark.parametrize(
    "replacement",
    [
        ("(1)</option>", "(2)</option>"),
        ('value="1"', 'value="1" selected="selected"'),
        ("Career Center", "Unknown"),
        ("Open Positions", "Unknown"),
        ("</html>", ""),
        ("cid=7&jid=12", "cid=8&jid=12"),
        ("xFiles/7/", "xFiles/8/"),
        ("</ul>", '</ul><a href="/v3/Jobs/JobDetails.aspx?cid=7&jid=13">Other</a>'),
    ],
)
def test_partial_filtered_or_unsafe_roster_aborts(replacement):
    with pytest.raises(ValueError):
        run(html=board().replace(*replacement))


@pytest.mark.parametrize(
    "replacement",
    [
        ("<h1>Engineer", "<h1>Other"),
        ("<h2>Remote - UK", "<h2>London"),
        ("cid=7&jid=12", "cid=7&jid=13"),
        ("xFiles/7/", "xFiles/8/"),
        ("public_jobdesc", "public_missing"),
        ("javascript:popUp", "javascript:malicious"),
        ("https://recruit.hirebridge.com/v3/applicationv2", "https://evil.com/v3/applicationv2"),
    ],
)
def test_detail_customer_title_location_or_application_mismatch_aborts(replacement):
    with pytest.raises(ValueError):
        run(body=detail().replace(*replacement))


def test_changed_description_metadata_roster_aborts():
    with pytest.raises(ValueError):
        run(confirm=board().replace("Engineering", "Other"))


def test_failed_request_is_not_complete_empty_result():
    with pytest.raises(httpx.HTTPStatusError):
        run(status=503)


def test_robots_denial_aborts():
    with pytest.raises(ValueError):
        run(robots="User-agent: *\nDisallow: /v3/Jobs/JobDetails.aspx")


@pytest.mark.parametrize(
    "url",
    [
        ORIGIN + LIST + "&location=1",
        ORIGIN + LIST + "&cid=8",
        ORIGIN + "/v3/Jobs/list.aspx?cid=0",
        ORIGIN + PATH,
    ],
)
def test_registration_rejects_filters_duplicates_and_job_urls(url):
    with pytest.raises(ValueError):
        detect(url)


def test_upstream_long_cooldown_is_recorded_without_retrying_early(monkeypatch):
    from vindex.connectors.hirebridge import HireBridgeConnector

    calls = []

    async def discover():
        def handle(request):
            calls.append(request.url.path)
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text="User-agent: *\nAllow: /")
            return httpx.Response(429, headers={"Retry-After": "900"})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await HireBridgeConnector("hirebridge", "7", "Example", client).discover()

    with pytest.raises(ValueError, match="Retry-After=900"):
        asyncio.run(discover())
    assert calls == ["/robots.txt", "/v3/Jobs/list.aspx"]

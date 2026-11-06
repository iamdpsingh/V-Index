"""Controlled legacy Manatal paging/detail safety cases; not live evidence."""

import asyncio
import copy

import httpx
import pytest
from vindex.connectors.registry import create_connector, detect

ORIGIN = "https://www.careers-page.com"
BOARD = ORIGIN + "/example"
API = "/api/v1.0/c/example/jobs/"
ORDER = "-is_pinned_in_career_page,-last_published_at"


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.manatal.asyncio.sleep", no_wait)


def row(identifier="AAAA1111", number=1):
    return dict(
        id=number,
        hash=identifier,
        position_name="Engineer",
        description="<p>Build systems</p>",
        city="London",
        state="",
        country="UK",
        location_display="",
        is_salary_visible=True,
        currency_code="GBP",
        salary_min="50000",
        salary_max="60000",
    )


def board(total=1):
    return f"""<html><head><title> - Example | Career Page</title></head><body>
    <h4 class="positions">{total} Open Positions</h4><script>const clientSlug = "example";</script>
    <a href="/example/job/AAAA1111"><h5>Engineer</h5></a></body></html>"""


def detail(item=None):
    item = item or row()
    name = item["position_name"]
    identifier = item["hash"]
    return f'''<html><head><title>{name} - Example | Career Page</title>
    <meta property="og:title" content="{name} - Example | Career Page"><meta property="og:site_name" content="Manatal"></head><body>
    <h1 class="job-position-break">{name}</h1><a href="/example">Job Openings</a>
    <div class="redactor-styles">{item["description"]}</div><a href="/example/job/{identifier}/apply">Apply</a></body></html>'''


def page_link(page):
    return f"{ORIGIN}{API}?page_size=50&page={page}&ordering={ORDER}"


def feed():
    return dict(count=1, results=[row()], next=None, previous=None)


def run(
    data=None,
    html=None,
    job=None,
    confirm=None,
    paged=False,
    status=200,
    robots="User-agent: *\nAllow: /",
):
    calls = 0

    async def discover():
        def handler(request):
            nonlocal calls
            assert request.url.host == "www.careers-page.com"
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text=robots)
            if request.url.path == "/example":
                return httpx.Response(
                    200, text=html if html is not None else board(2 if paged else 1)
                )
            if request.url.path == API:
                assert dict(request.url.params) == {
                    "page_size": "50",
                    "page": request.url.params["page"],
                    "ordering": ORDER,
                }
                calls += 1
                if paged:
                    second = request.url.params["page"] == "2"
                    value = dict(
                        count=2,
                        results=[row("BBBB2222", 2) if second else row()],
                        next=None if second else page_link(2),
                        previous=page_link(1) if second else None,
                    )
                    if calls > 2 and second and confirm is not None:
                        value = confirm
                else:
                    value = confirm if calls > 1 and confirm is not None else data
                    value = value if value is not None else feed()
                return httpx.Response(200, json=value)
            item = row("BBBB2222", 2) if request.url.path.endswith("BBBB2222") else row()
            assert request.url.path in ("/example/job/AAAA1111", "/example/job/BBBB2222")
            return httpx.Response(status, text=job if job is not None else detail(item))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await create_connector("manatal", "example", "Configured", client).discover()

    return asyncio.run(discover())


def test_complete_public_fields_and_real_application_entry():
    batch = run()
    job = batch.jobs[0]
    assert batch.complete and job.external_id == "AAAA1111" and job.company == "Example"
    assert job.location == "London, UK" and job.description == "Build systems"
    assert (
        job.source_url == BOARD + "/job/AAAA1111"
        and job.application_url == job.source_url + "/apply"
    )
    assert job.salary == {"currency_code": "GBP", "salary_min": "50000", "salary_max": "60000"}
    assert job.published_at is None and job.employment_type is None and job.remote_status is None
    assert job.raw["listing"] == row()


def test_pagination_and_full_later_page_reconfirmation():
    batch = run(paged=True)
    assert batch.complete and [j.external_id for j in batch.jobs] == ["AAAA1111", "BBBB2222"]
    changed = dict(count=2, results=[row("BBBB2222", 2)], next=None, previous=page_link(1))
    changed["results"][0]["description"] = "<p>Changed</p>"
    with pytest.raises(ValueError, match="changed"):
        run(paged=True, confirm=changed)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d.update(count=True),
        lambda d: d.update(count=2),
        lambda d: d.update(results=[]),
        lambda d: d.update(next="https://evil.com/page2"),
        lambda d: d.update(previous=page_link(1)),
        lambda d: d["results"][0].update(hash="../bad"),
        lambda d: d["results"][0].update(id=True),
        lambda d: d["results"][0].update(position_name="Other"),
    ],
)
def test_malformed_partial_or_unsafe_collection_aborts(mutation):
    data = feed()
    mutation(data)
    with pytest.raises(ValueError):
        run(data=data)


def test_pagination_next_url_is_checked_before_fetch():
    data = feed()
    data["count"] = 2
    for url in (
        page_link(3),
        page_link(2) + "&country=UK",
        page_link(2).replace("example", "other"),
    ):
        data["next"] = url
        with pytest.raises(ValueError):
            run(data=data, html=board(2))


@pytest.mark.parametrize(
    "html",
    [
        board(0),
        board(401),
        board().replace('example";', 'other";'),
        board().replace("</html>", ""),
        board().replace("Open Positions", "Positions"),
    ],
)
def test_bad_board_identity_and_size_aborts(html):
    with pytest.raises(ValueError):
        run(html=html)


@pytest.mark.parametrize(
    "replacement",
    [
        ("Example | Career Page", "Other | Career Page"),
        ("/AAAA1111/apply", "/BBBB2222/apply"),
        ("job-position-break", "other-heading"),
        ("Build systems", "Changed description"),
        ('content="Manatal"', 'content="Other"'),
        ("</html>", ""),
    ],
)
def test_mismatched_or_partial_details_abort(replacement):
    with pytest.raises(ValueError):
        run(job=detail().replace(*replacement))


def test_failed_request_changed_roster_and_robots_denial():
    changed = copy.deepcopy(feed())
    changed["results"][0]["salary_min"] = "55000"
    for kwargs in ({"status": 404}, {"confirm": changed}, {"robots": "User-agent: *\nDisallow: /"}):
        with pytest.raises(ValueError):
            run(**kwargs)


def test_hidden_salary_not_promoted_and_unprovided_fields_not_invented():
    data = feed()
    data["results"][0]["is_salary_visible"] = False
    job = run(data=data).jobs[0]
    assert job.salary is None and job.raw["listing"]["salary_min"] == "50000"


def test_manatal_detection_requires_canonical_host_and_slug():
    assert detect(BOARD + "/job/AAAA1111") == ("manatal", "example")
    for url in (
        "https://www.careers-page.com/",
        "https://www.careers-page.com.evil.com/example",
        "https://www.careers-page.com/%2e%2e",
    ):
        with pytest.raises(ValueError):
            detect(url)

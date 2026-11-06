import asyncio
import copy
import json
from pathlib import Path

import httpx
import pytest
from defusedxml.common import DefusedXmlException
from vindex.connectors.recruitee import RecruiteeConnector
from vindex.connectors.registry import create_connector, detect
from vindex.connectors.workday import WorkdayConnector

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.workday.asyncio.sleep", no_wait)


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://imf.wd5.myworkdayjobs.com/en-US/IMF", ("workday", "imf~wd5~IMF")),
        (
            "https://gatesfoundation.wd1.myworkdayjobs.com/Gates/job/Seattle-WA/title_123",
            ("workday", "gatesfoundation~wd1~Gates"),
        ),
        ("https://natilik.recruitee.com/o/role", ("recruitee", "natilik")),
    ],
)
def test_cohort3_detection(url, expected):
    assert detect(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://imf.wd5.myworkdayjobs.com.evil.com/IMF",
        "https://foo.bar.wd5.myworkdayjobs.com/IMF",
        "https://imf.wd0.myworkdayjobs.com/IMF",
        "https://imf.wd5.myworkdayjobs.com/en-US",
        "https://imf.wd5.myworkdayjobs.com/%2e%2e",
        "https://natilik.recruitee.com.evil.com",
        "https://a.b.recruitee.com",
        "https://user@natilik.recruitee.com",
        "http://imf.wd5.myworkdayjobs.com/IMF",
    ],
)
def test_cohort3_url_rejection(url):
    with pytest.raises(ValueError):
        detect(url)


def sample(tenant="imf"):
    return json.loads((ROOT / f"evidence/workday-{tenant}-detail.json").read_text())


def test_workday_real_detail_samples():
    for tenant, site, dc in [("imf", "IMF", "wd5"), ("gatesfoundation", "Gates", "wd1")]:
        raw = sample(tenant)
        job = WorkdayConnector("workday", f"{tenant}~{dc}~{site}", "Example", None).parse(raw)[0]
        assert job.title == raw["jobPostingInfo"]["title"]
        assert job.external_id == raw["jobPostingInfo"]["id"]
        assert job.description and "<p>" not in job.description
        assert job.application_url == raw["jobPostingInfo"]["externalUrl"]
        assert job.published_at is None


def run_workday(handler):
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await create_connector("workday", "imf~wd5~IMF", "IMF", client).discover()

    return asyncio.run(run())


def list_row(raw):
    path = raw["jobPostingInfo"]["externalUrl"].split("/IMF")[1]
    return {"externalPath": path, "title": raw["jobPostingInfo"]["title"]}


def test_workday_multiple_pages_zero_later_total_and_final_confirmation():
    raw = sample()
    row = list_row(raw)
    second = copy.deepcopy(raw)
    second["jobPostingInfo"].update(
        id="second", externalUrl="https://imf.wd5.myworkdayjobs.com/IMF/job/US/Other_2"
    )
    calls = []
    starts = 0

    def handler(request):
        nonlocal starts
        calls.append(request)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        if request.method == "POST":
            data = json.loads(request.content)
            assert set(data) == {"appliedFacets", "limit", "offset", "searchText"}
            offset = data["offset"]
            if offset == 0:
                starts += 1
                return httpx.Response(200, json={"total": 2, "jobPostings": [row]})
            return httpx.Response(
                200, json={"total": 0, "jobPostings": [list_row(second)] if offset == 1 else []}
            )
        return httpx.Response(200, json=second if request.url.path.endswith("Other_2") else raw)

    batch = run_workday(handler)
    assert batch.complete and len(batch.jobs) == 2 and starts == 2
    assert len(calls) == 7  # robots, two details, two list pages, tail and final recheck.


@pytest.mark.parametrize(
    "failure",
    [
        "cap",
        "budget",
        "duplicate",
        "premature",
        "tail",
        "drift",
        "wrongdetail",
        "closed",
        "robots",
        "robots403",
        "redirect",
        "detail404",
    ],
)
def test_workday_partial_or_disallowed_enumeration_rejected(failure):
    raw = sample()
    row = list_row(raw)
    starts = 0

    def handler(request):
        nonlocal starts
        if request.url.path == "/robots.txt":
            if failure == "robots403":
                return httpx.Response(403)
            return httpx.Response(
                200,
                text="User-agent: *\nDisallow: /wday/"
                if failure == "robots"
                else "User-agent: *\nAllow: /",
            )
        if failure == "redirect":
            return httpx.Response(302, headers={"Location": "https://127.0.0.1/"})
        if request.method == "POST":
            offset = json.loads(request.content)["offset"]
            if offset == 0:
                starts += 1
                total = (
                    2000
                    if failure == "cap"
                    else (
                        401
                        if failure == "budget"
                        else (2 if failure in {"duplicate", "premature"} else 1)
                    )
                )
                return httpx.Response(
                    200,
                    json={
                        "total": total,
                        "jobPostings": [] if failure == "drift" and starts > 1 else [row],
                    },
                )
            rows = (
                [row]
                if failure == "duplicate"
                else ([{"externalPath": "/job/US/Unexpected_3"}] if failure == "tail" else [])
            )
            return httpx.Response(200, json={"total": 0, "jobPostings": rows})
        if failure == "detail404":
            return httpx.Response(404)
        detail = copy.deepcopy(raw)
        if failure == "wrongdetail":
            detail["jobPostingInfo"]["externalUrl"] = (
                "https://imf.wd5.myworkdayjobs.com/IMF/job/US/wrong"
            )
        if failure == "closed":
            detail["jobPostingInfo"]["posted"] = False
        return httpx.Response(200, json=detail)

    with pytest.raises(ValueError):
        run_workday(handler)


@pytest.mark.parametrize(
    "path",
    [
        "https://127.0.0.1/job/1",
        "/job/../private",
        "/job/%2e%2e/private",
        "/job/%252e/private",
        "/job/US/x?url=http://127.0.0.1",
        "/job/US/%2fprivate",
    ],
)
def test_workday_detail_path_rejection(path):
    with pytest.raises(ValueError):
        WorkdayConnector("workday", "imf~wd5~IMF", "IMF", None).path(path)


def test_robots_404_is_absent_but_long_delay_is_not_ignored():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nCrawl-delay: 60")
        pytest.fail("A disallowed pacing budget must not trigger job requests")

    with pytest.raises(ValueError, match="pacing"):
        run_workday(handler)

    def missing(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, json={"total": 0, "jobPostings": []})

    assert run_workday(missing).complete


def test_recruitee_actual_xml_samples():
    for slug in ["natilik", "bunq"]:
        jobs = RecruiteeConnector("recruitee", slug, "Example", None).parse(
            (ROOT / f"evidence/recruitee-{slug}-sample.xml").read_bytes()
        )
        assert len(jobs) == 1 and jobs[0].description and jobs[0].published_at
        assert jobs[0].application_url.startswith(
            "https://natilik.recruitee.com/" if slug == "natilik" else "https://careers.bunq.com/"
        )
        assert jobs[0].raw["xml"]


def test_recruitee_dtd_and_duplicate_ids_rejected():
    con = RecruiteeConnector("recruitee", "example", "Example", None)
    with pytest.raises(DefusedXmlException):
        con.parse(b'<!DOCTYPE offers [<!ENTITY x "bad">]><offers>&x;</offers>')

    async def run():
        xml = (ROOT / "evidence/recruitee-natilik-sample.xml").read_text()
        from defusedxml import ElementTree as E

        root = E.fromstring(xml)
        root.append(copy.deepcopy(root[0]))
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda r: httpx.Response(200, content=E.tostring(root)))
        ) as client:
            with pytest.raises(ValueError, match="Duplicate"):
                await create_connector("recruitee", "natilik", "Natilik", client).discover()

    asyncio.run(run())


def test_workday_observed_out_of_range_reset_is_terminal():
    rows = json.loads((ROOT / "evidence/workday-imf-boundary.json").read_text())
    assert rows[0]["offset"] == 0
    assert all(row["paths"] == rows[0]["paths"] for row in rows[1:])
    raw = sample()
    listing = list_row(raw)

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        if request.method == "POST":
            return httpx.Response(200, json={"total": 1, "jobPostings": [listing]})
        return httpx.Response(200, json=raw)

    result = run_workday(handler)
    assert result.complete and len(result.jobs) == 1

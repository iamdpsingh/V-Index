"""Complete native Deel boards, mandatory details and failure-safe reconciliation."""

import asyncio
import copy
import json

import httpx
import pytest
from vindex.connectors.deel import document, flight
from vindex.connectors.registry import create_connector, detect

ID = "11111111-1111-1111-1111-111111111111"
URL = "https://jobs.deel.com/example"
JOB = URL + "/job-details/" + ID + "/overview"


def row():
    return {
        "id": ID,
        "jobId": ID,
        "title": "Engineer",
        "richtextDescription": "$a",
        "isCompensationVisible": False,
        "createdAt": "2026-01-01T00:00:00Z",
        "updatedAt": "2026-01-01T00:00:00Z",
        "applicationFormId": "DO_NOT_RETAIN",
        "job": {
            "id": ID,
            "jobLocations": [{"location": {"name": "London"}}],
            "jobEmploymentTypes": [{"employmentType": {"name": "Full-time"}}],
            "currentCompensation": None,
            "workArrangementEnum": "REMOTE",
        },
        "jobPostingPublications": [
            {
                "jobBoard": {"id": "board"},
                "currentState": {
                    "stateSlug": "published_basic",
                    "createdByHrisOrganizationUserId": "DO_NOT_RETAIN",
                },
            }
        ],
    }


def ld(value):
    return '<script type="application/ld+json">' + json.dumps(value) + "</script>"


def board(rows=None, urls=None, tail=True):
    rows = [row()] if rows is None else rows
    props = {
        "careerPageSettings": {
            "urlSlug": "example",
            "preferredOrganizationName": "Example",
            "jobBoard": {"id": "board"},
        },
        "orgSlug": "example",
        "jobPostings": rows,
    }
    description = "<p>Build café systems.</p>"
    stream = (
        ':HL["asset"]\na:T'
        + format(len(description.encode()), "x")
        + ","
        + description
        + "b:"
        + json.dumps(["$", "$L1", None, props])
        + "\n"
    )
    return (
        "<html>"
        + ld({"@type": "Organization", "name": "Example", "url": URL})
        + ld(
            {
                "@type": "ItemList",
                "itemListElement": urls if urls is not None else [{"position": 1, "url": JOB}],
            }
        )
        + "<script>self.__next_f.push("
        + json.dumps([1, stream])
        + ")</script>"
        + ("</html>" if tail else "")
    ).encode()


def detail(**overrides):
    data = {
        "@type": "JobPosting",
        "title": "Engineer",
        "description": "Build café systems.",
        "url": JOB,
        "identifier": {"value": ID},
        "hiringOrganization": {"name": "Example"},
        "datePosted": "2026-01-01T00:00:00Z",
    }
    return ("<html>" + ld({**data, **overrides}) + "</html>").encode()


def run(shell=None, job=None, changed=False, fail=False):
    calls = 0

    async def main():
        def handler(request):
            nonlocal calls
            assert request.url.host == "jobs.deel.com" and request.method == "GET"
            assert "/api/" not in request.url.path and "/apply" not in request.url.path
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text="User-agent: *\nAllow: /")
            if str(request.url) == URL:
                calls += 1
                return httpx.Response(
                    200, content=board(rows=[]) if changed and calls > 1 else shell or board()
                )
            assert str(request.url) == JOB
            return httpx.Response(403 if fail else 200, content=job or detail())

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), trust_env=False
        ) as client:
            return await create_connector("deel", "example", "Ignored", client).discover()

    return asyncio.run(main())


@pytest.fixture(autouse=True)
def pacing(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.deel.asyncio.sleep", no_wait)


def test_complete_and_privacy():
    result = run()
    assert result.complete and len(result.jobs) == 1
    job = result.jobs[0]
    assert job.company == "Example" and job.location == "London"
    assert job.remote_status == "REMOTE" and job.employment_type == "Full-time"
    assert job.published_at.year == 2026 and job.application_url == JOB
    assert "DO_NOT_RETAIN" not in job.model_dump_json()
    assert detect(URL) == ("deel", "example")


@pytest.mark.parametrize(
    "url",
    [
        URL + "?search=x",
        URL + "/job-details/" + ID + "/overview",
        URL + "#filter",
        "https://jobs.deel.com.evil/example",
        "https://user@jobs.deel.com/example",
        "http://jobs.deel.com/example",
    ],
)
def test_reject_source_urls(url):
    with pytest.raises(ValueError):
        detect(url)


@pytest.mark.parametrize(
    "change", ["duplicate", "private", "missing_text", "bad_id", "mismatch_job", "unpublished"]
)
def test_bad_public_rosters(change):
    r = row()
    rows = [r]
    if change == "duplicate":
        rows.append(copy.deepcopy(r))
    elif change == "private":
        r["jobPostingPublications"][0]["jobBoard"]["id"] = "another"
    elif change == "missing_text":
        r["richtextDescription"] = "$dead"
    elif change == "bad_id":
        r["id"] = "../../internal"
    elif change == "mismatch_job":
        r["job"]["id"] = "other"
    else:
        r["jobPostingPublications"][0]["currentState"]["stateSlug"] = "unpublished"
    with pytest.raises(ValueError):
        run(shell=board(rows=rows))


@pytest.mark.parametrize(
    "change",
    [
        {"title": "Other"},
        {"description": "Partial"},
        {"url": "https://evil.example/job"},
        {"identifier": {"value": "other"}},
        {"hiringOrganization": {"name": "Other"}},
    ],
)
def test_detail_mismatch(change):
    with pytest.raises(ValueError):
        run(job=detail(**change))


def test_failure_never_complete():
    with pytest.raises(ValueError, match="403"):
        run(fail=True)
    with pytest.raises(ValueError):
        run(changed=True)
    with pytest.raises(ValueError):
        run(shell=board(urls=[]))
    with pytest.raises(ValueError):
        run(shell=board(tail=False))


@pytest.mark.parametrize("stream", ["a:T100,short", 'a:{"x":1}', "a:{}\na:{}\n", "x broken"])
def test_truncated_or_duplicate_flight(stream):
    html = "<html><script>self.__next_f.push(" + json.dumps([1, stream]) + ")</script></html>"
    with pytest.raises(ValueError):
        flight(document(html.encode()))


def test_hidden_compensation_not_invented():
    r = row()
    r["job"]["currentCompensation"] = {"currency": "GBP", "amount": 1}
    result = run(shell=board(rows=[r]))
    assert result.jobs[0].salary is None

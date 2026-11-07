"""Kula public visibility, completeness, detail identity and failure regressions."""

import asyncio
import copy
import json

import httpx
import pytest
from vindex.connectors.registry import create_connector, detect

ORIGIN = "https://careers.kula.ai"
PATH = "/example/12-engineer"


def listing():
    return {
        "id": 12,
        "account_id": 7,
        "title": "Engineer",
        "listed": True,
        "kind": "external",
        "is_confidential": False,
        "on_career_page": True,
        "launch_at": "2026-11-01T10:00:00Z",
        "end_at": None,
        "eeoc": {"private_config": "not retained"},
        "ats_job": {
            "job_description": "$23",
            "workplace": "remote",
            "employment_type": "full_time",
            "work_type_name": "Full time",
            "offices": [{"location": "London, UK"}],
        },
    }


def board(rows=None, links=None):
    stream = (
        "1:"
        + json.dumps(["$", "div", None, {"jobs": rows if rows is not None else [listing()]}])
        + "\n"
    )
    encoded = json.dumps([1, stream])
    return (
        '<html><script type="application/ld+json">{"@type":"Organization","name":"Example"}</script>'
        + f"<script>self.__next_f.push({encoded})</script>"
        + (links if links is not None else f'<a href="{PATH}">Apply Now</a>')
        + "</html>"
    )


def schema():
    return {
        "@type": "JobPosting",
        "title": "Engineer",
        "identifier": {"value": "12"},
        "hiringOrganization": {"name": "Example"},
        "directApply": True,
        "description": "<p>Build reliable systems</p>",
        "employmentType": "FULL_TIME",
        "datePosted": "2026-11-01T10:00:00Z",
        "baseSalary": {"currency": "GBP"},
    }


def detail(row=None):
    return f'''<html><link rel="canonical" href="{ORIGIN + PATH}">
    <script type="application/ld+json">{json.dumps(row or schema())}</script>
    <h1>Engineer</h1><button>Apply for this position</button><button>Application form</button></html>'''


def run(html=None, job=None, confirm=None, status=200, robots="User-agent: *\nAllow: /"):
    calls = 0

    async def discover():
        def handle(request):
            nonlocal calls
            assert request.url.host == "careers.kula.ai" and not request.url.query
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text=robots)
            if request.url.path == "/example":
                calls += 1
                return httpx.Response(
                    200, text=confirm if calls > 1 and confirm is not None else html or board()
                )
            assert request.url.path == PATH
            return httpx.Response(status, text=detail(job))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await create_connector("kula", "example", "Configured", client).discover()

    return asyncio.run(discover())


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.kula.asyncio.sleep", no_wait)


def test_complete_public_snapshot_preserves_fields_without_form_configuration():
    batch = run()
    job = batch.jobs[0]
    assert batch.complete and job.company == "Example" and job.external_id == "12"
    assert job.description == "Build reliable systems" and job.location == "London, UK"
    assert job.application_url == ORIGIN + PATH and job.remote_status == "remote"
    assert job.employment_type == "FULL_TIME" and job.published_at.year == 2026
    assert "private_config" not in job.model_dump_json() and "$23" not in job.model_dump_json()
    assert detect(ORIGIN + "/example") == ("kula", "example")


@pytest.mark.parametrize(
    "field,value",
    [
        ("listed", False),
        ("on_career_page", False),
        ("is_confidential", True),
        ("kind", "internal"),
        ("id", True),
        ("account_id", 0),
    ],
)
def test_hidden_internal_or_malformed_rows_abort(field, value):
    row = listing()
    row[field] = value
    with pytest.raises(ValueError):
        run(html=board([row]))


@pytest.mark.parametrize(
    "html",
    [
        board([]),
        board(links=""),
        board([listing(), listing()]),
        board().replace("</html>", ""),
        board().replace(PATH, "/example/13-engineer"),
    ],
)
def test_partial_duplicate_empty_truncated_or_unmatched_roster_aborts(html):
    with pytest.raises(ValueError):
        run(html=html)


@pytest.mark.parametrize(
    "field,value",
    [
        ("title", "Other"),
        ("identifier", {"value": "13"}),
        ("hiringOrganization", {"name": "Other"}),
        ("directApply", False),
    ],
)
def test_mismatched_details_abort(field, value):
    row = copy.deepcopy(schema())
    row[field] = value
    with pytest.raises(ValueError):
        run(job=row)


def test_changed_snapshot_aborts():
    row = listing()
    row["ats_job"]["workplace"] = "hybrid"
    with pytest.raises(ValueError):
        run(confirm=board([row]))


def test_failed_fetch_is_not_empty_success():
    with pytest.raises(httpx.HTTPStatusError):
        run(status=503)


def test_robots_denial_aborts():
    with pytest.raises(ValueError):
        run(robots="User-agent: *\nDisallow: /example")


def test_flight_text_records_use_utf8_byte_length_not_lines_or_json_substrings():
    from bs4 import BeautifulSoup
    from vindex.connectors.kula import public_jobs

    description = '\n1:{"jobs":[]}\nUnicode: Łódź '
    stream = "23:T" + format(len(description.encode()), "x") + "," + description
    stream += "2:" + json.dumps({"jobs": [listing()]}) + "\n"
    markup = "<script>self.__next_f.push(" + json.dumps([1, stream]) + ")</script>"
    assert public_jobs(BeautifulSoup(markup, "html.parser")) == [listing()]
    broken = "<script>self.__next_f.push(" + json.dumps([1, "23:Tffff,short"]) + ")</script>"
    with pytest.raises(ValueError):
        public_jobs(BeautifulSoup(broken, "html.parser"))

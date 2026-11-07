"""Zoho public constants, retained inactive listings and source completeness regressions."""

import asyncio
import html
import json

import httpx
import pytest
from vindex.connectors.registry import create_connector, detect
from vindex.connectors.zoho import loads, object_literal, string_literal

ORIGIN = "https://example.zohorecruit.eu"
ROOT = "/jobs/Careers"
PATH = ROOT + "/12"
URL = ORIGIN + PATH + "/Engineer?source=CareerSite"


def row():
    return {
        "id": "12",
        "Posting_Title": "Engineer",
        "Job_Opening_Name": "Engineer",
        "Remote_Job": True,
        "Publish": True,
        "Keep_on_Career_Site": False,
        "Is_Locked": False,
        "Job_Type": "Full time",
        "City": "London",
        "Country": "UK",
        "Currency": "GBP",
    }


def meta():
    return {
        "org_info": {"company_name": "Example", "id": "7", "hide_company_name": False},
        "employee_portal": False,
        "source": "CareerSite",
        "page_name": "Careers",
        "list_url": ORIGIN + ROOT,
        "detail_url": URL,
        "csrfToken": "DO_NOT_RETAIN",
    }


def board(rows=None, data=None):
    config = {
        "detail": {
            "section": {
                "data": [{"blocktype": "jobs", "isenabled": True, "applynow": "I'm interested"}]
            }
        }
    }
    values = {
        "jobs": rows if rows is not None else [row()],
        "meta": data or meta(),
        "pageJson": config,
    }
    return (
        "<html><title>Jobs at Example</title>"
        + "".join(
            '<input id="' + k + '" value="' + html.escape(json.dumps(v), quote=True) + '">'
            for k, v in values.items()
        )
        + "</html>"
    )


def detail(r=None, m=None):
    value = r or {
        **row(),
        "Job_Description": "<p>Build systems</p>",
        "Salary": "GBP 50,000",
        "Date_Opened": "2026-11-01",
    }
    # Data-only literals; the native template also uses ESAPI hex/punctuation escapes.
    source = (
        "var jobs = JSON.parse("
        + json.dumps(json.dumps([value]))
        + ");\nvar meta = "
        + json.dumps(m or meta())
        + ";"
    )
    return (
        '<html><meta property="og:url" content="'
        + html.escape(URL, quote=True)
        + '"><script>'
        + source
        + "</script></html>"
    )


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.zoho.asyncio.sleep", no_wait)


def run(body=None, job=None, confirm=None, status=200, robots="User-agent: *\nAllow: /"):
    calls = 0

    async def discover():
        def handle(request):
            nonlocal calls
            assert request.url.host == "example.zohorecruit.eu" and not request.url.query
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text=robots)
            if request.url.path == ROOT:
                calls += 1
                return httpx.Response(
                    200, text=confirm if calls > 1 and confirm is not None else body or board()
                )
            assert request.url.path == PATH
            return httpx.Response(status, text=job or detail())

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await create_connector("zoho-eu", "example", "Configured", client).discover()

    return asyncio.run(discover())


def test_full_public_record_and_source_date_salary_without_bootstrap_tokens():
    b = run()
    j = b.jobs[0]
    assert b.complete and j.company == "Example" and j.external_id == "12"
    assert j.description == "Build systems" and j.location == "London, UK"
    assert (
        j.salary == {"text": "GBP 50,000", "currency": "GBP"} and j.employment_type == "Full time"
    )
    assert j.published_at.isoformat() == "2026-11-01T00:00:00" and j.remote_status == "remote"
    assert j.application_url == URL and "DO_NOT_RETAIN" not in j.model_dump_json()
    assert detect(ORIGIN + ROOT) == ("zoho-eu", "example")


def test_retained_unpublished_jobs_are_not_promoted_to_active_records():
    inactive = {
        **row(),
        "id": "13",
        "Publish": False,
        "Keep_on_Career_Site": True,
        "Is_Locked": True,
    }
    b = run(body=board([row(), inactive]))
    assert len(b.jobs) == 1
    assert b.jobs[0].raw["board"]["retained_inactive_records"][0]["id"] == "13"


@pytest.mark.parametrize(
    "rows",
    [
        [],
        [row(), row()],
        [{**row(), "Publish": False, "Keep_on_Career_Site": False}],
        [{**row(), "Publish": False, "Keep_on_Career_Site": True}],
        [{**row(), "Publish": True, "Is_Locked": True}],
        [{**row(), "id": "https://evil.com"}],
    ],
)
def test_empty_duplicate_unpublished_or_ambiguous_rosters_abort(rows):
    with pytest.raises(ValueError):
        run(body=board(rows))


@pytest.mark.parametrize(
    "field,value", [("employee_portal", True), ("source", "EmployeePortal"), ("page_name", "Other")]
)
def test_private_or_alternate_portal_states_abort(field, value):
    m = meta()
    m[field] = value
    with pytest.raises(ValueError):
        run(body=board(data=m))


@pytest.mark.parametrize(
    "field,value",
    [("id", "13"), ("Posting_Title", "Other"), ("Publish", False), ("Is_Locked", True)],
)
def test_detail_identity_and_publication_must_match(field, value):
    r = {**row(), "Job_Description": "<p>Build systems</p>"}
    r[field] = value
    with pytest.raises(ValueError):
        run(job=detail(r))


def test_foreign_canonical_is_rejected():
    m = meta()
    m["detail_url"] = "https://evil.com/jobs/Careers/12/Engineer?source=CareerSite"
    with pytest.raises(ValueError):
        run(job=detail(m=m))


def test_inactive_metadata_changes_abort_snapshot_too():
    inactive = {**row(), "id": "13", "Publish": False, "Keep_on_Career_Site": True}
    initial = board([row(), inactive])
    changed = board([row(), {**inactive, "Posting_Title": "Changed"}])
    with pytest.raises(ValueError):
        run(body=initial, confirm=changed)


def test_source_failure_is_not_empty_success():
    with pytest.raises(httpx.HTTPStatusError):
        run(status=503)


def test_robots_denial_aborts():
    with pytest.raises(ValueError):
        run(robots="User-agent: *\nDisallow: /jobs/Careers/12")


def test_native_hex_identity_escapes_and_unicode_are_decoded_as_data():
    value, end = string_literal(r"""'[{\x22x\x22:\x22£30,000 \- £38,500\x22}]'""", 0)
    assert loads(value) == [{"x": "£30,000 - £38,500"}] and end > 0
    value, _ = string_literal(r"'\uD83D\uDE80'", 0)
    assert value == "🚀"
    assert object_literal(r'{"url":"https:\/\/example.com\/a\-b","nested":{"text":"{}"}}', 0) == {
        "url": "https://example.com/a-b",
        "nested": {"text": "{}"},
    }


@pytest.mark.parametrize(
    "value", ["'unterminated", r"'\xZZ'", r"'\u0XX0'", r"'\1'", r"'\q'", "'literal\nnewline'"]
)
def test_malformed_js_constants_abort_instead_of_being_executed_or_repaired(value):
    with pytest.raises(ValueError):
        string_literal(value, 0)


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_constants_that_javascript_json_parse_rejects_are_rejected(value):
    with pytest.raises(ValueError):
        loads(value)


def test_company_terminal_period_is_preserved_without_rejecting_source_seo_title():
    m = meta()
    m["org_info"]["company_name"] = "Example."
    b = run(body=board(data=m), job=detail(m=m))
    assert b.jobs[0].company == "Example."


def test_optional_remote_field_can_be_absent_without_inventing_onsite():
    listing = row()
    del listing["Remote_Job"]
    source = {**listing, "Job_Description": "<p>Build systems</p>"}
    j = run(body=board([listing]), job=detail(source)).jobs[0]
    assert j.remote_status is None and "Remote_Job" not in j.raw["job"]

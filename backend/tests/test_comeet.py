"""Comeet native public roster plus scoped documented public detail API regressions."""

import asyncio
import json

import httpx
import pytest
from vindex.connectors.registry import create_connector, detect

ORIGIN = "https://www.comeet.com"
ROOT = "/jobs/example/AA.001"
URL = ORIGIN + ROOT + "/engineer_role/BB.002"
TOKEN = "0123456789ABCDEF0123456789ABCDEF"


def row():
    return {
        "uid": "BB.002",
        "name": "Engineer",
        "is_internal": False,
        "company_name": "Example",
        "url_comeet_hosted_page": URL,
        "url_active_page": URL,
        "url_detected_page": None,
        "url_recruit_hosted_page": "https://jobs.sparkhire.com/example/engineer",
        "workplace_type": "Hybrid",
        "employment_type": "Full time",
        "time_updated": "2026-11-01T10:00:00Z",
        "location": {"name": "London", "city": "London", "country": "UK", "is_remote": True},
        "department": "Engineering",
        "email": "excluded@example.com",
    }


def board(rows=None):
    company = {
        "name": "Example",
        "company_uid": "AA.001",
        "slug": "example",
        "url_comeet_hosted_page": ORIGIN + ROOT,
        "token": TOKEN,
        "application_form_settings": {"must_not_retain": True},
    }
    return (
        "<html><script>\nCOMPANY_DATA = "
        + json.dumps(company)
        + ";\nCOMPANY_POSITIONS_DATA = "
        + json.dumps(rows if rows is not None else [row()])
        + ";</script></html>"
    )


def detail():
    return {
        **row(),
        "details": [
            {"name": "Description", "order": 1, "value": "<p>Build systems</p>"},
            {"name": "Requirements", "order": 2, "value": "<p>Know Python</p>"},
        ],
        "questionnaires": [{"must_not_retain": True}],
    }


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.comeet.asyncio.sleep", no_wait)


def run(
    html=None,
    data=None,
    confirm=None,
    status=200,
    robots="User-agent: *\nAllow: /",
    position_uid="BB.002",
):
    calls = 0

    async def discover():
        def handle(request):
            nonlocal calls
            assert request.url.host == "www.comeet.com" and "authorization" not in request.headers
            assert "/employee" not in request.url.path
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text=robots)
            if request.url.path == ROOT:
                calls += 1
                assert not request.url.query
                return httpx.Response(
                    200, text=confirm if calls > 1 and confirm is not None else html or board()
                )
            assert request.url.path == "/careers-api/2.0/company/AA.001/positions/" + position_uid
            assert dict(request.url.params) == {"token": TOKEN, "details": "true"}
            return httpx.Response(status, json=data or detail())

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await create_connector(
                "comeet", "example~AA.001", "Configured", client
            ).discover()

    return asyncio.run(discover())


def test_complete_public_roster_details_and_requirements_without_forms_or_read_token():
    b = run()
    j = b.jobs[0]
    assert b.complete and j.external_id == "BB.002" and j.company == "Example"
    assert j.description == "Build systems\n\nKnow Python" and j.remote_status == "Hybrid"
    assert j.published_at is None and j.raw["job"]["time_updated"] == "2026-11-01T10:00:00Z"
    assert j.application_url == URL and j.employment_type == "Full time"
    assert TOKEN not in j.model_dump_json() and "must_not_retain" not in j.model_dump_json()
    assert "excluded@example.com" not in j.model_dump_json()
    assert detect(ORIGIN + ROOT) == ("comeet", "example~AA.001")


@pytest.mark.parametrize(
    "rows",
    [
        [],
        [row(), row()],
        [{**row(), "is_internal": True}],
        [{**row(), "company_name": "Other"}],
        [{**row(), "uid": "https://evil.com"}],
        [{**row(), "url_comeet_hosted_page": "https://evil.com/job"}],
    ],
)
def test_incomplete_private_or_mismatched_roster_aborts(rows):
    with pytest.raises(ValueError):
        run(html=board(rows))


@pytest.mark.parametrize(
    "key,value",
    [
        ("uid", "CC.003"),
        ("name", "Other"),
        ("is_internal", True),
        ("company_name", "Other"),
        ("workplace_type", "Remote"),
        ("url_active_page", "https://evil.com/job"),
    ],
)
def test_listed_and_mandatory_detail_metadata_must_match(key, value):
    d = detail()
    d[key] = value
    with pytest.raises(ValueError):
        run(data=d)


@pytest.mark.parametrize(
    "sections",
    [
        [],
        [{"name": "Description", "order": 1, "value": 7}],
        [
            {"name": "Description", "order": 1, "value": "A"},
            {"name": "Requirements", "order": 1, "value": "B"},
        ],
    ],
)
def test_missing_malformed_or_duplicate_full_sections_abort(sections):
    d = detail()
    d["details"] = sections
    with pytest.raises(ValueError):
        run(data=d)


def test_changed_full_roster_aborts():
    with pytest.raises(ValueError):
        run(confirm=board().replace("Engineering", "Other"))


def test_request_failure_is_recorded_without_query_read_token():
    with pytest.raises(ValueError) as error:
        run(status=503)
    assert TOKEN not in str(error.value) and "HTTP 503" in str(error.value)


def test_robots_denial_does_not_expose_read_token():
    with pytest.raises(ValueError) as error:
        run(robots="User-agent: *\nDisallow: /careers-api/")
    assert TOKEN not in str(error.value)


def test_known_documented_sandbox_is_not_counted_as_production_source():
    with pytest.raises(ValueError):
        create_connector("comeet", "example~E5.007", "Configured", httpx.AsyncClient())


def test_optional_requisition_id_enrichment_preserves_both_observations():
    d = detail()
    d["internal_use_custom_id"] = "REQ42"
    j = run(data=d).jobs[0]
    assert j.raw["job"]["internal_use_custom_id"] == "REQ42"
    assert j.raw["listing"]["internal_use_custom_id"] is None


def test_location_specific_postings_keep_their_own_uid_and_original_link():
    value = row()
    value["uid"] = "BB.002-CC.003"
    for key in ("url_comeet_hosted_page", "url_active_page"):
        value[key] = value[key].replace("/BB.002", "/BB.002-CC.003")
    value["location"]["location_uid"] = "CC.003"
    data = {**detail(), **value}
    j = run(html=board([value]), data=data, position_uid=value["uid"]).jobs[0]
    assert j.external_id == "BB.002-CC.003" and j.source_url.endswith("/BB.002-CC.003")
    value["location"]["location_uid"] = "DD.004"
    with pytest.raises(ValueError):
        run(html=board([value]), data=data, position_uid=value["uid"])


def test_explicit_null_optional_section_is_preserved_without_inventing_text():
    d = detail()
    d["details"].append({"name": "What we offer", "order": 3, "value": None})
    j = run(data=d).jobs[0]
    assert j.description == "Build systems\n\nKnow Python"
    assert j.quality_flags == ["description_section_missing"]
    assert j.raw["detail_sections"][2]["value"] is None

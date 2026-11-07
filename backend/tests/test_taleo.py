"""Taleo TBE native scope, full pagination, public fallback and original date formats."""

import asyncio
import json

import httpx
import pytest
from vindex.connectors.registry import create_connector, detect

HOST = "phf.tbe.taleo.net"
ORIGIN = "https://" + HOST
BASE = ORIGIN + "/phf03/ats/careers/v2/"


def url(route="viewRequisition", identifier=1):
    return BASE + route + f"?org=EXAMPLE&cws=42&rid={identifier}"


def card(identifier=1):
    return (
        '<h4 class="oracletaleocwsv2-head-title"><a class="viewJobLink" href="'
        + url(identifier=identifier)
        + '">Engineer</a></h4>'
    )


def board(total=1, offset=0, show_total=True):
    cards = "".join(
        "<div><div>" + card(i + 1) + '<div tabindex="0">London</div></div></div>'
        for i in range(offset, min(offset + 10, total))
    )
    count = (
        f'<div><h3 aria-label="Positions Matched">Positions Matched</h3><span class="oracletaleocwsv2-panel-number">{total}</span></div>'
        if show_total
        else ""
    )
    more = (
        f'<a class="jscroll-next" href="/phf03/ats/careers/v2/searchResults?next&amp;rowFrom={offset + 10}&amp;act=null&amp;sortColumn=null&amp;sortOrder=null&amp;currentTime=1234">next</a>'
        if offset + 10 < total
        else ""
    )
    return "<html><title>Career Center</title>" + count + cards + more + "</html>"


def posting(identifier=1):
    return {
        "@type": "JobPosting",
        "identifier": {"value": str(identifier)},
        "title": "Engineer",
        "url": url(identifier=identifier),
        "description": "<p>Build systems and know Python</p>",
        "hiringOrganization": {"name": "Native Example"},
        "employmentType": "Full time",
        "datePosted": "2026-11-01 00:00:00.0",
    }


def detail(identifier=1, structured=True, row=None):
    ld = (
        '<script type="application/ld+json">' + json.dumps(row or posting(identifier)) + "</script>"
        if structured
        else ""
    )
    return (
        "<html><title>Career Center</title>"
        + ld
        + '<div class="well oracletaleocwsv2-job-description"><strong>Engineer</strong><div class="row"><div><span class="small">Location</span><strong>London</strong></div><div><span class="small">Job Code</span><strong>H123</strong></div></div></div><div class="alert alert-info"><h2>Job Brief</h2>Brief source summary</div><div class="col-md-12 row"><p>Build systems and know Python</p></div><a href="'
        + url("applyRequisition", identifier)
        + '">Apply Now</a></html>'
    )


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.taleo.asyncio.sleep", no_wait)


def run(
    total=1, show_total=True, structured=True, listing=None, content=None, changed=False, status=200
):
    calls = 0

    async def discover():
        def handle(request):
            nonlocal calls
            assert (
                request.url.host == HOST
                and request.method == "GET"
                and "authorization" not in request.headers
            )
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text="User-agent: *\nAllow: /")
            params = dict(request.url.params)
            assert params["org"] == "EXAMPLE" and params["cws"] == "42"
            if request.url.path.endswith("/searchResults"):
                calls += 1
                offset = int(params.get("rowFrom", "0"))
                data = listing or board(total, offset, show_total)
                if changed and calls > 1:
                    data = data.replace(">Engineer<", ">Changed<")
                return httpx.Response(200, text=data)
            assert request.url.path.endswith("/viewRequisition")
            identifier = int(params["rid"])
            assert 1 <= identifier <= total
            return httpx.Response(status, text=content or detail(identifier, structured))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await create_connector(
                "taleo-tbe", HOST + "~phf03~EXAMPLE~42", "Configured Example", client
            ).discover()

    return asyncio.run(discover())


def test_complete_native_description_brief_application_scope_and_original_naive_publication():
    result = run()
    job = result.jobs[0]
    assert result.complete and job.company == "Native Example" and job.external_id == "1"
    assert job.description == "Job Brief Brief source summary Build systems and know Python"
    assert job.application_url == url("applyRequisition") and job.source_url == url()
    assert job.location == "London" and job.employment_type == "Full time"
    assert job.published_at.year == 2026 and job.published_at.tzinfo is None
    assert job.quality_flags == ["publication_timezone_unspecified"]
    assert job.raw["native_metadata"]["Job Code"] == "H123"
    assert detect(BASE + "jobSearch?org=EXAMPLE&cws=42") == (
        "taleo-tbe",
        HOST + "~phf03~EXAMPLE~42",
    )


def test_public_html_only_template_preserves_unknown_optional_metadata_without_fabrication():
    job = run(structured=False).jobs[0]
    assert (
        job.company == "Configured Example"
        and job.published_at is None
        and job.employment_type is None
    )
    assert (
        "structured_job_metadata_missing" in job.quality_flags
        and "company_from_source_configuration" in job.quality_flags
    )
    assert "know Python" in job.description


@pytest.mark.parametrize("show_total", [True, False])
def test_all_native_ten_job_pages_are_mandatory_with_or_without_optional_source_total(show_total):
    result = run(total=11, show_total=show_total)
    assert result.complete and len(result.jobs) == 11 and result.jobs[-1].external_id == "11"


def test_explicit_gmt_java_date_is_parsed_with_supplied_timezone_only():
    row = posting()
    row["datePosted"] = "Wed Oct 28 00:00:00 GMT 2026"
    job = run(content=detail(row=row)).jobs[0]
    assert job.published_at.month == 10 and job.published_at.utcoffset().total_seconds() == 0
    assert job.quality_flags == []


@pytest.mark.parametrize(
    "old,new",
    [
        ("</html>", ""),
        ("Career Center", "Other"),
        ("org=EXAMPLE", "org=OTHER"),
        ("cws=42", "cws=99"),
        (HOST, "evil.test"),
    ],
)
def test_truncated_foreign_or_unbound_native_roster_fails(old, new):
    with pytest.raises(ValueError):
        run(listing=board().replace(old, new))


def test_partial_duplicate_or_unbounded_pagination_aborts():
    with pytest.raises(ValueError):
        run(listing=board(total=2).replace(card(2), ""))
    with pytest.raises(ValueError):
        run(listing=board(total=2).replace(card(2), card(1)))
    with pytest.raises(ValueError):
        run(total=11, listing=board(total=11).replace("rowFrom=10", "rowFrom=20"))
    with pytest.raises(ValueError):
        run(listing=board(total=201))


@pytest.mark.parametrize(
    "key,value",
    [
        ("title", "Other"),
        ("identifier", {"value": "2"}),
        ("url", url(identifier=2)),
        ("description", "Partial"),
        ("hiringOrganization", {"name": ""}),
    ],
)
def test_full_structured_identity_and_native_text_must_agree(key, value):
    # Empty native SEO employer falls back to explicit configured company.
    if key == "hiringOrganization":
        assert (
            run(content=detail(row={**posting(), key: value})).jobs[0].company
            == "Configured Example"
        )
    else:
        with pytest.raises(ValueError):
            run(content=detail(row={**posting(), key: value}))


@pytest.mark.parametrize(
    "old,new",
    [
        (">Engineer</strong>", ">Other</strong>"),
        ('class="well oracletaleocwsv2-job-description"', 'class="other"'),
        ('class="col-md-12 row"', 'class="other"'),
        ("/applyRequisition?", "/other?"),
        ("applyRequisition?org=EXAMPLE&cws=42&rid=1", "applyRequisition?org=EXAMPLE&cws=42&rid=2"),
    ],
)
def test_mandatory_full_native_identity_application_and_body_required(old, new):
    with pytest.raises(ValueError):
        run(content=detail().replace(old, new))


def test_failed_required_detail_and_changed_board_never_become_empty_success():
    with pytest.raises(ValueError):
        run(status=404)
    with pytest.raises(ValueError):
        run(changed=True)


@pytest.mark.parametrize(
    "url",
    [
        BASE + "searchResults?org=EXAMPLE&cws=42&rowFrom=10",
        BASE + "viewRequisition?org=EXAMPLE&cws=42&rid=1",
        BASE + "searchResults?org=EXAMPLE&cws=42&keyword=x",
        BASE.replace("phf03", "phg01") + "jobSearch?org=EXAMPLE&cws=42",
        BASE + "jobSearch?org=TIMESTAMP_DEMO2&cws=42",
    ],
)
def test_registration_or_factory_rejects_filters_private_scope_and_known_demo(url):
    with pytest.raises(ValueError):
        provider, slug = detect(url)
        create_connector(provider, slug, "Example", httpx.AsyncClient())

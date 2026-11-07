"""Native Avature modern/classic six-job portals and complete descriptions."""

import asyncio
import json

import httpx
import pytest
from vindex.connectors.registry import create_connector, detect

ORIGIN = "https://example.avature.net"
BASE = ORIGIN + "/careers"


def url(identifier=1):
    return BASE + f"/JobDetail/Engineer/{identifier}"


def card(identifier=1, modern=True):
    title = "Engineer" if modern else "(ENG) Engineer"
    if modern:
        return (
            '<article class="article--jobs"><h3><a href="'
            + url(identifier)
            + '">'
            + title
            + '</a></h3><p><span class="icon-address"></span>London</p><p><span class="icon-tag"></span>Engineering</p></article>'
        )
    return (
        '<li class="group"><h3><a href="'
        + url(identifier)
        + '">'
        + title
        + '</a></h3><p class="job-context"><span><strong>Team: </strong>Engineering</span><span><strong>Location: </strong>London</span><span><strong>Ref: </strong>REQ'
        + str(identifier)
        + "</span><span><strong>Closing Date: </strong>07-Nov-2026</span></p></li>"
    )


def board(total=1, offset=0, modern=True):
    title = "<h1>Example</h1>" if modern else '<h2 class="pageTitle">Example Careers</h2>'
    legend = (
        f"{offset + 1}-{min(offset + 6, total)} of {total} results"
        if modern
        else f"Displaying {offset + 1}-{min(offset + 6, total)} of {total}"
    )
    klass = "list-controls__text__legend" if modern else "jobPaginationLegend"
    cards = "".join(card(i + 1, modern) for i in range(offset, min(offset + 6, total)))
    if not modern:
        cards = '<ul class="results">' + cards + "</ul>"
    return (
        "<html><title>Example Careers</title>"
        + title
        + f'<div class="{klass}">{legend}</div>'
        + cards
        + "</html>"
    )


def detail(identifier=1, modern=True):
    if modern:
        return (
            '<html><h1>Example</h1><link rel="canonical" href="'
            + url(identifier)
            + '"><div class="banner__text"><h2>Engineer</h2><p><span class="icon-address-white"></span>London</p><p><span class="icon-tag-white"></span>Engineering</p></div><main><article class="article--details"><h3>Requirements</h3><div class="article__content__view__field">Build systems and know Python</div></article><article class="article--details"><h3>Benefits</h3><div class="article__content__view__field">Health insurance</div></article></main><a href="'
            + BASE
            + "/ApplicationMethods?jobId="
            + str(identifier)
            + '">Apply</a></html>'
        )
    fields = [
        ("", "(ENG) Engineer"),
        ("Team", "Engineering"),
        ("Location", "London"),
        ("County", "Greater London"),
        ("Ref #", "REQ" + str(identifier)),
        ("Closing Date", "07-Nov-2026"),
        ("", "Build systems and know Python"),
        ("Important Footnote", "Health insurance"),
    ]
    paragraphs = "".join(
        '<p class="paragraph"><span class="field--name">'
        + k
        + '</span><span class="field--value">'
        + v
        + "</span></p>"
        for k, v in fields
    )
    schema = {
        "@type": "JobPosting",
        "title": "Engineer",
        "description": "Build systems and know Python Health insurance",
        "hiringOrganization": {"name": "Example Ltd"},
        "datePosted": "2026-11-01",
        "employmentType": "FULL_TIME",
        "baseSalary": {"currency": "GBP", "value": 40000},
    }
    return (
        '<html><script type="application/ld+json">'
        + json.dumps(schema)
        + '</script><div id="main-col"><article class="article--details">'
        + paragraphs
        + '</article></div><a href="'
        + BASE
        + "/RegisterMethod?jobId="
        + str(identifier)
        + '">Start here</a></html>'
    )


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.avature.asyncio.sleep", no_wait)


def run(total=1, modern=True, listing=None, content=None, changed=False, status=200):
    calls = 0

    async def discover():
        def handle(request):
            nonlocal calls
            assert request.url.host == "example.avature.net" and request.method == "GET"
            assert "authorization" not in request.headers
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text="User-agent: *\nAllow: /")
            if request.url.path in ["/careers/SearchJobs", "/careers/SearchJobs/"]:
                calls += 1
                offset = int(request.url.params.get("jobOffset", "0"))
                text = listing or board(total, offset, modern)
                if changed and calls > 1:
                    text = text.replace("Engineer", "Changed")
                return httpx.Response(200, text=text)
            identifier = int(request.url.path.split("/")[-1])
            assert 1 <= identifier <= total and not request.url.query
            return httpx.Response(status, text=content or detail(identifier, modern))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await create_connector(
                "avature", "example~careers", "Configured", client
            ).discover()

    return asyncio.run(discover())


def test_modern_full_description_includes_every_section_and_native_employer_location():
    result = run()
    job = result.jobs[0]
    assert result.complete and job.company == "Example" and job.location == "London"
    assert job.description == "Requirements Build systems and know Python Benefits Health insurance"
    assert job.application_url == BASE + "/ApplicationMethods?jobId=1"
    assert job.salary is None and job.published_at is None and job.remote_status is None
    assert detect(BASE + "/SearchJobs") == ("avature", "example~careers")


def test_classic_native_display_prefix_original_reference_and_all_full_text_preserved():
    result = run(modern=False)
    job = result.jobs[0]
    assert result.complete and job.title == "(ENG) Engineer" and job.company == "Example Ltd"
    assert (
        "Build systems and know Python" in job.description and "Health insurance" in job.description
    )
    assert job.raw["detail_fields"]["Ref #"] == "REQ1" and job.employment_type == "FULL_TIME"
    assert job.salary["currency"] == "GBP" and job.published_at.year == 2026
    assert job.application_url == BASE + "/RegisterMethod?jobId=1"


@pytest.mark.parametrize("modern", [True, False])
def test_every_six_item_page_required(modern):
    result = run(total=7, modern=modern)
    assert result.complete and len(result.jobs) == 7 and result.jobs[-1].external_id == "7"


@pytest.mark.parametrize(
    "old,new",
    [
        ("1-1 of 1 results", "1-1 of 2 results"),
        ("1-1 of 1 results", "2-2 of 2 results"),
        ("</html>", ""),
        ("1-1 of 1 results", "1-1 of 201 results"),
        (url(), "https://evil.test/JobDetail/Engineer/1"),
        ("/Engineer/1", "/%2fprivate/1"),
        ("icon-address", "other"),
    ],
)
def test_partial_unsafe_or_unsupported_modern_board_fails(old, new):
    with pytest.raises(ValueError):
        run(listing=board().replace(old, new))


@pytest.mark.parametrize(
    "old,new",
    [
        ('rel="canonical"', 'rel="other"'),
        ("<h2>Engineer</h2>", "<h2>Other</h2>"),
        ("jobId=1", "jobId=2"),
        ("icon-address-white", "other"),
        ("article__content__view__field", "other"),
    ],
)
def test_modern_mandatory_identity_full_fields_and_apply_control(old, new):
    with pytest.raises(ValueError):
        run(content=detail().replace(old, new))


@pytest.mark.parametrize(
    "old,new",
    [
        ("REQ1", "OTHER"),
        (">London<", ">Paris<"),
        (">07-Nov-2026<", ">08-Nov-2026<"),
        (
            '"description": "Build systems and know Python Health insurance"',
            '"description": "Other role"',
        ),
        ("jobId=1", "jobId=2"),
    ],
)
def test_classic_native_metadata_schema_and_application_must_agree(old, new):
    with pytest.raises(ValueError):
        run(modern=False, content=detail(modern=False).replace(old, new))


def test_changed_full_public_roster_and_failed_required_detail_abort():
    with pytest.raises(ValueError):
        run(changed=True)
    with pytest.raises(ValueError):
        run(status=404)


@pytest.mark.parametrize(
    "url",
    [
        BASE + "/SearchJobs?jobOffset=6",
        BASE + "/Login",
        BASE + "/JobDetail/Engineer/1",
        BASE.replace("example.avature.net", "example.avature.net.evil.test") + "/SearchJobs",
        ORIGIN + "/internal/SearchJobs",
    ],
)
def test_registration_rejects_filters_accounts_details_and_nonpublic_scope(url):
    with pytest.raises(ValueError):
        provider, slug = detect(url)
        create_connector(provider, slug, "", httpx.AsyncClient())


def test_classic_alternate_internal_seo_title_is_retained_without_replacing_visible_title():
    page = detail(modern=False).replace(
        '"title": "Engineer"', '"title": "Different internal title"'
    )
    job = run(modern=False, content=page).jobs[0]
    assert (
        job.title == "(ENG) Engineer"
        and job.raw["detail_fields"]["jobposting"]["title"] == "Different internal title"
    )
    assert "structured_title_differs" in job.quality_flags
    with pytest.raises(ValueError):
        run(modern=False, content=page.replace(">(ENG) Engineer<", ">Unrelated visible role<"))


def test_classic_omitted_list_location_can_use_only_real_full_structured_location():
    listing = board(modern=False).replace("<span><strong>Location: </strong>London</span>", "")
    page = detail(modern=False).replace(">London<", "><")
    # No schema address was provided either; keep unknown, do not infer London from prose.
    job = run(modern=False, listing=listing, content=page).jobs[0]
    assert job.location == "" and "location_missing" in job.quality_flags


def test_classic_salary_present_only_in_list_is_preserved_without_guessing_units():
    listing = board(modern=False).replace(
        "</p></li>", "<span><strong>Starting Salary From: </strong>£26,230</span></p></li>"
    )
    page = detail(modern=False).replace(', "baseSalary": {"currency": "GBP", "value": 40000}', "")
    assert run(modern=False, listing=listing, content=page).jobs[0].salary == {"text": "£26,230"}


def test_optional_native_team_omission_matches_explicit_empty_detail_field():
    listing = board(modern=False).replace("<span><strong>Team: </strong>Engineering</span>", "")
    page = detail(modern=False).replace(">Engineering<", "><")
    assert run(modern=False, listing=listing, content=page).complete

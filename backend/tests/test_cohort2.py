import asyncio
import json
from pathlib import Path
from xml.etree.ElementTree import ParseError

import httpx
import pytest
from defusedxml.common import DefusedXmlException
from vindex.connectors.http import PublicHTTP
from vindex.connectors.personio import PersonioConnector
from vindex.connectors.registry import create_connector, detect
from vindex.connectors.smartrecruiters import SmartRecruitersConnector

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.http.asyncio.sleep", no_wait)


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://matrix42.jobs.personio.de", ("personio-de", "matrix42")),
        ("https://planqc-gmbh.jobs.personio.com/job/123", ("personio-com", "planqc-gmbh")),
        ("https://careers.smartrecruiters.com/Colliers", ("smartrecruiters", "Colliers")),
        (
            "https://jobs.smartrecruiters.com/SmartRecruiters/123-role",
            ("smartrecruiters", "SmartRecruiters"),
        ),
    ],
)
def test_new_provider_detection(url, expected):
    assert detect(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://matrix42.jobs.personio.de.evil.com",
        "https://a.b.jobs.personio.de",
        "https://-tenant.jobs.personio.de",
        "https://tenant-.jobs.personio.com",
        "https://jobs.smartrecruiters.com/",
        "https://jobs.smartrecruiters.com/%2e%2e",
        "http://matrix42.jobs.personio.de",
        "https://user@matrix42.jobs.personio.de",
        "https://matrix42.jobs.personio.de:8080",
        "https://127.0.0.1/xml",
    ],
)
def test_reject_unsafe_new_provider_urls(url):
    with pytest.raises(ValueError):
        detect(url)


def test_personio_live_xml_samples_preserve_raw_and_locations():
    for slug in ["matrix42", "planqc-gmbh"]:
        connector = PersonioConnector("personio-de", slug, "Example", None)
        jobs = connector.parse((ROOT / f"evidence/personio-{slug}-sample.xml").read_bytes())
        assert len(jobs) == 1
        assert jobs[0].title
        assert jobs[0].description == ""  # Actual default-language samples omit translations.
        assert jobs[0].application_url.endswith("#apply")
        assert jobs[0].raw["createdAt"]  # Creation must not be relabelled publication.
        assert jobs[0].published_at is None
        assert "<position>" in jobs[0].raw["xml"]
    assert "Ulm" in jobs[0].location


@pytest.mark.parametrize(
    "xml",
    [
        b"<html/>",
        b"<workzag-jobs><error/></workzag-jobs>",
        b"<workzag-jobs><position><id>../../</id></position></workzag-jobs>",
        b"<workzag-jobs>",
    ],
)
def test_bad_xml_rejected(xml):
    with pytest.raises((ValueError, ParseError)):
        PersonioConnector("personio-de", "example", "Example", None).parse(xml)


def test_xml_dtd_and_entity_expansion_rejected():
    xml = b'<!DOCTYPE workzag-jobs [<!ENTITY secret SYSTEM "file:///etc/passwd">]><workzag-jobs>&secret;</workzag-jobs>'
    with pytest.raises(DefusedXmlException):
        PersonioConnector("personio-de", "example", "Example", None).parse(xml)


def discover(provider, handler):
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await create_connector(provider, "example", "Example", client).discover()

    return asyncio.run(run())


def test_personio_duplicate_positions_rejected():
    position = "<position><id>1</id><name>Engineer</name></position>"
    with pytest.raises(ValueError, match="Repeated"):
        discover(
            "personio-de",
            lambda r: httpx.Response(
                200, content=f"<workzag-jobs>{position}{position}</workzag-jobs>"
            ),
        )


def test_smartrecruiters_real_detail_sample():
    payload = json.loads(
        (ROOT / "evidence/smartrecruiters-SmartRecruiters-detail.json").read_text()
    )
    jobs = SmartRecruitersConnector("smartrecruiters", "SmartRecruiters", "Example", None).parse(
        payload
    )
    assert jobs[0].title == payload["name"]
    assert jobs[0].remote_status == "Remote"
    assert jobs[0].description and "<p>" not in jobs[0].description
    assert jobs[0].application_url == payload["applyUrl"]
    assert jobs[0].published_at is not None


def detail(i):
    return {
        "id": str(i),
        "name": "Engineer",
        "jobAd": {"sections": {"jobDescription": {"text": "<p>Build</p>"}}},
        "postingUrl": f"https://jobs.smartrecruiters.com/example/{i}",
        "applyUrl": f"https://jobs.smartrecruiters.com/example/{i}?oga=true",
    }


def test_smartrecruiters_pagination_and_detail_completion():
    calls = []

    def handler(r):
        calls.append(str(r.url))
        if "offset" in r.url.params:
            offset = int(r.url.params["offset"])
            return httpx.Response(
                200,
                json={
                    "offset": offset,
                    "totalFound": 2,
                    "content": [{"id": str(offset + 1), "visibility": "PUBLIC"}],
                },
            )
        return httpx.Response(200, json=detail(r.url.path.split("/")[-1]))

    batch = discover("smartrecruiters", handler)
    assert batch.complete and len(batch.jobs) == 2
    assert len(calls) == 4


@pytest.mark.parametrize(
    "failure",
    [
        "detail404",
        "mismatch",
        "nonpublic",
        "totaldrift",
        "offset",
        "earlyempty",
        "duplicate",
        "nodescription",
    ],
)
def test_smartrecruiters_partial_results_never_complete(failure):
    def handler(r):
        if "offset" in r.url.params:
            offset = int(r.url.params["offset"])
            page = {
                "offset": offset,
                "totalFound": 2,
                "content": [
                    {
                        "id": "1" if offset == 0 or failure == "duplicate" else "2",
                        "visibility": "PUBLIC",
                    }
                ],
            }
            if failure == "nonpublic":
                page["content"][0]["visibility"] = "INTERNAL"
            if failure == "offset":
                page["offset"] = 99
            if offset and failure == "totaldrift":
                page["totalFound"] = 3
            if offset and failure == "earlyempty":
                page["content"] = []
            return httpx.Response(200, json=page)
        if failure == "detail404":
            return httpx.Response(404)
        payload = detail(r.url.path.split("/")[-1])
        if failure == "mismatch":
            payload["id"] = "wrong"
        if failure == "nodescription":
            payload["jobAd"]["sections"] = {}
        return httpx.Response(200, json=payload)

    with pytest.raises(ValueError):
        discover("smartrecruiters", handler)


def test_http_bounds_redirects_and_host_validation(monkeypatch):
    monkeypatch.setattr("vindex.connectors.http.MAX_RESPONSE_BYTES", 16)

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda r: httpx.Response(200, content=b"x" * 17))
        ) as c:
            h = PublicHTTP(c, {"api.example.com"})
            with pytest.raises(ValueError, match="limit"):
                await h.read("https://api.example.com/jobs")
            with pytest.raises(ValueError, match="rejected"):
                await h.read("https://127.0.0.1/jobs")
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda r: httpx.Response(302, headers={"Location": "https://api.example.com/next"})
            )
        ) as c:
            with pytest.raises(ValueError, match="302"):
                await PublicHTTP(c, {"api.example.com"}).read("https://api.example.com/jobs")

    asyncio.run(run())


def test_long_retry_after_is_failure_not_premature_retry():
    calls = []

    async def run():
        def handler(r):
            calls.append(r)
            return httpx.Response(429, headers={"Retry-After": "120"})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            with pytest.raises(ValueError, match="Retry-After"):
                await PublicHTTP(c, {"api.example.com"}).read("https://api.example.com/jobs")

    asyncio.run(run())
    assert len(calls) == 1


def test_personio_real_empty_default_enriches_from_english():
    default = (ROOT / "evidence/personio-matrix42-sample.xml").read_bytes()
    english = (ROOT / "evidence/personio-matrix42-english.xml").read_bytes()
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(
            200, content=english if request.url.params.get("language") == "en" else default
        )

    batch = discover("personio-de", handler)
    assert batch.complete and batch.jobs[0].description
    assert batch.jobs[0].raw["description_translation"]["language"] == "en"
    assert len(calls) == 2


def test_personio_missing_description_is_incomplete():
    xml = b"<workzag-jobs><position><id>1</id><name>Engineer</name></position></workzag-jobs>"
    with pytest.raises(ValueError, match="Description unavailable"):
        discover("personio-de", lambda r: httpx.Response(200, content=xml))


def test_personio_language_feed_cannot_expand_snapshot():
    default = b"<workzag-jobs><position><id>1</id><name>Engineer</name></position></workzag-jobs>"
    translated = default.replace(b"<id>1</id>", b"<id>2</id>")
    with pytest.raises(ValueError, match="identifiers changed"):
        discover(
            "personio-de",
            lambda r: httpx.Response(200, content=translated if r.url.query else default),
        )


def test_smartrecruiters_live_optional_title_only_section():
    payload = json.loads(
        (ROOT / "evidence/smartrecruiters-Colliers-optional-section.json").read_text()
    )
    assert any("text" not in section for section in payload["jobAd"]["sections"].values())
    job = SmartRecruitersConnector("smartrecruiters", "Colliers", "Colliers", None).parse(payload)[
        0
    ]
    assert job.description and job.title == payload["name"]


def test_smartrecruiters_company_blurb_cannot_replace_missing_job_description():
    payload = detail("1")
    payload["jobAd"]["sections"] = {"companyDescription": {"text": "About our company"}}
    with pytest.raises(ValueError, match="no job description"):
        SmartRecruitersConnector("smartrecruiters", "example", "Example", None).parse(payload)

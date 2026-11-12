import json

import httpx
import pytest
from vindex.connectors.jobiqo import JobiqoConnector


def test_united_way_matches_numeric_card_id_and_allows_blank_badge():
    connector = JobiqoConnector("careers.unitedway.org", httpx.AsyncClient())
    body = b"""
    <html><h1>1 Job</h1><div data-test-id="job-teaser-123 ">
    <a href="/job/engineer-123">Engineer</a></div></html>
    """
    assert connector.page(body) == (1, {"123": "https://careers.unitedway.org/job/engineer-123"})
    with pytest.raises(ValueError, match="card and posting IDs differ"):
        connector.page(body.replace(b"engineer-123", b"engineer-456"))


def test_agrajo_markdown_apply_link_takes_precedence_over_contact_email():
    connector = JobiqoConnector("www.agrajo.com", httpx.AsyncClient())
    url = "https://www.agrajo.com/job/engineer"
    posting = {
        "@type": "JobPosting",
        "title": "Engineer",
        "hiringOrganization": {"name": "Employer"},
        "description": (
            "Fragen: recruiting@example.test. Keine Bewerbungen per E-Mail. "
            '[Jetzt bewerben](https://example.test/apply "Jetzt bewerben")'
        ),
    }
    body = f"""
    <html><head><link rel="canonical" href="{url}">
    <script type="application/ld+json">{json.dumps(posting)}</script></head>
    <body><main><h1>Engineer</h1></main></body></html>
    """.encode()
    job = connector.detail(body, "123", url)
    assert job.application_url == "https://example.test/apply"
    assert "application_by_email" not in job.quality_flags


def test_registry_accepts_only_unfiltered_jobiqo_board():
    from vindex.connectors.registry import detect

    assert detect("https://careers.unitedway.org/jobs") == ("jobiqo", "careers.unitedway.org")
    with pytest.raises(ValueError, match="unfiltered"):
        detect("https://careers.unitedway.org/jobs?page=2")

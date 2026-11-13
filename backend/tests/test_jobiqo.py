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


def test_kampajobs_uses_zero_based_page_parameter():
    import asyncio

    requests = []

    async def handler(request):
        requests.append(request.url)
        return httpx.Response(200, content=b"<html></html>")

    async def fetch_pages():
        from urllib.robotparser import RobotFileParser

        from vindex.connectors.robots import RobotsPolicy

        parser = RobotFileParser()
        parser.parse([])
        policy = RobotsPolicy(parser)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            connector = JobiqoConnector("www.kampajobs.ch", client)
            await connector.fetch(0, policy)
            await connector.fetch(1, policy)

    asyncio.run(fetch_pages())
    assert [str(url) for url in requests] == [
        "https://www.kampajobs.ch/jobs",
        "https://www.kampajobs.ch/jobs?page=1",
    ]


def test_kampajobs_linked_job_requires_matching_publisher_identity():
    import asyncio

    url = "https://www.kampajobs.ch/job/engineer"
    frame = "https://www.publicjobs.ch/jobs/~job123/~channel0123456789abcdef0123456789abcdef?ext"
    posting = {"@type": "JobPosting", "hiringOrganization": {"name": "Employer"}}
    body = f"""
    <html><body class="page-node-42 node-type-job-per-link">
    <div class="pane-node-title"><h2>Engineer</h2></div>
    <iframe class="l-page-slim-iframe" src="{frame}"></iframe>
    <script type="application/ld+json">{json.dumps(posting)}</script>
    </body></html>
    """.encode()

    async def run(publisher_id):
        def respond(request):
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text="User-agent: *\nDisallow:\n")
            assert str(request.url) == frame
            return httpx.Response(
                200,
                text=f"""
                <html><head><link rel="canonical"
                    href="https://publicjobs.ch/jobs/region/sector/{publisher_id}-engineer">
                </head><body><h1>Engineer</h1><div class="preview_body">
                Full description.
                <a href="https://www.publicjobs.ch/bewerben/~applyID321">Apply</a>
                </div></body></html>
                """,
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await JobiqoConnector("www.kampajobs.ch", client).kampajobs_linked_job(
                body, "42", url
            )

    assert asyncio.run(run(123)).application_url.endswith("~applyID321")
    with pytest.raises(ValueError, match="publisher identity mismatch"):
        asyncio.run(run(124))

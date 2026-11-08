import asyncio
from datetime import datetime

import httpx
import pytest
from vindex.connectors.jobboardcom import HOSTS, JobBoardComConnector
from vindex.connectors.registry import create_connector, detect

NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


def test_jobboardcom_rejects_unreviewed_origin():
    with pytest.raises(ValueError, match="Unreviewed JobBoard.com origin"):
        JobBoardComConnector("unreviewed.example.com", httpx.AsyncClient())


@pytest.mark.parametrize("host", sorted(HOSTS))
def test_jobboardcom_detection_is_scoped(host):
    for path in ("", "/", "/jobs", "/jobs/"):
        assert detect(f"https://{host}{path}") == ("jobboard_com", host)
    with pytest.raises(ValueError, match="Expected an unfiltered reviewed"):
        detect(f"https://{host}/jobs?query=test")
    with pytest.raises(ValueError, match="Expected an unfiltered reviewed"):
        detect(f"https://{host}/unrelated-path")


def test_jobboardcom_roster_success_and_filtering():
    host = "jobs.acevo.org.uk"
    connector = JobBoardComConnector(host, httpx.AsyncClient())
    index_xml = f"""<?xml version="1.0" encoding="utf-8"?>
    <sitemapindex xmlns="{NS}">
        <sitemap><loc>https://{host}/xml-sitemaps/1.xml</loc></sitemap>
    </sitemapindex>
    """.encode()

    jobs_xml = f"""<?xml version="1.0" encoding="utf-8"?>
    <urlset xmlns="{NS}">
        <url><loc>https://{host}/category/management/</loc></url>
        <url><loc>https://{host}/jobs/director-of-operations/101-1/</loc></url>
        <url><loc>https://{host}/jobs/finance-manager/102-1/</loc></url>
        <url><loc>https://{host}/jobs/alert/</loc></url>
    </urlset>
    """.encode()

    roster = connector.roster(index_xml, jobs_xml)
    assert roster == {
        "101-1": f"https://{host}/jobs/director-of-operations/101-1/",
        "102-1": f"https://{host}/jobs/finance-manager/102-1/",
    }


def test_jobboardcom_roster_rejects_missing_sitemap_index_target():
    host = "jobs.acevo.org.uk"
    connector = JobBoardComConnector(host, httpx.AsyncClient())
    index_xml = f"""<?xml version="1.0" encoding="utf-8"?>
    <sitemapindex xmlns="{NS}">
        <sitemap><loc>https://{host}/xml-sitemaps/other.xml</loc></sitemap>
    </sitemapindex>
    """.encode()
    jobs_xml = f"""<?xml version="1.0" encoding="utf-8"?>
    <urlset xmlns="{NS}">
        <url><loc>https://{host}/jobs/test-role/101-1/</loc></url>
    </urlset>
    """.encode()

    with pytest.raises(ValueError, match="jobs sitemap not found in sitemap index"):
        connector.roster(index_xml, jobs_xml)


def test_jobboardcom_roster_rejects_empty_or_oversized():
    host = "jobs.acevo.org.uk"
    connector = JobBoardComConnector(host, httpx.AsyncClient())
    index_xml = f"""<?xml version="1.0" encoding="utf-8"?>
    <sitemapindex xmlns="{NS}">
        <sitemap><loc>https://{host}/xml-sitemaps/1.xml</loc></sitemap>
    </sitemapindex>
    """.encode()

    # Empty
    empty_jobs = f'<urlset xmlns="{NS}"></urlset>'.encode()
    with pytest.raises(ValueError, match="outside supported bounds"):
        connector.roster(index_xml, empty_jobs)

    # Oversized (>200)
    urls = "".join(
        f"<url><loc>https://{host}/jobs/role-{i}/{i}-1/</loc></url>" for i in range(1, 202)
    )
    oversized_jobs = f'<urlset xmlns="{NS}">{urls}</urlset>'.encode()
    with pytest.raises(ValueError, match="outside supported bounds"):
        connector.roster(index_xml, oversized_jobs)


def test_jobboardcom_roster_rejects_duplicate_identifiers():
    host = "jobs.acevo.org.uk"
    connector = JobBoardComConnector(host, httpx.AsyncClient())
    index_xml = f"""<?xml version="1.0" encoding="utf-8"?>
    <sitemapindex xmlns="{NS}">
        <sitemap><loc>https://{host}/xml-sitemaps/1.xml</loc></sitemap>
    </sitemapindex>
    """.encode()
    dup_jobs = f"""<?xml version="1.0" encoding="utf-8"?>
    <urlset xmlns="{NS}">
        <url><loc>https://{host}/jobs/slug-a/101-1/</loc></url>
        <url><loc>https://{host}/jobs/slug-b/101-1/</loc></url>
    </urlset>
    """.encode()
    with pytest.raises(ValueError, match="Duplicate job identifier"):
        connector.roster(index_xml, dup_jobs)


def test_jobboardcom_parse_valid_detail():
    host = "jobs.acevo.org.uk"
    connector = JobBoardComConnector(host, httpx.AsyncClient())
    url = f"https://{host}/jobs/senior-director/501-1/"
    identifier = "501-1"

    body = f"""<!DOCTYPE html>
    <html>
    <head>
        <link rel="canonical" href="{url}">
        <script type="application/ld+json">
        {{
            "@context": "http://schema.org/",
            "@type": "JobPosting",
            "title": "Senior Director",
            "hiringOrganization": {{"@type": "Organization", "name": "Community Trust"}},
            "description": "&lt;p&gt;Leading operations and strategy.&lt;/p&gt;",
            "jobLocation": {{"@type": "Place", "name": "London, UK"}},
            "datePosted": "2026-10-20T09:00:00Z",
            "employmentType": ["FULL_TIME"],
            "baseSalary": {{"@type": "MonetaryAmount", "currency": "GBP", "value": {{"minValue": 50000, "maxValue": 60000}}}}
        }}
        </script>
    </head>
    <body>
        <a class="vacancy-apply" href="/jobs/apply/ats-redirect/?id={identifier}">Apply Now</a>
        <footer>
            <a href="https://www.jobboard.com/">Powered by JobBoard.com</a>
        </footer>
    </body>
    </html>
    """.encode()

    jobs = connector.parse((identifier, url, body))
    assert len(jobs) == 1
    job = jobs[0]
    assert job.external_id == identifier
    assert job.title == "Senior Director"
    assert job.company == "Community Trust"
    assert job.description == "Leading operations and strategy."
    assert job.location == "London, UK"
    assert job.source_url == url
    assert job.application_url == f"https://{host}/jobs/apply/ats-redirect/?id={identifier}"
    assert job.employment_type == "FULL_TIME"
    assert job.published_at == datetime.fromisoformat("2026-10-20T09:00:00+00:00")
    assert job.quality_flags == []
    assert job.salary == {
        "@type": "MonetaryAmount",
        "currency": "GBP",
        "value": {"minValue": 50000, "maxValue": 60000},
    }


def test_jobboardcom_parse_missing_location_adds_flag():
    host = "www.gradsouthwest.com"
    connector = JobBoardComConnector(host, httpx.AsyncClient())
    url = f"https://{host}/jobs/trainee/601-1/"
    identifier = "601-1"

    body = f"""<!DOCTYPE html>
    <html>
    <head>
        <link rel="canonical" href="{url}">
        <script type="application/ld+json">
        {{
            "@context": "http://schema.org/",
            "@type": "JobPosting",
            "title": "Graduate Trainee",
            "hiringOrganization": {{"@type": "Organization", "name": "Innovate Corp"}},
            "description": "Exciting graduate opportunity."
        }}
        </script>
    </head>
    <body>
        <a href="/jobs/apply/?id={identifier}">Apply</a>
        <a href="https://hotlizard.net/">HotLizard</a>
    </body>
    </html>
    """.encode()

    jobs = connector.parse((identifier, url, body))
    assert len(jobs) == 1
    assert jobs[0].quality_flags == ["location_missing"]
    assert jobs[0].location == ""


def test_jobboardcom_parse_validations():
    host = "jobs.acevo.org.uk"
    connector = JobBoardComConnector(host, httpx.AsyncClient())
    url = f"https://{host}/jobs/lead/701-1/"
    identifier = "701-1"

    valid_body = f"""<!DOCTYPE html>
    <html>
    <head>
        <link rel="canonical" href="{url}">
        <script type="application/ld+json">
        {{
            "@context": "http://schema.org/",
            "@type": "JobPosting",
            "title": "Team Lead",
            "hiringOrganization": {{"@type": "Organization", "name": "Charity A"}},
            "description": "Job details description"
        }}
        </script>
    </head>
    <body>
        <a href="/jobs/apply/?id={identifier}">Apply</a>
        <a href="https://www.jobboard.com/">JobBoard.com</a>
    </body>
    </html>
    """.encode()

    # Mismatched identifier
    with pytest.raises(ValueError, match="does not match identifier"):
        connector.parse(("999-1", url, valid_body))

    # Missing canonical
    with pytest.raises(ValueError, match="canonical"):
        connector.parse((identifier, url, valid_body.replace(b'rel="canonical"', b'rel="other"')))

    # Missing attribution
    with pytest.raises(ValueError, match="attribution"):
        connector.parse(
            (identifier, url, valid_body.replace(b"https://www.jobboard.com/", b"https://foo.com/"))
        )

    # Missing JobPosting
    with pytest.raises(ValueError, match="JobPosting schema"):
        connector.parse((identifier, url, valid_body.replace(b'"JobPosting"', b'"WebPage"')))

    # Missing company
    with pytest.raises(ValueError, match="Missing required title, company, or description"):
        connector.parse((identifier, url, valid_body.replace(b'"Charity A"', b'""')))

    # Missing apply button
    with pytest.raises(ValueError, match="Missing or ambiguous same-ID"):
        connector.parse((identifier, url, valid_body.replace(b"/jobs/apply/?id=701-1", b"/home")))


def test_jobboardcom_discover_flow():
    host = "jobs.acevo.org.uk"
    origin = f"https://{host}"
    job_url = f"{origin}/jobs/director/801-1/"

    robots_txt = f"User-agent: *\nAllow: /\nSitemap: {origin}/sitemap.xml\n".encode()
    index_xml = f"""<?xml version="1.0" encoding="utf-8"?>
    <sitemapindex xmlns="{NS}">
        <sitemap><loc>{origin}/xml-sitemaps/1.xml</loc></sitemap>
    </sitemapindex>
    """.encode()
    jobs_xml = f"""<?xml version="1.0" encoding="utf-8"?>
    <urlset xmlns="{NS}">
        <url><loc>{job_url}</loc></url>
    </urlset>
    """.encode()
    job_html = f"""<!DOCTYPE html>
    <html>
    <head>
        <link rel="canonical" href="{job_url}">
        <script type="application/ld+json">
        {{
            "@context": "http://schema.org/",
            "@type": "JobPosting",
            "title": "Director",
            "hiringOrganization": {{"@type": "Organization", "name": "Charity Org"}},
            "description": "Full director responsibility"
        }}
        </script>
    </head>
    <body>
        <a href="/jobs/apply/?id=801-1">Apply</a>
        <a href="https://www.jobboard.com/">JobBoard.com</a>
    </body>
    </html>
    """.encode()

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if url_str == f"{origin}/robots.txt":
            return httpx.Response(200, content=robots_txt)
        if url_str == f"{origin}/sitemap.xml":
            return httpx.Response(200, content=index_xml)
        if url_str == f"{origin}/xml-sitemaps/1.xml":
            return httpx.Response(200, content=jobs_xml)
        if url_str == job_url:
            return httpx.Response(200, content=job_html)
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = create_connector("jobboard_com", host, "Charity Org", client)

    enum = asyncio.run(connector.discover())
    assert enum.complete is True
    assert len(enum.jobs) == 1
    assert enum.jobs[0].title == "Director"
    assert enum.jobs[0].external_id == "801-1"


def test_jobboardcom_discover_drift_fails():
    host = "jobs.acevo.org.uk"
    origin = f"https://{host}"
    job_url1 = f"{origin}/jobs/director/801-1/"
    job_url2 = f"{origin}/jobs/manager/802-1/"

    robots_txt = f"User-agent: *\nAllow: /\nSitemap: {origin}/sitemap.xml\n".encode()
    index_xml = f"""<?xml version="1.0" encoding="utf-8"?>
    <sitemapindex xmlns="{NS}">
        <sitemap><loc>{origin}/xml-sitemaps/1.xml</loc></sitemap>
    </sitemapindex>
    """.encode()
    jobs_xml_1 = f"""<?xml version="1.0" encoding="utf-8"?>
    <urlset xmlns="{NS}">
        <url><loc>{job_url1}</loc></url>
    </urlset>
    """.encode()
    jobs_xml_2 = f"""<?xml version="1.0" encoding="utf-8"?>
    <urlset xmlns="{NS}">
        <url><loc>{job_url1}</loc></url>
        <url><loc>{job_url2}</loc></url>
    </urlset>
    """.encode()

    job_html = f"""<!DOCTYPE html>
    <html>
    <head>
        <link rel="canonical" href="{job_url1}">
        <script type="application/ld+json">
        {{
            "@context": "http://schema.org/",
            "@type": "JobPosting",
            "title": "Director",
            "hiringOrganization": {{"@type": "Organization", "name": "Charity Org"}},
            "description": "Full director responsibility"
        }}
        </script>
    </head>
    <body>
        <a href="/jobs/apply/?id=801-1">Apply</a>
        <a href="https://www.jobboard.com/">JobBoard.com</a>
    </body>
    </html>
    """.encode()

    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        url_str = str(request.url)
        if url_str == f"{origin}/robots.txt":
            return httpx.Response(200, content=robots_txt)
        if url_str == f"{origin}/sitemap.xml":
            return httpx.Response(200, content=index_xml)
        if url_str == f"{origin}/xml-sitemaps/1.xml":
            call_count += 1
            if call_count == 1:
                return httpx.Response(200, content=jobs_xml_1)
            return httpx.Response(200, content=jobs_xml_2)
        if url_str == job_url1:
            return httpx.Response(200, content=job_html)
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = create_connector("jobboard_com", host, "Charity Org", client)

    with pytest.raises(ValueError, match="roster changed during enumeration"):
        asyncio.run(connector.discover())

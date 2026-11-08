"""Tests for WP Job Manager public job board connector."""

import asyncio
import json
from datetime import datetime

import httpx
import pytest
from vindex.connectors.registry import create_connector, detect
from vindex.connectors.wp_job_manager import (
    HOSTS,
    WPJobManagerConnector,
)
from vindex.schemas import Enumeration, JobInput

SAMPLE_AJAX_JSON = json.dumps(
    {
        "found_jobs": True,
        "max_num_pages": 1,
        "html": """
<ul class="job_listings">
  <li class="post-99331 job_listing type-job_listing status-publish hentry">
    <a href="https://oliver-walters.com/job/cloud-architect-99331/">
      <div class="position"><h3>Cloud Architect</h3></div>
      <div class="company"><strong>Oliver Walters</strong></div>
      <div class="location">London, UK</div>
    </a>
  </li>
  <li class="post-99332 job_listing type-job_listing status-publish hentry">
    <a href="https://oliver-walters.com/job/erp-programme-manager-99332/">
      <div class="position"><h3>ERP Programme Manager</h3></div>
      <div class="company"><strong>Oliver Walters</strong></div>
      <div class="location">London, UK</div>
    </a>
  </li>
</ul>
""",
    }
).encode()

SAMPLE_AJAX_DRIFT_JSON = json.dumps(
    {
        "found_jobs": True,
        "max_num_pages": 1,
        "html": """
<ul class="job_listings">
  <li class="post-99331 job_listing type-job_listing status-publish hentry">
    <a href="https://oliver-walters.com/job/cloud-architect-99331/">
      <div class="position"><h3>Cloud Architect</h3></div>
    </a>
  </li>
</ul>
""",
    }
).encode()

SAMPLE_DETAIL_99331_HTML = b"""<!DOCTYPE html>
<html>
<head>
<title>Cloud Architect - Oliver Walters</title>
<script type="application/ld+json">
{
  "@context": "https://schema.org/",
  "@type": "JobPosting",
  "title": "Cloud Architect",
  "description": "<p>Lead AWS enterprise cloud transformations for Tier 1 institutions.</p>",
  "datePosted": "2026-11-05T15:43:53+00:00",
  "employmentType": "FULL_TIME",
  "hiringOrganization": {
    "@type": "Organization",
    "name": "Oliver Walters"
  },
  "jobLocation": {
    "@type": "Place",
    "address": {
      "addressLocality": "London",
      "addressCountry": "UK"
    }
  }
}
</script>
</head>
<body>
<div class="job_description">
  <p>Lead AWS enterprise cloud transformations for Tier 1 institutions.</p>
</div>
<div class="job-application">
  <a class="application_button button" href="https://oliver-walters.com/apply/99331">Apply for job</a>
</div>
</body>
</html>"""

SAMPLE_DETAIL_PEARL_HTML = b"""<!DOCTYPE html>
<html>
<head>
<title>Field Project Manager - Pearl Street Systems</title>
</head>
<body>
<h1 class="entry-title">Field Project Manager</h1>
<div class="job_description">
  <p>Overseeing the planning, coordination, and implementation of field-based projects.</p>
</div>
<div class="job-application">
  <a class="application_button button" href="https://pearlstreetsystems.com/job/field-project-manager/">Apply for job</a>
</div>
</body>
</html>"""


def test_wp_job_manager_rejects_unreviewed_host():
    client = httpx.AsyncClient()
    assert HOSTS == {"oliver-walters.com", "pearlstreetsystems.com"}
    with pytest.raises(ValueError, match="Unreviewed WP Job Manager host: unreviewed.example.com"):
        WPJobManagerConnector("unreviewed.example.com", client)


def test_wp_job_manager_detection():
    assert detect("https://oliver-walters.com/job-listings/") == (
        "wp_job_manager",
        "oliver-walters.com",
    )
    assert detect("https://oliver-walters.com/job-listings") == (
        "wp_job_manager",
        "oliver-walters.com",
    )
    assert detect("https://pearlstreetsystems.com/careers/") == (
        "wp_job_manager",
        "pearlstreetsystems.com",
    )
    assert detect("https://pearlstreetsystems.com/careers") == (
        "wp_job_manager",
        "pearlstreetsystems.com",
    )

    with pytest.raises(ValueError, match="Expected an unfiltered reviewed"):
        detect("https://oliver-walters.com/unreviewed-path")

    with pytest.raises(ValueError, match="Expected an unfiltered reviewed"):
        detect("https://pearlstreetsystems.com/?query=param")


def test_wp_job_manager_create_connector():
    client = httpx.AsyncClient()
    c = create_connector("wp_job_manager", "oliver-walters.com", "Oliver Walters", client)
    assert isinstance(c, WPJobManagerConnector)
    assert c.host == "oliver-walters.com"
    assert c.origin == "https://oliver-walters.com"
    assert c.default_company == "Oliver Walters"


def test_wp_job_manager_roster_ajax_json():
    client = httpx.AsyncClient()
    connector = WPJobManagerConnector("oliver-walters.com", client)
    roster = connector.roster(SAMPLE_AJAX_JSON)
    assert len(roster) == 2
    assert "99331" in roster
    assert "99332" in roster
    assert roster["99331"] == "https://oliver-walters.com/job/cloud-architect-99331/"
    assert roster["99332"] == "https://oliver-walters.com/job/erp-programme-manager-99332/"


def test_wp_job_manager_roster_empty_fails():
    client = httpx.AsyncClient()
    connector = WPJobManagerConnector("oliver-walters.com", client)
    with pytest.raises(ValueError, match="No jobs found on WP Job Manager board"):
        connector.roster(
            json.dumps({"found_jobs": False, "html": "<ul class='job_listings'></ul>"}).encode()
        )


def test_wp_job_manager_parse_detail_schema():
    client = httpx.AsyncClient()
    connector = WPJobManagerConnector("oliver-walters.com", client)
    job = connector.parse_detail(
        "99331",
        "https://oliver-walters.com/job/cloud-architect-99331/",
        SAMPLE_DETAIL_99331_HTML,
    )
    assert isinstance(job, JobInput)
    assert job.external_id == "99331"
    assert job.title == "Cloud Architect"
    assert job.company == "Oliver Walters"
    assert job.location == "London, UK"
    assert job.employment_type == "FULL_TIME"
    assert "enterprise cloud transformations" in job.description
    assert job.published_at == datetime.fromisoformat("2026-11-05T15:43:53+00:00")
    assert job.application_url == "https://oliver-walters.com/apply/99331"
    assert job.quality_flags == []


def test_wp_job_manager_parse_detail_html_fallback():
    client = httpx.AsyncClient()
    connector = WPJobManagerConnector("pearlstreetsystems.com", client)
    job = connector.parse_detail(
        "826",
        "https://pearlstreetsystems.com/job/field-project-manager/",
        SAMPLE_DETAIL_PEARL_HTML,
    )
    assert isinstance(job, JobInput)
    assert job.external_id == "826"
    assert job.title == "Field Project Manager"
    assert job.company == "Pearl Street Systems"
    assert "Overseeing the planning" in job.description
    assert job.application_url == "https://pearlstreetsystems.com/job/field-project-manager/"
    assert job.quality_flags == []


def test_wp_job_manager_discover_success():
    call_counts = {"ajax": 0, "detail": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("robots.txt"):
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        if "jm-ajax/get_listings" in url:
            call_counts["ajax"] += 1
            return httpx.Response(200, content=SAMPLE_AJAX_JSON)
        if "cloud-architect-99331" in url or "erp-programme-manager-99332" in url:
            call_counts["detail"] += 1
            return httpx.Response(200, content=SAMPLE_DETAIL_99331_HTML)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)

    async def run():
        async with httpx.AsyncClient(transport=transport) as client:
            connector = WPJobManagerConnector("oliver-walters.com", client)
            enum = await connector.discover()
            assert isinstance(enum, Enumeration)
            assert enum.complete is True
            assert len(enum.jobs) == 2
            assert call_counts["ajax"] == 2
            assert call_counts["detail"] == 2

    asyncio.run(run())


def test_wp_job_manager_discover_drift_failure():
    call_counts = {"ajax": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("robots.txt"):
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        if "jm-ajax/get_listings" in url:
            call_counts["ajax"] += 1
            if call_counts["ajax"] == 1:
                return httpx.Response(200, content=SAMPLE_AJAX_JSON)
            return httpx.Response(200, content=SAMPLE_AJAX_DRIFT_JSON)
        if "cloud-architect-99331" in url or "erp-programme-manager-99332" in url:
            return httpx.Response(200, content=SAMPLE_DETAIL_99331_HTML)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)

    async def run():
        async with httpx.AsyncClient(transport=transport) as client:
            connector = WPJobManagerConnector("oliver-walters.com", client)
            with pytest.raises(
                ValueError, match="WP Job Manager roster changed during enumeration"
            ):
                await connector.discover()

    asyncio.run(run())


def test_wp_job_manager_rejects_partial_pagination():
    connector = WPJobManagerConnector("oliver-walters.com", httpx.AsyncClient())
    payload = json.loads(SAMPLE_AJAX_JSON)
    payload["max_num_pages"] = 2
    with pytest.raises(ValueError, match="incomplete"):
        connector.roster(json.dumps(payload).encode())

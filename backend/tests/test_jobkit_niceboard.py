import httpx
import pytest
from vindex.connectors.jobkit import JobKitConnector
from vindex.connectors.niceboard import NiceboardConnector
from vindex.connectors.registry import detect


def test_jobkit_rejects_a_valid_looking_first_page_with_missing_jobs():
    connector = JobKitConnector("jobs.rubyonrails.org", httpx.AsyncClient())
    body = b"""
    <html><link rel="canonical" href="https://jobs.rubyonrails.org/">
    <a href="https://www.jobkit.io/">JobKit</a>
    <input name="q" placeholder="Search through 2 jobs...">
    <a href="/jobs/7-an-engineer">Engineer</a></html>
    """
    with pytest.raises(ValueError, match="does not match"):
        connector.roster(body)


def test_niceboard_rejects_out_of_scope_sitemap_job():
    connector = NiceboardConnector("jobs.aiacolorado.org", httpx.AsyncClient())
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    entries = "".join(
        f"<sitemap><loc>https://jobs.aiacolorado.org/sitemap-{kind}.xml</loc></sitemap>"
        for kind in ("jobs", "base", "companies")
    )
    index = f'<sitemapindex xmlns="{ns}">{entries}</sitemapindex>'
    jobs = f'<urlset xmlns="{ns}"><url><loc>https://example.com/job/7-some-job</loc></url></urlset>'
    with pytest.raises(ValueError, match="Unscoped"):
        connector.roster(index.encode(), jobs.encode())


@pytest.mark.parametrize(
    ("url", "provider"),
    [
        ("https://jobs.aiacolorado.org/", "niceboard"),
        ("https://jobs.medicalalley.org/", "niceboard"),
        ("https://jobs.rubyonrails.org/", "jobkit"),
        ("https://welpora.jobkit.io/", "jobkit"),
    ],
)
def test_native_board_detection_is_scoped(url, provider):
    assert detect(url)[0] == provider
    with pytest.raises(ValueError):
        detect(url + "?q=engineering")

import httpx
import pytest
from vindex.connectors.exenzo import ExenzoConnector
from vindex.connectors.jobboardhq import JobBoardHQConnector
from vindex.connectors.paradox import ParadoxConnector
from vindex.connectors.phenompeople import PhenomPeopleConnector
from vindex.connectors.registry import detect
from vindex.connectors.rival import RivalConnector


def test_jobboardhq_rejects_a_postback_that_returns_the_previous_page():
    connector = JobBoardHQConnector("resume.absc.org", httpx.AsyncClient())
    html = b"""
    <html><form id="form1" method="post" action="./search">
      <div class="pagerLinks"><span class="pagerCurrentPage">1</span></div>
    </form></html>
    """
    with pytest.raises(ValueError, match="Unexpected JobBoardHQ page number"):
        connector.page(html, 2)


def test_rival_rejects_next_page_for_another_portal():
    connector = RivalConnector("BlandLandscaping/Careers", httpx.AsyncClient())
    html = b"""
    <html><h1 id="Jobs_JobsList_CompanyName">Bland Landscaping Company</h1>
      <section class="sr-pagination">
        <div id="Jobs_PagedJobList_CurrentPageText">Page 1 of 2</div>
        <button id="Jobs_PagedJobList_NextLink" data-href="/RSCS/Careers?page=2">Next</button>
      </section>
    </html>
    """
    with pytest.raises(ValueError, match="Unexpected Rival next page"):
        connector.page(html, 1)


def test_exenzo_rejects_a_partial_advertised_roster():
    connector = ExenzoConnector("agconnect.exenzo.nl", httpx.AsyncClient())
    html = b"""
    <html><h3><span>2</span> vacatures gevonden</h3>
      <div class="row job">
        <h2 itemprop="title"><a href="/vacatures/engineer-9x">Engineer</a></h2>
      </div>
    </html>
    """
    with pytest.raises(ValueError, match="full advertised roster"):
        connector.roster(html)


@pytest.mark.parametrize(
    ("url", "provider"),
    [
        ("https://jobs.silkroad.com/RSCS/Careers", "rival"),
        ("https://resume.absc.org/search", "jobboardhq"),
        ("https://vacatures.ecommerce.nl/vacatures", "exenzo"),
    ],
)
def test_coverage_sources_accept_only_the_unfiltered_entry(url, provider):
    assert detect(url)[0] == provider
    with pytest.raises(ValueError, match="unfiltered"):
        detect(url + "?page=2")


def test_paradox_rejects_repeated_first_page_at_second_offset():
    connector = ParadoxConnector("flynnrgcareers.com", httpx.AsyncClient())
    html = b'<html><p class="results-header__content">Showing 1-10 of 12 jobs</p></html>'
    with pytest.raises(ValueError, match="Unexpected Paradox result range"):
        connector.page(html, 2)


def test_phenom_rejects_a_truncated_terminal_search_page():
    connector = PhenomPeopleConnector("careers.phenom.com", httpx.AsyncClient())
    html = b"""
    <html><script>phApp.ddo = {"eagerLoadRefineSearch": {
      "status": 200, "hits": 1, "totalHits": 12,
      "eid": {"searchType": "allJobs", "query": ""},
      "data": {"jobs": [{"jobId": "1", "jobSeqNo": "EXTERNAL1", "title": "Engineer"}]}
    }};</script></html>
    """
    with pytest.raises(ValueError, match="incomplete Phenom search page"):
        connector.page(html, 10)

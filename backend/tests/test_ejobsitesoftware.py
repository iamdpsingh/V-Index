import httpx
import pytest
from vindex.connectors.ejobsitesoftware import EJobsiteSoftwareConnector
from vindex.connectors.registry import detect


def test_ejobsitesoftware_rejects_incomplete_terminal_page():
    connector = EJobsiteSoftwareConnector("seasonaljobs.co.nz", httpx.AsyncClient())
    fragment = b'<div class="previewBox" id="123"><h4>Engineer</h4></div>'
    assert connector.page(fragment, 10, 11) == (11, {"123": ("", "Engineer")}, "")
    with pytest.raises(ValueError, match="Incomplete eJobsiteSoftware page"):
        connector.page(fragment, 10, 12)
    with pytest.raises(ValueError, match="repeated"):
        connector.page(fragment * 2, 10, 12)


def test_ejobsitesoftware_detection_scopes_to_unfiltered_boards():
    assert detect("https://gurushrconsultancy.com/jobboard/job-search/") == (
        "ejobsitesoftware_com",
        "gurushrconsultancy.com",
    )
    with pytest.raises(ValueError, match="unfiltered"):
        detect("https://gurushrconsultancy.com/jobboard/job-search/?keyword=engineer")

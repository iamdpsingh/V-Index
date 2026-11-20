import httpx
import pytest
from vindex.connectors.jboard import JBoardConnector


def test_native_pipe_slug_retains_origin_and_encoded_separator_protection():
    connector = JBoardConnector("jboard", "jobs.cisontario.ca", "Board", httpx.AsyncClient())
    for suffix in ("role-|-2027", "role-%7C-2027"):
        assert (
            connector.identifier("https://jobs.cisontario.ca/jobs/802886053-" + suffix)
            == "802886053"
        )
    for url in (
        "https://evil.example/jobs/1-role",
        "/jobs/1-role%2Fadmin",
        "/jobs/1-role?private=1",
        "/jobs/1-role#fragment",
    ):
        with pytest.raises(ValueError):
            connector.identifier(url)

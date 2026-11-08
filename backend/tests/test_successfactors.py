import httpx
import pytest
from vindex.connectors.successfactors import SuccessFactorsConnector


def test_successfactors_rejects_missing_rows_and_detail_opt_out():
    origin = "https://careers.icbc.com"
    connector = SuccessFactorsConnector("careers.icbc.com", httpx.AsyncClient())
    path = "/job/Engineer/1234/"
    board = f"""
    <html><span class="paginationLabel">Results 1 – 1 of 1</span>
    <a class="jobTitle-link" href="{path}">Engineer</a></html>
    """.encode()
    assert connector.roster(board) == {"1234": origin + path}
    with pytest.raises(ValueError, match="complete single-page"):
        connector.roster(board.replace(b"of 1", b"of 2"))
    with pytest.raises(ValueError, match="opts out"):
        connector.parse(
            ("1234", origin + path, b'<html><meta name="robots" content="noindex"></html>')
        )

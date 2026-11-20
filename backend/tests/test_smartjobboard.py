import httpx
import pytest
from vindex.connectors.smartjobboard import SmartJobBoardConnector


def test_repeated_or_truncated_smartjobboard_page_cannot_reconcile():
    host = "americanbath.mysmartjobboard.com"
    connector = SmartJobBoardConnector(host, httpx.AsyncClient())
    body = f"""
    <html>
    <h1>21 jobs found</h1>
    <button class="load-more" data-page="2" data-backfilling="true"></button>
    <script>var listingPerPage = 20; $.get('?&page=' + page);</script>
    <h2 class="listing-item__title"><a href="https://{host}/job/7/example/">Engineer</a></h2>
    </html>
    """.encode()
    assert connector.page(body, 2, 21) == (21, {"7": f"https://{host}/job/7/example/"})
    with pytest.raises(ValueError, match="mismatched"):
        connector.page(body.replace(b'data-page="2"', b'data-page="1"'), 2, 21)
    with pytest.raises(ValueError, match="Incomplete"):
        connector.page(body.replace(b"listing-item__title", b"unrelated"), 2, 21)


def test_native_accented_slugs_are_not_mistaken_for_unscoped_hosts():
    host = "americanbath.mysmartjobboard.com"
    connector = SmartJobBoardConnector(host, httpx.AsyncClient())
    url = f"https://{host}/job/7975/journalier-ère-de-production/"
    body = f'''<html><h1>1 job found</h1><script>var listingPerPage = 20; $.get('?&page=' + page);</script>
    <h2 class="listing-item__title"><a href="{url}">Role</a></h2></html>'''.encode()
    assert connector.page(body, 1, None) == (1, {"7975": url})
    with pytest.raises(ValueError, match="Unscoped"):
        connector.page(body.replace(host.encode(), b"evil.example"), 1, None)

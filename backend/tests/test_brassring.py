import json
from html import escape

import httpx
import pytest
from vindex.connectors.brassring import BrassRingConnector
from vindex.connectors.registry import detect


def test_brassring_rejects_partial_public_roster():
    connector = BrassRingConnector("25749-5764", httpx.AsyncClient())
    fields = {"reqid": "1", "clientid": "25749", "siteid": "5764", "jobtitle": "Engineer"}
    job = {"Questions": [{"QuestionName": key, "Value": value} for key, value in fields.items()]}
    payload = {
        "LoggedIn": False,
        "ShowCaptcha": False,
        "SolarErrorOccurred": False,
        "searchResultsResponse": {"Jobs": {"Job": [job]}, "JobsCount": 2},
    }
    with pytest.raises(ValueError, match="entire advertised roster"):
        connector.roster(
            f'<html><input id="preLoadJSON" value="{escape(json.dumps(payload))}"></html>'.encode()
        )
    assert detect(connector.url()) == ("brassring", "25749-5764")
    with pytest.raises(ValueError, match="unfiltered"):
        detect(connector.url() + "&jobid=1")

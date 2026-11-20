import asyncio
import json
from copy import deepcopy

import httpx
import pytest
from vindex.connectors.registry import detect
from vindex.connectors.talentreef import GATEWAY, SEARCH, TalentReefConnector

TEMPLATE = {
    "locale": "en",
    "published": True,
    "availability": "EXTERNAL",
    "clientId": "20929",
    "clients": [{"legacyClientId": "20929", "clientName": "Example"}],
    "brands": [],
    "brandIds": [],
    "locationIds": [],
    "jobCategories": [],
}


def posting(identifier):
    return {
        "jobId": identifier,
        "clientId": 20929,
        "clientName": "Example",
        "brand": "Example Brand",
        "positionType": "Engineer",
        "description": "<p>Build things.</p>",
        "internalOrExternal": "externalOnly",
        "address": {"city": "London", "country": "UK"},
        "url": f"/apply/c_example/l_en/engineer-{identifier}.html",
        "extUuid": "",
        "createdDate": "2026-11-19T12:00:00Z",
        "contractType": "fullTime",
        "pubCompensation": 0,
        "minCompensation": 12345,
        "maxCompensation": 99999,
    }


@pytest.mark.parametrize("failure", [None, "internal", "partial", "duplicate", "drift", "template"])
def test_talentreef_complete_external_collection_and_reconfirmation(monkeypatch, failure):
    monkeypatch.setattr("vindex.connectors.talentreef.PAGE_SIZE", 2)
    searches = 0

    def handle(request):
        nonlocal searches
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.method == "GET":
            assert str(request.url) == GATEWAY + "/apply/careerPages/alias/jcresortsjobs"
            template = deepcopy(TEMPLATE)
            if failure == "template":
                template["availability"] = "INTERNAL"
            return httpx.Response(200, json=[template])
        assert str(request.url) == SEARCH
        body = json.loads(request.content)
        assert body["query"]["bool"]["filter"] == [
            {"terms": {"clientId.raw": ["20929"]}},
            {"terms": {"internalOrExternal": [{"internalOrExternal": "externalOnly"}]}},
        ]
        searches += 1
        offset = body["from"]
        rows = [posting(i) for i in range(1, 4)][offset : offset + 2]
        if failure == "duplicate" and offset:
            rows[0] = posting(1)
        if failure == "internal" and rows:
            rows[0]["internalOrExternal"] = "internalOnly"
        if failure == "drift" and searches > 2 and rows:
            rows[0]["description"] = "Changed during the crawl"
        return httpx.Response(
            200,
            json={
                "timed_out": False,
                "_shards": {
                    "total": 1,
                    "successful": 0 if failure == "partial" else 1,
                    "failed": 0,
                },
                "hits": {
                    "total": {"value": 3, "relation": "eq"},
                    "hits": [{"_source": row} for row in rows],
                },
            },
        )

    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            connector = TalentReefConnector("jcresortsjobs", client)
            if failure:
                with pytest.raises(ValueError):
                    await connector.discover()
                return
            result = await connector.discover()
            assert result.complete and len(result.jobs) == 3
            assert searches == 4
            job = result.jobs[0]
            assert job.company == "Example Brand" and job.description == "Build things."
            assert job.salary is None
            assert "minCompensation" not in job.raw["posting"]
            assert job.published_at.year == 2026
            assert job.application_url.endswith("engineer-1.html")

    asyncio.run(check())


def test_talentreef_application_identity_and_public_salary():
    connector = TalentReefConnector("jcresortsjobs", httpx.AsyncClient())
    row = posting(123)
    row.update(pubCompensation=1, isSalaried=False)
    assert connector.parse(row)[0].salary["minCompensation"] == 12345
    for path in [
        "https://example.org/apply",
        "/apply/c_example/l_en/engineer-999.html",
        "/apply/c_example/l_en/engineer-123.html?internalApplicant=true",
    ]:
        row["url"] = path
        with pytest.raises(ValueError):
            connector.parse(row)
    assert detect("https://apply.jobappnetwork.com/jcresortsjobs/en") == (
        "talentreef",
        "jcresortsjobs",
    )
    with pytest.raises(ValueError):
        detect("https://apply.jobappnetwork.com/unreviewed/en")

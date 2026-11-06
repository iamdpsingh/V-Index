import asyncio
import json
from pathlib import Path

import httpx
import pytest
from vindex.connectors.public import PublicConnector, detect, text


@pytest.mark.parametrize(
    "url",
    [
        "http://jobs.lever.co/a",
        "https://localhost/a",
        "https://127.0.0.1/a",
        "https://jobs.lever.co.evil.com/a",
        "https://user@jobs.lever.co/a",
        "https://jobs.lever.co:444/a",
        "https://jobs.lever.co/%2e%2e",
        "https://jobs.lever.co/",
        "https://jobs.lever.co/a%2fb",
    ],
)
def test_detect_rejects_unsafe_urls(url):
    with pytest.raises(ValueError):
        detect(url)


@pytest.mark.parametrize(
    "url,provider",
    [
        ("https://job-boards.greenhouse.io/stripe", "greenhouse"),
        ("https://jobs.lever.co/palantir", "lever"),
        ("https://jobs.eu.lever.co/example", "lever-eu"),
        ("https://jobs.ashbyhq.com/Ashby", "ashby"),
    ],
)
def test_detect_known(url, provider):
    assert detect(url)[0] == provider


def test_html_entities_become_text():
    assert text("&lt;p&gt;Build &amp; ship&lt;/p&gt;") == "Build & ship"


def test_live_sample_regressions():
    root = Path(__file__).resolve().parents[2] / "evidence"
    for name in ["greenhouse-stripe", "lever-palantir", "ashby-Ashby"]:
        sample = json.loads((root / (name + "-sample.json")).read_text())
        provider = name.split("-")[0]
        connector = PublicConnector(provider, "example", sample["company"], None)
        payload = [sample["raw"]] if provider == "lever" else {"jobs": [sample["raw"]]}
        parsed = connector.parse(payload)[0]
        assert parsed.title == sample["title"]
        assert parsed.description == sample["description"]
        assert parsed.application_url == sample["application_url"]


def lever_row(i):
    return {
        "id": str(i),
        "text": "Engineer",
        "hostedUrl": f"https://jobs.lever.co/example/{i}",
        "applyUrl": f"https://jobs.lever.co/example/{i}/apply",
    }


def run_connector(provider, handler):
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await PublicConnector(provider, "example", "Example", client).discover()

    return asyncio.run(run())


def test_lever_pagination_fetches_final_empty_page():
    seen = []

    def handler(request):
        skip = int(request.url.params["skip"])
        seen.append(skip)
        return httpx.Response(200, json=[lever_row(i) for i in range(100)] if skip == 0 else [])

    assert len(run_connector("lever", handler).jobs) == 100
    assert seen == [0, 100]


def test_repeated_pages_rejected():
    with pytest.raises(ValueError, match="Duplicate"):
        run_connector(
            "lever", lambda request: httpx.Response(200, json=[lever_row(i) for i in range(100)])
        )


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(302, headers={"Location": "http://127.0.0.1"}),
        httpx.Response(200, json={}),
        httpx.Response(200, json={"jobs": [], "meta": {"total": 4}}),
    ],
)
def test_bad_or_incomplete_snapshots_rejected(response):
    with pytest.raises((ValueError, KeyError)):
        run_connector("greenhouse", lambda request: response)


def test_ashby_unlisted_not_exposed_and_hybrid_preserved():
    row = {
        "jobUrl": "https://jobs.ashbyhq.com/example/1",
        "applyUrl": "https://jobs.ashbyhq.com/example/1/apply",
        "title": "Engineer",
        "workplaceType": "Hybrid",
        "isRemote": True,
    }
    result = run_connector(
        "ashby",
        lambda request: httpx.Response(200, json={"jobs": [row, {**row, "isListed": False}]}),
    )
    assert len(result.jobs) == 1
    assert result.jobs[0].remote_status == "Hybrid"


def test_retry_budget(monkeypatch):
    async def no_wait(_):
        pass

    monkeypatch.setattr("vindex.connectors.http.asyncio.sleep", no_wait)
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(503)

    with pytest.raises(httpx.HTTPStatusError):
        run_connector("greenhouse", handler)
    assert len(calls) == 3

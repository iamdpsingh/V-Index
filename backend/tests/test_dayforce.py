import asyncio
import json

import httpx
import pytest
from vindex.connectors.dayforce import ORIGIN, DayforceConnector
from vindex.connectors.http import PublicHTTP
from vindex.connectors.registry import detect

SITE = {
    "clientNamespace": "mew",
    "jobBoardCode": "candidateportal",
    "cultureCode": "en-US",
    "jobBoardId": 1,
    "enableApplyWithoutAccount": True,
}


def listing(identifier):
    return {
        "jobPostingId": identifier,
        "clientNamespace": "mew",
        "jobBoardId": 1,
        "jobReqId": identifier + 100,
        "jobTitle": "Engineer",
    }


def page(identifier=None, failure=None):
    queries = [{"queryKey": ["site-info"], "state": {"status": "success", "data": SITE}}]
    if identifier is not None:
        row = listing(identifier)
        row.update(
            isInternal=failure == "internal",
            postingStatus=1,
            jobApplicationTemplateId=2,
            jobPostingContent={
                "jobDescriptionHeader": "About us",
                "jobDescription": "<p>Build things.</p>",
                "jobDescriptionFooter": "Apply today",
            },
            postingLocations=[{"formattedAddress": "London"}],
            jobPostingAttributes=[{"name": "EmploymentIndicator", "value": "Full-time"}],
            postingStartTimestampUTC="2026-11-19T12:00:00Z",
        )
        if failure == "identity":
            row["jobPostingId"] += 1
        queries.append({"queryKey": ["jobs"], "state": {"status": "success", "data": row}})
    data = {
        "props": {
            "pageProps": {
                "session": {"status": "unauthenticated", "data": {"user": {}}},
                "dehydratedState": {"queries": queries},
            }
        }
    }
    return f'<html><script id="__NEXT_DATA__" type="application/json">{json.dumps(data)}</script></html>'


@pytest.mark.parametrize("failure", [None, "csrf", "internal", "identity", "drift", "short_page"])
def test_dayforce_anonymous_handshake_and_full_reconciliation(monkeypatch, failure):
    monkeypatch.setattr("vindex.connectors.dayforce.PAGE_SIZE", 2)
    searches = 0

    def handle(request):
        nonlocal searches
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.path == "/api/auth/csrf":
            return httpx.Response(
                200,
                json={"csrfToken": "invalid" if failure == "csrf" else "a" * 64},
                headers={"Set-Cookie": "visitor=anonymous; Path=/"},
            )
        if request.method == "POST":
            searches += 1
            assert request.url.path == "/api/geo/mew/jobposting/search"
            assert request.headers["X-CSRF-TOKEN"] == "a" * 64
            assert "visitor=anonymous" in request.headers.get("cookie", "")
            assert "authorization" not in request.headers
            data = json.loads(request.content)
            assert data["clientNamespace"] == "mew" and data["jobBoardCode"] == "CANDIDATEPORTAL"
            offset = data["paginationStart"]
            rows = [listing(i) for i in range(1, 4)][offset : offset + 2]
            if failure == "drift" and searches > 2:
                rows[0]["jobTitle"] = "Changed during extraction"
            if failure == "short_page":
                rows = rows[:1]
            return httpx.Response(
                200, json={"maxCount": 3, "offset": offset, "count": len(rows), "jobPostings": rows}
            )
        identifier = (
            int(request.url.path.rsplit("/", 1)[-1]) if "/jobs/" in request.url.path else None
        )
        return httpx.Response(200, text=page(identifier, failure))

    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            connector = DayforceConnector("mew", client)
            if failure:
                with pytest.raises(ValueError):
                    await connector.discover()
                return
            result = await connector.discover()
            assert result.complete and len(result.jobs) == 3 and searches == 4
            job = result.jobs[0]
            assert job.description == "About us\n\nBuild things.\n\nApply today"
            assert job.company == "MAAS Energy Works" and job.employment_type == "Full-time"
            assert job.application_url == ORIGIN + "/en-US/mew/CANDIDATEPORTAL/jobs/1/apply"
            assert job.published_at.year == 2026

    asyncio.run(check())


def test_dayforce_csrf_header_and_source_locale_are_scoped():
    with pytest.raises(ValueError, match="anonymous public visitor"):
        DayforceConnector("mew", httpx.AsyncClient()).state(
            page().replace("unauthenticated", "authenticated").encode()
        )
    assert detect(ORIGIN + "/en-AU/silklaser/CANDIDATEPORTAL") == ("dayforce", "silklaser")
    for url in [
        ORIGIN + "/en-US/silklaser/CANDIDATEPORTAL",
        ORIGIN + "/en-US/mew/CANDIDATEPORTAL/jobs/1",
        ORIGIN + "/en-US/mew/CANDIDATEPORTAL?internal=true",
    ]:
        with pytest.raises(ValueError):
            detect(url)

    async def check():
        async with httpx.AsyncClient() as client:
            http = PublicHTTP(client, {"jobs.dayforcehcm.com"})
            for url, token in [
                (ORIGIN + "/api/auth/signin", "a" * 64),
                (ORIGIN + "/api/geo/mew/jobposting/search", "invalid"),
            ]:
                with pytest.raises(ValueError):
                    await http.read(url, headers={"X-CSRF-TOKEN": token})

    asyncio.run(check())

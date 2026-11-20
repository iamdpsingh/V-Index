import asyncio
import json

import httpx
import pytest
from vindex.connectors.gem import API, GemConnector
from vindex.connectors.http import PublicHTTP
from vindex.connectors.registry import detect

IDENTIFIER = "am9icG9zdDExample123"
LISTING = {
    "extId": IDENTIFIER,
    "title": "Engineer",
    "locations": [{"name": "London", "isRemote": False}],
    "job": {"locationType": "IN_OFFICE", "employmentType": "FULL_TIME"},
}
DETAIL = {
    "extId": IDENTIFIER,
    "title": "Engineer",
    "descriptionHtml": "<p>Build useful things.</p>",
    "firstPublishedTsSec": 1795046400,
    "compensationHtml": "<p>£50,000 annually</p>",
    "jobPostSectionHtml": {"introHtml": "About Example", "outroHtml": "Apply today"},
}


@pytest.mark.parametrize("failure", [None, "partial", "identity", "drift", "403"])
def test_gem_full_discovery_rejects_partial_or_changing_rosters(failure):
    listings = 0
    methods = []

    def handle(request):
        nonlocal listings
        methods.append((request.method, request.url.path))
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.method == "POST":
            assert str(request.url) == API
            assert request.headers["batch"] == "true"
            assert "authorization" not in request.headers
            query = json.loads(request.content)[0]
            assert query["query"].lstrip().startswith("query ")
            if failure == "403":
                return httpx.Response(403)
            if query["operationName"] == "JobBoardList":
                listings += 1
                row = dict(LISTING)
                if failure == "drift" and listings > 1:
                    row["title"] = "Changed role"
                response = {"data": {"oatsExternalJobPostings": {"jobPostings": [row]}}}
                if failure == "partial":
                    response["errors"] = [{"message": "Partial response"}]
            else:
                row = dict(DETAIL)
                if failure == "identity":
                    row["extId"] = "AnotherPosting123"
                response = {"data": {"oatsExternalJobPosting": row}}
            return httpx.Response(200, json=[response])
        title = "Example Careers" if request.url.path == "/example" else "Engineer"
        return httpx.Response(200, text=f"<html><title>{title}</title>{IDENTIFIER}</html>")

    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            connector = GemConnector("example", "Example", client)
            if failure:
                with pytest.raises(ValueError):
                    await connector.discover()
                return
            batch = await connector.discover()
            assert batch.complete and len(batch.jobs) == 1
            job = batch.jobs[0]
            assert (
                job.description
                == "About Example\n\nBuild useful things.\n\n£50,000 annually\n\nApply today"
            )
            assert job.salary == {"text": "£50,000 annually"}
            assert job.published_at.year == 2026
            assert job.remote_status == "On-site"
            assert job.application_url == f"https://jobs.gem.com/example/{IDENTIFIER}"

    asyncio.run(check())
    assert all(method in {"GET", "POST"} for method, _ in methods)
    if failure == "403":
        assert sum(method == "POST" for method, _ in methods) == 1


def test_gem_detection_and_batch_header_are_scoped():
    assert detect("https://jobs.gem.com/example") == ("gem", "example")
    for url in [
        "https://jobs.gem.com/example?filter=1",
        "https://jobs.gem.com/example/job-id",
        "https://jobs.gem.com@localhost/example",
    ]:
        with pytest.raises(ValueError):
            detect(url)

    async def check():
        async with httpx.AsyncClient() as client:
            http = PublicHTTP(client, {"jobs.gem.com"})
            for url, headers in [
                (API, {"batch": "false"}),
                (API, {"Origin": "https://example.org"}),
                ("https://jobs.gem.com/other", {"batch": "true"}),
            ]:
                with pytest.raises(ValueError):
                    await http.read(url, headers=headers)

    asyncio.run(check())

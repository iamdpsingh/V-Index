import asyncio
from contextlib import nullcontext
from datetime import datetime, timedelta
from unittest.mock import Mock

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_lifecycle import posting
from vindex import api, worker
from vindex.db import Observation, Run
from vindex.ingest import ingest
from vindex.schemas import Enumeration


@pytest.fixture
def client(database, monkeypatch):
    monkeypatch.setattr(api, "Session", database)
    monkeypatch.setenv("ADMIN_TOKEN", "test-secret")
    return TestClient(api.app)


def test_api_auth_validation_and_duplicate_sources(client):
    body = {"url": "https://jobs.ashbyhq.com/example", "company": "Example"}
    headers = {"Authorization": "Bearer test-secret"}
    assert client.post("/api/v1/sources", json=body).status_code == 401
    assert client.post("/api/v1/sources", json=body, headers=headers).status_code == 201
    assert client.post("/api/v1/sources", json=body, headers=headers).status_code == 409
    assert (
        client.post(
            "/api/v1/sources", json={**body, "url": "https://127.0.0.1/a"}, headers=headers
        ).status_code
        == 422
    )
    assert client.post("/api/v1/sources/1/refresh", headers=headers).status_code == 202
    assert client.post("/api/v1/sources/99/refresh", headers=headers).status_code == 404
    assert client.get("/health").json() == {"status": "ok"}


def test_search_filter_pagination_and_literal_wildcard(client, database, source):
    with database() as s:
        ingest(
            s,
            source,
            Enumeration(
                jobs=[
                    posting(),
                    posting(
                        external_id="2",
                        title="Analyst",
                        location="Paris",
                        application_url="https://example.com/jobs/2",
                    ),
                ],
                complete=True,
            ),
        )
        s.commit()
    result = client.get("/api/v1/jobs?keyword=engineer&company=example&location=london").json()
    assert result["total"] == 1
    assert result["items"][0]["sources"][0]["status"] == "open"
    assert client.get("/api/v1/jobs?limit=1&offset=1").json()["items"][0]["title"] == "Engineer"
    assert client.get("/api/v1/jobs?keyword=%25").json()["total"] == 0
    assert client.get("/api/v1/jobs?limit=0").status_code == 422
    assert client.get("/api/v1/jobs/1").status_code == 200
    assert client.get("/api/v1/jobs/99").status_code == 404


def test_exact_provider_inventory(client):
    rows = client.get("/api/v1/providers").json()
    assert len(rows) == 78
    assert len({r["name"] for r in rows}) == 78
    assert sum(r["kind"] == "ats" for r in rows) == 58


def test_api_reads_updated_index_without_cached_snapshot(client, database, source):
    with database() as session:
        ingest(session, source, Enumeration(jobs=[posting()], complete=True))
        session.commit()
    first = client.get("/api/v1/jobs")
    assert first.headers["cache-control"] == "no-store"
    assert first.json()["total"] == 1
    item = first.json()["items"][0]
    for value in (
        item["first_seen_at"],
        item["last_changed_at"],
        item["sources"][0]["last_checked_at"],
    ):
        assert datetime.fromisoformat(value).utcoffset() == timedelta(0)
    job_id = first.json()["items"][0]["id"]
    with database() as session:
        ingest(
            session,
            source,
            Enumeration(
                jobs=[
                    posting(description="Newly revised pipeline responsibilities"),
                    posting(
                        external_id="new-role",
                        title="Data Analyst",
                        application_url="https://example.com/jobs/new-role",
                    ),
                ],
                complete=True,
            ),
        )
        session.commit()
    updated = client.get("/api/v1/jobs")
    assert updated.json()["total"] == 2
    original = next(item for item in updated.json()["items"] if item["id"] == job_id)
    assert original["description"] == "Newly revised pipeline responsibilities"
    assert client.get("/api/v1/jobs?keyword=analyst").json()["total"] == 1
    for url in (f"/api/v1/jobs/{job_id}", "/api/v1/providers", "/health", "/api/v1/jobs/999999"):
        assert client.get(url).headers["cache-control"] == "no-store"
    detail = client.get(f"/api/v1/jobs/{job_id}").json()
    for value in (
        detail["first_seen_at"],
        detail["last_changed_at"],
        detail["sources"][0]["last_checked_at"],
    ):
        assert datetime.fromisoformat(value).utcoffset() == timedelta(0)


def test_fetch_failure_recorded_without_closing(database, source, monkeypatch):
    with database() as s:
        ingest(s, source, Enumeration(jobs=[posting()], complete=True))
        s.commit()
    monkeypatch.setattr(worker, "Session", database)
    redis = Mock()
    redis.lock.return_value = nullcontext()
    monkeypatch.setattr(worker.Redis, "from_url", lambda url: redis)

    async def failed(self):
        raise ValueError("Incomplete pagination")

    monkeypatch.setattr(
        worker, "create_connector", lambda *args: Mock(discover=lambda: failed(None))
    )
    run_id = asyncio.run(worker.refresh(source.id))
    with database() as s:
        run = s.get(Run, run_id)
        assert run.status == "failed"
        assert "Incomplete pagination" in run.error
        obs = s.scalar(select(Observation))
        assert obs.status == "open" and obs.missing_count == 0


def test_public_detail_does_not_disclose_raw_or_internal_observations(client, database, source):
    canary = "PRIVATE_INGESTION_CANARY_NEVER_PUBLIC"
    with database() as session:
        ingest(
            session,
            source,
            Enumeration(
                jobs=[posting(raw={"browser_token": canary, "candidate": canary})], complete=True
            ),
        )
        session.commit()
        observation = session.scalar(select(Observation))
        job_id = observation.job_id
        assert observation.data["raw"]["browser_token"] == canary
    for path in ("/api/v1/jobs", f"/api/v1/jobs/{job_id}"):
        response = client.get(path)
        assert response.status_code == 200
        assert canary not in response.text
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-content-type-options"] == "nosniff"
        item = response.json() if path.endswith(str(job_id)) else response.json()["items"][0]
        assert "raw" not in item
        provenance = item["sources"][0]
        assert set(provenance) == {
            "source_id",
            "source_url",
            "application_url",
            "status",
            "last_checked_at",
        }
        assert provenance["source_url"] == posting().source_url
    with database() as session:
        assert session.scalar(select(Observation)).data["raw"]["browser_token"] == canary


def test_worker_retires_abandoned_run_and_publishes_fresh_data(database, source, monkeypatch):
    from vindex.db import now

    with database() as session:
        abandoned = Run(
            source_id=source.id,
            started_at=now() - timedelta(seconds=worker.SOURCE_LEASE_SECONDS + 1),
        )
        session.add(abandoned)
        session.commit()
        abandoned_id = abandoned.id

    monkeypatch.setattr(worker, "Session", database)
    redis = Mock()
    redis.lock.return_value = nullcontext()
    monkeypatch.setattr(worker.Redis, "from_url", lambda url: redis)

    async def discover():
        return Enumeration(jobs=[posting()], complete=True)

    monkeypatch.setattr(worker, "create_connector", lambda *args: Mock(discover=discover))
    run_id = asyncio.run(worker.refresh(source.id))
    with database() as session:
        abandoned = session.get(Run, abandoned_id)
        assert abandoned.status == "failed" and abandoned.finished_at is not None
        assert session.get(Run, run_id).status == "success"


def test_worker_preserves_long_upstream_retry_after(database, source, monkeypatch):
    from vindex.connectors.http import PublicHTTP
    from vindex.db import Source, now
    from vindex.ingest import aware

    monkeypatch.setattr(worker, "Session", database)
    redis = Mock()
    redis.lock.return_value = nullcontext()
    monkeypatch.setattr(worker.Redis, "from_url", lambda url: redis)
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(429, headers={"Retry-After": "7200"})

    async def discover():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            await PublicHTTP(client, {"example.com"}).read("https://example.com/jobs")

    monkeypatch.setattr(worker, "create_connector", lambda *args: Mock(discover=discover))
    before = now()
    run_id = asyncio.run(worker.refresh(source.id))

    with database() as session:
        assert session.get(Run, run_id).status == "failed"
        assert aware(session.get(Source, source.id).next_check) >= before + timedelta(hours=2)
    assert len(requests) == 1


@pytest.mark.parametrize(("status", "minutes"), [(502, 2), (429, 2), (403, 30)])
def test_refresh_retries_transient_responses_sooner(database, source, monkeypatch, status, minutes):
    from vindex.db import Source

    async def discover():
        request = httpx.Request("GET", "https://example.com/jobs")
        httpx.Response(status, request=request).raise_for_status()

    monkeypatch.setattr(worker, "Session", database)
    redis = Mock()
    redis.lock.return_value = nullcontext()
    monkeypatch.setattr(worker.Redis, "from_url", lambda url: redis)
    monkeypatch.setattr(worker, "create_connector", lambda *args: Mock(discover=discover))

    run_id = asyncio.run(worker.refresh(source.id))
    with database() as session:
        run = session.get(Run, run_id)
        assert run.status == "failed"
        assert session.get(Source, source.id).next_check - run.finished_at == timedelta(
            minutes=minutes
        )

import asyncio
import hashlib
import hmac
import time
from contextlib import nullcontext
from datetime import timedelta
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from starlette.requests import Request
from test_lifecycle import posting
from vindex import api, operations, worker
from vindex.accounts import security
from vindex.accounts.models import Account, AccountSession
from vindex.client_ip import client_ip
from vindex.db import Observation, Run, now
from vindex.ingest import ingest
from vindex.retention import expire_auth_artifacts, retire_abandoned_runs
from vindex.schemas import Enumeration


def request(headers):
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/auth/login",
            "headers": [(k.encode(), v.encode()) for k, v in headers.items()],
            "scheme": "https",
            "server": ("example.test", 443),
            "client": ("192.0.2.1", 1),
            "query_string": b"",
        }
    )


def test_proxy_ip_requires_fresh_signature_and_rejects_forwarded_header_spoofing(monkeypatch):
    secret = "a" * 40
    monkeypatch.setenv("PROXY_SHARED_SECRET", secret)
    stamp = str(int(time.time()))
    headers = {
        "x-rolewisp-client-ip": "198.51.100.2",
        "x-rolewisp-proxy-time": stamp,
        "x-forwarded-for": "203.0.113.1",
    }
    assert client_ip(request(headers)) == "192.0.2.1"
    message = f"{stamp}\nPOST\n/api/v1/auth/login\n198.51.100.2"
    headers["x-rolewisp-proxy-signature"] = hmac.new(
        secret.encode(), message.encode(), hashlib.sha256
    ).hexdigest()
    assert client_ip(request(headers)) == "198.51.100.2"
    headers["x-rolewisp-client-ip"] = "203.0.113.2"
    assert client_ip(request(headers)) == "192.0.2.1"
    headers["x-rolewisp-proxy-time"] = str(int(stamp) - 120)
    assert client_ip(request(headers)) == "192.0.2.1"
    headers["x-rolewisp-proxy-signature"] = "not-ascii-\u00e9"
    assert client_ip(request(headers)) == "192.0.2.1"


def test_operator_health_separates_initial_indexing_failure_and_staleness(database, source):
    with database() as session:
        session.add(
            Run(source_id=source.id, status="success", finished_at=now() - timedelta(days=1))
        )
        session.add(Run(source_id=source.id, status="failed", error="ValueError: private detail"))
        stored = session.get(type(source), source.id)
        stored.failures = 1
        session.commit()
        report = operations.source_health(session)
    assert report["counts"]["initial_index_complete"] == 1
    assert report["counts"]["stale"] == 1 and report["counts"]["failing"] == 1
    assert "private detail" not in str(report)
    assert report["sources"][0]["failure_kind"] == "ValueError"


def test_security_reports_keep_classifications_only_and_have_bounded_bodies(monkeypatch):
    redis = Mock()
    monkeypatch.setattr(api, "redis_client", lambda: redis)
    monkeypatch.setattr(api, "rate_limit", lambda *args: None)
    client = TestClient(api.app)
    result = client.post(
        "/api/v1/security/csp-report",
        json={
            "csp-report": {
                "effective-directive": "script-src-elem",
                "disposition": "enforce",
                "document-uri": "https://example.org/?private=CANARY",
                "script-sample": "SECRET_CANARY",
            }
        },
    )
    assert result.status_code == 204
    assert "CANARY" not in str(redis.mock_calls)
    assert "vindex:csp:script-src-elem:enforce" in str(redis.mock_calls)
    assert client.post("/api/v1/security/csp-report", content=b"x" * 17000).status_code == 413
    assert client.get("/api/v1/operations").status_code in (401, 503)


def test_cancellation_records_failure_without_closures(database, source, monkeypatch):
    with database() as session:
        ingest(session, source, Enumeration(jobs=[posting()], complete=True))
        session.commit()
    redis = Mock()
    redis.lock.return_value = nullcontext()
    monkeypatch.setattr(worker, "Session", database)
    monkeypatch.setattr(worker.Redis, "from_url", lambda *args, **kwargs: redis)

    async def interrupted():
        raise asyncio.CancelledError()

    monkeypatch.setattr(worker, "create_connector", lambda *args: Mock(discover=interrupted))
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(worker.refresh(source.id))
    with database() as session:
        obs = session.scalar(select(Observation))
        assert obs.status == "open" and obs.missing_count == 0
        run = session.scalar(select(Run))
        assert run.status == "failed" and "stopped" in run.error


def test_expiry_removes_only_expired_auth_artifacts(database):
    checked = now()
    with database() as session:
        account = Account(
            email="expiry@example.org",
            password_hash="synthetic",
            email_code_hash="expired",
            email_code_expires_at=checked - timedelta(seconds=1),
            password_reset_hash="valid",
            password_reset_expires_at=checked + timedelta(minutes=1),
        )
        session.add(account)
        session.flush()
        session.add_all(
            [
                AccountSession(token_hash="old", account_id=account.id, expires_at=checked),
                AccountSession(
                    token_hash="valid",
                    account_id=account.id,
                    expires_at=checked + timedelta(days=1),
                ),
            ]
        )
        session.commit()
        expire_auth_artifacts(session, checked)
        session.commit()
        assert session.get(AccountSession, "old") is None
        assert session.get(AccountSession, "valid") is not None
        session.refresh(account)
        assert account.email_code_hash is None and account.password_reset_hash == "valid"


def test_logout_clears_browser_storage_alongside_session_cookie():
    from starlette.responses import Response

    response = Response()
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv("PUBLIC_WEB_ORIGIN", "https://example.org")
        security.clear_cookie(response)
    assert response.headers["clear-site-data"] == '"cookies", "storage", "cache"'


def test_unexpected_private_failures_are_no_store_and_do_not_log_payloads(monkeypatch, caplog):
    from vindex.accounts import api as account_api

    def failed():
        raise RuntimeError("PRIVATE_EXCEPTION_PARAMETER_CANARY")

    monkeypatch.setattr(account_api, "Session", failed)
    response = TestClient(api.app).get("/api/v1/me")
    assert response.status_code == 500
    assert response.headers["cache-control"] == "no-store"
    assert "CANARY" not in response.text and "CANARY" not in caplog.text


def test_abandoned_run_cleanup_preserves_active_runs_and_job_lifecycle(database, source):
    checked = now()
    with database() as session:
        ingest(
            session,
            source,
            Enumeration(jobs=[posting()], complete=True),
            checked - timedelta(hours=2),
        )
        old = Run(source_id=source.id, started_at=checked - timedelta(hours=2))
        active = Run(source_id=source.id, started_at=checked - timedelta(minutes=10))
        session.add_all([old, active])
        session.commit()
        assert operations.source_health(session, checked)["sources"][0]["abandoned_run"]
        retire_abandoned_runs(session, checked)
        session.commit()
        session.refresh(old)
        session.refresh(active)
        assert old.status == "failed" and active.status == "running"
        observation = session.scalar(select(Observation))
        assert observation.status == "open" and observation.missing_count == 0

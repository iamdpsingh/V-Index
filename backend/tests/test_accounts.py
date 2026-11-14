from datetime import timedelta
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy import func, select
from vindex import api
from vindex.accounts import api as account_api
from vindex.accounts import security
from vindex.accounts.models import Account, AccountSession, Profile
from vindex.db import now

ORIGIN = "https://app.example.test"
PASSWORD = "A deliberate test passphrase 123!"


@pytest.fixture
def account_client(database, monkeypatch):
    monkeypatch.setattr(account_api, "Session", database)
    monkeypatch.setenv("PUBLIC_WEB_ORIGIN", ORIGIN)
    monkeypatch.setenv("ACCOUNT_REGISTRATION_ENABLED", "true")
    redis = Mock()
    redis.eval.return_value = 1
    monkeypatch.setattr(security, "redis_client", lambda: redis)
    return TestClient(api.app, base_url=ORIGIN, headers={"Origin": ORIGIN})


def register(client, email="first@example.com"):
    response = client.post("/api/v1/auth/register", json={"email": email, "password": PASSWORD})
    assert response.status_code == 201, response.text
    return response


def test_password_hash_session_cookie_and_profile_persistence(account_client, database):
    response = register(account_client)
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=lax" in cookie
    assert "__Host-vindex_session" in cookie
    with database() as session:
        account = session.scalar(select(Account))
        assert account.password_hash.startswith("$argon2id$") and account.password_hash != PASSWORD
        saved = session.scalar(select(AccountSession))
        assert saved.token_hash != account_client.cookies.get("__Host-vindex_session")
    assert account_client.get("/api/v1/me").json()["email"] == "first@example.com"
    saved = account_client.put(
        "/api/v1/me/profile",
        json={
            "full_name": "Example Person",
            "skills": ["Python", "SQL"],
            "desired_titles": ["Backend Engineer"],
        },
    )
    assert saved.status_code == 200
    assert saved.headers["cache-control"] == "no-store"
    assert account_client.get("/api/v1/me/profile").json()["skills"] == ["Python", "SQL"]
    assert "password_hash" not in response.text


def test_origin_guard_unverified_identity_and_generic_login_errors(account_client):
    denied = account_client.post(
        "/api/v1/auth/register",
        headers={"Origin": "https://other.test"},
        json={"email": "bad@example.com", "password": PASSWORD},
    )
    assert denied.status_code == 403
    assert register(account_client).json()["email_verified"] is False
    account_client.post("/api/v1/auth/logout")
    a = account_client.post(
        "/api/v1/auth/login",
        json={"email": "first@example.com", "password": "Incorrect password 123"},
    )
    b = account_client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@example.com", "password": "Incorrect password 123"},
    )
    assert a.status_code == b.status_code == 401 and a.json() == b.json()
    good = account_client.post(
        "/api/v1/auth/login", json={"email": "FIRST@example.com", "password": PASSWORD}
    )
    assert good.status_code == 200


def test_session_rotation_logout_and_expiry(account_client, database):
    register(account_client)
    original = account_client.cookies.get("__Host-vindex_session")
    assert (
        account_client.post(
            "/api/v1/auth/login", json={"email": "first@example.com", "password": PASSWORD}
        ).status_code
        == 200
    )
    assert account_client.cookies.get("__Host-vindex_session") != original
    with database() as session:
        assert session.get(AccountSession, security.token_digest(original)) is None
        current = session.scalar(select(AccountSession))
        current.expires_at = now() - timedelta(seconds=1)
        session.commit()
    assert account_client.get("/api/v1/me").status_code == 401
    assert account_client.post("/api/v1/auth/logout").status_code == 204
    assert account_client.get("/api/v1/me/profile").status_code == 401


def test_profiles_are_private_and_account_deletion_cascades(account_client, database):
    first = register(account_client).json()["id"]
    account_client.put("/api/v1/me/profile", json={"bio": "Private first profile"})
    account_client.post("/api/v1/auth/logout")
    register(account_client, "second@example.com")
    assert account_client.get("/api/v1/me/profile").json()["bio"] == ""
    assert account_client.get(f"/api/v1/users/{first}/profile").status_code == 404
    rejected = account_client.request("DELETE", "/api/v1/me", json={"password": "wrong"})
    assert rejected.status_code == 401
    deleted = account_client.request("DELETE", "/api/v1/me", json={"password": PASSWORD})
    assert deleted.status_code == 204
    with database() as session:
        assert session.scalar(select(func.count()).select_from(Account)) == 1
        assert session.scalar(select(func.count()).select_from(Profile)) == 1


def test_password_change_revokes_other_sessions(account_client, database):
    register(account_client)
    with database() as session:
        user = session.scalar(select(Account))
        session.add(
            AccountSession(
                token_hash="other-session", account_id=user.id, expires_at=now() + timedelta(days=1)
            )
        )
        session.commit()
    changed = account_client.post(
        "/api/v1/me/password",
        json={"password": PASSWORD, "new_password": "An entirely different password 456!"},
    )
    assert changed.status_code == 204
    assert account_client.get("/api/v1/me").status_code == 200
    with database() as session:
        assert session.get(AccountSession, "other-session") is None
        assert session.scalar(select(func.count()).select_from(AccountSession)) == 1


def test_private_body_and_validation_limits_do_not_echo_passwords(account_client):
    short = "tiny-secret"
    invalid = account_client.post(
        "/api/v1/auth/register", json={"email": "first@example.com", "password": short}
    )
    assert invalid.status_code == 422 and short not in invalid.text
    assert (
        account_client.post(
            "/api/v1/auth/login", content=b"x" * 65537, headers={"Content-Type": "application/json"}
        ).status_code
        == 413
    )
    assert account_client.get("/api/v1/me").headers["cache-control"] == "no-store"


def test_registration_origin_and_rate_fail_closed(account_client, monkeypatch):
    monkeypatch.delenv("PUBLIC_WEB_ORIGIN")
    assert account_client.get("/api/v1/me").status_code == 503
    monkeypatch.setenv("PUBLIC_WEB_ORIGIN", "http://public.example.com")
    assert account_client.get("/api/v1/me").status_code == 503
    monkeypatch.setenv("PUBLIC_WEB_ORIGIN", ORIGIN)
    denied = Mock()
    denied.eval.return_value = 0
    monkeypatch.setattr(security, "redis_client", lambda: denied)
    assert (
        account_client.post(
            "/api/v1/auth/register", json={"email": "first@example.com", "password": PASSWORD}
        ).status_code
        == 429
    )
    denied.eval.side_effect = RedisConnectionError()
    assert (
        account_client.post(
            "/api/v1/auth/register", json={"email": "first@example.com", "password": PASSWORD}
        ).status_code
        == 503
    )


def test_private_rows_cannot_outlive_a_missing_owner(database):
    from sqlalchemy.exc import IntegrityError

    with database() as session:
        session.add(Profile(account_id="missing-owner", data={"bio": "A private test value"}))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_application_sqlite_connections_enable_foreign_keys():
    from sqlalchemy import text
    from vindex.db import engine

    if engine.dialect.name == "sqlite":
        with engine.connect() as connection:
            assert connection.scalar(text("PRAGMA foreign_keys")) == 1


def test_email_verification_code_is_required_and_single_use(account_client, database, monkeypatch):
    from vindex.accounts import email_verification

    codes = []
    monkeypatch.setattr(email_verification, "Session", database)
    monkeypatch.setattr(email_verification, "deliver", lambda _, code: codes.append(code))
    register(account_client)
    endpoint = "/api/v1/me/email/verification"
    assert account_client.post(endpoint).status_code == 204
    wrong = "00000000" if codes[0] != "00000000" else "00000001"
    assert account_client.post(endpoint + "/confirm", json={"code": wrong}).status_code == 422
    assert account_client.post(endpoint + "/confirm", json={"code": codes[0]}).status_code == 204
    assert account_client.get("/api/v1/me").json()["email_verified"] is True
    assert account_client.post(endpoint + "/confirm", json={"code": codes[0]}).status_code == 422

import os
import uuid
from unittest.mock import Mock

import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from test_accounts import ORIGIN, PASSWORD, register
from vindex import api
from vindex.accounts import api as account_api
from vindex.accounts import recommendations, resume_api, security
from vindex.accounts.models import Resume

REAL_REDIS_CLIENT = security.redis_client

TEXT = b"Example Candidate\nProfessional skills: Python, PostgreSQL, Airflow and SQL.\nBuild reliable data pipelines."


@pytest.fixture
def private_client(database, monkeypatch):
    for module in (account_api, recommendations, resume_api):
        monkeypatch.setattr(module, "Session", database)
    monkeypatch.setenv("PUBLIC_WEB_ORIGIN", ORIGIN)
    monkeypatch.setenv("ACCOUNT_REGISTRATION_ENABLED", "true")
    monkeypatch.setenv("RESUME_ENCRYPTION_KEY", Fernet.generate_key().decode())
    redis = Mock()
    redis.eval.return_value = 1
    monkeypatch.setattr(security, "redis_client", lambda: redis)
    return TestClient(
        api.app,
        base_url=ORIGIN,
        headers={"Origin": ORIGIN},
        client=("isolated-" + uuid.uuid4().hex, 50000),
    )


def upload(client, data=TEXT, name="resume.txt"):
    return client.put(
        "/api/v1/me/resume",
        content=data,
        headers={"X-Filename": name, "Content-Type": "application/octet-stream"},
    )


def test_private_resume_encryption_download_replace_and_delete(private_client, database):
    register(private_client)
    response = upload(private_client)
    assert response.status_code == 200, response.text
    assert set(response.json()) == {"filename", "size_bytes", "media_type", "updated_at"}
    assert private_client.get("/api/v1/me/profile").json()["full_name"] == ""
    assert private_client.get("/api/v1/me/recommendations").json()["needs_preferences"]
    assert response.headers["cache-control"] == "no-store"
    with database() as session:
        saved = session.scalar(select(Resume))
        assert TEXT not in saved.file_ciphertext
    download = private_client.get("/api/v1/me/resume/download")
    assert download.content == TEXT and download.headers["cache-control"] == "no-store"
    assert "attachment" in download.headers["content-disposition"]
    assert (
        private_client.put(
            "/api/v1/me/resume", content=b"changed", headers={"X-Filename": "../../bad.pdf"}
        ).status_code
        == 422
    )
    assert private_client.get("/api/v1/me/resume/download").content == TEXT
    replacement = b"A professional resume with TypeScript and React experience."
    assert upload(private_client, replacement).status_code == 200
    with database() as session:
        assert session.scalar(select(func.count()).select_from(Resume)) == 1
    assert private_client.delete("/api/v1/me/resume").status_code == 204
    assert private_client.get("/api/v1/me/resume").status_code == 404


def test_resume_isolation_key_requirement_and_account_delete(private_client, database, monkeypatch):
    register(private_client)
    assert upload(private_client).status_code == 200
    first_token = private_client.cookies.get("__Host-vindex_session")
    private_client.post("/api/v1/auth/logout")
    register(private_client, "second@example.com")
    assert private_client.get("/api/v1/me/resume/download").status_code == 404
    assert private_client.get("/api/v1/me/resume").status_code == 404
    assert upload(private_client).status_code == 200
    monkeypatch.delenv("RESUME_ENCRYPTION_KEY")
    assert upload(private_client).status_code == 503
    private_client.request("DELETE", "/api/v1/me", json={"password": PASSWORD})
    with database() as session:
        assert session.scalar(select(func.count()).select_from(Resume)) == 1
    assert first_token


def test_corrupt_upload_preserves_previous_private_resume(private_client):
    register(private_client)
    assert upload(private_client).status_code == 200
    assert upload(private_client, b"%PDF-not a valid document", "resume.pdf").status_code == 422
    assert private_client.get("/api/v1/me/resume/download").content == TEXT
    assert upload(private_client, b"x" * (5 * 1024 * 1024 + 1)).status_code == 413
    assert upload(private_client, TEXT, "bad%0D%0Aheader.txt").status_code == 422
    assert upload(private_client, TEXT, "unsupported.exe").status_code == 415


def test_encryption_key_rotation_requires_original_key(private_client, monkeypatch):
    register(private_client)
    assert upload(private_client).status_code == 200
    monkeypatch.setenv("RESUME_ENCRYPTION_KEY", Fernet.generate_key().decode())
    response = private_client.get("/api/v1/me/resume/download")
    assert response.status_code == 503 and TEXT.decode() not in response.text
    assert private_client.delete("/api/v1/me/resume").status_code == 204


@pytest.mark.skipif(
    not os.getenv("TEST_REDIS_URL"),
    reason="Set TEST_REDIS_URL for real account/resume service checks",
)
def test_real_redis_rate_budget_and_private_resume_storage(private_client, monkeypatch):
    monkeypatch.setenv("REDIS_URL", os.environ["TEST_REDIS_URL"])
    monkeypatch.setattr(security, "redis_client", REAL_REDIS_CLIENT)
    register(private_client, f"service-{uuid.uuid4().hex}@example.com")
    assert upload(private_client).status_code == 200
    assert private_client.get("/api/v1/me/resume/download").content == TEXT
    bucket = "integration-check-" + uuid.uuid4().hex
    security.rate_limit(bucket, 2)
    security.rate_limit(bucket, 2)
    with pytest.raises(HTTPException) as error:
        security.rate_limit(bucket, 2)
    assert error.value.status_code == 429


def test_openapi_declares_raw_upload_and_filename_contract():
    operation = api.app.openapi()["paths"]["/api/v1/me/resume"]["put"]
    assert (
        operation["requestBody"]["content"]["application/octet-stream"]["schema"]["format"]
        == "binary"
    )
    assert any(p["name"] == "x-filename" and p["required"] for p in operation["parameters"])
    download = api.app.openapi()["paths"]["/api/v1/me/resume/download"]["get"]
    assert "application/octet-stream" in download["responses"]["200"]["content"]


def test_chunked_private_upload_and_json_limits(private_client):
    register(private_client)
    too_large = private_client.put(
        "/api/v1/me/resume",
        content=iter([b"x" * (5 * 1024 * 1024), b"x"]),
        headers={"X-Filename": "resume.txt"},
    )
    assert too_large.status_code == 413
    json_too_large = private_client.post(
        "/api/v1/auth/login",
        content=iter([b"x" * 65536, b"x"]),
        headers={"Content-Type": "application/json"},
    )
    assert json_too_large.status_code == 413


def test_pdf_attachment_does_not_need_selectable_text(private_client):
    register(private_client)
    document = b"%PDF-1.4\n% attachment without a text layer\n%%EOF\n"
    response = upload(private_client, document, "resume.pdf")
    assert response.status_code == 200
    assert private_client.get("/api/v1/me/resume/download").content == document

import io
import os
import uuid
import zipfile
from contextlib import nullcontext
from unittest.mock import Mock

import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from sqlalchemy import func, select
from test_accounts import ORIGIN, PASSWORD, register
from vindex import api
from vindex.accounts import api as account_api
from vindex.accounts import resume_api, security
from vindex.accounts.matching import detected_skills
from vindex.accounts.models import Resume
from vindex.accounts.resumes import extract_text

REAL_REDIS_CLIENT = security.redis_client
REAL_PARSER_SLOT = security.parser_slot

TEXT = b"Example Candidate\nProfessional skills: Python, PostgreSQL, Airflow and SQL.\nBuild reliable data pipelines."


@pytest.fixture
def private_client(database, monkeypatch):
    for module in (account_api, resume_api):
        monkeypatch.setattr(module, "Session", database)
    monkeypatch.setenv("PUBLIC_WEB_ORIGIN", ORIGIN)
    monkeypatch.setenv("ACCOUNT_REGISTRATION_ENABLED", "true")
    monkeypatch.setenv("RESUME_ENCRYPTION_KEY", Fernet.generate_key().decode())
    redis = Mock()
    redis.eval.return_value = 1
    monkeypatch.setattr(security, "redis_client", lambda: redis)
    monkeypatch.setattr(resume_api, "parser_slot", nullcontext)
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
    assert "Python" in response.json()["detected_skills"]
    assert response.json()["suggestions"]["full_name"] == "Example Candidate"
    assert "text" not in response.json()
    assert response.headers["cache-control"] == "no-store"
    with database() as session:
        saved = session.scalar(select(Resume))
        assert TEXT not in saved.file_ciphertext and b"Python" not in saved.text_ciphertext
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


def test_real_pdf_and_docx_subprocess_text_extraction():
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )
    stream = DecodedStreamObject()
    stream.set_data(
        b"BT /F1 12 Tf 20 700 Td (Python SQL professional resume skills and data pipelines) Tj ET"
    )
    page[NameObject("/Contents")] = writer._add_object(stream)
    out = io.BytesIO()
    writer.write(out)
    assert "Python SQL" in extract_text(out.getvalue(), "pdf")
    doc = io.BytesIO()
    with zipfile.ZipFile(doc, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr(
            "word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Python SQL professional resume with experience</w:t></w:r></w:p></w:body></w:document>',
        )
    assert "Python SQL" in extract_text(doc.getvalue(), "docx")
    writer.encrypt("private-password")
    encrypted = io.BytesIO()
    writer.write(encrypted)
    with pytest.raises(HTTPException):
        extract_text(encrypted.getvalue(), "pdf")
    with pytest.raises(HTTPException):
        extract_text(b"not a zip", "docx")


def test_matching_does_not_treat_contact_urls_or_go_verb_as_skills():
    skills = detected_skills(
        "Go to market. Contact python@example.com or https://company.test/React for details. Golang developer."
    )
    assert skills == ["Go"]


@pytest.mark.skipif(
    not os.getenv("TEST_REDIS_URL"),
    reason="Set TEST_REDIS_URL for real account/resume service checks",
)
def test_real_redis_rate_budget_and_resume_parser_lease(private_client, monkeypatch):
    monkeypatch.setenv("REDIS_URL", os.environ["TEST_REDIS_URL"])
    monkeypatch.setattr(security, "redis_client", REAL_REDIS_CLIENT)
    monkeypatch.setattr(resume_api, "parser_slot", REAL_PARSER_SLOT)
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

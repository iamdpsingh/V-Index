"""Ephemeral CI account checks through the real web proxy. Never prints private data."""

import http.cookiejar
import json
import secrets
import urllib.error
import urllib.request

ORIGIN = "http://localhost:3000"


def main():
    client = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
    )

    def call(path, method="GET", body=None, data=None, headers=None):
        request_headers = {"Origin": ORIGIN, **(headers or {})}
        if body is not None:
            data = json.dumps(body).encode()
            request_headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            ORIGIN + "/api/v1" + path, data=data, method=method, headers=request_headers
        )
        with client.open(request, timeout=20) as response:
            payload = response.read()
            assert response.headers.get("Cache-Control") == "no-store"
            return (
                json.loads(payload)
                if payload and response.headers.get_content_type() == "application/json"
                else payload
            )

    password = secrets.token_urlsafe(32)
    suffix = secrets.token_hex(6)
    account = call(
        "/auth/register",
        "POST",
        {"email": f"ci-private-{suffix}@example.com", "password": password},
    )
    assert not account["email_verified"]
    call("/me/role", "PUT", {"role": "candidate"})
    assert call("/me")["role"] == "candidate"
    call(
        "/me/profile",
        "PUT",
        {
            "skills": ["Python", "SQL"],
            "desired_titles": ["Data Engineer"],
            "education": [{"qualification": "bachelors", "details": "CI synthetic qualification"}],
        },
    )
    profile = call("/me/profile")
    assert profile["skills"] == ["Python", "SQL"]
    assert profile["education"][0]["qualification"] == "bachelors"
    resume = (
        b"Controlled CI resume fixture: professional Python SQL and data engineering experience."
    )
    saved = call(
        "/me/resume",
        "PUT",
        data=resume,
        headers={"X-Filename": "ci-resume.txt", "Content-Type": "application/octet-stream"},
    )
    assert saved["filename"] == "ci-resume.txt"
    assert set(saved) == {"filename", "media_type", "size_bytes", "updated_at"}
    assert call("/me/resume/download") == resume
    result = call("/me/recommendations")
    assert result["items"] == [] and not result["needs_preferences"]
    call("/me", "DELETE", {"password": password})
    try:
        call("/me")
    except urllib.error.HTTPError as error:
        assert error.code == 401
    else:
        raise AssertionError("Deleted account remained authenticated")
    call(
        "/auth/register",
        "POST",
        {
            "email": f"ci-employer-{suffix}@example.com",
            "password": password,
        },
    )
    call("/me/role", "PUT", {"role": "employer"})
    posting = call(
        "/me/postings",
        "POST",
        {
            "title": "CI synthetic role",
            "company": "CI synthetic company",
            "location": "Remote",
            "description": "Controlled CI posting fixture",
            "application_url": "https://example.com/rolewisp-ci",
        },
    )
    assert posting["status"] == "draft"
    assert call("/me/postings")[0]["id"] == posting["id"]
    try:
        call(f"/me/postings/{posting['id']}/publish", "POST")
    except urllib.error.HTTPError as error:
        assert error.code == 403
    else:
        raise AssertionError("Unverified employer published a posting")
    assert call(f"/me/postings/{posting['id']}/close", "POST")["status"] == "closed"
    call("/me", "DELETE", {"password": password})
    print("Private stack checks passed through the web proxy, including employer draft permissions")


if __name__ == "__main__":
    main()

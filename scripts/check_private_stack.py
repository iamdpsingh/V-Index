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
    account = call(
        "/auth/register", "POST", {"email": "ci-private-check@example.com", "password": password}
    )
    assert not account["email_verified"]
    call("/me/profile", "PUT", {"skills": ["Python", "SQL"], "desired_titles": ["Data Engineer"]})
    assert call("/me/profile")["skills"] == ["Python", "SQL"]
    resume = (
        b"Controlled CI resume fixture: professional Python SQL and data engineering experience."
    )
    saved = call(
        "/me/resume",
        "PUT",
        data=resume,
        headers={"X-Filename": "ci-resume.txt", "Content-Type": "application/octet-stream"},
    )
    assert "Python" in saved["detected_skills"]
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
    print(
        "Private stack checks passed: account, profile, resume round-trip, recommendations and account deletion"
    )


if __name__ == "__main__":
    main()

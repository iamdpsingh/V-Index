from datetime import UTC, datetime, timedelta

import httpx2
import pytest

from scripts.cloud_backup import enforce_ttl, verify_ttl


def test_retention_headers_are_limited_to_the_fixed_blob_upload_api():
    upload = httpx2.Request("PUT", "https://vercel.com/api/blob?pathname=backup")
    enforce_ttl(upload)
    assert upload.headers["x-ttl-days"] == "7"
    assert upload.headers["x-api-version"] == "13"
    unrelated = httpx2.Request("PUT", "https://example.org/upload")
    enforce_ttl(unrelated)
    assert "x-ttl-days" not in unrelated.headers


@pytest.mark.parametrize("days", [None, 90])
def test_provider_must_confirm_the_actual_retention_period(days):
    payload = (
        {}
        if days is None
        else {"expiresAt": (datetime.now(UTC) + timedelta(days=days)).isoformat()}
    )
    response = httpx2.Response(
        200, json=payload, request=httpx2.Request("PUT", "https://vercel.com/api/blob")
    )
    with pytest.raises(ValueError):
        verify_ttl(response)


def test_valid_provider_expiry_is_accepted():
    response = httpx2.Response(
        200,
        json={"expiresAt": (datetime.now(UTC) + timedelta(days=7)).isoformat()},
        request=httpx2.Request("PUT", "https://vercel.com/api/blob"),
    )
    verify_ttl(response)

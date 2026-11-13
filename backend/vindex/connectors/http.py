"""Bounded public HTTP reads; hosts are supplied by validated provider constructors."""

import asyncio
import json
import math
import random
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Any, Literal
from urllib.parse import urlsplit

import httpx

MAX_RESPONSE_BYTES = 20_000_000


class UpstreamStatusError(ValueError):
    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__(f"Upstream HTTP {status_code}")


class RetryAfterError(UpstreamStatusError):
    def __init__(self, status_code: int, retry_at: datetime):
        super().__init__(status_code)
        self.retry_at = retry_at
        self.args = (f"Upstream HTTP {status_code}; Retry-After until {retry_at.isoformat()}",)


def retry_after_at(value: str, observed_at: datetime) -> datetime | None:
    try:
        seconds = float(value)
    except ValueError:
        try:
            target = parsedate_to_datetime(value)
            if target.tzinfo is None:
                target = target.replace(tzinfo=UTC)
            return max(target, observed_at)
        except (ValueError, TypeError, OverflowError):
            return None
    if not math.isfinite(seconds) or seconds < 0:
        return None
    try:
        return observed_at + timedelta(seconds=seconds)
    except OverflowError:
        return datetime.max.replace(tzinfo=UTC)


class PublicHTTP:
    def __init__(self, client: httpx.AsyncClient, hosts: set[str]):
        self.client, self.hosts = client, hosts

    async def read(
        self,
        url: str,
        *,
        method: Literal["GET", "POST"] = "GET",
        accept: str = "*/*",
        json_body: dict[str, Any] | None = None,
        form: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> bytes:
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.hostname not in self.hosts
            or parsed.username
            or parsed.password
            or parsed.port not in (None, 443)
        ):
            raise ValueError("Outbound URL rejected")
        if form is not None and (method != "POST" or json_body is not None):
            raise ValueError("Form data requires a form-only POST")
        allowed_headers = {"Authorization"}
        if parsed.hostname == "myjobs.adp.com" and parsed.path.startswith(
            "/public/staffing/v1/job-requisitions"
        ):
            allowed_headers = {"orgoid"}
        if (
            parsed.hostname
            and parsed.hostname.endswith(".careers.hibob.com")
            and parsed.path == "/api/job-ad"
        ):
            allowed_headers = {"companyidentifier"}
        if headers and set(headers) != allowed_headers:
            raise ValueError("Unsupported provider request header")
        for attempt in range(3):
            try:
                async with self.client.stream(
                    method,
                    url,
                    json=json_body,
                    data=form,
                    headers={"Accept": accept, **(headers or {})},
                    follow_redirects=False,
                ) as response:
                    if response.status_code == 429 or response.status_code >= 500:
                        response.raise_for_status()
                    if response.status_code != 200:
                        raise UpstreamStatusError(response.status_code)
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > MAX_RESPONSE_BYTES:
                            raise ValueError("Response exceeds 20 MB limit")
                    return bytes(body)
            except (httpx.TransportError, httpx.HTTPStatusError) as error:
                delay = 2**attempt + random.random()
                if isinstance(error, httpx.HTTPStatusError):
                    observed_at = datetime.now(UTC)
                    retry_at = retry_after_at(
                        error.response.headers.get("Retry-After", ""), observed_at
                    )
                    if retry_at is not None:
                        wait = (retry_at - observed_at).total_seconds()
                        if attempt == 2 or wait > 30:
                            raise RetryAfterError(error.response.status_code, retry_at) from error
                        delay = max(delay, wait)
                if attempt == 2:
                    raise
                await asyncio.sleep(min(30, delay))
        raise RuntimeError("Retry budget exhausted")

    async def json(
        self,
        url: str,
        *,
        method: Literal["GET", "POST"] = "GET",
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        return json.loads(
            await self.read(
                url, method=method, json_body=json_body, accept="application/json", headers=headers
            )
        )

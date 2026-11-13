"""Bounded public HTTP reads; hosts are supplied by validated provider constructors."""

import asyncio
import json
import random
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any, Literal
from urllib.parse import urlsplit

import httpx

MAX_RESPONSE_BYTES = 20_000_000


class UpstreamStatusError(ValueError):
    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__(f"Upstream HTTP {status_code}")


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
                if attempt == 2:
                    raise
                delay = 2**attempt + random.random()
                if isinstance(error, httpx.HTTPStatusError):
                    retry_after = error.response.headers.get("Retry-After")
                    if retry_after:
                        try:
                            wait = float(retry_after)
                        except ValueError:
                            try:
                                date = parsedate_to_datetime(retry_after)
                                wait = (date - datetime.now(UTC)).total_seconds()
                            except (ValueError, TypeError, OverflowError):
                                wait = 0
                        if wait > 30:
                            # Fail the run into durable cooldown rather than retrying too soon.
                            raise ValueError("Retry-After exceeds inline retry budget") from error
                        delay = max(delay, wait)
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

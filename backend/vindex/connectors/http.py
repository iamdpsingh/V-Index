"""Bounded public HTTP reads; hosts are supplied by validated provider constructors."""

import asyncio
import json
import random
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlsplit

import httpx

MAX_RESPONSE_BYTES = 20_000_000


class PublicHTTP:
    def __init__(self, client: httpx.AsyncClient, hosts: set[str]):
        self.client, self.hosts = client, hosts

    async def read(self, url: str) -> bytes:
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.hostname not in self.hosts
            or parsed.username
            or parsed.password
            or parsed.port not in (None, 443)
        ):
            raise ValueError("Outbound URL rejected")
        for attempt in range(3):
            try:
                async with self.client.stream("GET", url, follow_redirects=False) as response:
                    if response.status_code == 429 or response.status_code >= 500:
                        response.raise_for_status()
                    if response.status_code != 200:
                        raise ValueError(f"Upstream HTTP {response.status_code}")
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

    async def json(self, url: str) -> Any:
        return json.loads(await self.read(url))

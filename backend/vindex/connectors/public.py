"""Public APIs only. Submitted URLs are identifiers, never outbound fetch targets."""

import asyncio
import html
import random
import re
from typing import Any, Protocol
from urllib.parse import urlsplit

import httpx
from bs4 import BeautifulSoup
from vindex.schemas import Enumeration, JobInput

HOSTS = {
    "boards.greenhouse.io": "greenhouse",
    "job-boards.greenhouse.io": "greenhouse",
    "jobs.lever.co": "lever",
    "jobs.eu.lever.co": "lever-eu",
    "jobs.ashbyhq.com": "ashby",
}
API_HOSTS = {"boards-api.greenhouse.io", "api.lever.co", "api.eu.lever.co", "api.ashbyhq.com"}


def detect(url: str) -> tuple[str, str]:
    p = urlsplit(url)
    if p.scheme != "https" or p.username or p.password or p.port not in (None, 443):
        raise ValueError("Use an HTTPS career board URL without credentials or custom ports")
    provider = HOSTS.get(p.hostname or "")
    slug = p.path.strip("/").split("/")[0]
    if not provider or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", slug):
        raise ValueError("Supported hosted boards: Greenhouse, Lever and Ashby")
    return provider, slug


def text(value: str) -> str:
    return BeautifulSoup(html.unescape(value), "html.parser").get_text(" ", strip=True)


class Connector(Protocol):
    async def discover(self) -> Enumeration: ...
    async def fetch(self, cursor: int = 0) -> Any: ...
    def parse(self, payload: Any) -> list[JobInput]: ...


class PublicConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider not in set(HOSTS.values()) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", slug):
            raise ValueError("Invalid connector configuration")
        self.provider, self.slug, self.company, self.client = provider, slug, company, client

    async def fetch(self, cursor: int = 0) -> Any:
        if self.provider == "greenhouse":
            url = f"https://boards-api.greenhouse.io/v1/boards/{self.slug}/jobs?content=true"
        elif self.provider == "ashby":
            url = f"https://api.ashbyhq.com/posting-api/job-board/{self.slug}?includeCompensation=true"
        else:
            host = "api.eu.lever.co" if self.provider == "lever-eu" else "api.lever.co"
            url = f"https://{host}/v0/postings/{self.slug}?mode=json&skip={cursor}&limit=100"
        if urlsplit(url).hostname not in API_HOSTS:
            raise ValueError("Outbound host rejected")
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
                        if len(body) > 20_000_000:
                            raise ValueError("Response exceeds 20 MB limit")
                    import json

                    return json.loads(body)
            except (httpx.TransportError, httpx.HTTPStatusError):
                if attempt == 2:
                    raise
                await asyncio.sleep(min(30, 2**attempt + random.random()))
        raise RuntimeError("Retry budget exhausted")

    def parse(self, payload: Any) -> list[JobInput]:
        rows = payload if self.provider.startswith("lever") else payload["jobs"]
        if not isinstance(rows, list):
            raise ValueError("Expected jobs array")
        jobs = []
        for row in rows:
            if self.provider == "ashby":
                if row.get("isListed") is False:
                    continue
                url = row["jobUrl"]
                data = dict(
                    external_id=urlsplit(url).path.rstrip("/").split("/")[-1],
                    title=row["title"],
                    description=row.get("descriptionPlain") or text(row.get("descriptionHtml", "")),
                    location=row.get("location", ""),
                    source_url=url,
                    application_url=row["applyUrl"],
                    employment_type=row.get("employmentType"),
                    remote_status=row.get("workplaceType"),
                    salary=row.get("compensation"),
                    published_at=row.get("publishedAt"),
                )
            elif self.provider == "greenhouse":
                data = dict(
                    external_id=str(row["id"]),
                    title=row["title"],
                    description=text(row["content"]),
                    location=row["location"]["name"],
                    source_url=row["absolute_url"],
                    application_url=row["absolute_url"],
                    published_at=row.get("first_published"),
                )
            else:
                data = dict(
                    external_id=row["id"],
                    title=row["text"],
                    description=text(
                        row.get("description", "")
                        + " "
                        + " ".join(
                            item["text"] + " " + item["content"] for item in row.get("lists", [])
                        )
                        + " "
                        + row.get("additional", "")
                    ),
                    location=row.get("categories", {}).get("location", ""),
                    source_url=row["hostedUrl"],
                    application_url=row["applyUrl"],
                    employment_type=row.get("categories", {}).get("commitment"),
                    remote_status=row.get("workplaceType"),
                    salary=row.get("salaryRange"),
                )
            jobs.append(JobInput(**data, company=self.company, raw=row))
        return jobs

    async def discover(self) -> Enumeration:
        result: list[JobInput] = []
        seen: set[str] = set()
        for page in range(100):
            payload = await self.fetch(page * 100)
            jobs = self.parse(payload)
            for job in jobs:
                if job.external_id in seen:
                    raise ValueError(
                        "Duplicate identifier or repeated pagination; enumeration incomplete"
                    )
                seen.add(job.external_id)
            result.extend(jobs)
            if not self.provider.startswith("lever") or len(payload) < 100:
                if self.provider == "greenhouse" and payload.get("meta", {}).get("total") != len(
                    result
                ):
                    raise ValueError("Greenhouse total does not match enumeration")
                return Enumeration(jobs=result, complete=True)
            await asyncio.sleep(0.5)
        raise ValueError("Pagination limit exceeded")

"""Freshteam's public full career HTML list and JobPosting details, without account APIs."""

import asyncio
import html
import json
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit

import httpx
from bs4 import BeautifulSoup
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.connectors.teamtailor import TENANT
from vindex.schemas import Enumeration, JobInput

JOB_PATH = re.compile(r"/jobs/([A-Za-z0-9_-]{8,100})/[a-z0-9-]+")


class FreshteamConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider != "freshteam" or not re.fullmatch(TENANT, slug):
            raise ValueError("Invalid Freshteam tenant")
        self.origin = f"https://{slug}.freshteam.com"
        self.http = PublicHTTP(client, {f"{slug}.freshteam.com"})

    def listings(self, body: bytes) -> tuple[str, dict[str, dict]]:
        if b"</html>" not in body.lower():
            raise ValueError("Truncated Freshteam career page")
        soup = BeautifulSoup(body, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        if not title or not soup.select_one(".job-role-list"):
            raise ValueError("Missing Freshteam career-list template")
        if soup.select('a[rel="next"],.pagination,nav[aria-label="Pagination"],a[href*="page="]'):
            raise ValueError("Freshteam paginated templates unsupported")
        result = {}
        seen = set()
        for anchor in soup.select(".job-role-list a.heading[href]"):
            path = str(anchor["href"])
            matched = JOB_PATH.fullmatch(path)
            heading = anchor.select_one(".job-title")
            if (
                not matched
                or path in result
                or matched[1] in seen
                or heading is None
                or not heading.get_text(" ", strip=True)
            ):
                raise ValueError("Invalid or duplicate Freshteam listed job")
            remote = anchor.get("data-portal-remote-location")
            if remote not in ("true", "false"):
                raise ValueError("Unsupported Freshteam remote flag")
            result[path] = {
                "title": heading.get_text(" ", strip=True),
                "location": str(anchor.get("data-portal-location", "")),
                "remote": remote,
                "job_type_id": anchor.get("data-portal-job-type"),
            }
            seen.add(matched[1])
        if not 0 < len(result) <= 400:
            raise ValueError("Freshteam empty list or 400-detail limit")
        return title, result

    def parse(self, payload: Any) -> list[JobInput]:
        path, listing, body = payload
        matched = JOB_PATH.fullmatch(path)
        if not matched or b"</html>" not in body.lower():
            raise ValueError("Invalid Freshteam detail path/document")
        soup = BeautifulSoup(body, "html.parser")
        rows = [json.loads(x.get_text()) for x in soup.select('script[type="application/ld+json"]')]
        rows = [r for r in rows if isinstance(r, dict) and r.get("@type") == "JobPosting"]
        if len(rows) != 1:
            raise ValueError("Missing unique Freshteam JobPosting")
        row = rows[0]
        source = urlsplit(html.unescape(row["url"]))
        if (
            html.unescape(row["title"]).strip() != listing["title"]
            or source.scheme != "https"
            or source.netloc != urlsplit(self.origin).netloc
            or source.query
            or source.fragment
            or not re.fullmatch(rf"/jobs/{re.escape(matched[1])}/[^/]+", source.path)
            or row["remote"] != listing["remote"]
            or not soup.select_one(f'form[action="/jobs/{matched[1]}/applicants"]')
        ):
            raise ValueError("Freshteam title/ID/remote/native application mismatch")
        value = row["datePosted"]
        if value.endswith(" UTC"):
            published = datetime.strptime(value, "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=UTC)
        else:
            published = datetime.fromisoformat(value)
        description = text(html.unescape(row["description"]))
        return [
            JobInput(
                external_id=matched[1],
                title=html.unescape(row["title"]).strip(),
                company=row["hiringOrganization"]["name"],
                description=description,
                quality_flags=[] if description else ["description_missing"],
                location=listing["location"],
                source_url=self.origin + path,
                application_url=self.origin + path,
                salary=row.get("baseSalary"),
                employment_type=row.get("employmentType"),
                remote_status="Remote" if row["remote"] == "true" else None,
                published_at=published,
                raw={
                    "listing": listing,
                    "jobposting": row,
                    "application_entry": "native_application_form",
                },
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("Freshteam paginated template unsupported")
        return await self.http.read(self.origin + "/jobs")

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)

        async def read(url: str) -> bytes:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        board = self.origin + "/jobs"
        identity, rows = self.listings(await read(board))
        jobs = []
        for path, listing in rows.items():
            jobs.extend(self.parse((path, listing, await read(self.origin + path))))
        if self.listings(await read(board)) != (identity, rows):
            raise ValueError("Freshteam full roster changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

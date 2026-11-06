"""Public Teamtailor JSON Feed joined to its RSS workplace/location metadata."""

import asyncio
import re
from typing import Any
from uuid import UUID

import httpx
from defusedxml import ElementTree
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.schemas import Enumeration, JobInput

TENANT = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
NS = "{https://teamtailor.com/locations}"


class TeamtailorConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider != "teamtailor" or not re.fullmatch(TENANT, slug):
            raise ValueError("Invalid Teamtailor tenant")
        self.origin = f"https://{slug}.teamtailor.com"
        self.http = PublicHTTP(client, {f"{slug}.teamtailor.com"})
        self.company = company

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("Paginated Teamtailor feeds are not supported by this adapter yet")
        return await self.http.json(f"{self.origin}/jobs.json")

    def rows(self, payload: Any) -> list[dict[str, Any]]:
        if (
            not isinstance(payload, dict)
            or payload.get("version") != "https://jsonfeed.org/version/1.1"
            or payload.get("home_page_url") != f"{self.origin}/jobs"
            or payload.get("feed_url") != f"{self.origin}/jobs.json"
            or not isinstance(payload.get("items"), list)
        ):
            raise ValueError("Invalid Teamtailor feed identity or shape")
        if payload.get("next_url") or len(payload["items"]) >= 100:
            raise ValueError("Teamtailor feed requires pagination; snapshot incomplete")
        rows = payload["items"]
        ids = [str(UUID(row["id"])) for row in rows]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate Teamtailor identifiers")
        return rows

    def parse(self, payload: Any) -> list[JobInput]:
        feed, rss = payload
        rows = self.rows(feed)
        root = ElementTree.fromstring(rss, forbid_dtd=True)
        if root.tag != "rss" or root.findtext("channel/link") != f"{self.origin}/jobs":
            raise ValueError("Invalid Teamtailor RSS identity")
        metadata = {}
        for item in root.findall("channel/item"):
            key = item.findtext("guid")
            if not key or key in metadata:
                raise ValueError("Invalid or duplicate Teamtailor RSS identifier")
            metadata[key] = item
        if set(metadata) != {row["id"] for row in rows}:
            raise ValueError("Teamtailor JSON/RSS identifiers disagree; snapshot incomplete")
        jobs = []
        for row in rows:
            item = metadata[row["id"]]
            schema = row["_jobposting"]
            url = row["url"]
            if (
                not re.fullmatch(re.escape(self.origin) + r"/jobs/[0-9]+-[A-Za-z0-9_%~-]+", url)
                or item.findtext("link") != url
                or schema["@type"] != "JobPosting"
                or schema["title"] != row["title"]
            ):
                raise ValueError("Teamtailor job metadata or links disagree")
            description = text(row["content_html"])
            locations = []
            for location in item.findall(f"{NS}locations/{NS}location"):
                parts = [location.findtext(f"{NS}{key}") for key in ("name", "city", "country")]
                locations.append(", ".join(dict.fromkeys(part for part in parts if part)))
            employment = schema.get("employmentType")
            if isinstance(employment, list):
                employment = ", ".join(employment)
            jobs.append(
                JobInput(
                    external_id=row["id"],
                    title=row["title"],
                    company=schema.get("hiringOrganization", {}).get("name") or self.company,
                    description=description,
                    quality_flags=[] if description else ["description_missing"],
                    location="; ".join(locations),
                    source_url=url,
                    application_url=url,
                    employment_type=employment,
                    remote_status=item.findtext("remoteStatus") or schema.get("jobLocationType"),
                    salary=schema.get("baseSalary"),
                    published_at=row.get("date_published") or schema.get("datePosted"),
                    raw={
                        "feed_item": row,
                        "rss_item": ElementTree.tostring(item, encoding="unicode"),
                    },
                )
            )
        return jobs

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)
        for path in ("/jobs", "/jobs.json", "/jobs.rss"):
            policy.check(self.origin + path)
        await asyncio.sleep(policy.delay())
        feed = await self.fetch()
        self.rows(feed)
        await asyncio.sleep(policy.delay())
        rss = await self.http.read(f"{self.origin}/jobs.rss")
        jobs = self.parse((feed, rss))
        await asyncio.sleep(policy.delay())
        confirmation = self.rows(await self.fetch())
        if {row["id"] for row in confirmation} != {job.external_id for job in jobs}:
            raise ValueError("Teamtailor feed changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

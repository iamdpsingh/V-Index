"""Public Breezy hosted feed, with mandatory career-page details and reconciliation."""

import asyncio
import json
import re
from typing import Any
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup
from vindex.connectors.http import PublicHTTP
from vindex.connectors.robots import RobotsPolicy
from vindex.connectors.teamtailor import TENANT
from vindex.schemas import Enumeration, JobInput


class BreezyConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider != "breezy" or not re.fullmatch(TENANT, slug):
            raise ValueError("Invalid Breezy tenant")
        self.origin = f"https://{slug}.breezy.hr"
        self.http = PublicHTTP(client, {f"{slug}.breezy.hr"})
        self.company = company

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("Breezy hosted JSON is not paginated")
        return await self.http.json(f"{self.origin}/json")

    def rows(self, payload: Any) -> list[dict[str, Any]]:
        if not isinstance(payload, list) or len(payload) > 400:
            raise ValueError("Invalid Breezy feed or board exceeds 400-detail budget")
        ids = set()
        for row in payload:
            identifier = row["id"]
            friendly = row["friendly_id"]
            if (
                not isinstance(identifier, str)
                or not re.fullmatch(r"[a-f0-9]{12}", identifier)
                or not isinstance(friendly, str)
                or not re.fullmatch(re.escape(identifier) + r"-[A-Za-z0-9_-]+", friendly)
                or row["url"] != f"{self.origin}/p/{friendly}"
                or identifier in ids
            ):
                raise ValueError("Invalid or duplicate Breezy job identifier/link")
            ids.add(identifier)
        return payload

    def parse(self, payload: Any) -> list[JobInput]:
        row, body = payload
        self.rows([row])
        soup = BeautifulSoup(body, "html.parser")
        schemas = []
        for script in soup.select('script[type="application/ld+json"]'):
            schema = json.loads(script.get_text())
            if isinstance(schema, dict) and schema.get("@type") == "JobPosting":
                schemas.append(schema)
        if len(schemas) != 1:
            raise ValueError("Expected exactly one Breezy JobPosting detail")
        schema = schemas[0]
        # The source adds a GoogleJobs attribution query to its structured URL.
        if schema["url"].split("?", 1)[0] != row["url"]:
            raise ValueError("Breezy detail belongs to a different job")
        description_node = soup.select_one(".description")
        if description_node is None or "description" not in schema:
            raise ValueError("Breezy description schema missing")
        description = description_node.get_text(" ", strip=True)
        apply_url = row["url"] + "/apply"
        if not any(
            urljoin(self.origin, str(a.get("href", ""))) == apply_url
            for a in soup.select("a[href]")
        ):
            raise ValueError("Breezy application link missing")
        locations = row.get("locations") or [row["location"]]
        location_text = "; ".join(dict.fromkeys(loc.get("name", "") for loc in locations))
        workplace = []
        for loc in locations:
            label = (loc.get("remote_details") or {}).get("label")
            if label:
                workplace.append(label)
            elif type(loc.get("is_remote")) is bool:
                workplace.append("Remote" if loc["is_remote"] else "OnSite")
        salary = schema.get("baseSalary")
        if row.get("salary"):
            salary = {"source_text": row["salary"], **({"structured": salary} if salary else {})}
        return [
            JobInput(
                external_id=row["id"],
                title=row["name"],
                company=row.get("company", {}).get("name") or self.company,
                description=description,
                quality_flags=[] if description else ["description_missing"],
                location=location_text,
                source_url=row["url"],
                application_url=apply_url,
                employment_type=(row.get("type") or {}).get("name"),
                remote_status="; ".join(dict.fromkeys(workplace)) or None,
                salary=salary,
                published_at=row.get("published_date") or schema.get("datePosted"),
                raw={"listing": row, "jobposting": schema},
            )
        ]

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)
        policy.check(f"{self.origin}/json")
        policy.check(self.origin + "/")
        await asyncio.sleep(policy.delay())
        rows = self.rows(await self.fetch())
        await asyncio.sleep(policy.delay())
        board = BeautifulSoup(await self.http.read(self.origin + "/"), "html.parser")
        links = set()
        for a in board.select("a[href]"):
            parsed = urlsplit(urljoin(self.origin, str(a["href"])))
            if parsed.netloc == urlsplit(self.origin).netloc and re.fullmatch(
                r"/p/[a-f0-9]{12}-[A-Za-z0-9_-]+", parsed.path
            ):
                links.add(self.origin + parsed.path)
        if links != {row["url"] for row in rows}:
            raise ValueError("Breezy board links and feed disagree; snapshot incomplete")
        if not rows:
            # No explicit upstream total or proven empty-board marker yet.
            raise ValueError("Empty Breezy feed is not sufficient proof of complete enumeration")
        jobs = []
        for row in rows:
            policy.check(row["url"])
            await asyncio.sleep(policy.delay())
            jobs.extend(self.parse((row, await self.http.read(row["url"]))))
        await asyncio.sleep(policy.delay())
        if {row["id"] for row in self.rows(await self.fetch())} != {
            job.external_id for job in jobs
        }:
            raise ValueError("Breezy feed changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

"""HireHive public hosted ItemList and JobPosting documents, without account APIs."""

import asyncio
import json
import math
import re
from typing import Any
from urllib.parse import urlsplit

import httpx
from bs4 import BeautifulSoup
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.connectors.teamtailor import TENANT
from vindex.schemas import Enumeration, JobInput


def structured(body: bytes, kind: str) -> dict[str, Any]:
    soup = BeautifulSoup(body, "html.parser")
    rows = [
        json.loads(script.get_text())
        for script in soup.select('script[type="application/ld+json"]')
    ]
    matches = [row for row in rows if isinstance(row, dict) and row.get("@type") == kind]
    if len(matches) != 1:
        raise ValueError(f"Expected one public HireHive {kind} document")
    return matches[0]


class HireHiveConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider != "hirehive" or not re.fullmatch(TENANT, slug):
            raise ValueError("Invalid HireHive tenant")
        self.origin = f"https://{slug}.hirehive.com"
        self.http = PublicHTTP(client, {f"{slug}.hirehive.com"})

    def path(self, url: str) -> str:
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.netloc != urlsplit(self.origin).netloc
            or parsed.fragment
            or not re.fullmatch(r"/[A-Za-z0-9_%~-]+-[A-Za-z0-9]{6}", parsed.path)
            or re.search(r"%(?:2f|5c|2e|25)", parsed.path, re.I)
        ):
            raise ValueError("Invalid HireHive public job link")
        return parsed.path

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("HireHive hosted ItemList is not paginated")
        return await self.http.read(self.origin + "/")

    def listings(self, body: bytes) -> dict[str, str]:
        payload = structured(body, "ItemList")
        name = payload.get("name")
        if (
            not isinstance(name, str)
            or not name.startswith("Open jobs for ")
            or not name.removeprefix("Open jobs for ").strip()
        ):
            raise ValueError("HireHive named employer collection is missing")
        total = payload["numberOfItems"]
        rows = payload["itemListElement"]
        # JSON-LD permits either a singleton object or an array.
        if isinstance(rows, dict):
            rows = [rows]
        if (
            not isinstance(rows, list)
            or type(total) is not int
            or not 0 <= total <= 400
            or total != len(rows)
        ):
            raise ValueError("HireHive list total is invalid, partial or exceeds 400-detail budget")
        result = {}
        for position, row in enumerate(rows, 1):
            if (
                row["@type"] != "ListItem"
                or type(row["position"]) is not int
                or row["position"] != position
            ):
                raise ValueError("Invalid HireHive list position")
            path = self.path(row["url"])
            if path in result or not isinstance(row["name"], str) or not row["name"].strip():
                raise ValueError("Duplicate or malformed HireHive listing")
            result[path] = row["name"]
        return result

    def parse(self, payload: Any) -> list[JobInput]:
        path, title, body = payload
        self.path(self.origin + path)
        row = structured(body, "JobPosting")
        soup = BeautifulSoup(body, "html.parser")
        canonical = soup.select_one('link[rel="canonical"]')
        if (
            self.path(row["url"]) != path
            or row["title"] != title
            or canonical is None
            or canonical.get("href") != self.origin + path
        ):
            raise ValueError("HireHive detail does not match listed title and canonical URL")
        identifier = row["identifier"]["value"]
        if (
            type(identifier) not in (int, float)
            or not math.isfinite(identifier)
            or identifier <= 0
            or int(identifier) != identifier
        ):
            raise ValueError("Invalid HireHive numeric job identifier")
        description = text(row["description"])
        locations = row.get("jobLocation") or []
        if isinstance(locations, dict):
            locations = [locations]
        places = []
        remote = row.get("jobLocationType")
        for location in locations:
            address = location["address"]
            places.append(
                ", ".join(
                    dict.fromkeys(
                        address[k]
                        for k in ("addressLocality", "addressRegion", "addressCountry")
                        if address.get(k)
                    )
                )
            )
            if not remote and re.match(
                r"^Remote(?:\b|$)", address.get("addressLocality", ""), re.I
            ):
                remote = "Remote"
        employment = row.get("employmentType")
        if isinstance(employment, list):
            employment = ", ".join(employment)
        return [
            JobInput(
                external_id=str(int(identifier)),
                title=row["title"],
                company=row["hiringOrganization"]["name"],
                description=description,
                quality_flags=[] if description else ["description_missing"],
                location="; ".join(places),
                source_url=self.origin + path,
                application_url=self.origin + path,
                employment_type=employment,
                remote_status=remote,
                salary=row.get("baseSalary"),
                published_at=row.get("datePosted"),
                raw=row,
            )
        ]

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)
        policy.check(self.origin + "/")
        await asyncio.sleep(policy.delay())
        listings = self.listings(await self.fetch())
        jobs = []
        seen_ids = set()
        for path, title in listings.items():
            url = self.origin + path
            policy.check(url)
            await asyncio.sleep(policy.delay())
            job = self.parse((path, title, await self.http.read(url)))[0]
            if job.external_id in seen_ids:
                raise ValueError("Duplicate HireHive detail identifier")
            jobs.append(job)
            seen_ids.add(job.external_id)
        await asyncio.sleep(policy.delay())
        if self.listings(await self.fetch()) != listings:
            raise ValueError("HireHive full list changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

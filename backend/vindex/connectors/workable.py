"""Documented public Workable jobs collection, on its fixed widget API host."""

import asyncio
import re
from typing import Any

import httpx
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.connectors.teamtailor import TENANT
from vindex.schemas import Enumeration, JobInput


class WorkableConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider != "workable" or not re.fullmatch(TENANT, slug):
            raise ValueError("Invalid Workable tenant")
        self.slug, self.company = slug, company
        self.origin = "https://apply.workable.com"
        self.http = PublicHTTP(client, {"apply.workable.com"})
        self.url = f"{self.origin}/api/v1/widget/accounts/{slug}?details=true"

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("Workable public collection is not paginated")
        return await self.http.json(self.url)

    def parse(self, payload: Any) -> list[JobInput]:
        if (
            not isinstance(payload, dict)
            or not isinstance(payload.get("name"), str)
            or not payload["name"].strip()
            or not isinstance(payload.get("jobs"), list)
            or any(payload.get(key) for key in ("next", "next_url", "paging"))
        ):
            raise ValueError("Invalid Workable collection or unexpected pagination")
        jobs = []
        seen = set()
        for row in payload["jobs"]:
            identifier = row["shortcode"]
            if (
                not isinstance(identifier, str)
                or not re.fullmatch(r"[A-Za-z0-9]{1,100}", identifier)
                or identifier in seen
            ):
                raise ValueError("Invalid or duplicate Workable shortcode")
            seen.add(identifier)
            # Description must be present even when explicitly empty upstream.
            description = text(row["description"])
            for key in ("requirements", "benefits"):
                if row.get(key):
                    description += "\n\n" + text(row[key])
            locations = row.get("locations") or [row]
            if not isinstance(locations, list):
                raise ValueError("Invalid Workable locations")
            places = [
                ", ".join(
                    dict.fromkeys(
                        loc[k] for k in ("city", "region", "state", "country") if loc.get(k)
                    )
                )
                for loc in locations
            ]
            remote = row.get("workplace_type")
            if not remote and type(row.get("telecommuting")) is bool:
                remote = "Remote" if row["telecommuting"] else None
            jobs.append(
                JobInput(
                    external_id=identifier,
                    title=row["title"],
                    company=payload["name"],
                    description=description,
                    quality_flags=[] if description.strip() else ["description_missing"],
                    location="; ".join(dict.fromkeys(places)),
                    source_url=row["url"],
                    application_url=row["application_url"],
                    employment_type=row.get("employment_type"),
                    remote_status=remote,
                    salary=row.get("salary"),
                    published_at=row.get("published_on"),
                    raw=row,
                )
            )
        return jobs

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)
        policy.check(self.url)
        await asyncio.sleep(policy.delay())
        first = await self.fetch()
        jobs = self.parse(first)
        await asyncio.sleep(policy.delay())
        confirmation = await self.fetch()
        confirmed = self.parse(confirmation)
        if first["name"] != confirmation["name"] or {j.external_id for j in jobs} != {
            j.external_id for j in confirmed
        }:
            raise ValueError("Workable collection changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

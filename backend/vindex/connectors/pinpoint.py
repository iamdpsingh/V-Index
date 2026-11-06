"""Documented all-postings feed; each posting keeps its distinct posting ID."""

import asyncio
import re
from typing import Any

import httpx
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.connectors.teamtailor import TENANT
from vindex.schemas import Enumeration, JobInput


class PinpointConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider != "pinpoint" or not re.fullmatch(TENANT, slug):
            raise ValueError("Invalid Pinpoint tenant")
        self.origin = f"https://{slug}.pinpointhq.com"
        self.http = PublicHTTP(client, {f"{slug}.pinpointhq.com"})
        self.company = company

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("Pinpoint public postings feed is not paginated")
        return await self.http.json(f"{self.origin}/postings.json")

    def parse(self, payload: Any) -> list[JobInput]:
        if (
            not isinstance(payload, dict)
            or not isinstance(payload.get("data"), list)
            or payload.get("next")
            or payload.get("next_url")
            or (isinstance(payload.get("links"), dict) and payload["links"].get("next"))
        ):
            raise ValueError("Invalid Pinpoint feed or unexpected pagination")
        jobs = []
        seen = set()
        for row in payload["data"]:
            key = row["id"]
            if not isinstance(key, str) or not re.fullmatch(r"[0-9]{1,20}", key) or key in seen:
                raise ValueError("Invalid or duplicate Pinpoint posting ID")
            seen.add(key)
            description = text(row["description"] or "")
            for field in ("key_responsibilities", "skills_knowledge_expertise", "benefits"):
                if row.get(field):
                    description += "\n\n" + text(
                        (row.get(field + "_header") or "") + "\n" + row[field]
                    )
            location = row["location"]
            locations = ", ".join(
                dict.fromkeys(
                    location[k] for k in ("name", "city", "province", "country") if location.get(k)
                )
            )
            compensation = None
            if row.get("compensation_visible") is True:
                compensation = {
                    k: row[k]
                    for k in (
                        "compensation",
                        "compensation_minimum",
                        "compensation_maximum",
                        "compensation_currency",
                        "compensation_frequency",
                    )
                    if row.get(k) is not None
                }
            jobs.append(
                JobInput(
                    external_id=key,
                    title=row["title"],
                    company=self.company,
                    description=description,
                    quality_flags=[] if description.strip() else ["description_missing"],
                    location=locations,
                    source_url=row["url"],
                    application_url=row.get("application_form_url") or row["url"],
                    employment_type=row.get("employment_type_text") or row.get("employment_type"),
                    remote_status=row.get("workplace_type_text") or row.get("workplace_type"),
                    salary=compensation or None,
                    # The public feed does not promise an original publication timestamp.
                    raw=row,
                )
            )
        return jobs

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)
        policy.check(f"{self.origin}/postings.json")
        await asyncio.sleep(policy.delay())
        jobs = self.parse(await self.fetch())
        await asyncio.sleep(policy.delay())
        confirmation = self.parse(await self.fetch())
        if {job.external_id for job in jobs} != {job.external_id for job in confirmation}:
            raise ValueError("Pinpoint posting identifiers changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

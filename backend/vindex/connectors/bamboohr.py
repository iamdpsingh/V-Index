"""Hosted BambooHR public career list/detail interface with explicit total checks."""

import asyncio
import re
from typing import Any

import httpx
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.connectors.teamtailor import TENANT
from vindex.schemas import Enumeration, JobInput


class BambooHRConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider != "bamboohr" or not re.fullmatch(TENANT, slug):
            raise ValueError("Invalid BambooHR tenant")
        self.origin = f"https://{slug}.bamboohr.com"
        self.http = PublicHTTP(client, {f"{slug}.bamboohr.com"})
        self.company = company

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("BambooHR list pagination is not supported")
        return await self.http.json(f"{self.origin}/careers/list")

    @staticmethod
    def rows(payload: Any) -> list[dict[str, Any]]:
        rows = payload["result"]
        total = payload["meta"]["totalCount"]
        if (
            not isinstance(rows, list)
            or type(total) is not int
            or total != len(rows)
            or total > 400
            or total < 0
        ):
            raise ValueError("BambooHR list is malformed, partial or exceeds 400-detail budget")
        ids = [row["id"] for row in rows]
        if any(not isinstance(key, str) or not re.fullmatch(r"[0-9]{1,20}", key) for key in ids):
            raise ValueError("Invalid BambooHR job identifier")
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate BambooHR identifiers")
        return rows

    def parse(self, payload: Any) -> list[JobInput]:
        row, detail = payload
        identifier = row["id"]
        self.rows({"meta": {"totalCount": 1}, "result": [row]})
        job = detail["result"]["jobOpening"]
        url = f"{self.origin}/careers/{identifier}"
        if (
            job["jobOpeningShareUrl"] != url
            or job["jobOpeningStatus"] != "Open"
            or job["jobOpeningName"] != row["jobOpeningName"]
        ):
            raise ValueError("BambooHR detail identity/status differs from listing")
        description = text(job["description"])
        location = job["location"]
        ats = job.get("atsLocation") or {}
        parts = [ats.get(k) or location.get(k) for k in ("city", "state")]
        parts.append(ats.get("country") or location.get("addressCountry"))
        flags = [] if description else ["description_missing"]
        # Retain numeric vendor enums without guessing their workplace semantics.
        remote = "Remote" if row.get("isRemote") is True else None
        if job.get("locationType") is not None and remote is None:
            flags.append("workplace_type_unmapped")
        compensation = job.get("compensation")
        salary = (
            compensation
            if isinstance(compensation, dict)
            else ({"source_text": compensation} if compensation else None)
        )
        return [
            JobInput(
                external_id=identifier,
                title=job["jobOpeningName"],
                company=self.company,
                description=description,
                quality_flags=flags,
                location=", ".join(dict.fromkeys(part for part in parts if part)),
                source_url=url,
                application_url=url,
                employment_type=job.get("employmentStatusLabel") or job.get("employmentType"),
                remote_status=remote,
                salary=salary,
                published_at=job.get("datePosted"),
                raw={"listing": row, "jobOpening": job},
            )
        ]

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)
        policy.check(f"{self.origin}/careers/list")
        policy.check(f"{self.origin}/careers")
        await asyncio.sleep(policy.delay())
        rows = self.rows(await self.fetch())
        if not rows:
            raise ValueError(
                "BambooHR empty list requires independent tenant identity verification"
            )
        jobs = []
        for row in rows:
            url = f"{self.origin}/careers/{row['id']}/detail"
            policy.check(url)
            await asyncio.sleep(policy.delay())
            jobs.extend(self.parse((row, await self.http.json(url))))
        await asyncio.sleep(policy.delay())
        confirmed = self.rows(await self.fetch())
        if {row["id"] for row in confirmed} != {job.external_id for job in jobs}:
            raise ValueError("BambooHR list changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

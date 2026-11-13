"""Published HiBob job ads from reviewed career tenants."""

import re
from typing import Any

import httpx
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.schemas import Enumeration, JobInput

TENANTS = {"oseyo-c916b6e4132742": "Oseyo", "ecarstrade": "eCarsTrade"}
SUFFIX = ".careers.hibob.com"
JOB_ID = re.compile(r"[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}")


class HiBobConnector:
    def __init__(self, tenant: str, client: httpx.AsyncClient):
        if tenant not in TENANTS:
            raise ValueError("Unreviewed HiBob career board")
        self.tenant = tenant
        host = tenant + SUFFIX
        self.origin = f"https://{host}"
        self.url = self.origin + "/api/job-ad"
        self.http = PublicHTTP(client, {host})

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("HiBob publishes a single job ad collection")
        policy = await RobotsPolicy.load(self.http, self.origin)
        policy.check(self.url)
        return await self.http.json(self.url, headers={"companyidentifier": self.tenant})

    def parse(self, payload: Any) -> list[JobInput]:
        rows = payload.get("jobAdDetails")
        if (
            not isinstance(rows, list)
            or not 0 < len(rows) < 100
            or not isinstance(payload.get("filterGroups"), dict)
            or not isinstance(payload.get("jobOpeningMetadata"), list)
            or set(payload) != {"jobAdDetails", "filterGroups", "jobOpeningMetadata"}
        ):
            raise ValueError("Unexpected or potentially truncated HiBob job collection")

        jobs = []
        seen = set()
        for row in rows:
            identifier = row["id"]
            title = text(row["title"])
            description = text(row.get("description") or "")
            if (
                not JOB_ID.fullmatch(identifier)
                or identifier in seen
                or not title
                or not description
            ):
                raise ValueError("Invalid or repeated HiBob job ad")
            seen.add(identifier)
            sections = [description]
            for key in ("requirements", "responsibilities", "benefits"):
                section = text(row.get(key) or "")
                if section:
                    sections.append(section)
            locations = []
            for place in row.get("postingLocations") or [row]:
                location = ", ".join(
                    dict.fromkeys(
                        value
                        for key in ("site", "country")
                        if isinstance(value := place.get(key), str) and value
                    )
                )
                if location and location not in locations:
                    locations.append(location)
            salary = {
                key: row[field]
                for key, field in (
                    ("min", "payTransparencyMinSalary"),
                    ("max", "payTransparencyMaxSalary"),
                    ("currency", "payTransparencySalaryCurrency"),
                    ("period", "payTransparencySalaryPayPeriod"),
                    ("additional_info", "payTransparencySalaryAdditionalInfo"),
                )
                if row.get(field) is not None and row[field] != ""
            }
            url = f"{self.origin}/jobs/{identifier}"
            jobs.append(
                JobInput(
                    external_id=identifier,
                    title=title,
                    company=TENANTS[self.tenant],
                    description="\n\n".join(sections),
                    location="; ".join(locations),
                    source_url=url,
                    application_url=url,
                    employment_type=row.get("employmentType") or None,
                    remote_status=row.get("workspaceType") or None,
                    salary=salary or None,
                    published_at=row.get("publishedAt") or None,
                    raw={"language": row.get("language"), "department": row.get("department")},
                )
            )
        return jobs

    async def discover(self) -> Enumeration:
        first = self.parse(await self.fetch())
        second = self.parse(await self.fetch())
        if {job.external_id: job for job in first} != {job.external_id: job for job in second}:
            raise ValueError("HiBob job ads changed during refresh")
        return Enumeration(jobs=first, complete=True)

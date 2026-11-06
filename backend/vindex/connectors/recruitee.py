"""Documented Recruitee XML feed, independent of careers JSON token migration."""

import re
from datetime import UTC, datetime
from typing import Any

import httpx
from defusedxml import ElementTree
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.schemas import Enumeration, JobInput


class RecruiteeConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider != "recruitee" or not re.fullmatch(
            r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", slug
        ):
            raise ValueError("Invalid Recruitee tenant")
        self.base = f"https://{slug}.recruitee.com"
        self.http = PublicHTTP(client, {f"{slug}.recruitee.com"})
        self.company = company

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("Recruitee XML is not paginated")
        return await self.http.read(f"{self.base}/api/feeds/offers.xml")

    def parse(self, payload: Any) -> list[JobInput]:
        root = ElementTree.fromstring(payload, forbid_dtd=True)
        if root.tag != "offers" or any(row.tag != "offer" for row in root):
            raise ValueError("Unexpected Recruitee XML structure")
        jobs = []
        for row in root:

            def value(name: str, element=row) -> str:
                return (element.findtext(name) or "").strip()

            if not re.fullmatch(r"[0-9]+", value("id")):
                raise ValueError("Invalid Recruitee identifier")
            description = text(value("description") + "\n" + value("requirements"))
            salary_node = row.find("salary")
            salary = (
                {child.tag: (child.text or "").strip() for child in salary_node}
                if salary_node is not None
                else {}
            )
            published = value("published_at")
            date = (
                datetime.strptime(published, "%Y-%m-%d %H:%M:%S %Z").replace(tzinfo=UTC)
                if published
                else None
            )
            jobs.append(
                JobInput(
                    external_id=value("id"),
                    title=value("title"),
                    company=value("company_name") or self.company,
                    description=description,
                    quality_flags=[] if description else ["description_missing"],
                    location=value("location"),
                    source_url=value("careers_url"),
                    application_url=value("apply_url"),
                    remote_status="Hybrid"
                    if value("hybrid") == "true"
                    else (
                        "Remote"
                        if value("remote") == "true"
                        else ("OnSite" if value("on_site") == "true" else None)
                    ),
                    employment_type=value("employment_type_code") or None,
                    salary=salary or None,
                    published_at=date,
                    raw={"xml": ElementTree.tostring(row, encoding="unicode")},
                )
            )
        return jobs

    async def discover(self) -> Enumeration:
        jobs = self.parse(await self.fetch())
        if len({job.external_id for job in jobs}) != len(jobs):
            raise ValueError("Duplicate Recruitee identifiers")
        return Enumeration(jobs=jobs, complete=True)

"""SmartRecruiters Posting API; details are mandatory before a snapshot completes."""

import asyncio
import re
from typing import Any

import httpx
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.schemas import Enumeration, JobInput


class SmartRecruitersConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider != "smartrecruiters" or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", slug):
            raise ValueError("Invalid SmartRecruiters configuration")
        self.slug, self.company = slug, company
        self.http = PublicHTTP(client, {"api.smartrecruiters.com"})
        self.base = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"

    async def fetch(self, cursor: int = 0) -> Any:
        return await self.http.json(f"{self.base}?limit=100&offset={cursor}")

    def parse(self, payload: Any) -> list[JobInput]:
        if payload.get("visibility") not in (None, "PUBLIC"):
            raise ValueError("Non-public posting rejected")
        location = payload.get("location", {})
        sections = payload["jobAd"]["sections"]
        description = "\n\n".join(
            text(section.get("title", "") + "\n" + section["text"])
            for section in sections.values()
            if section
        )
        if not description.strip():
            raise ValueError("Posting detail has no description")
        return [
            JobInput(
                external_id=str(payload["id"]),
                title=payload["name"],
                company=payload.get("company", {}).get("name") or self.company,
                description=description,
                location=location.get("fullLocation")
                or ", ".join(
                    str(location[k]) for k in ("city", "region", "country") if location.get(k)
                ),
                source_url=payload["postingUrl"],
                application_url=payload["applyUrl"],
                employment_type=payload.get("typeOfEmployment", {}).get("label"),
                remote_status="Hybrid"
                if location.get("hybrid") is True
                else (
                    "Remote"
                    if location.get("remote") is True
                    else ("OnSite" if location.get("remote") is False else None)
                ),
                published_at=payload.get("releasedDate"),
                salary=payload.get("compensation"),
                raw=payload,
            )
        ]

    async def discover(self) -> Enumeration:
        jobs: list[JobInput] = []
        seen: set[str] = set()
        total: int | None = None
        offset = 0
        for _ in range(100):
            page = await self.fetch(offset)
            rows = page["content"]
            count = page["totalFound"]
            if not isinstance(rows, list) or type(count) is not int or count < 0:
                raise ValueError("Invalid posting list shape")
            if page["offset"] != offset or (total is not None and total != count):
                raise ValueError("Pagination offset or total changed; enumeration incomplete")
            total = count
            if not rows and len(jobs) != total:
                raise ValueError("Premature end of postings")
            for row in rows:
                posting_id = str(row["id"])
                if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", posting_id) or posting_id in seen:
                    raise ValueError("Invalid or repeated posting identifier")
                if row.get("visibility") != "PUBLIC":
                    raise ValueError("Non-public listing rejected")
                detail = await self.http.json(f"{self.base}/{posting_id}")
                if str(detail["id"]) != posting_id:
                    raise ValueError("Posting detail identifier mismatch")
                jobs.extend(self.parse(detail))
                seen.add(posting_id)
                await asyncio.sleep(0.2)
            if len(jobs) == total:
                return Enumeration(jobs=jobs, complete=True)
            if len(jobs) > total:
                raise ValueError("Posting count exceeds total")
            offset += len(rows)
            await asyncio.sleep(0.5)
        raise ValueError("Pagination limit exceeded")

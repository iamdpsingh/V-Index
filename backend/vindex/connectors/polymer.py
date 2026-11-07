"""Documented unauthenticated Polymer jobs API; bounded complete single-page boards."""

import asyncio
import re
from typing import Any
from urllib.parse import urlsplit

import httpx
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.schemas import Enumeration, JobInput

SLUG = r"[a-z0-9](?:[a-z0-9-]{0,98}[a-z0-9])?"


class PolymerConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider != "polymer" or not re.fullmatch(SLUG, slug):
            raise ValueError("Invalid Polymer organization")
        self.slug = slug
        self.origin = "https://api.polymer.co"
        self.collection = f"{self.origin}/v1/hire/organizations/{slug}/jobs"
        self.http = PublicHTTP(client, {"api.polymer.co"})

    def link(self, url: str, identifier: int) -> str:
        p = urlsplit(url)
        if (
            p.scheme != "https"
            or p.netloc != "jobs.polymer.co"
            or p.query
            or p.fragment
            or p.path != f"/{self.slug}/{identifier}"
        ):
            raise ValueError("Unsupported or mismatched Polymer posting link")
        return url

    def listings(self, payload: Any) -> tuple[str, dict[int, dict]]:
        meta, items = payload["meta"], payload["items"]
        if (
            not isinstance(items, list)
            or not isinstance(meta, dict)
            or type(meta["page"]) is not int
            or meta["page"] != 1
            or meta["is_first"] is not True
            or meta["is_last"] is not True
            or type(meta["total"]) is not int
            or meta["total"] != 1
            or meta.get("next_page") is not None
            or type(meta["count"]) is not int
            or meta["count"] != len(items)
            or not 0 < len(items) <= 400
        ):
            raise ValueError("Polymer partial, paginated, empty or oversized collection")
        company = meta["organization_name"]
        if not isinstance(company, str) or not company.strip():
            raise ValueError("Missing Polymer organization identity")
        rows = {}
        for row in items:
            identifier = row["id"]
            if type(identifier) is not int or identifier <= 0 or identifier in rows:
                raise ValueError("Invalid or duplicate Polymer job ID")
            if (
                type(row["job_id"]) is not int
                or row["job_id"] != identifier
                or row["organization_name"] != company
            ):
                raise ValueError("Polymer list identity mismatch")
            self.link(row["job_post_url"], identifier)
            if not isinstance(row["title"], str) or not row["title"].strip():
                raise ValueError("Missing Polymer listing title")
            rows[identifier] = row
        return company, rows

    def parse(self, payload: Any) -> list[JobInput]:
        listing, detail = payload
        if not any(field in detail for field in ("archived_at", "closed_at")):
            raise ValueError("Missing Polymer detail lifecycle fields")
        if any(detail.get(field) is not None for field in ("archived_at", "closed_at")):
            raise ValueError("Polymer listed detail is archived or closed")
        for key in ("id", "job_id"):
            if type(detail[key]) is not int or detail[key] != listing[key]:
                raise ValueError("Polymer detail ID mismatch")
        for key in (
            "title",
            "hash_id",
            "organization_name",
            "job_post_url",
            "kind_pretty",
            "display_location",
            "remoteness_pretty",
            "published_at",
        ):
            if detail[key] != listing[key]:
                raise ValueError(f"Polymer list/detail mismatch: {key}")
        description = text(detail["description"])
        source_url = self.link(detail["job_post_url"], detail["id"])
        application_url = self.link(detail["job_application_description_url"], detail["id"])
        salary = listing.get("salary_pretty")
        if salary is not None and not isinstance(salary, str):
            raise ValueError("Invalid Polymer source salary")
        public_fields = {
            "id",
            "job_id",
            "hash_id",
            "title",
            "organization_name",
            "description",
            "department",
            "country",
            "state_region",
            "city",
            "kind",
            "kind_pretty",
            "created_at",
            "published_at",
            "created_at_timestamp",
            "published_at_timestamp",
            "archived_at",
            "closed_at",
            "display_location",
            "job_post_url",
            "job_application_description_url",
            "remoteness_pretty",
            "job_category_name",
            "remote_restriction_country_residency_is_required",
            "remote_restriction_country_list",
            "remote_restriction_overlap_hours_is_required",
            "remote_restriction_overlap_hours",
            "remote_restriction_city",
            "remote_restriction_city_google_place_id",
            "remote_restriction_timezone_utc_offset_seconds",
        }
        return [
            JobInput(
                external_id=str(detail["id"]),
                title=detail["title"],
                company=detail["organization_name"],
                description=description,
                quality_flags=[] if description else ["description_missing"],
                location=detail["display_location"] or "",
                source_url=source_url,
                application_url=application_url,
                salary={"source_text": salary} if salary else None,
                employment_type=detail["kind_pretty"],
                remote_status=detail["remoteness_pretty"],
                published_at=detail["published_at"],
                raw={
                    "listing": listing,
                    "detail": {k: v for k, v in detail.items() if k in public_fields},
                },
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("Polymer paginated boards are not supported")
        return await self.http.json(self.collection)

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)

        async def read(url: str) -> Any:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.json(url)

        company, rows = self.listings(await read(self.collection))
        jobs = []
        for identifier, row in rows.items():
            jobs.extend(self.parse((row, await read(f"{self.collection}/{identifier}"))))
        confirmed_company, confirmed = self.listings(await read(self.collection))

        def stable(rows: dict[int, dict]) -> dict[int, dict]:
            # Preserve original relative ages raw; exclude only clock text from comparison.
            return {
                identifier: {k: v for k, v in row.items() if k != "published_at_time_ago_short"}
                for identifier, row in rows.items()
            }

        if confirmed_company != company or stable(confirmed) != stable(rows):
            raise ValueError("Polymer full collection changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

"""Hosted Workday career search. Unsupported sizes fail without closing jobs."""

import asyncio
import re
from typing import Any
from urllib.parse import urlsplit

import httpx
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.schemas import Enumeration, JobInput

TENANT = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
HOST_PATTERN = re.compile(rf"({TENANT})\.(wd[1-9][0-9]{{0,2}})\.myworkdayjobs\.com")
SITE_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,80}")
# The observed API reports 2000 at its ceiling; never assume that means all jobs.
UNSAFE_TOTAL = 2000
MAX_DETAIL_JOBS = 400


class WorkdayConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        parts = slug.split("~")
        if provider != "workday" or len(parts) != 3 or len(slug) > 100:
            raise ValueError("Invalid Workday configuration")
        self.tenant, self.dc, self.site = parts
        host = f"{self.tenant}.{self.dc}.myworkdayjobs.com"
        if not HOST_PATTERN.fullmatch(host) or not SITE_PATTERN.fullmatch(self.site):
            raise ValueError("Invalid Workday tenant, data center or site")
        self.origin = f"https://{host}"
        self.base = f"{self.origin}/wday/cxs/{self.tenant}/{self.site}"
        self.company = company
        self.http = PublicHTTP(client, {host})
        self.policy: RobotsPolicy | None = None

    async def fetch(self, cursor: int = 0) -> Any:
        url = f"{self.base}/jobs"
        if self.policy is None:
            raise ValueError("Load career-site robots policy before fetching")
        self.policy.check(url)
        return await self.http.json(
            url,
            method="POST",
            json_body={"appliedFacets": {}, "limit": 20, "offset": cursor, "searchText": ""},
        )

    def parse(self, payload: Any) -> list[JobInput]:
        info = payload["jobPostingInfo"]
        if info["jobPostingSiteId"] != self.site or info["posted"] is not True:
            raise ValueError("Detail is not an active posting on the selected site")
        url = info["externalUrl"]
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.netloc != urlsplit(self.origin).netloc
            or not parsed.path.startswith(f"/{self.site}/job/")
        ):
            raise ValueError("Posting link belongs to a different host or career site")
        description = text(info["jobDescription"])
        # startDate is source posting metadata; it is not proven original publication time.
        return [
            JobInput(
                external_id=info["id"],
                title=info["title"],
                company=payload.get("hiringOrganization", {}).get("name") or self.company,
                description=description,
                quality_flags=[] if description else ["description_missing"],
                location=info.get("location", ""),
                source_url=url,
                application_url=url,
                employment_type=info.get("timeType"),
                remote_status=info.get("remoteType"),
                salary=info.get("salary") if isinstance(info.get("salary"), dict) else None,
                raw=payload,
            )
        ]

    def path(self, value: Any) -> str:
        if not isinstance(value, str) or not re.fullmatch(r"/job/[A-Za-z0-9_./%~-]+", value):
            raise ValueError("Invalid Workday posting path")
        # Reject encoded separators, dot traversal, query strings and external links.
        if any(part in {".", ".."} for part in value.split("/")) or re.search(
            r"%(?:2f|5c|2e|25)", value, re.I
        ):
            raise ValueError("Unsafe Workday posting path")
        return value

    @staticmethod
    def rows(payload: Any) -> list[dict[str, Any]]:
        rows = payload["jobPostings"]
        if not isinstance(rows, list) or len(rows) > 20:
            raise ValueError("Invalid Workday page shape")
        return rows

    async def discover(self) -> Enumeration:
        self.policy = await RobotsPolicy.load(self.http, self.origin)
        self.policy.check(f"{self.origin}/{self.site}/")
        delay = self.policy.delay()
        await asyncio.sleep(delay)
        first = await self.fetch()
        total = first["total"]
        if type(total) is not int or total < 0 or total >= UNSAFE_TOTAL:
            raise ValueError(
                "Workday reported total is invalid or at its unsafe enumeration ceiling"
            )
        if total > MAX_DETAIL_JOBS:
            raise ValueError("Workday board exceeds the bounded detail budget; snapshot incomplete")
        rows = self.rows(first)
        first_paths = [self.path(row["externalPath"]) for row in rows]
        paths: set[str] = set()
        jobs: list[JobInput] = []
        for _ in range(21):
            for row in rows:
                path = self.path(row["externalPath"])
                if path in paths:
                    raise ValueError("Repeated Workday posting path; snapshot incomplete")
                detail_url = f"{self.base}{path}"
                self.policy.check(detail_url)
                await asyncio.sleep(delay)
                payload = await self.http.json(detail_url)
                job = self.parse(payload)[0]
                if urlsplit(job.source_url).path != f"/{self.site}{path}":
                    raise ValueError("Detail does not match the listed posting path")
                if any(job.external_id == seen.external_id for seen in jobs):
                    raise ValueError("Duplicate Workday posting identifier")
                paths.add(path)
                jobs.append(job)
            if len(jobs) > total or (not rows and len(jobs) != total):
                raise ValueError("Workday enumeration does not match its first-page total")
            if len(jobs) == total:
                # Probe beyond the advertised end, then recheck the first-page snapshot.
                await asyncio.sleep(delay)
                tail = await self.fetch(total)
                tail_paths = [self.path(row["externalPath"]) for row in self.rows(tail)]
                # Observed hosts reset an out-of-range offset to the entire first page.
                # Only that exact reset is accepted; any new/different tail is incomplete.
                if tail_paths and tail_paths != first_paths:
                    raise ValueError("Workday contains jobs beyond its advertised total")
                await asyncio.sleep(delay)
                final = await self.fetch()
                if (
                    final["total"] != total
                    or [self.path(r["externalPath"]) for r in self.rows(final)] != first_paths
                ):
                    raise ValueError("Workday first-page snapshot changed during enumeration")
                return Enumeration(jobs=jobs, complete=True)
            await asyncio.sleep(delay)
            page = await self.fetch(len(jobs))
            # Observed subsequent pages can return total=0; only nonzero changes are conflicts.
            if page.get("total") not in (0, total):
                raise ValueError("Workday total changed during enumeration")
            rows = self.rows(page)
        raise ValueError("Workday page budget exceeded")

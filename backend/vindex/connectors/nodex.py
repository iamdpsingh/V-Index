"""Nodex public job search roster and structured JobPosting details."""

import asyncio
import json
import re
from datetime import datetime
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
from bs4 import BeautifulSoup
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.schemas import Enumeration, JobInput

HOSTS = frozenset({"www.emotivtech.co.uk", "www.geckotravelrecruitment.co.uk"})
MAX_JOBS = 200
JOB_PATH = re.compile(r"^/job/([a-z0-9_-]+)/([0-9]{1,12})$")


def document(body: bytes) -> BeautifulSoup:
    if b"</html>" not in body.lower():
        raise ValueError("Truncated public HTML document")
    return BeautifulSoup(body, "html.parser")


class NodexConnector:
    """Connector for Nodex-powered recruitment websites and job boards."""

    def __init__(self, slug: str, client: httpx.AsyncClient):
        if slug not in HOSTS:
            raise ValueError(f"Unreviewed Nodex origin: {slug}")
        self.host = slug
        self.origin = f"https://{slug}"
        self.http = PublicHTTP(client, {slug})

    def roster(self, body: bytes) -> dict[str, str]:
        soup = document(body)
        links = soup.find_all("a", href=True)
        if not links:
            raise ValueError("No links found on Nodex search page")

        result: dict[str, str] = {}
        for a in links:
            href = a.get("href")
            if not isinstance(href, str):
                continue
            matched = JOB_PATH.match(href)
            if not matched:
                continue
            job_id = matched.group(2)
            if job_id not in result:
                result[job_id] = f"{self.origin}{href}"

        if not result:
            raise ValueError("No matching job links found on Nodex search page")
        if len(result) > MAX_JOBS:
            raise ValueError(f"Nodex search page exceeded {MAX_JOBS}-job limit")
        return result

    def parse_detail(self, job_id: str, url: str, body: bytes) -> JobInput:
        soup = document(body)
        scripts = soup.find_all("script", type="application/ld+json")
        job_data: dict[str, Any] | None = None
        for script in scripts:
            try:
                data = json.loads(script.get_text())
                if isinstance(data, dict) and data.get("@type") == "JobPosting":
                    job_data = data
                    break
            except Exception:
                continue

        if not job_data:
            raise ValueError(f"Missing JobPosting schema on Nodex detail page: {url}")

        title = str(job_data.get("title", "")).strip()
        if not title:
            raise ValueError("Nodex job missing title")

        company = ""
        org = job_data.get("hiringOrganization")
        if isinstance(org, dict) and org.get("name"):
            company = str(org["name"]).strip()
        if not company:
            company = self.host

        description = text(job_data.get("description", ""))
        flags = [] if description else ["description_missing"]

        location = ""
        loc_obj = job_data.get("jobLocation")
        if isinstance(loc_obj, list) and loc_obj:
            loc_obj = loc_obj[0]
        if isinstance(loc_obj, dict):
            addr = loc_obj.get("address")
            if isinstance(addr, dict):
                parts = [
                    addr.get("addressLocality"),
                    addr.get("addressRegion"),
                    addr.get("addressCountry"),
                ]
                location = ", ".join(str(p).strip() for p in parts if p and str(p).strip())

        published_at: datetime | None = None
        date_str = job_data.get("datePosted")
        if isinstance(date_str, str) and date_str:
            try:
                published_at = datetime.fromisoformat(date_str)
            except ValueError:
                pass

        employment: str | None = None
        emp_raw = job_data.get("employmentType")
        if isinstance(emp_raw, list) and emp_raw:
            employment = str(emp_raw[0]).strip() or None
        elif isinstance(emp_raw, str):
            employment = emp_raw.strip() or None

        return JobInput(
            external_id=job_id,
            title=title,
            company=company,
            description=description,
            quality_flags=flags,
            location=location,
            source_url=url,
            application_url=url,
            employment_type=employment,
            published_at=published_at,
            raw=job_data,
        )

    def parse(self, payload: Any) -> list[JobInput]:
        if isinstance(payload, tuple) and len(payload) == 3:
            job_id, url, body = payload
            return [self.parse_detail(job_id, url, body)]
        if isinstance(payload, list):
            return payload
        raise ValueError("Invalid payload for Nodex parse")

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor != 0:
            raise ValueError("Nodex does not support pagination cursor")
        return await self.discover()

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)
        search_url = f"{self.origin}/search"
        policy.check(search_url)
        await asyncio.sleep(policy.delay())

        async def read(url: str) -> bytes:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        async def full_roster() -> dict[str, str]:
            result: dict[str, str] = {}
            current = search_url
            expected_total: int | None = None
            for page in range(1, MAX_JOBS // 10 + 1):
                body = await read(current)
                soup = document(body)
                totals = {
                    int(m[1])
                    for node in soup.select("h1, .hz-rs-count")
                    if (
                        m := re.fullmatch(
                            r"([1-9][0-9]*) jobs?(?: found)?", node.get_text(" ", strip=True)
                        )
                    )
                }
                if len(totals) != 1:
                    raise ValueError("Missing native Nodex result total")
                total = totals.pop()
                if total > MAX_JOBS or (expected_total is not None and total != expected_total):
                    raise ValueError("Nodex result total changed or exceeds budget")
                expected_total = total
                pages = (total - 1) // 10 + 1
                if page > pages:
                    raise ValueError("Nodex pagination exceeded result total")
                labels = soup.select(".hz-rs-pageof, .hz-rs-pg-of, .hint")
                counters = {
                    (int(m[1]), int(m[2]))
                    for node in labels
                    if (
                        m := re.fullmatch(
                            r"Page\s+([0-9]+)\s+of\s+([0-9]+)", node.get_text(" ", strip=True)
                        )
                    )
                }
                if counters != {(page, pages)} and (counters or pages > 1):
                    raise ValueError("Missing or mismatched Nodex page counter")
                rows = self.roster(body)
                if len(rows) != min(10, total - len(result)) or result.keys() & rows.keys():
                    raise ValueError("Partial or duplicate Nodex page")
                result.update(rows)
                next_links = {
                    str(a["href"]) for a in soup.select('a[aria-label="Next page"][href]')
                }
                if page == pages:
                    if next_links or len(result) != total:
                        raise ValueError("Unexpected Nodex terminal page")
                    return result
                if len(next_links) != 1:
                    raise ValueError("Missing or ambiguous Nodex next page")
                link = next_links.pop()
                parts = urlsplit(link)
                params = parse_qs(parts.query, keep_blank_values=True)
                if (
                    not link.startswith("?")
                    or parts.fragment
                    or params
                    != {
                        "match": ["broad"],
                        "latitude": [""],
                        "longitude": [""],
                        "keywords": [""],
                        "view": ["list"],
                        "sort": ["date"],
                        "location": [""],
                        "page": [str(page + 1)],
                    }
                ):
                    raise ValueError("Unexpected or filtered Nodex next page")
                current = search_url + link
            raise ValueError("Nodex pagination exceeded budget")

        before = await full_roster()

        result: list[JobInput] = []
        for job_id, detail_url in before.items():
            detail_bytes = await read(detail_url)
            result.append(self.parse_detail(job_id, detail_url, detail_bytes))

        after = await full_roster()
        if before != after:
            raise ValueError("Nodex roster changed during enumeration")

        return Enumeration(jobs=result, complete=True)

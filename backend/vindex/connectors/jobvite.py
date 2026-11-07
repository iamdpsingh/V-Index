"""Jobvite hosted, unfiltered server-rendered job tables and matching details."""

import asyncio
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.connectors.teamtailor import TENANT
from vindex.schemas import Enumeration, JobInput


class JobviteConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider != "jobvite" or not re.fullmatch(TENANT, slug):
            raise ValueError("Invalid Jobvite hosted career site")
        self.slug = slug
        self.origin = "https://jobs.jobvite.com"
        self.board = f"{self.origin}/{slug}/jobs"
        self.http = PublicHTTP(client, {"jobs.jobvite.com"})

    def soup(self, body: bytes) -> BeautifulSoup:
        if b"</html>" not in body.lower():
            raise ValueError("Truncated Jobvite document")
        return BeautifulSoup(body, "html.parser")

    def listings(self, body: bytes) -> tuple[str, dict[str, str]]:
        soup = self.soup(body)
        title = soup.title.get_text(strip=True) if soup.title else ""
        if not title.endswith(" Careers") or not title.removesuffix(" Careers").strip():
            raise ValueError("Missing Jobvite employer identity")
        if not any(h.get_text(" ", strip=True) == "Open Positions" for h in soup.select("h1,h2")):
            raise ValueError("Missing Jobvite Open Positions collection")
        scripts = "\n".join(s.get_text() for s in soup.select("script:not([src])"))
        if not re.search(r"careersiteName:\s*'" + re.escape(self.slug) + "'", scripts):
            raise ValueError("Jobvite career site identity mismatch")
        if soup.select(
            'a[rel="next"],.jv-pagination,.pagination,nav[aria-label="Pagination"],a[href*="page="]'
        ):
            raise ValueError("Jobvite paginated template unsupported")
        rows = {}
        for anchor in soup.select("table.jv-job-list td.jv-job-list-name a[href]"):
            path = str(anchor["href"])
            if (
                not re.fullmatch(rf"/{re.escape(self.slug)}/job/[A-Za-z0-9]{{8}}", path)
                or path in rows
                or not anchor.get_text(" ", strip=True)
            ):
                raise ValueError("Invalid or repeated Jobvite listing")
            rows[path] = anchor.get_text(" ", strip=True)
        if not 0 < len(rows) <= 400:
            raise ValueError("Jobvite empty list or 400-detail limit")
        return title.removesuffix(" Careers").strip(), rows

    def parse(self, payload: Any) -> list[JobInput]:
        path, title, company, body = payload
        if not re.fullmatch(rf"/{re.escape(self.slug)}/job/[A-Za-z0-9]{{8}}", path):
            raise ValueError("Invalid Jobvite job path")
        soup = self.soup(body)
        heading = soup.select_one("h2.jv-header")
        descriptions = soup.select("div.jv-job-detail-description")
        metadata = soup.select_one("p.jv-job-detail-meta")
        scripts = "\n".join(s.get_text() for s in soup.select("script:not([src])"))
        identifiers = re.findall(r"\bjobId:\s*'([A-Za-z0-9]{8})'", scripts)
        categories = re.findall(r"\bjobCategoryName:\s*'([^'\\]*)'", scripts)
        if (
            identifiers != [path.rsplit("/", 1)[1]]
            or len(categories) != 1
            or soup.title is None
            or soup.title.get_text(strip=True) != f"{company} Careers - {title}"
            or heading is None
            or heading.get_text(" ", strip=True) != title
            or len(descriptions) != 1
            or metadata is None
            or not soup.select_one(f'a[href="{path}/apply"]')
        ):
            raise ValueError("Jobvite detail title/employer/ID/application mismatch")
        parts = [" ".join(value.split()) for value in metadata.stripped_strings]
        if categories[0]:
            if not parts or parts[0] != categories[0]:
                raise ValueError("Jobvite category/location template mismatch")
            parts = parts[1:]
        description = text(str(descriptions[0]))
        remote = (
            "Remote" if any(re.match(r"^Remote(?:\b|$)", place, re.I) for place in parts) else None
        )
        return [
            JobInput(
                external_id=identifiers[0],
                title=title,
                company=company,
                description=description,
                quality_flags=[] if description else ["description_missing"],
                location="; ".join(parts),
                source_url=self.origin + path,
                application_url=self.origin + path + "/apply",
                remote_status=remote,
                raw={
                    "title": title,
                    "company": company,
                    "job_id": identifiers[0],
                    "category": categories[0],
                    "description_html": str(descriptions[0]),
                    "metadata_html": str(metadata),
                    "locations": parts,
                    "application_url": self.origin + path + "/apply",
                },
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("Jobvite paginated template unsupported")
        return await self.http.read(self.board)

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)

        async def read(url: str) -> bytes:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        company, rows = self.listings(await read(self.board))
        jobs = []
        for path, title in rows.items():
            jobs.extend(self.parse((path, title, company, await read(self.origin + path))))
        if self.listings(await read(self.board)) != (company, rows):
            raise ValueError("Jobvite full collection changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

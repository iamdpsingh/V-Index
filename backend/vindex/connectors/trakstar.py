"""Trakstar Hire public hosted opening totals and JobPosting/application pages."""

import asyncio
import html
import json
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.connectors.teamtailor import TENANT
from vindex.schemas import Enumeration, JobInput


def normalized(value: str) -> str:
    return " ".join(html.unescape(value).split())


class TrakstarConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider != "trakstar" or not re.fullmatch(TENANT, slug):
            raise ValueError("Invalid Trakstar hosted tenant")
        self.origin = f"https://{slug}.hire.trakstar.com"
        self.http = PublicHTTP(client, {f"{slug}.hire.trakstar.com"})

    def listings(self, body: bytes) -> tuple[str, dict[str, dict]]:
        if b"</html>" not in body.lower():
            raise ValueError("Truncated Trakstar board")
        soup = BeautifulSoup(body, "html.parser")
        title = normalized(soup.title.get_text(" ", strip=True)) if soup.title else ""
        company = title.split(" jobs |", 1)[0]
        if title != f"{company} jobs | {company} openings | {company} careers":
            raise ValueError("Missing named Trakstar employer board")
        totals = {
            int(n)
            for n in re.findall(r"\bView\s+([0-9]+)\s+Openings?\b", soup.get_text(" ", strip=True))
        }
        if len(totals) != 1 or not 0 < next(iter(totals)) <= 400:
            raise ValueError("Missing Trakstar complete opening total or unsupported size")
        rows = {}
        for anchor in soup.select("a[href]"):
            heading = anchor.select_one(".js-job-list-opening-name")
            if heading is None:
                continue
            path = str(anchor["href"])
            if not re.fullmatch(r"/jobs/[A-Za-z0-9]{4,100}/", path) or path in rows:
                raise ValueError("Invalid or duplicate Trakstar listed path")
            name = normalized(heading.get_text(" ", strip=True))
            meta = anchor.select_one(".js-job-list-opening-meta")
            if not name or meta is None:
                raise ValueError("Missing Trakstar job title/metadata")
            label = normalized(meta.get_text(" ", strip=True))
            pieces = label.split("|", 1)
            rows[path] = {
                "title": name,
                "metadata": label,
                "workplace": pieces[1].strip() if len(pieces) == 2 else None,
            }
        if len(rows) != next(iter(totals)):
            raise ValueError("Trakstar list is empty or does not enumerate the full total")
        return company, rows

    def parse(self, payload: Any) -> list[JobInput]:
        path, listing, company, body = payload
        if not re.fullmatch(r"/jobs/[A-Za-z0-9]{4,100}/", path) or b"</html>" not in body.lower():
            raise ValueError("Invalid Trakstar detail document")
        identifier = path.strip("/").split("/")[1]
        soup = BeautifulSoup(body, "html.parser")
        docs = [
            json.loads(script.get_text())
            for script in soup.select('script[type="application/ld+json"]')
        ]
        docs = [d for d in docs if isinstance(d, dict) and d.get("@type") == "JobPosting"]
        if len(docs) != 1:
            raise ValueError("Missing unique Trakstar JobPosting")
        row = docs[0]
        og = soup.select_one('meta[property="og:url"]')
        action = path.rstrip("/")
        if (
            normalized(row["title"]) != listing["title"]
            or row["identifier"]["value"] != identifier
            or normalized(row["hiringOrganization"]["name"]) != company
            or og is None
            or og.get("content") != self.origin + path
            or not soup.select_one(f'form#job_application_form[action="{action}"]')
            or not soup.select_one('a[href="?apply=true"]')
        ):
            raise ValueError("Trakstar detail ID/title/employer/application mismatch")
        location = row.get("jobLocation") or {}
        address = location.get("address") or {}
        place = ", ".join(
            dict.fromkeys(
                address[k]
                for k in ("addressLocality", "addressRegion", "addressCountry")
                if address.get(k)
            )
        )
        description = text(html.unescape(row["description"]))
        employment = row.get("employmentType")
        if isinstance(employment, list):
            employment = ", ".join(employment)
        return [
            JobInput(
                external_id=identifier,
                title=listing["title"],
                company=company,
                description=description,
                quality_flags=[] if description else ["description_missing"],
                location=place,
                source_url=self.origin + path,
                application_url=self.origin + path + "?apply=true",
                employment_type=employment,
                remote_status=listing["workplace"] or row.get("jobLocationType"),
                salary=row.get("baseSalary"),
                published_at=row.get("datePosted"),
                raw={"listing": listing, "jobposting": row},
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("Trakstar paginated templates unsupported")
        return await self.http.read(self.origin + "/")

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)

        async def read(url: str) -> bytes:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        company, rows = self.listings(await read(self.origin + "/"))
        jobs = []
        for path, listing in rows.items():
            jobs.extend(self.parse((path, listing, company, await read(self.origin + path))))
        if self.listings(await read(self.origin + "/")) != (company, rows):
            raise ValueError("Trakstar complete opening collection changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

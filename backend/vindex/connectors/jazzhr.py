"""JazzHR's public hosted Current Openings list and native application pages."""

import asyncio
import json
import re
from typing import Any
from urllib.parse import urlsplit

import httpx
from bs4 import BeautifulSoup
from vindex.connectors.http import PublicHTTP
from vindex.connectors.robots import RobotsPolicy
from vindex.connectors.teamtailor import TENANT
from vindex.schemas import Enumeration, JobInput


def document(body: bytes) -> BeautifulSoup:
    if b"</html>" not in body[-2048:].lower():
        raise ValueError("Truncated or non-document JazzHR HTML")
    return BeautifulSoup(body, "html.parser")


class JazzHRConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider != "jazzhr" or not re.fullmatch(TENANT, slug):
            raise ValueError("Invalid JazzHR tenant")
        self.origin = f"https://{slug}.applytojob.com"
        self.http = PublicHTTP(client, {f"{slug}.applytojob.com"})
        self.company = company

    def identifier(self, url: str) -> str:
        parsed = urlsplit(url)
        match = re.fullmatch(r"/apply/([A-Za-z0-9]{10})/[A-Za-z0-9_%~-]+", parsed.path)
        if (
            parsed.scheme != "https"
            or parsed.netloc != urlsplit(self.origin).netloc
            or parsed.query
            or parsed.fragment
            or not match
            or re.search(r"%(?:2f|5c|2e|25)", parsed.path, re.I)
        ):
            raise ValueError("Invalid JazzHR listing URL")
        return match[1]

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("JazzHR hosted Current Openings list is not paginated")
        return await self.http.read(f"{self.origin}/apply")

    def listings(self, body: bytes) -> dict[str, str]:
        soup = document(body)
        listing = soup.select_one(".jobs-list")
        if listing is None or not any(
            h.get_text(" ", strip=True) == "Current Openings" for h in listing.select("h2")
        ):
            raise ValueError("JazzHR Current Openings list missing")
        if listing.select('.pagination, a[rel="next"], [data-next-page]'):
            raise ValueError("Unexpected JazzHR pagination; snapshot incomplete")
        rows = {}
        ids = set()
        for link in listing.select(".list-group-item-heading a[href]"):
            url = str(link["href"])
            key = self.identifier(url)
            title = link.get_text(" ", strip=True)
            if not title or key in ids:
                raise ValueError("Invalid or duplicate JazzHR listing")
            rows[url] = title
            ids.add(key)
        if not rows or len(rows) > 400:
            raise ValueError("JazzHR empty list is unproven or exceeds 400-detail budget")
        return rows

    def parse(self, payload: Any) -> list[JobInput]:
        url, title, body = payload
        key = self.identifier(url)
        soup = document(body)
        canonical = soup.select_one('link[rel="canonical"]')
        header = soup.select_one(".job-header")
        heading = header.select_one("h2") if header else None
        description = soup.select_one("#job-description")
        form = soup.select_one("form#form_submit_new_resume")
        if (
            canonical is None
            or canonical.get("href") != url
            or heading is None
            or heading.get_text(" ", strip=True) != title
            or description is None
            or form is None
            or form.get("action") != url
            or str(form.get("method", "")).lower() != "post"
        ):
            raise ValueError("JazzHR detail identity, description or native application is missing")
        companies = []
        for script in soup.select('script[type="application/ld+json"]'):
            row = json.loads(script.get_text())
            if isinstance(row, dict) and row.get("@type") == "Organization":
                companies.append(row["name"])
        if len(set(companies)) != 1:
            raise ValueError("JazzHR employer identity is missing or ambiguous")
        assert header is not None
        location = header.select_one('[title="Location"]')
        employment = header.select_one("#resumator-job-employment")
        role_text = description.get_text(" ", strip=True)
        location_text = location.get_text(" ", strip=True) if location else ""
        return [
            JobInput(
                external_id=key,
                title=title,
                company=companies[0],
                description=role_text,
                quality_flags=[] if role_text else ["description_missing"],
                location=location_text,
                source_url=url,
                application_url=url,
                employment_type=employment.get_text(" ", strip=True) if employment else None,
                remote_status="Remote"
                if re.match(r"^Remote(?:\b|$)", location_text, re.I)
                else None,
                raw={
                    "url": url,
                    "title": title,
                    "employer": companies[0],
                    "description_html": str(description),
                    "job_header_html": str(header),
                },
            )
        ]

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)
        policy.check(f"{self.origin}/apply")
        await asyncio.sleep(policy.delay())
        listings = self.listings(await self.fetch())
        jobs = []
        for url, title in listings.items():
            policy.check(url)
            await asyncio.sleep(policy.delay())
            jobs.extend(self.parse((url, title, await self.http.read(url))))
        await asyncio.sleep(policy.delay())
        if self.listings(await self.fetch()) != listings:
            raise ValueError("JazzHR Current Openings changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

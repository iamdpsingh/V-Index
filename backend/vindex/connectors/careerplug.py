"""CareerPlug native account ItemList and matching public application pages."""

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
from vindex.schemas import Enumeration, JobInput


def document(body: bytes) -> BeautifulSoup:
    if b"</html>" not in body.lower():
        raise ValueError("Truncated CareerPlug document")
    return BeautifulSoup(body, "html.parser")


def schemas(soup: BeautifulSoup, kind: str) -> list[dict]:
    values = [json.loads(s.get_text()) for s in soup.select('script[type="application/ld+json"]')]
    return [v for v in values if isinstance(v, dict) and v.get("@type") == kind]


class CareerPlugConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider != "careerplug" or not re.fullmatch(r"[1-9][0-9]{0,14}", slug):
            raise ValueError("Invalid CareerPlug account ID")
        self.slug = slug
        self.origin = "https://app.careerplug.com"
        self.url = self.origin + "/accounts/" + slug
        self.http = PublicHTTP(client, {"app.careerplug.com"})

    def listings(self, body: bytes) -> tuple[str, dict[str, dict]]:
        soup = document(body)
        lists = schemas(soup, "ItemList")
        company = soup.title.get_text(" ", strip=True) if soup.title else ""
        if len(lists) != 1 or not company:
            raise ValueError("Missing named CareerPlug account ItemList")
        source = lists[0]
        count = source["numberOfItems"]
        items = source["itemListElement"]
        # The observed template caps its initial schema at 30. Never reconcile that ceiling.
        if (
            type(count) is not int
            or not 0 < count < 30
            or not isinstance(items, list)
            or len(items) != count
        ):
            raise ValueError("CareerPlug empty, capped or partial ItemList")
        form = soup.select_one("#job_filters form")
        if (
            form is None
            or form.get("action") != f"/jobs?id={self.slug}#job_filters"
            or str(form.get("method", "")).lower() != "get"
        ):
            raise ValueError("CareerPlug account/filter identity mismatch")
        names = {
            str(o.get("value"))
            for o in soup.select("#job_filter_n option[value]")
            if o.get("value")
        }
        rows = {}
        for position, item in enumerate(items, 1):
            row = item["item"]
            identifier = row["identifier"]
            value = identifier["value"]
            if (
                item.get("@type") != "ListItem"
                or type(item["position"]) is not int
                or item["position"] != position
                or row.get("@type") != "JobPosting"
                or identifier.get("name") != "CareerPlug Job ID"
                or not isinstance(value, str)
                or not re.fullmatch(r"[1-9][0-9]{0,14}", value)
                or value in rows
                or not isinstance(row["title"], str)
                or not row["title"].strip()
                or row["hiringOrganization"]["name"] != company
                or row.get("directApply") is not True
            ):
                raise ValueError("CareerPlug invalid list position, job ID or employer")
            rows[value] = row
        if {r["title"] for r in rows.values()} != names:
            raise ValueError("CareerPlug full position selector and ItemList disagree")
        return company, rows

    def parse(self, payload: Any) -> list[JobInput]:
        identifier, listing, company, body = payload
        soup = document(body)
        docs = schemas(soup, "JobPosting")
        if len(docs) != 1:
            raise ValueError("Missing unique CareerPlug JobPosting detail")
        row = docs[0]
        if (
            row["identifier"]["value"] != identifier
            or row["identifier"].get("name") != "CareerPlug Job ID"
            or row["title"] != listing["title"]
            or row["hiringOrganization"]["name"] != company
            or row.get("directApply") is not True
            or not any(h.get_text(" ", strip=True) == row["title"] for h in soup.select("h1"))
            or soup.title is None
            or soup.title.get_text(" ", strip=True) != row["title"] + " | " + company
            or soup.select_one(f'form#new_app[action="/jobs/{identifier}/apps"][method="post"]')
            is None
        ):
            raise ValueError("CareerPlug detail/application ID, title or employer mismatch")
        locations = row.get("jobLocation") or []
        if isinstance(locations, dict):
            locations = [locations]
        places = []
        for location in locations:
            address = location.get("address") or {}
            places.append(
                ", ".join(
                    dict.fromkeys(
                        address[k]
                        for k in (
                            "addressLocality",
                            "addressRegion",
                            "postalCode",
                            "addressCountry",
                        )
                        if address.get(k)
                    )
                )
            )
        employment = row.get("employmentType")
        if isinstance(employment, list):
            employment = ", ".join(employment)
        description = text(html.unescape(row["description"]))
        return [
            JobInput(
                external_id=identifier,
                title=row["title"],
                company=company,
                description=description,
                quality_flags=[] if description else ["description_missing"],
                location="; ".join(dict.fromkeys(places)),
                source_url=f"{self.origin}/jobs/{identifier}/apps/new",
                application_url=f"{self.origin}/jobs/{identifier}/apps/new",
                employment_type=employment,
                remote_status=row.get("jobLocationType"),
                salary=row.get("baseSalary"),
                published_at=row.get("datePosted"),
                raw={"listing": listing, "jobposting": row},
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("CareerPlug paginated accounts unsupported")
        return await self.http.read(self.url)

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)

        async def read(url: str) -> bytes:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        company, rows = self.listings(await read(self.url))
        jobs = []
        for identifier, listing in rows.items():
            jobs.extend(
                self.parse(
                    (
                        identifier,
                        listing,
                        company,
                        await read(f"{self.origin}/jobs/{identifier}/apps/new"),
                    )
                )
            )
        if self.listings(await read(self.url)) != (company, rows):
            raise ValueError("CareerPlug full account roster changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

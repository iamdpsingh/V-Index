"""First (FirstStage) complete public native SSR boards and matching job details."""

import asyncio
import json
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup, Tag
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.connectors.teamtailor import TENANT
from vindex.schemas import Enumeration, JobInput


def document(body: bytes) -> BeautifulSoup:
    if b"</html>" not in body.lower():
        raise ValueError("Truncated FirstStage document")
    return BeautifulSoup(body, "html.parser")


def normalized(value: str) -> str:
    return " ".join(value.split())


def meta(soup: BeautifulSoup, name: str) -> str:
    values = soup.select(f'meta[property="{name}"]')
    if len(values) != 1 or not values[0].get("content"):
        raise ValueError("Missing unique FirstStage public metadata")
    return str(values[0]["content"])


def badges(node: Tag) -> dict[str, str]:
    result = {}
    for kind in ("map-pin", "briefcase", "building-2", "tag", "wallet"):
        icons = node.select("svg.lucide-" + kind)
        if len(icons) > 1 and kind != "map-pin":
            raise ValueError("Duplicate FirstStage job badge")
        values = []
        for icon in icons:
            parent = icon.parent
            if not isinstance(parent, Tag):
                raise ValueError("Malformed FirstStage job badge")
            values.append(normalized(parent.get_text(" ", strip=True)))
        if values:
            result[kind] = "; ".join(dict.fromkeys(values))
    return result


class FirstStageConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider != "firststage" or not re.fullmatch(TENANT, slug):
            raise ValueError("Invalid FirstStage tenant")
        self.origin = f"https://{slug}.firststage.co"
        self.base = self.origin + "/jobs"
        self.http = PublicHTTP(client, {slug + ".firststage.co"})

    def listings(self, body: bytes) -> tuple[str, dict[str, dict]]:
        soup = document(body)
        company = meta(soup, "og:site_name")
        headings = soup.select("h1")
        totals = [
            re.fullmatch(r"([1-9][0-9]*) jobs? open", h.get_text(" ", strip=True))
            for h in soup.select("h2")
        ]
        totals = [m for m in totals if m is not None]
        if (
            not company.strip()
            or meta(soup, "og:url") != self.base
            or len(headings) != 1
            or normalized(headings[0].get_text(" ", strip=True)) != "Jobs at " + company
            or len(totals) != 1
            or soup.select('[rel="next"],.pagination')
        ):
            raise ValueError("Unsupported FirstStage unfiltered full board template")
        result: dict[str, dict] = {}
        for anchor in soup.select("a[href]"):
            url = str(anchor["href"])
            if "/jobs/" not in url:
                continue
            match = re.fullmatch(
                re.escape(self.base) + r"/([A-Za-z0-9]{10})/view\?layout=list", url
            )
            title_node = anchor.find("span", recursive=False)
            if not match or title_node is None:
                raise ValueError("Unexpected FirstStage native job link")
            title = normalized(title_node.get_text(" ", strip=True))
            if not title:
                raise ValueError("Missing FirstStage public title")
            row = {"url": url, "title": title, "badges": badges(anchor)}
            identifier = match[1]
            # Native location groups repeat the same multi-location role. Require exact identity.
            if identifier in result and result[identifier] != row:
                raise ValueError("Conflicting FirstStage grouped job observations")
            result[identifier] = row
        total = totals[0]
        assert total is not None
        if not 0 < len(result) == int(total[1]) <= 400:
            raise ValueError("Incomplete or oversized FirstStage public job collection")
        return company, result

    def parse(self, payload: Any) -> list[JobInput]:
        identifier, listing, company, body = payload
        soup = document(body)
        docs = [json.loads(s.get_text()) for s in soup.select('script[type="application/ld+json"]')]
        docs = [d for d in docs if isinstance(d, dict) and d.get("@type") == "JobPosting"]
        h1 = soup.select("h1")
        full = soup.select("div.prose")
        native = self.base + f"/{identifier}/view"
        if len(docs) != 1 or len(h1) != 1 or len(full) != 1:
            raise ValueError("Missing unique FirstStage full public detail")
        row = docs[0]
        title_parts = h1[0].find_all("div", recursive=False)
        detail_badges = badges(h1[0])
        apply = soup.select_one("#apply")
        if (
            row["title"] != listing["title"]
            or len(title_parts) < 2
            or normalized(title_parts[1].get_text(" ", strip=True)) != listing["title"]
            or row["hiringOrganization"]["name"] != company
            or meta(soup, "og:site_name") != company
            or meta(soup, "og:url") not in (native, native + "?")
            or row.get("directApply") != native
            or any(detail_badges.get(k) != v for k, v in listing["badges"].items())
            or soup.select_one('a[href="#apply"]') is None
            or apply is None
            or apply.select_one('input[type="file"]') is None
            or apply.select_one("button") is None
        ):
            raise ValueError("FirstStage public detail/application identity mismatch")
        description_html = str(full[0])
        description = text(description_html)
        if normalized(description) != normalized(text(row["description"])):
            raise ValueError("FirstStage full HTML and JobPosting descriptions disagree")
        location = row.get("jobLocation")
        if not isinstance(location, dict) or not isinstance(location.get("address"), str):
            raise ValueError("Unsupported FirstStage location template")
        if detail_badges.get("map-pin", "").replace("; ", ", ") != normalized(location["address"]):
            raise ValueError("FirstStage location metadata disagrees")
        salary = row.get("baseSalary")
        if salary is not None:
            salary = {
                "structured": salary,
                "display_text": detail_badges.get("wallet"),
                "salaryCurrency": row.get("salaryCurrency"),
                "incentiveCompensation": row.get("incentiveCompensation"),
            }
        elif detail_badges.get("wallet"):
            salary = {"text": detail_badges["wallet"]}
        return [
            JobInput(
                external_id=identifier,
                title=row["title"],
                company=company,
                description=description,
                quality_flags=[] if description else ["description_missing"],
                location=detail_badges["map-pin"],
                source_url=listing["url"],
                application_url=native + "#apply",
                salary=salary,
                employment_type=detail_badges.get("briefcase"),
                remote_status=detail_badges.get("building-2"),
                published_at=row.get("datePosted"),
                raw={
                    "listing": listing,
                    "jobposting": row,
                    "detail_badges": detail_badges,
                    "full_description_html": description_html,
                },
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("FirstStage alternate pagination unsupported")
        return await self.http.read(self.base)

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)

        async def read(url: str) -> bytes:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        company, rows = self.listings(await read(self.base))
        jobs = []
        for identifier, listing in rows.items():
            jobs.extend(self.parse((identifier, listing, company, await read(listing["url"]))))
        if self.listings(await read(self.base)) != (company, rows):
            raise ValueError("FirstStage full public board changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

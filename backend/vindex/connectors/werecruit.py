"""WeRecruit native French public sitemap plus full public JobPosting/application pages."""

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


def document(body: bytes) -> BeautifulSoup:
    if b"</html>" not in body.lower():
        raise ValueError("Truncated WeRecruit document")
    return BeautifulSoup(body, "html.parser")


def schemas(soup: BeautifulSoup, kind: str) -> list[dict]:
    data = [json.loads(s.get_text()) for s in soup.select('script[type="application/ld+json"]')]
    return [d for d in data if isinstance(d, dict) and d.get("@type") == kind]


def normalized(value: str) -> str:
    return " ".join(html.unescape(value).split())


class WeRecruitConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider != "werecruit" or not re.fullmatch(TENANT, slug):
            raise ValueError("Invalid WeRecruit French tenant")
        self.origin = "https://careers.werecruit.io"
        self.base = f"{self.origin}/fr/{slug}"
        self.http = PublicHTTP(client, {"careers.werecruit.io"})

    def company(self, soup: BeautifulSoup) -> dict:
        orgs = schemas(soup, "Organization")
        if (
            len(orgs) != 1
            or orgs[0]["url"] != self.base
            or not isinstance(orgs[0]["name"], str)
            or not orgs[0]["name"].strip()
        ):
            raise ValueError("Missing unique named WeRecruit tenant identity")
        return {k: orgs[0][k] for k in ("name", "url")}

    def listings(self, body: bytes) -> tuple[dict, dict[str, dict]]:
        soup = document(body)
        company = self.company(soup)
        headings = [h for h in soup.select("h2") if h.get_text(" ", strip=True) == "Offres"]
        if (
            soup.title is None
            or soup.title.get_text(" ", strip=True) != "Plan du site"
            or len(headings) != 1
        ):
            raise ValueError("Unsupported WeRecruit full sitemap template")
        group = headings[0].find_next_sibling("ul")
        if group is None or soup.select('.pagination,[rel="next"]'):
            raise ValueError("Missing full WeRecruit sitemap offers list")
        result = {}
        pools = {}
        for anchor in group.select("a[href]"):
            url = str(anchor["href"])
            if url.startswith("/fr/redirectToPage/"):
                if not re.fullmatch(r"/fr/redirectToPage/[1-9][0-9]*", url):
                    raise ValueError("Malformed WeRecruit sitemap navigation")
                continue  # Native navigation redirect, not a job; never followed.
            matched = re.fullmatch(
                re.escape(self.base) + r"/offres/([a-z0-9_-]+)-([a-f0-9]{6})", url
            )
            title = normalized(anchor.get_text(" ", strip=True))
            if not matched or not title:
                raise ValueError("Invalid WeRecruit native offer link/title")
            if matched[1] == "candidature-spontanee" and title.casefold().startswith(
                "candidature spontanée"
            ):
                pools[url] = title
                continue
            identifier = matched[2]
            if identifier in result:
                raise ValueError("Duplicate WeRecruit native offer ID")
            result[identifier] = {"title": title, "url": url}
        if not 0 < len(result) <= 400:
            raise ValueError("WeRecruit empty or oversized active sitemap")
        return {**company, "excluded_spontaneous_applications": pools}, result

    def parse(self, payload: Any) -> list[JobInput]:
        identifier, listing, board, body = payload
        soup = document(body)
        company = self.company(soup)
        docs = schemas(soup, "JobPosting")
        headings = soup.select("h1")
        canonicals = soup.select('link[rel="canonical"]')
        full = soup.select("div.description.rich-text")
        form = soup.select_one("form#form")
        if len(docs) != 1:
            raise ValueError("Missing unique WeRecruit JobPosting")
        row = docs[0]
        if (
            company != {k: board[k] for k in ("name", "url")}
            or normalized(row["title"]) != listing["title"]
            or len(headings) != 1
            or normalized(headings[0].get_text(" ", strip=True)) != listing["title"]
            or len(canonicals) != 1
            or canonicals[0].get("href") != listing["url"]
            or len(full) != 1
            or form is None
            or form.get("action") != listing["url"]
            or str(form.get("method", "")).lower() != "post"
            or soup.select_one('button#submit-button[type="submit"]') is None
            or not isinstance(row["hiringOrganization"]["name"], str)
            or not row["hiringOrganization"]["name"].strip()
        ):
            raise ValueError("WeRecruit title/tenant/canonical/native application mismatch")
        description_html = str(full[0])
        description = text(description_html)
        role = text(html.unescape(row["description"]))
        if role and normalized(role) not in normalized(description):
            raise ValueError("WeRecruit full HTML and structured role text disagree")
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
        flags = [] if description else ["description_missing"]
        if not role:
            flags.append("role_description_missing")
        return [
            JobInput(
                external_id=identifier,
                title=listing["title"],
                company=row["hiringOrganization"]["name"],
                description=description,
                quality_flags=flags,
                location="; ".join(dict.fromkeys(places)),
                source_url=listing["url"],
                application_url=listing["url"],
                employment_type=employment,
                remote_status=row.get("jobLocationType"),
                salary=row.get("baseSalary"),
                published_at=row.get("datePosted"),
                raw={
                    "listing": listing,
                    "board": board,
                    "jobposting": row,
                    "full_description_html": description_html,
                },
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("WeRecruit alternate sitemap pagination unsupported")
        return await self.http.read(self.base + "/site-map")

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)

        async def read(url: str) -> bytes:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        board, rows = self.listings(await read(self.base + "/site-map"))
        jobs = []
        for identifier, listing in rows.items():
            jobs.extend(self.parse((identifier, listing, board, await read(listing["url"]))))
        if self.listings(await read(self.base + "/site-map")) != (board, rows):
            raise ValueError("WeRecruit full public sitemap changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

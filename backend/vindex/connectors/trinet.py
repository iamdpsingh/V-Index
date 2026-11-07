"""TriNet Hire native public full job tables and matching native application pages."""

import asyncio
import re
from typing import Any
from urllib.parse import urlsplit

import httpx
from bs4 import BeautifulSoup
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.schemas import Enumeration, JobInput

SLUG = r"[1-9][0-9]{0,14}-[a-z0-9]+(?:-[a-z0-9]+)*"


def document(body: bytes) -> BeautifulSoup:
    if b"</html>" not in body.lower():
        raise ValueError("Truncated TriNet Hire document")
    return BeautifulSoup(body, "html.parser")


class TriNetConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider != "trinet" or not re.fullmatch(SLUG, slug) or len(slug) > 100:
            raise ValueError("Invalid TriNet Hire native company")
        self.slug = slug
        self.origin = "https://app.trinethire.com"
        self.path = f"/companies/{slug}/jobs"
        self.http = PublicHTTP(client, {"app.trinethire.com"})

    def listings(self, body: bytes) -> tuple[str, dict[str, dict]]:
        soup = document(body)
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        if not title.startswith("Careers at ") or not title.removeprefix("Careers at ").strip():
            raise ValueError("Missing named TriNet Hire company")
        company = title.removeprefix("Careers at ").strip()
        if not soup.select_one(f'a[href="{self.path}"]') or soup.select('.pagination,[rel="next"]'):
            raise ValueError("TriNet Hire company identity or pagination unsupported")
        rows = {}
        tables = soup.select("table.job-list")
        if not tables:
            raise ValueError("Missing TriNet Hire public opening table")
        for table in tables:
            if [h.get_text(" ", strip=True) for h in table.select("thead th")] != [
                "Role",
                "Type",
                "Location",
            ]:
                raise ValueError("Unexpected TriNet Hire table columns")
            for row in table.select("tbody tr"):
                anchors = row.select("td a[href]")
                if len(anchors) != 1 or "job" not in row.get_attribute_list("class"):
                    raise ValueError("Malformed TriNet Hire opening row")
                path = str(anchors[0]["href"])
                matched = re.fullmatch(
                    re.escape(self.path) + r"/([1-9][0-9]{0,14})-[a-z0-9-]+", path
                )
                kind, location = row.select_one("td.type"), row.select_one("td.location")
                name = anchors[0].get_text(" ", strip=True)
                if matched is None or path in rows or not name or kind is None or location is None:
                    raise ValueError("Invalid TriNet Hire listed ID/title/metadata")
                rows[path] = {
                    "id": matched[1],
                    "title": name,
                    "employment_type": kind.get_text(" ", strip=True),
                    "location": location.get_text(" ", strip=True),
                }
        if not 0 < len(rows) <= 400 or len({r["id"] for r in rows.values()}) != len(rows):
            raise ValueError("Empty, duplicate or oversized TriNet Hire list")
        native_links = {
            str(a["href"])
            for a in soup.select("a[href]")
            if str(a["href"]).startswith(self.path + "/")
        }
        if native_links != set(rows):
            raise ValueError("TriNet Hire opening links and full tables disagree")
        return company, rows

    def parse(self, payload: Any) -> list[JobInput]:
        path, listing, company, body = payload
        soup = document(body)
        heading = soup.select("h3.job-name")
        description = soup.select("div.job-descr.content")
        identifier = soup.select('input#job_id[name="job_id"]')
        meta_url = soup.select('meta[property="og:url"]')
        meta_title = soup.select('meta[property="og:title"]')
        site = soup.select_one('meta[property="og:site_name"]')
        if len(meta_url) != 1 or len(meta_title) != 1:
            raise ValueError("Missing unique TriNet Hire detail identity")
        original_url = str(meta_url[0].get("content", ""))
        parsed = urlsplit(original_url)
        if (
            parsed.scheme != "https"
            or parsed.netloc != "app.trinethire.com"
            or parsed.path != path
            or parsed.query not in ("", "source=Our+Job+Board")
            or parsed.fragment
            or meta_title[0].get("content") != company + " | " + listing["title"]
            or site is None
            or site.get("content") != "TriNet Applicant Tracking"
            or len(heading) != 1
            or heading[0].get_text(" ", strip=True) != listing["title"]
            or len(description) != 1
            or len(identifier) != 1
            or identifier[0].get("value") != listing["id"]
            or soup.select_one(f'form#new_applicant[action="{path}"][method="post"]') is None
            or not any(
                a.get_text(" ", strip=True) == "Jobs at " + company
                for a in soup.select(f'a[href="{self.path}"]')
            )
        ):
            raise ValueError(
                "TriNet Hire detail/company/application mismatch or confidential template"
            )
        metadata = [li.get_text(" ", strip=True) for li in soup.select("ul.job-meta > li")]
        kinds = [v.removeprefix("Type:").strip() for v in metadata if v.startswith("Type:")]
        place_nodes = soup.select("ul.job-meta .map-pin-icon")
        if (
            kinds != [listing["employment_type"]]
            or len(place_nodes) != 1
            or place_nodes[0].parent is None
        ):
            raise ValueError("TriNet Hire listing and detail type/location mismatch")
        detail_location = place_nodes[0].parent.get_text(" ", strip=True)
        description_html = str(description[0])
        description_text = text(description_html)
        salary = [v for v in metadata if v.startswith(("Salary:", "Compensation:"))]
        return [
            JobInput(
                external_id=listing["id"],
                title=listing["title"],
                company=company,
                description=description_text,
                quality_flags=[] if description_text else ["description_missing"],
                location="; ".join(
                    dict.fromkeys(v for v in [listing["location"], detail_location] if v)
                ),
                source_url=self.origin + path,
                application_url=self.origin + path,
                employment_type=listing["employment_type"],
                remote_status="Remote" if listing["location"].lower() == "remote" else None,
                salary={"text": "; ".join(salary)} if salary else None,
                raw={
                    "listing": listing,
                    "detail_metadata": metadata,
                    "description_html": description_html,
                    "original_source_url": original_url,
                },
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("TriNet Hire pagination unsupported")
        return await self.http.read(self.origin + self.path)

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)

        async def read(url: str) -> bytes:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        company, rows = self.listings(await read(self.origin + self.path))
        jobs = []
        for path, listing in rows.items():
            jobs.extend(self.parse((path, listing, company, await read(self.origin + path))))
        if self.listings(await read(self.origin + self.path)) != (company, rows):
            raise ValueError("TriNet Hire complete public roster changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

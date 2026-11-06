"""PageUp native public career website listing counters and mandatory full job pages."""

import asyncio
import re
from datetime import datetime
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
from bs4 import BeautifulSoup, Tag
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.schemas import Enumeration, JobInput


class PageUpConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if (
            provider != "pageup"
            or not re.fullmatch(r"[1-9][0-9]{0,5}~en(?:-us)?", slug)
            or not company.strip()
        ):
            raise ValueError("Invalid native PageUp career website source")
        self.tenant, self.locale = slug.split("~")
        self.company = company
        self.origin = "https://careers.pageuppeople.com"
        self.base = self.origin + f"/{self.tenant}/cw/{self.locale}"
        self.http = PublicHTTP(client, {"careers.pageuppeople.com"})

    def document(self, body: bytes) -> BeautifulSoup:
        if b"</html>" not in body.lower():
            raise ValueError("Truncated PageUp public document")
        return BeautifulSoup(body, "html.parser")

    def group(self, box: Tag, page: int) -> tuple[int, dict[str, dict]]:
        rows = {}
        for anchor in box.select("a.job-link[href]"):
            path = str(anchor["href"])
            match = re.fullmatch(
                rf"/{self.tenant}/cw/{self.locale}/job/([1-9][0-9]*)/([a-z0-9_-]+)", path
            )
            title = anchor.get_text(" ", strip=True)
            parent = anchor.find_parent("tr")
            if not match or not title or parent is None or match[1] in rows:
                raise ValueError("Invalid or duplicate PageUp native listed job")
            places = parent.select("span.location")
            dates = parent.select(".close-date time[datetime]")
            if len(places) != 1 or len(dates) > 1:
                raise ValueError("Missing unique PageUp listed location/closing metadata")
            rows[match[1]] = {
                "title": title,
                "url": self.origin + path,
                "location": places[0].get_text(" ", strip=True),
                "closing_date": str(dates[0]["datetime"]) if dates else None,
            }
        if not 0 < len(rows) <= 20:
            raise ValueError("Empty or oversized native PageUp page")
        more = box.select("a.more-link")
        if len(more) > 1:
            raise ValueError("Ambiguous PageUp next-page counter")
        remaining = 0
        if more:
            counts = more[0].select("span.count")
            href = urlsplit(str(more[0].get("href", "")))
            if (
                len(counts) != 1
                or not re.fullmatch(r"[1-9][0-9]*", counts[0].get_text(strip=True))
                or more[0].get("data-page") != str(page + 1)
                or more[0].get("data-page-items") != "20"
                or href.scheme
                or href.netloc
                or href.path != f"/{self.tenant}/cw/{self.locale}/listing/"
                or parse_qs(href.query) != {"page": [str(page + 1)], "page-items": ["20"]}
                or href.fragment
                or len(rows) != 20
            ):
                raise ValueError("Invalid PageUp native pagination/counter")
            remaining = int(counts[0].get_text(strip=True))
        total = (page - 1) * 20 + len(rows) + remaining
        if not total <= 200:
            raise ValueError("PageUp source exceeds 200 mandatory jobs")
        return total, rows

    def page(self, body: bytes, page: int) -> tuple[str, int, dict[str, dict]]:
        soup = self.document(body)
        recent = soup.select("#recent-jobs")
        search = soup.select("#search-results")
        if soup.title is None or len(recent) != 1 or len(search) != 1:
            raise ValueError("Unsupported PageUp full public listing template")
        result = self.group(recent[0], page)
        if self.group(search[0], page) != result:
            raise ValueError("PageUp current and unfiltered search lists disagree")
        return soup.title.get_text(" ", strip=True), *result

    def parse(self, payload: Any) -> list[JobInput]:
        identifier, listing, brand, body = payload
        soup = self.document(body)
        contents = soup.select("#job-content")
        canonicals = soup.select('link[rel="canonical"]')
        titles = soup.select('meta[property="og:title"]')
        if (
            len(contents) != 1
            or len(canonicals) != 1
            or canonicals[0].get("href") != listing["url"]
            or len(titles) != 1
            or titles[0].get("content") != listing["title"]
        ):
            raise ValueError("Missing or mismatched full PageUp job identity")
        content = contents[0]
        headings = content.find_all("h2", recursive=False)
        ids = content.select(".job-externalJobNo")
        descriptions = content.select("#job-details")
        locations = content.select("span.location")
        employment = content.select("span.work-type")
        posted = content.select(".open-date time[datetime]")
        closing = content.select(".close-date time[datetime]")
        if (
            len(headings) != 1
            or headings[0].get_text(" ", strip=True) != listing["title"]
            or len(ids) != 1
            or not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", ids[0].get_text(strip=True))
            or len(descriptions) != 1
            or len(locations) != 1
            or locations[0].get_text(" ", strip=True) != listing["location"]
            or len(employment) != 1
            or len(posted) > 1
            or len(closing) > 1
            or (str(closing[0]["datetime"]) if closing else None) != listing["closing_date"]
        ):
            raise ValueError("PageUp listed/detail title, ID or metadata disagree")
        applications = []
        for anchor in content.select("a.apply-link[href]"):
            url = str(anchor["href"])
            parsed = urlsplit(url)
            params = parse_qs(parsed.query)
            if (
                parsed.scheme != "https"
                or not re.fullmatch(r"secure\.dc[1-9][0-9]?\.pageuppeople\.com", parsed.netloc)
                or parsed.path != f"/apply/{self.tenant}/gateway/default.aspx"
                or params.get("c") != ["apply"]
                or params.get("lJobID") != [identifier]
                or parsed.fragment
                or set(params) - {"c", "lJobID", "lJobSourceTypeID", "sLanguage"}
            ):
                raise ValueError("Unscoped PageUp native application control")
            applications.append(url)
        if not applications or len(set(applications)) != 1:
            raise ValueError("Missing or inconsistent PageUp native apply links")
        description = text(str(descriptions[0]))
        if not description:
            raise ValueError("Empty PageUp full description")
        salaries = []
        for node in descriptions[0].select("p,li"):
            value = node.get_text(" ", strip=True)
            if re.match(r"(?:salary(?: range)?|remuneration|pay)\s*:", value, re.I):
                salaries.append(value)
        workplace = content.select("span.work-arrangement")
        if len(workplace) > 1:
            raise ValueError("Ambiguous PageUp explicit workplace metadata")
        return [
            JobInput(
                external_id=identifier,
                title=listing["title"],
                company=self.company,
                description=description,
                location=listing["location"],
                source_url=listing["url"],
                application_url=applications[0],
                salary={"text": "; ".join(dict.fromkeys(salaries))} if salaries else None,
                employment_type=employment[0].get_text(" ", strip=True),
                remote_status=workplace[0].get_text(" ", strip=True) if workplace else None,
                published_at=datetime.fromisoformat(str(posted[0]["datetime"])) if posted else None,
                quality_flags=["company_from_source_configuration"],
                raw={
                    "listing": listing,
                    "board_title": brand,
                    "full_description_html": str(descriptions[0]),
                    "published_at_original": str(posted[0]["datetime"]) if posted else None,
                    "application_url": applications[0],
                    "external_job_number": ids[0].get_text(strip=True),
                    "employer_identity_source": "source_configuration",
                },
            )
        ]

    def page_url(self, page: int) -> str:
        return self.base + "/listing/" + (f"?page={page}&page-items=20" if page > 1 else "")

    async def fetch(self, cursor: int = 0) -> Any:
        if not 0 <= cursor < 10:
            raise ValueError("PageUp native page budget exceeded")
        return await self.http.read(self.page_url(cursor + 1))

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)

        async def read(url: str) -> bytes:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        async def roster() -> tuple[str, dict[str, dict]]:
            brand, total, rows = self.page(await read(self.page_url(1)), 1)
            for page in range(2, (total + 19) // 20 + 1):
                next_brand, count, following = self.page(await read(self.page_url(page)), page)
                if brand != next_brand or count != total or set(rows) & set(following):
                    raise ValueError("PageUp public total/brand changed or repeated IDs")
                rows.update(following)
            if len(rows) != total:
                raise ValueError("Incomplete PageUp full public roster")
            return brand, rows

        brand, rows = await roster()
        jobs = []
        for identifier, listing in rows.items():
            jobs.extend(self.parse((identifier, listing, brand, await read(listing["url"]))))
        if await roster() != (brand, rows):
            raise ValueError("PageUp full public roster changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

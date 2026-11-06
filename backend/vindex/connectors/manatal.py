"""Public legacy Manatal careers-page.com collection and matching HTML details."""

import asyncio
import re
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit

import httpx
from bs4 import BeautifulSoup
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.connectors.teamtailor import TENANT
from vindex.schemas import Enumeration, JobInput

ORDER = "-is_pinned_in_career_page,-last_published_at"


class ManatalConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider != "manatal" or not re.fullmatch(TENANT, slug):
            raise ValueError("Invalid Manatal hosted board")
        self.slug = slug
        self.origin = "https://www.careers-page.com"
        self.board = f"{self.origin}/{slug}"
        self.api_path = f"/api/v1.0/c/{slug}/jobs/"
        self.http = PublicHTTP(client, {"www.careers-page.com"})

    def page_url(self, page: int) -> str:
        return (
            self.origin
            + self.api_path
            + "?"
            + urlencode({"page_size": 50, "page": page, "ordering": ORDER})
        )

    def validate_page_link(self, url: Any, page: int) -> None:
        if not isinstance(url, str):
            raise ValueError("Missing Manatal pagination link")
        p = urlsplit(url)
        if (
            p.scheme != "https"
            or p.netloc != "www.careers-page.com"
            or p.path != self.api_path
            or p.fragment
            or parse_qs(p.query) != {"page_size": ["50"], "page": [str(page)], "ordering": [ORDER]}
        ):
            raise ValueError("Invalid Manatal pagination link")

    def board_info(self, body: bytes) -> tuple[str, int, dict[str, str]]:
        if b"</html>" not in body.lower():
            raise ValueError("Truncated Manatal board")
        soup = BeautifulSoup(body, "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else ""
        match = re.fullmatch(r"- (.+) \| Career Page", title)
        totals = soup.select("h4.positions")
        if not match or len(totals) != 1:
            raise ValueError("Missing Manatal employer identity or total")
        count = re.fullmatch(r"([0-9]+) Open Positions", totals[0].get_text(" ", strip=True))
        if not count or not 0 < int(count[1]) <= 400:
            raise ValueError("Manatal empty board or 400-detail limit")
        scripts = "\n".join(s.get_text() for s in soup.select("script:not([src])"))
        if f'const clientSlug = "{self.slug}";' not in scripts:
            raise ValueError("Manatal board slug mismatch")
        links = {}
        for anchor in soup.select("a[href]"):
            path = str(anchor["href"])
            m = re.fullmatch(rf"/{re.escape(self.slug)}/job/([A-Z0-9]{{8}})", path)
            heading = anchor.select_one("h5")
            if m and heading:
                name = heading.get_text(" ", strip=True)
                if m[1] in links or not name:
                    raise ValueError("Duplicate or empty Manatal visible listing")
                links[m[1]] = name
        if not links or len(links) > int(count[1]):
            raise ValueError("Missing Manatal visible listings")
        return match[1], int(count[1]), links

    def parse(self, payload: Any) -> list[JobInput]:
        row, company, body = payload
        identifier = row["hash"]
        soup = BeautifulSoup(body, "html.parser")
        expected = f"{row['position_name']} - {company} | Career Page"
        heading = soup.select_one("h1.job-position-break")
        og = soup.select_one('meta[property="og:title"]')
        site = soup.select_one('meta[property="og:site_name"]')
        descriptions = soup.select("div.redactor-styles")
        path = f"/{self.slug}/job/{identifier}"
        if (
            b"</html>" not in body.lower()
            or soup.title is None
            or soup.title.get_text(strip=True) != expected
            or og is None
            or og.get("content") != expected
            or site is None
            or site.get("content") != "Manatal"
            or heading is None
            or heading.get_text(" ", strip=True) != row["position_name"]
            or len(descriptions) != 1
            or not soup.select_one(f'a[href="/{self.slug}"]')
            or not soup.select_one(f'a[href="{path}/apply"]')
        ):
            raise ValueError("Manatal detail identity/application template mismatch")
        description = text(row["description"])
        if " ".join(description.split()) != " ".join(text(str(descriptions[0])).split()):
            raise ValueError("Manatal collection/detail descriptions differ")
        location = row.get("location_display") or ", ".join(
            dict.fromkeys(row[k] for k in ("city", "state", "country") if row.get(k))
        )
        visible = row["is_salary_visible"]
        if type(visible) is not bool:
            raise ValueError("Invalid Manatal salary visibility")
        salary = (
            {k: row.get(k) for k in ("currency_code", "salary_min", "salary_max")}
            if visible
            else None
        )
        return [
            JobInput(
                external_id=identifier,
                title=row["position_name"],
                company=company,
                description=description,
                quality_flags=[] if description else ["description_missing"],
                location=location,
                source_url=self.origin + path,
                application_url=self.origin + path + "/apply",
                salary=salary,
                raw={
                    "listing": row,
                    "detail": {
                        "title": expected,
                        "description_html": str(descriptions[0]),
                        "application_url": self.origin + path + "/apply",
                    },
                },
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        return await self.http.json(self.page_url(cursor + 1))

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)

        async def read(url: str, json: bool = False) -> Any:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.json(url) if json else await self.http.read(url)

        info = self.board_info(await read(self.board))

        async def enumerate_rows() -> dict[str, dict]:
            rows: dict[str, dict] = {}
            ids = set()
            for page in range(1, 101):
                data = await read(self.page_url(page), True)
                count, items = data["count"], data["results"]
                if (
                    type(count) is not int
                    or count != info[1]
                    or not isinstance(items, list)
                    or not 0 < len(items) <= 50
                ):
                    raise ValueError("Manatal partial or changed page/count")
                if page == 1:
                    if data["previous"] is not None:
                        raise ValueError("Manatal first page has previous link")
                else:
                    self.validate_page_link(data["previous"], page - 1)
                for row in items:
                    identifier = row["hash"]
                    if (
                        not isinstance(identifier, str)
                        or not re.fullmatch(r"[A-Z0-9]{8}", identifier)
                        or identifier in rows
                        or type(row["id"]) is not int
                        or row["id"] <= 0
                        or row["id"] in ids
                        or not isinstance(row["position_name"], str)
                        or not row["position_name"].strip()
                    ):
                        raise ValueError("Duplicate or invalid Manatal listing identity")
                    rows[identifier] = row
                    ids.add(row["id"])
                if len(rows) > count:
                    raise ValueError("Manatal collection exceeds total")
                if data["next"] is None:
                    if len(rows) != count:
                        raise ValueError("Manatal terminal page is incomplete")
                    return rows
                if len(rows) >= count:
                    raise ValueError("Unexpected Manatal extra page")
                self.validate_page_link(data["next"], page + 1)
            raise ValueError("Manatal pagination budget exceeded")

        rows = await enumerate_rows()
        if any(k not in rows or rows[k]["position_name"] != v for k, v in info[2].items()):
            raise ValueError("Manatal visible listings disagree with collection")
        jobs = []
        for identifier, row in rows.items():
            jobs.extend(self.parse((row, info[0], await read(f"{self.board}/job/{identifier}"))))
        if self.board_info(await read(self.board)) != info or await enumerate_rows() != rows:
            raise ValueError("Manatal full roster changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

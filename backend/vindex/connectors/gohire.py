"""Public GoHire board totals plus widget collection and matching job details."""

import asyncio
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

import httpx
from bs4 import BeautifulSoup
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.schemas import Enumeration, JobInput

SLUG = r"[a-z0-9](?:[a-z0-9-]{0,89}[a-z0-9])?-[a-z0-9]{8}"
HOSTS = {"jobs.gohire.io", "api2.gohire.io", "api.gohire.io"}


class GoHireConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider != "gohire" or not re.fullmatch(SLUG, slug) or len(slug) > 100:
            raise ValueError("Invalid GoHire hosted board")
        self.slug = slug
        self.origin = "https://jobs.gohire.io"
        self.board = f"{self.origin}/{slug}/"
        self.http = PublicHTTP(client, HOSTS)

    def link_id(self, url: str) -> int:
        p = urlsplit(url)
        match = re.fullmatch(rf"/{re.escape(self.slug)}/[a-z0-9-]+-([1-9][0-9]*)/", p.path)
        if (
            p.scheme != "https"
            or p.netloc != "jobs.gohire.io"
            or p.query
            or p.fragment
            or not match
        ):
            raise ValueError("Invalid or unsupported GoHire job link")
        return int(match[1])

    def board_info(self, body: bytes) -> tuple[str, str, int, dict[int, str]]:
        if b"</html>" not in body.lower():
            raise ValueError("Truncated GoHire career page")
        soup = BeautifulSoup(body, "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else ""
        if not title.startswith("Jobs at ") or not title.removeprefix("Jobs at ").strip():
            raise ValueError("Missing GoHire employer identity")
        keys = {
            m[1]
            for script in soup.select("script[src]")
            if (
                m := re.fullmatch(
                    r"https://widget\.gohire\.io/widget/([A-Za-z0-9]{8})", str(script.get("src"))
                )
            )
        }
        totals = [
            int(m[1])
            for paragraph in soup.select("p")
            if (m := re.fullmatch(r"([0-9]+) Job openings", paragraph.get_text(" ", strip=True)))
        ]
        if len(keys) != 1 or len(totals) != 1:
            raise ValueError("Missing unique GoHire widget identity or explicit board total")
        key = keys.pop()
        if key.lower() != self.slug.rsplit("-", 1)[1] or not 0 < totals[0] <= 400:
            raise ValueError("GoHire board identity mismatch, empty board or 400-detail limit")
        links = {}
        for anchor in soup.select("a.gohire-job[href]"):
            identifier = self.link_id(str(anchor["href"]))
            heading = anchor.select_one("h3.job-title")
            if identifier in links or heading is None or not heading.get_text(strip=True):
                raise ValueError("Duplicate or malformed GoHire visible job")
            links[identifier] = heading.get_text(strip=True)
        if not links or len(links) > totals[0]:
            raise ValueError("Missing or inconsistent GoHire visible job list")
        return key, title.removeprefix("Jobs at ").strip(), totals[0], links

    def listings(self, payload: Any, info: tuple[str, str, int, dict[int, str]]) -> dict[int, dict]:
        if (
            not isinstance(payload, dict)
            or set(payload)
            != {"generalApplication", "generalPoolID", "template", "colour", "jobs", "language"}
            or payload["language"] != "en"
            or not isinstance(payload["jobs"], list)
        ):
            raise ValueError("Unsupported GoHire widget collection schema or language")
        if len(payload["jobs"]) != info[2]:
            raise ValueError("GoHire API collection does not match explicit career-board total")
        rows = {}
        for row in payload["jobs"]:
            identifier = row["id"]
            if type(identifier) is not int or identifier <= 0 or identifier in rows:
                raise ValueError("Invalid or duplicate GoHire job ID")
            if (
                self.link_id(row["link"]) != identifier
                or not isinstance(row["title"], str)
                or not row["title"].strip()
            ):
                raise ValueError("GoHire listing identity mismatch")
            rows[identifier] = row
        if any(
            identifier not in rows or rows[identifier]["title"] != title
            for identifier, title in info[3].items()
        ):
            raise ValueError("GoHire API and visible career listings disagree")
        return rows

    def parse(self, payload: Any) -> list[JobInput]:
        listing, detail, company = payload
        employer = detail["client"]
        if (
            type(detail["id"]) is not int
            or detail["id"] != listing["id"]
            or detail["title"] != listing["title"]
            or employer["name"] != company
            or type(employer["id"]) is not int
            or employer["id"] <= 0
            or type(detail["isGeneralPool"]) is not int
            or detail["isGeneralPool"] != 0
        ):
            raise ValueError("GoHire detail does not match listed opening/employer")
        self.link_id(listing["link"])
        description = text(detail["description"])
        employment = detail["type"]["name"]
        if employment != listing["type"] or detail["salary"] != (listing["salary"] or None):
            raise ValueError("GoHire list/detail employment or salary changed")
        location = listing["location"]
        if not isinstance(location, str):
            raise ValueError("Malformed GoHire location")
        published = datetime.strptime(listing["date"], "%d %B, %Y") if listing["date"] else None
        raw_detail = {
            k: detail.get(k)
            for k in (
                "id",
                "title",
                "type",
                "city",
                "county",
                "postcode",
                "country",
                "description",
                "salary",
                "isGeneralPool",
            )
        }
        raw_detail["client"] = {"id": employer["id"], "name": employer["name"]}
        return [
            JobInput(
                external_id=str(detail["id"]),
                title=detail["title"],
                company=company,
                description=description,
                quality_flags=[] if description else ["description_missing"],
                location=location,
                source_url=listing["link"],
                application_url=listing["link"],
                salary={"source_text": detail["salary"]} if detail["salary"] else None,
                employment_type=employment,
                published_at=published,
                remote_status="Remote" if re.match(r"^Remote(?:\b|$)", location, re.I) else None,
                raw={"listing": listing, "detail": raw_detail, "publication_precision": "date"},
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("GoHire collection pagination is not supported")
        return await self.http.read(self.board)

    async def discover(self) -> Enumeration:
        policies = {
            host: await RobotsPolicy.load(self.http, f"https://{host}") for host in sorted(HOSTS)
        }

        async def read(url: str, json: bool = False) -> Any:
            policy = policies[urlsplit(url).hostname or ""]
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.json(url) if json else await self.http.read(url)

        info = self.board_info(await read(self.board))
        collection = f"https://api2.gohire.io/widget-jobs/{info[0]}"
        rows = self.listings(await read(collection, True), info)
        jobs = []
        employers = set()
        for identifier, listing in rows.items():
            detail = await read(
                f"https://api.gohire.io/widget-job?clientHash={info[0]}&jobId={identifier}", True
            )
            jobs.extend(self.parse((listing, detail, info[1])))
            employers.add(detail["client"]["id"])
        if len(employers) != 1:
            raise ValueError("GoHire employer identity changed across details")
        confirmed = self.board_info(await read(self.board))
        if confirmed != info or self.listings(await read(collection, True), confirmed) != rows:
            raise ValueError("GoHire board or full collection changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

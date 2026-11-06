"""Recooty careerspage.io public server-rendered Inertia state and job details."""

import asyncio
import json
import re
from typing import Any
from urllib.parse import urlsplit

import httpx
from bs4 import BeautifulSoup
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.connectors.teamtailor import TENANT
from vindex.schemas import Enumeration, JobInput


def state(body: bytes, component: str) -> tuple[BeautifulSoup, dict]:
    if b"</html>" not in body.lower():
        raise ValueError("Truncated Recooty document")
    soup = BeautifulSoup(body, "html.parser")
    docs = [
        json.loads(s.get_text())
        for s in soup.select("script")
        if s.get_text().startswith('{"component"')
    ]
    if (
        len(docs) != 1
        or docs[0]["component"] != component
        or not isinstance(docs[0]["props"], dict)
    ):
        raise ValueError("Unsupported Recooty public page state")
    return soup, docs[0]["props"]


class RecootyConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider != "recooty" or not re.fullmatch(TENANT, slug):
            raise ValueError("Invalid Recooty hosted team")
        self.slug = slug
        self.origin = "https://careerspage.io"
        self.board = f"{self.origin}/{slug}"
        self.http = PublicHTTP(client, {"careerspage.io"})

    def path(self, url: str) -> str:
        p = urlsplit(url)
        if (
            p.scheme
            or p.netloc
            or p.query
            or p.fragment
            or not re.fullmatch(rf"/{re.escape(self.slug)}/[a-z0-9-]+", p.path)
        ):
            raise ValueError("Invalid Recooty relative posting link")
        return p.path

    def team(self, props: dict) -> tuple[int, str]:
        team = props["team"]
        if (
            type(team["id"]) is not int
            or team["id"] <= 0
            or team["slug"] != self.slug
            or not isinstance(team["name"], str)
            or not team["name"].strip()
        ):
            raise ValueError("Recooty team identity mismatch")
        return team["id"], team["name"]

    def listings(self, body: bytes) -> tuple[tuple[int, str], dict[int, dict]]:
        soup, props = state(body, "CareersPage/Index")
        employer = self.team(props)
        items = props["job_posts"]
        counts = {
            int(n)
            for n in re.findall(
                r"\b([0-9]+) open positions\b", soup.get_text(" ", strip=True), re.I
            )
        }
        if not isinstance(items, list) or not 0 < len(items) <= 400 or counts != {len(items)}:
            raise ValueError("Recooty collection/visible total missing, empty or incomplete")
        rows = {}
        for row in items:
            identifier = row["id"]
            path = self.path(row["url"])
            anchors = [
                a for a in soup.select("a[href]") if a.get("href") in (path, self.origin + path)
            ]
            if (
                type(identifier) is not int
                or identifier <= 0
                or identifier in rows
                or row["slug"] != path.rsplit("/", 1)[1]
                or not isinstance(row["title"], str)
                or not row["title"].strip()
                or not anchors
                or not any(row["title"] in a.get_text(" ", strip=True) for a in anchors)
            ):
                raise ValueError("Recooty listing ID/title/link mismatch")
            rows[identifier] = row
        if len({r["url"] for r in rows.values()}) != len(rows):
            raise ValueError("Duplicate Recooty source links")
        return employer, rows

    def parse(self, payload: Any) -> list[JobInput]:
        listing, employer, body = payload
        soup, props = state(body, "CareersPage/JobDescription")
        job = props["job"]
        schema = props["json_ld"]
        seo = props["seo"]
        path = self.path(listing["url"])
        url = self.origin + path
        if (
            self.team(props) != employer
            or type(job["id"]) is not int
            or job["id"] != listing["id"]
            or job["slug"] != listing["slug"]
            or job["title"] != listing["title"]
            or job["type"] != "JOB_POST"
            or job["status"] != "OPEN"
            or job["job_board_status"] != "APPROVED"
            or schema["@type"] != "JobPosting"
            or schema["title"] != job["title"]
            or schema["url"] != url
            or schema["hiringOrganization"]["name"] != employer[1]
            or schema["identifier"]["value"] != job["ulid"]
            or seo["canonical_url"] != url
            or not soup.select_one(f'a[href="{path}/apply"]')
        ):
            raise ValueError("Recooty job detail identity, open status or application mismatch")
        for field, label in (
            ("employment_type", "employment_type_label"),
            ("location_type", "location_type_label"),
        ):
            if listing[field] != job[label]:
                raise ValueError("Recooty list/detail employment or workplace changed")
        if listing["location"] != job["location"]["display"]:
            raise ValueError("Recooty list/detail location changed")
        description = text(job["description_html"])
        pay = job["pay"]
        salary = pay if pay["min"] is not None or pay["max"] is not None else None
        return [
            JobInput(
                external_id=str(job["id"]),
                title=job["title"],
                company=employer[1],
                description=description,
                quality_flags=[] if description else ["description_missing"],
                location=job["location"]["display"] or "",
                source_url=url,
                application_url=url + "/apply",
                salary=salary,
                employment_type=job["employment_type_label"],
                remote_status=job["location_type_label"],
                published_at=job["published_at_iso"],
                raw={
                    "listing": listing,
                    "job": {
                        k: v
                        for k, v in job.items()
                        if k
                        in {
                            "id",
                            "ulid",
                            "title",
                            "slug",
                            "type",
                            "description_html",
                            "status",
                            "job_board_status",
                            "department",
                            "employment_type",
                            "employment_type_label",
                            "experience_required",
                            "experience_required_label",
                            "location_type",
                            "location_type_label",
                            "location",
                            "pay",
                            "published_at",
                            "published_at_iso",
                        }
                    },
                    "team": {"id": employer[0], "name": employer[1], "slug": self.slug},
                    "jobposting": schema,
                },
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("Recooty paginated templates unsupported")
        return await self.http.read(self.board)

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)

        async def read(url: str) -> bytes:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        employer, rows = self.listings(await read(self.board))
        jobs = []
        for row in rows.values():
            jobs.extend(
                self.parse((row, employer, await read(self.origin + self.path(row["url"]))))
            )
        if self.listings(await read(self.board)) != (employer, rows):
            raise ValueError("Recooty full roster changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

"""Rippling native public SSR board/job state; no private platform API or browser execution."""

import asyncio
import json
import re
from typing import Any
from uuid import UUID

import httpx
from bs4 import BeautifulSoup
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.connectors.teamtailor import TENANT
from vindex.schemas import Enumeration, JobInput


def page_state(body: bytes) -> tuple[BeautifulSoup, dict]:
    if b"</html>" not in body.lower():
        raise ValueError("Truncated Rippling document")
    soup = BeautifulSoup(body, "html.parser")
    states = soup.select('script#__NEXT_DATA__[type="application/json"]')
    if len(states) != 1:
        raise ValueError("Missing unique Rippling public SSR state")
    data = json.loads(states[0].get_text())["props"]["pageProps"]
    if not isinstance(data, dict):
        raise ValueError("Invalid Rippling public page state")
    return soup, data


class RipplingConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider != "rippling" or not re.fullmatch(TENANT, slug):
            raise ValueError("Invalid Rippling board")
        self.slug = slug
        self.origin = "https://ats.rippling.com"
        self.board_url = f"{self.origin}/{slug}/jobs"
        self.http = PublicHTTP(client, {"ats.rippling.com"})

    def board(self, data: dict) -> dict:
        board = data["apiData"]["jobBoard"]
        if (
            board["boardType"] != "RIPPLING"
            or board["slug"] != self.slug
            or type(board["groupJobsByLocation"]) is not bool
            or board["isTest"] is not False
            or board["boardURL"] != self.board_url
            or not isinstance(board["companyName"], str)
            or not board["companyName"].strip()
        ):
            raise ValueError("Rippling board identity/test-state mismatch")
        return {
            k: board[k]
            for k in (
                "boardType",
                "slug",
                "title",
                "boardURL",
                "companyName",
                "isTest",
                "groupJobsByLocation",
            )
        }

    def listings(self, body: bytes) -> tuple[dict, dict[str, dict]]:
        soup, data = page_state(body)
        board = self.board(data)
        if data["apiData"]["jobBoardSlug"] != self.slug:
            raise ValueError("Rippling career slug mismatch")
        queries = [
            q
            for q in data["dehydratedState"]["queries"]
            if q["queryKey"][:3] == ["board", self.slug, "job-posts"]
        ]
        if len(queries) != 1:
            raise ValueError("Missing unique Rippling public jobs collection")
        query = queries[0]
        key = query["queryKey"]
        if len(key) != 5 or type(key[3]) is not bool or key[3] != board["groupJobsByLocation"]:
            raise ValueError("Unsupported Rippling jobs query")
        params = key[4]
        if (
            params["searchQuery"] != ""
            or params["departments"] != []
            or params["workplaceType"] is not None
            or any(params[k] != "" for k in ("country", "state", "city"))
            or params["page"] != 0
        ):
            raise ValueError("Rippling collection is filtered or not its first page")
        payload = query["state"]["data"]
        items = payload["items"]
        if (
            type(payload["page"]) is not int
            or payload["page"] != 0
            or type(payload["totalPages"]) is not int
            or payload["totalPages"] != 1
            or type(payload["totalItems"]) is not int
            or not isinstance(items, list)
            or not 0 < len(items) == payload["totalItems"] <= 100
            or type(payload["pageSize"]) is not int
            or payload["pageSize"] != params["pageSize"]
            or payload["pageSize"] < len(items)
        ):
            raise ValueError("Rippling partial, paginated, empty or oversized SSR collection")
        rows = {}
        for item in items:
            identifier = item["id"]
            if (
                not isinstance(identifier, str)
                or str(UUID(identifier)) != identifier
                or identifier in rows
            ):
                raise ValueError("Invalid or duplicate Rippling public job UUID")
            path = f"/{self.slug}/jobs/{identifier}"
            anchors = [
                a for a in soup.select("a[href]") if a.get("href") in (path, self.origin + path)
            ]
            if (
                item["url"] != self.origin + path
                or not isinstance(item["name"], str)
                or not item["name"].strip()
                or not any(item["name"].strip() in a.get_text(" ", strip=True) for a in anchors)
            ):
                raise ValueError("Rippling visible jobs and SSR state disagree")
            rows[identifier] = item
        return board, rows

    def parse(self, payload: Any) -> list[JobInput]:
        listing, board, body = payload
        soup, data = page_state(body)
        post = data["apiData"]["jobPost"]
        post_board = post["board"]
        if (
            self.board(data) != board
            or post["uuid"] != listing["id"]
            or post["url"] != listing["url"]
            or post["name"].strip() != listing["name"].strip()
            or post["companyName"] != board["companyName"]
            or post["unlistedFromSearch"] is not False
            or post_board["slug"] != self.slug
            or post_board["isTest"] is not False
            or not any(b.get_text(" ", strip=True) == "Apply now" for b in soup.select("button"))
        ):
            raise ValueError("Rippling detail UUID/title/company/listed-state/application mismatch")
        locations = listing["locations"]
        if not isinstance(locations, list) or not isinstance(post["workLocations"], list):
            raise ValueError("Invalid Rippling work locations")
        if {place["name"] for place in locations} != set(post["workLocations"]):
            raise ValueError("Rippling list/detail locations differ")
        descriptions = post["description"]
        if not isinstance(descriptions, dict) or any(
            v is not None and not isinstance(v, str) for v in descriptions.values()
        ):
            raise ValueError("Unsupported Rippling full-description schema")
        description = "\n\n".join(text(v) for v in descriptions.values() if v)
        flags = [] if description else ["description_missing"]
        if "role" in descriptions and not text(descriptions["role"] or ""):
            flags.append("role_description_missing")
        source_schema = post.get("jsonLd")
        published = source_schema.get("datePosted") if isinstance(source_schema, dict) else None
        ranges = post["payRangeDetails"]
        if not isinstance(ranges, list):
            raise ValueError("Invalid Rippling source pay ranges")
        job_fields = {
            "uuid",
            "name",
            "description",
            "workLocations",
            "department",
            "employmentType",
            "createdOn",
            "url",
            "payRangeDetails",
            "companyName",
            "unlistedFromSearch",
        }
        return [
            JobInput(
                external_id=post["uuid"],
                title=post["name"].strip(),
                company=post["companyName"],
                description=description,
                quality_flags=flags,
                location="; ".join(post["workLocations"]),
                source_url=post["url"],
                application_url=post["url"],
                salary={"ranges": ranges} if ranges else None,
                employment_type=post["employmentType"]["id"]
                if post.get("employmentType")
                else None,
                remote_status="; ".join(
                    dict.fromkeys(p["workplaceType"] for p in locations if p.get("workplaceType"))
                )
                or None,
                published_at=published,
                raw={
                    "listing": listing,
                    "board": board,
                    "job": {k: v for k, v in post.items() if k in job_fields},
                    "source_date_posted": published,
                    "application_entry": "native_apply_button",
                },
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("Rippling multi-page boards unsupported")
        return await self.http.read(self.board_url)

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)

        async def read(url: str) -> bytes:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        board, rows = self.listings(await read(self.board_url))
        jobs = []
        for listing in rows.values():
            jobs.extend(self.parse((listing, board, await read(listing["url"]))))
        if self.listings(await read(self.board_url)) != (board, rows):
            raise ValueError("Rippling complete public collection changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

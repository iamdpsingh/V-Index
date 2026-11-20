"""Gem hosted boards: public read-only GraphQL, full details, roster reconfirmation."""

import asyncio
import re
from datetime import UTC, datetime
from typing import Any

import httpx
from vindex.connectors.http import PublicHTTP
from vindex.connectors.jobboardio import document
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.connectors.teamtailor import TENANT
from vindex.schemas import Enumeration, JobInput

ORIGIN = "https://jobs.gem.com"
API = ORIGIN + "/api/public/graphql/batch"
POST_ID = re.compile(r"[A-Za-z0-9_-]{10,100}")
LIST_QUERY = """query JobBoardList($boardId:String!) {
  oatsExternalJobPostings(boardId:$boardId) { jobPostings {
    extId title locations { name city isoCountry isRemote }
    job { locationType employmentType }
  } }
}"""
DETAIL_QUERY = """query ExternalJobPostingQuery($boardId:String!,$extId:String!) {
  oatsExternalJobPosting(boardId:$boardId,extId:$extId) {
    extId title firstPublishedTsSec descriptionHtml compensationHtml
    jobPostSectionHtml { introHtml outroHtml }
  }
}"""


class GemConnector:
    def __init__(self, slug: str, company: str, client: httpx.AsyncClient):
        if not re.fullmatch(TENANT, slug) or not company.strip():
            raise ValueError("Invalid Gem board")
        self.slug, self.company = slug, company
        self.board = ORIGIN + "/" + slug
        self.http = PublicHTTP(client, {"jobs.gem.com"})

    async def query(
        self, operation: str, query: str, variables: dict, policy: RobotsPolicy
    ) -> dict:
        policy.check(API)
        await asyncio.sleep(policy.delay())
        payload = await self.http.json(
            API,
            method="POST",
            headers={"batch": "true"},
            json_body=[{"operationName": operation, "query": query, "variables": variables}],
        )
        if (
            not isinstance(payload, list)
            or len(payload) != 1
            or not isinstance(payload[0], dict)
            or payload[0].get("errors")
            or not isinstance(payload[0].get("data"), dict)
        ):
            raise ValueError("Gem public query failed or returned partial data")
        return payload[0]["data"]

    async def roster(self, policy: RobotsPolicy) -> dict[str, dict]:
        data = await self.query("JobBoardList", LIST_QUERY, {"boardId": self.slug}, policy)
        board = data.get("oatsExternalJobPostings")
        rows = board.get("jobPostings") if isinstance(board, dict) else None
        if not isinstance(rows, list) or not 0 < len(rows) <= 400:
            raise ValueError("Missing, empty or oversized Gem full collection")
        result = {}
        for row in rows:
            if (
                not isinstance(row, dict)
                or not isinstance(row.get("extId"), str)
                or not POST_ID.fullmatch(row["extId"])
                or row["extId"] in result
                or not isinstance(row.get("title"), str)
                or not row["title"].strip()
                or not isinstance(row.get("locations"), list)
                or not isinstance(row.get("job"), dict)
            ):
                raise ValueError("Invalid or repeated Gem posting")
            result[row["extId"]] = row
        return result

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("Gem uses a full published collection")
        policy = await RobotsPolicy.load(self.http, ORIGIN)
        return await self.roster(policy)

    def parse(self, payload: tuple[dict, dict | None]) -> list[JobInput]:
        listing, detail = payload
        if (
            not isinstance(detail, dict)
            or detail.get("extId") != listing["extId"]
            or detail.get("title") != listing["title"]
        ):
            raise ValueError("Gem listing/detail identity mismatch")
        sections = detail.get("jobPostSectionHtml") or {}
        if not isinstance(sections, dict) or not isinstance(detail.get("descriptionHtml"), str):
            raise ValueError("Missing Gem description fields")
        parts = [
            sections.get("introHtml"),
            detail["descriptionHtml"],
            detail.get("compensationHtml"),
            sections.get("outroHtml"),
        ]
        if any(part is not None and not isinstance(part, str) for part in parts):
            raise ValueError("Malformed Gem description section")
        description = "\n\n".join(text(part) for part in parts if part and text(part))
        if not text(detail["descriptionHtml"]):
            raise ValueError("Missing Gem role description")
        locations = []
        for place in listing["locations"]:
            if not isinstance(place, dict) or not isinstance(place.get("name"), str):
                raise ValueError("Malformed Gem job location")
            if place["name"] and place["name"] not in locations:
                locations.append(place["name"])
        employment = listing["job"].get("employmentType")
        workplace = listing["job"].get("locationType")
        if any(v is not None and not isinstance(v, str) for v in (employment, workplace)):
            raise ValueError("Malformed Gem employment metadata")
        workplace_map = {"REMOTE": "Remote", "IN_OFFICE": "On-site", "HYBRID": "Hybrid"}
        flags = ["workplace_type_unmapped"] if workplace and workplace not in workplace_map else []
        timestamp = detail.get("firstPublishedTsSec")
        published = None
        if timestamp is not None:
            if (
                isinstance(timestamp, bool)
                or not isinstance(timestamp, (int, float))
                or timestamp <= 0
            ):
                raise ValueError("Invalid Gem publication timestamp")
            published = datetime.fromtimestamp(timestamp, UTC)
        compensation = detail.get("compensationHtml")
        url = self.board + "/" + listing["extId"]
        return [
            JobInput(
                external_id=listing["extId"],
                title=listing["title"],
                company=self.company,
                description=description,
                location="; ".join(locations),
                source_url=url,
                application_url=url,
                employment_type=employment,
                remote_status=workplace_map.get(workplace),
                quality_flags=flags,
                salary={"text": text(compensation)}
                if compensation and text(compensation)
                else None,
                published_at=published,
                raw={
                    "listing": listing,
                    "detail": detail,
                    "application_entry": "Original Gem hosted posting containing its application flow",
                },
            )
        ]

    async def read_page(self, url: str, policy: RobotsPolicy) -> bytes:
        policy.check(url)
        await asyncio.sleep(policy.delay())
        return await self.http.read(url)

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, ORIGIN)
        soup = document(await self.read_page(self.board, policy))
        expected = self.company + " Careers"
        if not soup.title or soup.title.get_text().strip().casefold() != expected.casefold():
            raise ValueError("Gem board/company identity mismatch")
        roster = await self.roster(policy)
        jobs = []
        for identifier, listing in roster.items():
            data = await self.query(
                "ExternalJobPostingQuery",
                DETAIL_QUERY,
                {"boardId": self.slug, "extId": identifier},
                policy,
            )
            jobs.extend(self.parse((listing, data.get("oatsExternalJobPosting"))))
            posting = await self.read_page(self.board + "/" + identifier, policy)
            page = document(posting)
            if (
                not page.title
                or page.title.get_text().strip() != listing["title"]
                or identifier.encode() not in posting
            ):
                raise ValueError("Gem hosted posting identity mismatch")
        if await self.roster(policy) != roster:
            raise ValueError("Gem published collection changed during extraction")
        return Enumeration(jobs=jobs, complete=True)

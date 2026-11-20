"""Dayforce public candidate boards with their native anonymous CSRF handshake."""

import asyncio
import json
import re
from typing import Any

import httpx
from vindex.connectors.http import PublicHTTP
from vindex.connectors.jobboardio import document
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.schemas import Enumeration, JobInput

ORIGIN = "https://jobs.dayforcehcm.com"
BOARDS = {
    "mew": ("en-US", "CANDIDATEPORTAL", "MAAS Energy Works"),
    "silklaser": ("en-AU", "CANDIDATEPORTAL", "SILK Laser Clinics"),
}
PAGE_SIZE = 25
MAX_JOBS = 400


class DayforceConnector:
    def __init__(self, tenant: str, client: httpx.AsyncClient):
        if tenant not in BOARDS:
            raise ValueError("Unknown Dayforce public board")
        self.tenant = tenant
        self.locale, self.code, self.company = BOARDS[tenant]
        self.board = f"{ORIGIN}/{self.locale}/{tenant}/{self.code}"
        self.api = f"{ORIGIN}/api/geo/{tenant}/jobposting/search"
        self.http = PublicHTTP(client, {"jobs.dayforcehcm.com"})
        self.csrf: str | None = None

    async def read(self, url: str, policy: RobotsPolicy) -> bytes:
        policy.check(url)
        await asyncio.sleep(policy.delay())
        return await self.http.read(url)

    async def anonymous_csrf(self, policy: RobotsPolicy) -> None:
        # A fresh anonymous token/cookie pair, as issued to ordinary public visitors.
        # No login, owner cookie, CAPTCHA workaround or forged token is used.
        payload = json.loads(await self.read(ORIGIN + "/api/auth/csrf", policy))
        token = payload.get("csrfToken") if isinstance(payload, dict) else None
        if not isinstance(token, str) or not re.fullmatch(r"[a-f0-9]{64}", token):
            raise ValueError("Missing Dayforce anonymous visitor CSRF token")
        self.csrf = token

    def state(self, body: bytes) -> tuple[dict, list[dict]]:
        soup = document(body)
        nodes = soup.select("script#__NEXT_DATA__")
        if len(nodes) != 1:
            raise ValueError("Missing Dayforce public page state")
        payload = json.loads(nodes[0].get_text())
        props = payload["props"]["pageProps"]
        visitor = props.get("session")
        if visitor is not None and not (
            isinstance(visitor, dict)
            and visitor.get("status") == "unauthenticated"
            and visitor.get("data") == {"user": {}}
        ):
            raise ValueError("Dayforce extraction requires an anonymous public visitor")
        queries = props["dehydratedState"]["queries"]
        if not isinstance(queries, list):
            raise ValueError("Missing Dayforce public query state")
        sites = [
            q["state"].get("data")
            for q in queries
            if q.get("queryKey", [None])[0] == "site-info"
            and q.get("state", {}).get("status") == "success"
        ]
        if len(sites) != 1 or not isinstance(sites[0], dict):
            raise ValueError("Missing Dayforce career site identity")
        site = sites[0]
        if (
            site.get("clientNamespace") != self.tenant
            or str(site.get("jobBoardCode", "")).casefold() != self.code.casefold()
            or site.get("cultureCode") != self.locale
            or type(site.get("jobBoardId")) is not int
            or site["jobBoardId"] <= 0
        ):
            raise ValueError("Dayforce public career site identity mismatch")
        return site, queries

    async def search(self, offset: int, policy: RobotsPolicy) -> Any:
        if self.csrf is None:
            await self.anonymous_csrf(policy)
        assert self.csrf is not None
        policy.check(self.api)
        await asyncio.sleep(policy.delay())
        return await self.http.json(
            self.api,
            method="POST",
            headers={"X-CSRF-TOKEN": self.csrf},
            json_body={
                "clientNamespace": self.tenant,
                "jobBoardCode": self.code,
                "cultureCode": self.locale,
                "distanceUnit": 1,
                "exactLocationOnly": False,
                "paginationStart": offset,
            },
        )

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor < 0 or cursor % PAGE_SIZE:
            raise ValueError("Invalid Dayforce native page offset")
        policy = await RobotsPolicy.load(self.http, ORIGIN)
        return await self.search(cursor, policy)

    async def roster(self, site: dict, policy: RobotsPolicy) -> dict[str, dict]:
        result = {}
        expected = None
        offset = 0
        while True:
            data = await self.search(offset, policy)
            if not isinstance(data, dict):
                raise ValueError("Malformed Dayforce public search")
            total, rows = data.get("maxCount"), data.get("jobPostings")
            if (
                type(total) is not int
                or not 0 < total <= MAX_JOBS
                or not isinstance(rows, list)
                or data.get("offset") != offset
                or data.get("count") != len(rows)
                or len(rows) != min(PAGE_SIZE, total - offset)
            ):
                raise ValueError("Incomplete or oversized Dayforce public page")
            if expected is not None and total != expected:
                raise ValueError("Dayforce total changed during pagination")
            expected = total
            for row in rows:
                if (
                    not isinstance(row, dict)
                    or type(row.get("jobPostingId")) is not int
                    or row["jobPostingId"] <= 0
                    or row.get("clientNamespace") != self.tenant
                    or row.get("jobBoardId") != site["jobBoardId"]
                    or not isinstance(row.get("jobTitle"), str)
                    or not row["jobTitle"].strip()
                ):
                    raise ValueError("Dayforce listing scope/identity mismatch")
                identifier = str(row["jobPostingId"])
                if identifier in result:
                    raise ValueError("Dayforce repeated a posting across pages")
                result[identifier] = row
            offset += len(rows)
            if offset == total:
                break
        return result

    def parse(self, payload: tuple[dict, bytes]) -> list[JobInput]:
        listing, body = payload
        site, queries = self.state(body)
        details = [
            q["state"].get("data")
            for q in queries
            if q.get("queryKey", [None])[0] == "jobs"
            and q.get("state", {}).get("status") == "success"
        ]
        if len(details) != 1 or not isinstance(details[0], dict):
            raise ValueError("Missing Dayforce full posting")
        row = details[0]
        if (
            row.get("jobPostingId") != listing["jobPostingId"]
            or row.get("jobReqId") != listing.get("jobReqId")
            or row.get("jobTitle") != listing["jobTitle"]
            or row.get("isInternal") is not False
            or row.get("postingStatus") != 1
            or type(row.get("jobApplicationTemplateId")) is not int
            or row["jobApplicationTemplateId"] <= 0
            or site.get("enableApplyWithoutAccount") is not True
        ):
            raise ValueError("Dayforce posting identity or public application mismatch")
        content = row.get("jobPostingContent")
        if not isinstance(content, dict) or not isinstance(content.get("jobDescription"), str):
            raise ValueError("Missing Dayforce full role description")
        parts = [
            content.get(k)
            for k in ("jobDescriptionHeader", "jobDescription", "jobDescriptionFooter")
        ]
        if any(p is not None and not isinstance(p, str) for p in parts) or not text(
            content["jobDescription"]
        ):
            raise ValueError("Malformed or empty Dayforce full role description")
        description = "\n\n".join(text(p) for p in parts if p and text(p))
        locations = row.get("postingLocations")
        if not isinstance(locations, list):
            raise ValueError("Malformed Dayforce posting locations")
        places = []
        for loc in locations:
            if not isinstance(loc, dict) or not isinstance(loc.get("formattedAddress"), str):
                raise ValueError("Missing Dayforce native location")
            if loc["formattedAddress"] and loc["formattedAddress"] not in places:
                places.append(loc["formattedAddress"])
        attrs = row.get("jobPostingAttributes")
        if not isinstance(attrs, list):
            raise ValueError("Malformed Dayforce job attributes")
        values: dict[str, Any] = {}
        for attr in attrs:
            if not isinstance(attr, dict) or not isinstance(attr.get("name"), str):
                raise ValueError("Malformed Dayforce job attribute")
            if attr["name"] in values and values[attr["name"]] != attr.get("value"):
                raise ValueError("Conflicting Dayforce job attributes")
            values[attr["name"]] = attr.get("value")
        salary = {
            k: values[k]
            for k in ("HiringMinRate", "HiringMaxRate", "HiringRate")
            if values.get(k) not in (None, "")
        }
        if salary:
            salary.update(
                pay_type=values.get("PayType"), currency_region=row.get("isoCurrencyRegion")
            )
        identifier = str(row["jobPostingId"])
        url = self.board + "/jobs/" + identifier
        return [
            JobInput(
                external_id=identifier,
                title=row["jobTitle"],
                company=self.company,
                description=description,
                location="; ".join(places),
                source_url=url,
                application_url=url + "/apply",
                salary=salary or None,
                employment_type=values.get("EmploymentIndicator") or None,
                remote_status="Remote option" if row.get("hasVirtualLocation") is True else None,
                published_at=row.get("postingStartTimestampUTC"),
                raw={
                    "content": content,
                    "attributes": attrs,
                    "locations": locations,
                    "posting_expiry": row.get("postingExpiryTimestampUTC"),
                    "application_entry": "Native public Dayforce application route",
                },
            )
        ]

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, ORIGIN)
        site, _ = self.state(await self.read(self.board, policy))
        before = await self.roster(site, policy)
        jobs = []
        for identifier, listing in before.items():
            url = self.board + "/jobs/" + identifier
            jobs.extend(self.parse((listing, await self.read(url, policy))))
        if await self.roster(site, policy) != before:
            raise ValueError("Dayforce full roster changed during extraction")
        return Enumeration(jobs=jobs, complete=True)

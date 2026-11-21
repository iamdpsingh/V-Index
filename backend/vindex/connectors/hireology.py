"""Hireology explicitly public careers API; never uses frontend tokens or private APIs."""

import asyncio
import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
from bs4 import BeautifulSoup
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.connectors.teamtailor import TENANT
from vindex.schemas import Enumeration, JobInput

FIELDS = (
    "id",
    "name",
    "created_at",
    "status",
    "employment_status",
    "job_description",
    "locations",
    "remote",
    "blind_posted",
    "job_family",
    "career_site_url",
    "application_path",
    "career_site_path",
    "organization",
    "compensation",
)


class HireologyConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider != "hireology" or not re.fullmatch(TENANT, slug):
            raise ValueError("Invalid Hireology careers path")
        self.slug = slug
        self.origin = "https://careers.hireology.com"
        self.api = "https://api.hireology.com"
        self.http = PublicHTTP(client, {"careers.hireology.com", "api.hireology.com"})

    def bootstrap(self, body: bytes) -> dict:
        if b"</html>" not in body.lower():
            raise ValueError("Truncated Hireology career page")
        soup = BeautifulSoup(body, "html.parser")
        values = []
        for script in soup.select("script:not([src])"):
            code = script.get_text()
            for matched in re.finditer(r"var startingData\s*=\s*", code):
                value, _ = json.JSONDecoder().raw_decode(code[matched.end() :])
                values.append(value)
        if not values:
            return self.rendered_board(soup)
        if len(values) != 1:
            raise ValueError("Missing unique Hireology public career bootstrap")
        value = values[0]
        if (
            value["apiUrl"] != self.api + "/v2"
            or value["appUrl"] != self.origin
            or value["careersPath"] != self.slug
            or value["page"] is not None
            or value["pageSize"] is not None
            or not isinstance(value["filters"], dict)
            or not set(value["filters"]) <= {"location", "job_family", "store"}
            or any(not isinstance(options, list) for options in value["filters"].values())
        ):
            raise ValueError("Hireology public bootstrap host/filter/page mismatch")
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        if not title.startswith("Jobs for ") or not title.removeprefix("Jobs for ").strip():
            raise ValueError("Missing named Hireology employer")
        # Explicitly discard apiToken, forms, tracking and all unrelated bootstrap state.
        return {
            "company": title.removeprefix("Jobs for "),
            "careersPath": self.slug,
            "pageSize": 10,
        }

    def rendered_board(self, soup: BeautifulSoup) -> dict:
        """Current native SSR board: bind the complete visible roster to the public API."""
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        canonical = soup.select('link[rel="canonical"]')
        headings = [node.get_text(" ", strip=True) for node in soup.select("h1")]
        if (
            len(canonical) != 1
            or canonical[0].get("href") != self.origin + "/" + self.slug
            or headings != ["Available Jobs"]
            or not title.startswith("Jobs for ")
            or not title.removeprefix("Jobs for ").strip()
        ):
            raise ValueError("Unrecognized Hireology rendered board identity")
        jobs = {}
        for anchor in soup.select('a[href*="/description"]'):
            href = anchor.get("href")
            if not isinstance(href, str):
                raise ValueError("Invalid Hireology native listing link")
            parsed = urlsplit(href)
            match = re.fullmatch(
                r"/" + re.escape(self.slug) + r"/([1-9][0-9]*)/description", parsed.path
            )
            query = parse_qs(parsed.query, keep_blank_values=True)
            if (
                parsed.scheme != "https"
                or parsed.netloc != "careers.hireology.com"
                or parsed.fragment
                or match is None
                or any(
                    query.get(key) not in (None, [value])
                    for key, value in {"ref": "career_site", "ref_m": "api"}.items()
                )
                or not set(query) <= {"ref", "ref_m"}
            ):
                raise ValueError("Hireology rendered listing host/path/query mismatch")
            identifier = int(match.group(1))
            name = anchor.get_text(" ", strip=True)
            if identifier in jobs or not name:
                raise ValueError("Duplicate or unnamed Hireology rendered listing")
            jobs[identifier] = name
        if not 0 < len(jobs) <= 10:
            raise ValueError("Hireology rendered roster empty or beyond verified page budget")
        return {
            "company": title.removeprefix("Jobs for "),
            "careersPath": self.slug,
            "pageSize": 10,
            "native_jobs": jobs,
        }

    def public_row(self, row: dict, board: dict) -> dict:
        identifier = row["id"]
        org = row["organization"]
        if (
            type(identifier) is not int
            or identifier <= 0
            or row["status"] != "Open"
            or row["blind_posted"] is not False
            or type(row["remote"]) is not bool
            or type(org["id"]) is not int
            or org["id"] <= 0
            or org["name"] != board["company"]
            or not isinstance(row["name"], str)
            or not row["name"].strip()
            or row["career_site_path"] != f"/{self.slug}/{identifier}/description"
            or row["career_site_url"] != self.origin + row["career_site_path"]
            or row["application_path"] != f"/careers/{identifier}/application"
            or not isinstance(row["job_description"], str)
            or not isinstance(row["locations"], list)
        ):
            raise ValueError("Hireology public job lifecycle/employer/native link mismatch")
        return {k: row[k] for k in FIELDS}

    def listings(self, payload: Any, board: dict) -> dict[int, dict]:
        rows = payload["data"]
        if (
            type(payload["count"]) is not int
            or type(payload["page"]) is not int
            or payload["page"] != 1
            or type(payload["page_size"]) is not int
            or payload["page_size"] != board["pageSize"]
            or not isinstance(rows, list)
            or not 0 < len(rows) == payload["count"] <= payload["page_size"]
        ):
            raise ValueError("Hireology partial, empty or multipage public collection")
        result = {}
        for row in rows:
            job = self.public_row(row, board)
            if job["id"] in result:
                raise ValueError("Duplicate Hireology public job ID")
            result[job["id"]] = job
        if "native_jobs" in board and board["native_jobs"] != {
            identifier: row["name"] for identifier, row in result.items()
        }:
            raise ValueError("Hireology rendered roster and complete public API disagree")
        if len({r["organization"]["id"] for r in result.values()}) != 1:
            raise ValueError("Mixed Hireology organization IDs")
        return result

    def parse(self, payload: Any) -> list[JobInput]:
        listing, board, data = payload
        row = self.public_row(data["data"], board)
        if row != listing:
            raise ValueError("Hireology full listed/detail record changed")
        places = []
        for location in row["locations"]:
            places.append(
                ", ".join(
                    dict.fromkeys(
                        location[k]
                        for k in ("address", "city", "state", "zip_code")
                        if location.get(k)
                    )
                )
            )
        compensation = row["compensation"]
        values = []
        for field in ("comp_single_amount", "comp_range_min", "comp_range_max"):
            amount = compensation.get(field)
            if amount is None:
                continue
            try:
                number = Decimal(str(amount))
            except InvalidOperation as error:
                raise ValueError("Malformed Hireology source compensation") from error
            if not number.is_finite() or number < 0:
                raise ValueError("Invalid Hireology source compensation")
            values.append(number)
        description = text(row["job_description"])
        return [
            JobInput(
                external_id=str(row["id"]),
                title=row["name"],
                company=board["company"],
                description=description,
                quality_flags=[] if description else ["description_missing"],
                location="; ".join(dict.fromkeys(places)),
                source_url=row["career_site_url"],
                application_url=row["career_site_url"],
                employment_type=row["employment_status"],
                remote_status="remote" if row["remote"] else None,
                salary={"source_compensation": compensation}
                if any(v > 0 for v in values)
                else None,
                raw={"job": row, "board": board},
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("Hireology paginated public collections unsupported")
        return await self.http.json(self.api + "/v2/public/careers/" + self.slug)

    async def discover(self) -> Enumeration:
        policies = {}
        for origin in (self.origin, self.api):
            policies[origin] = await RobotsPolicy.load(self.http, origin)

        async def read(origin: str, path: str, as_json: bool = False) -> Any:
            policy = policies[origin]
            policy.check(origin + path)
            await asyncio.sleep(policy.delay())
            return (
                await self.http.json(origin + path)
                if as_json
                else await self.http.read(origin + path)
            )

        board = self.bootstrap(await read(self.origin, "/" + self.slug))
        path = "/v2/public/careers/" + self.slug
        rows = self.listings(await read(self.api, path, True), board)
        jobs = []
        for identifier, listing in rows.items():
            jobs.extend(
                self.parse(
                    (
                        listing,
                        board,
                        await read(self.api, f"/v2/public/careers/jobs/{identifier}", True),
                    )
                )
            )
        if (
            self.bootstrap(await read(self.origin, "/" + self.slug)) != board
            or self.listings(await read(self.api, path, True), board) != rows
        ):
            raise ValueError(
                "Hireology complete public board/collection changed during enumeration"
            )
        return Enumeration(jobs=jobs, complete=True)

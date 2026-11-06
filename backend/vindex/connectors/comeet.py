"""Comeet native public roster and documented Careers API details, never employee APIs."""

import asyncio
import json
import re
from typing import Any
from urllib.parse import urlencode, urlsplit

import httpx
from bs4 import BeautifulSoup
from vindex.connectors.http import PublicHTTP, UpstreamStatusError
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.schemas import Enumeration, JobInput

TENANT = r"[a-z0-9][a-z0-9_-]{0,84}"
UID = r"[0-9A-Fa-f]{2}\.[0-9A-Fa-f]{3}"
POSITION_UID = rf"{UID}(?:-{UID})?"
FIELDS = (
    "name",
    "department",
    "employment_type",
    "experience_level",
    "uid",
    "internal_use_custom_id",
    "time_updated",
    "company_name",
    "is_internal",
    "workplace_type",
    "url_comeet_hosted_page",
    "url_recruit_hosted_page",
    "url_active_page",
    "url_detected_page",
)


def document(body: bytes) -> BeautifulSoup:
    if b"</html>" not in body.lower():
        raise ValueError("Truncated Comeet public document")
    return BeautifulSoup(body, "html.parser")


def variable(soup: BeautifulSoup, name: str) -> Any:
    values = []
    for script in soup.select("script:not([src])"):
        code = script.get_text()
        for matched in re.finditer(rf"(?m)^\s*{re.escape(name)}\s*=\s*", code):
            value, _ = json.JSONDecoder().raw_decode(code[matched.end() :])
            values.append(value)
    if len(values) != 1:
        raise ValueError("Missing unique Comeet public data assignment")
    return values[0]


class ComeetConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        parts = slug.split("~")
        if (
            provider != "comeet"
            or len(parts) != 2
            or not re.fullmatch(TENANT, parts[0])
            or not re.fullmatch(UID, parts[1])
            or parts[1].upper() == "E5.007"
        ):
            raise ValueError("Invalid Comeet public company or documented vendor sandbox")
        self.slug, self.uid = parts
        self.origin = "https://www.comeet.com"
        self.url = f"{self.origin}/jobs/{self.slug}/{self.uid}"
        self.http = PublicHTTP(client, {"www.comeet.com"})

    def public_row(self, row: dict, board: dict) -> dict:
        identifier = row["uid"]
        url = row["url_comeet_hosted_page"]
        if (
            not isinstance(identifier, str)
            or not re.fullmatch(POSITION_UID, identifier)
            or row["is_internal"] is not False
            or row["company_name"] != board["name"]
            or not isinstance(row["name"], str)
            or not row["name"].strip()
            or not isinstance(url, str)
            or not re.fullmatch(re.escape(self.url) + r"/[a-z0-9_-]+/" + re.escape(identifier), url)
            or not isinstance(row["location"], dict)
        ):
            raise ValueError("Comeet public row employer/UID/internal-state/native link mismatch")
        if "-" in identifier and row["location"].get("location_uid") != identifier.split("-", 1)[1]:
            raise ValueError("Comeet location-specific posting UID/location mismatch")
        result = {k: row.get(k) for k in FIELDS}
        for key in ("url_recruit_hosted_page", "url_active_page", "url_detected_page"):
            value = result[key]
            if value:
                parsed = urlsplit(value)
                if (
                    parsed.scheme != "https"
                    or not parsed.hostname
                    or parsed.username
                    or parsed.password
                    or parsed.port not in (None, 443)
                ):
                    raise ValueError("Invalid Comeet attributed source link")
        result["location"] = {
            k: row["location"].get(k)
            for k in (
                "name",
                "country",
                "city",
                "state",
                "postal_code",
                "street_name",
                "street_number",
                "location_uid",
                "is_remote",
            )
        }
        return result

    def listings(self, body: bytes) -> tuple[dict, dict[str, dict], str]:
        soup = document(body)
        company = variable(soup, "COMPANY_DATA")
        if (
            company["company_uid"] != self.uid
            or company["slug"] != self.slug
            or not isinstance(company["name"], str)
            or not company["name"].strip()
            or company["url_comeet_hosted_page"] != self.url
            or not isinstance(company["token"], str)
            or not re.fullmatch(r"[A-Fa-f0-9]{16,100}", company["token"])
        ):
            raise ValueError("Comeet native public company identity mismatch")
        board = {k: company[k] for k in ("name", "company_uid", "slug", "url_comeet_hosted_page")}
        rows = variable(soup, "COMPANY_POSITIONS_DATA")
        if not isinstance(rows, list) or not 0 < len(rows) <= 200:
            raise ValueError("Comeet empty or oversized public collection")
        result = {}
        for row in rows:
            value = self.public_row(row, board)
            if value["uid"] in result:
                raise ValueError("Duplicate Comeet public position UID")
            result[value["uid"]] = value
        # Public browser Careers read token is in-memory only; never return it as raw evidence.
        return board, result, company["token"]

    def parse(self, payload: Any) -> list[JobInput]:
        listing, board, data = payload
        row = self.public_row(data, board)
        differing = sorted(k for k in row if k != "internal_use_custom_id" and row[k] != listing[k])
        if differing:
            raise ValueError(
                f"Comeet {listing['uid']} listed/detail fields differ: " + ", ".join(differing)
            )
        details = data["details"]
        if not isinstance(details, list) or not details:
            raise ValueError("Missing Comeet full public description sections")
        orders = set()
        sections = []
        for item in details:
            if (
                not isinstance(item["name"], str)
                or (item["value"] is not None and not isinstance(item["value"], str))
                or type(item["order"]) is not int
                or item["order"] in orders
            ):
                raise ValueError(
                    f"Comeet {row['uid']} malformed detail section: name={item.get('name')!r}, order={item.get('order')!r}, value_type={type(item.get('value')).__name__}"
                )
            orders.add(item["order"])
            sections.append({k: item[k] for k in ("name", "value", "order")})
        sections.sort(key=lambda item: item["order"])
        description = "\n\n".join(
            text(s["value"]) for s in sections if s["value"] is not None and text(s["value"])
        )
        salaries = [
            text(s["value"])
            for s in sections
            if s["name"].strip().lower() in {"salary", "compensation", "salary range"}
            and s["value"] is not None
            and text(s["value"])
        ]
        location = row["location"]
        labels = [
            location[k]
            for k in ("name", "city", "state", "postal_code", "country")
            if location.get(k)
        ]
        if row["employment_type"] is not None and not isinstance(row["employment_type"], str):
            raise ValueError("Unexpected Comeet source employment label")
        if row["workplace_type"] is not None and not isinstance(row["workplace_type"], str):
            raise ValueError("Unexpected Comeet source workplace label")
        return [
            JobInput(
                external_id=row["uid"],
                title=row["name"],
                company=board["name"],
                description=description,
                quality_flags=(["description_missing"] if not description else [])
                + (
                    ["description_section_missing"]
                    if any(s["value"] is None for s in sections)
                    else []
                ),
                location="; ".join(dict.fromkeys(labels)),
                source_url=row["url_comeet_hosted_page"],
                application_url=row["url_comeet_hosted_page"],
                employment_type=row["employment_type"],
                remote_status=row["workplace_type"],
                salary={"text": "; ".join(salaries)} if salaries else None,
                published_at=data.get("time_published"),
                raw={
                    "listing": listing,
                    "job": row,
                    "board": board,
                    "time_published_original": data.get("time_published"),
                    "detail_sections": sections,
                },
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("Comeet alternate pagination unsupported")
        return await self.http.read(self.url)

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)

        async def read(url: str) -> bytes:
            policy.check(url)
            await asyncio.sleep(policy.delay(baseline=2.0))
            return await self.http.read(url)

        board, rows, token = self.listings(await read(self.url))
        jobs = []
        for identifier, listing in rows.items():
            url = (
                f"{self.origin}/careers-api/2.0/company/{self.uid}/positions/{identifier}?"
                + urlencode({"token": token, "details": "true"})
            )
            try:
                body = await read(url)
            except httpx.HTTPStatusError as error:
                raise ValueError(
                    f"Comeet public detail HTTP {error.response.status_code}"
                ) from None
            except httpx.TransportError:
                raise ValueError("Comeet public detail transport failure") from None
            except UpstreamStatusError:
                raise
            except ValueError as error:
                # PublicHTTP/policy messages have no URL; discard a credential-bearing cause.
                raise ValueError(str(error)) from None
            jobs.extend(self.parse((listing, board, json.loads(body))))
        final_board, final_rows, _ = self.listings(await read(self.url))
        if (final_board, final_rows) != (board, rows):
            raise ValueError("Comeet complete public roster changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

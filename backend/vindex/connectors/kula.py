"""Kula public rendered board and JobPosting pages; parse data without executing scripts."""

import asyncio
import json
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.connectors.teamtailor import TENANT
from vindex.schemas import Enumeration, JobInput


def document(body: bytes) -> BeautifulSoup:
    if b"</html>" not in body.lower():
        raise ValueError("Truncated Kula document")
    return BeautifulSoup(body, "html.parser")


def public_jobs(soup: BeautifulSoup) -> list[dict]:
    chunks = []
    decoder = json.JSONDecoder()
    for script in soup.select("script"):
        code = script.get_text()
        for matched in re.finditer(r"self\.__next_f\.push\(", code):
            value, _ = decoder.raw_decode(code[matched.end() :])
            if isinstance(value, list) and len(value) == 2 and value[0] == 1:
                if not isinstance(value[1], str):
                    raise ValueError("Invalid Kula public Flight data")
                chunks.append(value[1])
    candidates = []

    def walk(value):
        if isinstance(value, dict):
            if "jobs" in value:
                candidates.append(value["jobs"])
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    stream = "".join(chunks).encode("utf-8")
    offset = 0
    while offset < len(stream):
        header = re.match(rb"[0-9a-f]*:", stream[offset:])
        if header is None:
            raise ValueError("Malformed Kula Flight record boundary")
        offset += header.end()
        if stream[offset : offset + 1] == b"T":
            size = re.match(rb"T([0-9a-f]+),", stream[offset:])
            if size is None:
                raise ValueError("Invalid Kula Flight text length")
            offset += size.end() + int(size[1], 16)
            if offset > len(stream):
                raise ValueError("Truncated Kula Flight text")
            continue
        end = stream.find(b"\n", offset)
        if end < 0:
            raise ValueError("Truncated Kula Flight record")
        record = stream[offset:end]
        if record.startswith((b"[", b"{")):
            walk(json.loads(record))
        offset = end + 1
    if not candidates or any(value != candidates[0] for value in candidates):
        raise ValueError("Missing or conflicting Kula public job collection")
    rows = candidates[0]
    if not isinstance(rows, list) or not 0 < len(rows) <= 400:
        raise ValueError("Empty or oversized Kula collection")
    return rows


class KulaConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider != "kula" or not re.fullmatch(TENANT, slug):
            raise ValueError("Invalid Kula hosted board")
        self.slug = slug
        self.origin = "https://careers.kula.ai"
        self.url = self.origin + "/" + slug
        self.http = PublicHTTP(client, {"careers.kula.ai"})

    def listings(self, body: bytes) -> tuple[str, dict[str, dict]]:
        soup = document(body)
        orgs = [json.loads(s.get_text()) for s in soup.select('script[type="application/ld+json"]')]
        orgs = [o for o in orgs if isinstance(o, dict) and o.get("@type") == "Organization"]
        if (
            len(orgs) != 1
            or not isinstance(orgs[0].get("name"), str)
            or not orgs[0]["name"].strip()
        ):
            raise ValueError("Missing named Kula employer")
        company = orgs[0]["name"].strip()
        paths = {}
        for anchor in soup.select("a[href]"):
            path = str(anchor["href"])
            if path.startswith("/" + self.slug + "/"):
                matched = re.fullmatch(rf"/{re.escape(self.slug)}/([1-9][0-9]*)-[a-z0-9-]+", path)
                if not matched or matched[1] in paths:
                    raise ValueError("Invalid or duplicate Kula visible job path")
                paths[matched[1]] = path
        result = {}
        accounts = set()
        for row in public_jobs(soup):
            identifier = row["id"]
            if (
                type(identifier) is not int
                or identifier <= 0
                or str(identifier) not in paths
                or paths[str(identifier)] in result
                or row["listed"] is not True
                or row["on_career_page"] is not True
                or row["is_confidential"] is not False
                or row["kind"] not in {"external", "internal_and_external"}
                or not isinstance(row["title"], str)
                or not row["title"].strip()
                or type(row["account_id"]) is not int
                or row["account_id"] <= 0
            ):
                raise ValueError("Kula public visibility, ID or identity mismatch")
            accounts.add(row["account_id"])
            ats = row["ats_job"]
            result[paths[str(identifier)]] = {
                k: row[k]
                for k in (
                    "id",
                    "account_id",
                    "title",
                    "listed",
                    "kind",
                    "is_confidential",
                    "on_career_page",
                    "launch_at",
                    "end_at",
                )
            }
            result[paths[str(identifier)]]["ats_job"] = {
                k: ats[k] for k in ("workplace", "employment_type", "work_type_name", "offices")
            }
        if len(accounts) != 1 or len(result) != len(paths):
            raise ValueError("Kula incomplete or mixed-account collection")
        return company, result

    def parse(self, payload: Any) -> list[JobInput]:
        path, listing, company, body = payload
        soup = document(body)
        docs = [json.loads(s.get_text()) for s in soup.select('script[type="application/ld+json"]')]
        docs = [d for d in docs if isinstance(d, dict) and d.get("@type") == "JobPosting"]
        if len(docs) != 1:
            raise ValueError("Missing unique Kula JobPosting")
        row = docs[0]
        canonical = soup.select('link[rel="canonical"]')
        heading = soup.select("h1")
        buttons = {b.get_text(" ", strip=True) for b in soup.select("button")}
        if (
            row["title"].strip() != listing["title"].strip()
            or str(row["identifier"]["value"]) != str(listing["id"])
            or row["hiringOrganization"]["name"].strip() != company
            or len(canonical) != 1
            or canonical[0].get("href") != self.origin + path
            or len(heading) != 1
            or heading[0].get_text(" ", strip=True) != listing["title"].strip()
            or "Apply for this position" not in buttons
            or "Application form" not in buttons
            or row.get("directApply") is not True
        ):
            raise ValueError("Kula detail/application identity mismatch")
        description = text(row["description"])
        ats = listing["ats_job"]
        offices = ats["offices"]
        if not isinstance(offices, list) or any(
            not isinstance(o.get("location"), str) for o in offices
        ):
            raise ValueError("Invalid Kula locations")
        employment = row.get("employmentType")
        if isinstance(employment, list):
            employment = ", ".join(employment)
        return [
            JobInput(
                external_id=str(listing["id"]),
                title=listing["title"].strip(),
                company=company,
                description=description,
                quality_flags=[] if description else ["description_missing"],
                location="; ".join(dict.fromkeys(o["location"] for o in offices)),
                source_url=self.origin + path,
                application_url=self.origin + path,
                employment_type=employment or ats["work_type_name"],
                remote_status=ats["workplace"],
                salary=row.get("baseSalary"),
                published_at=row.get("datePosted"),
                raw={"listing": listing, "jobposting": row},
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("Kula pagination unsupported")
        return await self.http.read(self.url)

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)

        async def read(url: str) -> bytes:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        company, rows = self.listings(await read(self.url))
        jobs = []
        for path, listing in rows.items():
            jobs.extend(self.parse((path, listing, company, await read(self.origin + path))))
        if self.listings(await read(self.url)) != (company, rows):
            raise ValueError("Kula public collection changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

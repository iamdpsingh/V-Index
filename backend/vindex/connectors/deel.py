"""Deel native public rendered boards; no account, candidate or application API calls."""

import asyncio
import json
import re
from datetime import datetime
from typing import Any

import httpx
from bs4 import BeautifulSoup
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.connectors.teamtailor import TENANT
from vindex.schemas import Enumeration, JobInput

UUID = r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}"


def document(body: bytes) -> BeautifulSoup:
    if b"</html>" not in body.lower():
        raise ValueError("Truncated Deel public document")
    return BeautifulSoup(body, "html.parser")


def flight(soup: BeautifulSoup) -> dict[str, Any]:
    """Decode length-delimited text and JSON records without evaluating JavaScript."""
    decoder = json.JSONDecoder()
    chunks = []
    for script in soup.select("script"):
        code = script.get_text()
        for match in re.finditer(r"self\.__next_f\.push\(", code):
            value, _ = decoder.raw_decode(code[match.end() :])
            if isinstance(value, list) and len(value) == 2 and value[0] == 1:
                if not isinstance(value[1], str):
                    raise ValueError("Malformed Deel Flight chunk")
                chunks.append(value[1])
    stream = "".join(chunks).encode()
    records: dict[str, Any] = {}
    offset = 0
    while offset < len(stream):
        boundary = re.match(rb"([0-9a-f]*):", stream[offset:])
        if boundary is None:
            raise ValueError("Malformed Deel Flight boundary")
        key = boundary[1].decode()
        if key and key in records:
            raise ValueError("Duplicate Deel Flight record")
        offset += boundary.end()
        if stream[offset : offset + 1] == b"T":
            size = re.match(rb"T([0-9a-f]+),", stream[offset:])
            if size is None:
                raise ValueError("Malformed Deel Flight text length")
            offset += size.end()
            end = offset + int(size[1], 16)
            if end > len(stream):
                raise ValueError("Truncated Deel Flight text")
            records[key] = stream[offset:end].decode()
            offset = end
        else:
            end = stream.find(b"\n", offset)
            if end < 0:
                raise ValueError("Truncated Deel Flight JSON")
            value = stream[offset:end]
            records[key] = json.loads(value) if value.startswith((b"[", b"{", b'"')) else None
            offset = end + 1
    return records


def objects(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from objects(child)


def compact(value: str) -> str:
    return re.sub(r"\s+([.,;:!?])", r"\1", " ".join(text(value).split()))


class DeelConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider != "deel" or not re.fullmatch(TENANT, slug):
            raise ValueError("Invalid Deel native public board")
        self.slug = slug
        self.url = "https://jobs.deel.com/" + slug
        self.http = PublicHTTP(client, {"jobs.deel.com"})

    def job_url(self, identifier: str) -> str:
        if not re.fullmatch(UUID, identifier):
            raise ValueError("Invalid Deel native posting UUID")
        return self.url + "/job-details/" + identifier + "/overview"

    def listings(self, body: bytes) -> tuple[str, dict[str, dict]]:
        soup = document(body)
        ld = [json.loads(t.get_text()) for t in soup.select('script[type="application/ld+json"]')]
        orgs = [d for d in ld if isinstance(d, dict) and d.get("@type") == "Organization"]
        lists = [d for d in ld if isinstance(d, dict) and d.get("@type") == "ItemList"]
        if len(orgs) != 1 or len(lists) != 1 or orgs[0].get("url") != self.url:
            raise ValueError("Missing Deel public employer/complete SEO roster")
        company = orgs[0]["name"]
        records = flight(soup)
        candidates = [o for r in records.values() for o in objects(r) if "jobPostings" in o]
        if len(candidates) != 1:
            raise ValueError("Ambiguous Deel public collection")
        props = candidates[0]
        settings = props["careerPageSettings"]
        if (
            props["orgSlug"] != self.slug
            or settings["urlSlug"] != self.slug
            or settings["preferredOrganizationName"] != company
            or not isinstance(company, str)
            or not company.strip()
        ):
            raise ValueError("Deel public employer identity mismatch")
        rows = props["jobPostings"]
        if not isinstance(rows, list) or not 0 < len(rows) <= 200:
            raise ValueError("Empty or oversized Deel collection")
        result = {}
        for original in rows:
            row = dict(original)
            identifier = row["id"]
            self.job_url(identifier)
            if identifier in result or row["jobId"] != row["job"]["id"]:
                raise ValueError("Duplicate/mismatched Deel posting identity")
            publications = row["jobPostingPublications"]
            native = [p for p in publications if p["jobBoard"]["id"] == settings["jobBoard"]["id"]]
            if len(native) != 1 or native[0]["currentState"]["stateSlug"] != "published_basic":
                raise ValueError("Deel posting is not published on this public board")
            description = row["richtextDescription"]
            if isinstance(description, str) and re.fullmatch(r"\$[0-9a-f]+", description):
                description = records.get(description[1:])
            if not isinstance(description, str) or not compact(description):
                raise ValueError("Unresolved/missing Deel public full description")
            row["richtextDescription"] = description
            # Retain public job facts, not application-form or internal user identifiers.
            result[identifier] = {
                k: row[k]
                for k in (
                    "id",
                    "jobId",
                    "title",
                    "richtextDescription",
                    "isCompensationVisible",
                    "createdAt",
                    "updatedAt",
                    "job",
                )
            }
        entries = lists[0]["itemListElement"]
        if not isinstance(entries, list) or [e["position"] for e in entries] != list(
            range(1, len(rows) + 1)
        ):
            raise ValueError("Partial Deel SEO roster")
        urls = [e["url"] for e in entries]
        if len(set(urls)) != len(rows) or set(urls) != {self.job_url(i) for i in result}:
            raise ValueError("Deel rendered and SEO rosters disagree")
        return company, result

    def parse(self, payload: Any) -> list[JobInput]:
        company, row, body = payload
        soup = document(body)
        docs = [json.loads(t.get_text()) for t in soup.select('script[type="application/ld+json"]')]
        jobs = [d for d in docs if isinstance(d, dict) and d.get("@type") == "JobPosting"]
        if len(jobs) != 1:
            raise ValueError("Missing Deel native public full job detail")
        job = jobs[0]
        url = self.job_url(row["id"])
        if (
            job["url"] != url
            or job["identifier"]["value"] != row["id"]
            or job["hiringOrganization"]["name"] != company
            or compact(job["title"]) != compact(row["title"])
            or compact(job["description"]) != compact(row["richtextDescription"])
        ):
            raise ValueError("Deel native detail identity/employer/title/full text mismatch")
        locations = [v["location"]["name"] for v in row["job"]["jobLocations"]]
        employment = [v["employmentType"]["name"] for v in row["job"]["jobEmploymentTypes"]]
        published = job.get("datePosted")
        flags = [] if locations else ["location_missing"]
        if not published:
            flags.append("publication_date_missing")
        salary = job.get("baseSalary")
        if salary is None and row["isCompensationVisible"]:
            salary = row["job"].get("currentCompensation")
        return [
            JobInput(
                external_id=row["id"],
                title=row["title"],
                company=company,
                description=text(row["richtextDescription"]),
                location="; ".join(dict.fromkeys(locations)),
                source_url=url,
                application_url=url,
                employment_type=", ".join(employment) or None,
                remote_status=row["job"].get("workArrangementEnum"),
                salary=salary,
                published_at=datetime.fromisoformat(published) if published else None,
                quality_flags=flags,
                raw={
                    "public_posting": row,
                    "jobposting": job,
                    "application_entry": "native public posting",
                },
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("Deel requires complete native board enumeration")
        return await self.http.read(self.url)

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, "https://jobs.deel.com")

        async def read(url):
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        company, rows = self.listings(await read(self.url))
        jobs = []
        for identifier, row in rows.items():
            jobs.extend(self.parse((company, row, await read(self.job_url(identifier)))))
        if self.listings(await read(self.url)) != (company, rows):
            raise ValueError("Deel complete public board changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

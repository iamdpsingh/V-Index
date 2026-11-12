"""Public Job Board Fire sitemap, server-rendered roster, and job details."""

import asyncio
import json
import re
from datetime import datetime
from html import unescape
from typing import Any
from urllib.parse import urlsplit

import httpx
from vindex.connectors.http import PublicHTTP
from vindex.connectors.jobboardio import document, xml_urls
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.schemas import Enumeration, JobInput

BOARDS = {"jobs.trellis.net": "greenbiz", "lpjc.jobboardfire.com": "lpjc"}
SLUG = r"[a-z0-9][a-z0-9-]{0,200}-[0-9a-f]{12}"
UUID = r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}"


class PublicPageState:
    def __init__(self, body: bytes):
        soup = document(body)
        scripts = soup.select('script#__NUXT_DATA__[type="application/json"]')
        if len(scripts) != 1:
            raise ValueError("Missing Job Board Fire public page state")
        self.soup = soup
        self.values = json.loads(scripts[0].get_text())
        if not isinstance(self.values, list) or not self.values:
            raise ValueError("Malformed Job Board Fire public page state")
        root = self.reactive(self.values[0])
        if self.get(root["serverRendered"]) is not True:
            raise ValueError("Job Board Fire page is not server-rendered")
        self.path = self.get(root["path"])
        self.data = self.reactive(self.get(root["data"]))

    def get(self, reference: int) -> Any:
        if type(reference) is not int or not 0 <= reference < len(self.values):
            raise ValueError("Invalid Job Board Fire state reference")
        return self.values[reference]

    def reactive(self, wrapper: Any) -> dict[str, Any]:
        if not isinstance(wrapper, list) or len(wrapper) != 2 or wrapper[0] != "ShallowReactive":
            raise ValueError("Unexpected Job Board Fire state wrapper")
        value = self.get(wrapper[1])
        if not isinstance(value, dict):
            raise ValueError("Malformed Job Board Fire state object")
        return value

    def result(self, key: str) -> Any:
        wrapper = self.get(self.data[key])
        if self.get(wrapper["error"]) not in (False, None):
            raise ValueError("Job Board Fire returned a state error")
        return self.get(wrapper["data"])

    def field(self, obj: dict[str, Any], key: str) -> Any:
        reference = obj.get(key, -1)
        return None if reference == -1 else self.get(reference)


class JobBoardFireConnector:
    def __init__(self, slug: str, client: httpx.AsyncClient):
        if slug not in BOARDS:
            raise ValueError("Unreviewed Job Board Fire site")
        self.origin = "https://" + slug
        self.index = BOARDS[slug]
        self.http = PublicHTTP(client, {slug})

    def roster(self, body: bytes) -> dict[str, tuple[str, str]]:
        state = PublicPageState(body)
        data = state.result("jobs")
        hits = state.get(data["hits"])
        if (
            state.path != "/"
            or state.get(data["query"]) != ""
            or state.get(data["offset"]) != 0
            or state.get(data["indexUid"]) != self.index
            or not isinstance(hits, list)
            or not 1 <= len(hits) <= 20
            or state.get(data["limit"]) != 20
            or state.get(data["estimatedTotalHits"]) != len(hits)
        ):
            raise ValueError("Incomplete or oversized Job Board Fire search roster")
        rows = {}
        for ref in hits:
            row = state.get(ref)
            slug = state.get(row["slug"])
            identifier = state.get(row["id"])
            title = state.get(row["title"])
            if (
                not isinstance(slug, str)
                or not re.fullmatch(SLUG, slug)
                or slug in rows
                or not isinstance(identifier, str)
                or not re.fullmatch(UUID, identifier)
                or not isinstance(title, str)
                or not title.strip()
            ):
                raise ValueError("Malformed or repeated Job Board Fire job")
            rows[slug] = (identifier, title)
        if len({identifier for identifier, _ in rows.values()}) != len(rows):
            raise ValueError("Repeated Job Board Fire posting ID")
        return rows

    def parse(self, payload: Any) -> list[JobInput]:
        slug, (identifier, title), body = payload
        state = PublicPageState(body)
        url = self.origin + "/j/" + slug
        canonical = state.soup.select('link[rel="canonical"][href]')
        heading = state.soup.select("h1")
        if (
            state.path != "/j/" + slug
            or len(canonical) != 1
            or canonical[0]["href"] != url
            or len(heading) != 1
            or heading[0].get_text(" ", strip=True) != " ".join(title.split())
        ):
            raise ValueError(f"Job Board Fire detail identity mismatch for {identifier}")
        records = state.result("jobPost")
        if not isinstance(records, list) or len(records) != 2:
            raise ValueError("Malformed Job Board Fire detail state")
        row = state.get(records[1])
        if any(
            state.field(row, key) != value
            for key, value in (("id", identifier), ("slug", slug), ("title", title), ("status", 1))
        ):
            raise ValueError(f"Job Board Fire active job state mismatch for {identifier}")
        postings = []
        for script in state.soup.select('script[type="application/ld+json"]'):
            item = json.loads(unescape(script.get_text()))
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                postings.append(item)
        if len(postings) != 1:
            raise ValueError("Missing Job Board Fire JobPosting")
        job = postings[0]
        if job.get("identifier", {}).get("value") != identifier or job.get("title") != title:
            raise ValueError("Job Board Fire structured posting identity mismatch")
        company = text(job.get("hiringOrganization", {}).get("name", ""))
        description = text(job.get("description", ""))
        if not company or not description:
            raise ValueError(f"Incomplete Job Board Fire posting {identifier}")
        places = job.get("jobLocation") or []
        if isinstance(places, dict):
            places = [places]
        locations = []
        for place in places:
            address = place.get("address", {})
            location = ", ".join(
                value.strip()
                for key in ("addressLocality", "addressRegion", "addressCountry")
                if isinstance(value := address.get(key), str) and value.strip()
            )
            if location and location not in locations:
                locations.append(location)
        application = url
        if state.field(row, "applyBy") == "LINK":
            link = state.field(row, "applicationLink")
            if isinstance(link, str):
                target = urlsplit(link)
                if (
                    target.scheme == "https"
                    and target.hostname
                    and target.username is None
                    and target.password is None
                    and target.port in (None, 443)
                ):
                    application = link
        date = state.field(row, "datePublished")
        employment = job.get("employmentType")
        if isinstance(employment, list):
            employment = ", ".join(employment)
        return [
            JobInput(
                external_id=identifier,
                title=title,
                company=company,
                description=description,
                location="; ".join(locations),
                source_url=url,
                application_url=application,
                employment_type=employment,
                salary=job.get("baseSalary"),
                remote_status="Remote" if job.get("jobLocationType") == "TELECOMMUTE" else None,
                published_at=datetime.fromisoformat(date) if date else None,
                quality_flags=([] if date else ["publication_date_missing"])
                + ([] if locations else ["location_missing"]),
                raw={
                    "date_published_original": date,
                    "date_expiring": state.field(row, "dateExpiring"),
                },
            )
        ]

    async def fetch(self, cursor: int = 0) -> bytes:
        if cursor:
            raise ValueError("Only single-page Job Board Fire boards are supported")
        return await self.http.read(self.origin + "/")

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)
        index = self.origin + "/sitemap.xml"
        jobs_map = self.origin + "/sitemap-jobs.xml"
        if index not in (policy.parser.site_maps() or []):
            raise ValueError("Missing Job Board Fire sitemap declaration")

        async def read(url: str) -> bytes:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        async def roster() -> dict[str, tuple[str, str]]:
            rows = self.roster(await read(self.origin + "/"))
            maps = xml_urls(await read(index), index=True)
            if jobs_map not in maps or any(
                re.fullmatch(re.escape(self.origin) + r"/sitemap-jobs[^/]*\.xml", url)
                and url != jobs_map
                for url in maps
            ):
                raise ValueError("Unexpected Job Board Fire job sitemap scope")
            urls = xml_urls(await read(jobs_map), index=False)
            if {self.origin + "/j/" + slug for slug in rows} != set(urls):
                raise ValueError("Job Board Fire search and sitemap do not agree")
            return rows

        before = await roster()
        jobs = []
        for slug, identity in before.items():
            jobs.extend(self.parse((slug, identity, await read(self.origin + "/j/" + slug))))
        if await roster() != before:
            raise ValueError("Job Board Fire roster changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

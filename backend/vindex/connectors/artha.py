"""Artha's published job sitemaps and canonical posting pages."""

import asyncio
import json
import re
from typing import Any
from urllib.parse import urlsplit

import httpx
from vindex.connectors.http import PublicHTTP
from vindex.connectors.jobboardio import document, xml_urls
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.schemas import Enumeration, JobInput

HOSTS = frozenset({"lexpath.com.au", "joberly.eu"})
JOB_PATH = re.compile(r"/job-detail/[a-zA-Z0-9_-]{1,250}")
MAP_PATH = re.compile(r"/jd/[1-9][0-9]{0,3}/sitemap\.xml")
ASSET_ORIGIN = "https://cdn-static.arthajobboard.com/"


class ArthaConnector:
    def __init__(self, host: str, client: httpx.AsyncClient):
        if host not in HOSTS:
            raise ValueError("Unknown Artha host")
        self.host = host
        self.origin = f"https://{host}"
        self.http = PublicHTTP(client, {host})

    async def read(self, url: str, policy: RobotsPolicy) -> bytes:
        policy.check(url)
        await asyncio.sleep(policy.delay())
        return await self.http.read(url)

    async def fetch(self, cursor: int = 0) -> bytes:
        if cursor:
            raise ValueError("Artha uses sitemap pagination")
        policy = await RobotsPolicy.load(self.http, self.origin)
        return await self.read(f"{self.origin}/sitemap.xml", policy)

    def scoped(self, url: str, path: re.Pattern[str]) -> bool:
        parts = urlsplit(url)
        return (
            parts.scheme == "https"
            and parts.netloc == self.host
            and not parts.query
            and not parts.fragment
            and path.fullmatch(parts.path) is not None
        )

    async def roster(self, policy: RobotsPolicy) -> set[str]:
        index = f"{self.origin}/sitemap.xml"
        if index not in (policy.parser.site_maps() or []):
            raise ValueError("Missing advertised Artha sitemap")
        maps = [
            url
            for url in xml_urls(await self.read(index, policy), index=True)
            if self.scoped(url, MAP_PATH)
        ]
        if not maps or len(maps) > 4:
            raise ValueError("Missing or oversized Artha job sitemap set")
        urls: set[str] = set()
        for url in maps:
            entries = xml_urls(await self.read(url, policy), index=False)
            if any(not self.scoped(entry, JOB_PATH) or entry in urls for entry in entries):
                raise ValueError("Out-of-scope or repeated Artha job URL")
            urls.update(entries)
        return urls

    def parse(self, payload: tuple[str, bytes]) -> list[JobInput]:
        url, body = payload
        soup = document(body)
        canonical = soup.select('link[rel="canonical"][href]')
        if (
            len(canonical) != 1
            or canonical[0]["href"] != url
            or not any(
                str(tag["src"]).startswith(ASSET_ORIGIN) for tag in soup.select("script[src]")
            )
        ):
            raise ValueError("Invalid Artha posting origin or identity")
        postings = []
        for script in soup.select('script[type="application/ld+json"]'):
            data = json.loads(script.get_text())
            if isinstance(data, dict) and data.get("@type") == "JobPosting":
                postings.append(data)
        if len(postings) != 1:
            raise ValueError("Missing or ambiguous Artha JobPosting")
        job = postings[0]
        identifier = job["identifier"]["value"]
        company = text(job["hiringOrganization"]["name"])
        title = text(job["title"])
        description = text(job["description"])
        if (
            job.get("url") != url
            or not re.fullmatch(r"[0-9a-f]{24}", identifier)
            or not title
            or not description
            or not company
        ):
            raise ValueError("Invalid Artha posting fields")
        action = job.get("potentialAction") or {}
        target = (action.get("target") or {}).get("urlTemplate")
        has_apply_control = any(
            node.get_text(" ", strip=True).casefold()
            in {"apply for this job", "apply now", "apply"}
            and not node.has_attr("disabled")
            for node in soup.select("button, a")
        )
        if action.get("@type") != "ApplyAction" or target != url or not has_apply_control:
            raise ValueError("Missing verified Artha application entry")
        location_rows = job.get("jobLocation") or []
        if isinstance(location_rows, dict):
            location_rows = [location_rows]
        locations = []
        for place in location_rows:
            address = place.get("address") or {}
            location = ", ".join(
                dict.fromkeys(
                    value
                    for key in (
                        "addressLocality",
                        "addressRegion",
                        "addressCountry",
                        "streetAddress",
                    )
                    if isinstance(value := address.get(key), str) and value
                )
            )
            if location and location not in locations:
                locations.append(location)
        employment = job.get("employmentType")
        salary: dict[str, Any] | None = job.get("baseSalary")
        return [
            JobInput(
                external_id=identifier,
                title=title,
                company=company,
                description=description,
                source_url=url,
                application_url=url,
                location="; ".join(locations),
                employment_type=", ".join(employment)
                if isinstance(employment, list)
                else employment,
                remote_status="Remote" if job.get("jobLocationType") == "TELECOMMUTE" else None,
                salary=salary,
                published_at=job.get("datePosted"),
            )
        ]

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)
        before = await self.roster(policy)
        jobs = []
        for url in sorted(before):
            jobs.extend(self.parse((url, await self.read(url, policy))))
        if len({job.external_id for job in jobs}) != len(before):
            raise ValueError("Repeated Artha posting ID")
        if await self.roster(policy) != before:
            raise ValueError("Artha roster changed during refresh")
        return Enumeration(jobs=jobs, complete=True)

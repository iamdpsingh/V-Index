"""Phenom public paginated search, advertised sitemaps, and posting details."""

import asyncio
import json
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

import httpx
from vindex.connectors.http import PublicHTTP
from vindex.connectors.jobboardio import document, xml_urls
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.schemas import Enumeration, JobInput

BOARDS = {"careers.phenom.com": "/global/en", "careers.bloodcancerunited.org": "/us/en"}
STATE = re.compile(rb"phApp\.ddo\s*=\s*(\{.*?\});", re.DOTALL)
JOB_ID = r"[A-Za-z0-9][A-Za-z0-9_-]{0,80}"
MAX_JOBS = 150


def state(body: bytes) -> dict[str, Any]:
    if b"</html>" not in body.lower():
        raise ValueError("Truncated Phenom HTML")
    matches = STATE.findall(body)
    if len(matches) != 1:
        raise ValueError("Missing or repeated Phenom server-rendered state")
    data = json.loads(matches[0])
    if not isinstance(data, dict):
        raise ValueError("Malformed Phenom server-rendered state")
    return data


class PhenomPeopleConnector:
    def __init__(self, slug: str, client: httpx.AsyncClient):
        if slug not in BOARDS:
            raise ValueError("Unreviewed Phenom site")
        self.origin = "https://" + slug
        self.locale = BOARDS[slug]
        self.base = self.origin + self.locale
        self.search = self.base + "/search-results"
        self.http = PublicHTTP(client, {slug})

    def page(self, body: bytes, offset: int) -> tuple[int, dict[str, tuple[str, str]]]:
        search = state(body).get("eagerLoadRefineSearch", {})
        tracking = search.get("eid", {})
        total = search.get("totalHits")
        rows = search.get("data", {}).get("jobs")
        if (
            search.get("status") != 200
            or tracking.get("searchType") != "allJobs"
            or tracking.get("query") != ""
            or type(total) is not int
            or not 0 <= offset < total <= MAX_JOBS
            or not isinstance(rows, list)
            or len(rows) != min(10, total - offset)
            or search.get("hits") != len(rows)
        ):
            raise ValueError("Missing or incomplete Phenom search page")
        jobs: dict[str, tuple[str, str]] = {}
        for item in rows:
            identifier = item.get("jobId")
            seq = item.get("jobSeqNo")
            title = item.get("title")
            if (
                not isinstance(identifier, str)
                or not re.fullmatch(JOB_ID, identifier)
                or not isinstance(seq, str)
                or not re.fullmatch(JOB_ID, seq)
                or not isinstance(title, str)
                or not title.strip()
                or identifier in jobs
            ):
                raise ValueError("Malformed or repeated Phenom job")
            jobs[identifier] = (seq, title)
        if len({seq for seq, _ in jobs.values()}) != len(jobs):
            raise ValueError("Repeated Phenom sequence identifier")
        return total, jobs

    def sitemap(self, body: bytes) -> dict[str, str]:
        urls = {}
        prefix = self.base + "/job/"
        for url in xml_urls(body, index=False):
            if not url.startswith(prefix):
                continue
            match = re.fullmatch(re.escape(prefix) + rf"({JOB_ID})/[^/?#\\]+", url)
            if not match or match[1] in urls:
                raise ValueError("Malformed or repeated Phenom sitemap job")
            urls[match[1]] = url
        return urls

    def parse(self, payload: Any) -> list[JobInput]:
        identifier, (seq, title), url, body = payload
        soup = document(body)
        canonical = soup.select('link[rel="canonical"][href]')
        if len(canonical) != 1 or canonical[0]["href"] != url:
            raise ValueError(f"Phenom canonical URL mismatch for job {identifier}")
        native = state(body).get("jobDetail", {}).get("data", {}).get("job", {})
        if (
            native.get("jobId") != identifier
            or native.get("jobSeqNo") != seq
            or native.get("title") != title
            or native.get("siteType") != "external"
            or native.get("displayCareerSite") is not True
            or native.get("isPrivate") is True
            or native.get("isConfidential") is True
        ):
            raise ValueError(f"Phenom public posting identity mismatch for job {identifier}")
        postings = []
        for script in soup.select('script[type="application/ld+json"]'):
            item = json.loads(script.get_text())
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                postings.append(item)
        if len(postings) != 1:
            raise ValueError(f"Missing Phenom JobPosting for job {identifier}")
        posting = postings[0]
        organization = posting.get("hiringOrganization", {})
        structured_title = posting.get("title")
        if not structured_title or organization.get("url") != url:
            raise ValueError(f"Phenom structured posting identity mismatch for job {identifier}")
        company = text(organization.get("name", ""))
        description = text(native.get("description") or "")
        if not company or not description:
            raise ValueError(f"Incomplete Phenom detail for job {identifier}")
        application = native.get("applyUrl") or url
        parsed = urlsplit(application)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in (None, 443)
        ):
            raise ValueError("Invalid Phenom application link")
        location = native.get("location") or ""
        date = native.get("postedDate") or posting.get("datePosted")
        remote = (
            posting.get("jobLocationType") == "TELECOMMUTE"
            or location.split(",")[0].strip().casefold() == "remote"
        )
        return [
            JobInput(
                external_id=seq,
                title=title,
                company=company,
                description=description,
                location=location,
                source_url=url,
                application_url=application,
                published_at=datetime.fromisoformat(date) if date else None,
                employment_type=native.get("type"),
                salary=posting.get("baseSalary"),
                remote_status="Remote" if remote else None,
                quality_flags=([] if date else ["publication_date_missing"])
                + ([] if location else ["location_missing"])
                + ([] if title == structured_title else ["structured_title_differs"]),
                raw={
                    "job_id": identifier,
                    "date_posted_original": date,
                    "structured_date_posted": posting.get("datePosted"),
                    "structured_title": structured_title,
                },
            )
        ]

    async def fetch(self, cursor: int = 0) -> bytes:
        if cursor:
            raise ValueError("Phenom uses its native public pager")
        return await self.http.read(self.search)

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)
        map_url = self.base + "/sitemap.xml"
        if map_url not in (policy.parser.site_maps() or []):
            raise ValueError("Missing Phenom sitemap declaration")

        async def read(url: str) -> bytes:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        async def roster() -> tuple[dict[str, tuple[str, str]], dict[str, str]]:
            total, jobs = self.page(await read(self.search), 0)
            for offset in range(10, total, 10):
                observed, page = self.page(await read(f"{self.search}?from={offset}&s=1"), offset)
                if total != observed or jobs.keys() & page.keys():
                    raise ValueError("Changed or repeated Phenom roster")
                jobs.update(page)
            urls = self.sitemap(await read(map_url))
            if len(jobs) != total or jobs.keys() != urls.keys():
                raise ValueError("Phenom search and sitemap rosters do not agree")
            return jobs, urls

        before, urls = await roster()
        jobs = []
        for identifier, row in before.items():
            url = urls[identifier]
            jobs.extend(self.parse((identifier, row, url, await read(url))))
        if len({job.external_id for job in jobs}) != len(jobs) or await roster() != (before, urls):
            raise ValueError("Phenom roster changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

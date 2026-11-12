"""Public Paradox Career Site Studio job lists and details."""

import asyncio
import json
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

import httpx
from vindex.connectors.http import PublicHTTP
from vindex.connectors.jobboardio import document
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.schemas import Enumeration, JobInput

HOSTS = frozenset({"flynnrgcareers.com", "careers.mwg.aaa.com"})
PATH = re.compile(r"/[a-z0-9][a-z0-9-]{1,220}/job/([A-Za-z0-9][A-Za-z0-9-]{1,80})")
MAX_JOBS = 200


class ParadoxConnector:
    def __init__(self, slug: str, client: httpx.AsyncClient):
        if slug not in HOSTS:
            raise ValueError("Unreviewed Paradox site")
        self.origin = "https://" + slug
        self.http = PublicHTTP(client, {slug})

    def page(self, body: bytes, number: int) -> tuple[int, dict[str, tuple[str, str]]]:
        soup = document(body)
        counter = soup.select_one(".results-header__content")
        if counter is None:
            raise ValueError("Missing Paradox search total")
        match = re.fullmatch(
            r"Showing ([0-9]+)\s*-\s*([0-9]+) of ([0-9]+) jobs",
            counter.get_text(" ", strip=True),
        )
        if not match:
            raise ValueError("Malformed Paradox result range")
        start, end, total = map(int, match.groups())
        if not 1 <= start <= end <= total <= MAX_JOBS:
            raise ValueError("Empty or oversized Paradox roster")
        if start != (number - 1) * 10 + 1 or end != min(number * 10, total):
            raise ValueError("Unexpected Paradox result range")
        pager = soup.select_one(".jobs-pagination")
        if pager is not None:
            current = pager.select('a[aria-current="page"]')
            next_links = pager.select(".page-link-next")
            if (
                len(current) != 1
                or current[0].get("href") != f"/page/{number}"
                or len(next_links) != 1
            ):
                raise ValueError("Unexpected Paradox page")
            next_link = next_links[0]
            if end < total:
                if (
                    next_link.get("href") != f"/page/{number + 1}"
                    or next_link.get("aria-disabled") != "false"
                ):
                    raise ValueError("Unscoped Paradox next page")
            elif next_link.has_attr("href") or next_link.get("aria-disabled") != "true":
                raise ValueError("Unexpected Paradox terminal link")
        elif number != 1 or end != total:
            raise ValueError("Missing Paradox pagination")
        rows: dict[str, tuple[str, str]] = {}
        for link in soup.select("a.results-list__item-title--link"):
            path = str(link.get("href") or "")
            job = PATH.fullmatch(path)
            title = link.get_text(" ", strip=True)
            if not job or not title or job[1] in rows:
                raise ValueError("Malformed or repeated Paradox job")
            rows[job[1]] = (path, title)
        if len(rows) != end - start + 1:
            raise ValueError("Partial Paradox search page")
        return total, rows

    def parse(self, payload: Any) -> list[JobInput]:
        identifier, (path, title), body = payload
        soup = document(body)
        url = self.origin + path
        headings = soup.select("h1.hd-2")
        canonical = soup.select('link[rel="canonical"][href]')
        if (
            len(headings) != 1
            or headings[0].get_text(" ", strip=True) != title
            or len(canonical) != 1
            or canonical[0]["href"] != url
        ):
            raise ValueError(f"Paradox visible identity mismatch for job {identifier}")
        postings = []
        for script in soup.select('script[type="application/ld+json"]'):
            item = json.loads(script.get_text())
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                postings.append(item)
        if len(postings) != 1:
            raise ValueError(f"Missing Paradox JobPosting for job {identifier}")
        job = postings[0]
        if (
            job.get("url") != url
            or job.get("identifier", {}).get("value") != identifier
            or job.get("title") != title
        ):
            raise ValueError(f"Paradox structured identity mismatch for job {identifier}")
        company = text(job.get("hiringOrganization", {}).get("name", ""))
        description = text(job.get("description", ""))
        if not company or not description:
            raise ValueError(f"Incomplete Paradox details for job {identifier}")
        apply_urls = {
            str(a["href"])
            for a in soup.select("a.olivia-apply[href],a.apply-button[href]")
            if a.get_text(" ", strip=True) == "Apply for this position"
        }
        if len(apply_urls) != 1:
            raise ValueError(f"Missing or conflicting Paradox application for job {identifier}")
        application = apply_urls.pop()
        target = urlsplit(application)
        if (
            target.scheme != "https"
            or not target.hostname
            or target.username is not None
            or target.password is not None
            or target.port not in (None, 443)
        ):
            raise ValueError("Invalid Paradox application link")
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
        date = job.get("datePosted")
        return [
            JobInput(
                external_id=identifier,
                title=title,
                company=company,
                description=description,
                location="; ".join(locations),
                source_url=url,
                application_url=application,
                published_at=datetime.fromisoformat(date) if date else None,
                employment_type=job.get("employmentType"),
                salary=job.get("baseSalary"),
                remote_status="Remote" if job.get("jobLocationType") == "TELECOMMUTE" else None,
                quality_flags=([] if date else ["publication_date_missing"])
                + ([] if locations else ["location_missing"]),
                raw={"date_posted_original": date, "valid_through": job.get("validThrough")},
            )
        ]

    async def fetch(self, cursor: int = 0) -> bytes:
        if cursor:
            raise ValueError("Paradox uses its native public pager")
        return await self.http.read(self.origin + "/")

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)

        async def read(path: str) -> bytes:
            url = self.origin + path
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        async def roster() -> dict[str, tuple[str, str]]:
            total, rows = self.page(await read("/"), 1)
            for number in range(2, (total + 9) // 10 + 1):
                observed, page = self.page(await read(f"/page/{number}"), number)
                if total != observed or rows.keys() & page.keys():
                    raise ValueError("Changed or repeated Paradox roster")
                rows.update(page)
            if len(rows) != total:
                raise ValueError("Incomplete Paradox roster")
            return rows

        before = await roster()
        jobs = []
        for identifier, row in before.items():
            jobs.extend(self.parse((identifier, row, await read(row[0]))))
        if await roster() != before:
            raise ValueError("Paradox roster changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

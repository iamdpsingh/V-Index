"""Public Madgex pagination and canonical posting extraction."""

import asyncio
import json
import re
from datetime import datetime
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup
from vindex.connectors.http import PublicHTTP
from vindex.connectors.jobboardio import document
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.schemas import JobInput

BOARDS = {"jobs.sciencecareers.org": "", "www.nature.com": "/naturecareers"}
SLUG = r"(?:[A-Za-z0-9_-]|%[89a-fA-F][0-9a-fA-F])+"
PAGE_SIZE = 20
MAX_PAGES = 65


class WileyMadgexConnector:
    def __init__(self, host: str, client: httpx.AsyncClient):
        if host not in BOARDS:
            raise ValueError("Unreviewed Wiley Madgex site")
        self.host = host
        self.origin = f"https://{host}"
        self.prefix = BOARDS[host]
        self.search = self.origin + self.prefix + "/jobs/"
        self.path = re.compile(re.escape(self.prefix) + rf"/job/([1-9][0-9]{{0,15}})/{SLUG}/?")
        self.http = PublicHTTP(client, {host})

    async def read(self, url: str, policy: RobotsPolicy) -> bytes:
        policy.check(url)
        await asyncio.sleep(policy.delay())
        return await self.http.read(url)

    def page(
        self, body: bytes, number: int
    ) -> tuple[int | None, dict[str, tuple[str, str]], str | None]:
        soup = document(body)
        url = self.search if number == 1 else self.search + f"{number}/"
        totals = {
            int(match[1].replace(",", ""))
            for heading in soup.select("h1")
            if (match := re.fullmatch(r"Found ([0-9,]+) jobs?", heading.get_text(" ", strip=True)))
        }
        if len(totals) > 1 or (not totals and (number != 1 or not self.prefix)):
            raise ValueError("Missing or conflicting Madgex advertised total")
        total = next(iter(totals), None)
        if total is not None and not 1 <= total <= MAX_PAGES * PAGE_SIZE:
            raise ValueError("Empty or oversized Madgex roster")
        rows = {}
        for anchor in soup.select(".lister__item .lister__header a[href]"):
            link = urlsplit(urljoin(url, str(anchor["href"]).strip()))
            match = self.path.fullmatch(link.path)
            title = anchor.get_text(" ", strip=True)
            if (
                link.scheme != "https"
                or link.netloc != self.host
                or not match
                or not title
                or match[1] in rows
            ):
                raise ValueError("Malformed or repeated Madgex listing")
            rows[match[1]] = (self.origin + link.path.rstrip("/") + "/", title)
        next_urls = {
            urljoin(url, str(anchor["href"]).strip())
            for anchor in soup.select('[rel="next"][href]')
        }
        next_url = self.search + f"{number + 1}/" if next_urls else None
        if next_urls and next_urls != {next_url}:
            raise ValueError("Unexpected Madgex next page")
        if not 1 <= len(rows) <= PAGE_SIZE or (next_url and len(rows) != PAGE_SIZE):
            raise ValueError("Incomplete Madgex listing page")
        return total, rows, next_url

    async def roster(self, policy: RobotsPolicy) -> dict[str, tuple[str, str]]:
        url: str | None = self.search
        result: dict[str, tuple[str, str]] = {}
        total = None
        for number in range(1, MAX_PAGES + 1):
            assert url is not None
            observed, rows, url = self.page(await self.read(url, policy), number)
            if observed is not None:
                if total is not None and observed != total:
                    raise ValueError("Madgex advertised total changed during the run")
                total = observed
            if result.keys() & rows.keys():
                raise ValueError("Repeated Madgex listing across pages")
            result.update(rows)
            if url is None:
                if total is None or len(result) != total:
                    raise ValueError("Madgex roster does not match its advertised total")
                return result
        raise ValueError("Madgex exceeded its page limit")

    def parse_detail(self, identifier: str, url: str, listed_title: str, body: bytes) -> JobInput:
        soup = document(body)
        canonical = soup.select('link[rel="canonical"][href]')
        headings = soup.select("h1.mds-font-s6")
        canonical_url = urlsplit(str(canonical[0]["href"])) if len(canonical) == 1 else None
        canonical_job = self.path.fullmatch(canonical_url.path) if canonical_url else None
        if (
            canonical_url is None
            or canonical_url.scheme != "https"
            or canonical_url.netloc != self.host
            or canonical_url.query
            or canonical_url.fragment
            or not canonical_job
            or canonical_job[1] != identifier
            or len(headings) != 1
            or headings[0].get_text(" ", strip=True) != listed_title
        ):
            raise ValueError(f"Madgex visible posting mismatch for job {identifier}")
        postings = []
        for script in soup.select('script[type="application/ld+json"]'):
            item = json.loads(script.get_text())
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                postings.append(item)
        if len(postings) != 1:
            raise ValueError(f"Missing Madgex JobPosting for job {identifier}")
        job = postings[0]
        structured_title = text(job.get("title") or "")
        company = text(job.get("hiringOrganization", {}).get("name") or "")
        description_html = job.get("description") or ""
        description = text(description_html)
        if not structured_title or not company or not description:
            raise ValueError(f"Incomplete Madgex detail fields for job {identifier}")
        source_url = canonical_url.geturl()
        application = source_url
        native_apply = set()
        for anchor in soup.select("a[href]"):
            target = urlsplit(urljoin(url, str(anchor["href"]).strip()))
            if (
                target.scheme == "https"
                and target.netloc == self.host
                and re.fullmatch(
                    re.escape(self.prefix) + rf"/(?:apply|job-apply)/{identifier}/{SLUG}/?",
                    target.path,
                )
            ):
                native_apply.add(self.origin + target.path)
        if len(native_apply) == 1:
            application = next(iter(native_apply))
        elif len(native_apply) > 1:
            raise ValueError(f"Conflicting Madgex application entries for job {identifier}")
        email_application = False
        if not native_apply and not soup.select_one(
            'a[href="#application-form"], #application-form'
        ):
            email_application = (
                "application" in description.casefold()
                and BeautifulSoup(description_html, "html.parser").select_one('a[href^="mailto:"]')
                is not None
            )
            if not email_application:
                raise ValueError(f"Missing Madgex application entry for job {identifier}")
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
        employment = job.get("employmentType")
        if isinstance(employment, list):
            employment = ", ".join(employment)
        structured_id = job.get("identifier")
        return JobInput(
            external_id=identifier,
            title=listed_title,
            company=company,
            description=description,
            location="; ".join(locations),
            source_url=source_url,
            application_url=application,
            published_at=datetime.fromisoformat(date) if date else None,
            employment_type=employment,
            salary=job.get("baseSalary"),
            remote_status="Remote" if job.get("jobLocationType") == "TELECOMMUTE" else None,
            quality_flags=([] if date else ["publication_date_missing"])
            + ([] if locations else ["location_missing"])
            + ([] if structured_title == listed_title else ["structured_title_differs"])
            + (["application_by_email"] if email_application else []),
            raw={
                "date_posted_original": date,
                "valid_through": job.get("validThrough"),
                "requisition_id": structured_id.get("value")
                if isinstance(structured_id, dict)
                else structured_id,
                "structured_title": structured_title,
            },
        )

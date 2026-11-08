"""JobKit's public server-rendered board and job posting pages."""

import asyncio
import json
import re
from datetime import datetime
from typing import Any
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.schemas import Enumeration, JobInput

HOSTS = frozenset({"jobs.rubyonrails.org", "welpora.jobkit.io"})
JOB_PATH = r"/jobs/([1-9][0-9]{0,17})-[a-z0-9][a-z0-9-]*"


class JobKitConnector:
    def __init__(self, slug: str, client: httpx.AsyncClient):
        if slug not in HOSTS:
            raise ValueError("Unreviewed JobKit origin")
        self.origin = "https://" + slug
        self.http = PublicHTTP(client, {slug})

    def roster(self, body: bytes) -> dict[str, str]:
        soup = public_document(body)
        canonical = soup.select('link[rel="canonical"]')
        search = soup.select('input[name="q"][placeholder]')
        if len(canonical) != 1 or canonical[0].get("href") != self.origin + "/" or len(search) != 1:
            raise ValueError("Missing canonical JobKit board")
        if not any(
            a.get_text(" ", strip=True) == "JobKit"
            for a in soup.select('a[href="https://www.jobkit.io/"]')
        ):
            raise ValueError("Missing native JobKit attribution")
        count = re.fullmatch(
            r"Search through ([1-9][0-9]{0,2}) jobs?\.\.\.", str(search[0]["placeholder"])
        )
        if not count or int(count[1]) > 200:
            raise ValueError("Invalid or oversized JobKit board total")
        jobs = {}
        for anchor in soup.select('a[href^="/jobs/"]'):
            path = str(anchor["href"])
            if path == "/jobs/new":
                continue
            match = re.fullmatch(JOB_PATH, path)
            if not match or match[1] in jobs:
                raise ValueError("Invalid or repeated JobKit roster entry")
            jobs[match[1]] = self.origin + path
        if len(jobs) != int(count[1]):
            raise ValueError("JobKit board total does not match complete first page")
        return jobs

    def parse(self, payload: Any) -> list[JobInput]:
        identifier, url, body = payload
        soup = public_document(body)
        canonical = soup.select('link[rel="canonical"]')
        titles = soup.select("main h1:not(.prose h1)")
        descriptions = soup.select("main .prose")
        structured = [
            json.loads(t.get_text()) for t in soup.select('script[type="application/ld+json"]')
        ]
        postings = [j for j in structured if isinstance(j, dict) and j.get("@type") == "JobPosting"]
        if any(len(items) != 1 for items in (canonical, titles, descriptions, postings)):
            raise ValueError("Missing full JobKit detail")
        row = postings[0]
        title = text(row["title"])
        company = text(row["hiringOrganization"]["name"])
        description = descriptions[0].get_text(" ", strip=True)
        visible_title = titles[0].get_text(" ", strip=True)
        if (
            canonical[0].get("href") != url
            or str(row["identifier"]["value"]) != identifier
            or text(row["identifier"]["name"]) != company
            or visible_title != f"{title} at {company}"
            or not description
        ):
            raise ValueError("JobKit canonical, title, employer or description mismatch")
        buttons = {
            str(a["href"])
            for a in soup.select("main a[href].btn")
            if a.get_text(" ", strip=True).casefold() == "apply now"
        }
        if len(buttons) != 1:
            raise ValueError("Missing or ambiguous JobKit application entry")
        apply = buttons.pop()
        parsed = urlsplit(apply)
        flags = ["publication_date_only"]
        if parsed.scheme == "mailto" or (
            not parsed.netloc and parsed.path == "/cdn-cgi/l/email-protection"
        ):
            apply = url
            flags.append("application_by_email")
        elif (
            parsed.scheme == "http"
            and parsed.hostname
            and not parsed.username
            and not parsed.password
        ):
            apply = url
            flags.append("application_http_source")
        elif (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in (None, 443)
        ):
            raise ValueError("Unsupported JobKit application URL")
        visible_labels = [li.get_text(" ", strip=True) for li in soup.select("main h1 + ul > li")]
        employment = row.get("employmentType")
        if isinstance(employment, list):
            employment = ", ".join(employment)
        place = row.get("jobLocation") or []
        if isinstance(place, dict):
            place = [place]
        address = [
            ", ".join(
                addr[k]
                for k in ("addressLocality", "addressRegion", "addressCountry")
                if addr.get(k)
            )
            for addr in (loc.get("address", {}) for loc in place)
        ]
        region = row.get("applicantLocationRequirements") or {}
        location = "; ".join(dict.fromkeys(x for x in address if x)) or region.get("name") or ""
        if not location:
            flags.append("location_missing")
        remote = "Remote" if row.get("jobLocationType") == "TELECOMMUTE" else None
        if any(re.match(r"^Hybrid(?:,|$)", label, re.I) for label in visible_labels):
            remote = "Hybrid"
        date = row["datePosted"]
        return [
            JobInput(
                external_id=identifier,
                title=title,
                company=company,
                description=description,
                location=location,
                source_url=url,
                application_url=apply,
                employment_type=employment,
                remote_status=remote,
                salary=row.get("baseSalary"),
                published_at=datetime.fromisoformat(date),
                quality_flags=flags,
                raw={
                    "published_at_original": date,
                    "valid_through_original": row.get("validThrough"),
                },
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("JobKit requires full public enumeration")
        return await self.http.read(self.origin + "/")

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)

        async def read(url: str) -> bytes:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        root = urljoin(self.origin, "/")
        before = self.roster(await read(root))
        result = []
        for identifier, url in before.items():
            result.extend(self.parse((identifier, url, await read(url))))
        if before != self.roster(await read(root)):
            raise ValueError("JobKit board changed during enumeration")
        return Enumeration(jobs=result, complete=True)


def public_document(body: bytes):
    if b"</html>" not in body.lower():
        raise ValueError("Truncated public job board HTML")
    return BeautifulSoup(body, "html.parser")

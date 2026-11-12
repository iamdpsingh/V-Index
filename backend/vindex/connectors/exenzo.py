"""Public Exenzo boards for the challenge's jobboardsoftware.com platform."""

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

BOARDS = {"agconnect.exenzo.nl": "/", "vacatures.ecommerce.nl": "/vacatures"}
JOB_PATH = re.compile(r"/vacatures?/[a-z0-9][a-z0-9-]{1,240}")
UUID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")


class ExenzoConnector:
    def __init__(self, slug: str, client: httpx.AsyncClient):
        if slug not in BOARDS:
            raise ValueError("Unreviewed Exenzo origin")
        self.origin = "https://" + slug
        self.search = self.origin + BOARDS[slug]
        self.legacy = slug == "agconnect.exenzo.nl"
        self.http = PublicHTTP(client, {slug})

    def roster(self, body: bytes) -> dict[str, str]:
        soup = document(body)
        if self.legacy:
            counters = soup.select("h3")
            pattern = r"([1-9][0-9]*) vacatures? gevonden"
            rows = soup.select(".row.job")
            selector, attr = "h2[itemprop=title] a[href]", "href"
        else:
            counters = soup.select(".filter-preview__title--bold")
            pattern = r"\(\s*([1-9][0-9]*) resultaten?\s*\)"
            rows = soup.select(".wrapper__job-card")
            selector, attr = "nuxt-link.job__card--title[to]", "to"
        totals = {
            int(match[1])
            for node in counters
            if (match := re.fullmatch(pattern, node.get_text(" ", strip=True)))
        }
        if totals != {len(rows)} or not 1 <= len(rows) <= 30:
            raise ValueError("Exenzo does not expose its full advertised roster on this page")
        for link in soup.select('a[rel="next"], a[href*="page="]'):
            if link.get("href") not in {"/vacatures?page=1", self.search + "?page=1"}:
                raise ValueError("Unsupported Exenzo pagination")
        result: dict[str, str] = {}
        for row in rows:
            links = row.select(selector)
            if len(links) != 1:
                raise ValueError("Missing Exenzo listing link")
            path = str(links[0][attr])
            title = links[0].get_text(" ", strip=True)
            if not JOB_PATH.fullmatch(path) or not title or path in result:
                raise ValueError("Malformed or repeated Exenzo listing")
            result[path] = title
        return result

    def parse(self, payload: Any) -> list[JobInput]:
        path, expected_title, body = payload
        soup = document(body)
        source = self.origin + path
        heading = soup.select("h1" if self.legacy else "h1.card__info__position")
        if len(heading) != 1 or heading[0].get_text(" ", strip=True) != expected_title:
            raise ValueError("Exenzo visible job title mismatch")
        robots = soup.select_one('meta[name="robots"]')
        if robots is not None and "noindex" in str(robots.get("content", "")).lower():
            raise ValueError("Exenzo job is excluded from indexing")
        postings = []
        for script in soup.select('script[type="application/ld+json"]'):
            item = json.loads(script.get_text())
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                postings.append(item)
        if len(postings) != 1:
            raise ValueError("Missing Exenzo JobPosting")
        posting = postings[0]
        identifier = posting.get("identifier")
        if (
            posting.get("url") != source
            or posting.get("title") != expected_title
            or not isinstance(identifier, str)
            or not UUID.fullmatch(identifier)
        ):
            raise ValueError("Conflicting Exenzo posting identity")
        company = text(posting.get("hiringOrganization", {}).get("name", ""))
        description = text(posting.get("description", ""))
        if not company or not description:
            raise ValueError("Incomplete Exenzo posting details")
        address = posting.get("jobLocation", {}).get("address", {})
        location = address.get("addressLocality") or address.get("addressCountry") or ""
        application = source
        if self.legacy:
            links = {
                str(anchor["href"])
                for anchor in soup.select("a.btn[href]")
                if anchor.get_text(" ", strip=True).casefold() == "solliciteren op deze functie"
            }
            if len(links) != 1:
                raise ValueError("Missing or conflicting Exenzo application link")
            application = links.pop()
            parsed = urlsplit(application)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.port not in (None, 443)
            ):
                raise ValueError("Invalid Exenzo application link")
        elif not soup.select_one("button.btn-action--apply"):
            raise ValueError("Missing Exenzo application entry")
        employment = posting.get("employmentType")
        if not employment:
            labels = soup.select(
                "td > span" if self.legacy else ".segments-card__segments-list .segment-item"
            )
            types = {
                value
                for label in labels
                if (value := label.get_text(" ", strip=True)).casefold() in {"fulltime", "parttime"}
            }
            employment = ", ".join(sorted(types)) or None
        date = posting.get("datePosted")
        salary = posting.get("baseSalary")
        if isinstance(salary, dict):
            values = salary.get("value")
            if not isinstance(values, dict):
                values = {"value": values}
            if not any(
                isinstance(value, (int, float))
                for value in (*values.values(), salary.get("minValue"), salary.get("maxValue"))
            ):
                salary = None
        return [
            JobInput(
                external_id=identifier,
                title=expected_title,
                company=company,
                description=description,
                location=location,
                source_url=source,
                application_url=application,
                employment_type=employment,
                salary=salary,
                published_at=datetime.fromisoformat(date) if date else None,
                remote_status="Remote" if posting.get("jobLocationType") == "TELECOMMUTE" else None,
                quality_flags=([] if location else ["location_missing"])
                + (["publication_timezone_unspecified"] if date else ["publication_date_missing"]),
                raw={"date_posted_original": date, "valid_through": posting.get("validThrough")},
            )
        ]

    async def fetch(self, cursor: int = 0) -> bytes:
        if cursor:
            raise ValueError("Only single-page Exenzo boards are supported")
        return await self.http.read(self.search)

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)

        async def read(url: str) -> bytes:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        before = self.roster(await read(self.search))
        jobs = []
        for path, title in before.items():
            jobs.extend(self.parse((path, title, await read(self.origin + path))))
        if (
            len({job.external_id for job in jobs}) != len(jobs)
            or self.roster(await read(self.search)) != before
        ):
            raise ValueError("Repeated or changed Exenzo public roster")
        return Enumeration(jobs=jobs, complete=True)

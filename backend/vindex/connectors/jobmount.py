"""Enumerate JobMount's public search pages and matching posting details."""

import asyncio
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

import httpx
from vindex.connectors.http import PublicHTTP
from vindex.connectors.jobboardio import document
from vindex.connectors.jobiqo import structured_postings
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.schemas import Enumeration, JobInput

HOSTS = {"soudeur.ca", "www.jobsrus.com"}
SEARCH = "/candidate/job_search/quick/results"
POSTING = re.compile(r"/(?:emploi|career)/([1-9]\d{0,15})/[^/?#]+/?")
MAX_PAGES = 100


class JobMountConnector:
    def __init__(self, host: str, client: httpx.AsyncClient):
        if host not in HOSTS:
            raise ValueError("Unreviewed JobMount origin")
        self.origin = f"https://{host}"
        self.http = PublicHTTP(client, {host})

    async def roster(self, policy: RobotsPolicy) -> dict[str, str]:
        result: dict[str, str] = {}
        for offset in range(MAX_PAGES):
            path = SEARCH if not offset else f"{SEARCH}/{offset}"
            url = self.origin + path
            policy.check(url)
            await asyncio.sleep(policy.delay())
            page = document(await self.http.read(url))
            jobs = {
                match[1]: self.origin + str(anchor["href"])
                for anchor in page.select("h3 a[href]")
                if (match := POSTING.fullmatch(str(anchor["href"])))
            }
            if not jobs or result.keys() & jobs.keys():
                raise ValueError("Empty or repeated JobMount roster page")
            result.update(jobs)
            next_paths = {
                str(anchor["href"])
                for anchor in page.select("a[href]")
                if anchor.get_text(" ", strip=True).casefold() in {"next", "suiv."}
                and str(anchor["href"]).startswith(SEARCH + "/")
            }
            if not next_paths:
                total = page.find(string=re.compile(r"Votre recherche a généré \d+ résultats"))
                if (
                    total
                    and (match := re.search(r"\d+", str(total)))
                    and int(match[0]) != len(result)
                ):
                    raise ValueError("JobMount advertised total differs from roster")
                return result
            if next_paths != {f"{SEARCH}/{offset + 1}"}:
                raise ValueError("Unexpected JobMount next page")
        raise ValueError("JobMount exceeded its page limit")

    async def detail(self, identifier: str, url: str, policy: RobotsPolicy) -> JobInput:
        policy.check(url)
        await asyncio.sleep(policy.delay())
        return self.parse((identifier, url, await self.http.read(url)))[0]

    async def fetch(self, cursor: int = 0) -> bytes:
        path = SEARCH if not cursor else f"{SEARCH}/{cursor}"
        policy = await RobotsPolicy.load(self.http, self.origin)
        policy.check(self.origin + path)
        return await self.http.read(self.origin + path)

    def parse(self, payload: Any) -> list[JobInput]:
        identifier, url, body = payload
        page = document(body)
        postings = structured_postings(page)
        if len(postings) != 1:
            raise ValueError(f"Missing unique JobMount posting {identifier}")
        row = postings[0]
        published_url = page.select_one('meta[property="og:url"][content]')
        detail_path = urlsplit(str(published_url["content"])).path if published_url else ""
        match = POSTING.fullmatch(detail_path)
        if not match or match[1] != identifier:
            raise ValueError(f"JobMount posting identity mismatch for {identifier}")
        forms = {
            match[0]
            for control in page.select('input[name="apply"][onclick]')
            if (
                match := re.search(
                    rf"/main/sendform/\d+/\d+/\d+/1/{identifier}(?=['\"])", str(control["onclick"])
                )
            )
        }
        if not forms and not re.search(rf"vacancy(?:Redirect)?Apply\({identifier},", str(page)):
            raise ValueError(f"Missing JobMount application entry for {identifier}")
        description = text(row.get("description") or "")
        company = text((row.get("hiringOrganization") or {}).get("name") or "")
        title = text(row.get("title") or "")
        if not title or not company or not description:
            raise ValueError(f"Incomplete JobMount details for {identifier}")
        address = (row.get("jobLocation") or {}).get("address") or {}
        location = ", ".join(
            str(address[field])
            for field in ("addressLocality", "addressRegion", "addressCountry")
            if address.get(field) and address[field] != "Not specified"
        )
        posted = row.get("datePosted")
        employment = row.get("employmentType")
        return [
            JobInput(
                external_id=identifier,
                title=title,
                company=company,
                description=description,
                location=location,
                source_url=url,
                application_url=self.origin + next(iter(forms)) if len(forms) == 1 else url,
                published_at=datetime.fromisoformat(posted) if posted else None,
                employment_type=", ".join(employment)
                if isinstance(employment, list)
                else employment,
                salary=row.get("baseSalary"),
                raw={"valid_through": row.get("validThrough")},
            )
        ]

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)
        roster = await self.roster(policy)
        jobs = [await self.detail(identifier, url, policy) for identifier, url in roster.items()]
        if await self.roster(policy) != roster:
            raise ValueError("JobMount roster changed during extraction")
        return Enumeration(jobs=jobs, complete=True)

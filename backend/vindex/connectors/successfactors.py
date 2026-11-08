"""SAP SuccessFactors Career Site Builder public search and detail pages."""

import asyncio
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
from vindex.connectors.http import PublicHTTP
from vindex.connectors.jobboardio import document
from vindex.connectors.robots import RobotsPolicy
from vindex.schemas import Enumeration, JobInput

HOSTS = frozenset({"careers.icbc.com", "careers.kaust.edu.sa"})
JOB_PATH = r"/job/[A-Za-z0-9][A-Za-z0-9_.~%&()+,-]*/([1-9][0-9]{0,17})/"


class SuccessFactorsConnector:
    def __init__(self, slug: str, client: httpx.AsyncClient):
        if slug not in HOSTS:
            raise ValueError("Unreviewed SuccessFactors Career Site Builder origin")
        self.origin = f"https://{slug}"
        self.search_url = self.origin + "/search/"
        self.http = PublicHTTP(client, {slug})

    def roster(self, body: bytes) -> dict[str, str]:
        soup = document(body)
        labels = {n.get_text(" ", strip=True) for n in soup.select(".paginationLabel")}
        if len(labels) != 1:
            raise ValueError("Missing SuccessFactors search total")
        m = re.fullmatch(r"Results 1 [–-] ([1-9][0-9]*) of ([1-9][0-9]*)", labels.pop())
        if not m or m[1] != m[2] or int(m[2]) > 50:
            raise ValueError("SuccessFactors public search requires complete single-page results")
        rows: dict[str, str] = {}
        for a in soup.select("a.jobTitle-link[href]"):
            path = str(a["href"])
            match = re.fullmatch(JOB_PATH, path)
            if not match or re.search(r"%(?:2f|5c|00|2e)", path, re.I):
                raise ValueError("Unscoped SuccessFactors result")
            url = self.origin + path
            if match[1] in rows and rows[match[1]] != url:
                raise ValueError("Conflicting SuccessFactors result URLs")
            rows[match[1]] = url
        if len(rows) != int(m[2]) or soup.select('a[rel="next"], link[rel="next"]'):
            raise ValueError("SuccessFactors listing count does not match public total")
        return rows

    def parse(self, payload: Any) -> list[JobInput]:
        identifier, url, body = payload
        soup = document(body)
        directives = soup.select('meta[name="robots" i][content]')
        if any(
            re.search(r"\b(?:noindex|none)\b", str(n.get("content", "")), re.I) for n in directives
        ):
            raise ValueError("SuccessFactors detail opts out of indexing")
        canonical = soup.select('link[rel="canonical"]')
        scopes = soup.select('[itemscope][itemtype$="/JobPosting"]')
        if len(canonical) != 1 or canonical[0].get("href") != url or len(scopes) != 1:
            raise ValueError("Missing canonical SuccessFactors JobPosting")
        scope = scopes[0]

        def field(name: str) -> str:
            nodes = scope.select(f'[itemprop="{name}"]')
            values = {str(n.get("content") or n.get_text(" ", strip=True)).strip() for n in nodes}
            values.discard("")
            if len(values) > 1:
                raise ValueError(f"Ambiguous SuccessFactors {name}")
            return next(iter(values), "")

        title, company, description = (
            field("title"),
            field("hiringOrganization"),
            field("description"),
        )
        if not title or not company or not description:
            raise ValueError("Incomplete SuccessFactors title, employer or description")
        apply_path = f"/talentcommunity/apply/{identifier}/"
        apply_links = set()
        for anchor in soup.select("a.dialogApplyBtn[href]"):
            href = str(anchor["href"])
            parsed = urlsplit(href)
            query = parse_qs(parsed.query, keep_blank_values=True)
            if (
                parsed.path != apply_path
                or parsed.netloc
                or parsed.scheme
                or parsed.fragment
                or (
                    query
                    and (
                        set(query) != {"locale"}
                        or len(query["locale"]) != 1
                        or not re.fullmatch(r"[a-z]{2}_[A-Z]{2}", query["locale"][0])
                    )
                )
            ):
                raise ValueError("Unexpected SuccessFactors application target")
            apply_links.add(href)
        if len(apply_links) != 1:
            raise ValueError("Missing or ambiguous same-ID SuccessFactors apply link")
        apply = apply_links.pop()
        location = "; ".join(
            dict.fromkeys(
                value
                for node in soup.select(".jobGeoLocation")
                if (value := node.get_text(" ", strip=True))
            )
        ) or field("jobLocation")
        date = field("datePosted")
        published = (
            datetime.strptime(date, "%a %b %d %H:%M:%S UTC %Y").replace(tzinfo=UTC)
            if date
            else None
        )
        flags = ([] if location else ["location_missing"]) + (
            [] if date else ["publication_date_missing"]
        )
        return [
            JobInput(
                external_id=identifier,
                title=title,
                company=company,
                description=description,
                location=location,
                source_url=url,
                application_url=self.origin + apply,
                published_at=published,
                employment_type=field("employmentType") or None,
                remote_status="Remote" if field("jobLocationType") == "TELECOMMUTE" else None,
                quality_flags=flags,
                raw={"published_at_original": date or None},
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("Unsupported SuccessFactors cursor")
        return await self.http.read(self.search_url)

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)

        async def read(url: str) -> bytes:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        before = self.roster(await read(self.search_url))
        jobs = []
        for identifier, url in before.items():
            path = urlsplit(url).path
            if not path.endswith(f"/{identifier}/"):
                raise ValueError("SuccessFactors detail identifier mismatch")
            jobs.extend(self.parse((identifier, url, await read(url))))
        if before != self.roster(await read(self.search_url)):
            raise ValueError("SuccessFactors roster changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

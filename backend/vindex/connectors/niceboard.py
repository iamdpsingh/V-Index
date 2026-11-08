"""Niceboard's public job sitemap and published listing pages."""

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

HOSTS = frozenset({"jobs.aiacolorado.org", "jobs.medicalalley.org"})
JOB_PATH = r"/job/([1-9][0-9]{0,17})-[a-z0-9][a-z0-9-]*"


class NiceboardConnector:
    def __init__(self, slug: str, client: httpx.AsyncClient):
        if slug not in HOSTS:
            raise ValueError("Unreviewed Niceboard origin")
        self.origin = "https://" + slug
        self.http = PublicHTTP(client, {slug})

    def roster(self, index: bytes, jobs: bytes) -> dict[str, str]:
        index_urls = xml_urls(index, index=True)
        expected = {
            self.origin + "/sitemap-" + kind + ".xml" for kind in ("base", "jobs", "companies")
        }
        if set(index_urls) != expected:
            raise ValueError("Unexpected Niceboard sitemap index")
        result = {}
        for url in xml_urls(jobs, index=False):
            match = re.fullmatch(re.escape(self.origin) + JOB_PATH, url)
            if not match or match[1] in result:
                raise ValueError("Unscoped or duplicate Niceboard job URL")
            result[match[1]] = url
        if not 0 < len(result) <= 200:
            raise ValueError("Niceboard roster outside supported bounds")
        return result

    def parse(self, payload: Any) -> list[JobInput]:
        identifier, url, body = payload
        soup = document(body)
        canonical = soup.select('link[rel="canonical"]')
        scripts = [
            script.get_text().split("var job_json = ", 1)[1]
            for script in soup.select("script:not([src])")
            if re.match(
                r"\s*var is_default_translation = [^;]+;\s*var job_json = ", script.get_text()
            )
        ]
        if len(canonical) != 1 or canonical[0].get("href") != url or len(scripts) != 1:
            raise ValueError("Missing canonical Niceboard detail")
        row, end = json.JSONDecoder().raw_decode(scripts[0])
        if not scripts[0][end:].startswith(";") or str(row["id"]) != identifier:
            raise ValueError("Niceboard detail identity mismatch")
        if (
            row["is_published"] is not True
            or row["is_draft"] is not False
            or row["is_sample"] is not False
        ):
            raise ValueError("Niceboard detail is not a published production job")
        if any(type(row[key]) is not bool for key in ("is_filled", "is_expired")):
            raise ValueError("Unknown Niceboard job state")
        if row["is_filled"] or row["is_expired"]:
            # Positive state from the posting itself, never an HTTP error or a missing page.
            return []
        employers = soup.select(".full-job h2.company-name")
        title = text(row["title"])
        description = text(row["description_html"])
        company = text(row["company"]["name"])
        if (
            len(employers) != 1
            or employers[0].get_text(" ", strip=True) != company
            or not title
            or not description
        ):
            raise ValueError("Incomplete Niceboard detail")
        flags = []
        application = row.get("apply_url")
        if row.get("apply_by_form") is True:
            application = url
        elif not application and row.get("apply_email"):
            application = url
            flags.append("application_by_email")
        elif application and urlsplit(application).scheme == "http":
            application = url
            flags.append("application_http_source")
        if not application:
            if not text(row.get("how_to_apply") or ""):
                raise ValueError("No Niceboard application instructions")
            application = url
        parsed = urlsplit(application)
        if (
            parsed.username is not None
            or parsed.password is not None
            or parsed.port not in (None, 443)
        ):
            raise ValueError("Unsafe Niceboard application URL")
        salary = None
        if row.get("show_salary") is True:
            salary = {
                key: row[field]
                for key, field in (
                    ("min", "salary_min"),
                    ("max", "salary_max"),
                    ("currency", "salary_currency"),
                    ("unit", "salary_timeframe"),
                    ("text", "salary_description"),
                )
                if row.get(field) is not None
            }
            if not any(k in salary for k in ("min", "max", "text")):
                salary = None
        location = row.get("location_name") or row.get("remote_required_location") or ""
        if not location:
            flags.append("location_missing")
        date = row["published_at"]
        return [
            JobInput(
                external_id=identifier,
                title=title,
                company=company,
                description=description,
                location=location,
                source_url=url,
                application_url=application,
                employment_type=(row.get("jobtype") or {}).get("name"),
                remote_status="Remote" if row.get("remote_only") is True else None,
                salary=salary,
                published_at=datetime.fromisoformat(date),
                quality_flags=flags,
                raw={
                    "published_at_original": date,
                    "expires_on_original": row.get("expires_on"),
                    "remote_available": row.get("is_remote"),
                    "remote_only": row.get("remote_only"),
                    "remote_required_location": row.get("remote_required_location"),
                },
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("Niceboard requires full public enumeration")
        return await self.discover()

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)
        index = self.origin + "/sitemap.xml"
        jobs = self.origin + "/sitemap-jobs.xml"
        if index not in (policy.parser.site_maps() or []):
            raise ValueError("Niceboard sitemap not advertised in robots.txt")

        async def read(url: str) -> bytes:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        async def roster() -> dict[str, str]:
            raw_index = await read(index)
            if jobs not in xml_urls(raw_index, index=True):
                raise ValueError("Niceboard jobs map not advertised")
            return self.roster(raw_index, await read(jobs))

        before = await roster()
        result = []
        for identifier, url in before.items():
            result.extend(self.parse((identifier, url, await read(url))))
        if not result or before != await roster():
            raise ValueError("Niceboard public roster empty or changed")
        return Enumeration(jobs=result, complete=True)

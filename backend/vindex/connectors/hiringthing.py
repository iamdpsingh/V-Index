"""HiringThing hosted public HTML/RSS rosters and sanitized React job observations."""

import asyncio
import json
import re
from typing import Any
from urllib.parse import urlsplit

import httpx
from bs4 import BeautifulSoup
from defusedxml import ElementTree as ET
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.connectors.teamtailor import TENANT
from vindex.schemas import Enumeration, JobInput


class HiringThingConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider != "hiringthing" or not re.fullmatch(TENANT, slug):
            raise ValueError("Invalid HiringThing tenant")
        self.origin = f"https://{slug}.hiringthing.com"
        self.metadata_hosts = {f"{slug}.hiringthing.com", f"{slug}.oasisrecruit.com"}
        self.http = PublicHTTP(client, {f"{slug}.hiringthing.com"})

    def path(self, value: str) -> str:
        p = urlsplit(value)
        if (
            p.query
            or p.fragment
            or p.netloc
            and (p.scheme != "https" or p.netloc not in self.metadata_hosts)
            or not p.netloc
            and p.scheme
            or not re.fullmatch(r"/job/[1-9][0-9]*/[a-z0-9-]+", p.path)
        ):
            raise ValueError("Invalid HiringThing native job link")
        return p.path

    def listings(self, body: bytes) -> tuple[str, dict[str, str]]:
        if b"</html>" not in body.lower():
            raise ValueError("Truncated HiringThing board")
        soup = BeautifulSoup(body, "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else ""
        if not title.endswith(" Career Opportunities") or not any(
            h.get_text(" ", strip=True) == "Career Opportunities" for h in soup.select("h1")
        ):
            raise ValueError("Missing named HiringThing career collection")
        if soup.select('a[rel="next"],.pagination,nav[aria-label="Pagination"]'):
            raise ValueError("HiringThing paginated template unsupported")
        rows: dict[str, str] = {}
        paths = set()
        for anchor in soup.select("a[href]"):
            url = str(anchor["href"])
            if not url.startswith("/job/"):
                continue
            path = self.path(url)
            paths.add(path)
            label = anchor.get_text(" ", strip=True)
            if label in {"Learn more", "Apply", ""}:
                continue
            if path in rows and rows[path] != label:
                raise ValueError("Ambiguous HiringThing listed title")
            rows[path] = label
        if not 0 < len(rows) <= 400 or set(rows) != paths:
            raise ValueError("HiringThing empty, ambiguous or oversized roster")
        return title.removesuffix(" Career Opportunities"), rows

    def feed(self, body: bytes, company: str, rows: dict[str, str]) -> dict[str, dict]:
        root = ET.fromstring(body, forbid_dtd=True, forbid_entities=True)
        channel = root.find("channel")
        if root.tag != "rss" or channel is None or channel.findtext("title") != company + " Jobs":
            raise ValueError("HiringThing RSS employer identity mismatch")
        channel_url = urlsplit(channel.findtext("link") or "")
        if (
            channel_url.scheme != "https"
            or channel_url.netloc not in self.metadata_hosts
            or channel_url.path not in ("", "/")
            or channel_url.query
            or channel_url.fragment
        ):
            raise ValueError("HiringThing RSS channel host is unsupported")
        result = {}
        for item in channel.findall("item"):
            link = item.findtext("link") or ""
            path = self.path(link)
            if (
                urlsplit(link).scheme != "https"
                or urlsplit(link).netloc != channel_url.netloc
                or path in result
                or item.findtext("title") != rows.get(path)
            ):
                raise ValueError("HiringThing RSS/list job identity mismatch")
            result[path] = {
                "title": item.findtext("title"),
                "source_url": link,
                "location": item.findtext("location") or "",
                "description_html": item.findtext("{http://search.yahoo.com/mrss/}description"),
                "xml": ET.tostring(item, encoding="unicode"),
            }
            if not isinstance(result[path]["description_html"], str):
                raise ValueError("Missing full HiringThing media description")
        if set(result) != set(rows):
            raise ValueError("HiringThing RSS and full HTML roster disagree")
        return result

    def parse(self, payload: Any) -> list[JobInput]:
        path, company, feed, body = payload
        identifier = int(path.split("/")[2])
        url = self.origin + path
        if b"</html>" not in body.lower():
            raise ValueError("Truncated HiringThing detail")
        soup = BeautifulSoup(body, "html.parser")
        canonical = soup.select_one('link[rel="canonical"]')
        heading = soup.select_one(".job-title-container h2")
        og = soup.select_one('meta[property="og:url"]')
        groups = soup.select('[data-react-class="HiringThing.Components.ApplyButtonGroup"]')
        observed = []
        for group in groups:
            props = json.loads(str(group["data-react-props"]))
            observed.append(props["jobObj"]["table"])
        if (
            not observed
            or canonical is None
            or canonical.get("href") != feed["source_url"]
            or og is None
            or og.get("content") != feed["source_url"]
            or heading is None
            or heading.get_text(" ", strip=True) != feed["title"]
        ):
            raise ValueError("HiringThing detail canonical/title/application identity mismatch")
        job = observed[0]
        if any(row != job for row in observed):
            raise ValueError("HiringThing application components disagree")
        if (
            type(job["id"]) is not int
            or job["id"] != identifier
            or job["title"] != feed["title"]
            or job["company_name"] != company
            or job["url"] != path
            or job["joblink_url"] != feed["source_url"]
            or job["hidden?"] is not False
        ):
            raise ValueError("HiringThing public application job identity/visibility mismatch")
        schemas = [
            json.loads(s.get_text()) for s in soup.select('script[type="application/ld+json"]')
        ]
        schemas = [s for s in schemas if isinstance(s, dict) and s.get("@type") == "JobPosting"]
        if len(schemas) > 1:
            raise ValueError("Ambiguous HiringThing JobPosting documents")
        schema = schemas[0] if schemas else None
        if schema and (
            schema["title"] != job["title"] or schema["hiringOrganization"]["name"] != company
        ):
            raise ValueError("HiringThing source JobPosting identity mismatch")
        employment = schema.get("employmentType") if schema else None
        if isinstance(employment, list):
            employment = ", ".join(employment)
        description = text(job["html_description"])
        if " ".join(description.split()) != " ".join(text(feed["description_html"]).split()):
            raise ValueError("HiringThing RSS/detail descriptions changed")
        salary = (
            {k: job[k] for k in ("min_salary", "max_salary", "pay_frequency")}
            if job["min_salary"] or job["max_salary"]
            else None
        )
        safe = {
            "id",
            "company_id",
            "company_name",
            "title",
            "html_description",
            "url",
            "joblink_url",
            "posted_at",
            "location",
            "location_info",
            "job_code",
            "category",
            "remote",
            "max_salary",
            "min_salary",
            "pay_frequency",
            "hidden?",
        }
        return [
            JobInput(
                external_id=str(identifier),
                title=job["title"],
                company=company,
                description=description,
                quality_flags=[] if description else ["description_missing"],
                location=job["location"] or feed["location"],
                source_url=url,
                application_url=url,
                salary=salary,
                employment_type=employment,
                remote_status="Remote" if job["remote"] is True else None,
                published_at=job["posted_at"],
                raw={
                    "rss": feed,
                    "job": {k: v for k, v in job.items() if k in safe},
                    "application_entry": "native_apply_button_group",
                    "jobposting": schema,
                },
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("HiringThing paginated template unsupported")
        return await self.http.read(self.origin + "/")

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)

        async def read(url: str) -> bytes:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        company, rows = self.listings(await read(self.origin + "/"))
        feed = self.feed(await read(self.origin + "/api/rss.xml"), company, rows)
        jobs = []
        for path, item in feed.items():
            jobs.extend(self.parse((path, company, item, await read(self.origin + path))))
        if (
            self.listings(await read(self.origin + "/")) != (company, rows)
            or self.feed(await read(self.origin + "/api/rss.xml"), company, rows) != feed
        ):
            raise ValueError("HiringThing complete roster/feed changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

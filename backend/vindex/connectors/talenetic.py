"""Reviewed Talenetic boards: advertised job sitemaps and full native details."""

import asyncio
import json
import re
from typing import Any
from urllib.parse import urlsplit
from xml.etree.ElementTree import ParseError

import httpx
from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException
from vindex.connectors.http import PublicHTTP
from vindex.connectors.jobboardio import document
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.schemas import Enumeration, JobInput

HOSTS = frozenset({"jobs.medicalupdateonline.com", "www.procontractjobs.com"})
NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
MAX_JOBS = 50_000
JOB_PATH = re.compile(r"/(?:job-detail|jobs)/([1-9][0-9]{0,12})/[^/?#]{1,500}/")
MAP_PATH = re.compile(r"/sitemap-job-pages-([1-9][0-9]{0,2})\.xml")


class TaleneticConnector:
    def __init__(self, host: str, client: httpx.AsyncClient):
        if host not in HOSTS:
            raise ValueError("Unknown Talenetic board")
        self.host = host
        self.origin = "https://" + host
        self.http = PublicHTTP(client, {host})
        self._read_lock = asyncio.Lock()

    def scoped(self, url: str) -> str:
        p = urlsplit(url)
        if p.scheme != "https" or p.netloc != self.host or p.query or p.fragment:
            raise ValueError("Unscoped Talenetic URL")
        return p.path

    def identifier(self, url: str) -> str:
        match = JOB_PATH.fullmatch(self.scoped(url))
        if not match:
            raise ValueError("Invalid Talenetic job URL")
        return match[1]

    async def read(self, url: str, policy: RobotsPolicy) -> bytes:
        self.scoped(url)
        policy.check(url)
        # Concurrent detail requests share one start-rate budget per source.
        async with self._read_lock:
            await asyncio.sleep(policy.delay())
        return await self.http.read(url)

    def xml_urls(self, body: bytes, *, index: bool) -> list[str]:
        try:
            root = ElementTree.fromstring(body)
        except (ParseError, DefusedXmlException) as error:
            raise ValueError("Malformed or unsafe Talenetic sitemap") from error
        kind = "sitemapindex" if index else "urlset"
        namespaces = (NS, "{https://www.sitemaps.org/schemas/sitemap/0.9}")
        if root.tag not in {ns + kind for ns in namespaces}:
            raise ValueError("Unexpected Talenetic sitemap root")
        namespace = root.tag[: -len(kind)]
        rows = root.findall(namespace + ("sitemap" if index else "url"))
        if not 0 < len(rows) <= (100 if index else 10_000):
            raise ValueError("Empty or oversized Talenetic sitemap")
        urls = []
        for row in rows:
            locs = row.findall(namespace + "loc")
            if len(locs) != 1 or not locs[0].text:
                raise ValueError("Missing Talenetic sitemap URL")
            url = locs[0].text
            self.scoped(url)
            urls.append(url)
        if len(set(urls)) != len(urls):
            raise ValueError("Repeated Talenetic sitemap URL")
        return urls

    async def fetch(self, cursor: int = 0) -> bytes:
        if cursor:
            raise ValueError("Talenetic uses sitemap pagination")
        policy = await RobotsPolicy.load(self.http, self.origin)
        return await self.read(self.origin + "/sitemap-index.xml", policy)

    async def roster(self, policy: RobotsPolicy) -> dict[str, str]:
        index = self.origin + "/sitemap-index.xml"
        if index not in (policy.parser.site_maps() or []):
            raise ValueError("Talenetic sitemap is not advertised")
        maps = []
        for url in self.xml_urls(await self.read(index, policy), index=True):
            path = self.scoped(url)
            match = MAP_PATH.fullmatch(path)
            if match:
                maps.append((int(match[1]), url))
            elif path not in {
                "/sitemap-news-pages.xml",
                "/sitemap-advice-pages.xml",
                "/sitemap-pages.xml",
            }:
                raise ValueError("Unknown Talenetic sitemap partition")
        maps.sort()
        if not maps or [n for n, _ in maps] != list(range(1, len(maps) + 1)):
            raise ValueError("Missing Talenetic sitemap partition")
        result = {}
        home_entries = 0
        for _, url in maps:
            for entry in self.xml_urls(await self.read(url, policy), index=False):
                if self.scoped(entry) in {"", "/"}:
                    home_entries += 1
                    if home_entries > 1:
                        raise ValueError("Repeated Talenetic sitemap home entry")
                    continue
                identifier = self.identifier(entry)
                if identifier in result:
                    raise ValueError("Repeated Talenetic job identity")
                result[identifier] = entry
                if len(result) > MAX_JOBS:
                    raise ValueError("Talenetic roster exceeds bounded snapshot")
        return result

    def parse(self, payload: tuple[str, bytes]) -> list[JobInput]:
        url, body = payload
        identifier = self.identifier(url)
        soup = document(body)
        if "Talenetic Job Board Software" not in soup.get_text(" ", strip=True):
            raise ValueError("Missing Talenetic platform marker")
        postings = []
        for node in soup.select('script[type="application/ld+json"]'):
            row = json.loads(node.get_text())
            if isinstance(row, dict) and str(row.get("@type", "")).lower() == "jobposting":
                postings.append(row)
        expired = soup.select("h1.expired-title")
        if expired:
            identities = soup.select("input#externalvacncyid")
            headings = soup.select("h2.job-title")
            if (
                len(expired) != 1
                or expired[0].get_text(" ", strip=True) != "This job has expired"
                or len(identities) != 1
                or identities[0].get("value") != identifier
                or len(postings) != 1
                or len(headings) != 1
                or text(postings[0]["title"]) != headings[0].get_text(" ", strip=True)
            ):
                raise ValueError("Unverified Talenetic expired posting")
            return []
        titles = soup.select('[itemprop="title"]')
        descriptions = soup.select(".job_description_hold")
        if len(postings) != 1 or len(titles) != 1 or len(descriptions) != 1:
            raise ValueError("Missing complete Talenetic posting")
        row = postings[0]
        title, description = text(row["title"]), text(row["description"])
        if (
            not title
            or title != titles[0].get_text(" ", strip=True)
            or not description
            or "".join(description.split()) != "".join(text(str(descriptions[0])).split())
        ):
            raise ValueError("Talenetic structured/native fields disagree")

        def value(field: str) -> str:
            nodes = soup.select(f"input#{field}")
            if len(nodes) != 1:
                raise ValueError("Missing or ambiguous Talenetic posting field")
            return str(nodes[0].get("value", "")).strip()

        if value("externaljobtitle") != title:
            raise ValueError("Talenetic application title mismatch")
        company = text(row["hiringOrganization"]["name"])
        if not company or company != value("externalcompanyname"):
            raise ValueError("Talenetic employer identity mismatch")
        if not soup.select(f"#shortlist{identifier}, [data-vacancy='{identifier}']"):
            raise ValueError("Talenetic native job identity mismatch")
        if not any("apply" in a.get_text().lower() for a in soup.select("a,button")):
            raise ValueError("Missing Talenetic application control")
        targets = {v for v in (value("externalurl"), value("directurl")) if v}
        if len(targets) > 1:
            raise ValueError("Conflicting Talenetic application destinations")
        application = next(iter(targets), url)
        flags = []
        if company.casefold() == "partner jobs":
            flags.append("publisher_supplied_company_label")
        if not targets:
            flags.append("application_on_source_page")
        location = row.get("jobLocation") or {}
        if not isinstance(location, dict):
            raise ValueError("Unsupported Talenetic location shape")
        address = location.get("address") or {}
        locations = [
            address[k]
            for k in ("addressLocality", "addressRegion", "addressCountry")
            if isinstance(address.get(k), str) and address[k]
        ]
        salary: dict[str, Any] | None = row.get("baseSalary") or None
        employment_nodes = soup.select('dd[itemprop="employmentType"]')
        if len(employment_nodes) > 1:
            raise ValueError("Ambiguous Talenetic native employment type")
        native_employment = (
            employment_nodes[0].get_text(" ", strip=True) if employment_nodes else ""
        )
        employment = row.get("employmentType") or native_employment or None
        if isinstance(employment, list) and all(isinstance(value, str) for value in employment):
            employment = "; ".join(dict.fromkeys(employment)) or None
        return [
            JobInput(
                external_id=identifier,
                title=title,
                company=company,
                description=description,
                location=", ".join(dict.fromkeys(locations)),
                source_url=url,
                application_url=application,
                employment_type=employment,
                remote_status="Remote" if row.get("jobLocationType") == "TELECOMMUTE" else None,
                salary=salary,
                published_at=row.get("datePosted"),
                quality_flags=flags,
                raw={
                    "job_posting": row,
                    "native_employment_html": str(employment_nodes[0])
                    if employment_nodes
                    else None,
                    "application_entry": "Native posting application control",
                },
            )
        ]

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)
        roster = await self.roster(policy)
        jobs = []
        for url in roster.values():
            jobs.extend(self.parse((url, await self.read(url, policy))))
        if await self.roster(policy) != roster:
            raise ValueError("Talenetic roster changed during extraction")
        return Enumeration(jobs=jobs, complete=True)

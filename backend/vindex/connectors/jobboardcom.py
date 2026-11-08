"""JobBoard.com (HotLizard) public published sitemaps and job detail pages."""

import asyncio
import json
import re
from datetime import datetime
from typing import Any
from urllib.parse import parse_qs, urljoin, urlsplit
from xml.etree.ElementTree import ParseError

import httpx
from bs4 import BeautifulSoup
from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.schemas import Enumeration, JobInput

HOSTS = frozenset({"jobs.acevo.org.uk", "www.gradsouthwest.com"})
NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
MAX_JOBS = 200


def document(body: bytes) -> BeautifulSoup:
    if b"</html>" not in body.lower():
        raise ValueError("Truncated public HTML document")
    return BeautifulSoup(body, "html.parser")


class JobBoardComConnector:
    def __init__(self, slug: str, client: httpx.AsyncClient):
        if slug not in HOSTS:
            raise ValueError("Unreviewed JobBoard.com origin")
        self.host = slug
        self.origin = "https://" + slug
        self.http = PublicHTTP(client, {slug})
        self.job_path = re.compile(
            rf"^{re.escape(self.origin)}/jobs/([a-z0-9][a-z0-9-]*)/([1-9][0-9]*)-1/$"
        )

    def roster(self, index_body: bytes, jobs_body: bytes) -> dict[str, str]:
        try:
            index_root = ElementTree.fromstring(index_body)
        except (ParseError, DefusedXmlException) as error:
            raise ValueError("Malformed public sitemap index") from error
        if index_root.tag != NS + "sitemapindex":
            raise ValueError("Unexpected public sitemap index document")
        sitemaps = [
            loc.text
            for s in index_root.findall(NS + "sitemap")
            for loc in s.findall(NS + "loc")
            if loc.text
        ]
        expected_sitemap = f"{self.origin}/xml-sitemaps/1.xml"
        if sitemaps != [expected_sitemap]:
            raise ValueError("JobBoard.com jobs sitemap not found in sitemap index")

        try:
            jobs_root = ElementTree.fromstring(jobs_body)
        except (ParseError, DefusedXmlException) as error:
            raise ValueError("Malformed public jobs sitemap") from error
        if jobs_root.tag != NS + "urlset":
            raise ValueError("Unexpected public jobs sitemap document")

        jobs: dict[str, str] = {}
        for u in jobs_root.findall(NS + "url"):
            locs = u.findall(NS + "loc")
            if len(locs) != 1 or not locs[0].text:
                raise ValueError("Missing or duplicated location in jobs sitemap")
            loc = locs[0].text
            match = self.job_path.fullmatch(loc)
            if not match:
                path = urlsplit(loc).path
                if re.fullmatch(r"/jobs/[^/]+/[0-9]+(?:-[0-9]+)?/?", path):
                    raise ValueError("Unsupported job detail URL in JobBoard.com sitemap")
                continue
            identifier = match.group(2) + "-1"
            if identifier in jobs:
                raise ValueError("Duplicate job identifier in JobBoard.com sitemap")
            jobs[identifier] = loc

        if not 0 < len(jobs) <= MAX_JOBS:
            raise ValueError("JobBoard.com roster outside supported bounds")
        return jobs

    def parse(self, payload: Any) -> list[JobInput]:
        identifier, url, body = payload
        match = self.job_path.fullmatch(url)
        if not match or match.group(2) + "-1" != identifier:
            raise ValueError("JobBoard.com job URL does not match identifier")

        soup = document(body)
        canonical = soup.select('link[rel="canonical"]')
        if len(canonical) != 1 or canonical[0].get("href") != url:
            raise ValueError("Missing or mismatched canonical link in JobBoard.com posting")

        hl_links = [
            a.get("href") for a in soup.select('a[href*="jobboard.com"], a[href*="hotlizard.net"]')
        ]
        if not hl_links:
            raise ValueError("Missing JobBoard.com / HotLizard platform attribution")

        ld_nodes = soup.select('script[type="application/ld+json"]')
        postings = []
        for node in ld_nodes:
            try:
                data = json.loads(node.get_text())
                if isinstance(data, dict) and data.get("@type") == "JobPosting":
                    postings.append(data)
            except Exception:
                pass
        if len(postings) != 1:
            raise ValueError(f"Expected exactly 1 JobPosting schema, found {len(postings)}")

        row = postings[0]
        if row.get("url") and row.get("url") != url:
            raise ValueError("JobPosting schema URL mismatch")

        title = text(str(row.get("title", "")))
        org = row.get("hiringOrganization")
        company = text(str(org.get("name", ""))) if isinstance(org, dict) else ""
        description = text(str(row.get("description", "")))
        if not title or not company or not description:
            raise ValueError("Missing required title, company, or description")

        location = ""
        loc_obj = row.get("jobLocation")
        if isinstance(loc_obj, dict):
            addr = loc_obj.get("address")
            addr_locality = addr.get("addressLocality") if isinstance(addr, dict) else ""
            location = text(str(loc_obj.get("name") or addr_locality or ""))
        flags = []
        if not location:
            flags.append("location_missing")

        apply_links = set()
        for a in soup.select('a[href*="/jobs/apply/"]'):
            apply_url = urljoin(self.origin, str(a.get("href", "")))
            parsed_apply = urlsplit(apply_url)
            if (
                f"{parsed_apply.scheme}://{parsed_apply.netloc}" == self.origin
                and parsed_apply.path in {"/jobs/apply/", "/jobs/apply/ats-redirect/"}
                and parse_qs(parsed_apply.query, keep_blank_values=True) == {"id": [identifier]}
                and not parsed_apply.fragment
            ):
                apply_links.add(apply_url)
        if len(apply_links) != 1:
            raise ValueError("Missing or ambiguous same-ID JobBoard.com application link")
        apply_url = apply_links.pop()

        date_str = row.get("datePosted")
        published_at = datetime.fromisoformat(date_str) if isinstance(date_str, str) else None

        salary = row.get("baseSalary") if isinstance(row.get("baseSalary"), dict) else None

        employment = row.get("employmentType")
        if isinstance(employment, list):
            employment = ", ".join(str(e) for e in employment)
        elif not isinstance(employment, str):
            employment = None

        remote_status = "Remote" if row.get("jobLocationType") == "TELECOMMUTE" else None

        return [
            JobInput(
                external_id=identifier,
                title=title,
                company=company,
                description=description,
                quality_flags=flags,
                location=location,
                source_url=url,
                application_url=apply_url,
                employment_type=employment,
                remote_status=remote_status,
                salary=salary,
                published_at=published_at,
                raw={
                    "published_at_original": date_str,
                    "valid_through_original": row.get("validThrough"),
                    "employment_type_original": row.get("employmentType"),
                    "identifier_original": row.get("identifier"),
                    "hiring_organization_original": row.get("hiringOrganization"),
                },
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("JobBoard.com requires full public enumeration")
        return await self.discover()

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)
        index_url = f"{self.origin}/sitemap.xml"
        jobs_url = f"{self.origin}/xml-sitemaps/1.xml"

        advertised_maps = policy.parser.site_maps() or []
        if index_url not in advertised_maps:
            raise ValueError("JobBoard.com sitemap not advertised in robots.txt")

        async def read(url: str) -> bytes:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        async def get_roster() -> dict[str, str]:
            index_bytes = await read(index_url)
            jobs_bytes = await read(jobs_url)
            return self.roster(index_bytes, jobs_bytes)

        before = await get_roster()
        result: list[JobInput] = []
        for identifier, url in before.items():
            result.extend(self.parse((identifier, url, await read(url))))

        after = await get_roster()
        if before != after:
            raise ValueError("JobBoard.com roster changed during enumeration")

        return Enumeration(jobs=result, complete=True)

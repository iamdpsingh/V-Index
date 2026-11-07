"""JBoard's public HTML roster, sitemap cross-check and mandatory full job pages."""

import asyncio
import json
import re
from datetime import UTC, datetime
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

# Fixed, operator-reviewed origins advertised by https://jboard.io/showcase.
# No arbitrary/custom user-supplied host, CNAME or vendor API access is enabled.
HOSTS = frozenset({"jobs.aame.org", "jobs.cisontario.ca"})
NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
JOB_PATH = r"/jobs/([1-9][0-9]*)-[a-z0-9][a-z0-9!_-]*"


def document(body: bytes) -> BeautifulSoup:
    if b"</html>" not in body.lower():
        raise ValueError("Truncated JBoard public document")
    return BeautifulSoup(body, "html.parser")


def compact(value: str) -> str:
    return "".join(text(value).split())


class JBoardConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider != "jboard" or slug not in HOSTS:
            raise ValueError("Unsupported unreviewed JBoard origin")
        self.host = slug
        self.origin = "https://" + slug
        self.http = PublicHTTP(client, {slug})

    def scoped(self, url: str, pattern: str, *, page: bool = False) -> str:
        full = urljoin(self.origin, url)
        p = urlsplit(full)
        if (
            p.scheme != "https"
            or p.netloc != self.host
            or p.fragment
            or not re.fullmatch(pattern, p.path)
        ):
            raise ValueError("Unscoped JBoard public URL")
        if page:
            query = parse_qs(p.query, keep_blank_values=True)
            if (
                set(query) != {"page"}
                or len(query["page"]) != 1
                or not re.fullmatch("[1-9][0-9]*", query["page"][0])
            ):
                raise ValueError("Invalid JBoard native page link")
        elif p.query:
            raise ValueError("Filtered JBoard public URL")
        return full

    def identifier(self, url: str) -> str:
        full = self.scoped(url, JOB_PATH)
        match = re.fullmatch(JOB_PATH, urlsplit(full).path)
        assert match is not None
        return match[1]

    def sitemap(self, body: bytes, *, index: bool) -> dict[str, str]:
        try:
            root = ElementTree.fromstring(body)
        except (ParseError, DefusedXmlException) as error:
            raise ValueError("Malformed or unsafe JBoard sitemap XML") from error
        expected = "sitemapindex" if index else "urlset"
        if root.tag != NS + expected:
            raise ValueError("Missing complete JBoard sitemap")
        rows = root.findall(NS + ("sitemap" if index else "url"))
        if not 0 < len(rows) <= (100 if index else 200):
            raise ValueError("Empty or oversized JBoard sitemap")
        result = {}
        seen = set()
        for row in rows:
            locs = row.findall(NS + "loc")
            if len(locs) != 1 or not locs[0].text or locs[0].text in seen:
                raise ValueError("Malformed or duplicated JBoard sitemap entry")
            url = locs[0].text
            seen.add(url)
            if index:
                self.scoped(url, r"/sitemap-[a-z0-9-]+\.xml")
                match = re.fullmatch(r"/sitemap-jobs-([1-9][0-9]*)\.xml", urlsplit(url).path)
                if not match:
                    if urlsplit(url).path.startswith("/sitemap-jobs-"):
                        raise ValueError("Unsupported JBoard job map naming")
                    continue
                key = match[1]
            else:
                key = self.identifier(url)
            if key in result:
                raise ValueError("Repeated JBoard sitemap identity")
            result[key] = url
        if not result:
            raise ValueError("Missing JBoard job maps/jobs")
        return result

    def listings(self, body: bytes, page: int) -> tuple[dict[str, dict], str | None]:
        soup = document(body)
        rows = soup.select(".job-listings-item[data-jobid]")
        if not 0 < len(rows) <= 30:
            raise ValueError("Missing complete JBoard native listing page")
        result = {}
        for node in rows:
            links = node.select("a.job-details-link")
            employers = node.select('a.job-info-link-item[href^="/companies/"]')
            places = node.select('a.job-info-link-item[href^="/jobs/in-"]')
            if len(links) != 1 or len(employers) != 1 or len(places) > 1:
                raise ValueError("Ambiguous JBoard title/employer/location")
            url = self.scoped(str(links[0]["href"]), JOB_PATH)
            identifier = self.identifier(url)
            title, company = (
                links[0].get_text(" ", strip=True),
                employers[0].get_text(" ", strip=True),
            )
            applies = [
                a for a in node.select("a[href]") if a.get("href") == f"/jobs/{identifier}/apply"
            ]
            if (
                str(node["data-jobid"]) != identifier
                or identifier in result
                or len(applies) != 1
                or not title
                or not company
            ):
                raise ValueError("JBoard listing identity/employer/application mismatch")
            result[identifier] = {
                "url": url,
                "title": title,
                "company": company,
                "location": places[0].get_text(" ", strip=True) if places else "",
                "tags": [t.get_text(" ", strip=True) for t in node.select(".job-tags a")],
            }
        nexts = soup.select('a[rel="next"]')
        if len(nexts) > 1:
            raise ValueError("Ambiguous JBoard next page")
        next_url = None
        if nexts:
            next_url = self.scoped(str(nexts[0]["href"]), r"/jobs", page=True)
            if len(rows) != 30 or int(parse_qs(urlsplit(next_url).query)["page"][0]) != page + 1:
                raise ValueError("Partial or nonsequential JBoard pagination")
        return result, next_url

    def parse(self, payload: Any) -> list[JobInput]:
        identifier, listing, body = payload
        soup = document(body)
        docs = [json.loads(t.get_text()) for t in soup.select('script[type="application/ld+json"]')]
        docs = [d for d in docs if isinstance(d, dict) and d.get("@type") == "JobPosting"]
        titles = [
            node
            for node in soup.select("aside.job-inner-left h1")
            if node.find_parent(id="quill-container-with-job-details") is None
        ]
        native = soup.select("aside.job-inner-left #quill-container-with-job-details")
        canonical = soup.select('link[rel="canonical"]')
        employers = [
            node
            for node in soup.select('aside.job-inner-left a[href^="/companies/"]')
            if node.find_parent(id="quill-container-with-job-details") is None
        ]
        if (
            len(docs) != 1
            or len(titles) != 1
            or len(native) != 1
            or len(canonical) != 1
            or len(employers) != 1
        ):
            raise ValueError("Missing complete native JBoard job detail")
        row = docs[0]
        url = listing["url"]
        applies = [
            a
            for a in soup.select(".job-inner-btn-box a[href]")
            if a.get("href") == f"/jobs/{identifier}/apply"
        ]
        if (
            canonical[0]["href"] != url
            or str(row["identifier"]["value"]) != identifier
            or self.identifier(url) != identifier
            or not applies
            or compact(row["title"]) != compact(listing["title"])
            or compact(titles[0].get_text()) != compact(listing["title"])
            or compact(row["hiringOrganization"]["name"]) != compact(listing["company"])
            or compact(employers[0].get_text()) != compact(listing["company"])
            or not isinstance(row.get("description"), str)
            or not compact(row["description"])
            or compact(row["description"]) != compact(str(native[0]))
        ):
            raise ValueError("JBoard full detail ID/title/employer/description mismatch")
        flags = []
        published = datetime.fromisoformat(row["datePosted"]) if row.get("datePosted") else None
        if published is None:
            flags.append("publication_date_missing")
        elif published.tzinfo is None:
            flags.append("publication_timezone_unspecified")
        if not listing["location"]:
            flags.append("location_missing")
        expiry = datetime.fromisoformat(row["validThrough"]) if row.get("validThrough") else None
        if expiry and expiry.tzinfo is not None and expiry <= datetime.now(UTC):
            # Retain the contradiction, never silently close or drop a listed role.
            flags.append("source_expiry_elapsed_while_listed")
        employment = row.get("employmentType")
        if isinstance(employment, list):
            employment = ", ".join(employment)
        return [
            JobInput(
                external_id=identifier,
                title=listing["title"],
                company=listing["company"],
                description=text(str(native[0])),
                location=listing["location"],
                source_url=url,
                application_url=self.origin + f"/jobs/{identifier}/apply",
                employment_type=employment,
                remote_status=row.get("jobLocationType"),
                salary=row.get("baseSalary"),
                published_at=published,
                quality_flags=flags,
                raw={
                    "listing": listing,
                    "jobposting": row,
                    "description_html": str(native[0]),
                    "application_entry": "Native board application control; destination not requested",
                    "location_basis": "Native listing label; structured geocoding preserved without correction",
                    "published_at_original": row.get("datePosted"),
                    "valid_through_original": row.get("validThrough"),
                },
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("JBoard requires full list/sitemap enumeration")
        return await self.http.read(self.origin + "/jobs")

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)
        indices = [u for u in policy.parser.site_maps() or [] if urlsplit(u).path == "/sitemap.xml"]
        if (
            len(indices) != 1
            or self.scoped(indices[0], r"/sitemap\.xml") != self.origin + "/sitemap.xml"
        ):
            raise ValueError("Missing unique native JBoard sitemap index")

        async def read(url):
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        async def roster():
            maps = self.sitemap(await read(indices[0]), index=True)
            if len(maps) > 7 or set(maps) != {str(i) for i in range(1, len(maps) + 1)}:
                raise ValueError("Incomplete JBoard job map sequence")
            mapped: dict[str, str] = {}
            for key in sorted(maps, key=int):
                mapped_rows = self.sitemap(await read(maps[key]), index=False)
                if set(mapped_rows) & set(mapped):
                    raise ValueError("JBoard job repeated across maps")
                mapped.update(mapped_rows)
            if len(mapped) > 200:
                raise ValueError("JBoard detail budget exceeds 200")
            result: dict[str, dict] = {}
            url = self.origin + "/jobs"
            page = 1
            while True:
                rows, next_url = self.listings(await read(url), page)
                if set(rows) & set(result):
                    raise ValueError("JBoard job repeated across native pages")
                result.update(rows)
                if len(result) > 200:
                    raise ValueError("JBoard native listing budget exceeded")
                if next_url is None:
                    break
                if page >= 7:
                    raise ValueError("JBoard pagination exceeds budget")
                url = next_url
                page += 1
            if {k: v["url"] for k, v in result.items()} != mapped:
                raise ValueError("JBoard sitemap and complete native roster disagree")
            return result

        rows = await roster()
        jobs = []
        for identifier, listing in rows.items():
            jobs.extend(self.parse((identifier, listing, await read(listing["url"]))))
        if await roster() != rows:
            raise ValueError("JBoard complete public roster changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

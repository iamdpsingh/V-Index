"""eJobsiteSoftware public search form, native paging and posting details."""

import asyncio
import json
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlencode, urlsplit
from zoneinfo import ZoneInfo

import httpx
from bs4 import BeautifulSoup
from defusedxml import ElementTree
from vindex.connectors.http import PublicHTTP
from vindex.connectors.jobboardio import document
from vindex.connectors.robots import RobotsPolicy
from vindex.schemas import Enumeration, JobInput

BOARDS = {"seasonaljobs.co.nz": "", "gurushrconsultancy.com": "/jobboard"}
JOB_PATH = r"/([1-9][0-9]{0,17})/[A-Za-z0-9_-]+/?"
PAGE_SIZE = 10
MAX_JOBS = 200


class EJobsiteSoftwareConnector:
    def __init__(self, slug: str, client: httpx.AsyncClient):
        if slug not in BOARDS:
            raise ValueError("Unreviewed eJobsiteSoftware origin")
        self.host = slug
        self.origin = "https://" + slug
        self.base = self.origin + BOARDS[slug]
        self.search = self.base + "/job-search/"
        self.http = PublicHTTP(client, {slug})

    def page(
        self, body: bytes, offset: int, total: int | None
    ) -> tuple[int, dict[str, tuple[str, str]], str]:
        soup = document(body) if offset == 0 else BeautifulSoup(body, "html.parser")
        if offset == 0:
            totals = [
                int(m[1])
                for node in soup.select(".card-body.pb-0 > div")
                if (
                    m := re.fullmatch(
                        r"([1-9][0-9]*) Jobs? Found\.", node.get_text(" ", strip=True), re.I
                    )
                )
            ]
            if len(totals) != 1 or totals[0] > MAX_JOBS:
                raise ValueError("Missing or oversized eJobsiteSoftware search total")
            total = totals[0]
        if total is None or offset >= total:
            raise ValueError("Invalid eJobsiteSoftware result offset")
        rows: dict[str, tuple[str, str]] = {}
        for card in soup.select(".previewBox[id]"):
            identifier = str(card["id"])
            nodes = card.select("h6 a[href]" if offset == 0 else "h4")
            if len(nodes) != 1 or not re.fullmatch(r"[1-9][0-9]{0,17}", identifier):
                raise ValueError("Incomplete eJobsiteSoftware search row")
            title = nodes[0].get_text(" ", strip=True)
            url = str(nodes[0]["href"]) if offset == 0 else ""
            match = re.fullmatch(re.escape(self.base) + JOB_PATH, url)
            if (
                (offset == 0 and (not match or match[1] != identifier))
                or identifier in rows
                or not title
            ):
                raise ValueError("Unscoped or repeated eJobsiteSoftware posting")
            rows[identifier] = (url, title)
        if len(rows) != min(PAGE_SIZE, total - offset):
            raise ValueError("Incomplete eJobsiteSoftware page")
        links = [
            str(a["href"])
            for a in soup.select('a[href^="javascript:jobsearch_pagination("]')
            if a.get_text(" ", strip=True) == "Next"
        ]
        country = ""
        if offset + PAGE_SIZE < total:
            args = [
                offset + PAGE_SIZE,
                "",
                "",
                "1",
                "",
                "",
                "",
                "",
                "",
                "1",
                "",
                "0",
                self.base + "/",
                "0",
                "",
            ]
            if len(links) != 1 or not links[0].endswith(");"):
                raise ValueError("Missing eJobsiteSoftware next page")
            raw = links[0].removeprefix("javascript:jobsearch_pagination(")[:-2]
            actual = json.loads("[" + raw + "]")
            if len(actual) == len(args) and actual[4] in ("", "0"):
                country = args[4] = actual[4]
            if actual != args:
                raise ValueError("Unexpected eJobsiteSoftware next page parameters")
        elif links:
            raise ValueError("Unexpected eJobsiteSoftware terminal page")
        return total, rows, country

    def parse(self, payload: Any) -> list[JobInput]:
        identifier, url, expected_title, body = payload
        soup = document(body)
        headers = soup.select(".card-body-custom h1")
        if len(headers) != 1 or headers[0].get_text(" ", strip=True) != expected_title:
            raise ValueError(f"eJobsiteSoftware title mismatch for job {identifier}")
        card = headers[0].find_parent("div", class_="card-body-custom")
        assert card is not None
        meta = card.select_one(".mt-2.mb-4")
        employer, _, location = (meta.get_text(" ", strip=True) if meta else "").partition("•")
        employer, location = employer.strip(), location.strip()
        descriptions = [
            node.get_text(" ", strip=True)
            for node in card.select("h3 + div.card-text")
            if (heading := node.find_previous_sibling("h3")) is not None
            and heading.get_text(" ", strip=True) in {"Job Summary", "Job Description"}
        ]
        description = "\n\n".join(dict.fromkeys(x for x in descriptions if x))
        if not employer or not description:
            raise ValueError(
                f"Missing eJobsiteSoftware employer or description for job {identifier}"
            )
        posting: dict[str, Any] = {}
        for script in soup.select('script[type="application/ld+json"]'):
            item = json.loads(script.get_text())
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                if posting or item.get("url") not in (None, url):
                    raise ValueError("Unexpected eJobsiteSoftware JobPosting identity")
                posting = item
        application = url
        external = [
            str(a["href"])
            for a in card.select("a[href]")
            if "original listing" in a.get_text(" ", strip=True).casefold()
        ]
        if external:
            parsed = urlsplit(external[0])
            if (
                len(external) != 1
                or parsed.scheme != "https"
                or not parsed.hostname
                or parsed.port not in (None, 443)
                or parsed.username is not None
                or parsed.password is not None
            ):
                raise ValueError("Invalid eJobsiteSoftware original application link")
            application = external[0]
        date = posting.get("datePosted")
        employment = posting.get("employmentType")
        if isinstance(employment, list):
            employment = ", ".join(employment)
        gear = card.select_one("i.bi-gear")
        if not employment and gear and gear.parent:
            employment = gear.parent.get_text(" ", strip=True)
        return [
            JobInput(
                external_id=identifier,
                title=expected_title,
                company=employer,
                description=description,
                location=location,
                source_url=url,
                application_url=application,
                employment_type=employment or None,
                published_at=datetime.fromisoformat(date.strip()) if date else None,
                salary=posting.get("baseSalary"),
                remote_status="Remote" if posting.get("jobLocationType") == "TELECOMMUTE" else None,
                quality_flags=([] if date else ["publication_date_missing"])
                + ([] if location else ["location_missing"]),
                raw={"published_at_original": date},
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("eJobsiteSoftware uses its native complete search flow")
        return await self.http.read(self.search)

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)

        async def read(url: str, form: dict[str, str] | None = None) -> bytes:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(
                url, method="POST" if form is not None else "GET", form=form
            )

        async def roster() -> dict[str, tuple[str, str]]:
            soup = document(await read(self.search))
            native = soup.select(
                f'form[action="{self.search}"][method="post"] input[name="action"][value="search"]'
            )
            if len(native) != 1:
                raise ValueError("Missing eJobsiteSoftware public search form")
            form = {"action": "search", "keyword": "", "word1": "1"}
            if self.host == "seasonaljobs.co.nz":
                parent = native[0].find_parent("form")
                token = parent.select_one('input[name="_csrf_token"][value]') if parent else None
                if token is None or not token["value"]:
                    raise ValueError("Missing anonymous eJobsiteSoftware form state")
                form["_csrf_token"] = str(token["value"])
            total, result, country = self.page(await read(self.search, form), 0, None)
            for offset in range(PAGE_SIZE, total, PAGE_SIZE):
                query = urlencode(
                    {
                        "starting": offset,
                        "keyword": "",
                        "location": "",
                        "word1": "1",
                        "country": country,
                        "state": "",
                        "experience": "",
                        "job_post_day": "",
                        "search_zip_code": "1",
                        "zip_code": "",
                        "radius": "0",
                        "skill": "",
                        "map_view": "0",
                    }
                )
                _, rows, country = self.page(
                    await read(f"{self.base}/ajax/job_search_result1.php?{query}"), offset, total
                )
                for identifier, row in rows.items():
                    previous = result.get(identifier)
                    if previous is not None and previous[1] != row[1]:
                        raise ValueError("Conflicting eJobsiteSoftware search titles")
                    result.setdefault(identifier, row)
            if self.host == "seasonaljobs.co.nz":
                # The publisher's two public surfaces omit different active rows.
                sitemap_url = self.origin + "/sitemap.xml"
                if sitemap_url not in (policy.parser.site_maps() or []):
                    raise ValueError("Missing eJobsiteSoftware sitemap declaration")
                sitemap = ElementTree.fromstring(await read(sitemap_url))
                namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
                if sitemap.tag != namespace + "urlset":
                    raise ValueError("Unexpected eJobsiteSoftware sitemap format")
                locations: dict[str, str] = {}
                for node in sitemap.findall(f"{namespace}url/{namespace}loc"):
                    url = node.text or ""
                    match = re.fullmatch(re.escape(self.base) + JOB_PATH, url)
                    if match:
                        if match[1] in locations:
                            raise ValueError("Repeated eJobsiteSoftware sitemap ID")
                        locations[match[1]] = url
                if len(result.keys() | locations.keys()) != total:
                    raise ValueError("eJobsiteSoftware search and sitemap do not reconcile")
                for identifier in sorted(result.keys() | locations.keys()):
                    url, title = result.get(identifier, ("", ""))
                    listed = locations.get(identifier)
                    if listed and title:
                        if url and url != listed:
                            raise ValueError("Conflicting eJobsiteSoftware canonical URLs")
                        result[identifier] = (listed, title)
                        continue
                    preview = json.loads(await read(f"{self.base}/api/index.php?id={identifier}"))
                    if (
                        not isinstance(preview, list)
                        or len(preview) != 1
                        or not isinstance(preview[0], dict)
                    ):
                        raise ValueError("Missing eJobsiteSoftware public preview")
                    item = preview[0]
                    canonical = item.get("titleLink")
                    if not isinstance(canonical, str):
                        raise ValueError("Missing eJobsiteSoftware canonical URL")
                    match = re.fullmatch(re.escape(self.base) + JOB_PATH, canonical)
                    preview_title = BeautifulSoup(
                        str(item.get("job_title") or ""), "html.parser"
                    ).get_text(" ", strip=True)
                    if (
                        not match
                        or match[1] != identifier
                        or str(item.get("job_id")) != identifier
                        or item.get("yourHomeURL") != self.base + "/"
                        or not preview_title
                        or (title and title != preview_title)
                        or (listed and listed != canonical)
                        or (url and url != canonical)
                    ):
                        raise ValueError(
                            f"Conflicting eJobsiteSoftware preview identity for job {identifier}"
                        )
                    if not title:
                        expiry = datetime.fromisoformat(item["expired"])
                        if expiry.tzinfo is not None or expiry <= datetime.now(
                            ZoneInfo("Pacific/Auckland")
                        ).replace(tzinfo=None):
                            raise ValueError("Sitemap-only eJobsiteSoftware posting is not active")
                    result[identifier] = (canonical, preview_title)
            if len(result) != total or any(not url for url, _ in result.values()):
                raise ValueError("Incomplete eJobsiteSoftware canonical roster")
            return result

        before = await roster()
        jobs = []
        for identifier, (url, title) in before.items():
            jobs.extend(self.parse((identifier, url, title, await read(url))))
        if await roster() != before:
            raise ValueError("eJobsiteSoftware roster changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

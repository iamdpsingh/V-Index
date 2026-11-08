"""SmartJobBoard public board pages and same-board posting details."""

import asyncio
import json
import re
from datetime import datetime
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
from vindex.connectors.http import PublicHTTP
from vindex.connectors.jobboardio import document
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.schemas import Enumeration, JobInput

HOSTS = frozenset({"americanbath.mysmartjobboard.com", "jobs.psychologicalscience.org"})
JOB_PATH = r"/job/([1-9][0-9]{0,17})/[a-zA-Z0-9][a-zA-Z0-9_.~-]*/"
PAGE_SIZE = 20
MAX_JOBS = 200


class SmartJobBoardConnector:
    def __init__(self, slug: str, client: httpx.AsyncClient):
        if slug not in HOSTS:
            raise ValueError("Unreviewed SmartJobBoard origin")
        self.origin = "https://" + slug
        self.http = PublicHTTP(client, {slug})

    def page(self, body: bytes, page: int, total: int | None) -> tuple[int, dict[str, str]]:
        soup = document(body)
        matches = [
            m
            for h in soup.select("h1")
            if (m := re.fullmatch(r"([1-9][0-9]{0,2}) jobs? found", h.get_text(" ", strip=True)))
        ]
        if len(matches) != 1:
            raise ValueError("Missing native SmartJobBoard result total")
        count = int(matches[0][1])
        if count > MAX_JOBS or (total is not None and total != count):
            raise ValueError("SmartJobBoard total changed or exceeds supported bounds")
        pagination = soup.select("button.load-more[data-page]")
        expected = min(PAGE_SIZE, count - (page - 1) * PAGE_SIZE)
        if (
            expected <= 0
            or ((page > 1 or count > PAGE_SIZE) and not pagination)
            or (
                pagination
                and (
                    len(pagination) != 1
                    or pagination[0]["data-page"] != str(page)
                    or (
                        count > page * PAGE_SIZE
                        and pagination[0].get("data-backfilling") != "false"
                    )
                )
            )
        ):
            raise ValueError("Missing or mismatched SmartJobBoard native page")
        scripts = [s.get_text() for s in soup.select("script:not([src])")]
        if not any(
            "var listingPerPage = 20;" in s and "$.get('?&page=' + page" in s for s in scripts
        ):
            raise ValueError("Unsupported SmartJobBoard pagination template")
        jobs = {}
        for anchor in soup.select(".listing-item__title a[href]"):
            url = str(anchor["href"])
            match = re.fullmatch(re.escape(self.origin) + JOB_PATH, url)
            if not match or match[1] in jobs:
                raise ValueError("Unscoped or repeated SmartJobBoard listing")
            jobs[match[1]] = url
        if len(jobs) != expected:
            raise ValueError("Incomplete SmartJobBoard page")
        return count, jobs

    def parse(self, payload: Any) -> list[JobInput]:
        identifier, url, body = payload
        soup = document(body)
        canonical = soup.select('link[rel="canonical"]')
        native_titles = soup.select("h1.details-header__title")
        sections = soup.select("h3.details-body__title + div.details-body__content")
        details: dict[str, str] = {}
        for section in sections:
            heading = section.find_previous_sibling("h3")
            if heading is not None:
                name = heading.get_text(" ", strip=True)
                if name in {"Job Description", "Employer"}:
                    if name in details:
                        raise ValueError("Repeated SmartJobBoard detail section")
                    details[name] = section.get_text(" ", strip=True)
        companies = soup.select(".listing-item__info--item-company")
        structured = [
            json.loads(t.get_text()) for t in soup.select('script[type="application/ld+json"]')
        ]
        postings = [j for j in structured if isinstance(j, dict) and j.get("@type") == "JobPosting"]
        if any(len(items) != 1 for items in (canonical, native_titles, companies, postings)):
            raise ValueError("Missing full SmartJobBoard job detail")
        row = postings[0]
        company = text(row["hiringOrganization"]["name"])
        title = text(row["title"])
        description = details.get("Job Description", "")
        if (
            canonical[0].get("href") != url
            or row.get("url") != url
            or native_titles[0].get_text(" ", strip=True) != title
            or companies[0].get_text(" ", strip=True) != company
            or not title
            or not company
            or not description
        ):
            raise ValueError("SmartJobBoard canonical, title, employer or description mismatch")
        expected_apply = self.origin + f"/application-redirect/?listing_id={identifier}"
        buttons = soup.select(".details-footer__btn-apply")
        if not buttons:
            raise ValueError("Missing SmartJobBoard application entry")
        if all(a.name == "a" and a.get("href") == expected_apply for a in buttons):
            apply = expected_apply
        else:
            for button in buttons:
                target = urlsplit(str(button.get("data-href", "")))
                params = parse_qs(target.query, keep_blank_values=True)
                if (
                    button.get("href") != ""
                    or button.get("data-toggle") != "modal"
                    or button.get("data-target") != "#apply-modal"
                    or f"{target.scheme}://{target.netloc}" != self.origin
                    or target.path != "/apply-now/"
                    or target.fragment
                    or set(params) != {"ajaxRelocate", "json_redirect", "listing_id"}
                    or params["listing_id"] != [identifier]
                ):
                    raise ValueError("Unsupported SmartJobBoard application control")
            if len(soup.select("#apply-modal")) != 1:
                raise ValueError("Missing SmartJobBoard application modal")
            apply = url
        location_node = soup.select_one(".listing-item__info--item-location")
        location = location_node.get_text(" ", strip=True) if location_node else ""
        flags = [] if location else ["location_missing"]
        date = row["datePosted"]
        employment = row.get("employmentType")
        if isinstance(employment, list):
            employment = ", ".join(employment)
        return [
            JobInput(
                external_id=identifier,
                title=title,
                company=details.get("Employer") or company,
                description=description,
                location=location,
                source_url=url,
                application_url=apply,
                employment_type=employment if employment != "OTHER" else None,
                remote_status="Remote" if row.get("jobLocationType") == "TELECOMMUTE" else None,
                salary=row.get("baseSalary"),
                published_at=datetime.fromisoformat(date),
                quality_flags=flags,
                raw={
                    "published_at_original": date,
                    "valid_through_original": row.get("validThrough"),
                    "employment_type_original": row.get("employmentType"),
                    "posting_organization": company,
                },
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        return await self.http.read(self.page_url(cursor or 1))

    def page_url(self, page: int) -> str:
        if not 1 <= page <= MAX_JOBS // PAGE_SIZE:
            raise ValueError("SmartJobBoard pagination outside supported bounds")
        return self.origin + ("/jobs/" if page == 1 else f"/jobs/?&page={page}")

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)

        async def read(url: str) -> bytes:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        async def roster() -> dict[str, str]:
            total, jobs = self.page(await read(self.page_url(1)), 1, None)
            for page in range(2, (total - 1) // PAGE_SIZE + 2):
                _, rows = self.page(await read(self.page_url(page)), page, total)
                if jobs.keys() & rows.keys():
                    raise ValueError("Repeated SmartJobBoard listing across pages")
                jobs.update(rows)
            return jobs

        before = await roster()
        result = []
        for identifier, url in before.items():
            result.extend(self.parse((identifier, url, await read(url))))
        if before != await roster():
            raise ValueError("SmartJobBoard roster changed during enumeration")
        return Enumeration(jobs=result, complete=True)

"""Rival's public SilkRoad career listings and native posting details."""

import asyncio
import json
import re
from datetime import datetime
from typing import Any

import httpx
from vindex.connectors.http import PublicHTTP
from vindex.connectors.jobboardio import document
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.schemas import Enumeration, JobInput

HOST = "jobs.silkroad.com"
ORIGIN = "https://" + HOST
PORTALS = {
    "RSCS/Careers": ("Restaurant Supply Chain Solutions", 10),
    "BlandLandscaping/Careers": ("Bland Landscaping Company", 25),
}
PAGER = "Jobs_PagedJobList_"


class RivalConnector:
    def __init__(self, slug: str, client: httpx.AsyncClient):
        if slug not in PORTALS:
            raise ValueError("Unreviewed Rival portal")
        self.path = "/" + slug
        self.company, self.page_size = PORTALS[slug]
        self.http = PublicHTTP(client, {HOST})

    def page(self, body: bytes, number: int) -> tuple[int, dict[str, tuple[str, str]]]:
        soup = document(body)
        headings = soup.select("#Jobs_JobsList_CompanyName")
        if len(headings) != 1 or headings[0].get_text(" ", strip=True) != self.company:
            raise ValueError("Rival portal identity mismatch")
        pagination = soup.select(".sr-pagination")
        last = 1
        if pagination:
            pagers = soup.select(f"#{PAGER}CurrentPageText")
            if len(pagination) != 1 or len(pagers) != 1:
                raise ValueError("Malformed Rival pager")
            match = re.fullmatch(
                r"Page ([1-9][0-9]*) of ([1-9][0-9]*)", pagers[0].get_text(" ", strip=True)
            )
            if (
                not match
                or int(match[1]) != number
                or not number <= int(match[2]) <= 200 // self.page_size
            ):
                raise ValueError("Unexpected Rival page number")
            last = int(match[2])
            buttons = soup.select(f"#{PAGER}NextLink")
            if (
                len(buttons) != 1
                or buttons[0].has_attr("disabled") != (number == last)
                or buttons[0].get("data-href") != f"{self.path}?page={min(number + 1, last)}"
            ):
                raise ValueError("Unexpected Rival next page")
        elif number != 1:
            raise ValueError("Missing Rival pager")
        rows: dict[str, tuple[str, str]] = {}
        for anchor in soup.select(f'a.sr-panel[id^="{PAGER}Job-"]'):
            path = str(anchor.get("href") or "")
            match = re.fullmatch(re.escape(self.path) + r"/jobs/([1-9][0-9]{0,11})", path)
            if not match:
                raise ValueError("Unscoped Rival job")
            identifier = match[1]
            title = anchor.select_one(f"#{PAGER}JobTitle-{identifier}")
            location = anchor.select_one(f"#{PAGER}JobLocation-{identifier}")
            if anchor["id"] != PAGER + "Job-" + identifier or identifier in rows or title is None:
                raise ValueError("Malformed or repeated Rival listing")
            name = title.get_text(" ", strip=True)
            if not name:
                raise ValueError("Missing Rival listing title")
            rows[identifier] = (name, location.get_text(" ", strip=True) if location else "")
        if not 1 <= len(rows) <= self.page_size or (number < last and len(rows) != self.page_size):
            raise ValueError("Incomplete Rival result page")
        if not pagination and len(rows) == self.page_size:
            raise ValueError("Rival page is full but has no terminal pager")
        return last, rows

    def parse(self, payload: Any) -> list[JobInput]:
        identifier, (expected_title, listed_location), body = payload
        soup = document(body)
        source = f"{self.path}/jobs/{identifier}"
        headings = soup.select("#Jobs_JobDetail_TitleText")
        employer = soup.select_one("#Jobs_JobsList_CompanyName")
        if (
            len(headings) != 1
            or headings[0].get_text(" ", strip=True) != expected_title
            or employer is None
            or employer.get_text(" ", strip=True) != self.company
        ):
            raise ValueError(f"Rival detail identity mismatch for job {identifier}")
        apply = soup.select_one('a[id^="Jobs_JobDetail_"][id$="_ApplyLink"][href]')
        apply_path = str(apply["href"]) if apply else ""
        if not re.fullmatch(
            re.escape(self.path) + rf"/Apply/(?:MultiForm|QuickApply)/{identifier}", apply_path
        ):
            raise ValueError(f"Missing same-ID Rival application entry for job {identifier}")
        prefix = "#ConfigurablePageDetail__"
        blocks = soup.select(
            ", ".join(
                prefix + name for name in ("JobDescription", "RequiredSkills", "RequiredExperience")
            )
        )
        description = "\n\n".join(value for block in blocks if (value := text(str(block))))
        if not description or not soup.select_one(prefix + "JobDescription"):
            raise ValueError(f"Missing Rival description for job {identifier}")
        native = soup.select_one(prefix + "DisplayLocation > div")
        all_locations = soup.select_one(prefix + "DisplayAllLocations > div")
        location = native or all_locations
        location_text = location.get_text(" ", strip=True) if location else listed_location
        position = soup.select_one(prefix + "DisplayPosition > div")
        tracking = soup.select_one(prefix + "TrackingCode > div")
        tracking_code = tracking.get_text(" ", strip=True) if tracking else None
        posting: dict[str, Any] = {}
        for script in soup.select('script[type="application/ld+json"]'):
            data = json.loads(script.get_text())
            if isinstance(data, dict) and data.get("@type") == "JobPosting":
                if (
                    posting
                    or data.get("title") != expected_title
                    or data.get("identifier", {}).get("value") != tracking_code
                ):
                    raise ValueError(f"Conflicting Rival structured identity for job {identifier}")
                posting = data
        date = posting.get("datePosted")
        return [
            JobInput(
                external_id=identifier,
                title=expected_title,
                company=self.company,
                description=description,
                location=location_text,
                source_url=ORIGIN + source,
                application_url=ORIGIN + apply_path,
                published_at=datetime.fromisoformat(date) if date else None,
                employment_type=posting.get("employmentType")
                or (position.get_text(" ", strip=True) if position else None),
                salary=posting.get("baseSalary"),
                remote_status="Remote" if posting.get("jobLocationType") == "TELECOMMUTE" else None,
                quality_flags=([] if date else ["publication_date_missing"])
                + ([] if location_text else ["location_missing"]),
                raw={"date_posted_original": date, "tracking_code": tracking_code},
            )
        ]

    async def fetch(self, cursor: int = 0) -> bytes:
        if cursor:
            raise ValueError("Rival uses its native public pager")
        return await self.http.read(ORIGIN + self.path)

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, ORIGIN)

        async def read(path: str) -> bytes:
            url = ORIGIN + path
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        async def roster() -> dict[str, tuple[str, str]]:
            last, jobs = self.page(await read(self.path), 1)
            for number in range(2, last + 1):
                observed, rows = self.page(await read(f"{self.path}?page={number}"), number)
                if observed != last or jobs.keys() & rows.keys():
                    raise ValueError("Changed or repeated Rival search results")
                jobs.update(rows)
            return jobs

        before = await roster()
        jobs = []
        for identifier, row in before.items():
            jobs.extend(self.parse((identifier, row, await read(f"{self.path}/jobs/{identifier}"))))
        if await roster() != before:
            raise ValueError("Rival roster changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

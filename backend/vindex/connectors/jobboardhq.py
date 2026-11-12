"""Reviewed JobBoardHQ public ASP.NET search and job detail pages."""

import asyncio
import json
import re
from datetime import datetime
from typing import Any
from urllib.parse import unquote

import httpx
from vindex.connectors.http import PublicHTTP
from vindex.connectors.jobboardio import document
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.schemas import Enumeration, JobInput

HOSTS = frozenset({"jobboardhq.esc17.net", "resume.absc.org"})
JOB_PATH = re.compile(
    r"/job/([a-z0-9]{6})(?:/(?:[A-Za-z0-9._~()-]|%[89a-fA-F][0-9a-fA-F])+){1,4}/?"
)
PAGE_FIELD = "ctl00$MainContent$ddlPageRows"
HIDDEN = {"__VIEWSTATE", "__VIEWSTATEGENERATOR", "ctl00$hfVerificationToken"}
MAX_PAGES = 10


class JobBoardHQConnector:
    def __init__(self, slug: str, client: httpx.AsyncClient):
        if slug not in HOSTS:
            raise ValueError("Unreviewed JobBoardHQ origin")
        self.origin = "https://" + slug
        self.search = self.origin + "/search"
        self.http = PublicHTTP(client, {slug})

    def page(
        self, body: bytes, number: int
    ) -> tuple[int, dict[str, tuple[str, str]], dict[str, str]]:
        soup = document(body)
        forms = soup.select('form#form1[method="post"][action="./search"]')
        if len(forms) != 1:
            raise ValueError("Missing JobBoardHQ search form")
        form = forms[0]
        pagers = form.select(".pagerLinks")
        if len(pagers) != 1:
            raise ValueError("Missing JobBoardHQ pager")
        pager = pagers[0]
        current = pager.select(".pagerCurrentPage")
        if len(current) != 1 or current[0].get_text(strip=True) != str(number):
            raise ValueError("Unexpected JobBoardHQ page number")
        numbers = {number}
        for link in pager.select("a"):
            value = link.get_text(strip=True)
            if (
                not re.fullmatch(r"[1-9][0-9]?", value)
                or link.get("href") != "#"
                or link.get("onclick") != f"__doPostBack('Page', '{value}'); return false;"
                or int(value) in numbers
            ):
                raise ValueError("Unsupported JobBoardHQ pager link")
            numbers.add(int(value))
        last = max(numbers)
        if last > MAX_PAGES or numbers != set(range(1, last + 1)):
            raise ValueError("Incomplete or oversized JobBoardHQ pager")
        rows: dict[str, tuple[str, str]] = {}
        for row in form.select(".listRow"):
            anchors = row.select(".title a[href]")
            if len(anchors) != 1:
                raise ValueError("Missing JobBoardHQ job link")
            path = str(anchors[0]["href"])
            match = JOB_PATH.fullmatch(path)
            title = anchors[0].get_text(" ", strip=True)
            if not match or not title or match[1] in rows:
                raise ValueError("Malformed or repeated JobBoardHQ job")
            rows[match[1]] = (self.origin + path, title)
        if not 1 <= len(rows) <= 20 or (number < last and len(rows) != 20):
            raise ValueError("Incomplete JobBoardHQ result page")
        state = {}
        for field in form.select('input[type="hidden"][name]'):
            name = str(field["name"])
            if name in HIDDEN:
                if name in state or (name.startswith("__") and not field.get("value")):
                    raise ValueError("Invalid JobBoardHQ public form state")
                state[name] = str(field.get("value", ""))
        if set(state) != HIDDEN:
            raise ValueError("Incomplete JobBoardHQ public form state")
        for field in form.select('input[type="text"][name],input[type="radio"][name][checked]'):
            name = str(field["name"])
            value = str(field.get("value", ""))
            if not name.startswith("ctl00$MainContent$") or (field["type"] == "text" and value):
                raise ValueError("Unexpected JobBoardHQ search filter")
            state[name] = value
        if form.select('input[type="checkbox"][name][checked]'):
            raise ValueError("Unexpected JobBoardHQ search filter")
        for field in form.select("select[name]"):
            name = str(field["name"])
            option = field.select_one("option[selected]") or field.select_one("option")
            if not name.startswith("ctl00$MainContent$") or option is None:
                raise ValueError("Unexpected JobBoardHQ search selector")
            state[name] = str(option.get("value", ""))
            if name not in {PAGE_FIELD, "ctl00$MainContent$ddlLocationRadius"} and state[
                name
            ] not in {"", "0"}:
                raise ValueError("Unexpected JobBoardHQ search filter")
        if state.get(PAGE_FIELD) != "20":
            raise ValueError("Unexpected JobBoardHQ page size")
        return last, rows, state

    def parse(self, payload: Any) -> list[JobInput]:
        identifier, (url, expected_title), body = payload
        soup = document(body)
        canonical = soup.select('link[rel="canonical"][href]')
        headers = soup.select("h1.pageTitle")
        if (
            len(canonical) != 1
            or unquote(str(canonical[0]["href"])) != unquote(url)
            or len(headers) != 1
            or headers[0].get_text(" ", strip=True) != expected_title
        ):
            raise ValueError(f"JobBoardHQ visible identity mismatch for job {identifier}")
        postings = []
        for script in soup.select('script[type="application/ld+json"]'):
            item = json.loads(script.get_text())
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                postings.append(item)
        if len(postings) != 1:
            raise ValueError(f"Missing JobBoardHQ JobPosting for job {identifier}")
        job = postings[0]
        if (
            job.get("identifier", {}).get("value") != identifier
            or text(job.get("title", "")) != expected_title
            or unquote(str(job.get("url") or url)) != unquote(url)
        ):
            raise ValueError(f"JobBoardHQ structured identity mismatch for job {identifier}")
        company = text(job.get("hiringOrganization", {}).get("name", ""))
        description = text(job.get("description", ""))
        if not company or not description or not soup.select_one('#btnApply[value="Apply"]'):
            raise ValueError(f"Incomplete JobBoardHQ details for job {identifier}")
        address = job.get("jobLocation", {}).get("address", {})
        location = ", ".join(
            value
            for key in ("addressLocality", "addressRegion", "addressCountry")
            if isinstance(value := address.get(key), str) and value.strip()
        )
        original_date = job.get("datePosted")
        date = datetime.fromisoformat(original_date) if original_date else None
        return [
            JobInput(
                external_id=identifier,
                title=expected_title,
                company=company,
                description=description,
                location=location,
                source_url=url,
                application_url=url,
                employment_type=job.get("employmentType") or None,
                remote_status="Remote" if job.get("jobLocationType") == "TELECOMMUTE" else None,
                salary=job.get("baseSalary"),
                published_at=date,
                quality_flags=([] if location else ["location_missing"])
                + (
                    ["publication_date_missing"]
                    if date is None
                    else ["publication_timezone_unspecified"]
                    if date.tzinfo is None
                    else []
                ),
                raw={
                    "date_posted_original": original_date,
                    "valid_through": job.get("validThrough"),
                },
            )
        ]

    async def fetch(self, cursor: int = 0) -> bytes:
        if cursor:
            raise ValueError("JobBoardHQ uses its native public pager")
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
            last, result, state = self.page(await read(self.search), 1)
            for number in range(2, last + 1):
                form = {**state, "__EVENTTARGET": "Page", "__EVENTARGUMENT": str(number)}
                observed, rows, state = self.page(await read(self.search, form), number)
                if observed != last or result.keys() & rows.keys():
                    raise ValueError("Changed or repeated JobBoardHQ search results")
                result.update(rows)
            return result

        before = await roster()
        jobs = []
        for identifier, row in before.items():
            jobs.extend(self.parse((identifier, row, await read(row[0]))))
        if await roster() != before:
            raise ValueError("JobBoardHQ roster changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

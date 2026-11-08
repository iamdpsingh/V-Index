"""WP Job Manager public job board connector."""

import asyncio
import json
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

import httpx
from bs4 import BeautifulSoup
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.schemas import Enumeration, JobInput

HOSTS = frozenset({"oliver-walters.com", "pearlstreetsystems.com"})
CONFIGS: dict[str, dict[str, str]] = {
    "oliver-walters.com": {
        "origin": "https://oliver-walters.com",
        "board_path": "/job-listings/",
        "company": "Oliver Walters",
    },
    "pearlstreetsystems.com": {
        "origin": "https://pearlstreetsystems.com",
        "board_path": "/careers/",
        "company": "Pearl Street Systems",
    },
}
POST_ID_PATTERN = re.compile(r"\bpost-(\d+)\b")
JOB_URL_PATTERN = re.compile(r"^/job/([^/]+)/?$")
MAX_JOBS = 200


def document(body: bytes) -> BeautifulSoup:
    if b"</html>" not in body.lower():
        raise ValueError("Truncated public HTML document")
    return BeautifulSoup(body, "html.parser")


class WPJobManagerConnector:
    """Connector for WP Job Manager-powered public career portals."""

    def __init__(self, slug: str, client: httpx.AsyncClient):
        if slug not in HOSTS:
            raise ValueError(f"Unreviewed WP Job Manager host: {slug}")
        cfg = CONFIGS[slug]
        self.host = slug
        self.origin = cfg["origin"]
        self.board_path = cfg["board_path"]
        self.default_company = cfg["company"]
        self.http = PublicHTTP(client, {slug})

    def ajax_url(self) -> str:
        return f"{self.origin}/jm-ajax/get_listings/"

    def board_url(self) -> str:
        return f"{self.origin}{self.board_path}"

    def roster(self, body: bytes) -> dict[str, str]:
        soup: BeautifulSoup
        stripped = body.strip()
        if stripped.startswith(b"{"):
            try:
                data = json.loads(stripped.decode("utf-8"))
            except Exception as err:
                raise ValueError(f"Malformed WP Job Manager AJAX JSON payload: {err}") from err
            if data.get("found_jobs") is not True:
                raise ValueError("No jobs found on WP Job Manager board")
            if type(data.get("max_num_pages")) is not int or data["max_num_pages"] != 1:
                raise ValueError(
                    "WP Job Manager returned an incomplete or unsupported pagination response"
                )
            html_content = data.get("html", "")
            soup = BeautifulSoup(html_content, "html.parser")
        else:
            raise ValueError("Expected WP Job Manager native JSON response")

        roster: dict[str, str] = {}
        for li in soup.find_all("li", class_=lambda c: c and "job_listing" in c):
            raw_cls = li.get("class")
            classes = " ".join(raw_cls) if isinstance(raw_cls, list) else str(raw_cls or "")
            if any(
                status in classes
                for status in (
                    "status-expired",
                    "status-filled",
                    "status-trash",
                    "job_listing-expired",
                    "job_listing-filled",
                )
            ):
                continue

            job_id = ""
            m = POST_ID_PATTERN.search(classes)
            if m:
                job_id = m.group(1)

            a = li.find("a", href=True)
            if not a:
                raise ValueError("WP Job Manager active row missing a job link")

            href = str(a["href"]).strip()
            if not href.startswith("http://") and not href.startswith("https://"):
                href = f"{self.origin}{href}"

            parsed = urlsplit(href)
            path_m = JOB_URL_PATTERN.fullmatch(parsed.path)
            if (
                f"{parsed.scheme}://{parsed.netloc}" != self.origin
                or parsed.query
                or parsed.fragment
                or not path_m
            ):
                raise ValueError("WP Job Manager active row has an unscoped job URL")
            job_id = job_id or path_m[1]
            if job_id in roster:
                raise ValueError("WP Job Manager repeated job ID")
            roster[job_id] = href
            if len(roster) > MAX_JOBS:
                raise ValueError("WP Job Manager roster exceeds supported bounds")

        if not roster:
            raise ValueError(f"No jobs found on WP Job Manager board: {self.host}")

        return roster

    def parse_detail(self, job_id: str, url: str, body: bytes) -> JobInput:
        soup = document(body)
        title = ""
        company = ""
        location = ""
        description = ""
        employment_type: str | None = None
        published_at: datetime | None = None
        raw_schema: dict[str, Any] = {}

        scripts = soup.find_all("script", type="application/ld+json")
        for s in scripts:
            try:
                data = json.loads(s.get_text())
                candidates = []
                if isinstance(data, dict):
                    if data.get("@type") == "JobPosting":
                        candidates.append(data)
                    elif isinstance(data.get("@graph"), list):
                        for g in data["@graph"]:
                            if isinstance(g, dict) and g.get("@type") == "JobPosting":
                                candidates.append(g)
                for cand in candidates:
                    raw_schema = cand
                    cand_title = str(cand.get("title", "")).strip()
                    if cand_title and not title:
                        title = cand_title

                    cand_desc = cand.get("description", "")
                    if cand_desc and not description:
                        description = text(cand_desc)

                    org = cand.get("hiringOrganization")
                    if isinstance(org, dict):
                        org_name = str(org.get("name", "")).strip()
                        if org_name and not company:
                            company = org_name

                    loc_obj = cand.get("jobLocation")
                    if loc_obj and not location:
                        if isinstance(loc_obj, dict):
                            addr = loc_obj.get("address")
                            if isinstance(addr, dict):
                                parts = [
                                    addr.get("addressLocality"),
                                    addr.get("addressRegion"),
                                    addr.get("addressCountry"),
                                ]
                                location = ", ".join(
                                    str(p).strip() for p in parts if p and str(p).strip()
                                )
                            elif isinstance(addr, str) and addr.strip():
                                location = addr.strip()
                        elif isinstance(loc_obj, str) and loc_obj.strip():
                            location = loc_obj.strip()

                    emp = cand.get("employmentType")
                    if emp and not employment_type:
                        if isinstance(emp, list) and emp:
                            employment_type = str(emp[0]).strip()
                        elif isinstance(emp, str) and emp.strip():
                            employment_type = emp.strip()

                    dp = cand.get("datePosted")
                    if dp and not published_at:
                        try:
                            published_at = datetime.fromisoformat(str(dp).strip())
                        except Exception:
                            pass
                    break
            except Exception:
                continue

        if not title:
            h1 = soup.find("h1")
            if h1:
                title = h1.get_text(strip=True)
            elif soup.title:
                raw_t = soup.title.get_text(strip=True)
                title = re.sub(r"\s*[-|]\s*.*$", "", raw_t).strip()

        if not title:
            raise ValueError(f"Missing job title on WP Job Manager detail page: {url}")

        if not description:
            desc_el = soup.find(class_="job_description") or soup.find(class_="entry-content")
            if desc_el:
                description = text(desc_el.get_text(separator="\n", strip=True))

        if not company:
            company = self.default_company

        apply_url = url
        apply_btn = soup.find(
            "a", class_=lambda c: c and ("application_button" in c or "apply" in c)
        )
        if apply_btn and apply_btn.get("href"):
            cand_apply = str(apply_btn["href"]).strip()
            if cand_apply.startswith("http://") or cand_apply.startswith("https://"):
                apply_url = cand_apply

        flags = [] if description else ["description_missing"]

        return JobInput(
            external_id=job_id,
            title=title,
            company=company,
            description=description,
            quality_flags=flags,
            location=location,
            source_url=url,
            application_url=apply_url,
            employment_type=employment_type,
            published_at=published_at,
            raw={"schema": raw_schema},
        )

    def parse(self, payload: Any) -> list[JobInput]:
        if isinstance(payload, tuple) and len(payload) == 3:
            job_id, url, body = payload
            return [self.parse_detail(job_id, url, body)]
        if isinstance(payload, list):
            return payload
        raise ValueError("Invalid payload for WP Job Manager parse")

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor != 0:
            raise ValueError("WP Job Manager does not support pagination cursor")
        return await self.discover()

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)
        ajax_url = self.ajax_url()
        policy.check(ajax_url)
        await asyncio.sleep(policy.delay())

        async def fetch_roster_payload() -> bytes:
            policy.check(ajax_url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(
                ajax_url,
                method="POST",
                accept="application/json",
                form={"action": "get_listings", "per_page": str(MAX_JOBS)},
            )

        async def read_detail(url: str) -> bytes:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        before_bytes = await fetch_roster_payload()
        before = self.roster(before_bytes)

        result: list[JobInput] = []
        for job_id, detail_url in before.items():
            detail_bytes = await read_detail(detail_url)
            result.append(self.parse_detail(job_id, detail_url, detail_bytes))

        after_bytes = await fetch_roster_payload()
        after = self.roster(after_bytes)
        if before != after:
            raise ValueError("WP Job Manager roster changed during enumeration")

        return Enumeration(jobs=result, complete=True)

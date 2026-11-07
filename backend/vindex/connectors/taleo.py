"""Oracle Taleo Business Edition v2 public boards and full native JobPosting pages."""

import asyncio
import json
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit

import httpx
from bs4 import BeautifulSoup
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.schemas import Enumeration, JobInput

HOST = r"(?:phf|phg|phh|chp|chj|chu)\.tbe\.taleo\.net"
ORG = r"[A-Z0-9_]{1,80}"


def compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


class TaleoConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        parts = slug.split("~")
        if (
            provider != "taleo-tbe"
            or len(parts) != 4
            or not re.fullmatch(HOST, parts[0])
            or not re.fullmatch(re.escape(parts[0].split(".")[0]) + r"[0-9]{2}", parts[1])
            or not re.fullmatch(ORG, parts[2])
            or not re.fullmatch(r"[1-9][0-9]{0,5}", parts[3])
            or parts[2] == "TIMESTAMP_DEMO2"
        ):
            raise ValueError("Invalid Taleo Business Edition public board")
        self.host, self.pod, self.org, self.site = parts
        self.company = company
        self.origin = "https://" + self.host
        self.base = self.origin + f"/{self.pod}/ats/careers/v2/"
        self.http = PublicHTTP(client, {self.host})

    def url(self, route: str, identifier: str | None = None, offset: int = 0) -> str:
        params = {"org": self.org, "cws": self.site}
        if identifier:
            params["rid"] = identifier
        if offset:
            params["rowFrom"] = str(offset)
        return self.base + route + "?" + urlencode(params)

    def link(self, url: str, route: str, identifier: str | None = None) -> str:
        parsed = urlsplit(url)
        params = parse_qs(parsed.query)
        if (
            parsed.scheme != "https"
            or parsed.netloc != self.host
            or parsed.path != urlsplit(self.base + route).path
            or parsed.fragment
            or set(params) != {"org", "cws", "rid"}
            or params.get("org") != [self.org]
            or params.get("cws") != [self.site]
            or len(params["rid"]) != 1
            or not re.fullmatch(r"[1-9][0-9]*", params["rid"][0])
            or (identifier is not None and params["rid"] != [identifier])
        ):
            raise ValueError("Unscoped Taleo public job/application link")
        return params["rid"][0]

    def document(self, body: bytes) -> BeautifulSoup:
        if b"</html>" not in body.lower():
            raise ValueError("Truncated Taleo public document")
        soup = BeautifulSoup(body, "html.parser")
        if soup.title is None or soup.title.get_text(" ", strip=True) != "Career Center":
            raise ValueError("Unsupported native Taleo Business Edition v2 shell")
        return soup

    def page(self, body: bytes, offset: int) -> tuple[int | None, bool, dict[str, dict]]:
        soup = self.document(body)
        titles = soup.select("h4.oracletaleocwsv2-head-title > a.viewJobLink[href]")
        if not 0 < len(titles) <= 10:
            raise ValueError("Empty or oversized Taleo native ten-job page")
        rows = {}
        for anchor in titles:
            url = str(anchor["href"])
            identifier = self.link(url, "viewRequisition")
            title = anchor.get_text(" ", strip=True)
            if identifier in rows or not title:
                raise ValueError("Duplicate or missing Taleo public job identity")
            parent = anchor.parent
            info = parent.parent if parent is not None else None
            if info is None:
                raise ValueError("Missing Taleo original public list fields")
            columns = [d.get_text(" ", strip=True) for d in info.find_all("div", recursive=False)]
            rows[identifier] = {"url": url, "title": title, "unmapped_columns": columns}
        totals = []
        for heading in soup.select('h3[aria-label="Positions Matched"]'):
            if heading.parent is None:
                raise ValueError("Missing Taleo total container")
            counts = heading.parent.select(".oracletaleocwsv2-panel-number")
            if len(counts) != 1 or not re.fullmatch(r"[1-9][0-9]*", counts[0].get_text(strip=True)):
                raise ValueError("Malformed Taleo explicit total")
            totals.append(int(counts[0].get_text(strip=True)))
        if len(totals) > 1 or (totals and totals[0] > 200):
            raise ValueError("Ambiguous or oversized Taleo public total")
        next_links = soup.select("a.jscroll-next[href]")
        if len(next_links) > 1:
            raise ValueError("Ambiguous Taleo public pagination")
        if next_links:
            parsed = urlsplit(str(next_links[0]["href"]))
            params = parse_qs(parsed.query, keep_blank_values=True)
            if (
                parsed.scheme
                or parsed.netloc
                or parsed.path != urlsplit(self.base + "searchResults").path
                or parsed.fragment
                or params.get("rowFrom") != [str(offset + 10)]
                or set(params)
                - {"next", "rowFrom", "act", "sortColumn", "sortOrder", "currentTime"}
                or len(rows) != 10
            ):
                raise ValueError("Invalid Taleo native next-page scope/offset")
        if offset + len(rows) > 200 or (next_links and offset + 10 >= 200):
            raise ValueError("Taleo public page/detail budget exceeded")
        return totals[0] if totals else None, bool(next_links), rows

    def parse(self, payload: Any) -> list[JobInput]:
        identifier, listing, body = payload
        soup = self.document(body)
        docs = [json.loads(t.get_text()) for t in soup.select('script[type="application/ld+json"]')]
        docs = [d for d in docs if isinstance(d, dict) and d.get("@type") == "JobPosting"]
        boxes = soup.select(".well.oracletaleocwsv2-job-description")
        if len(docs) > 1 or len(boxes) != 1:
            raise ValueError("Taleo public job is unavailable or missing mandatory full metadata")
        row = docs[0] if docs else {}
        box = boxes[0]
        native_title = box.find("strong", recursive=False)
        if (
            (bool(row) and row.get("title") != listing["title"])
            or native_title is None
            or native_title.get_text(" ", strip=True) != listing["title"]
            or (bool(row) and str(row.get("identifier", {}).get("value")) != identifier)
        ):
            raise ValueError("Taleo native listed/detail job identity mismatch")
        if row:
            self.link(row["url"], "viewRequisition", identifier)
        applications = []
        for anchor in soup.select("a[href]"):
            value = str(anchor["href"])
            if urlsplit(value).path.endswith("/applyRequisition"):
                self.link(value, "applyRequisition", identifier)
                applications.append(value)
        if not applications or len(set(applications)) != 1:
            raise ValueError("Missing unique Taleo native public application control")
        metadata = {}
        for field in box.select("div.row > div"):
            key = field.select_one("span.small")
            content = field.select_one("strong")
            if (
                key is None
                or content is None
                or not key.get_text(strip=True)
                or key.get_text(strip=True) in metadata
            ):
                raise ValueError("Malformed Taleo native public job metadata")
            metadata[key.get_text(strip=True)] = content.get_text(" ", strip=True)
        native_company = row.get("hiringOrganization", {}).get("name") or metadata.get("Company")
        company = native_company or self.company
        if not metadata.get("Location") or not isinstance(company, str) or not company.strip():
            raise ValueError("Missing Taleo full public employer/location")
        full = soup.select("div.col-md-12.row")
        if len(full) != 1 or not text(str(full[0])).strip():
            raise ValueError("Missing unique Taleo full native description")
        if row and (
            not isinstance(row.get("description"), str)
            or compact(text(str(full[0]))) != compact(text(row["description"]))
        ):
            raise ValueError("Taleo full native description disagrees with JobPosting")
        descriptions = []
        brief = soup.select("div.alert.alert-info")
        if len(brief) > 1:
            raise ValueError("Ambiguous Taleo native Job Brief")
        if brief:
            descriptions.append(str(brief[0]))
        descriptions.append(str(full[0]))
        description_html = "\n".join(descriptions)
        supplied = row.get("datePosted")
        published = None
        flags = [] if row else ["structured_job_metadata_missing"]
        if not native_company:
            flags.append("company_from_source_configuration")
        if supplied:
            if re.fullmatch(
                r"[A-Z][a-z]{2} [A-Z][a-z]{2} [0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2} GMT [0-9]{4}",
                supplied,
            ):
                published = datetime.strptime(supplied, "%a %b %d %H:%M:%S GMT %Y").replace(
                    tzinfo=UTC
                )
            else:
                published = datetime.fromisoformat(supplied)
            if published.tzinfo is None:
                flags.append("publication_timezone_unspecified")
        salary = row.get("baseSalary")
        if salary is None and metadata.get("Salary"):
            salary = {"text": metadata["Salary"]}
        return [
            JobInput(
                external_id=identifier,
                title=listing["title"],
                company=company,
                description=text(description_html),
                location=metadata["Location"],
                source_url=listing["url"],
                application_url=applications[0],
                salary=salary,
                employment_type=row.get("employmentType"),
                remote_status=row.get("jobLocationType"),
                published_at=published,
                quality_flags=flags,
                raw={
                    "listing": listing,
                    "jobposting": row,
                    "native_metadata": metadata,
                    "employer_identity_source": "native"
                    if native_company
                    else "source_configuration",
                    "full_description_html": description_html,
                    "published_at_original": supplied,
                },
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor < 0 or cursor % 10 or cursor >= 200:
            raise ValueError("Invalid Taleo public ten-job offset")
        return await self.http.read(self.url("searchResults", offset=cursor))

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)

        async def read(url: str) -> bytes:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        async def roster() -> dict[str, dict]:
            result: dict[str, dict] = {}
            total = None
            offset = 0
            while True:
                count, more, rows = self.page(
                    await read(self.url("searchResults", offset=offset)), offset
                )
                if total is None:
                    total = count
                if (count is not None and total != count) or set(rows) & set(result):
                    raise ValueError("Taleo public total changed or repeated jobs")
                result.update(rows)
                if not more:
                    break
                offset += 10
            if total is not None and len(result) != total:
                raise ValueError("Incomplete Taleo full public result count")
            return result

        rows = await roster()
        jobs = []
        for identifier, listing in rows.items():
            jobs.extend(self.parse((identifier, listing, await read(listing["url"]))))
        if await roster() != rows:
            raise ValueError("Taleo full public board changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

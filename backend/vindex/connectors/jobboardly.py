"""Public hosted JobBoardly HTML pagination and JobPosting detail metadata."""

import asyncio
import json
import re
from typing import Any
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.connectors.teamtailor import TENANT
from vindex.schemas import Enumeration, JobInput

JOB_PATH = re.compile(r"/jobs/[a-z0-9-]+-[a-f0-9]{8}")


class JobboardlyConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider != "jobboardly" or not re.fullmatch(TENANT, slug):
            raise ValueError("Invalid JobBoardly tenant")
        self.origin = f"https://{slug}.jobboardly.com"
        self.http = PublicHTTP(client, {f"{slug}.jobboardly.com"})

    async def fetch(self, cursor: int = 0) -> Any:
        if type(cursor) is not int or not 0 <= cursor < 100:
            raise ValueError("Invalid JobBoardly page")
        query = f"?page={cursor + 1}" if cursor else ""
        return await self.http.read(f"{self.origin}/jobs{query}")

    def page(self, body: bytes, page: int, expected_start: int) -> tuple[list[str], bool]:
        soup = BeautifulSoup(body, "html.parser")
        nav = soup.select_one('nav[aria-label="Pagination"]')
        counter = soup.find(string=re.compile(r"^\s*Showing\s*$"))
        if nav is None or counter is None or counter.parent is None:
            raise ValueError("JobBoardly pagination or range counter missing")
        match = re.fullmatch(
            r"Showing ([0-9]+) to ([0-9]+)", counter.parent.get_text(" ", strip=True)
        )
        if not match or int(match[1]) != expected_start:
            raise ValueError("JobBoardly range does not match pagination")
        paths = []
        for link in soup.select("a[href]"):
            parsed = urlsplit(urljoin(self.origin, str(link["href"])))
            if parsed.netloc == urlsplit(self.origin).netloc and JOB_PATH.fullmatch(parsed.path):
                if parsed.query or parsed.fragment:
                    raise ValueError("Unexpected query on JobBoardly listing link")
                paths.append(parsed.path)
        paths = list(dict.fromkeys(paths))
        if not paths or int(match[2]) - int(match[1]) + 1 != len(paths):
            raise ValueError("JobBoardly listed links disagree with page range")
        controls = [
            node
            for node in nav.select("a,span[aria-disabled]")
            if node.get_text(" ", strip=True) == "Next"
        ]
        if len(controls) != 1:
            raise ValueError("JobBoardly Next control missing or ambiguous")
        next_control = controls[0]
        if next_control.name == "a":
            if next_control.get("href") != f"/jobs?page={page + 1}":
                raise ValueError("Unsafe or unexpected JobBoardly pagination target")
            return paths, True
        if next_control.get("aria-disabled") != "true":
            raise ValueError("JobBoardly terminal page is not explicit")
        return paths, False

    def parse(self, payload: Any) -> list[JobInput]:
        path, body = payload
        if not isinstance(path, str) or not JOB_PATH.fullmatch(path):
            raise ValueError("Invalid JobBoardly detail path")
        soup = BeautifulSoup(body, "html.parser")
        rows = []
        for script in soup.select('script[type="application/ld+json"]'):
            node = json.loads(script.get_text())
            if isinstance(node, dict) and node.get("@type") == "JobPosting":
                rows.append(node)
        flags = []
        html_metadata = []
        source_schema = rows[0] if len(rows) == 1 else None
        html_observation = None
        if not rows:
            heading = soup.select_one("main h1")
            description_node = soup.select_one("main .rich-text")
            canonical = soup.select_one('link[rel="canonical"]')
            og_url = soup.select_one('meta[property="og:url"]')
            og_title = soup.select_one('meta[property="og:title"]')
            og_image = soup.select_one('meta[property="og:image"]')
            company_link = (
                heading.parent.select_one("a[href]") if heading and heading.parent else None
            )
            image_url = str(og_image.get("content", "")) if og_image else ""
            image_id = re.fullmatch(r"/og/jobs/([0-9]{1,30})/[0-9]+\.jpg", urlsplit(image_url).path)
            if (
                heading is None
                or description_node is None
                or canonical is None
                or og_url is None
                or og_title is None
                or company_link is None
                or not image_id
                or og_url.get("content") != canonical.get("href")
                or og_title.get("content") != heading.get_text(" ", strip=True)
                or urlsplit(image_url).netloc != urlsplit(str(canonical.get("href"))).netloc
            ):
                raise ValueError("JobBoardly public HTML posting identity is incomplete")
            html_metadata = [
                node.get_text(" ", strip=True)
                for node in soup.select("div.flex.items-center.text-sm")
            ]
            employment_labels = {
                "Full-time",
                "Part-time",
                "Contract",
                "Temporary",
                "Internship",
                "Volunteer",
            }
            employment = next(
                (label for label in html_metadata if label in employment_labels), None
            )
            salary = next(
                (label for label in html_metadata if re.match(r"^[£$€][0-9]", label)), None
            )
            posted = soup.select_one("#job-posted-at")
            posted_text = posted.get_text(" ", strip=True) if posted else None
            locations = [
                label
                for label in html_metadata
                if label not in employment_labels
                and label not in {"Remote", "On-site", "Hybrid", salary, posted_text}
            ]
            if len(locations) > 1:
                raise ValueError("Ambiguous JobBoardly HTML location metadata")
            rows = [
                {
                    "@type": "JobPosting",
                    "url": str(canonical["href"]),
                    "identifier": {"value": image_id[1]},
                    "title": heading.get_text(" ", strip=True),
                    "hiringOrganization": {"name": company_link.get_text(" ", strip=True)},
                    "description": str(description_node),
                    "employmentType": employment,
                    "baseSalary": {"source_text": salary} if salary else None,
                    "jobLocation": {"address": {"addressLocality": locations[0]}}
                    if locations
                    else [],
                }
            ]
            html_observation = {
                "title_html": str(heading),
                "company_html": str(company_link),
                "description_html": str(description_node),
                "canonical_url": str(canonical["href"]),
                "og_image_url": image_url,
                "og_url": str(og_url.get("content")),
            }
            flags.append("jobposting_schema_missing")
        if len(rows) != 1:
            raise ValueError("JobBoardly full public JobPosting detail missing")
        row = rows[0]
        canonical = soup.select_one('link[rel="canonical"]')
        if (
            canonical is None
            or canonical.get("href") != row["url"]
            or urlsplit(row["url"]).path != path
        ):
            raise ValueError("JobBoardly detail identity mismatch")
        targets = [
            urljoin(self.origin, str(a["href"]))
            for a in soup.select("a[href]")
            if a.get_text(" ", strip=True).lower() == "apply now"
        ]
        if len(set(targets)) != 1:
            raise ValueError("JobBoardly application destination missing or ambiguous")
        key = row["identifier"]["value"]
        if isinstance(key, bool) or not re.fullmatch(r"[0-9]{1,30}", str(key)):
            raise ValueError("Invalid JobBoardly identifier")
        description = text(row["description"])
        places = row.get("jobLocation") or []
        if isinstance(places, dict):
            places = [places]
        locations = []
        for place in places:
            address = place["address"]
            locations.append(
                ", ".join(
                    dict.fromkeys(
                        address[k]
                        for k in ("addressLocality", "addressRegion", "addressCountry")
                        if address.get(k)
                    )
                )
            )
        employment = row.get("employmentType")
        if isinstance(employment, list):
            employment = ", ".join(employment)
        workplace_labels = list(
            dict.fromkeys(
                node.get_text(" ", strip=True)
                for node in soup.select("div.flex.items-center.text-sm")
                if node.get_text(" ", strip=True) in {"On-site", "Hybrid", "Remote"}
            )
        )
        if len(workplace_labels) > 1:
            raise ValueError("Ambiguous JobBoardly workplace labels")
        workplace = workplace_labels[0] if workplace_labels else row.get("jobLocationType")
        if not description:
            flags.append("description_missing")
        application = targets[0]
        if urlsplit(application).scheme == "mailto":
            # The public posting is the application entry point for email-only roles.
            # Preserve the actual destination in raw; public API links remain HTTPS.
            application = row["url"]
            flags.append("application_by_email")
        return [
            JobInput(
                external_id=str(key),
                title=row["title"],
                company=row["hiringOrganization"]["name"],
                description=description,
                quality_flags=flags,
                location="; ".join(locations),
                source_url=row["url"],
                application_url=application,
                employment_type=employment,
                remote_status=workplace,
                salary=row.get("baseSalary"),
                published_at=row.get("datePosted"),
                raw={
                    "jobposting": source_schema,
                    "application_url": targets[0],
                    "workplace_labels": workplace_labels,
                    "metadata_origin": "public_html" if html_metadata else "source_jsonld",
                    "html_metadata": html_metadata,
                    "html_observation": html_observation,
                },
            )
        ]

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)
        policy.check(f"{self.origin}/jobs")
        seen_paths: set[str] = set()
        jobs: list[JobInput] = []
        first_paths = []
        for page in range(1, 101):
            url = f"{self.origin}/jobs" + (f"?page={page}" if page > 1 else "")
            policy.check(url)
            await asyncio.sleep(policy.delay())
            paths, has_next = self.page(await self.fetch(page - 1), page, len(seen_paths) + 1)
            if page == 1:
                first_paths = paths
            for path in paths:
                if path in seen_paths:
                    raise ValueError("Repeated JobBoardly page or listing")
                if len(jobs) >= 400:
                    raise ValueError("JobBoardly exceeds 400-detail budget; snapshot incomplete")
                policy.check(self.origin + path)
                await asyncio.sleep(policy.delay())
                job = self.parse((path, await self.http.read(self.origin + path)))[0]
                if any(j.external_id == job.external_id for j in jobs):
                    raise ValueError("Duplicate JobBoardly detail identifier")
                jobs.append(job)
                seen_paths.add(path)
            if not has_next:
                await asyncio.sleep(policy.delay())
                confirmed, confirmed_next = self.page(await self.fetch(), 1, 1)
                if confirmed != first_paths or confirmed_next != (page > 1):
                    raise ValueError("JobBoardly first page changed during enumeration")
                return Enumeration(jobs=jobs, complete=True)
        raise ValueError("JobBoardly page budget exceeded")

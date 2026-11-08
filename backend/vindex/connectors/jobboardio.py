"""JobBoard.io public published job sitemaps and visible job details only."""

import asyncio
import json
import re
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any
from urllib.parse import parse_qs, urljoin, urlsplit
from xml.etree.ElementTree import ParseError

import httpx
from bs4 import BeautifulSoup, Tag
from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.schemas import Enumeration, JobInput

# These fixed origins are identified by the vendor case study or board owner.
# https://jobboard.io/case-studies/ and https://www.nifajobs.com/Disclaimer
HOSTS = frozenset({"www.nifajobs.com", "www.cancercareers.org"})
NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
JOB_PATH = r"/jobs/([1-9][0-9]{0,18})-[a-z0-9][a-z0-9._!~-]*"
MAP = "/sitemaps/jobs/job_sitemap_details.xml"
EMAIL = re.compile(r"[\w.!#$%&'*+/=?^`{|}~-]+@[\w-]+(?:\.[\w-]+)+")


def compact(value: str) -> str:
    return "".join(text(value).split())


def document(body: bytes) -> BeautifulSoup:
    if b"</html>" not in body.lower():
        raise ValueError("Truncated public HTML document")
    return BeautifulSoup(body, "html.parser")


def description_fields(source: str | None, native: Tag) -> tuple[str, dict[str, str]]:
    visible = text(str(native))
    if not visible or (source is not None and not compact(source)):
        raise ValueError("Missing JobBoard.io full description")
    markers = native.select(".__cf_email__[data-cfemail]")
    if not markers:
        if source is not None and compact(source) != compact(str(native)):
            raise ValueError("JobBoard.io full description mismatch")
        return visible, {"description_html": str(native)}
    if any(" ".join(m.get_text().split()) != "[email protected]" for m in markers):
        raise ValueError("Unrecognized JobBoard.io protected contact marker")
    visible = EMAIL.sub("[email protected]", " ".join(visible.split()))
    if source is not None:
        published = EMAIL.sub("[email protected]", text(source))
        if "".join(published.split()) != "".join(visible.split()):
            raise ValueError("JobBoard.io full description mismatch after contact masking")
    return visible, {
        "original_description_sha256": sha256(
            (source if source is not None else str(native)).encode()
        ).hexdigest()
    }


def xml_urls(body: bytes, *, index: bool) -> list[str]:
    try:
        root = ElementTree.fromstring(body)
    except (ParseError, DefusedXmlException) as error:
        raise ValueError("Malformed or unsafe public sitemap") from error
    if root.tag != NS + ("sitemapindex" if index else "urlset"):
        raise ValueError("Unexpected public sitemap document")
    entries = root.findall(NS + ("sitemap" if index else "url"))
    if not 0 < len(entries) <= (50 if index else 201):
        raise ValueError("Empty or oversized public sitemap")
    urls = []
    for entry in entries:
        loc = entry.findall(NS + "loc")
        if len(loc) != 1 or not loc[0].text or loc[0].text in urls:
            raise ValueError("Missing or duplicated public sitemap location")
        urls.append(loc[0].text)
    return urls


class JobBoardIOConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider != "jobboardio" or slug not in HOSTS:
            raise ValueError("Unsupported unreviewed JobBoard.io origin")
        self.host = slug
        self.origin = "https://" + slug
        self.http = PublicHTTP(client, {slug})

    def scope(self, url: str):
        p = urlsplit(url)
        if p.scheme != "https" or p.netloc != self.host or p.fragment:
            raise ValueError("Unscoped JobBoard.io URL")
        return p

    def identifier(self, url: str) -> str:
        p = self.scope(url)
        m = re.fullmatch(JOB_PATH, p.path)
        if p.query or not m:
            raise ValueError("Invalid native JobBoard.io job URL")
        return m[1]

    def maps(self, body: bytes) -> list[tuple[int, int, str]]:
        result = []
        for url in xml_urls(body, index=True):
            p = self.scope(url)
            if p.path != MAP:
                if (
                    not re.fullmatch(
                        r"/sitemaps/(?:pages/page|taxonomy/taxonomy)_sitemap_details\.xml", p.path
                    )
                    or p.query
                ):
                    raise ValueError("Unrecognized JobBoard.io sitemap entry")
                continue
            query = parse_qs(p.query, keep_blank_values=True)
            if set(query) != {"start_id", "finish_id"} or any(
                len(v) != 1 or not re.fullmatch(r"[1-9][0-9]{0,18}", v[0]) for v in query.values()
            ):
                raise ValueError("Invalid JobBoard.io sitemap bounds")
            start, finish = int(query["start_id"][0]), int(query["finish_id"][0])
            if start > finish:
                raise ValueError("Reversed JobBoard.io sitemap bounds")
            result.append((start, finish, url))
        result.sort()
        if not 0 < len(result) <= 4 or any(
            a[1] >= b[0] for a, b in zip(result, result[1:], strict=False)
        ):
            raise ValueError("Missing or overlapping JobBoard.io job-map ranges")
        return result

    def jobs_in_map(self, body: bytes, start: int, finish: int) -> dict[str, str]:
        result = {}
        homes = 0
        for url in xml_urls(body, index=False):
            p = self.scope(url)
            if p.path in {"", "/"} and not p.query:
                homes += 1
                continue
            identifier = self.identifier(url)
            if identifier in result or not start <= int(identifier) <= finish:
                raise ValueError("Repeated or out-of-range JobBoard.io ID")
            result[identifier] = url
        if homes > 1 or not result:
            raise ValueError("Empty or malformed JobBoard.io jobs map")
        return result

    def preview(self, body: bytes) -> dict[str, str]:
        soup = document(body)
        if not soup.select('form[action="/jobs/search"][method="get"]'):
            raise ValueError("Unsupported native JobBoard.io public board template")
        rows: dict[str, str] = {}
        for anchor in soup.select("a[href]"):
            href = str(anchor["href"])
            url = urljoin(self.origin, href)
            p = urlsplit(url)
            if p.netloc != self.host or not re.match(r"/jobs/[0-9]", p.path):
                continue
            identifier = self.identifier(url)
            if identifier in rows and rows[identifier] != url:
                raise ValueError("Ambiguous JobBoard.io public preview identity")
            rows[identifier] = url
        if not rows:
            raise ValueError("No native jobs in JobBoard.io public preview")
        return rows

    def parse(self, payload: Any) -> list[JobInput]:
        identifier, url, body = payload
        soup = document(body)
        rows = [json.loads(t.get_text()) for t in soup.select('script[type="application/ld+json"]')]
        rows = [r for r in rows if isinstance(r, dict) and r.get("@type") == "JobPosting"]
        canonical = soup.select('link[rel="canonical"]')
        titles = soup.select(".jobDetail-headerIntro h1")
        employers = soup.select(".jobDetail-headerIntro .text-primary.text-large")
        native = soup.select(".job-body")
        if len(rows) > 1 or any(
            len(nodes) != 1 for nodes in (canonical, titles, employers, native)
        ):
            raise ValueError("Missing complete JobBoard.io native job detail")
        row = rows[0] if rows else {}
        title = titles[0].get_text(" ", strip=True)
        company = employers[0].get_text(" ", strip=True)
        if (
            canonical[0].get("href") != url
            or self.identifier(url) != identifier
            or not title
            or not company
        ):
            raise ValueError("JobBoard.io canonical identity/employer/title mismatch")
        if rows:
            if (
                not isinstance(row.get("title"), str)
                or not isinstance(row["hiringOrganization"].get("name"), str)
                or compact(row["title"]) != compact(title)
                or compact(row["hiringOrganization"]["name"]) != compact(company)
                or not isinstance(row.get("description"), str)
            ):
                raise ValueError("JobBoard.io structured employer/title mismatch")
        description, description_raw = description_fields(row.get("description"), native[0])
        controls = soup.select('a.apply-button[id^="apply_button_job-details-"][data-job-id]')
        if not controls or any(a.get("data-job-id") != identifier for a in controls):
            raise ValueError("Missing or mismatched JobBoard.io application controls")
        links = {str(a.get("href", "")) for a in controls}
        if len(links) != 1:
            raise ValueError("Conflicting JobBoard.io application destinations")
        apply = links.pop()
        p = urlsplit(apply)
        flags = []
        application_raw = {}
        if all("external_apply" in a.get_attribute_list("class") for a in controls) and (
            p.scheme in {"http", "https"}
            and p.hostname
            and p.username is None
            and p.password is None
            and p.port in (None, 443 if p.scheme == "https" else 80)
        ):
            application_entry = "Advertised external HTTPS link; not fetched"
            if p.scheme == "http":
                flags.append("application_http_source")
                application_raw["application_url_original"] = apply
                apply = url
                application_entry = "Public posting links to upstream HTTP application"
        elif (
            apply == f"/applicants/new?id={identifier}&modal=true"
            and all(
                "modal_apply" in a.get_attribute_list("class")
                and a.get("data-target") == "#applyModal"
                and a.get("data-toggle") == "modal"
                for a in controls
            )
            and soup.select_one("#applyModal")
        ):
            # The applicant form is a modal fragment, not a standalone page.
            apply = url
            application_entry = "Public posting opens same-ID native application modal"
        else:
            raise ValueError("Unsupported JobBoard.io native application type")
        locations = [
            x.get_text(" ", strip=True)
            for x in soup.select(".jobDetail-headerIntro .fa-map-marker-alt + span")
        ]
        if "original_description_sha256" in description_raw:
            flags.append("source_contact_protected")
            if rows:
                row = {**row, "description": description}
        if not locations:
            flags.append("location_missing")
        date = row.get("datePosted")
        if not rows:
            dates = [
                x.get_text(" ", strip=True)
                for x in soup.select(".panel-body > .text-muted > span")
                if x.get_text(" ", strip=True).startswith("Posted ")
            ]
            if len(dates) != 1:
                raise ValueError("Missing or ambiguous JobBoard.io visible publication date")
            date = dates[0]
            published = datetime.strptime(date, "Posted %B %d, %Y")
            flags.extend(("structured_posting_missing", "publication_date_only"))
        elif not date:
            published = None
            flags.append("publication_date_missing")
        else:
            published = datetime.fromisoformat(date)
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
                flags.append("publication_date_only")
            elif published.tzinfo is None:
                flags.append("publication_timezone_unspecified")
        expiry = datetime.fromisoformat(row["validThrough"]) if row.get("validThrough") else None
        if expiry and expiry.tzinfo is not None and expiry <= datetime.now(UTC):
            flags.append("source_expiry_elapsed_while_listed")
        employment = row.get("employmentType")
        if isinstance(employment, list):
            employment = ", ".join(employment)
        visible_employment = soup.select_one(".jobDetail-headerIntro .fa-running + span")
        if not employment and visible_employment:
            employment = visible_employment.get_text(" ", strip=True)
        remote = row.get("jobLocationType")
        visible_remote = soup.select_one(".jobDetail-headerIntro .fa-wifi + span")
        if not remote and visible_remote:
            remote = visible_remote.get_text(" ", strip=True)
        salary = row.get("baseSalary")
        if not salary:
            visible = soup.select_one(".job-posting-salary-description")
            if visible and visible.get_text(" ", strip=True):
                salary = {"text": visible.get_text(" ", strip=True)}
        return [
            JobInput(
                external_id=identifier,
                title=title,
                company=company,
                description=description,
                location="; ".join(dict.fromkeys(locations)),
                source_url=url,
                application_url=apply,
                employment_type=employment,
                remote_status=remote,
                salary=salary,
                published_at=published,
                quality_flags=flags,
                raw={
                    "jobposting": row,
                    **description_raw,
                    **application_raw,
                    "published_at_original": date,
                    "valid_through_original": row.get("validThrough"),
                    "application_entry": application_entry,
                },
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("JobBoard.io requires full public sitemap enumeration")
        return await self.http.read(self.origin + "/")

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)
        index = self.origin + "/sitemap.xml"
        if index not in (policy.parser.site_maps() or []):
            raise ValueError("Missing advertised JobBoard.io sitemap")

        async def read(url):
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        async def roster() -> dict[str, str]:
            preview = self.preview(await read(self.origin + "/"))
            result: dict[str, str] = {}
            for start, finish, url in self.maps(await read(index)):
                rows = self.jobs_in_map(await read(url), start, finish)
                if set(result) & set(rows):
                    raise ValueError("Duplicate JobBoard.io job across maps")
                result.update(rows)
            if not 0 < len(result) <= 200 or any(result.get(i) != u for i, u in preview.items()):
                raise ValueError(
                    "JobBoard.io published sitemap disagrees with public preview or bounds"
                )
            return result

        rows = await roster()
        jobs = []
        for identifier, url in rows.items():
            jobs.extend(self.parse((identifier, url, await read(url))))
        if await roster() != rows:
            raise ValueError("JobBoard.io published roster changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

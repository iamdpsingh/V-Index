"""Public Jobiqo listings and canonical details on the reviewed Agrajo and United Way templates."""

import asyncio
import json
import re
from typing import Any
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup
from vindex.connectors.http import PublicHTTP
from vindex.connectors.jobboardio import EMAIL, document
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.schemas import Enumeration, JobInput

BOARDS = {
    "www.agrajo.com": ("/job", 12),
    "careers.unitedway.org": ("/jobs", 10),
    "www.kampajobs.ch": ("/jobs", 20),
}
STAGED_HOSTS = frozenset({"careers.unitedway.org", "www.kampajobs.ch"})
MAX_PAGES = 15
EMBED_HOST = "j.brt.mv"
EMBED_ORIGIN = f"https://{EMBED_HOST}"
POST_PATH = re.compile(r"/job/[a-z0-9][a-z0-9-]{0,249}")


class MissingJobPosting(ValueError):
    pass


def structured_postings(soup: BeautifulSoup) -> list[dict[str, Any]]:
    postings = []
    for script in soup.select('script[type="application/ld+json"]'):
        item = json.loads(script.get_text())
        if isinstance(item, dict) and item.get("@type") == "JobPosting":
            postings.append(item)
    return postings


class JobiqoConnector:
    def __init__(self, host: str, client: httpx.AsyncClient):
        if host not in BOARDS:
            raise ValueError("Unreviewed Jobiqo board")
        self.host = host
        self.origin = f"https://{host}"
        path, self.page_size = BOARDS[host]
        self.listing = self.origin + path
        self.agrajo = host == "www.agrajo.com"
        self.kampajobs = host == "www.kampajobs.ch"
        self.united_way = host == "careers.unitedway.org"
        self.http = PublicHTTP(client, {host})
        self.embed_http = PublicHTTP(client, {EMBED_HOST})
        self.embed_policy: RobotsPolicy | None = None

    async def read(self, url: str, policy: RobotsPolicy) -> bytes:
        policy.check(url)
        await asyncio.sleep(policy.delay())
        return await self.http.read(url)

    async def fetch(self, cursor: int = 0, policy: RobotsPolicy | None = None) -> bytes:
        if not 0 <= cursor < MAX_PAGES:
            raise ValueError("Jobiqo page is outside the supported range")
        page_parameter = cursor if self.kampajobs else cursor + 1
        url = self.listing if not cursor else f"{self.listing}?page={page_parameter}"
        return await self.read(url, policy or await RobotsPolicy.load(self.http, self.origin))

    def page(self, body: bytes) -> tuple[int, dict[str, str]]:
        soup = document(body)
        headings = soup.select("h1")
        total = (
            re.fullmatch(r"([1-9][0-9]*) Jobs?", headings[0].get_text(" ", strip=True))
            if len(headings) == 1
            else None
        )
        if total is None or int(total[1]) > self.page_size * MAX_PAGES:
            raise ValueError("Missing or oversized Jobiqo advertised total")
        rows = {}
        if self.kampajobs:
            selector, attribute, prefix = "article.node-job[id]", "id", "node-"
        elif self.agrajo:
            selector, attribute, prefix = '[id^="job-post-"]', "id", "job-post-"
        else:
            selector, attribute, prefix = (
                '[data-test-id^="job-teaser-"]',
                "data-test-id",
                "job-teaser-",
            )
        for card in soup.select(selector):
            identifier = re.fullmatch(
                re.escape(prefix) + r"([1-9][0-9]{0,15})(?: [a-z-]+)*",
                str(card[attribute]).strip(),
            )
            urls = set()
            for anchor in card.select("a[href]"):
                url = urlsplit(urljoin(self.listing, str(anchor["href"])))
                if (
                    url.scheme == "https"
                    and url.netloc == self.host
                    and POST_PATH.fullmatch(url.path)
                    and not url.query
                    and not url.fragment
                ):
                    urls.add(self.origin + url.path)
            if identifier is None or identifier[1] in rows or len(urls) != 1:
                raise ValueError("Invalid or repeated Jobiqo job card")
            posting_url = next(iter(urls))
            if self.united_way and not posting_url.endswith("-" + identifier[1]):
                raise ValueError("United Way card and posting IDs differ")
            rows[identifier[1]] = posting_url
        return int(total[1]), rows

    async def roster(self, policy: RobotsPolicy) -> dict[str, str]:
        total, rows = self.page(await self.fetch(policy=policy))
        if len(rows) != min(total, self.page_size):
            raise ValueError("Incomplete Jobiqo first page")
        for number in range(2, (total + self.page_size - 1) // self.page_size + 1):
            observed, page = self.page(await self.fetch(number - 1, policy))
            if (
                observed != total
                or rows.keys() & page.keys()
                or len(page) != min(self.page_size, total - len(rows))
            ):
                raise ValueError("Incomplete or changing Jobiqo roster")
            rows.update(page)
        if len(set(rows.values())) != total:
            raise ValueError("Repeated canonical Jobiqo posting")
        return rows

    def detail(
        self, body: bytes, identifier: str, url: str, embedded: dict[str, Any] | None = None
    ) -> JobInput:
        soup = document(body)
        canonical = soup.select('link[rel="canonical"][href]')
        headings = soup.select("main h1" if self.agrajo else "h1")
        if len(canonical) != 1 or canonical[0]["href"] != url or len(headings) != 1:
            raise ValueError(f"Invalid Jobiqo canonical detail for {identifier}")
        if self.kampajobs and not soup.select_one(f".node-job.node--full[id='node-{identifier}']"):
            raise ValueError(f"Kampajobs detail ID mismatch for {identifier}")
        postings = structured_postings(soup)
        if not postings and embedded is None:
            raise MissingJobPosting(f"Missing Jobiqo structured posting for {identifier}")
        if len(postings) > 1 or (postings and embedded is not None):
            raise ValueError(f"Ambiguous Jobiqo structured posting for {identifier}")
        posting = embedded if embedded is not None else postings[0]
        title = headings[0].get_text(" ", strip=True)
        company = text(posting.get("hiringOrganization", {}).get("name") or "")
        description_html = posting.get("description") or ""
        description = text(description_html)
        if not title or not company or not description:
            raise ValueError(f"Missing Jobiqo detail fields for {identifier}")
        if embedded is not None and text(embedded.get("title") or "") != title:
            raise ValueError(f"Jobiqo embedded title mismatch for {identifier}")
        if self.agrajo:
            controls = [
                control
                for control in soup.select("main a, main button")
                if re.fullmatch(r"(?i)(?:hier |jetzt )?bewerben", control.get_text(" ", strip=True))
            ]
        elif self.kampajobs:
            controls = [
                control
                for control in soup.select(".public-profile a[href], .public-profile button")
                if re.fullmatch(
                    r"(?i)(?:online |hier |jetzt )?bewerben(?: Sie sich)?",
                    control.get_text(" ", strip=True),
                )
                or "bewerben" in control.get_text(" ", strip=True).casefold()
                and control.get("href")
            ]
        else:
            controls = soup.select(
                '[data-test-id="job-apply-submit-button"], a:has(> [data-test-id="job-apply-submit-button"])'
            )
        advertised = [str(control["href"]) for control in controls if control.get("href")]
        board = {}
        if self.united_way:
            state = soup.select_one('script#__NEXT_DATA__[type="application/json"]')
            if state is None:
                raise ValueError(f"Missing United Way posting state for {identifier}")
            board = json.loads(state.get_text())["props"]["pageProps"]["data"]["jobByPath"][
                "content"
            ]
            if str(board["id"]) != identifier or board["urlNoPrefix"] != urlsplit(url).path:
                raise ValueError(f"United Way posting state mismatch for {identifier}")
            if (
                controls
                and board.get("applicationWorkflow") == "external"
                and board.get("applicationLink")
            ):
                advertised.append(board["applicationLink"])
        elif self.agrajo:
            advertised.extend(
                re.findall(
                    r'(?i)\[(?:hier |jetzt )?bewerben\]\((https://[^\s)]+)(?: "[^"]*")?\)',
                    description,
                )
            )
        links = set()
        for destination in advertised:
            link = urlsplit(urljoin(url, destination))
            if (
                link.scheme == "https"
                and link.hostname
                and not link.username
                and not link.password
                and link.port in (None, 443)
                and link.geturl() != url
            ):
                links.add(link.geturl())
        email_application = (
            self.agrajo
            and not controls
            and not links
            and "bewerbung" in description.casefold()
            and (
                soup.select_one('main .toastui-design a[href^="mailto:"]') is not None
                or (
                    "senden sie" in description.casefold() and EMAIL.search(description) is not None
                )
            )
        )
        if self.kampajobs and not controls and not links:
            email_application = (
                "bewerb" in description.casefold()
                and soup.select_one('.node--full .field--name-body a[href^="mailto:"]') is not None
            )
        if len(links) > 1 or (not controls and not links and not email_application):
            raise ValueError(f"Missing or ambiguous Jobiqo application entry for {identifier}")
        locations = []
        places = posting.get("jobLocation") or []
        for place in places if isinstance(places, list) else [places]:
            address = place.get("address") or {}
            location = ", ".join(
                str(address[key])
                for key in ("addressLocality", "addressRegion", "addressCountry")
                if address.get(key)
            )
            if location and location not in locations:
                locations.append(location)
        employment = posting.get("employmentType")
        remote = posting.get("remoteOption")
        salary = posting.get("baseSalary") or None
        if embedded is not None and board.get("salaryRangeFree", {}).get("currencyCode"):
            salary = {
                key: value
                for key, value in board["salaryRangeFree"].items()
                if key != "__typename" and value is not None
            }
        return JobInput(
            external_id=identifier,
            title=title,
            company=company,
            description=description,
            location="; ".join(locations),
            source_url=url,
            application_url=next(iter(links), url),
            employment_type=", ".join(employment) if isinstance(employment, list) else employment,
            remote_status=(
                ", ".join(remote) or None
                if isinstance(remote, list)
                else remote
                or ("Remote" if posting.get("jobLocationType") == "TELECOMMUTE" else None)
            ),
            salary=salary,
            published_at=board.get("published") or posting.get("datePosted"),
            quality_flags=["application_by_email"] if email_application else [],
            raw={
                "structured_title": posting.get("title"),
                "valid_through": posting.get("validThrough") or board.get("expiration"),
            },
        )

    def parse(self, payload: tuple[bytes, str, str, dict[str, Any] | None]) -> list[JobInput]:
        return [self.detail(*payload)]

    async def embedded_detail(self, body: bytes, identifier: str) -> dict[str, Any]:
        soup = document(body)
        frames = soup.select('[data-test-id="job_detail_container"] iframe[src]')
        if len(frames) == 1:
            destination = str(frames[0]["src"])
        elif not frames:
            state = soup.select_one('script#__NEXT_DATA__[type="application/json"]')
            if state is None:
                raise ValueError(f"Missing United Way posting state for {identifier}")
            board = json.loads(state.get_text())["props"]["pageProps"]["data"]["jobByPath"][
                "content"
            ]
            if (
                str(board["id"]) != identifier
                or board.get("type") != "job_per_template"
                or board.get("applicationWorkflow") != "external"
                or not text(board.get("description") or "")
            ):
                raise ValueError(f"Missing Jobiqo publisher posting for {identifier}")
            destination = board.get("applicationLink") or ""
        else:
            raise ValueError(f"Ambiguous Jobiqo embed for {identifier}")
        match = re.fullmatch(
            re.escape(EMBED_ORIGIN) + r"/jb\.do\?reqGK=([1-9][0-9]{0,15})&refresh=true",
            destination,
        )
        if match is None:
            raise ValueError(f"Unreviewed Jobiqo embed for {identifier}")
        url = match[0]
        if self.embed_policy is None:
            self.embed_policy = await RobotsPolicy.load(self.embed_http, EMBED_ORIGIN)
        self.embed_policy.check(url)
        await asyncio.sleep(self.embed_policy.delay())
        postings = structured_postings(document(await self.embed_http.read(url)))
        if (
            len(postings) != 1
            or str((postings[0].get("identifier") or {}).get("value")) != match[1]
        ):
            raise ValueError(f"Jobiqo embedded posting ID mismatch for {identifier}")
        return postings[0]

    async def read_job(self, identifier: str, url: str, policy: RobotsPolicy) -> JobInput:
        body = await self.read(url, policy)
        try:
            return self.detail(body, identifier, url)
        except MissingJobPosting:
            if not self.united_way:
                raise
            return self.detail(body, identifier, url, await self.embedded_detail(body, identifier))

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)
        roster = await self.roster(policy)
        jobs = [await self.read_job(identifier, url, policy) for identifier, url in roster.items()]
        if await self.roster(policy) != roster:
            raise ValueError("Jobiqo roster changed during refresh")
        return Enumeration(jobs=jobs, complete=True)

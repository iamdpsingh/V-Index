"""HireBridge public location-counted native boards and native job/application links."""

import asyncio
import re
from collections import Counter
from typing import Any

import httpx
from bs4 import BeautifulSoup
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.schemas import Enumeration, JobInput


def document(body: bytes) -> BeautifulSoup:
    if b"</html>" not in body.lower():
        raise ValueError("Truncated HireBridge document")
    return BeautifulSoup(body, "html.parser")


class HireBridgeConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider != "hirebridge" or not re.fullmatch(r"[1-9][0-9]{0,14}", slug):
            raise ValueError("Invalid HireBridge customer ID")
        self.cid = slug
        self.origin = "https://recruit.hirebridge.com"
        self.url = f"{self.origin}/v3/Jobs/list.aspx?cid={slug}"
        self.http = PublicHTTP(client, {"recruit.hirebridge.com"})

    def logos(self, soup: BeautifulSoup) -> list[str]:
        paths = sorted(
            {
                str(i.get("src"))
                for i in soup.select("img[src]")
                if str(i.get("src")).startswith(f"{self.origin}/v3/xFiles/{self.cid}/")
                and "?" not in str(i.get("src"))
            }
        )
        if not paths:
            raise ValueError("Missing HireBridge customer-scoped public brand identity")
        return paths

    def listings(self, body: bytes) -> tuple[dict, dict[str, dict]]:
        soup = document(body)
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        if not title.endswith(" Career Center") or not title.removesuffix(" Career Center").strip():
            raise ValueError("Missing named HireBridge career center")
        headings = [h.get_text(" ", strip=True) for h in soup.select("h1")]
        form = soup.select_one("form#aspnetForm")
        selects = soup.select('select[id$="_jobloc"]')
        if (
            headings != ["Open Positions"]
            or form is None
            or form.get("action") != f"./list.aspx?cid={self.cid}"
            or len(selects) != 1
            or soup.select('.pagination,[rel="next"]')
        ):
            raise ValueError("HireBridge unsupported filtered/paginated board")
        counts = {}
        empty = []
        for option in selects[0].select("option"):
            if not option.get("value"):
                empty.append(option.get_text(" ", strip=True))
                continue
            label = option.get_text(" ", strip=True)
            matched = re.fullmatch(r"(.+) \(([1-9][0-9]*)\)", label)
            if not matched or matched[1] in counts or option.has_attr("selected"):
                raise ValueError("Invalid HireBridge full location counters")
            counts[matched[1]] = int(matched[2])
        if empty != ["All Locations"] or not counts or not 0 < sum(counts.values()) <= 400:
            raise ValueError("Missing complete HireBridge location counters")
        rows = {}
        for element in soup.select("ul.jobs li"):
            anchors = element.select(".job a[href]")
            location = element.find_previous("h2")
            if len(anchors) != 1 or location is None:
                raise ValueError("Malformed HireBridge job/location group")
            path = str(anchors[0]["href"])
            matched = re.fullmatch(
                rf"/v3/Jobs/JobDetails\.aspx\?cid={self.cid}&jid=([1-9][0-9]{{0,14}})", path
            )
            name = anchors[0].get_text(" ", strip=True)
            department = element.select_one(".department")
            if not matched or not name or matched[1] in rows:
                raise ValueError("Invalid HireBridge native job ID/title")
            rows[matched[1]] = {
                "path": path,
                "title": name,
                "location": location.get_text(" ", strip=True),
                "department": department.get_text(" ", strip=True) if department else None,
            }
        if Counter(row["location"] for row in rows.values()) != counts:
            raise ValueError("HireBridge location counts and full list disagree")
        visible = {
            str(a["href"]) for a in soup.select("a[href]") if "JobDetails.aspx" in str(a["href"])
        }
        if visible != {r["path"] for r in rows.values()}:
            raise ValueError("HireBridge public links and location list disagree")
        return {
            "company": title.removesuffix(" Career Center"),
            "logos": self.logos(soup),
            "location_counts": counts,
        }, rows

    def parse(self, payload: Any) -> list[JobInput]:
        identifier, listing, board, body = payload
        soup = document(body)
        titles = soup.select("h1")
        locations = soup.select("h2")
        form = soup.select_one("form#aspnetForm")
        applies = []
        for anchor in soup.select("a[href]"):
            if anchor.get_text(" ", strip=True) != "Apply":
                continue
            matched = re.fullmatch(
                rf"javascript:popUp\('(https://recruit\.hirebridge\.com/v3/applicationv2/JobApplylogin\.aspx\?cid={self.cid}&jid={identifier})'\)",
                str(anchor["href"]),
            )
            if not matched:
                raise ValueError("Unsafe or mismatched HireBridge native application link")
            applies.append(matched[1])
        if (
            len(titles) != 1
            or titles[0].get_text(" ", strip=True) != listing["title"]
            or len(locations) != 1
            or locations[0].get_text(" ", strip=True) != listing["location"]
            or form is None
            or form.get("action") != f"./JobDetails.aspx?cid={self.cid}&jid={identifier}"
            or self.logos(soup) != board["logos"]
            or not applies
            or len(set(applies)) != 1
        ):
            raise ValueError("HireBridge detail/customer/location/application identity mismatch")
        sections = {}
        for suffix in ("jobdesc", "skilldesc"):
            elements = soup.select(f'span[id$="_{suffix}"]')
            if len(elements) > 1 or (suffix == "jobdesc" and len(elements) != 1):
                raise ValueError("Missing or duplicate HireBridge full description")
            if elements:
                sections[suffix] = str(elements[0])
        description = "\n\n".join(text(value) for value in sections.values() if text(value))
        return [
            JobInput(
                external_id=identifier,
                title=listing["title"],
                company=board["company"],
                description=description,
                quality_flags=[] if description else ["description_missing"],
                location=listing["location"],
                source_url=self.origin + listing["path"],
                application_url=applies[0],
                remote_status=listing["location"]
                if listing["location"].startswith("Remote")
                else None,
                raw={
                    "listing": listing,
                    "board": board,
                    "description_sections_html": sections,
                    "original_application_url": applies[0],
                },
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("HireBridge pagination unsupported")
        return await self.http.read(self.url)

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)

        async def read(url: str) -> bytes:
            policy.check(url)
            await asyncio.sleep(policy.delay(baseline=3.0))
            try:
                return await self.http.read(url)
            except ValueError as error:
                cause = error.__cause__
                if isinstance(cause, httpx.HTTPStatusError) and cause.response.headers.get(
                    "Retry-After"
                ):
                    wait = cause.response.headers["Retry-After"][:100]
                    raise ValueError(
                        f"HireBridge upstream cooldown Retry-After={wait}; run aborted"
                    ) from error
                raise

        board, rows = self.listings(await read(self.url))
        jobs = []
        for identifier, listing in rows.items():
            jobs.extend(
                self.parse((identifier, listing, board, await read(self.origin + listing["path"])))
            )
        if self.listings(await read(self.url)) != (board, rows):
            raise ValueError("HireBridge complete public board changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

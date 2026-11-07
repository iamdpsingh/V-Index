"""Paylocity public full client job-list state and native HTML description pages."""

import asyncio
import json
import re
from typing import Any
from uuid import UUID

import httpx
from bs4 import BeautifulSoup, Tag
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.schemas import Enumeration, JobInput


def page(body: bytes) -> tuple[BeautifulSoup, dict]:
    if b"</html>" not in body.lower():
        raise ValueError("Truncated Paylocity document")
    soup = BeautifulSoup(body, "html.parser")
    values = []
    for script in soup.select("script:not([src])"):
        code = script.get_text()
        for matched in re.finditer(r"window\.pageData\s*=\s*", code):
            value, _ = json.JSONDecoder().raw_decode(code[matched.end() :])
            values.append(value)
    if len(values) != 1 or not isinstance(values[0], dict):
        raise ValueError("Missing unique Paylocity public page state")
    return soup, values[0]


class PaylocityConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider != "paylocity" or str(UUID(slug)) != slug:
            raise ValueError("Invalid Paylocity public board UUID")
        self.slug = slug
        self.origin = "https://recruiting.paylocity.com"
        self.path = "/Recruiting/Jobs/All/" + slug
        self.http = PublicHTTP(client, {"recruiting.paylocity.com"})

    def listings(self, body: bytes) -> tuple[dict, dict[int, dict]]:
        soup, state = page(body)
        if (
            not isinstance(state["ModuleId"], str)
            or not re.fullmatch(r"[1-9][0-9]*", state["ModuleId"])
            or not isinstance(state["ModuleTitle"], str)
            or not state["ModuleTitle"].strip()
            or state["ModuleTitle"].strip().lower()
            in {
                "all positions",
                "job opportunities",
                "current open positions",
                "job openings",
                "openings & internships",
            }
            or state["ShowInternal"] is not False
            or state["LeadJoinUrl"] != "/Recruiting/PublicLeads/New/" + self.slug
            or not isinstance(state["Jobs"], list)
            or not 0 < len(state["Jobs"]) <= 400
        ):
            raise ValueError("Paylocity invalid/internal/empty or oversized public board")
        if (
            soup.title is None
            or soup.title.get_text(" ", strip=True) != state["ModuleTitle"] + " - Job Opportunities"
        ):
            raise ValueError("Paylocity named board identity mismatch")
        logo = state["LogoUrl"]
        if not isinstance(logo, str) or not re.fullmatch(
            rf"/Recruiting/Jobs/GetLogoFileById\?logoFileStoreId=[1-9][0-9]*&moduleId={state['ModuleId']}",
            logo,
        ):
            raise ValueError("Paylocity public module/brand identity mismatch")
        board = {k: state[k] for k in ("ModuleId", "ModuleTitle", "ShowInternal", "LogoUrl")}
        rows = {}
        for row in state["Jobs"]:
            identifier = row["JobId"]
            if (
                type(identifier) is not int
                or identifier <= 0
                or identifier in rows
                or row["IsInternal"] is not False
                or not isinstance(row["JobTitle"], str)
                or not row["JobTitle"].strip()
                or type(row["IsRemote"]) is not bool
                or type(row["ShouldDisplayLocation"]) is not bool
                or row["JobLocation"]["ModuleId"] != int(board["ModuleId"])
                or not isinstance(row["Description"], str)
                or not isinstance(row["PublishedDate"], str)
            ):
                raise ValueError("Paylocity listed ID/public state/module mismatch")
            rows[identifier] = {
                k: row[k]
                for k in (
                    "JobId",
                    "JobTitle",
                    "LocationName",
                    "ShouldDisplayLocation",
                    "PublishedDate",
                    "Description",
                    "IsInternal",
                    "HiringDepartment",
                    "IsRemote",
                    "IndeedRemoteType",
                )
            }
            rows[identifier]["JobLocation"] = {
                k: row["JobLocation"].get(k)
                for k in (
                    "LocationId",
                    "ModuleId",
                    "Name",
                    "Address",
                    "Address2",
                    "City",
                    "State",
                    "Zip",
                    "Country",
                )
            }
        return board, rows

    def parse(self, payload: Any) -> list[JobInput]:
        identifier, listing, board, body = payload
        soup, data = page(body)
        url = f"{self.origin}/Recruiting/Jobs/Details/{identifier}"
        og = soup.select('meta[property="og:url"]')
        heading = soup.select(".job-preview-title")
        apply = soup.select("a.apply-link-marker[href]")
        if (
            data["jobTitle"] != listing["JobTitle"]
            or data["moduleName"] != board["ModuleTitle"]
            or len(og) != 1
            or og[0].get("content") != url
            or len(heading) != 1
            or heading[0].get_text(" ", strip=True) != listing["JobTitle"]
            or not soup.select_one(f'img[src="{board["LogoUrl"]}"]')
            or not apply
            or any(a.get("href") != f"/Recruiting/Jobs/Apply/{identifier}" for a in apply)
        ):
            raise ValueError("Paylocity detail/company/native application identity mismatch")
        sections = {}
        for header in soup.select(".job-preview-details .job-listing-header"):
            label = header.get_text(" ", strip=True)
            if not label or label in sections:
                raise ValueError("Duplicate or unnamed Paylocity detail section")
            content = []
            for sibling in header.next_siblings:
                if isinstance(sibling, Tag) and (
                    "job-listing-header" in sibling.get_attribute_list("class")
                    or sibling.select_one(".job-listing-header,.apply-link-marker")
                    or "apply-link-marker" in sibling.get_attribute_list("class")
                ):
                    break
                content.append(str(sibling))
            sections[label] = "".join(content)
        if "Description" not in sections:
            raise ValueError("Missing full Paylocity description section")
        description = "\n\n".join(
            text(value)
            for label, value in sections.items()
            if label not in {"Job Type", "Salary Description"} and text(value)
        )
        salary = text(sections.get("Salary Description", ""))
        employment = text(sections.get("Job Type", ""))
        place = listing["JobLocation"]
        locations = [listing["LocationName"]] + [
            place[k] for k in ("City", "State", "Zip", "Country") if place.get(k)
        ]
        remote = None
        flags = [] if description else ["description_missing"]
        if listing["IsRemote"]:
            native_location = soup.select_one(".preview-location")
            if native_location is None:
                raise ValueError("Missing Paylocity native remote label")
            label = native_location.get_text(" ", strip=True).split("•", 1)[0].strip()
            if label not in {"Fully Remote", "Hybrid Remote"}:
                raise ValueError("Unrecognized Paylocity source remote label")
            remote = label
        return [
            JobInput(
                external_id=str(identifier),
                title=listing["JobTitle"],
                company=board["ModuleTitle"],
                description=description,
                quality_flags=flags,
                location="; ".join(dict.fromkeys(x for x in locations if x)),
                source_url=url,
                application_url=f"{self.origin}/Recruiting/Jobs/Apply/{identifier}",
                employment_type=employment or None,
                remote_status=remote,
                salary={"text": salary} if salary else None,
                published_at=listing["PublishedDate"],
                raw={"listing": listing, "board": board, "detail_sections_html": sections},
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("Paylocity alternate pagination unsupported")
        return await self.http.read(self.origin + self.path)

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)

        async def read(url: str) -> bytes:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        board, rows = self.listings(await read(self.origin + self.path))
        jobs = []
        for identifier, listing in rows.items():
            jobs.extend(
                self.parse(
                    (
                        identifier,
                        listing,
                        board,
                        await read(f"{self.origin}/Recruiting/Jobs/Details/{identifier}"),
                    )
                )
            )
        if self.listings(await read(self.origin + self.path)) != (board, rows):
            raise ValueError("Paylocity complete public roster changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

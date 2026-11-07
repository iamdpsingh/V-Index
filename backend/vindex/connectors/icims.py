"""Classic native iCIMS public iframe listings and complete structured job pages."""

import asyncio
import json
import re
from hashlib import sha256
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

import httpx
from bs4 import BeautifulSoup, Tag
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.connectors.teamtailor import TENANT
from vindex.schemas import Enumeration, JobInput


def document(body: bytes) -> BeautifulSoup:
    if b"</html>" not in body.lower():
        raise ValueError("Truncated iCIMS public document")
    return BeautifulSoup(body, "html.parser")


def normalized(value: str) -> str:
    return " ".join(value.split())


def fields(node: Tag) -> dict[str, str]:
    result = {}
    for group in node.select(".iCIMS_JobHeaderTag"):
        key = group.select_one(".iCIMS_JobHeaderField")
        value = group.select_one(".iCIMS_JobHeaderData")
        if key is None or value is None:
            raise ValueError("Malformed iCIMS native public field")
        name = normalized(key.get_text(" ", strip=True))
        if not name or name in result:
            raise ValueError("Duplicate iCIMS native public field")
        result[name] = normalized(value.get_text(" ", strip=True))
    return result


class ICIMSConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider != "icims" or not re.fullmatch(TENANT, slug):
            raise ValueError("Invalid iCIMS public tenant")
        self.host = slug + ".icims.com"
        self.origin = "https://" + self.host
        self.http = PublicHTTP(client, {self.host})

    def page_url(self, page: int) -> str:
        return self.origin + f"/jobs/search?pr={page}&in_iframe=1&searchRelation=keyword_all"

    def page(self, body: bytes, page: int) -> tuple[str, int, dict[str, dict]]:
        soup = document(body)
        headings = soup.select("h2.iCIMS_SubHeader_Jobs")
        titles = soup.select("h1.iCIMS_Header")
        if (
            soup.title is None
            or len(headings) != 1
            or len(titles) != 1
            or titles[0].get_text(" ", strip=True) != "Job Listings"
            or not soup.title.get_text().startswith("Job Listings at ")
        ):
            raise ValueError("Unsupported iCIMS public listings template")
        match = re.fullmatch(
            r"Search Results\s+Page ([1-9][0-9]*) of ([1-9][0-9]*)",
            normalized(headings[0].get_text(" ", strip=True)),
        )
        if not match or int(match[1]) != page + 1 or not page < int(match[2]) <= 8:
            raise ValueError("Invalid iCIMS public pagination metadata")
        cards = soup.select("ul.iCIMS_JobsTable > li.iCIMS_JobCardItem")
        if not 0 < len(cards) <= 50 or (page + 1 < int(match[2]) and len(cards) != 50):
            raise ValueError("Incomplete iCIMS native 50-job page")
        rows = {}
        for card in cards:
            anchors = card.select("div.title > a[href]")
            if len(anchors) != 1 or len(anchors[0].select("h3")) != 1:
                raise ValueError("Missing unique iCIMS public job link/title")
            anchor = anchors[0]
            parsed = urlsplit(str(anchor["href"]))
            identifier = re.fullmatch(r"/jobs/([1-9][0-9]*)/[^/]+/job", parsed.path)
            title = normalized(anchor.select("h3")[0].get_text(" ", strip=True))
            if (
                parsed.scheme != "https"
                or parsed.netloc != self.host
                or parse_qs(parsed.query) != {"in_iframe": ["1"]}
                or parsed.fragment
                or not identifier
                or any(c in unquote(parsed.path.split("/")[-2]) for c in "/\\?#")
                or not title
                or identifier[1] in rows
                or anchor.get("title") != identifier[1] + " - " + title
            ):
                raise ValueError("Invalid iCIMS native scoped job identity")
            rows[identifier[1]] = {
                "title": title,
                "url": str(anchor["href"]),
                "fields": fields(card),
            }
        return soup.title.get_text(), int(match[2]), rows

    def parse(self, payload: Any) -> list[JobInput]:
        identifier, listing, brand, body = payload
        soup = document(body)
        docs = [json.loads(t.get_text()) for t in soup.select('script[type="application/ld+json"]')]
        docs = [d for d in docs if isinstance(d, dict) and d.get("@type") == "JobPosting"]
        canonical = listing["url"].split("?", 1)[0]
        links = soup.select('link[rel="canonical"]')
        headings = soup.select("h1.iCIMS_Header")
        if (
            len(docs) != 1
            or len(links) != 1
            or links[0].get("href") != canonical
            or len(headings) != 1
            or normalized(headings[0].get_text(" ", strip=True)) != listing["title"]
        ):
            raise ValueError("Missing or mismatched iCIMS full public detail")
        row = docs[0]
        if (
            row.get("url") != canonical
            or row.get("title") != listing["title"]
            or not isinstance(row.get("hiringOrganization"), dict)
            or not isinstance(row["hiringOrganization"].get("name"), str)
            or not row["hiringOrganization"]["name"].strip()
        ):
            raise ValueError("iCIMS JobPosting public title/company/link mismatch")
        applications = []
        for anchor in soup.select("a[href]"):
            parsed = urlsplit(str(anchor["href"]))
            params = parse_qs(parsed.query)
            if params.get("mode") == ["apply"] and params.get("apply") == ["yes"]:
                if (
                    parsed.scheme != "https"
                    or parsed.netloc != self.host
                    or parsed.path != urlsplit(canonical).path
                    or parsed.fragment
                    or set(params) - {"mode", "apply", "in_iframe", "hashed"}
                    or params.get("in_iframe") != ["1"]
                ):
                    raise ValueError("Unscoped iCIMS native application control")
                applications.append(str(anchor["href"]))
        if not applications:
            raise ValueError("No iCIMS native public application control")
        sections = soup.select(".iCIMS_JobContent > .iCIMS_InfoMsg_Job")
        if not sections or not isinstance(row.get("description"), str):
            raise ValueError("Missing iCIMS full public description")
        section_parts = []
        section_headings = []
        for section in sections:
            heading = section.find_previous_sibling("h2")
            if heading is not None:
                section_parts.append(str(heading))
            else:
                heading = section.find("h2", recursive=False)
                if heading is None:
                    raise ValueError("Missing iCIMS full description section heading")
            section_headings.append(heading)
            section_parts.append(str(section))
        description_html = "\n".join(section_parts)
        description = text(description_html)
        if not description or re.sub(r"\s+", "", description) != re.sub(
            r"\s+", "", text(row["description"])
        ):
            raise ValueError("iCIMS complete HTML/JobPosting text disagrees")
        detail_fields = fields(soup)
        for key in set(listing["fields"]) & set(detail_fields):
            if listing["fields"][key] != detail_fields[key]:
                raise ValueError("iCIMS listed/detail native fields disagree")
        locations = row.get("jobLocation")
        if not isinstance(locations, list) or not locations:
            raise ValueError("Missing iCIMS structured locations")
        places = []
        for place in locations:
            address = place.get("address") or {}
            label = ", ".join(
                dict.fromkeys(
                    address[k]
                    for k in ("addressLocality", "addressRegion", "postalCode", "addressCountry")
                    if address.get(k) and address[k] != "UNAVAILABLE"
                )
            )
            if not label:
                raise ValueError("Unusable iCIMS structured location")
            places.append(label)
        pay = []
        for heading, section in zip(section_headings, sections, strict=True):
            content = section.select_one(".iCIMS_Expandable_Text")
            if (
                heading
                and content
                and any(
                    k in heading.get_text().casefold()
                    for k in ("salary", "pay range", "compensation")
                )
            ):
                value = content.get_text(" ", strip=True)
                if value:
                    pay.append(value)
        salary = row.get("baseSalary")
        if salary is None and pay:
            salary = {"text": "; ".join(pay)}
        elif salary is not None and pay:
            salary = {"structured": salary, "text": "; ".join(pay)}
        remote = (
            listing["fields"].get("Work Site")
            or detail_fields.get("Work Site")
            or row.get("jobLocationType")
        )
        # The original entry is stable; the application control's hashed parameter rotates.
        # Retain the public control's query keys without its rotating hash.
        if (
            listing["title"].startswith("PRACTICE:")
            and "it is not a real job opening and no one will be hired from it."
            in description.casefold()
        ):
            return []  # Explicit native non-job, after full detail validation; not counted.
        apply = canonical  # Stable native posting is the public application entry.
        return [
            JobInput(
                external_id=identifier,
                title=listing["title"],
                company=row["hiringOrganization"]["name"],
                description=description,
                location="; ".join(dict.fromkeys(places)),
                source_url=canonical,
                application_url=apply,
                salary=salary,
                employment_type=row.get("employmentType"),
                remote_status=remote,
                published_at=row.get("datePosted"),
                raw={
                    "listing": listing,
                    "board_title": brand,
                    "jobposting": row,
                    "detail_fields": detail_fields,
                    "full_description_html": description_html,
                    "native_apply_control_query_keys": sorted(
                        parse_qs(urlsplit(applications[0]).query)
                    ),
                    "publication_source": "native_jobposting_datePosted",
                },
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        if not 0 <= cursor < 8:
            raise ValueError("iCIMS public page budget exceeded")
        return await self.http.read(self.page_url(cursor))

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)

        async def read(url: str) -> bytes:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        async def roster() -> tuple[str, dict[str, dict]]:
            brand, pages, rows = self.page(await read(self.page_url(0)), 0)
            for page in range(1, pages):
                next_brand, total, following = self.page(await read(self.page_url(page)), page)
                if next_brand != brand or total != pages or set(rows) & set(following):
                    raise ValueError("iCIMS public pages changed or repeated IDs")
                rows.update(following)
            return brand, rows

        brand, rows = await roster()
        jobs = []
        excluded = []
        for identifier, listing in rows.items():
            body = await read(listing["url"])
            parsed = self.parse((identifier, listing, brand, body))
            if not parsed:
                excluded.append(
                    {
                        "id": identifier,
                        "listing": listing,
                        "reason": "Native practice posting explicitly states it is not a real job opening and no one will be hired from it",
                        "payload_sha256": sha256(body).hexdigest(),
                    }
                )
            jobs.extend(parsed)
        for job in jobs:
            job.raw["excluded_non_job_postings"] = excluded
        if len({j.company for j in jobs}) != 1:
            raise ValueError("Unsupported mixed employer iCIMS public board")
        if await roster() != (brand, rows):
            raise ValueError("iCIMS full public board changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

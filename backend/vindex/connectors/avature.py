"""Avature native six-record public SSR portals, modern and classic full detail templates."""

import asyncio
import json
import re
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

import httpx
from bs4 import BeautifulSoup, Tag
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.connectors.teamtailor import TENANT
from vindex.schemas import Enumeration, JobInput

PORTAL = r"(?:[a-z]{2}_[A-Z]{2}/)?[A-Za-z0-9_-]{1,60}"


def normalized(value: str) -> str:
    return " ".join(value.split())


def compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


def parent_text(node: Tag) -> str:
    parent = node.parent
    if not isinstance(parent, Tag):
        raise ValueError("Malformed Avature native public label")
    return normalized(parent.get_text(" ", strip=True))


class AvatureConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        parts = slug.split("~")
        if (
            provider != "avature"
            or len(parts) != 2
            or not re.fullmatch(TENANT, parts[0])
            or not re.fullmatch(PORTAL, parts[1])
            or any(
                t.casefold() in {"internal", "employee", "employees", "referrals"}
                for t in parts[1].split("/")
            )
        ):
            raise ValueError("Invalid native Avature public portal")
        tenant, portal = parts
        self.host = tenant + ".avature.net"
        self.origin = "https://" + self.host
        self.base = self.origin + "/" + portal
        self.http = PublicHTTP(client, {self.host})

    def document(self, body: bytes) -> BeautifulSoup:
        if b"</html>" not in body.lower():
            raise ValueError("Truncated Avature public document")
        return BeautifulSoup(body, "html.parser")

    def details_url(self, url: str) -> str:
        parsed = urlsplit(url)
        matched = re.fullmatch(
            re.escape(urlsplit(self.base).path) + r"/JobDetail/([^/]+)/([1-9][0-9]*)", parsed.path
        )
        if (
            parsed.scheme != "https"
            or parsed.netloc != self.host
            or parsed.query
            or parsed.fragment
            or not matched
            or any(c in unquote(matched[1]) for c in "/\\?#")
        ):
            raise ValueError("Unscoped Avature public job URL")
        return matched[2]

    def context_fields(self, node: Tag, modern: bool) -> dict[str, str]:
        result = {}
        if modern:
            for key, selector in [("Location", ".icon-address"), ("Team", ".icon-tag")]:
                icons = node.select(selector)
                if len(icons) > 1:
                    raise ValueError("Duplicate Avature native public label")
                if icons:
                    result[key] = parent_text(icons[0])
        else:
            for span in node.select("p.job-context > span"):
                label = span.find("strong", recursive=False)
                if label is None:
                    raise ValueError("Missing Avature classic public field label")
                key = label.get_text(strip=True).rstrip(":").strip()
                value = normalized(span.get_text(" ", strip=True))[
                    len(normalized(label.get_text(" ", strip=True))) :
                ].strip()
                if not key or key in result:
                    raise ValueError("Duplicate Avature classic public label")
                result[key] = value
        return result

    def page(self, body: bytes, offset: int) -> tuple[dict, int, dict[str, dict]]:
        soup = self.document(body)
        modern = bool(soup.select(".list-controls__text__legend"))
        legends = soup.select(".list-controls__text__legend" if modern else ".jobPaginationLegend")
        values = {normalized(t.get_text(" ", strip=True)) for t in legends}
        if soup.title is None or len(values) != 1:
            raise ValueError("Missing unique Avature native public result range")
        pattern = (
            r"([1-9][0-9]*)-([1-9][0-9]*) of ([1-9][0-9]*) results"
            if modern
            else r"Displaying ([1-9][0-9]*)-([1-9][0-9]*) of ([1-9][0-9]*)"
        )
        match = re.fullmatch(pattern, next(iter(values)))
        if (
            not match
            or int(match[1]) != offset + 1
            or not 0 < int(match[3]) <= 200
            or int(match[2]) != min(offset + 6, int(match[3]))
        ):
            raise ValueError("Incomplete or oversized Avature native six-job range")
        cards = soup.select("article.article--jobs" if modern else "ul.results > li.group")
        if len(cards) != int(match[2]) - offset:
            raise ValueError("Avature public card/range count mismatch")
        headings = soup.select("h1" if modern else "h2.pageTitle")
        if len(headings) != 1 or not headings[0].get_text(" ", strip=True):
            raise ValueError("Missing Avature public board brand")
        rows = {}
        for card in cards:
            titles = card.select("h3 a[href]")
            if len(titles) != 1:
                raise ValueError("Missing unique Avature listed job title/link")
            url = str(titles[0]["href"])
            identifier = self.details_url(url)
            title = normalized(titles[0].get_text(" ", strip=True))
            context = self.context_fields(card, modern)
            if not title or identifier in rows or (modern and not context.get("Location")):
                raise ValueError("Duplicate or missing Avature job identity/location")
            rows[identifier] = {
                "title": title,
                "url": url,
                "fields": context,
                "template": "modern" if modern else "classic",
            }
        return (
            {
                "title": soup.title.get_text(" ", strip=True),
                "header": headings[0].get_text(" ", strip=True),
                "template": "modern" if modern else "classic",
            },
            int(match[3]),
            rows,
        )

    def parse(self, payload: Any) -> list[JobInput]:
        identifier, listing, brand, body = payload
        soup = self.document(body)
        if self.details_url(listing["url"]) != identifier:
            raise ValueError("Avature native ID mismatch")
        applications = []
        for a in soup.select("a[href]"):
            url = str(a["href"])
            p = urlsplit(url)
            if p.path in (
                urlsplit(self.base).path + "/ApplicationMethods",
                urlsplit(self.base).path + "/RegisterMethod",
            ):
                if (
                    p.scheme != "https"
                    or p.netloc != self.host
                    or parse_qs(p.query) != {"jobId": [identifier]}
                    or p.fragment
                ):
                    raise ValueError("Unscoped Avature native public application control")
                applications.append(url)
        if not applications or len(set(applications)) != 1:
            raise ValueError("Missing unique Avature native public apply entry")
        description_parts = []
        salary = None
        employment = None
        remote = None
        published = None
        raw_fields = {}
        location = listing["fields"].get("Location", "")
        flags = []
        if listing["template"] == "modern":
            heads = soup.select(".banner__text > h2")
            canonical = soup.select('link[rel="canonical"]')
            companies = soup.select("h1")
            if (
                len(heads) != 1
                or normalized(heads[0].get_text(" ", strip=True)) != listing["title"]
                or len(canonical) != 1
                or canonical[0].get("href") != listing["url"]
                or len(companies) != 1
                or companies[0].get_text(" ", strip=True) != brand["header"]
            ):
                raise ValueError("Avature modern public canonical/title/company mismatch")
            company = companies[0].get_text(" ", strip=True)
            for key, selector in [("Location", ".icon-address-white"), ("Team", ".icon-tag-white")]:
                nodes = soup.select(".banner__text " + selector)
                if len(nodes) != 1 or parent_text(nodes[0]) != listing["fields"].get(key):
                    raise ValueError("Avature modern public metadata mismatch")
            articles = soup.select("main article.article--details")
            if not articles or any(
                not a.select(".article__content__view__field") for a in articles
            ):
                raise ValueError("Missing Avature modern full description sections")
            description_parts = [str(a) for a in articles]
        else:
            docs = [
                json.loads(t.get_text()) for t in soup.select('script[type="application/ld+json"]')
            ]
            docs = [d for d in docs if isinstance(d, dict) and d.get("@type") == "JobPosting"]
            paragraphs = soup.select("#main-col article.article--details p.paragraph")
            if len(docs) != 1 or not paragraphs:
                raise ValueError("Missing Avature classic full JobPosting/detail fields")
            row = docs[0]
            company = row["hiringOrganization"]["name"]
            if not isinstance(company, str) or not company.strip():
                raise ValueError("Missing Avature classic public employer")
            original_values = []
            first = True
            for paragraph in paragraphs:
                keys = paragraph.select("span.field--name")
                values = paragraph.select("span.field--value")
                if len(keys) != 1 or len(values) != 1:
                    raise ValueError("Malformed Avature classic full public field")
                key = keys[0].get_text(" ", strip=True)
                value = normalized(values[0].get_text(" ", strip=True))
                if first:
                    if key or value != listing["title"]:
                        raise ValueError("Avature classic listed/full display title mismatch")
                    first = False
                    continue
                if key in {
                    "Team",
                    "Location",
                    "County",
                    "Ref #",
                    "Closing Date",
                    "Salary",
                    "Starting Salary From",
                    "Contract Type",
                    "Employment Type",
                    "Workplace",
                }:
                    if key in raw_fields:
                        raise ValueError("Duplicate Avature classic public metadata")
                    raw_fields[key] = value
                else:
                    description_parts.append(str(paragraph))
                    original_values.append(text(str(values[0])))
            for list_key, detail_key in [
                ("Team", "Team"),
                ("Location", "Location"),
                ("Ref", "Ref #"),
                ("Closing Date", "Closing Date"),
            ]:
                if list_key == "Location" and not listing["fields"].get(list_key):
                    continue
                if (listing["fields"].get(list_key) or None) != (
                    raw_fields.get(detail_key) or None
                ):
                    raise ValueError(
                        f"Avature classic {list_key} mismatch job {identifier}: listed={listing['fields'].get(list_key)!r}, detail={raw_fields.get(detail_key)!r}"
                    )
            if not isinstance(row.get("description"), str) or compact(
                " ".join(original_values)
            ) != compact(text(row["description"])):
                raise ValueError("Avature full native and structured descriptions disagree")
            # Two native visible titles and the scoped Apply ID bind this posting; SEO can
            # retain a substantially different internal title even while its full text agrees.
            if not isinstance(row.get("title"), str) or not row["title"].strip():
                raise ValueError("Missing Avature structured title")
            if row["title"] != listing["title"]:
                flags.append("structured_title_differs")
            location = raw_fields.get("Location") or ""
            if not location:
                places = row.get("jobLocation") or []
                if isinstance(places, dict):
                    places = [places]
                labels = []
                for place in places:
                    address = place.get("address") or {}
                    labels.append(
                        ", ".join(
                            dict.fromkeys(
                                str(address[k]).strip()
                                for k in (
                                    "addressLocality",
                                    "addressRegion",
                                    "postalCode",
                                    "addressCountry",
                                )
                                if address.get(k)
                            )
                        )
                    )
                location = "; ".join(dict.fromkeys(v for v in labels if v))
            if not listing["fields"].get("Location"):
                flags.append("listing_location_missing")
            if not location:
                flags.append("location_missing")
            raw_fields["jobposting"] = row
            salary = row.get("baseSalary") or (
                {"text": raw_fields["Salary"]} if raw_fields.get("Salary") else None
            )
            supplied_salary = raw_fields.get("Starting Salary From") or listing["fields"].get(
                "Starting Salary From"
            )
            if salary is None and supplied_salary:
                salary = {"text": supplied_salary}
            employment = (
                row.get("employmentType")
                or raw_fields.get("Employment Type")
                or raw_fields.get("Contract Type")
            )
            remote = row.get("jobLocationType") or raw_fields.get("Workplace")
            published = row.get("datePosted")
        description_html = "\n".join(description_parts)
        description = text(description_html)
        if not description:
            raise ValueError("Empty Avature full public description")
        return [
            JobInput(
                external_id=identifier,
                title=listing["title"],
                company=company,
                description=description,
                location=location,
                quality_flags=flags,
                source_url=listing["url"],
                application_url=applications[0],
                salary=salary,
                employment_type=employment,
                remote_status=remote,
                published_at=published,
                raw={
                    "listing": listing,
                    "board": brand,
                    "detail_fields": raw_fields,
                    "full_description_html": description_html,
                },
            )
        ]

    def page_url(self, offset: int) -> str:
        return self.base + "/SearchJobs" + (f"/?jobOffset={offset}" if offset else "")

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor < 0 or cursor % 6 or cursor >= 200:
            raise ValueError("Invalid Avature public six-job offset")
        return await self.http.read(self.page_url(cursor))

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)

        async def read(url: str) -> bytes:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        async def roster() -> tuple[dict, dict[str, dict]]:
            brand, total, rows = self.page(await read(self.page_url(0)), 0)
            for offset in range(6, total, 6):
                following_brand, count, following = self.page(
                    await read(self.page_url(offset)), offset
                )
                if following_brand != brand or count != total or set(rows) & set(following):
                    raise ValueError("Avature public pages changed or repeated jobs")
                rows.update(following)
            if len(rows) != total:
                raise ValueError("Incomplete Avature full public roster")
            return brand, rows

        brand, rows = await roster()
        jobs = []
        for identifier, listing in rows.items():
            jobs.extend(self.parse((identifier, listing, brand, await read(listing["url"]))))
        if len({j.company for j in jobs}) != 1:
            raise ValueError("Unsupported mixed-employer Avature native board")
        if await roster() != (brand, rows):
            raise ValueError("Avature full public roster changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

"""JOIN native public first-page SSR state with explicit pagination and mandatory details."""

import asyncio
import json
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.connectors.teamtailor import TENANT
from vindex.schemas import Enumeration, JobInput


def page(body: bytes) -> tuple[BeautifulSoup, dict]:
    if b"</html>" not in body.lower():
        raise ValueError("Truncated JOIN document")
    soup = BeautifulSoup(body, "html.parser")
    scripts = soup.select('script#__NEXT_DATA__[type="application/json"]')
    if len(scripts) != 1:
        raise ValueError("Missing unique JOIN SSR state")
    state = json.loads(scripts[0].get_text())["props"]["pageProps"]["pageData"]
    if not isinstance(state, dict):
        raise ValueError("Invalid JOIN public page data")
    return soup, state


def normalized(value: str) -> str:
    return " ".join(value.split())


class JoinConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider != "join" or not re.fullmatch(TENANT, slug):
            raise ValueError("Invalid JOIN company domain")
        self.slug = slug
        self.origin = "https://join.com"
        self.url = self.origin + "/companies/" + slug
        self.http = PublicHTTP(client, {"join.com"})

    def company(self, state: dict) -> dict:
        company = state["company"]
        if (
            type(company["id"]) is not int
            or company["id"] <= 0
            or company["domain"] != self.slug
            or company["isPublic"] is not True
            or company["inReview"] is not False
            or not isinstance(company["name"], str)
            or not company["name"].strip()
        ):
            raise ValueError("JOIN company identity/public state mismatch")
        return {k: company[k] for k in ("id", "domain", "name", "isPublic", "inReview")}

    def listings(self, body: bytes) -> tuple[dict, dict[str, dict]]:
        soup, state = page(body)
        company = self.company(state)
        jobs = state["jobs"]
        pagination = jobs["pagination"]
        rows = jobs["items"]
        if (
            jobs["filters"] != {}
            or type(pagination["page"]) is not int
            or pagination["page"] != 1
            or type(pagination["pageCount"]) is not int
            or pagination["pageCount"] != 1
            or type(pagination["total"]) is not int
            or not isinstance(rows, list)
            or not 0 < len(rows) == pagination["total"] <= 5
            or type(pagination["perPage"]) is not int
            or pagination["perPage"] != 5
            or type(pagination["pageSize"]) is not int
            or pagination["pageSize"] < len(rows)
        ):
            raise ValueError(
                "JOIN empty, filtered, partial, spontaneous-only or multipage collection"
            )
        if not any(
            normalized(h.get_text(" ", strip=True)) == normalized(company["name"])
            for h in soup.select("h1")
        ):
            raise ValueError("JOIN visible company does not match SSR identity")
        visible = {
            str(a["href"])
            for a in soup.select("a[href]")
            if str(a["href"]).startswith(self.url + "/")
        }
        result = {}
        ids = set()
        for row in rows:
            identifier = row["id"]
            slug = row["idParam"]
            if (
                type(identifier) is not int
                or identifier <= 0
                or identifier in ids
                or not isinstance(slug, str)
                or not re.fullmatch(r"[1-9][0-9]*-[a-z0-9-]+", slug)
                or slug in result
                or not isinstance(row["title"], str)
                or not row["title"].strip()
            ):
                raise ValueError("JOIN invalid or duplicate listed IDs/title")
            ids.add(identifier)
            result[slug] = {
                k: row[k]
                for k in (
                    "id",
                    "idParam",
                    "title",
                    "createdAt",
                    "workplaceType",
                    "city",
                    "employmentType",
                    "country",
                )
            }
        if visible != {self.url + "/" + slug for slug in result}:
            raise ValueError("JOIN full SSR collection and visible native links disagree")
        return company, result

    def parse(self, payload: Any) -> list[JobInput]:
        slug, listing, company, body = payload
        soup, state = page(body)
        job = state["job"]
        url = self.url + "/" + slug
        schemas = [
            json.loads(s.get_text()) for s in soup.select('script[type="application/ld+json"]')
        ]
        schemas = [s for s in schemas if isinstance(s, dict) and s.get("@type") == "JobPosting"]
        if len(schemas) != 1:
            raise ValueError("Missing unique JOIN JobPosting")
        schema = schemas[0]
        canonicals = {str(el.get("href")) for el in soup.select('link[rel="canonical"]')}
        headings = soup.select("h1")
        if (
            self.company({"company": job["company"]}) != company
            or job["companyId"] != company["id"]
            or job["company"]["id"] != company["id"]
            or job["company"]["domain"] != self.slug
            or type(job["id"]) is not int
            or job["id"] != listing["id"]
            or job["idParam"] != slug
            or job["status"] != "ONLINE"
            or job["closedAt"] is not None
            or normalized(job["title"]) != normalized(listing["title"])
            or normalized(schema["title"]) != normalized(listing["title"])
            or schema["hiringOrganization"]["name"] != company["name"]
            or schema["hiringOrganization"]["url"] != self.url
            or schema["url"] != url
            or canonicals != {url}
            or len(headings) != 1
            or normalized(headings[0].get_text(" ", strip=True)) != normalized(listing["title"])
            or schema.get("directApply") is not True
            or not soup.select('button[data-testid="ApplyButton"]')
            or schema["description"] != job["description"]
            or job["workplaceType"] != listing["workplaceType"]
        ):
            raise ValueError("JOIN detail/public state/company/application identity mismatch")
        description = text(schema["description"])
        city = listing["city"] or {}
        places = [
            ", ".join(dict.fromkeys(city[k] for k in ("cityName", "countryName") if city.get(k)))
        ]
        locations = schema.get("jobLocation") or []
        if isinstance(locations, dict):
            locations = [locations]
        for location in locations:
            address = location.get("address") or {}
            places.append(
                ", ".join(
                    dict.fromkeys(
                        address[k]
                        for k in ("addressLocality", "addressRegion", "addressCountry")
                        if address.get(k)
                    )
                )
            )
        flags = [] if description else ["description_missing"]
        salary = schema.get("baseSalary")
        if salary is None and (job.get("salaryAmountFrom") or job.get("salaryAmountTo")):
            salary = {
                k: job.get(k) for k in ("salaryAmountFrom", "salaryAmountTo", "salaryFrequency")
            }
            flags.append("salary_units_unmapped")
        raw_job = {
            k: job.get(k)
            for k in (
                "id",
                "idParam",
                "title",
                "status",
                "closedAt",
                "createdAt",
                "updatedAt",
                "companyId",
                "description",
                "workplaceType",
                "remoteType",
                "remoteRegion",
                "office",
                "hybrid",
                "employmentType",
                "employmentTerms",
                "salaryAmountFrom",
                "salaryAmountTo",
                "salaryFrequency",
            )
        }
        return [
            JobInput(
                external_id=str(job["id"]),
                title=normalized(listing["title"]),
                company=company["name"],
                description=description,
                quality_flags=flags,
                location="; ".join(dict.fromkeys(p for p in places if p)),
                source_url=url,
                application_url=url,
                employment_type=schema.get("employmentType"),
                remote_status=listing["workplaceType"],
                salary=salary,
                published_at=schema.get("datePosted"),
                raw={"listing": listing, "job": raw_job, "jobposting": schema, "company": company},
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("JOIN multi-page collections unsupported")
        return await self.http.read(self.url + "?page=1")

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)

        async def read(url: str) -> bytes:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        company, rows = self.listings(await read(self.url + "?page=1"))
        jobs = []
        for slug, listing in rows.items():
            jobs.extend(self.parse((slug, listing, company, await read(self.url + "/" + slug))))
        if self.listings(await read(self.url + "?page=1")) != (company, rows):
            raise ValueError("JOIN complete public collection changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

"""Anonymous ADP MyJobs requisitions scoped by the public career-site identity."""

import asyncio
import re
from typing import Any
from urllib.parse import urlencode

import httpx
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.schemas import Enumeration, JobInput

HOST = "myjobs.adp.com"
ORIGIN = f"https://{HOST}"
API = f"{ORIGIN}/public/staffing/v1"
COLLECTION = f"{API}/job-requisitions"
SLUG = r"[A-Za-z0-9_-]{1,80}"
PAGE_SIZE = 50
MAX_JOBS = 400


class ADPConnector:
    def __init__(self, slug: str, client: httpx.AsyncClient):
        if not re.fullmatch(SLUG, slug):
            raise ValueError("Invalid ADP MyJobs site")
        self.slug = slug
        self.http = PublicHTTP(client, {HOST})

    async def fetch(
        self, cursor: int = 0, *, organization: str = "", policy: RobotsPolicy | None = None
    ) -> Any:
        url = f"{COLLECTION}?{urlencode({'$top': PAGE_SIZE, '$skip': cursor})}"
        return await self.read(
            url, policy or await RobotsPolicy.load(self.http, ORIGIN), organization
        )

    async def read(self, url: str, policy: RobotsPolicy, organization: str = "") -> Any:
        policy.check(url)
        await asyncio.sleep(policy.delay())
        return await self.http.json(url, headers={"orgoid": organization} if organization else None)

    async def roster(self, policy: RobotsPolicy, organization: str) -> dict[str, str]:
        rows: dict[str, str] = {}
        total = None
        for offset in range(0, MAX_JOBS, PAGE_SIZE):
            page = await self.fetch(offset, organization=organization, policy=policy)
            count = page["count"]
            if type(count) is not int or not 1 <= count <= MAX_JOBS or total not in (None, count):
                raise ValueError("Invalid or changing ADP requisition total")
            total = count
            postings = page["jobRequisitions"]
            if not isinstance(postings, list) or len(postings) != min(PAGE_SIZE, count - offset):
                raise ValueError("Incomplete ADP requisition page")
            for posting in postings:
                identifier, title = posting["reqId"], posting["jobTitle"]
                if (
                    not re.fullmatch(r"[0-9]{1,20}", identifier)
                    or identifier in rows
                    or not text(title)
                    or posting.get("canApply") is not True
                ):
                    raise ValueError("Invalid, unavailable or repeated ADP requisition")
                domains = posting.get("careerSiteDomains")
                if domains and self.slug not in domains:
                    raise ValueError("ADP requisition belongs to another career site")
                rows[identifier] = title
            if len(rows) == total:
                return rows
        raise ValueError("ADP requisition page limit reached")

    def parse(self, payload: tuple[str, str, str, Any]) -> list[JobInput]:
        identifier, title, company, data = payload
        postings = data["jobRequisitions"]
        if not isinstance(postings, list) or len(postings) != 1:
            raise ValueError("Missing or ambiguous ADP detail")
        item = postings[0]
        published_title = text(item.get("publishedJobTitle") or item["jobTitle"])
        if (
            item["reqId"] != identifier
            or not published_title
            or item.get("canApply") is not True
            or (item.get("careerSiteDomains") and self.slug not in item["careerSiteDomains"])
        ):
            raise ValueError(f"ADP detail identity mismatch for {identifier}")
        description = text(item.get("jobDescription") or "")
        if not description:
            raise ValueError(f"Missing ADP description for {identifier}")
        qualifications = text(item.get("jobQualifications") or "")
        locations = []
        places = (
            item.get("postingLocations")
            or item.get("workLocations")
            or item.get("requisitionLocations")
            or []
        )
        for place in places:
            address = place.get("address") or {}
            location = ", ".join(
                value
                for value in (
                    address.get("cityName"),
                    (address.get("countrySubdivisionLevel1") or {}).get("codeValue"),
                    (address.get("country") or {}).get("longName"),
                )
                if value
            )
            if location and location not in locations:
                locations.append(location)
        url = f"{ORIGIN}/{self.slug}/cx/job-details?reqId={identifier}"
        return [
            JobInput(
                external_id=identifier,
                title=published_title,
                company=company,
                description="\n\n".join(filter(None, [description, qualifications])),
                location="; ".join(locations),
                source_url=url,
                application_url=url,
                published_at=item.get("postingDate") or None,
                employment_type=item.get("regularTemp") or None,
                raw={
                    "listing_title": title,
                    "pay_basis": item.get("salaried"),
                    "requisition_id": item.get("clientRequisitionID"),
                },
            )
        ]

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, ORIGIN)
        site_url = f"{API}/career-site/{self.slug}"
        site = await self.read(site_url, policy)
        organization = site.get("orgoid", "")
        company = text(site.get("clientName") or "")
        if (
            site.get("domain") != self.slug
            or site.get("active") is not True
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", organization)
            or not company
        ):
            raise ValueError("Invalid ADP public career-site identity")
        before = await self.roster(policy, organization)
        jobs = []
        for identifier, title in before.items():
            detail = await self.read(f"{COLLECTION}/{identifier}", policy, organization)
            jobs.extend(self.parse((identifier, title, company, detail)))
        if await self.roster(policy, organization) != before:
            raise ValueError("ADP roster changed during refresh")
        return Enumeration(jobs=jobs, complete=True)

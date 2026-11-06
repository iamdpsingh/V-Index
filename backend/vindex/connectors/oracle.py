"""Oracle Recruiting public Candidate Experience sites and advertised anonymous APIs."""

import asyncio
import json
import re
from datetime import datetime
from typing import Any

import httpx
from bs4 import BeautifulSoup
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.schemas import Enumeration, JobInput

HOST = r"[a-z0-9-]+\.fa\.(?:us[0-9]|em[0-9]|ap[0-9]|ca[0-9]|ocs)\.oraclecloud\.com"
SITE = r"[A-Za-z0-9_-]{1,80}"
IDENTIFIER = r"[A-Za-z0-9_-]{1,100}"
SECTIONS = (
    "ExternalDescriptionStr",
    "ExternalResponsibilitiesStr",
    "ExternalQualificationsStr",
    "CorporateDescriptionStr",
    "OrganizationDescriptionStr",
)
PUBLIC_DETAIL = (
    "Id",
    "Title",
    "Category",
    "RequisitionType",
    "JobGrade",
    "RequisitionId",
    "ExternalPostedStartDate",
    "ExternalPostedEndDate",
    "JobLevel",
    "JobSchedule",
    "JobShift",
    "StudyLevel",
    "ContractType",
    "ContentLocale",
    "PrimaryLocation",
    "PrimaryLocationCountry",
    "ApplyWhenNotPostedFlag",
    "JobFunctionCode",
    "WorkplaceTypeCode",
    "WorkplaceType",
    "NumberOfOpenings",
    "WorkerType",
    "JobType",
    "WorkMonths",
    "WorkYears",
    "WorkHours",
    "WorkDays",
    "LegalEmployer",
    "BusinessUnit",
    "Department",
    "DomesticTravelRequired",
    "InternationalTravelRequired",
    "JobFunction",
    "secondaryLocations",
    "workLocation",
    "otherWorkLocations",
    "requisitionFlexFields",
    "skills",
    *SECTIONS,
)
SITE_FIELDS = (
    "SiteName",
    "SiteNumber",
    "SiteURLName",
    "StatusCode",
    "SeoOrganizationName",
    "SeoOrganizationSameAs",
)


class OracleConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        parts = slug.split("~")
        if (
            provider != "oracle"
            or len(parts) != 2
            or not re.fullmatch(HOST, parts[0])
            or not re.fullmatch(SITE, parts[1])
            or not company.strip()
        ):
            raise ValueError("Invalid Oracle public Candidate Experience source")
        self.host, self.site = parts
        self.company = company
        self.origin = "https://" + self.host
        self.base = self.origin + "/hcmUI/CandidateExperience/en/sites/" + self.site
        self.api = self.origin + "/hcmRestApi/resources/11.13.18.05/"
        self.http = PublicHTTP(client, {self.host})

    def url(self, resource: str, params: dict[str, str]) -> str:
        return self.api + resource + "?" + str(httpx.QueryParams(params))

    def site_info(self, data: Any) -> dict:
        if (
            not isinstance(data, dict)
            or not isinstance(data.get("items"), list)
            or data.get("hasMore") is not False
            or data.get("count") != len(data["items"])
        ):
            raise ValueError("Incomplete Oracle public site metadata")
        sites = [
            r
            for r in data["items"]
            if isinstance(r, dict) and self.site in (r.get("SiteNumber"), r.get("SiteURLName"))
        ]
        if len(sites) != 1 or sites[0].get("StatusCode") != "ORA_ACTIVE":
            raise ValueError("Oracle public site is ambiguous or inactive")
        row = sites[0]
        if (
            not isinstance(row.get("SiteName"), str)
            or not row["SiteName"].strip()
            or not re.fullmatch(SITE, row.get("SiteNumber", ""))
        ):
            raise ValueError("Invalid Oracle public site identity")
        return {k: row.get(k) for k in SITE_FIELDS}

    def page(self, data: Any, offset: int) -> tuple[int, list[dict]]:
        if (
            not isinstance(data, dict)
            or data.get("hasMore") is not False
            or data.get("count") != 1
            or not isinstance(data.get("items"), list)
            or len(data["items"]) != 1
        ):
            raise ValueError("Invalid Oracle public search wrapper")
        row = data["items"][0]
        total = row.get("TotalJobsCount")
        if (
            type(total) is not int
            or not 0 < total <= 400
            or row.get("SiteNumber") != self.site
            or row.get("Offset") != offset
            or row.get("Limit") != 100
            or row.get("Keyword") not in (None, "")
        ):
            raise ValueError("Incomplete, filtered or oversized Oracle public search")
        for key, value in row.items():
            if key.startswith("Selected") and value not in (None, ""):
                raise ValueError("Unexpected Oracle active search facet")
        rows = row.get("requisitionList")
        if not isinstance(rows, list) or len(rows) != min(100, total - offset):
            raise ValueError("Oracle public search page count mismatch")
        for job in rows:
            if (
                not isinstance(job, dict)
                or not re.fullmatch(IDENTIFIER, str(job.get("Id", "")))
                or not isinstance(job.get("Title"), str)
                or not job["Title"].strip()
            ):
                raise ValueError("Invalid Oracle public job identity")
        return total, rows

    def parse(self, payload: Any) -> list[JobInput]:
        listing, site, data = payload
        if (
            not isinstance(data, dict)
            or data.get("hasMore") is not False
            or data.get("count") != 1
            or len(data.get("items", [])) != 1
        ):
            raise ValueError("Missing mandatory Oracle public job detail")
        original = data["items"][0]
        row = {k: original.get(k) for k in PUBLIC_DETAIL}
        for key in (
            "Id",
            "Title",
            "PrimaryLocation",
            "PrimaryLocationCountry",
            "WorkplaceType",
            "WorkplaceTypeCode",
            "JobSchedule",
            "JobType",
            "ContractType",
            "WorkerType",
        ):
            if listing.get(key) is not None and row.get(key) != listing[key]:
                raise ValueError("Oracle public listed/detail metadata mismatch: " + key)
        if (
            not isinstance(row["ExternalPostedStartDate"], str)
            or row["ExternalPostedStartDate"][:10] != listing["PostedDate"]
        ):
            raise ValueError("Oracle public posting date mismatch")
        sections = []
        for key in SECTIONS:
            value = row[key]
            if value is not None and not isinstance(value, str):
                raise ValueError("Malformed Oracle public full description")
            if value:
                sections.append(text(value))
        description = "\n\n".join(sections)
        locations = [row["PrimaryLocation"]] if row["PrimaryLocation"] else []
        secondary = row["secondaryLocations"]
        if not isinstance(secondary, list):
            raise ValueError("Oracle secondary locations not expanded")
        for location in secondary:
            if not isinstance(location.get("Name"), str) or not location["Name"].strip():
                raise ValueError("Malformed Oracle secondary location")
            locations.append(location["Name"])
        native_company = site.get("SeoOrganizationName")
        if native_company is not None and (
            not isinstance(native_company, str) or not native_company.strip()
        ):
            raise ValueError("Malformed Oracle public employer identity")
        # Many native sites deliberately omit SEO organization names, as the original APIs do.
        # Keep the operator's supplied employer explicit rather than guessing from prose/domain.
        flags = [] if native_company else ["company_from_source_configuration"]
        if not description:
            flags.append("description_missing")
        url = self.base + "/job/" + str(row["Id"])
        return [
            JobInput(
                external_id=str(row["Id"]),
                title=row["Title"],
                company=native_company or self.company,
                description=description,
                location="; ".join(dict.fromkeys(locations)),
                source_url=url,
                application_url=url,
                quality_flags=flags,
                employment_type=row["JobSchedule"] or row["JobType"] or row["ContractType"],
                remote_status=row["WorkplaceType"],
                published_at=datetime.fromisoformat(row["ExternalPostedStartDate"]),
                raw={
                    "listing": listing,
                    "site": site,
                    "detail": row,
                    "employer_identity_source": "native_seo"
                    if native_company
                    else "source_configuration",
                },
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor < 0 or cursor % 100 or cursor >= 400:
            raise ValueError("Invalid Oracle public search offset")
        return await self.http.json(self.search_url(cursor))

    def search_url(self, offset: int) -> str:
        return self.url(
            "recruitingCEJobRequisitions",
            {
                "onlyData": "true",
                "expand": "requisitionList",
                "finder": f"findReqs;siteNumber={self.site},limit=100,offset={offset}",
            },
        )

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)

        async def read(url: str) -> bytes:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        body = await read(self.base + "/jobs")
        if b"</html>" not in body.lower():
            raise ValueError("Truncated Oracle public site shell")
        soup = BeautifulSoup(body, "html.parser")
        if not any(
            str(t.get("src", "")).startswith("https://static.oracle.com/cdn/fa/oj-hcm-ce/")
            for t in soup.select("script[src]")
        ):
            raise ValueError("Unsupported Oracle Candidate Experience shell")
        site_url = self.url("recruitingCESites", {"onlyData": "true"})
        site = self.site_info(json.loads(await read(site_url)))

        async def roster() -> dict[str, dict]:
            total, first = self.page(json.loads(await read(self.search_url(0))), 0)
            rows = list(first)
            for offset in range(100, total, 100):
                count, page = self.page(json.loads(await read(self.search_url(offset))), offset)
                if count != total:
                    raise ValueError("Oracle public total changed between pages")
                rows.extend(page)
            result = {str(r["Id"]): r for r in rows}
            if len(result) != total:
                raise ValueError("Duplicate/incomplete Oracle public job IDs")
            return result

        rows = await roster()
        jobs = []
        for identifier, listing in rows.items():
            url = self.url(
                "recruitingCEJobRequisitionDetails",
                {
                    "expand": "all",
                    "onlyData": "true",
                    "finder": f'ById;Id="{identifier}",siteNumber={self.site}',
                },
            )
            jobs.extend(self.parse((listing, site, json.loads(await read(url)))))
        if await roster() != rows or self.site_info(json.loads(await read(site_url))) != site:
            raise ValueError("Oracle complete public board changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

"""Observed public ApplicantPro / iSolvedHire core jobs component and JSON-LD."""

import asyncio
import json
import re
from typing import Any
from urllib.parse import urlencode, urlsplit

import httpx
from bs4 import BeautifulSoup
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.connectors.teamtailor import TENANT
from vindex.schemas import Enumeration, JobInput

DOMAINS = {"applicantpro": "applicantpro.com", "isolvedhire": "isolvedhire.com"}


class ApplicantProConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider not in DOMAINS or not re.fullmatch(TENANT, slug):
            raise ValueError("Invalid ApplicantPro/iSolvedHire hosted board")
        self.slug = slug
        self.suffix = DOMAINS[provider]
        self.host = f"{slug}.{self.suffix}"
        self.origin = "https://" + self.host
        self.http = PublicHTTP(client, {self.host})

    def board_info(self, body: bytes) -> tuple[int, int, str]:
        if b"</html>" not in body.lower():
            raise ValueError("Truncated career board")
        soup = BeautifulSoup(body, "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else ""
        match = re.fullmatch(r"Job Listings - (.+) Jobs", title)
        scripts = "\n".join(x.get_text() for x in soup.select("script:not([src])"))
        ids = re.findall(
            r"organizationId\s*:\s*([1-9][0-9]*),\s*domainId\s*:\s*([1-9][0-9]*)", scripts
        )
        # Multiple components can repeat the same board IDs; never accept conflicting identities.
        distinct = {(int(a), int(b)) for a, b in ids}
        if (
            not match
            or len(distinct) != 1
            or "'JobListings'" not in scripts
            or not re.search(r'domainName\s*:\s*"' + re.escape(self.suffix) + '"', scripts)
            or not re.search(r'subdomainName\s*:\s*"' + re.escape(self.slug) + '"', scripts)
        ):
            raise ValueError("Career board/component identity missing or inconsistent")
        organization, domain = distinct.pop()
        return organization, domain, match[1]

    def collection_url(self, domain: int) -> str:
        return f"{self.origin}/core/jobs/{domain}?" + urlencode({"getParams": '{"isInternal":0}'})

    def listings(self, payload: Any, domain: int) -> dict[int, dict]:
        if payload["success"] is not True:
            raise ValueError("Career collection reported failure")
        data = payload["data"]
        rows = data["jobs"]
        total = data["jobCount"]
        if (
            type(total) is not int
            or not isinstance(rows, list)
            or not 0 < total <= 400
            or len(rows) != total
            or any(data.get(k) for k in ("next", "next_page", "pagination"))
        ):
            raise ValueError("Career collection empty, partial, paginated or over 400-detail limit")
        result = {}
        for row in rows:
            identifier = row["id"]
            if (
                type(identifier) is not int
                or identifier <= 0
                or identifier in result
                or row["subdomain"] != self.slug
                or row["domainName"] != self.suffix
                or type(row["siteId"]) is not int
                or row["siteId"] != domain
                or row["jobUrl"] != f"{self.origin}/jobs/{identifier}"
                or not isinstance(row["title"], str)
                or not row["title"].strip()
            ):
                raise ValueError("Career listing identity/host/site mismatch")
            result[identifier] = row
        return result

    def parse(self, payload: Any) -> list[JobInput]:
        listing, info, body, detail = payload
        identifier = listing["id"]
        url = listing["jobUrl"]
        if b"</html>" not in body.lower():
            raise ValueError("Truncated career job detail")
        if detail["success"] is not True:
            raise ValueError("Public career detail request reported failure")
        data = detail["data"]
        if (
            type(data["id"]) is not int
            or data["id"] != identifier
            or type(data["siteId"]) is not int
            or data["siteId"] != info[1]
            or data["title"] != listing["title"]
            or not isinstance(data["description"], str)
            or data.get("jobDescriptionFile")
        ):
            raise ValueError(
                "Public career detail ID/site/title mismatch or unsupported attachment"
            )
        soup = BeautifulSoup(body, "html.parser")
        schemas = [
            json.loads(s.get_text()) for s in soup.select('script[type="application/ld+json"]')
        ]
        schemas = [s for s in schemas if isinstance(s, dict) and s.get("@type") == "JobPosting"]
        if len(schemas) > 1:
            raise ValueError("Ambiguous career JobPosting documents")
        row = schemas[0] if schemas else None
        canonical = soup.select_one('link[rel="canonical"]')
        scripts = "\n".join(s.get_text() for s in soup.select("script:not([src])"))
        jobs = set(re.findall(r"jobListingId\s*:\s*([1-9][0-9]*)", scripts))
        ids = {
            (int(a), int(b))
            for a, b in re.findall(
                r"organizationId\s*:\s*([1-9][0-9]*),\s*domainId\s*:\s*([1-9][0-9]*)", scripts
            )
        }
        if (
            canonical is None
            or jobs != {str(identifier)}
            or ids != {(info[0], info[1])}
            or "'JobDetail'" not in scripts
            or "'InlineAuth'" not in scripts
        ):
            raise ValueError("Career detail job/board/application identity mismatch")
        if row is not None:
            if (
                row["title"] != listing["title"]
                or row["identifier"]["sameAs"] != str(identifier)
                or row["url"] not in (url, url + ".html")
            ):
                raise ValueError("Career JobPosting identity mismatch")
            # A present but malformed description must not silently become a missing schema.
            text(row["description"])
        else:
            page_title = soup.title.get_text(strip=True) if soup.title else ""
            if not page_title.startswith(listing["title"] + " - ") or not page_title.endswith(
                info[2] + " Jobs"
            ):
                raise ValueError("Career HTML fallback title/employer identity mismatch")
        p = urlsplit(str(canonical.get("href", "")))
        prefix = f"/openings/{self.slug}/jobs/{identifier}"
        native = p.netloc == self.host and p.path in (
            f"/jobs/{identifier}",
            f"/jobs/{identifier}.html",
        )
        shared = p.netloc == "www." + self.suffix and (
            p.path == prefix or p.path.startswith(prefix + "/")
        )
        if p.scheme != "https" or p.query or p.fragment or not (native or shared):
            raise ValueError("Career canonical URL does not match fixed provider/tenant/job")
        salary = row.get("baseSalary") if row else None
        if salary:
            amount = salary.get("value")
            if isinstance(amount, dict):
                if not any(
                    amount.get(k) not in (None, "") for k in ("value", "minValue", "maxValue")
                ):
                    salary = None
            elif amount in (None, ""):
                salary = None
        if row is None:
            supplied = {
                k: listing.get(k)
                for k in ("minSalary", "maxSalary", "payRate", "payTypeFrame", "payDetails")
            }
            if any(
                supplied.get(k) not in (None, "")
                for k in ("minSalary", "maxSalary", "payRate", "payDetails")
            ):
                salary = supplied
        description = text(data["description"])
        if data.get("benefits"):
            description += "\n\nBenefits\n" + text(data["benefits"])
        flags = [] if row else ["jobposting_schema_missing"]
        if not description:
            flags.append("description_missing")
        return [
            JobInput(
                external_id=str(identifier),
                title=listing["title"],
                company=row["hiringOrganization"]["name"] if row else info[2],
                description=description,
                quality_flags=flags,
                location=listing["jobLocation"] or "",
                source_url=url,
                application_url=url,
                salary=salary,
                employment_type=listing["employmentType"]
                or (row.get("employmentType") if row else None),
                remote_status=listing["workplaceType"]
                or (row.get("jobLocationType") if row else None),
                published_at=row.get("datePosted") if row else None,
                raw={
                    "listing": listing,
                    "jobposting": row,
                    "public_job_detail": {
                        k: v
                        for k, v in data.items()
                        if k
                        in {
                            "id",
                            "siteId",
                            "title",
                            "description",
                            "benefits",
                            "advertisingDescription",
                            "advertisingDescriptionHtml",
                            "startDateRef",
                            "endDateRef",
                            "hideFromIndeed",
                            "untilFilled",
                            "payDetails",
                        }
                    },
                    "canonical_url": str(canonical["href"]),
                    "board": {"organization_id": info[0], "domain_id": info[1], "title": info[2]},
                    "application_entry": "native_inline_auth",
                },
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("Career component pagination unsupported")
        return await self.http.read(self.origin + "/jobs/")

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)

        async def read(url: str, json: bool = False) -> Any:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.json(url) if json else await self.http.read(url)

        board_url = self.origin + "/jobs/"
        info = self.board_info(await read(board_url))
        collection = self.collection_url(info[1])
        rows = self.listings(await read(collection, True), info[1])
        jobs = []
        for row in rows.values():
            body = await read(row["jobUrl"])
            detail = await read(f"{self.origin}/core/jobs/{info[1]}/{row['id']}/job-details", True)
            jobs.extend(self.parse((row, info, body, detail)))
        if (
            self.board_info(await read(board_url)) != info
            or self.listings(await read(collection, True), info[1]) != rows
        ):
            raise ValueError("Complete career collection changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

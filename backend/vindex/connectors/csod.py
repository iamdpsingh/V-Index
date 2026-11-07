"""CSOD public career-site anonymous browser search, details and full native advertisements."""

import asyncio
import json
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
from bs4 import BeautifulSoup
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.connectors.teamtailor import TENANT
from vindex.schemas import Enumeration, JobInput


class CSODConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        parts = slug.split("~")
        if (
            provider != "csod"
            or len(parts) != 2
            or not re.fullmatch(TENANT, parts[0])
            or not re.fullmatch(r"[1-9][0-9]{0,5}", parts[1])
            or not company.strip()
        ):
            raise ValueError("Invalid CSOD public career-site source")
        self.tenant, site = parts
        self.site = int(site)
        self.company = company
        self.origin = f"https://{self.tenant}.csod.com"
        self.base = self.origin + f"/ux/ats/careersite/{site}/home"
        self.http = PublicHTTP(client, {self.tenant + ".csod.com"})

    def context(self, body: bytes) -> dict:
        if b"</html>" not in body.lower():
            raise ValueError("Truncated CSOD public shell")
        soup = BeautifulSoup(body, "html.parser")
        contexts = []
        for script in soup.select("script:not([src])"):
            value = script.get_text()
            match = re.search(
                r"if\(!csod\.context\s*\|\|\s*!csod\.context\.token\)\s*csod\.context\s*=\s*", value
            )
            if match:
                data, end = json.JSONDecoder().raw_decode(value[match.end() :])
                if value[match.end() + end :].strip() not in ("", ";"):
                    raise ValueError("Unsupported CSOD context assignment")
                contexts.append(data)
        if len(contexts) != 1:
            raise ValueError("Missing unique CSOD public anonymous context")
        row = contexts[0]
        if (
            row.get("corp") != self.tenant
            or (type(row.get("user")) is not int or row["user"] >= 0)
            or row.get("serviceBase") != "/"
            or row.get("applicationBase") != "/"
            or row.get("cultureName") not in {"en-GB", "en-US", "en-AU"}
            or type(row.get("cultureID")) is not int
            or not isinstance(row.get("token"), str)
            or not row["token"]
        ):
            raise ValueError("Unsupported or nonanonymous CSOD context")
        # Token is request-scoped memory only; no tracking, endpoint, candidate or account data retained.
        return {k: row[k] for k in ("corp", "user", "cultureName", "cultureID", "token")}

    def data(self, payload: Any) -> Any:
        if (
            not isinstance(payload, dict)
            or type(payload.get("status")) is not int
            or payload["status"] not in (0, 200)
            or "data" not in payload
        ):
            raise ValueError("Invalid CSOD public service response")
        return payload["data"]

    def config(self, payload: Any, ctx: dict) -> dict:
        row = self.data(payload)
        if (
            not isinstance(row, dict)
            or row.get("id") != self.site
            or row.get("active") is not True
            or row.get("anonymousUserId") != ctx["user"]
            or row.get("currentLanguage", {}).get("cultureId") != ctx["cultureID"]
            or row["currentLanguage"].get("cultureName") != ctx["cultureName"]
        ):
            raise ValueError("Inactive, nonanonymous or mismatched CSOD public career site")
        return {
            "id": row["id"],
            "active": True,
            "currentLanguage": row["currentLanguage"],
            "company_source": "source_configuration",
        }

    def search_body(self, ctx: dict, page: int) -> dict:
        return {
            "careerSiteId": self.site,
            "careerSitePageId": self.site,
            "pageNumber": page,
            "pageSize": 25,
            "cultureId": ctx["cultureID"],
            "cultureName": ctx["cultureName"],
            "searchText": "",
            "states": [],
            "countryCodes": [],
            "cities": [],
            "placeID": "",
            "radius": None,
            "postingsWithinDays": None,
            "customFieldCheckboxKeys": [],
            "customFieldDropdowns": [],
            "customFieldRadios": [],
        }

    def page(self, payload: Any, page: int) -> tuple[int, list[dict]]:
        data = self.data(payload)
        total = data.get("totalCount")
        rows = data.get("requisitions")
        if (
            type(total) is not int
            or not 0 < total <= 200
            or not isinstance(rows, list)
            or len(rows) != min(25, total - (page - 1) * 25)
        ):
            raise ValueError("Incomplete, empty or oversized CSOD public page")
        for row in rows:
            if (
                not isinstance(row, dict)
                or type(row.get("requisitionId")) is not int
                or row["requisitionId"] <= 0
                or not isinstance(row.get("displayJobTitle"), str)
                or not row["displayJobTitle"].strip()
                or not isinstance(row.get("locations"), list)
            ):
                raise ValueError("Invalid CSOD public listed identity")
        return total, rows

    def parse(self, payload: Any) -> list[JobInput]:
        listing, config, detail_payload, ad_payload = payload
        original = self.data(detail_payload)
        row = {
            k: original.get(k)
            for k in (
                "displayTitle",
                "externalDescription",
                "ref",
                "requisitionStatusId",
                "allowApply",
                "primaryLocation",
                "additionalLocations",
                "openDate",
                "companyApplyUrl",
            )
        }
        identifier = listing["requisitionId"]
        url = self.base + f"/requisition/{identifier}?c={self.tenant}"
        advertised = urlsplit(row["companyApplyUrl"] or "")
        if (
            row["displayTitle"] != listing["displayJobTitle"]
            or row["ref"] != f"req{identifier}"
            or row["allowApply"] is not True
            or advertised.scheme != "https"
            or advertised.netloc != self.tenant + ".csod.com"
            or not re.fullmatch(
                rf"/ux/ats/careersite/[1-9][0-9]{{0,5}}/home/requisition/{identifier}",
                advertised.path,
            )
            or parse_qs(advertised.query) != {"c": [self.tenant]}
            or advertised.fragment
        ):
            raise ValueError("CSOD listed/detail/public application identity mismatch")
        data = self.data(ad_payload)
        if (
            not isinstance(data, list)
            or len(data) != 1
            or not isinstance(data[0].get("items"), list)
            or len(data[0]["items"]) != 1
        ):
            raise ValueError("Missing full CSOD public advertisement")
        fields = data[0]["items"][0]["fields"]
        if (
            fields.get("id") != identifier
            or fields.get("reqId") != row["ref"]
            or fields.get("title") != row["displayTitle"]
            or not isinstance(fields.get("ad"), str)
        ):
            raise ValueError("CSOD full advertisement ID/title mismatch")
        description = text(fields["ad"])
        if not description:
            raise ValueError("Empty CSOD full public advertisement")
        places = [row["primaryLocation"], *(row["additionalLocations"] or [])]
        if not isinstance(row["additionalLocations"], list) or any(
            not isinstance(p, dict) for p in places
        ):
            raise ValueError("Malformed CSOD public locations")
        for listed in listing["locations"]:
            if not isinstance(listed, dict) or not any(
                all(
                    not listed.get(k) or listed[k] == place.get(k)
                    for k in ("city", "state", "country")
                )
                for place in places
            ):
                raise ValueError("CSOD listed/detail public locations disagree")
        locations = []
        for place in places:
            label = ", ".join(
                dict.fromkeys(
                    str(place[k]).strip()
                    for k in ("locationDisplayTitle", "title", "city", "state", "country")
                    if place.get(k)
                )
            )
            if not label:
                raise ValueError("Missing CSOD public location")
            locations.append(label)
        supplied = listing.get("postingEffectiveDate")
        published = None
        if supplied:
            pattern = (
                "%m/%d/%Y" if config["currentLanguage"]["cultureName"] == "en-US" else "%d/%m/%Y"
            )
            published = datetime.strptime(supplied, pattern).replace(tzinfo=UTC)
        return [
            JobInput(
                external_id=str(identifier),
                title=row["displayTitle"],
                company=self.company,
                description=description,
                location="; ".join(dict.fromkeys(locations)),
                source_url=url,
                application_url=row["companyApplyUrl"],
                published_at=published,
                quality_flags=["company_from_source_configuration"],
                raw={
                    "listing": listing,
                    "site": config,
                    "detail": row,
                    "advertisement": {
                        k: fields.get(k)
                        for k in ("id", "reqId", "title", "location", "ad", "description")
                    },
                    "posting_effective_date_original": supplied,
                },
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("CSOD fetch requires full public session enumeration")
        return await self.http.read(self.base + "?c=" + self.tenant)

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)

        async def read(url: str, *, body: dict | None = None, token: str | None = None) -> bytes:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(
                url,
                method="POST" if body is not None else "GET",
                json_body=body,
                headers={"Authorization": "Bearer " + token} if token else None,
            )

        ctx = self.context(await read(self.base + "?c=" + self.tenant))
        config_url = (
            self.origin
            + f"/services/x/career-site/v1/careersites/{self.site}?cultureId={ctx['cultureID']}"
        )
        config = self.config(json.loads(await read(config_url, token=ctx["token"])), ctx)

        async def roster() -> dict[int, dict]:
            url = self.origin + "/services/x/career-site/v1/search"
            total, rows = self.page(
                json.loads(await read(url, body=self.search_body(ctx, 1), token=ctx["token"])), 1
            )
            rows = list(rows)
            for page in range(2, (total + 24) // 25 + 1):
                count, following = self.page(
                    json.loads(
                        await read(url, body=self.search_body(ctx, page), token=ctx["token"])
                    ),
                    page,
                )
                if count != total:
                    raise ValueError("CSOD public total changed between pages")
                rows.extend(following)
            result = {r["requisitionId"]: r for r in rows}
            if len(result) != total:
                raise ValueError("Duplicate/incomplete CSOD public IDs")
            return result

        rows = await roster()
        jobs = []
        for identifier, listing in rows.items():
            detail_url = (
                self.origin
                + f"/services/x/job-requisition/v2/requisitions/{identifier}/jobDetails?cultureId={ctx['cultureID']}"
            )
            ad_url = (
                self.origin
                + f"/Services/API/ATS/CareerSite/{self.site}/JobRequisitions/{identifier}?useMobileAd=false&cultureId={ctx['cultureID']}"
            )
            detail = json.loads(await read(detail_url, token=ctx["token"]))
            ad = json.loads(await read(ad_url, token=ctx["token"]))
            jobs.extend(self.parse((listing, config, detail, ad)))
        if (
            await roster() != rows
            or self.config(json.loads(await read(config_url, token=ctx["token"])), ctx) != config
        ):
            raise ValueError("CSOD full public board changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

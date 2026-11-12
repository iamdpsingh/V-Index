"""Anonymous BrassRing portals whose native result totals fit in one page."""

import asyncio
import json
import re
from typing import Any

import httpx
from vindex.connectors.http import PublicHTTP
from vindex.connectors.jobboardio import document
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.schemas import Enumeration, JobInput

HOST = "sjobs.brassring.com"
PORTALS = {"25749-5764": "Halifax Regional Municipality", "25633-5440": "Infosys"}
PATH = "/TGnewUI/Search/Home/HomeWithPreLoad"


def preload(body: bytes) -> dict[str, Any]:
    nodes = document(body).select("input#preLoadJSON[value]")
    if len(nodes) != 1:
        raise ValueError("Missing BrassRing public posting payload")
    data = json.loads(str(nodes[0]["value"]))
    if (
        not isinstance(data, dict)
        or data.get("LoggedIn") is not False
        or data.get("ShowCaptcha") is not False
        or data.get("SolarErrorOccurred") is not False
    ):
        raise ValueError("Unexpected BrassRing public portal state")
    return data


class BrassRingConnector:
    def __init__(self, slug: str, client: httpx.AsyncClient):
        if slug not in PORTALS:
            raise ValueError("Unreviewed BrassRing portal")
        self.partner, self.site = slug.split("-")
        self.company = PORTALS[slug]
        self.origin = f"https://{HOST}"
        self.http = PublicHTTP(client, {HOST})

    def url(self, identifier: str | None = None) -> str:
        page = "searchResults" if identifier is None else f"JobDetails&jobid={identifier}"
        path = PATH if identifier is not None else PATH.replace("/Home/", "/home/")
        return f"{self.origin}{path}?partnerid={self.partner}&siteid={self.site}&PageType={page}"

    def roster(self, body: bytes) -> dict[str, str]:
        response = preload(body)["searchResultsResponse"]
        rows = response["Jobs"]["Job"]
        total = response["JobsCount"]
        if type(total) is not int or not isinstance(rows, list) or not 0 < total == len(rows) <= 50:
            raise ValueError("BrassRing search page does not contain the entire advertised roster")
        result: dict[str, str] = {}
        for row in rows:
            fields = {q["QuestionName"]: q["Value"] for q in row["Questions"] if "Value" in q}
            identifier = str(fields.get("reqid", ""))
            title = text(str(fields.get("jobtitle") or ""))
            if (
                str(fields.get("clientid")) != self.partner
                or str(fields.get("siteid")) != self.site
                or not re.fullmatch(r"[1-9][0-9]{0,17}", identifier)
                or identifier in result
                or not title
            ):
                raise ValueError("Invalid or duplicate BrassRing roster entry")
            result[identifier] = title
        return result

    def parse(self, payload: Any) -> list[JobInput]:
        identifier, title, body = payload
        data = preload(body)
        detail = data["Jobdetails"]
        fields = {
            q["VerityZone"]: text(str(q.get("AnswerValue") or ""))
            for q in detail["JobDetailQuestions"]
        }
        native_title = text(str(detail.get("Title") or ""))
        if (
            str(data.get("JobId")) != identifier
            or fields.get("reqid") != identifier
            or str(detail.get("JobSiteId")) != self.site
            or fields.get("siteid") != self.site
            or detail.get("isActive") is not True
            or " ".join(native_title.split()) != " ".join(title.split())
            or not fields.get("jobdescription")
        ):
            raise ValueError("BrassRing detail does not match the active roster")
        description = fields["jobdescription"]
        location = ", ".join(
            dict.fromkeys(
                fields[k] for k in ("formtext2", "formtext1", "formtext11") if fields.get(k)
            )
        )
        if self.partner == "25749":
            match = re.search(
                r"\bWORK LOCATION:\s*(.{1,200}?)(?=\s+[A-Z][A-Z /-]{3,}:)", description
            )
            if match:
                location = match[1].strip()
        url = self.url(identifier)
        return [
            JobInput(
                external_id=identifier,
                title=native_title,
                company=fields.get("formtext5") or self.company,
                description=description,
                location=location,
                source_url=url,
                application_url=url,
                quality_flags=["publication_date_missing"]
                + ([] if location else ["location_missing"]),
                raw={
                    "last_updated_original": fields.get("lastupdated"),
                    "requisition_reference": fields.get("autoreq"),
                },
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("Unsupported BrassRing cursor")
        return await self.http.read(self.url())

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)

        async def read(url: str) -> bytes:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        before = self.roster(await read(self.url()))
        jobs = []
        for identifier, title in before.items():
            jobs.extend(self.parse((identifier, title, await read(self.url(identifier)))))
        if before != self.roster(await read(self.url())):
            raise ValueError("BrassRing roster changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

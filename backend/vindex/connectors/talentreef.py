"""Published external TalentReef postings through the public career app's gateway."""

import asyncio
import re
from copy import deepcopy
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.schemas import Enumeration, JobInput

ORIGIN = "https://apply.jobappnetwork.com"
# Advertised by the production career app, resolved to public IPs during review.
# No private network, development host, account API, or alternate index is used.
GATEWAY = "https://prod-kong.internal.talentreef.com"
ALIASES = frozenset({"jcresortsjobs", "otbsdjobs"})
SEARCH = GATEWAY + "/apply/proxy-es/search-en-us/posting/_search"
FIELDS = [
    "positionType",
    "description",
    "address",
    "jobId",
    "clientId",
    "clientName",
    "brand",
    "location",
    "internalOrExternal",
    "url",
    "extUuid",
    "isSalaried",
    "minCompensation",
    "maxCompensation",
    "pubCompensation",
    "createdDate",
    "endDate",
    "contractType",
]
PAGE_SIZE = 50
MAX_JOBS = 2_000


class TalentReefConnector:
    def __init__(self, alias: str, client: httpx.AsyncClient):
        if alias not in ALIASES:
            raise ValueError("Unknown TalentReef career site")
        self.alias = alias
        self.http = PublicHTTP(
            client, {"apply.jobappnetwork.com", "prod-kong.internal.talentreef.com"}
        )

    async def read_json(self, url: str, policy: RobotsPolicy, body: dict | None = None) -> Any:
        policy.check(url)
        await asyncio.sleep(policy.delay())
        return await self.http.json(
            url, method="POST" if body is not None else "GET", json_body=body
        )

    async def template(self, policy: RobotsPolicy) -> dict:
        payload = await self.read_json(GATEWAY + "/apply/careerPages/alias/" + self.alias, policy)
        if not isinstance(payload, list):
            raise ValueError("Missing TalentReef published career configuration")
        rows = [row for row in payload if isinstance(row, dict) and row.get("locale") == "en"]
        if len(rows) != 1:
            raise ValueError("Missing or ambiguous TalentReef English career site")
        row = rows[0]
        clients = row.get("clients")
        if (
            row.get("published") is not True
            or row.get("availability") != "EXTERNAL"
            or not re.fullmatch(r"[1-9][0-9]{0,12}", str(row.get("clientId", "")))
            or not isinstance(clients, list)
            or len(clients) != 1
            or not isinstance(clients[0], dict)
            or str(clients[0].get("legacyClientId")) != str(row["clientId"])
            or not isinstance(clients[0].get("clientName"), str)
            or not clients[0]["clientName"].strip()
            or any(row.get(key) for key in ("brands", "brandIds", "locationIds", "jobCategories"))
        ):
            raise ValueError("Unsupported filtered, internal or unpublished TalentReef career site")
        return {"client_id": str(row["clientId"]), "client_name": clients[0]["clientName"]}

    def request_body(self, template: dict, offset: int) -> dict:
        return {
            "from": offset,
            "size": PAGE_SIZE,
            "_source": FIELDS,
            "query": {
                "bool": {
                    "filter": [
                        {"terms": {"clientId.raw": [template["client_id"]]}},
                        {"terms": {"internalOrExternal": [{"internalOrExternal": "externalOnly"}]}},
                    ]
                }
            },
            "sort": [{"jobId": {"order": "asc"}}],
        }

    def page(self, data: Any, template: dict) -> tuple[int, list[dict]]:
        if not isinstance(data, dict) or data.get("timed_out") is not False:
            raise ValueError("TalentReef query timed out or returned malformed data")
        shards = data.get("_shards") or {}
        if (
            not shards.get("total")
            or shards.get("failed") != 0
            or shards.get("successful") != shards["total"]
        ):
            raise ValueError("TalentReef query returned partial shards")
        hits = data.get("hits") or {}
        total = hits.get("total")
        if isinstance(total, dict):
            if total.get("relation") != "eq":
                raise ValueError("TalentReef supplied only a lower-bound total")
            total = total.get("value")
        rows = hits.get("hits")
        if (
            isinstance(total, bool)
            or not isinstance(total, int)
            or not 0 < total <= MAX_JOBS
            or not isinstance(rows, list)
            or len(rows) > PAGE_SIZE
        ):
            raise ValueError("Missing or oversized TalentReef full collection")
        result = []
        for hit in rows:
            row = hit.get("_source") if isinstance(hit, dict) else None
            if (
                not isinstance(row, dict)
                or str(row.get("clientId")) != template["client_id"]
                or row.get("clientName") != template["client_name"]
                or row.get("internalOrExternal") != "externalOnly"
                or isinstance(row.get("jobId"), bool)
                or not re.fullmatch(r"[1-9][0-9]{0,12}", str(row.get("jobId", "")))
            ):
                raise ValueError("TalentReef public posting scope mismatch")
            row = deepcopy(row)
            # Follow the native display flag; do not republish hidden compensation.
            if row.get("pubCompensation") != 1:
                for key in ("minCompensation", "maxCompensation", "isSalaried"):
                    row.pop(key, None)
            result.append(row)
        return total, result

    async def roster(self, template: dict, policy: RobotsPolicy) -> dict[str, dict]:
        result = {}
        expected = None
        offset = 0
        while True:
            total, rows = self.page(
                await self.read_json(SEARCH, policy, self.request_body(template, offset)), template
            )
            if expected is not None and total != expected:
                raise ValueError("TalentReef total changed during pagination")
            expected = total
            if len(rows) != min(PAGE_SIZE, total - offset):
                raise ValueError("TalentReef returned an incomplete page")
            for row in rows:
                identifier = str(row["jobId"])
                if identifier in result:
                    raise ValueError("TalentReef repeated a posting across pages")
                result[identifier] = row
            offset += len(rows)
            if offset == total:
                break
        return result

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("TalentReef pagination is reconciled internally")
        policy = await RobotsPolicy.load(self.http, GATEWAY)
        return await self.roster(await self.template(policy), policy)

    def parse(self, row: dict) -> list[JobInput]:
        identifier, client_id = str(row["jobId"]), str(row["clientId"])
        title = text(row.get("positionType") or "")
        description = text(row.get("description") or "")
        company = text(row.get("brand") or row.get("clientName") or "")
        if not title or not description or not company:
            raise ValueError("Missing TalentReef public title, employer or full description")
        path = row.get("url")
        if not isinstance(path, str):
            raise ValueError("Missing TalentReef native application path")
        parts = urlsplit(path)
        if (
            parts.scheme
            or parts.netloc
            or parts.fragment
            or parts.query
            or not re.fullmatch(
                r"/apply/c_[a-z0-9_-]+/l_en/[^/?#]+-" + identifier + r"\.html", parts.path
            )
        ):
            raise ValueError("TalentReef application path/identity mismatch")
        posting_id = row.get("extUuid") or identifier
        if posting_id != identifier and str(UUID(posting_id)) != posting_id:
            raise ValueError("Invalid TalentReef public external posting ID")
        source_url = f"{ORIGIN}/clients/{client_id}/posting/{posting_id}/en"
        address = row.get("address") or {}
        if not isinstance(address, dict):
            raise ValueError("Malformed TalentReef public location")
        places = [
            address[k]
            for k in ("city", "stateOrProvince", "country")
            if isinstance(address.get(k), str) and address[k]
        ]
        salary = None
        if row.get("pubCompensation") == 1:
            salary = {
                k: row[k]
                for k in ("minCompensation", "maxCompensation", "isSalaried")
                if row.get(k) is not None
            }
        return [
            JobInput(
                external_id=identifier,
                title=title,
                company=company,
                description=description,
                source_url=source_url,
                application_url="https://secure.jobappnetwork.com" + path,
                location=", ".join(dict.fromkeys(places)),
                employment_type=row.get("contractType") or None,
                published_at=row.get("createdDate") or None,
                salary=salary or None,
                raw={"posting": row, "application_entry": "Native advertised application link"},
            )
        ]

    async def discover(self) -> Enumeration:
        board_policy = await RobotsPolicy.load(self.http, ORIGIN)
        board_policy.check(ORIGIN + "/" + self.alias + "/en")
        policy = await RobotsPolicy.load(self.http, GATEWAY)
        template = await self.template(policy)
        before = await self.roster(template, policy)
        jobs = [self.parse(row)[0] for row in before.values()]
        if await self.template(policy) != template or await self.roster(template, policy) != before:
            raise ValueError("TalentReef public snapshot changed during extraction")
        return Enumeration(jobs=jobs, complete=True)

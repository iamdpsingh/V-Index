"""Zoho Recruit public Careers embedded records; decode constants without executing JS."""

import asyncio
import json
import re
from typing import Any
from urllib.parse import unquote, urlsplit

import httpx
from bs4 import BeautifulSoup
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.connectors.teamtailor import TENANT
from vindex.schemas import Enumeration, JobInput

FIELDS = (
    "id",
    "Posting_Title",
    "Job_Opening_Name",
    "Job_Description",
    "Remote_Job",
    "Job_Type",
    "Industry",
    "Country",
    "State",
    "City",
    "Zip_Code",
    "Salary",
    "Currency",
    "Date_Opened",
    "Publish",
    "Keep_on_Career_Site",
    "Is_Locked",
    "Work_Experience",
    "Number_of_Positions",
)


def loads(value: str) -> Any:
    def invalid_constant(constant: str):
        raise ValueError(f"Non-JSON constant in Zoho public data: {constant}")

    return json.loads(value, parse_constant=invalid_constant)


def string_literal(code: str, start: int) -> tuple[str, int]:
    if start >= len(code) or code[start] not in "\"'":
        raise ValueError("Expected Zoho quoted public data literal")
    quote = code[start]
    output: list[str] = []
    index = start + 1
    escaped = {"b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t", "v": "\v"}
    while index < len(code):
        char = code[index]
        index += 1
        if char == quote:
            value = "".join(output)
            if any(0xD800 <= ord(c) <= 0xDFFF for c in value):
                value = value.encode("utf-16-le", "surrogatepass").decode("utf-16-le")
            return value, index
        if char in "\r\n" or ord(char) < 32:
            raise ValueError("Unescaped control in Zoho string literal")
        if char != "\\":
            output.append(char)
            continue
        if index >= len(code):
            break
        char = code[index]
        index += 1
        if char in ("x", "u"):
            size = 2 if char == "x" else 4
            digits = code[index : index + size]
            if len(digits) != size or not re.fullmatch(r"[0-9a-fA-F]+", digits):
                raise ValueError("Malformed Zoho string escape")
            output.append(chr(int(digits, 16)))
            index += size
        elif char in escaped:
            output.append(escaped[char])
        elif not char.isalnum() and char not in "\r\n":
            # ECMAScript punctuation identity escapes, e.g. the observed \-.
            output.append(char)
        else:
            raise ValueError("Unsupported Zoho string escape")
    raise ValueError("Unterminated Zoho string literal")


def object_literal(code: str, start: int) -> dict:
    if code[start : start + 1] != "{":
        raise ValueError("Expected Zoho public object literal")
    output: list[str] = []
    stack: list[str] = []
    index = start
    while index < len(code):
        char = code[index]
        if char in "\"'":
            value, index = string_literal(code, index)
            output.append(json.dumps(value))
            continue
        output.append(char)
        index += 1
        if char in "{[":
            stack.append(char)
        elif char in "}]":
            if not stack or stack.pop() != ("{" if char == "}" else "["):
                raise ValueError("Unbalanced Zoho public object")
            if not stack:
                result = loads("".join(output))
                if not isinstance(result, dict):
                    raise ValueError("Invalid Zoho public object")
                return result
    raise ValueError("Truncated Zoho public object")


def variable(soup: BeautifulSoup, name: str, jobs: bool = False) -> Any:
    values = []
    suffix = r"JSON\.parse\(\s*" if jobs else ""
    pattern = re.compile(rf"(?m)^var {re.escape(name)}\s*=\s*{suffix}")
    for script in soup.select("script:not([src])"):
        code = script.get_text()
        for matched in pattern.finditer(code):
            if jobs:
                value, end = string_literal(code, matched.end())
                if not code[end:].lstrip().startswith(")"):
                    raise ValueError("Unexpected Zoho public JSON.parse argument")
                values.append(loads(value))
            else:
                values.append(object_literal(code, matched.end()))
    if len(values) != 1:
        raise ValueError("Missing unique Zoho public data variable")
    return values[0]


def document(body: bytes) -> BeautifulSoup:
    if b"</html>" not in body.lower():
        raise ValueError("Truncated Zoho Careers document")
    return BeautifulSoup(body, "html.parser")


class ZohoConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider not in {"zoho-com", "zoho-eu", "zoho-in"} or not re.fullmatch(TENANT, slug):
            raise ValueError("Invalid Zoho Recruit hosted tenant")
        self.host = f"{slug}.zohorecruit.{provider.removeprefix('zoho-')}"
        self.origin = "https://" + self.host
        self.path = "/jobs/Careers"
        self.http = PublicHTTP(client, {self.host})

    def board(self, meta: dict) -> dict:
        org = meta["org_info"]
        if (
            meta["employee_portal"] is not False
            or meta["source"] != "CareerSite"
            or meta["page_name"] != "Careers"
            or org["hide_company_name"] is not False
            or not isinstance(org["company_name"], str)
            or not org["company_name"].strip()
            or not isinstance(org["id"], str)
            or not re.fullmatch(r"[1-9][0-9]*", org["id"])
        ):
            raise ValueError("Zoho public employer/portal identity mismatch")
        return {
            "company": org["company_name"],
            "id": org["id"],
            "source": meta["source"],
            "page_name": meta["page_name"],
        }

    def public_row(self, row: dict) -> dict:
        if (
            not isinstance(row["id"], str)
            or not re.fullmatch(r"[1-9][0-9]*", row["id"])
            or type(row["Publish"]) is not bool
            or type(row["Keep_on_Career_Site"]) is not bool
            or type(row["Is_Locked"]) is not bool
            or ("Remote_Job" in row and type(row["Remote_Job"]) is not bool)
            or not isinstance(row["Posting_Title"], str)
            or not row["Posting_Title"].strip()
        ):
            raise ValueError("Zoho job is not a valid public career listing")
        return {key: row[key] for key in FIELDS if key in row}

    def listings(self, body: bytes) -> tuple[dict, dict[str, dict]]:
        soup = document(body)
        inputs = {key: soup.select(f"input#{key}[value]") for key in ("jobs", "meta", "pageJson")}
        if any(len(items) != 1 for items in inputs.values()):
            raise ValueError("Missing unique Zoho public board records")
        meta = loads(str(inputs["meta"][0]["value"]))
        board = self.board(meta)
        if (
            meta["list_url"] != self.origin + self.path
            or soup.title is None
            or soup.title.get_text(" ", strip=True).rstrip(".")
            != ("Jobs at " + board["company"]).rstrip(".")
        ):
            raise ValueError("Zoho board URL/title mismatch")
        config = loads(str(inputs["pageJson"][0]["value"]))
        blocks = [b for b in config["detail"]["section"]["data"] if b.get("blocktype") == "jobs"]
        if (
            len(blocks) != 1
            or blocks[0]["isenabled"] is not True
            or not isinstance(blocks[0].get("applynow"), str)
            or not blocks[0]["applynow"].strip()
        ):
            raise ValueError("Missing supported Zoho public jobs/application block")
        rows = loads(str(inputs["jobs"][0]["value"]))
        if not isinstance(rows, list) or not 0 < len(rows) <= 400:
            raise ValueError("Empty or oversized Zoho public collection")
        result = {}
        seen = set()
        inactive = []
        for row in rows:
            value = self.public_row(row)
            if value["id"] in seen:
                raise ValueError("Duplicate Zoho public job ID")
            seen.add(value["id"])
            if not value["Publish"]:
                if value["Keep_on_Career_Site"] is not True:
                    raise ValueError("Unexpected unpublished non-retained Zoho row")
                inactive.append(
                    {
                        k: value[k]
                        for k in (
                            "id",
                            "Posting_Title",
                            "Publish",
                            "Keep_on_Career_Site",
                            "Is_Locked",
                        )
                    }
                )
                continue
            if value["Is_Locked"] is not False:
                raise ValueError("Ambiguous locked active Zoho row")
            result[value["id"]] = value
        if not result:
            raise ValueError("No active Zoho public jobs; extraction not proven")
        board["retained_inactive_records"] = inactive
        return board, result

    def parse(self, payload: Any) -> list[JobInput]:
        identifier, listing, board, body = payload
        soup = document(body)
        rows = variable(soup, "jobs", jobs=True)
        meta = variable(soup, "meta")
        if not isinstance(rows, list) or len(rows) != 1:
            raise ValueError("Missing unique Zoho public detail record")
        row = self.public_row(rows[0])
        url = meta["detail_url"]
        parsed = urlsplit(url)
        prefix = self.path + "/" + identifier + "/"
        og = soup.select('meta[property="og:url"]')
        if (
            row["id"] != identifier
            or row["Posting_Title"] != listing["Posting_Title"]
            or self.board(meta)
            != {k: v for k, v in board.items() if k != "retained_inactive_records"}
            or row["Publish"] is not True
            or row["Is_Locked"] is not False
            or len(og) != 1
            or og[0].get("content") != url
            or parsed.scheme != "https"
            or parsed.netloc != self.host
            or not parsed.path.startswith(prefix)
            or not parsed.path.removeprefix(prefix)
            or "/" in parsed.path.removeprefix(prefix)
            or parsed.query != "source=CareerSite"
            or parsed.fragment
            or any(ord(c) <= 32 or c in '<>"\\' for c in unquote(url))
        ):
            raise ValueError("Zoho detail ID/title/employer/native URL mismatch")
        description = text(row["Job_Description"])
        locations = [row.get(k) or listing.get(k) for k in ("City", "State", "Zip_Code", "Country")]
        amount = row.get("Salary")
        salary = None
        if amount is not None and str(amount).strip():
            salary = {"text": str(amount)}
            currency = row.get("Currency") or listing.get("Currency")
            if currency:
                salary["currency"] = currency
        return [
            JobInput(
                external_id=identifier,
                title=row["Posting_Title"],
                company=board["company"],
                description=description,
                quality_flags=[] if description else ["description_missing"],
                location=", ".join(dict.fromkeys(x for x in locations if x)),
                source_url=url,
                application_url=url,
                employment_type=row.get("Job_Type") or listing.get("Job_Type"),
                remote_status="remote" if row.get("Remote_Job") is True else None,
                salary=salary,
                published_at=row.get("Date_Opened"),
                raw={
                    "listing": listing,
                    "job": row,
                    "board": board,
                    "fetched_from": self.origin + self.path + "/" + identifier,
                    "original_detail_url": url,
                },
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("Zoho alternate pagination unsupported")
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
                        await read(self.origin + self.path + "/" + identifier),
                    )
                )
            )
        if self.listings(await read(self.origin + self.path)) != (board, rows):
            raise ValueError("Zoho complete public collection changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

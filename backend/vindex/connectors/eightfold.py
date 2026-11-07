"""Eightfold public robots-advertised job sitemaps and mandatory JobPosting pages."""

import asyncio
import json
import re
from datetime import datetime
from typing import Any
from urllib.parse import parse_qs, unquote, urlencode, urlsplit

import httpx
from bs4 import BeautifulSoup
from defusedxml import ElementTree
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.connectors.robots import RobotsPolicy
from vindex.connectors.teamtailor import TENANT
from vindex.schemas import Enumeration, JobInput

NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


class EightfoldConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider != "eightfold" or not re.fullmatch(TENANT, slug):
            raise ValueError("Invalid Eightfold native public tenant")
        self.host = slug + ".eightfold.ai"
        self.origin = "https://" + self.host
        self.http = PublicHTTP(client, {self.host})

    def scoped(self, url: str, pattern: str) -> str:
        p = urlsplit(url)
        params = parse_qs(p.query)
        if (
            p.scheme != "https"
            or p.netloc != self.host
            or not re.fullmatch(pattern, p.path)
            or p.fragment
            or set(params) != {"domain"}
            or len(params["domain"]) != 1
            or not re.fullmatch(r"[a-z0-9.-]{1,200}", params["domain"][0])
        ):
            raise ValueError("Unscoped Eightfold public sitemap/job URL")
        return params["domain"][0]

    def identifier(self, url: str) -> str:
        self.scoped(url, r"/careers/job/[1-9][0-9]*(?:-[^/]+)?")
        path = unquote(urlsplit(url).path)
        if any(c in path.removeprefix("/careers/job/") for c in "/\\?#"):
            raise ValueError("Unsafe Eightfold native job slug")
        matched = re.match(r"/careers/job/([1-9][0-9]*)", path)
        assert matched is not None
        return matched[1]

    def document(self, body: bytes) -> BeautifulSoup:
        if b"</html>" not in body.lower():
            raise ValueError("Truncated Eightfold public document")
        return BeautifulSoup(body, "html.parser")

    def board(self, body: bytes) -> dict:
        soup = self.document(body)
        modern = soup.select("code#pcsx-data")
        legacy = soup.select("code#smartApplyData")
        if len(modern) + len(legacy) != 1:
            raise ValueError("Unsupported Eightfold native public careers shell")
        data = json.loads((modern or legacy)[0].get_text())
        if modern:
            cfg = data["configs"]["pcsxConfig"]
            privacy = cfg["searchConfig"]["excludePrivatePositions"]
            count = None
            seed = []
        else:
            cfg = data
            privacy = data["excludePrivatePositions"]
            count = data["count"]
            seed = data["positions"]
            if (
                data.get("isUserAuthenticated") is not False
                or type(count) is not int
                or not 0 < count <= 200
                or not isinstance(seed, list)
                or len(seed) != min(10, count)
            ):
                raise ValueError("Unsupported Eightfold anonymous legacy roster")
            if any(not isinstance(r, dict) or r.get("isPrivate") is not False for r in seed):
                raise ValueError("Eightfold seed is not strictly public")
        company = cfg["branding"]["companyName"]
        if (
            privacy is not True
            or not isinstance(company, str)
            or not company.strip()
            or not isinstance(data.get("domain"), str)
        ):
            raise ValueError("Eightfold public source privacy/employer identity missing")
        # Never retain candidate, user, onboarding, saved-job or application configuration.
        return {
            "company": company,
            "domain": data["domain"],
            "expected_count": count,
            "seed_ids": [str(r["id"]) for r in seed],
        }

    def jobmap(self, body: bytes) -> dict[str, str]:
        root = ElementTree.fromstring(body)
        if root.tag != NS + "urlset":
            raise ValueError("Missing complete Eightfold job sitemap")
        entries = root.findall(NS + "url")
        homes = []
        rows = {}
        if not 1 < len(entries) <= 201:
            raise ValueError("Empty or oversized Eightfold public sitemap")
        for entry in entries:
            locs = entry.findall(NS + "loc")
            if len(locs) != 1 or not locs[0].text:
                raise ValueError("Malformed Eightfold sitemap URL")
            url = locs[0].text
            if urlsplit(url).path == "/careers":
                homes.append(self.scoped(url, r"/careers"))
                continue
            identifier = self.identifier(url)
            if identifier in rows:
                raise ValueError("Duplicate Eightfold public job ID")
            rows[identifier] = url
        if len(homes) != 1 or any(
            self.scoped(url, r"/careers/job/[1-9][0-9]*(?:-[^/]+)?") != homes[0]
            for url in rows.values()
        ):
            raise ValueError("Ambiguous Eightfold canonical public namespace")
        return rows

    def parse(self, payload: Any) -> list[JobInput]:
        identifier, url, board, body = payload
        soup = self.document(body)
        docs = [json.loads(t.get_text()) for t in soup.select('script[type="application/ld+json"]')]
        docs = [d for d in docs if isinstance(d, dict) and d.get("@type") == "JobPosting"]
        if len(docs) != 1:
            raise ValueError("Missing complete Eightfold public job detail")
        row = docs[0]
        if (
            self.identifier(row["url"]) != identifier
            or self.scoped(row["url"], r"/careers/job/[1-9][0-9]*(?:-[^/]+)?")
            != self.scoped(url, r"/careers/job/[1-9][0-9]*(?:-[^/]+)?")
            or row["hiringOrganization"]["name"] != board["company"]
            or not isinstance(row.get("title"), str)
            or not row["title"].strip()
            or not isinstance(row.get("description"), str)
            or not text(row["description"]).strip()
        ):
            raise ValueError("Eightfold public job ID/namespace/employer/full text mismatch")
        nodes = soup.select("code#smartApplyData")
        extra = {}
        if nodes:
            if len(nodes) != 1:
                raise ValueError("Ambiguous Eightfold public legacy detail state")
            data = json.loads(nodes[0].get_text())
            positions = data.get("positions")
            if (
                data.get("isUserAuthenticated") is not False
                or data.get("count") != 1
                or not isinstance(positions, list)
                or len(positions) != 1
                or str(positions[0].get("id")) != identifier
                or positions[0].get("isPrivate") is not False
            ):
                raise ValueError("Eightfold legacy public detail state mismatch")
            position = positions[0]
            extra = {
                k: position.get(k)
                for k in (
                    "id",
                    "name",
                    "posting_name",
                    "locations",
                    "location",
                    "department",
                    "work_location_option",
                    "location_flexibility",
                    "canonicalPositionUrl",
                )
            }
        locations = row.get("jobLocation") or []
        if isinstance(locations, dict):
            locations = [locations]
        places = []
        for loc in locations:
            address = loc.get("address") or {}
            values = []
            for key in ("addressLocality", "addressRegion", "postalCode", "addressCountry"):
                value = address.get(key)
                if isinstance(value, dict):
                    value = value.get("name")
                if value and value != "UNAVAILABLE":
                    values.append(str(value))
            if values:
                places.append(", ".join(dict.fromkeys(values)))
        employment = row.get("employmentType")
        if isinstance(employment, list):
            employment = ", ".join(employment)
        supplied = row.get("datePosted")
        published = datetime.fromisoformat(supplied) if supplied else None
        flags = []
        if published is not None and published.tzinfo is None:
            flags.append("publication_timezone_unspecified")
        if not places:
            flags.append("location_missing")
        return [
            JobInput(
                external_id=identifier,
                title=row["title"],
                company=board["company"],
                description=text(row["description"]),
                location="; ".join(dict.fromkeys(places)),
                source_url=url,
                application_url=row["url"],
                salary=row.get("baseSalary"),
                employment_type=employment,
                remote_status=row.get("jobLocationType") or extra.get("work_location_option"),
                published_at=published,
                quality_flags=flags,
                raw={
                    "board": board,
                    "jobposting": row,
                    "public_legacy_position": extra,
                    "published_at_original": supplied,
                    "application_entry": "native public posting",
                },
            )
        ]

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("Eightfold requires complete advertised sitemap enumeration")
        return await self.http.read(self.origin + "/careers")

    async def discover(self) -> Enumeration:
        policy = await RobotsPolicy.load(self.http, self.origin)

        async def read(url: str) -> bytes:
            policy.check(url)
            await asyncio.sleep(policy.delay())
            return await self.http.read(url)

        board = self.board(await read(self.origin + "/careers"))
        advertised = policy.parser.site_maps() or []
        indices = [url for url in advertised if urlsplit(url).path == "/careers/sitemap_index.xml"]
        if not indices:
            # Modern native hosts can omit robots sitemap declarations while serving
            # the same standard public index. The company namespace comes from the shell.
            indices = [
                self.origin + "/careers/sitemap_index.xml?" + urlencode({"domain": board["domain"]})
            ]
        if len(indices) != 1:
            raise ValueError("Missing unique Eightfold public sitemap index")
        self.scoped(indices[0], r"/careers/sitemap_index\.xml")

        async def roster() -> dict[str, str]:
            root = ElementTree.fromstring(await read(indices[0]))
            maps = []
            if root.tag != NS + "sitemapindex":
                raise ValueError("Invalid Eightfold sitemap index")
            for node in root.findall(NS + "sitemap"):
                locs = node.findall(NS + "loc")
                if len(locs) != 1 or not locs[0].text:
                    raise ValueError("Truncated Eightfold sitemap index")
                url = locs[0].text
                self.scoped(url, r"/careers/sitemap(?:_[0-9]+|_cat)?\.xml")
                if urlsplit(url).path != "/careers/sitemap_cat.xml":
                    maps.append(url)
            if not 0 < len(maps) <= 4 or len(set(maps)) != len(maps):
                raise ValueError("Unsupported Eightfold job sitemap collection")
            result: dict[str, str] = {}
            for url in maps:
                rows = self.jobmap(await read(url))
                if set(rows) & set(result):
                    raise ValueError("Repeated Eightfold job IDs between maps")
                result.update(rows)
            if (
                not 0 < len(result) <= 200
                or (board["expected_count"] is not None and len(result) != board["expected_count"])
                or not set(board["seed_ids"]) <= set(result)
            ):
                raise ValueError("Incomplete Eightfold public sitemap/board count")
            return result

        rows = await roster()
        jobs = []
        for identifier, url in rows.items():
            jobs.extend(self.parse((identifier, url, board, await read(url))))
        if await roster() != rows or self.board(await read(self.origin + "/careers")) != board:
            raise ValueError("Eightfold full public source changed during enumeration")
        return Enumeration(jobs=jobs, complete=True)

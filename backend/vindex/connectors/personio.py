"""Personio's opt-in public XML feed; entity/DTD expansion is prohibited."""

import asyncio
import re
from typing import Any

import httpx
from defusedxml import ElementTree
from vindex.connectors.http import PublicHTTP
from vindex.connectors.public import text
from vindex.schemas import Enumeration, JobInput


class PersonioConnector:
    def __init__(self, provider: str, slug: str, company: str, client: httpx.AsyncClient):
        if provider not in {"personio-de", "personio-com"} or not re.fullmatch(
            r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", slug
        ):
            raise ValueError("Invalid Personio configuration")
        tld = provider.split("-")[1]
        self.base = f"https://{slug}.jobs.personio.{tld}"
        self.company = company
        self.http = PublicHTTP(client, {f"{slug}.jobs.personio.{tld}"})

    async def fetch(self, cursor: int = 0) -> Any:
        if cursor:
            raise ValueError("Personio feed is not paginated")
        # Default-language feed preserves all positions without assuming English exists.
        return await self.http.read(f"{self.base}/xml")

    def parse(self, payload: Any) -> list[JobInput]:
        root = ElementTree.fromstring(payload, forbid_dtd=True)
        if root.tag != "workzag-jobs" or any(child.tag != "position" for child in root):
            raise ValueError("Unexpected Personio XML structure")
        jobs = []
        for position in root:

            def value(name: str, element=position) -> str:
                return (element.findtext(name) or "").strip()

            job_id = value("id")
            if not re.fullmatch(r"[0-9]+", job_id):
                raise ValueError("Invalid Personio job identifier")
            parts = []
            for section in position.findall("jobDescriptions/jobDescription"):
                parts.append(
                    text(
                        (section.findtext("name") or "") + "\n" + (section.findtext("value") or "")
                    )
                )
            locations = [value("office")] + [
                (office.text or "").strip()
                for office in position.findall("additionalOffices/office")
            ]
            url = f"{self.base}/job/{job_id}"
            raw = {child.tag: "".join(child.itertext()).strip() for child in position}
            raw["xml"] = ElementTree.tostring(position, encoding="unicode")
            salary_node = position.find("salaryInformation")
            jobs.append(
                JobInput(
                    external_id=job_id,
                    title=value("name"),
                    company=value("subcompany") or self.company,
                    description="\n\n".join(parts),
                    location="; ".join(dict.fromkeys(p for p in locations if p)),
                    source_url=url,
                    application_url=f"{url}#apply",
                    employment_type=" / ".join(
                        v for v in [value("employmentType"), value("schedule")] if v
                    )
                    or None,
                    salary={"source_text": "".join(salary_node.itertext()).strip()}
                    if salary_node is not None
                    else None,
                    # createdAt is creation, not confirmed original publication; retained in raw.
                    raw=raw,
                )
            )
        return jobs

    async def discover(self) -> Enumeration:
        jobs = self.parse(await self.fetch())
        if len({job.external_id for job in jobs}) != len(jobs):
            raise ValueError("Repeated Personio position identifier")
        # Default XML can enumerate a position while omitting its translated description.
        # Keep the default feed's ID universe and enrich only missing descriptions.
        for language in ("en", "de", "fr", "es", "nl", "it", "pt"):
            if all(job.description.strip() for job in jobs):
                break
            await asyncio.sleep(0.5)
            translated = self.parse(await self.http.read(f"{self.base}/xml?language={language}"))
            translations = {job.external_id: job for job in translated}
            if len(translations) != len(translated) or not translations.keys() <= {
                job.external_id for job in jobs
            }:
                raise ValueError("Translated feed identifiers changed; enumeration incomplete")
            enriched = []
            for job in jobs:
                translation = translations.get(job.external_id)
                if not job.description.strip() and translation and translation.description.strip():
                    job = job.model_copy(
                        update={
                            "description": translation.description,
                            "raw": {
                                **job.raw,
                                "description_translation": {
                                    "language": language,
                                    "xml": translation.raw["xml"],
                                },
                            },
                        }
                    )
                enriched.append(job)
            jobs = enriched
        if any(not job.description.strip() for job in jobs):
            raise ValueError(
                "Description unavailable in supported feed languages; snapshot incomplete"
            )
        return Enumeration(jobs=jobs, complete=True)

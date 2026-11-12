"""Check the complete advertised public Madgex listing pages without fetching details."""

import asyncio
import json
import re
from urllib.parse import urljoin, urlsplit

import httpx
from vindex.connectors.http import PublicHTTP
from vindex.connectors.jobboardio import document
from vindex.connectors.robots import RobotsPolicy

BOARDS = {
    "jobs.sciencecareers.org": "",
    "www.nature.com": "/naturecareers",
}


async def audit(host, prefix):
    origin = "https://" + host
    base = origin + prefix + "/jobs/"
    seen = set()
    total = None
    page = 0
    url = base
    async with httpx.AsyncClient(
        trust_env=False, timeout=15, headers={"User-Agent": "V-Index/0.1 public-job-indexer"}
    ) as client:
        http = PublicHTTP(client, {host})
        policy = await RobotsPolicy.load(http, origin)
        try:
            while url and page < 65:
                page += 1
                policy.check(url)
                await asyncio.sleep(policy.delay())
                soup = document(await http.read(url))
                counts = {
                    int(match[1].replace(",", ""))
                    for heading in soup.select("h1")
                    if (
                        match := re.fullmatch(
                            r"Found ([0-9,]+) jobs?", heading.get_text(" ", strip=True)
                        )
                    )
                }
                if counts:
                    if len(counts) != 1 or (total is not None and counts != {total}):
                        raise ValueError("Advertised total changed")
                    total = counts.pop()
                rows = set()
                for link in soup.select(".lister__item .lister__header a[href]"):
                    candidate = urlsplit(urljoin(url, str(link["href"]).strip()))
                    match = re.fullmatch(
                        re.escape(prefix)
                        + r"/job/([0-9]+)/(?:[a-zA-Z0-9_-]|%[89a-fA-F][0-9a-fA-F])+/?",
                        candidate.path,
                    )
                    if (
                        candidate.netloc != host
                        or candidate.scheme != "https"
                        or not match
                        or match[1] in rows
                    ):
                        raise ValueError("Malformed or repeated posting in a page")
                    rows.add(match[1])
                if not rows or len(rows) > 20 or seen & rows:
                    raise ValueError(f"Repeated or empty page, overlap {len(seen & rows)}")
                seen.update(rows)
                next_urls = {
                    urljoin(url, str(link["href"]).strip())
                    for link in soup.select('[rel="next"][href]')
                }
                expected = base + f"{page + 1}/"
                if next_urls and next_urls != {expected}:
                    raise ValueError("Unexpected next URL")
                url = expected if next_urls else ""
                if url and len(rows) != 20:
                    raise ValueError("Short nonterminal result page")
                if page % 10 == 0:
                    print(host, page, len(seen), total, flush=True)
            if url or total != len(seen):
                raise ValueError("Roster did not reconcile to the advertised total")
            result = "complete list enumeration; details not checked"
        except (ValueError, httpx.HTTPError) as exc:
            result = f"{type(exc).__name__}: {exc}"
        return dict(
            source=base,
            pages_attempted=page,
            observed_ids=len(seen),
            advertised_total=total,
            result=result,
        )


async def main():
    for result in await asyncio.gather(*(audit(host, prefix) for host, prefix in BOARDS.items())):
        print(json.dumps(result), flush=True)


asyncio.run(main())

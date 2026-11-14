"""Extract a bounded live sample from both reviewed Wiley Madgex boards."""

import asyncio
import json
from datetime import UTC, datetime

import httpx
from vindex.connectors.robots import RobotsPolicy
from vindex.connectors.wileymadgex import BOARDS, WileyMadgexConnector


async def sample(host: str) -> dict:
    async with httpx.AsyncClient(
        timeout=12, trust_env=False, headers={"User-Agent": "V-Index/0.1 public-job-indexer"}
    ) as client:
        connector = WileyMadgexConnector(host, client)
        result: dict = {"url": connector.search, "complete": False, "jobs": [], "errors": []}
        try:
            policy = await RobotsPolicy.load(connector.http, connector.origin)
            total, rows, _ = connector.page(await connector.read(connector.search, policy), 1)
        except (httpx.HTTPError, ValueError) as error:
            result["errors"].append(str(error))
            return result
        result["advertised_total"] = total
        result["sample_size"] = len(rows)
        for identifier, (url, title) in rows.items():
            try:
                job = connector.parse_detail(
                    identifier, url, title, await connector.read(url, policy)
                )
            except (httpx.HTTPError, ValueError) as error:
                result["errors"].append({"url": url, "error": str(error)})
            else:
                result["jobs"].append(job.model_dump(mode="json"))
        return result


async def main() -> None:
    results = await asyncio.gather(*(sample(host) for host in BOARDS))
    print(json.dumps({"checked_at": datetime.now(UTC).isoformat(), "boards": results}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

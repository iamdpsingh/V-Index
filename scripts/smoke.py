"""Live connector smoke evidence. Does not require a database or Redis."""

import asyncio
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import httpx
from vindex.connectors.public import PublicConnector

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = [
    ("Greenhouse", "greenhouse", "stripe", "Stripe", "https://job-boards.greenhouse.io/stripe"),
    (
        "Greenhouse",
        "greenhouse",
        "cloudflare",
        "Cloudflare",
        "https://job-boards.greenhouse.io/cloudflare",
    ),
    ("Lever.co", "lever", "spotify", "Spotify", "https://jobs.lever.co/spotify"),
    ("Lever.co", "lever", "palantir", "Palantir", "https://jobs.lever.co/palantir"),
    ("Ashby", "ashby", "Ashby", "Ashby", "https://jobs.ashbyhq.com/Ashby"),
    ("Ashby", "ashby", "ramp", "Ramp", "https://jobs.ashbyhq.com/ramp"),
]


def report():
    rows = json.loads((ROOT / "backend/providers.json").read_text())
    lines = [
        "# Provider coverage",
        "",
        "Exactly 58 ATS + 20 job-board platforms. Risk is a planning estimate, not a verified access limitation.",
        "",
        "IMPLEMENTED means code exists. LIVE_VERIFIED means the latest smoke run retrieved non-empty, complete jobs for all configured example tenants. This is a point-in-time connector check, not full production acceptance. FAILED and BLOCKED retain genuine limitations. NOT_STARTED providers have no connector.",
        "",
        "| Platform | Kind | Implementation | Evidence | Risk | Count (sum) | Last run | Examples / failures |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        examples = "; ".join(f"{e['url']} ({e['count']}; {e['status']})" for e in row["examples"])
        lines.append(
            f"| {row['name']} | {row['kind']} | {row['implementation_status']} | {row['evidence_status']} | {row['risk']} | {row['extraction_count']} | {row['last_run_at']} | {examples or 'Not tested'} {row['failure_reason'] or ''} |"
        )
    (ROOT / "docs/COVERAGE.md").write_text("\n".join(lines) + "\n")


async def main():
    results = []
    revision = (
        subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
        if (ROOT / ".git/refs/heads/main").exists()
        else "uncommitted-initial-build"
    )
    async with httpx.AsyncClient(
        timeout=30, trust_env=False, headers={"User-Agent": "V-Index/0.1 public-job-indexer"}
    ) as client:
        for name, provider, slug, company, url in EXAMPLES:
            result = dict(
                provider=name,
                url=url,
                at=datetime.now(UTC).isoformat(),
                revision=revision,
                count=0,
                status="FAILED",
                complete=False,
                error=None,
            )
            try:
                batch = await PublicConnector(provider, slug, company, client).discover()
                result.update(
                    count=len(batch.jobs),
                    complete=batch.complete,
                    status="LIVE_VERIFIED" if batch.complete and batch.jobs else "FAILED",
                    error=None if batch.jobs else "No jobs; extraction not proven",
                    payload_sha256=hashlib.sha256(batch.model_dump_json().encode()).hexdigest(),
                )
                # Minimal sanitized regression example, no full multi-tenant dumps.
                if batch.jobs:
                    sample = batch.jobs[0].model_dump(mode="json")
                    (ROOT / f"evidence/{provider}-{slug}-sample.json").write_text(
                        json.dumps(sample, indent=2) + "\n"
                    )
            except Exception as e:
                result["error"] = f"{type(e).__name__}: {e}"
            results.append(result)
            print(json.dumps(result), flush=True)
            await asyncio.sleep(0.5)
    path = ROOT / "evidence" / (datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-smoke.json")
    path.write_text(json.dumps(results, indent=2) + "\n")
    rows = json.loads((ROOT / "backend/providers.json").read_text())
    for row in rows:
        runs = [r for r in results if r["provider"] == row["name"]]
        if runs:
            row.update(
                examples=runs,
                last_run_at=max(r["at"] for r in runs),
                extraction_count=sum(r["count"] for r in runs),
                evidence_status="LIVE_VERIFIED"
                if all(r["status"] == "LIVE_VERIFIED" for r in runs)
                else "FAILED",
                failure_reason="; ".join(r["error"] for r in runs if r["error"]) or None,
                limitations=[
                    "Point-in-time public API enumeration; deployment and continuous operation unverified"
                ],
            )
    (ROOT / "backend/providers.json").write_text(json.dumps(rows, indent=2) + "\n")
    report()
    if any(r["status"] != "LIVE_VERIFIED" for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())

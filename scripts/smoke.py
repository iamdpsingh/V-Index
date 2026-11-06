"""Live connector smoke evidence. Does not require a database or Redis."""

import argparse
import asyncio
import hashlib
import json
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import httpx
from vindex.connectors.registry import create_connector

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = [
    (
        "ApplicantPro",
        "applicantpro",
        "farbank",
        "Far Bank Enterprises",
        "https://farbank.applicantpro.com/jobs/",
    ),
    ("ApplicantPro", "applicantpro", "clarke", "Clarke", "https://clarke.applicantpro.com/jobs/"),
    (
        "iSolvedHire",
        "isolvedhire",
        "uasystem",
        "University of Alabama System Office",
        "https://uasystem.isolvedhire.com/jobs/",
    ),
    (
        "iSolvedHire",
        "isolvedhire",
        "verifiedcredentials",
        "Verified Credentials",
        "https://verifiedcredentials.isolvedhire.com/jobs/",
    ),
    ("Jobvite", "jobvite", "iboss", "iboss", "https://jobs.jobvite.com/iboss/jobs"),
    ("Jobvite", "jobvite", "optimas", "Optimas Solutions", "https://jobs.jobvite.com/optimas/jobs"),
    (
        "Recooty",
        "recooty",
        "augusto-digital",
        "Augusto Digital",
        "https://careerspage.io/augusto-digital",
    ),
    ("Recooty", "recooty", "recooty-inc", "Recooty Inc.", "https://careerspage.io/recooty-inc"),
    (
        "Manatal",
        "manatal",
        "quantilehealth",
        "Quantile Health",
        "https://www.careers-page.com/quantilehealth",
    ),
    (
        "Manatal",
        "manatal",
        "munich-ventures-2",
        "Munich Ventures",
        "https://www.careers-page.com/munich-ventures-2",
    ),
    (
        "Polymer",
        "polymer",
        "chemfinitytech",
        "ChemFinity Technologies",
        "https://jobs.polymer.co/chemfinitytech",
    ),
    (
        "Polymer",
        "polymer",
        "gencores-inc",
        "Gencores, Inc.",
        "https://jobs.polymer.co/gencores-inc",
    ),
    (
        "GoHire",
        "gohire",
        "dineamic-hospitality-fniota1h",
        "DineAmic Hospitality",
        "https://jobs.gohire.io/dineamic-hospitality-fniota1h/",
    ),
    (
        "GoHire",
        "gohire",
        "digital-shift-o0hrqw5o",
        "Digital Shift",
        "https://jobs.gohire.io/digital-shift-o0hrqw5o/",
    ),
    ("HireHive", "hirehive", "amcsgroup", "AMCS Group", "https://amcsgroup.hirehive.com"),
    ("HireHive", "hirehive", "echelon-dc", "Echelon DC", "https://echelon-dc.hirehive.com"),
    (
        "JazzHR",
        "jazzhr",
        "lapmasterwolters",
        "Lapmaster Wolters",
        "https://lapmasterwolters.applytojob.com/apply",
    ),
    (
        "JazzHR",
        "jazzhr",
        "belaytechnologies",
        "Belay Technologies",
        "https://belaytechnologies.applytojob.com/apply",
    ),
    (
        "Jobboardly",
        "jobboardly",
        "recruiter-jobs",
        "Recruiter jobs",
        "https://recruiter-jobs.jobboardly.com/jobs",
    ),
    (
        "Jobboardly",
        "jobboardly",
        "pennsylvania-communications",
        "Pennsylvania Communications",
        "https://pennsylvania-communications.jobboardly.com/jobs",
    ),
    ("Pinpoint", "pinpoint", "intermedia", "Intermedia", "https://intermedia.pinpointhq.com"),
    ("Pinpoint", "pinpoint", "workwithus", "Pinpoint", "https://workwithus.pinpointhq.com"),
    ("BambooHR", "bamboohr", "anaergia", "Anaergia", "https://anaergia.bamboohr.com/careers"),
    ("BambooHR", "bamboohr", "concept2", "Concept2", "https://concept2.bamboohr.com/careers"),
    ("Workable", "workable", "careers", "Workable", "https://apply.workable.com/careers/"),
    (
        "Workable",
        "workable",
        "learnworlds",
        "LearnWorlds",
        "https://apply.workable.com/learnworlds/",
    ),
    ("Teamtailor", "teamtailor", "clearroute", "ClearRoute", "https://clearroute.teamtailor.com"),
    ("Teamtailor", "teamtailor", "omny", "Omny", "https://omny.teamtailor.com"),
    ("Breezy HR", "breezy", "vald", "VALD", "https://vald.breezy.hr"),
    ("Breezy HR", "breezy", "subscribe", "SUBSCRIBE", "https://subscribe.breezy.hr"),
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
    (
        "SmartRecruiters",
        "smartrecruiters",
        "SmartRecruiters",
        "SmartRecruiters",
        "https://careers.smartrecruiters.com/SmartRecruiters",
    ),
    (
        "SmartRecruiters",
        "smartrecruiters",
        "Colliers",
        "Colliers",
        "https://careers.smartrecruiters.com/Colliers",
    ),
    ("Personio", "personio-de", "matrix42", "Matrix42", "https://matrix42.jobs.personio.de"),
    ("Personio", "personio-de", "planqc-gmbh", "planqc", "https://planqc-gmbh.jobs.personio.de"),
    ("Recruitee", "recruitee", "natilik", "Natilik", "https://natilik.recruitee.com"),
    ("Recruitee", "recruitee", "bunq", "bunq", "https://bunq.recruitee.com"),
    ("Workday", "workday", "imf~wd5~IMF", "IMF", "https://imf.wd5.myworkdayjobs.com/IMF"),
    (
        "Workday",
        "workday",
        "gatesfoundation~wd1~Gates",
        "Gates Foundation",
        "https://gatesfoundation.wd1.myworkdayjobs.com/Gates",
    ),
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider",
        action="append",
        choices=sorted({row[0] for row in EXAMPLES}),
        help="Check only selected providers (repeatable)",
    )
    selected = parser.parse_args().provider
    examples = [row for row in EXAMPLES if not selected or row[0] in selected]
    results = []
    try:
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except subprocess.CalledProcessError:
        revision = "uncommitted-initial-build"
    dirty = bool(
        subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
    )
    code_hash = hashlib.sha256()
    for file in sorted((ROOT / "backend/vindex").rglob("*.py")) + [Path(__file__).resolve()]:
        code_hash.update(str(file.relative_to(ROOT)).encode())
        code_hash.update(file.read_bytes())
    async with httpx.AsyncClient(
        timeout=30, trust_env=False, headers={"User-Agent": "V-Index/0.1 public-job-indexer"}
    ) as client:
        for name, provider, slug, company, url in examples:
            result = dict(
                provider=name,
                url=url,
                at=datetime.now(UTC).isoformat(),
                revision=revision,
                working_tree_dirty_at_start=dirty,
                code_sha256=code_hash.hexdigest(),
                count=0,
                status="FAILED",
                complete=False,
                error=None,
            )
            try:
                async with asyncio.timeout(600):
                    batch = await create_connector(provider, slug, company, client).discover()
                result.update(
                    count=len(batch.jobs),
                    quality_flag_counts=dict(
                        Counter(flag for job in batch.jobs for flag in job.quality_flags)
                    ),
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
            result["finished_at"] = datetime.now(UTC).isoformat()
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
                implementation_status="IMPLEMENTED",
                examples=runs,
                last_run_at=max(r["finished_at"] for r in runs),
                extraction_count=sum(r["count"] for r in runs),
                evidence_status="LIVE_VERIFIED"
                if len({r["url"] for r in runs}) >= 2
                and all(r["status"] == "LIVE_VERIFIED" for r in runs)
                else "FAILED",
                failure_reason="; ".join(r["error"] for r in runs if r["error"]) or None,
                limitations=[
                    "Point-in-time public API/feed enumeration; continuous operation is not established by this smoke test",
                    *(
                        {
                            "ApplicantPro": [
                                "Hosted applicantpro.com current public core/jobs component plus mandatory current public job detail and native page checks; custom domains/alternate templates unsupported",
                                "Board-discovered organization/domain identity, explicit external-only isInternal=0 collection, exact count/unique IDs and fixed tenant job links required",
                                "Maximum 400 details; empty, partial, changed and failed enumerations abort without reconciliation; board and full collection reconfirmed",
                                "Native and fixed shared-vendor canonical aliases are validated as metadata; redirects are never followed; native inline application page is the application entry",
                                "Source datePosted retains missing timezone precision; invalid validThrough strings remain raw and are not used for closure; empty salary amounts remain unknown",
                            ],
                            "iSolvedHire": [
                                "Separate required platform/host/evidence from ApplicantPro, sharing the observed current public core/jobs template only",
                                "Hosted isolvedhire.com boards only; exact discovered site IDs, external-only isInternal=0 collection and count/unique IDs are mandatory",
                                "Maximum 400 matching public job details; optional source JobPosting retained or omission flagged; board/native application/full collection reconfirmed; custom domains/alternate templates unsupported",
                                "Empty/failed/partial snapshots never close jobs; source labels/publication precision and actual supplied salaries retained without invention",
                            ],
                            "Jobvite": [
                                "Hosted jobs.jobvite.com unfiltered server-rendered Open Positions tables only; custom domains and alternate/paginated templates unsupported",
                                "No authoritative total is supplied; complete bounded table membership/title reconfirmation establishes the observed template snapshot",
                                "Maximum 400 details; every page must match listed title, employer title, native job ID, category/location metadata and native apply link",
                                "All explicit detail locations retained; salary/employment/original-publication fields absent as independent metadata remain unknown, source description retained intact",
                                "Empty, malformed, failed or changed enumerations abort without closures; no application form is fetched or submitted",
                            ],
                            "Recooty": [
                                "Current careerspage.io public server-rendered Inertia templates only; legacy jobs.recooty.com, www redirects and custom domains unsupported",
                                "Maximum 400 details; embedded job collection must match visible total, unique IDs and actual listing titles/links",
                                "Every detail must match employer, numeric ID, slug, title, source JobPosting ULID/canonical URL, OPEN career status, observed APPROVED/NOT_APPLIED board flag and native application link",
                                "Full roster reconfirmed after details; empty/partial/paginated/changed collections fail without closures",
                                "Original publication timestamp, source location/workplace/employment labels and provided salary fields preserved; unrelated auth/form/config state excluded",
                            ],
                            "Manatal": [
                                "Legacy www.careers-page.com boards only; new tenant subdomains, custom domains and other themes unsupported",
                                "Public unfiltered collection count must match named career-page total and visible titles; sequential fixed-host pagination validated before any detail requests",
                                "Maximum 400 details/100 pages; empty, malformed, partial, changed or failed snapshots abort without reconciliation",
                                "Every HTML detail must match title, employer, Manatal identity, full description and native application link; full collection and board reconfirmed",
                                "Source descriptions, locations and visible salary currency/range preserved; employment/workplace/publication metadata not independently supplied by supported template remains null",
                                "Raw observations preserve source collection and job-bearing detail HTML; no candidate application is submitted or fetched",
                            ],
                            "Polymer": [
                                "Documented unauthenticated public organizations/jobs API; no customer/candidate API or account token is used",
                                "Only complete single-page named collections with matching count/is_first/is_last/page/total metadata are supported; paginated/empty collections fail closed",
                                "Maximum 400 details; unique IDs, listed/detail employer/title/hash/lifecycle and source links must match",
                                "Complete collection reconfirmed after all details, excluding only changing relative-age text from comparison; original age text remains raw",
                                "Hosted jobs.polymer.co registration and posting links only; custom domains remain unsupported",
                                "Native application description URL retained as application entry; salary is source text, remoteness labels and published_at retained without substituting created_at",
                                "Public job fields retained; form questions/settings excluded; point-in-time evidence is not production freshness acceptance",
                            ],
                            "GoHire": [
                                "English jobs.gohire.io hosted boards only; custom domains and jobs.talentium.io links are unsupported",
                                "Public widget collection must match the explicit career-page total and visible first-page titles; every detail must match listing and employer identity",
                                "Maximum 400 details; empty, malformed, changed and failed enumerations abort without reconciliation",
                                "Complete board identity, visible list and full API collection are reconfirmed after extraction; this is not a transactional upstream snapshot",
                                "General application pools are excluded; form/questions/upload configuration is not retained",
                                "Native posting is the application entry point; salary remains source text and publication precision is date only",
                            ],
                            "HireHive": [
                                "Hosted hirehive.com public ItemList/JobPosting templates only; custom domains and legacy Embed URL registration remain unsupported",
                                "Explicit total, contiguous list positions, unique validated links and successful matching details are required; singleton JSON-LD items are supported",
                                "Maximum 400 details; unnamed/partial lists and any failed/changed detail abort without reconciliation",
                                "A zero-job snapshot requires an explicit named ItemList with total=0, no items and successful full reconfirmation; it does not count as live extraction evidence",
                                "Native career posting is the application entry point; original attributed JSON-LD links are retained raw",
                                "Completeness follows the public ItemList total and a final complete link/title reconfirmation, not a transactional upstream snapshot",
                            ],
                            "JazzHR": [
                                "Hosted applytojob.com Current Openings templates only; custom domains and alternative templates remain unsupported",
                                "No source total is supplied; completeness follows the full server-rendered Current Openings list and a final link/title reconfirmation",
                                "Maximum 400 details; empty, truncated, unexpectedly paginated or malformed lists fail closed",
                                "Every detail requires matching canonical URL/title, employer identity, description and native application form; no form is submitted",
                                "Original publication dates and structured salaries are not established by this template; provided source text remains in original description/header observations",
                            ],
                            "Jobboardly": [
                                "Hosted jobboardly.com public XML feed plus full HTML pagination; custom-domain registration and redirecting aliases unsupported",
                                "Explicit sequential Next controls, range counters, unique links and successful JobPosting/apply details are required",
                                "XML path: at most 5000 jobs/100 HTML pages and 20 MB per feed; HTML-only fallback remains capped at 400 details; empty feeds/pages fail closed",
                                "JSON-LD preserves salary, employment type, locations and datePosted; explicit visible workplace labels are preserved",
                                "Email-only applications retain the mailto destination in raw, use the original HTTPS posting as the application entry point, and carry application_by_email",
                                "Full XML record set and all HTML pages must agree and be reconfirmed; any change/failure aborts, not a transactional upstream snapshot",
                            ],
                            "Pinpoint": [
                                "Documented public postings.json full collection; legacy jobs.json is intentionally not used because it omits secondary postings",
                                "Each posting ID is preserved separately from its parent job ID; custom application/source links remain intact",
                                "Hosted tenant registration only; custom-domain entry detection and locale-specific feed selection remain unsupported",
                                "No original publication timestamp is promised by this feed; hidden compensation is not promoted to normalized salary",
                                "Robots policy can prevent a tenant fetch; no access controls are bypassed",
                            ],
                            "BambooHR": [
                                "Hosted bamboohr.com career list/detail only; maximum 400 details and no custom-domain detection",
                                "Reported total must equal unique listed identifiers, every detail must match the open listing, and IDs are reconfirmed",
                                "Empty lists fail closed pending independent tenant identity verification; no closures are inferred from those runs",
                                "Source numeric locationType is preserved raw and flagged workplace_type_unmapped; no workplace meaning is guessed",
                                "Application URL is the source career posting containing its native application entry; public website interfaces have no integration stability guarantee",
                            ],
                            "Workable": [
                                "Uses the public jobs collection with details=true on the fixed apply.workable.com widget host",
                                "Bare /j/shortcode URLs lack an account identifier; register an account career page instead",
                                "Custom-domain registration remains unsupported; all locations and source publication fields are preserved",
                                "No authoritative total is supplied; completeness follows the documented full-collection contract and an ID-set reconfirmation",
                                "Repeated shortcodes are merged only for non-conflicting location variants; all original rows are retained",
                            ],
                            "Teamtailor": [
                                "Hosted teamtailor.com tenants only; custom domains remain unsupported",
                                "Feeds with next_url or at least 100 items fail closed until pagination is supported",
                                "JSON Feed and RSS identifiers must match; workplace/location metadata is joined by UUID",
                                "Application URL is the original career posting entry point, not a separately fetched application form",
                            ],
                            "Breezy HR": [
                                "Hosted breezy.hr tenants only; custom domains remain unsupported",
                                "Maximum 400 details; empty feeds fail closed because an authoritative empty-board marker is not established",
                                "Feed IDs must match public board links; every description and application link requires a successful detail fetch",
                                "Hosted JSON/HTML interfaces are observed public interfaces without a vendor stability guarantee",
                                "Talent-pool postings without Google JobPosting schema require matching canonical/Open Graph URLs, title, description and apply link; the omission is flagged",
                            ],
                            "Workday": [
                                "Hosted myworkdayjobs.com sites only; myworkdaysite.com/custom domains are unsupported",
                                "Boards above 400 jobs or reported totals at/above 2000 fail closed; large-board completeness is not claimed",
                                "Robots policy and pacing are enforced; a missing robots file (404) is allowed, other robots failures abort",
                                "Verified counts depend on source totals plus ID/detail checks and first-page reconfirmation, not a transactional upstream snapshot",
                            ],
                            "Recruitee": [
                                "Uses documented XML feed; the careers JSON API token deadline (2027-02-10) is an external dependency to monitor",
                                "Custom application links are preserved; custom-domain source URL detection remains unsupported",
                            ],
                            "Personio": [
                                "Live tenants use .de; .com route is implemented but not live-tested",
                                "XML feed must be enabled; incomplete translated descriptions fail the run",
                            ],
                            "SmartRecruiters": [
                                "Every posting requires a detail request; very large boards may exceed the ten-minute budget",
                                "Explicitly blank role descriptions are preserved and flagged role_description_missing; source text is not invented",
                            ],
                        }.get(row["name"], [])
                    ),
                ],
            )
    (ROOT / "backend/providers.json").write_text(json.dumps(rows, indent=2) + "\n")
    report()
    if any(r["status"] != "LIVE_VERIFIED" for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())

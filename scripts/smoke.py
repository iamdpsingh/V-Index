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
    ("WeRecruit", "werecruit", "epec", "EPEC", "https://careers.werecruit.io/fr/epec"),
    (
        "WeRecruit",
        "werecruit",
        "ctlog-international",
        "CTLOG INTERNATIONAL",
        "https://careers.werecruit.io/fr/ctlog-international",
    ),
    ("Comeet", "comeet", "oriient~EA.005", "Oriient", "https://www.comeet.com/jobs/oriient/EA.005"),
    ("Comeet", "comeet", "webbing~46.00E", "Webbing", "https://www.comeet.com/jobs/webbing/46.00E"),
    ("Zoho Recruit", "zoho-eu", "mywork", "MyWork", "https://mywork.zohorecruit.eu/jobs/Careers"),
    (
        "Zoho Recruit",
        "zoho-com",
        "global",
        "Premier Inn Hotels LLC.",
        "https://global.zohorecruit.com/jobs/Careers",
    ),
    (
        "Paylocity",
        "paylocity",
        "a387d706-ac6f-4e58-b47b-be05001923ea",
        "SOLUTIONS FOR INFORMATION DESIGN",
        "https://recruiting.paylocity.com/Recruiting/Jobs/All/a387d706-ac6f-4e58-b47b-be05001923ea",
    ),
    (
        "Paylocity",
        "paylocity",
        "be178b00-f3fb-452e-9aef-dce1ef7fcdba",
        "Office Practicum",
        "https://recruiting.paylocity.com/Recruiting/Jobs/All/be178b00-f3fb-452e-9aef-dce1ef7fcdba",
    ),
    (
        "Hireology",
        "hireology",
        "beachchevrolet",
        "Beach Chevrolet",
        "https://careers.hireology.com/beachchevrolet",
    ),
    (
        "Hireology",
        "hireology",
        "pipprinting01151",
        "PIP / Dynamark",
        "https://careers.hireology.com/pipprinting01151",
    ),
    ("JOIN.com", "join", "2open", "2 OPEN CHINA ECOMMERCE", "https://join.com/companies/2open"),
    ("JOIN.com", "join", "joinit", "Join GmbH", "https://join.com/companies/joinit"),
    (
        "HireBridge",
        "hirebridge",
        "8484",
        "Confirm",
        "https://recruit.hirebridge.com/v3/Jobs/list.aspx?cid=8484",
    ),
    (
        "HireBridge",
        "hirebridge",
        "8427",
        "LCG, Inc.",
        "https://recruit.hirebridge.com/v3/Jobs/list.aspx?cid=8427",
    ),
    (
        "TriNet",
        "trinet",
        "69740-ark-investment-management",
        "ARK Investment Management",
        "https://app.trinethire.com/companies/69740-ark-investment-management/jobs",
    ),
    (
        "TriNet",
        "trinet",
        "665804-stridepath-consulting",
        "Stridepath Consulting",
        "https://app.trinethire.com/companies/665804-stridepath-consulting/jobs",
    ),
    (
        "CareerPlug",
        "careerplug",
        "576036",
        "Rubber & Accessories",
        "https://app.careerplug.com/accounts/576036",
    ),
    (
        "CareerPlug",
        "careerplug",
        "579908",
        "Freedom Motors USA",
        "https://app.careerplug.com/accounts/579908",
    ),
    ("Kula.ai", "kula", "fwg-internal", "Frontwise Group", "https://careers.kula.ai/fwg-internal"),
    ("Kula.ai", "kula", "massive-bio", "Massive Bio", "https://careers.kula.ai/massive-bio"),
    ("Rippling", "rippling", "realwork", "RealWork", "https://ats.rippling.com/realwork/jobs"),
    (
        "Rippling",
        "rippling",
        "sas",
        "Strategic Association Solutions",
        "https://ats.rippling.com/sas/jobs",
    ),
    (
        "Trakstar",
        "trakstar",
        "bsglaw",
        "Berman Sobin Gross LLP",
        "https://bsglaw.hire.trakstar.com/",
    ),
    (
        "Trakstar",
        "trakstar",
        "worksuites",
        "Lucid Private Offices",
        "https://worksuites.hire.trakstar.com/",
    ),
    (
        "Freshteam",
        "freshteam",
        "sequoiaat",
        "Sequoia Applied Technologies",
        "https://sequoiaat.freshteam.com/jobs",
    ),
    ("Freshteam", "freshteam", "talent360", "Talent 360", "https://talent360.freshteam.com/jobs"),
    (
        "HiringThing",
        "hiringthing",
        "math-learning-center",
        "The Math Learning Center",
        "https://math-learning-center.hiringthing.com/",
    ),
    (
        "HiringThing",
        "hiringthing",
        "rtrjobs",
        "Real Time Resolutions Inc",
        "https://rtrjobs.hiringthing.com/",
    ),
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
                            "WeRecruit": [
                                "Native careers.werecruit.io French tenant full public site-map template only; empty/alternate/custom templates unsupported",
                                "All unique native offer IDs, full description/profile/benefits and mandatory matching public JobPosting/application controls required; maximum 400 jobs",
                                "Explicit spontaneous-application pools retained as excluded source metadata; navigation redirects never followed; no application submitted",
                                "Full sitemap and tenant identity reconfirmed after every mandatory detail; failed/changed/partial requests abort without closures",
                                "Preserve supplied salary, employment, original publication, location and explicit workplace metadata; unknown values remain unknown",
                                "No independent total or atomic source snapshot; bounded point-in-time evidence does not establish production freshness",
                            ],
                            "Comeet": [
                                "Native www.comeet.com company public COMPANY_DATA/COMPANY_POSITIONS_DATA plus documented Careers API 2.0 details only; no employee/candidate/account APIs",
                                "Only listed is_internal=false positions with matching company UID/name/slug and scoped native URLs; at most 200 unique mandatory details, no empty/partial reconciliation",
                                "Browser-published Careers read token used only in memory for listed-position requests; never persisted in evidence or exception URLs; no application/questionnaires requested or retained",
                                "Every mandatory detail must match advertised UID/title/company/lifecycle/location/workplace/source links; optional requisition ID enrichment retained separately; final full roster reconfirmed",
                                "All ordered full description/requirements sections retained; explicit employment/workplace labels and salary sections preserved; time_updated is not substituted for absent publication date",
                                "No independent total or transactional upstream snapshot; source full public array defines supported completeness; known documented vendor sandbox rejected",
                            ],
                            "Zoho Recruit": [
                                "Native tenant.zohorecruit.com/eu/in /jobs/Careers embedded-record template only; legacy/custom/employee portals and renamed-brand title mismatches unsupported",
                                "Complete public embedded collection up to 400 records; unique IDs and boolean publication/lock/retention flags required; full active and retained-inactive metadata reconfirmed",
                                "Zoho explicitly permits closed/unpublished jobs to remain on career sites: unpublished retained records stay out of active jobs; Keep_on_Career_Site is a retention preference, not an active-job requirement",
                                "Every active job requires matching native detail ID/title/employer/org ID/canonical URL, Publish=true and Is_Locked=false; no failed or partial snapshot reconciled",
                                "Decode only public JSON constants and ESAPI quoted literals without executing JavaScript; no CDN scripts, forms, employee APIs, CSRF values or candidate configuration used/retained",
                                "Full actual description, supplied salary text/currency, employment, locations and Date_Opened preserved; native detail is the application entry; empty/ambiguous states fail closed",
                                "No independent source total/transactional snapshot; completeness follows the full public initial record collection and final reconfirmation, not a production freshness claim",
                            ],
                            "Paylocity": [
                                "Native recruiting.paylocity.com All/{board UUID} full public window.pageData template only; generic unnamed board brands, internal/custom/alternate templates unsupported",
                                "Public ShowInternal=false and per-job IsInternal=false, unique positive IDs, module/location/brand identity and full source collection required; maximum 400 mandatory HTML details",
                                "No independent total is supplied: the observed native client uses the entire Jobs array as OriginalJobs and computes its displayed total locally; full array/metadata reconfirmed after details",
                                "Each detail must match native title, module name, logo reference, Open Graph URL and exact Apply link; no application/form submitted or fetched",
                                "Full Description and Requirements sections preserved separately from preview text; source job type, salary description and PublishedDate retained",
                                "All original location/display flags retained, explicit rendered Fully Remote or Hybrid Remote labels preserved; third-party tracking and form configuration excluded",
                            ],
                            "Hireology": [
                                "Native careers.hireology.com/{careersPath} shell and explicitly public api.hireology.com/v2/public/careers routes only; no frontend token, authorization header or private API used",
                                "Complete first public API page only: count must equal all unique rows, page=1, page_size=10; larger, empty, duplicate, blind or mismatched employer collections abort",
                                "Mandatory public detail for each listed ID must exactly match all retained job fields; native career/application paths, organization IDs and named employer validated",
                                "Native description page is the application entry; no form endpoint, login, submission, third-party apply token or candidate configuration requested or retained",
                                "All public location labels/employment/description retained; positive source compensation preserved without inventing currency; zero-filled compensation stays unknown",
                                "created_at retained raw and never substituted for missing original posting date; false remote flag preserved raw without guessing onsite/hybrid; full board/collection reconfirmed",
                            ],
                            "JOIN.com": [
                                "Native join.com/companies/{domain} current pageData SSR template; explicit public page=1 collection only, legacy initialState/custom/locale variants unsupported",
                                "Single complete page only: page=1, pageCount=1, perPage=5 and total equals all unique visible job links and stable job IDs; empty/filtered/multipage or extra spontaneous-application counts abort",
                                "Each native detail must match stable job ID, current advertised idParam, public named company, ONLINE/null-closed lifecycle, canonical URL, full JobPosting and native ApplyButton",
                                "Native job page retained as application entry; rotating advert ID is not used as the stable external job ID; redirects never followed",
                                "All source locations/workplace/employment/publication fields retained; salary amounts without independently established units remain original fields with salary_units_unmapped",
                                "Full public roster reconfirmed; contact names, user state, form configuration and unrelated company state excluded; bounded snapshot is not production acceptance",
                            ],
                            "HireBridge": [
                                "Native recruit.hirebridge.com/v3/Jobs/list.aspx?cid={numeric customer} location-counted public template only; alternate/custom/filtered variants unsupported",
                                "Every unique job ID/native link and location group must exactly match all explicit location counters; maximum 400 mandatory details, no empty or partial reconciliation",
                                "Board/detail customer-scoped public brand asset references, title/location, native ASP.NET form action and explicit Apply URL must match",
                                "Fixed native HTTPS Apply target extracted from a narrowly matched popUp literal without executing JavaScript or fetching/submitting an application",
                                "Full job description and skills sections retained; source does not independently supply original publication/employment/salary fields in supported template, so these remain unknown",
                                "Native hosted brand references only; inline data-image branding currently unsupported; full roster/counters reconfirmed after details",
                            ],
                            "TriNet": [
                                "Native app.trinethire.com/companies/{ID-slug}/jobs complete public table template only; custom, confidential and paginated variants unsupported",
                                "All named Role/Type/Location table rows and unique native links must agree; maximum 400 mandatory details; empty, changed, malformed or failed collections abort",
                                "Detail native form/job ID/title/company/Open Graph URL and employment type must match; no application submitted or form tokens/configuration retained",
                                "Both board location label and detail physical location retained; Remote normalized only from an explicit Remote board label",
                                "No independent total or transactional upstream snapshot; full roster reconfirmed; original publication date absent in this template remains unknown",
                                "Full description HTML/text and header metadata retained; supplied salary labels preserved as source text, without inferring pay values from prose",
                            ],
                            "CareerPlug": [
                                "Native app.careerplug.com/accounts/{numeric ID} English public ItemList template only; custom domains, brands, locale and paginated registration unsupported",
                                "Contiguous positions, explicit numberOfItems and full named position selector must agree; empty collections and counts at or above the observed 30-record ceiling abort",
                                "Maximum 29 mandatory native application-page details; ID/title/employer and actual public native form action must match; no form submitted",
                                "Full original ItemList records and each detail JobPosting retained; list/detail descriptions differ in markup and both observations remain available",
                                "Full account metadata reconfirmed after details; salary/publication/employment/location retained when supplied, missing workplace status stays unknown",
                            ],
                            "Kula.ai": [
                                "Native careers.kula.ai public rendered template only; no browser script execution, private API or application submission",
                                "Complete embedded public jobs array must match every unique visible native link; named employer, one account and public visibility flags required",
                                "Maximum 400 mandatory JobPosting details, matching canonical URL/title/employer/identifier and native application controls; final full public roster reconfirmed",
                                "No authoritative independent total or upstream transactional snapshot; empty, changed, hidden, partial or failed collections abort without reconciliation",
                                "All source office locations and supplied publication/workplace/employment/salary metadata retained; form/EEO settings and unresolved Flight description references excluded",
                            ],
                            "Rippling": [
                                "Native ats.rippling.com public Next SSR template only; regional/custom domains and alternate templates unsupported",
                                "Complete unfiltered single-page collection only: explicit page/size/totalItems/totalPages must match all unique UUIDs and visible links; multi-page/empty boards fail closed",
                                "Non-test board identity and every detail UUID/title/company/listed-state/locations/native Apply button must match; full public collection reconfirmed",
                                "All full description sections, structured source workplace/employment labels and supplied pay ranges retained; createdOn remains raw, never substituted for absent datePosted",
                                "Signed asset URLs, candidate/form/EEO configuration and unrelated public state excluded; no browser/challenge execution or private platform API requested",
                            ],
                            "Trakstar": [
                                "Native tenant.hire.trakstar.com complete View-N-Openings template only; pagination beyond first page/custom domains/alternate templates unsupported",
                                "Explicit total must exactly match unique named job paths; at most 400 details; no partial/empty snapshots reconciled",
                                "Each JobPosting native identifier/title/employer/Open Graph URL must match; actual native application form/action and Apply link required",
                                "Source HTML entities/whitespace normalized for comparison and plain text, original schema retained; employment/location/date/salary and explicit workplace label preserved",
                                "Full opening title/metadata map and employer reconfirmed after all details; no candidate form/configuration retained",
                            ],
                            "Freshteam": [
                                "Native freshteam.com full job-role-list HTML plus mandatory JobPosting/native application-form details; custom domains/alternate/paginated templates unsupported",
                                "Maximum 400 details; unique native IDs, list/detail titles, schema host/ID, explicit remote string and native form action must match; full roster reconfirmed",
                                "Source entity-encoded description is decoded once before plain-text extraction; source UTC timestamps parsed explicitly rather than assuming local time",
                                "List location labels retained; potentially inconsistent schema address fields remain raw without inferred geocoding; no original truncated list summary substitutes for full description",
                                "Empty, failed, malformed and changed snapshots abort without closures; no candidate form is submitted or retained",
                            ],
                            "HiringThing": [
                                "Native hiringthing.com public Career Opportunities templates only; same-tenant oasisrecruit.com metadata aliases validated without fetching them; alternate/custom-domain registration unsupported",
                                "Maximum 400 details; complete HTML and RSS path/title sets must agree, and both are reconfirmed after extraction; pagination/empty snapshots unsupported",
                                "Every native detail requires canonical/Open Graph/title agreement and consistent public ApplyButtonGroup job IDs/company/URL/hidden=false",
                                "RSS full media description must match current public job HTML; native career page is the application entry, candidate questions/form/config excluded from raw",
                                "Original posted_at, structured salary fields and explicit remote flag retained; source JobPosting employment metadata retained when supplied",
                            ],
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

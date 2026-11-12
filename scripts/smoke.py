"""Live connector smoke evidence. Does not require a database or Redis."""

import argparse
import asyncio
import hashlib
import json
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

import httpx
from vindex.connectors.registry import create_connector

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = [
    (
        "Phenom People",
        "phenompeople",
        "careers.phenom.com",
        "Phenom",
        "https://careers.phenom.com/global/en/search-results",
    ),
    (
        "Phenom People",
        "phenompeople",
        "careers.bloodcancerunited.org",
        "Blood Cancer United",
        "https://careers.bloodcancerunited.org/us/en/search-results",
    ),
    ("Paradox", "paradox", "flynnrgcareers.com", "Flynn Group", "https://flynnrgcareers.com/"),
    (
        "Paradox",
        "paradox",
        "careers.mwg.aaa.com",
        "AAA Mountain West Group",
        "https://careers.mwg.aaa.com/",
    ),
    (
        "jobboardsoftware.com",
        "exenzo",
        "agconnect.exenzo.nl",
        "AG Connect",
        "https://agconnect.exenzo.nl/",
    ),
    (
        "jobboardsoftware.com",
        "exenzo",
        "vacatures.ecommerce.nl",
        "Twinkle",
        "https://vacatures.ecommerce.nl/vacatures",
    ),
    (
        "Rival",
        "rival",
        "RSCS/Careers",
        "Restaurant Supply Chain Solutions",
        "https://jobs.silkroad.com/RSCS/Careers",
    ),
    (
        "Rival",
        "rival",
        "BlandLandscaping/Careers",
        "Bland Landscaping Company",
        "https://jobs.silkroad.com/BlandLandscaping/Careers",
    ),
    (
        "jobBoardHQ",
        "jobboardhq",
        "jobboardhq.esc17.net",
        "Region 17",
        "https://jobboardhq.esc17.net/search",
    ),
    (
        "jobBoardHQ",
        "jobboardhq",
        "resume.absc.org",
        "Arkansas Baptist State Convention",
        "https://resume.absc.org/search",
    ),
    (
        "ejobsitesoftware.com",
        "ejobsitesoftware_com",
        "seasonaljobs.co.nz",
        "Seasonal Jobs NZ",
        "https://seasonaljobs.co.nz/job-search/",
    ),
    (
        "ejobsitesoftware.com",
        "ejobsitesoftware_com",
        "gurushrconsultancy.com",
        "Gurus HR Consultancy",
        "https://gurushrconsultancy.com/jobboard/job-search/",
    ),
    (
        "BrassRing",
        "brassring",
        "25749-5764",
        "Halifax Regional Municipality",
        "https://sjobs.brassring.com/TGnewUI/Search/home/HomeWithPreLoad?partnerid=25749&siteid=5764&PageType=searchResults",
    ),
    (
        "BrassRing",
        "brassring",
        "25633-5440",
        "Infosys",
        "https://sjobs.brassring.com/TGnewUI/Search/home/HomeWithPreLoad?partnerid=25633&siteid=5440&PageType=searchResults",
    ),
    ("JobBoard.com", "jobboard_com", "jobs.acevo.org.uk", "ACEVO", "https://jobs.acevo.org.uk/"),
    (
        "JobBoard.com",
        "jobboard_com",
        "www.gradsouthwest.com",
        "Gradsouthwest",
        "https://www.gradsouthwest.com/",
    ),
    ("Nodex", "nodex", "www.emotivtech.co.uk", "Emotiv", "https://www.emotivtech.co.uk/search"),
    (
        "Nodex",
        "nodex",
        "www.geckotravelrecruitment.co.uk",
        "Gecko Travel Recruitment",
        "https://www.geckotravelrecruitment.co.uk/search",
    ),
    (
        "WP Job Manager",
        "wp_job_manager",
        "oliver-walters.com",
        "Oliver Walters",
        "https://oliver-walters.com/job-listings/",
    ),
    (
        "WP Job Manager",
        "wp_job_manager",
        "pearlstreetsystems.com",
        "Pearl Street Systems",
        "https://pearlstreetsystems.com/careers/",
    ),
    (
        "SAP SuccessFactors",
        "successfactors",
        "careers.icbc.com",
        "ICBC",
        "https://careers.icbc.com/search/",
    ),
    (
        "SAP SuccessFactors",
        "successfactors",
        "careers.kaust.edu.sa",
        "KAUST",
        "https://careers.kaust.edu.sa/search/",
    ),
    (
        "SmartJobBoard",
        "smartjobboard",
        "americanbath.mysmartjobboard.com",
        "American Bath Group",
        "https://americanbath.mysmartjobboard.com/jobs/",
    ),
    (
        "SmartJobBoard",
        "smartjobboard",
        "jobs.psychologicalscience.org",
        "APS Employment Network",
        "https://jobs.psychologicalscience.org/jobs/",
    ),
    (
        "Niceboard",
        "niceboard",
        "jobs.aiacolorado.org",
        "AIA Colorado",
        "https://jobs.aiacolorado.org/",
    ),
    (
        "Niceboard",
        "niceboard",
        "jobs.medicalalley.org",
        "Medical Alley",
        "https://jobs.medicalalley.org/",
    ),
    (
        "JobKit",
        "jobkit",
        "jobs.rubyonrails.org",
        "Rails Job Board",
        "https://jobs.rubyonrails.org/",
    ),
    ("JobKit", "jobkit", "welpora.jobkit.io", "Welpora", "https://welpora.jobkit.io/"),
    ("JobBoard.io", "jobboardio", "www.nifajobs.com", "NIFA", "https://www.nifajobs.com/"),
    (
        "JobBoard.io",
        "jobboardio",
        "www.cancercareers.org",
        "AACR CancerCareers",
        "https://www.cancercareers.org/",
    ),
    (
        "JBoard.io",
        "jboard",
        "jobs.aame.org",
        "American Association of Municipal Executives",
        "https://jobs.aame.org/jobs",
    ),
    ("JBoard.io", "jboard", "jobs.cisontario.ca", "CIS Ontario", "https://jobs.cisontario.ca/jobs"),
    ("Deel", "deel", "dott", "dott", "https://jobs.deel.com/dott"),
    ("Deel", "deel", "offsec", "Offsec Services", "https://jobs.deel.com/offsec"),
    ("Eightfold AI", "eightfold", "app", "Eightfold", "https://app.eightfold.ai/careers"),
    ("Eightfold AI", "eightfold", "insight", "Insight", "https://insight.eightfold.ai/careers"),
    (
        "Taleo",
        "taleo-tbe",
        "phf.tbe.taleo.net~phf03~GRAYBARCANADA~42",
        "GRAYBAR CANADA",
        "https://phf.tbe.taleo.net/phf03/ats/careers/v2/jobSearch?org=GRAYBARCANADA&cws=42",
    ),
    (
        "Taleo",
        "taleo-tbe",
        "phg.tbe.taleo.net~phg01~GATEWAYVENT~72",
        "OLH Technical Services",
        "https://phg.tbe.taleo.net/phg01/ats/careers/v2/jobSearch?org=GATEWAYVENT&cws=72",
    ),
    (
        "Avature",
        "avature",
        "careers~en_US/main",
        "Avature",
        "https://careers.avature.net/en_US/main/SearchJobs",
    ),
    (
        "Avature",
        "avature",
        "metrobank~amazingcareers",
        "Metrobank",
        "https://metrobank.avature.net/amazingcareers/SearchJobs",
    ),
    (
        "PageUp",
        "pageup",
        "1220~en",
        "Adelaide University",
        "https://careers.pageuppeople.com/1220/cw/en/listing/",
    ),
    (
        "PageUp",
        "pageup",
        "1132~en-us",
        "University of North Dakota",
        "https://careers.pageuppeople.com/1132/cw/en-us/listing/",
    ),
    ("iCIMS", "icims", "careers-iomart", "iomart", "https://careers-iomart.icims.com/jobs/search"),
    (
        "iCIMS",
        "icims",
        "careers-fedwriters",
        "FedWriters, Inc.",
        "https://careers-fedwriters.icims.com/jobs/search",
    ),
    (
        "CSOD",
        "csod",
        "portstephens~1",
        "Port Stephens Council",
        "https://portstephens.csod.com/ux/ats/careersite/1/home?c=portstephens",
    ),
    (
        "CSOD",
        "csod",
        "nswconnect~1",
        "NSW Government",
        "https://nswconnect.csod.com/ux/ats/careersite/1/home?c=nswconnect",
    ),
    (
        "Oracle Recruiting",
        "oracle",
        "eoja.fa.ap1.oraclecloud.com~CX",
        "Hansen Technologies",
        "https://eoja.fa.ap1.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX/jobs",
    ),
    (
        "Oracle Recruiting",
        "oracle",
        "eifn.fa.us6.oraclecloud.com~ExternalCareerSite",
        "Datavail",
        "https://eifn.fa.us6.oraclecloud.com/hcmUI/CandidateExperience/en/sites/ExternalCareerSite/jobs",
    ),
    ("FirstStage", "firststage", "firststage", "First", "https://firststage.firststage.co/jobs"),
    (
        "FirstStage",
        "firststage",
        "quantumbase",
        "Quantum Base",
        "https://quantumbase.firststage.co/jobs",
    ),
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
                    job = batch.jobs[0]
                    if provider in {
                        "brassring",
                        "ejobsitesoftware_com",
                        "jobboardio",
                        "jobboardhq",
                        "rival",
                        "exenzo",
                        "paradox",
                        "phenompeople",
                        "niceboard",
                        "jobkit",
                        "smartjobboard",
                        "jobboard_com",
                        "nodex",
                        "wp_job_manager",
                        "successfactors",
                    }:
                        # Public evidence needs identity and field presence, not copies
                        # of employer descriptions, contact details, or apply queries.
                        sample = {
                            "external_id": job.external_id,
                            "source_url": job.source_url,
                            "title_present": bool(job.title),
                            "company_present": bool(job.company),
                            "description_length": len(job.description),
                            "location_present": bool(job.location),
                            "application_entry": job.raw.get(
                                "application_entry", "Public listing or advertised HTTPS link"
                            ),
                            "quality_flags": job.quality_flags,
                        }
                    else:
                        sample = job.model_dump(mode="json")
                    (ROOT / f"evidence/{provider}-{quote(slug, safe='')}-sample.json").write_text(
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
                            "JobBoard.com": [
                                "Only reviewed ACEVO and Gradsouthwest origins with one complete robots-advertised sitemap; same-origin full job details and application links",
                            ],
                            "Nodex": [
                                "Reviewed Emotiv and Gecko Travel search pages only; exact native total, numbered 10-item pages, duplicate detection and complete roster reconfirmation",
                            ],
                            "WP Job Manager": [
                                "Reviewed Oliver Walters and Pearl Street Systems; native read-only listing query must report a complete single page, with bounded HTTP and reviewed same-origin details",
                            ],
                            "SAP SuccessFactors": [
                                "Reviewed public Career Site Builder portals at ICBC and KAUST, complete single-page unfiltered public search only; canonical full details respect robots and noindex",
                            ],
                            "Phenom People": [
                                "Reviewed locale-specific Phenom public search pages; reads every offset and requires exact ID agreement with the robots-advertised job sitemap.",
                                "Checks every canonical public job detail and repeats the roster. Empty, oversized, changed and partial snapshots fail the refresh.",
                            ],
                            "Paradox": [
                                "Reviewed Career Site Studio public roots; verifies every native result range and matching detail up to 200 jobs, then repeats the roster.",
                                "Keeps the publisher's HTTPS application link without visiting it. Other installations and hosted freshness require separate verification.",
                            ],
                            "Rival": [
                                "Reviewed public SilkRoad employer portals; reads the native page count, validates next controls and reconfirms every job ID and title.",
                                "Mandatory matching detail, native job description and same-job application link. No application form is visited.",
                            ],
                            "jobBoardHQ": [
                                "Reviewed public search forms use unfiltered native pager submissions. Every numbered page and canonical job detail must match.",
                                "Public job detail is the application entry. No application form, saved search or profile is submitted.",
                            ],
                            "jobboardsoftware.com": [
                                "The exact .com vendor domain redirects to Exenzo. The separately branded .io platform is outside scope.",
                                "Reviewed AG Connect and Twinkle boards require an exact nonzero single-page total, every matching public JobPosting and roster reconfirmation.",
                            ],
                            "ejobsitesoftware.com": [
                                "Public source registration is enabled for Gurus HR Consultancy. Seasonal Jobs NZ is smoke-test only while advertised postings redirect.",
                                "Uses bounded public search and mandatory full details. Seasonal search and sitemap must reconcile to the advertised total and remain stable after extraction.",
                                "Point-in-time results do not establish coverage of other installations or hosted continuous operation.",
                            ],
                            "BrassRing": [
                                "Reviewed Halifax and Infosys public portals only. The complete advertised roster must fit in the first response.",
                                "Checks every native detail and reconfirms the full roster. Last-updated dates are preserved separately from original publication dates.",
                            ],
                            "SmartJobBoard": [
                                "Reviewed American Bath Group and APS Employment Network origins only; reads native unfiltered 20-item public search pages and requires exact advertised total",
                                "Reads every full detail and confirms the whole roster again; no backfilled provider pages, private routes or application redirect requests",
                                "Only native same-ID application links and observed supported public apply controls are accepted",
                            ],
                            "Niceboard": [
                                "Public robots-advertised jobs sitemap and same-ID published posting data on the two reviewed board origins; no private API or application-form fetches",
                                "Every job detail checked and whole sitemap roster reconfirmed; explicit filled/expired native state excluded from active jobs; unsupported image-only descriptions reject the run",
                                "Email and hosted form applications use the original public job page; no private board metadata or contact fields retained",
                            ],
                            "JobKit": [
                                "Public HTML on the reviewed Rails and Welpora origins; rendered unfiltered job total must equal unique listing links, reconfirmed after mandatory details",
                                "Only boards whose full advertised roster fits on the first page are supported; unsupported pagination and incomplete details reject the run",
                                "Protected email and HTTP applications use the original public job page; no encoded contact or applicant data retained",
                            ],
                            "JobBoard.io": [
                                "Distinct from JBoard.io; fixed reviewed public origins www.nifajobs.com and www.cancercareers.org, with no arbitrary custom-domain support",
                                "Reads every jobs map advertised in the robots-disclosed public sitemap index and checks every detail and home preview; reconfirms the map roster after details. No independent total is provided, so coverage is scoped to the advertised public job collection",
                                "No access to denied search, private API, candidate forms, profiles or external application destinations",
                                "Uses the visible canonical job detail, employer, title and full description; validates JobPosting when present. Preserves visible original date and employment/remote metadata when JobPosting is absent",
                                "Keeps masked contact placeholders; does not persist plaintext descriptions or HTML with encoded contacts for protected postings",
                                "Same-ID application modals and upstream HTTP destinations use the original HTTPS job page as application entry; original HTTP links are preserved privately",
                                "Point-in-time evidence does not establish all JobBoard.io deployments or hosted production freshness",
                            ],
                            "JBoard.io": [
                                "Distinct from JobBoard.io; supports the public JBoard HTML/JobPosting template on fixed vendor-showcased reviewed origins jobs.aame.org and jobs.cisontario.ca; arbitrary custom domains remain unsupported",
                                "Read robots-advertised sitemap index/job maps only, enumerate every native 30-job list page and require exact ID/URL agreement; no profiles, resumes, account APIs, tracking scripts or application submissions",
                                "Up to 200 mandatory full details, sequential native pages and numbered job maps; all complete maps/list pages are reconfirmed after details; malformed, duplicate, mismatched, failed, redirected or changed data aborts reconciliation",
                                "Every detail binds canonical URL, numeric native ID, title, real employer, full description and same-ID application control; board configuration label never replaces individual hiring organizations",
                                "Native visible location labels are normalized as supplied; potentially inaccurate upstream structured geocoding remains original metadata without guessed correction; salary, employment, remote and original source date/expiry retained when present",
                                "A source expiry already elapsed while the complete roster still lists the role is flagged, not silently dropped or used as immediate closure proof; native posting/apply destinations retained without following application forms",
                                "Bounded supported-site point-in-time evidence does not prove every JBoard installation, arbitrary-domain support or hosted continuous operation",
                            ],
                            "Deel": [
                                "Native jobs.deel.com public rendered boards and mandatory overview JobPosting HTML; no JavaScript execution, candidate/account APIs or application submission",
                                "Full server-rendered jobPostings and SEO ItemList must agree on every UUID; matching employer/settings and published_basic state on the actual board required; full board reconfirmed after up to 200 mandatory details",
                                "No independent total supplied; completeness follows full supported native collection plus SEO roster agreement, not a search-engine sample; custom, empty, changed or unsupported layouts never reconcile",
                                "Every detail must match UUID, employer, title and full native description apart from whitespace/punctuation spacing; preserve full rich text, all locations, employment, workplace and source datePosted without inventing missing metadata",
                                "Only public visible compensation is normalized; no conversion or guessed units; native public posting is application entry; application-form and publication-user identifiers omitted",
                                "Point-in-time supported-template evidence does not establish all Deel deployments or hosted production freshness",
                            ],
                            "Eightfold AI": [
                                "Native tenant.eightfold.ai public careers shells, job sitemap indices/maps and complete JobPosting HTML only; no account/candidate/application API requests or submissions",
                                "Explicit excludePrivatePositions=true required; legacy anonymous seeds must be isPrivate=false and complete sitemap count must equal public board count; up to 200 mandatory full details",
                                "Use robots-advertised job sitemap index when provided; modern native hosts without sitemap declaration use fixed standard public index scoped by shell namespace; robots still enforced on every URL",
                                "Enumerate all native job maps, excluding only explicitly non-job category map/home; reject duplicate IDs, unsafe URLs, malformed XML and wrong employer/namespace; final full maps and shell reconfirmed",
                                "Preserve canonical namespace aliases published in sitemap (Eightfold uses both volkscience.com and eightfold.ai), full source descriptions, all locations, structured salary/employment/workplace and original date strings",
                                "Naive source publication timestamps stay naive with a quality flag; no guessed timezone, location or pay; native posting is the public application entry",
                                "Legacy Insight rejects newer search API with HTTP403; no retries/bypass; connector uses its normal public advertised sitemap and native pages only",
                                "Only observed public HTML/sitemap templates supported; failed/partial/changed collections never reconcile; bounded evidence does not establish hosted production freshness",
                            ],
                            "Taleo": [
                                "Oracle Taleo Business Edition native TBE v2 public org/CWS boards only; distinct from Oracle Recruiting Cloud; Enterprise Taleo and other/custom templates unsupported",
                                "Fixed validated TBE pod/host/org/site scope; unfiltered ten-job public pages with native next offsets, unique IDs up to 200 and complete final enumeration; optional Positions Matched total enforced when provided",
                                "Every native full detail requires listed title, scoped same-ID Apply control, complete full HTML body and location; JobPosting identifier/url/full text required to agree when structured metadata is supplied",
                                "Some public TBE templates omit JobPosting entirely; preserve full native body/brief, explicit metadata and configured employer with source flags; do not fabricate absent publication/pay/employment/workplace",
                                "Public Job Code may differ from stable RID; preserve both; preserve original ISO and explicit GMT Java date formats, flag timezone when source timestamp omits it instead of inventing UTC",
                                "Closed or moved roles can return HTTP200 with no job/apply body; reject mandatory unavailable details and never reconcile a failed/partial snapshot; no login/application/employee API requests or submissions",
                                "Known TIMESTAMP_DEMO2 org rejected; fixtures/vendor demos never count; bounded point-in-time evidence does not establish all Taleo editions or hosted production freshness",
                            ],
                            "Avature": [
                                "Native tenant.avature.net public SearchJobs portals, modern article--jobs and classic results layouts only; no internal/employee/referral portals, private APIs or application requests",
                                "Explicit six-item result ranges and total up to 200 jobs, unique scoped IDs and every page/detail required; entire board brand/roster reconfirmed after extraction",
                                "Modern canonical/title/native employer/location/category and every full description article required; absent structured publication/pay/employment/workplace remain unknown",
                                "Classic native visible title/ref/team/closing metadata and same-ID RegisterMethod must agree; full native body equals JobPosting text except whitespace; original structured metadata retained",
                                "Classic SEO title can differ from public display title: preserve the matching list/full visible title, original SEO title and structured_title_differs flag; never silently rewrite titles",
                                "Source list may omit location; use only provided full metadata/structured addresses and flag omission; no title/prose geolocation guesses; list-only Starting Salary From text retained without guessed currency or units",
                                "Full original benefits/requirements/footer description sections retained; no preview substitution, scripts executed, login, application or candidate state requested; failed/empty/partial/changed sources never reconcile",
                                "Point-in-time coverage of observed layouts; custom or alternate portals unsupported, continuous hosted freshness not established",
                            ],
                            "PageUp": [
                                "Native careers.pageuppeople.com numeric tenant/cw/en or en-us listing template only; custom/mobile/other-site templates unsupported",
                                "Both native current and unfiltered-search widgets must agree exactly; 20-item pages plus explicit More Jobs remaining counter, up to 200 mandatory details, complete final roster reconfirmed",
                                "Every detail must bind canonical URL, title, locations and closing metadata to listed job and native secure.dcN.pageuppeople.com apply URL for identical tenant/job; no apply page requested or submitted",
                                "Human external requisition number may differ from numeric URL ID (e.g. H498332); preserve both without coercion or loss of source identity",
                                "Full native job-details HTML/text, source salary/remuneration labels, work type, location, Advertised datetime and closing observations preserved; missing structured workplace remains unknown",
                                "Employer explicitly supplied by source configuration and flagged; source pay text is preserved without guessing currency or units; empty/failed/partial/changed snapshots abort without closures",
                                "Bounded point-in-time coverage does not establish all PageUp templates or hosted production freshness",
                            ],
                            "iCIMS": [
                                "Classic native tenant.icims.com public iframe search and JobPosting detail template only; no authenticated Job Portal/Profile APIs, applications or candidate state",
                                "Enumerate every explicit Page N of M, 50 jobs on nonfinal pages, at most 8 pages; unique scoped IDs and entire roster reconfirmed after mandatory details",
                                "No independent total is supplied; completeness follows full native page enumeration and final reconfirmation; empty/malformed/changed snapshots never reconcile closures",
                                "Full native description sections including sibling platform headings and nested rich text must agree with JobPosting apart from whitespace; preserve salary sections, all locations, employment and explicit Work Site labels",
                                "Source jobPosting datePosted retained as provided with provenance; it is not independently verified as original publication and some deployments emit apparently generated/stale dates",
                                "Native Apply control verified without requesting/submitting it; stable original public posting is application entry; rotating hashed control parameter never retained",
                                "Explicit PRACTICE postings that state no real job/no hire are fully fetched and validated, retained as excluded metadata with source link/checksum, and never counted as jobs",
                                "Single source employer identity required across all details; custom/alternate templates and mixed-brand boards unsupported; bounded evidence does not establish production freshness",
                            ],
                            "CSOD": [
                                "Native tenant.csod.com /ux/ats/careersite/{id}/home public anonymous context and supported English cultures only; custom templates/new cloud search services unsupported",
                                "Negative anonymous browser identity must equal active site configuration; native public token stays in request-scoped memory and is never retained in jobs/evidence/log URLs",
                                "Native career-site v1 search with explicit unfiltered request, total and 25-job pages; all pages enumerated up to 200 mandatory jobs and final full roster/site reconfirmed",
                                "Each job requires matching public detail and complete native advertisement: externalDescription may only say default; failed or incomplete advertisements abort without reconciliation",
                                "Application URL may identify another public career site within same tenant for the identical job ID; preserve original source and advertised application links without requesting/submitting forms",
                                "All public native locations, full ad including source pay/employment text, original culture-formatted postingEffectiveDate preserved; employer explicitly supplied by source configuration and flagged",
                                "Structured pay/employment/workplace normalization not provided by this template; missing values remain unknown; owners/reviewers/hiring-manager IDs and tracking/session state excluded",
                                "Bounded point-in-time coverage does not establish production freshness or every CSOD deployment",
                            ],
                            "Oracle Recruiting": [
                                "Native English Oracle Fusion Candidate Experience sites only, fixed validated oraclecloud.com host families; custom domains and other Oracle/Taleo products remain distinct",
                                "Only anonymous public native-client advertised CE search and listed-ID detail routes; no ICE/internal-candidate, preview, employee, application, resume or account endpoints",
                                "Active public site metadata and complete unfiltered search total required, 100 jobs/page up to 400 mandatory details; all pages and site metadata reconfirmed",
                                "Full external description/responsibilities/qualifications/company sections, explicit workplace/employment/original publication, secondary and native work locations retained; contact/hiring-manager/internal text excluded",
                                "Absent native SEO employer uses explicitly supplied source company with company_from_source_configuration flag; never guess from prose/domain; source display/legal names may differ",
                                "Pay embedded in full descriptions and public custom fields preserved; no guessed currency, amounts or units; custom-field salary normalization remains unsupported",
                                "Only roster-listed IDs requested, regardless of ApplyWhenNotPostedFlag; missing/failed/changed/partial snapshots abort without closures; bounded evidence is not production freshness",
                            ],
                            "FirstStage": [
                                "First/FirstStage native tenant.firststage.co/jobs SSR unfiltered list template only; custom/alternate templates unsupported",
                                "Require explicit unique-job total equal native IDs; identical multi-location group copies deduplicated only within this source; conflicting copies rejected; maximum 400 mandatory details",
                                "Every detail must match native title, company, location and advertised labels, JobPosting directApply URL, native metadata and public application upload controls",
                                "Complete HTML description must agree with structured JobPosting; salary display text, original structured pay/incentives, datePosted and each native location preserved",
                                "No application uploaded/submitted, scripts executed, or account/candidate data retained; final full board reconfirmed; failed/partial snapshots never reconcile",
                                "Bounded point-in-time coverage; no transactional upstream snapshot or production freshness guarantee",
                            ],
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

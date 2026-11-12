# Coverage-first workflow

**Latest owner release requirements (November 7):** read [PRODUCTION_RELEASE_REQUIREMENTS.md](PRODUCTION_RELEASE_REQUIREMENTS.md). Coverage remains first. Public launch now requires a verified custom domain on the free-tier plan, favicon, permitted badge removal, reviewed legal/privacy pages, accessibility and a full security review. Older preview-only vercel.app guidance does not authorize launch. No spending or automatic deployment is authorized.

The owner has set the next priority: finish all 78 required live platform verifications before expanding the remaining backend/product work. Start with the largest gap: 19 job-board platforms; 14 ATS platforms also remain at the 45/78 baseline. A parser, fixture, blocked request, empty board or partial roster does not count. Preserve failed evidence and the acquisition acceptance criteria.

Work and commit locally in substantive batches. Push reviewed changes no more frequently than once per 12 hours, measured from the last successful push. Use the most recent successful main push to compute the next eligible window. Do not push early or create empty commits just to fill a window. This is a working cadence, not an unattended push automation.

Update the provider matrix, dated live evidence and connector contract as each platform qualifies. In parallel, note additive source URL/API behavior in the frontend handoff; do not change public UI copy to show development diagnostics or hardcoded counts.

Antigravity's frontend implementation is present in the existing `feat/frontend` worktree at `66baef8`, on top of the earlier account/profile/resume/recommendation work. Its commit reports 166 browser tests passed. Preserve its work; reported test output is distinct from independent verification and hosted acceptance. No automatic merge, push or deployment follows from a completed implementation report. Review integration in the proper release batch.

Existing account functionality includes signup, sign-in, session restoration, profile, resume controls, recommendations and logout. Preserve it while working on coverage; the remaining identity/recovery/privacy/hosting gates still apply. The Free/Plus price catalogue is already implemented. No payment provider is connected; do not simulate checkout or grant paid access from the browser. Real billing, remaining backend hardening and hosted validation follow the coverage milestone unless a necessary correctness/security fix arises during connector work.

November 7: JBoard.io passed formal runs on two independent reviewed boards (AAME 30 jobs, CIS Ontario 48), bringing the matrix to 46/78: 44 ATS and two job-board platforms. Remaining: 14 ATS and 18 job-board platforms. The earlier 45/78 figure above is the start-of-pass baseline.

JobBoard.io then passed clean live runs on NIFA (2 jobs) and AACR CancerCareers (61), using their advertised public job sitemaps. The verified total is **47/78**: 44 ATS and three job-board platforms. **31 remain:** 14 ATS and 17 job-board platforms. Review evidence and supported scope are in [COVERAGE.md](COVERAGE.md) and [CONNECTOR_CONTRACT.md](CONNECTOR_CONTRACT.md).

November 8: Niceboard, JobKit and SmartJobBoard each passed complete runs on two independent boards. The requested **50/78** milestone passed, with 44 ATS and six job-board platforms verified. **28 remain**, split evenly between ATS and job-board platforms. See the [coverage matrix](COVERAGE.md) and [connector contract](CONNECTOR_CONTRACT.md).

November 8 integration review: the independently verified total is **54/78** after accepting JobBoard.com, Nodex, WP Job Manager and SAP SuccessFactors. The remaining 24 are 13 ATS and 11 job-board platforms. See the [backend review](ANTIGRAVITY_BACKEND_REVIEW_2026-11-08.md).

November 12: BrassRing passed on Halifax Regional Municipality (33 jobs) and Infosys (10 jobs), bringing coverage to **55/78**. **23 remain**, including 12 ATS and 11 job-board platforms. Both reviewed portals returned their full advertised roster in one page. [Live evidence](../evidence/20261112T151441Z-smoke.json)

November 12: ejobsitesoftware.com returned all seven Gurus HR Consultancy jobs. Seasonal Jobs NZ advertised 166 results, with 161 unique search IDs and 161 sitemap job URLs. Five distinct jobs were exclusive to each surface. The five search-only jobs had a November 12 expiration in their public previews and their detail requests each returned HTTP 302. The live run rejected the incomplete snapshot. Coverage remains **55/78**. Retry Seasonal after its advertised roster stops including the redirecting jobs, or verify another independent vendor-listed board. [Live evidence](../evidence/20261112T153800Z-smoke.json)

November 12: Rival passed on Restaurant Supply Chain Solutions (2 jobs) and Bland Landscaping Company (43). jobBoardHQ passed on Region 17 (47) and Arkansas Baptist State Convention (152). Both providers verified complete public rosters and matching job details. Coverage reached **57/78**, with 11 ATS and 10 job-board platforms remaining. [Live evidence](../evidence/20261112T155152Z-smoke.json)

November 12: jobboardsoftware.com (Exenzo) passed on AG Connect (3 jobs) and Twinkle (1). Coverage reached **58/78**, with 11 ATS and nine job-board platforms remaining. The owner deferred ejobsitesoftware.com until the final coverage pass. [Live evidence](../evidence/20261112T155429Z-smoke.json)

November 12: Paradox Career Site Studio passed on Flynn Group (12 jobs) and AAA Mountain West Group (108), bringing coverage to **59/78**. The connector verified all 2 and 11 result pages respectively, then confirmed each full roster after reading the details. [Live evidence](../evidence/20261112T161102Z-smoke.json)

November 12: Phenom People passed on the vendor's own live recruiting site (78 jobs across 8 pages) and Blood Cancer United (51 across 6 pages). The connector independently reconciled all result IDs against each public job sitemap and read every canonical detail. The vendor's site supplied two explicitly blank descriptions and seven structured titles that differed from the native posting title. These are flagged. Coverage reached **60/78**. [Live evidence](../evidence/20261112T162429Z-smoke.json)

November 13 IST: JobBoardFire passed on Trellis (18 jobs) and Launch Pad Job Club (6). The first Trellis run encountered HTTP 429. The slower retry confirmed both public rosters and every canonical detail. Coverage reached **61/78**, with nine ATS and eight job-board platforms remaining. [Live evidence](../evidence/20261112T203739Z-smoke.json)

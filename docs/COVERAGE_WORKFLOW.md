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

November 13 IST: JobMount and Wiley Madgex exposed native page-two routes, but the examined RSS feeds cover only a subset of the advertised rosters. National Diversity Network also repeats five posting IDs across the first two pages. Jobiqo's LoveLocalJobs advertised 1,551 jobs, and the Bookseller route examined is a featured collection. Further coverage requires two complete, independently verified collections per platform. Verified coverage remains **61/78**. [Public source discovery](../evidence/20261112-public-roster-discovery.json)

November 13 IST: The public Wiley Madgex listing audit reconciled 523 Science Careers IDs across 27 pages and 1,166 Nature Careers IDs across 59 pages. These are listing audits. Full canonical detail extraction and roster reconfirmation are still required, so verified coverage remains **61/78**. Reproduce the listing audit with `PYTHONPATH=backend uv run python scripts/audit_madgex_rosters.py`. [Listing evidence](../evidence/20261113-madgex-public-rosters.json)

November 13 IST: The staged Wiley Madgex smoke run saved 30 Science Careers details and 10 Nature Careers details before both sources returned HTTP 502 after bounded retries. The worker persists progress and requires a complete snapshot and a matching final roster before reconciliation. Source registration awaits successful verification. Verified coverage remains **61/78**. Retry after upstream cooldown with `PYTHONPATH=backend uv run python scripts/smoke_madgex.py --checkpoint-directory .cache/madgex-smoke`. Reuse the original checkpoint directory to resume within its six-hour snapshot window. [Staged run evidence](../evidence/20261113-madgex-staged-smoke.json)

November 13 IST: Jobiqo discovery reconciled all 99 Agrajo listing IDs across nine pages. LoveLocalJobs advertised 1,551 jobs and returned 20 unique posting paths on its first two pages. Each site returned a canonical posting and a structured description in its sampled detail. Agrajo uses numeric card IDs that may be absent from detail slugs. Full canonical extraction, application handling and final roster reconciliation remain pending. [Jobiqo discovery evidence](../evidence/20261113-jobiqo-public-rosters.json)

Owner priority, November 13 IST: Put Wiley Madgex, JobMount, talentReef, Gem.com and ejobsitesoftware.com on hold until the other 12 remaining platforms have been addressed. Work on one new platform at a time, starting with Jobiqo. Revisit the deferred five with approaches suited to their specific access, pagination and completeness issues. Preserve the live verification and closure requirements.

November 13 IST: Jobiqo is implemented for Agrajo and United Way. Agrajo passed with all 99 jobs and a matching final roster. The United Way adapter verified a sample external description against the publisher's structured job ID and title, but the full run hit the standard 600-second refresh limit. Jobiqo remains unverified overall and coverage remains **61/78**. The next pass should measure per-origin request timing and evaluate reusing the robots policy within a run and checkpointing detail progress under the existing worker lease. Keep the final full roster reconciliation. [Live evidence](../evidence/20261112T214757Z-smoke.json)

November 13 IST: The checkpointed United Way run saved 59 of 67 jobs before reaching posting 5152. A later full listing read still included 5152 in a roster of 66. Its publisher returned an error page without structured job data on repeated checks. The run did not reconcile or publish. Kampajobs is another candidate: the public board advertised 124 jobs, exposed numbered pages, showed 20 distinct same-origin posting URLs on page one, and returned a canonical link on the sampled detail. Full indexing there remains unverified. Coverage stays **61/78**.

Owner target, November 13 IST: Implement and live-verify nine additional platforms, targeting **70/78** from the verified baseline of **61/78**. Keep the five previously deferred platforms for the final pass.

Kampajobs now uses the Jobiqo worker's existing checkpoint table. Its numbered public pager starts with `?page=1` for page two. The live worker reconciled 124 distinct advertised postings before reading details. The first pass stopped on a volunteer listing with explicit email instructions, and the connector now preserves the original posting as the application entry for that format. The resumed run must still read all details and reconfirm the roster. Dayforce's two sampled public career shells loaded, while four requests to the previously examined search endpoint returned HTTP 403. The ADP Findel public career shell loaded. Neither ATS probe established a complete roster.

November 13 IST: ADP MyJobs passed on Signature Performance (21 jobs) and WesBanco (178 jobs). Both complete runs reconfirmed the paginated requisition roster after detail extraction. Verified coverage reached **62/78**. [Live evidence](../evidence/20261113T073432Z-smoke.json)

November 13 IST: Kampajobs resumed from 50 of 124 saved details and reached 55 before another application-link variant. The adapter now recognizes the observed recruiting-tool link, an explicitly labeled link in the description, and the Onlineportal label. The latest checkpoint still requires complete details and a matching final roster. Two HiBob-hosted candidate shells loaded, but the assets origin returned HTTP 403 for robots.txt. UCC Environmental's linked Paycom career page loaded, while the separate listings path was disallowed by robots. These source checks add no verified coverage.

November 13 IST: Kampajobs saved 65 of 124 details. The linked Publicjobs template now validates the publisher posting ID and title, extracts its full description, and keeps its application URL. A separate roster read rejected inconsistent pagination. Full reconciliation is still pending. Dayforce documents an anonymous JobFeeds endpoint, but the documented host's robots policy disallowed the feed route for all six checked tenant paths. No feed requests were sent. [Dayforce JobFeeds documentation](https://help.dayforce.com/r/documents/Dayforce-Web-Services-Introduction-Guide/RESTful-Get-Job-Feeds)

November 13 IST: The original Kampajobs checkpoint reached 103 of 124 details before a public posting returned HTTP 404. That run did not publish. A fresh roster run was started. When a detail returns 404, the worker now discards its checkpoint only if a new complete roster confirms a change. Existing index records still follow the normal closure policy. The verified platform count remains **62/78**.

November 13 IST: The next coverage pass includes Dayforce, Dover, HiBob, Paycom, Paycor, UltiPro, Talenetic, CareerSiteCloud, Artha, eJobBoard and Jobiqo. Completing all eleven would bring the matrix to **73/78**. The five previously deferred platforms follow this pass.

A fresh Kampajobs roster reconciled 123 distinct postings across seven pages, and a new checkpointed detail run was started. For Artha, the vendor identifies EduJobs India and AnalyticsHiring as customers. EduJobs India and DataAIJobs, linked from AnalyticsHiring, exposed public job sitemaps with 13,346 and 2,274 URLs respectively. The sampled posting detail on each returned HTTP 403, so neither yielded a verified snapshot. [Artha customer case studies](https://arthajobboard.com/casestudy/)

November 13 IST: Kampajobs passed with 123 complete job details and a matching final roster. The run resumed across connector revisions as additional application formats were added. Together with Agrajo's 99-job pass, this brings verified coverage to **63/78**. Four anonymous HiBob tenant API requests returned HTTP 401. The tested eJobBoard .co.uk domain failed DNS and the .com home page pointed to a lander. [Kampajobs run](../evidence/20261113T100128Z-jobiqo-checkpoint.json)

November 13 IST: HiBob passed on Oseyo (7 jobs) and eCarsTrade (11 jobs), bringing coverage to **64/78**. The career feed accepts the public tenant name as its company identifier. Both runs read the entire published collection twice and required identical normalized postings. [Live evidence](../evidence/20261113T100332Z-smoke.json)

November 13 IST: The next live verification remains open at **64/78**. The Paycor host policy also disallows the public career paths linked by reviewed employers. Three reachable UltiPro host variants disallow the reviewed search route. Dover documents employer-authorized career postings access on ATS Premium; no tenant authorization was available for a live check. [Dover API overview](https://docs.dover.com/api/)

November 13 IST: Switched the next verification effort to CareerSiteCloud. Aspen's product profile names GroupM, LEO Pharma, Amedisys and Multiemplois as customers. The current WPP Media and LEO Pharma pages exposed Greenhouse and SuccessFactors markers respectively. Amedisys returned a redirect, and Multiemplois failed hostname certificate validation. Both CareerSiteCloud vendor host variants returned HTTP 403 on policy lookup. This did not establish an active CareerSiteCloud roster. [Aspen product profile](https://www.linkedin.com/products/aspen-technology-labs-inc-careersitecloud/)

The recovery plan below follows the latest live evidence. A documented interface is a lead until two independent sites pass complete runs.

| Platform | Next verification step |
|---|---|
| Dayforce | Obtain an employer-published mirror or approved JobFeeds route. The documented default host disallowed the tested feed paths. |
| Dover | Use the published-job-postings API with employer-issued ATS Premium access, or validate a complete employer-published careers feed. |
| Paycom | Check for an employer-provided full export. The sampled public shell and restricted roster route did not establish completeness. |
| Paycor | Verify a permitted employer feed or obtain approved integration access and confirm it covers public postings. |
| UltiPro | Verify a UKG-approved employer feed that includes the full active roster and original links. |
| Talenetic | Obtain the board owner's outbound XML job feed and reconcile it against the public count. |
| CareerSiteCloud | Confirm currently active customer installations and documentation for their outbound feeds. |
| eJobBoard | Ask the challenge host for current vendor and installation URLs. The tested domains yielded a lander and a DNS failure. |
| Wiley Madgex | Revisit checkpointed public detail extraction with bounded retries, or obtain complete exports from the publishers. |
| JobMount | Prefer a complete outbound feed or reconcile the native pager. The observed RSS feeds cap at 100 entries. |
| talentReef | Confirm a licensed or explicitly public route, then verify full pagination and detail coverage. |
| Gem.com | Retest the vendor-documented Job Board API on permitted, verified tenants. Prior probes returned HTTP 403. |
| ejobsitesoftware.com | Keep Gurus HR as the passing example and verify a second active board via its supported listing or export interface. |

The existing HTTP client retries 429 and 5xx within a bounded budget. Automatic refreshes now preserve the upstream Retry-After deadline if it exceeds the normal retry schedule. A failed run leaves the last complete index in place.

November 13 IST: Talenetic's Pro Contract Jobs publishes a robots-advertised sitemap index. Its four job maps returned 36,395 distinct URL entries, including the homepage. The listed same-origin URLs passed the robots policy check. Sampled detail pages exposed visible titles and application controls, while the sampled JSON-LD did not contain JobPosting objects. Sitemap counts alone do not establish the current active roster. Medical Update Jobs Online's root was disallowed, OilFinity returned a redirect, and TopEngineer timed out. A full outbound XML export from the board owner and a second reachable board remain the clearest paths to a verified run. [Talenetic XML feed capability](https://www.talenetic.com/features/)

Artha passed complete live runs on LexPath (11 jobs) and Joberly (113 jobs), bringing verified coverage to **65/78**. Both runs checked each posting against the board's sitemap, verified the published active flag and application entry, and reread the sitemap after extraction. Three Joberly postings advertised same-origin canonical aliases. [Live evidence](../evidence/20261113T151732Z-smoke.json)

November 13 IST: Follow-up checks left verified coverage at **65/78**. The alternate Dayforce host returned HTTP 403 for the YMCA Santa Monica and Project Renewal feed paths, which passed its robots check. Both reviewed Paycom employer pages exposed application links or an embedded ATS page, with no complete employer-side roster. Amedisys's current jobs page exposed iCIMS and Jibe assets. The Pro Contract Jobs filtered RSS link was disallowed and was skipped. The eJobBoard UK domain and its www variant failed DNS resolution again, while the .com origin returned a parking shell. [Source check evidence](../evidence/20261113-public-source-followup.json)

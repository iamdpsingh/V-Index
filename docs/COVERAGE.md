# Provider coverage

Exactly 58 ATS + 20 job-board platforms. Risk is a planning estimate, not a verified access limitation.

IMPLEMENTED means code exists. LIVE_VERIFIED means the latest smoke run retrieved non-empty, complete jobs for all configured example tenants. This is a point-in-time connector check, not full production acceptance. FAILED and BLOCKED retain genuine limitations. NOT_STARTED providers have no connector.

| Platform | Kind | Implementation | Evidence | Risk | Count (sum) | Last run | Examples / failures |
|---|---|---|---|---|---|---|---|
| ADP | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| ApplicantPro | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Ashby | ats | IMPLEMENTED | LIVE_VERIFIED | LOW | 243 | 2026-11-05T16:42:19.453089+00:00 | https://jobs.ashbyhq.com/Ashby (72; LIVE_VERIFIED); https://jobs.ashbyhq.com/ramp (171; LIVE_VERIFIED)  |
| Avature | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| BambooHR | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| BrassRing | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| Breezy HR | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| CareerPlug | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Comeet | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| CSOD | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| Dayforce | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| Deel | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Dover | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Eightfold AI | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| FirstStage | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Freshteam | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Gem.com | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| GoHire | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Greenhouse | ats | IMPLEMENTED | LIVE_VERIFIED | LOW | 1226 | 2026-11-05T16:41:54.721525+00:00 | https://job-boards.greenhouse.io/stripe (762; LIVE_VERIFIED); https://job-boards.greenhouse.io/cloudflare (464; LIVE_VERIFIED)  |
| HiBob | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| HireBridge | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| HireHive | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Hireology | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| HiringThing | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| iCIMS | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| iSolvedHire | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| JazzHR | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Jobvite | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| JOIN.com | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Kula.ai | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Lever.co | ats | IMPLEMENTED | LIVE_VERIFIED | LOW | 394 | 2026-11-05T16:42:17.172545+00:00 | https://jobs.lever.co/spotify (87; LIVE_VERIFIED); https://jobs.lever.co/palantir (307; LIVE_VERIFIED)  |
| Manatal | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Oracle Recruiting | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| PageUp | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Paradox | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| Paycom | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| Paycor | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Paylocity | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Personio | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 51 | 2026-11-05T16:44:39.531738+00:00 | https://matrix42.jobs.personio.de (34; LIVE_VERIFIED); https://planqc-gmbh.jobs.personio.de (17; LIVE_VERIFIED)  |
| Phenom People | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| Pinpoint | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Polymer | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Recooty | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Recruitee | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Rippling | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Rival | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| SAP SuccessFactors | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| SmartRecruiters | ats | IMPLEMENTED | FAILED | MEDIUM | 2 | 2026-11-05T16:44:34.345767+00:00 | https://careers.smartrecruiters.com/SmartRecruiters (2; LIVE_VERIFIED); https://careers.smartrecruiters.com/Colliers (0; FAILED) ValueError: Posting detail has no job description |
| talentReef | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Taleo | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| Teamtailor | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Trakstar | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| TriNet | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| UltiPro | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| WeRecruit | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Workable | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Workday | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| Zoho Recruit | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Niceboard | job_board | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| WP Job Manager | job_board | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| JobKit | job_board | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| Jobboardly | job_board | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| Jobiqo | job_board | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| JBoard.io | job_board | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| JobBoardFire | job_board | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| SmartJobBoard | job_board | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| JobBoard.io | job_board | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| Wiley Madgex | job_board | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| Talenetic | job_board | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| JobMount | job_board | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| CareerSiteCloud | job_board | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| JobBoard.com | job_board | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| Artha | job_board | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| jobboardsoftware.com | job_board | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| jobBoardHQ | job_board | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| Nodex | job_board | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| eJobBoard | job_board | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| ejobsitesoftware.com | job_board | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |

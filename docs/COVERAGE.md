# Provider coverage

Exactly 58 ATS + 20 job-board platforms. Risk is a planning estimate, not a verified access limitation.

IMPLEMENTED means code exists. LIVE_VERIFIED means the latest smoke run retrieved non-empty, complete jobs for all configured example tenants. This is a point-in-time connector check, not full production acceptance. FAILED and BLOCKED retain genuine limitations. NOT_STARTED providers have no connector.

| Platform | Kind | Implementation | Evidence | Risk | Count (sum) | Last run | Examples / failures |
|---|---|---|---|---|---|---|---|
| ADP | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| ApplicantPro | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Ashby | ats | IMPLEMENTED | LIVE_VERIFIED | LOW | 243 | 2026-11-05T16:42:19.453089+00:00 | https://jobs.ashbyhq.com/Ashby (72; LIVE_VERIFIED); https://jobs.ashbyhq.com/ramp (171; LIVE_VERIFIED)  |
| Avature | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| BambooHR | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 25 | 2026-11-06T03:18:07.998376+00:00 | https://anaergia.bamboohr.com/careers (20; LIVE_VERIFIED); https://concept2.bamboohr.com/careers (5; LIVE_VERIFIED)  |
| BrassRing | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| Breezy HR | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 81 | 2026-11-06T03:16:14.203649+00:00 | https://vald.breezy.hr (75; LIVE_VERIFIED); https://subscribe.breezy.hr (6; LIVE_VERIFIED)  |
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
| GoHire | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 45 | 2026-11-06T07:43:13.012881+00:00 | https://jobs.gohire.io/dineamic-hospitality-fniota1h/ (22; LIVE_VERIFIED); https://jobs.gohire.io/digital-shift-o0hrqw5o/ (23; LIVE_VERIFIED)  |
| Greenhouse | ats | IMPLEMENTED | LIVE_VERIFIED | LOW | 1226 | 2026-11-05T16:41:54.721525+00:00 | https://job-boards.greenhouse.io/stripe (762; LIVE_VERIFIED); https://job-boards.greenhouse.io/cloudflare (464; LIVE_VERIFIED)  |
| HiBob | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| HireBridge | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| HireHive | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 65 | 2026-11-06T06:55:14.734024+00:00 | https://amcsgroup.hirehive.com (59; LIVE_VERIFIED); https://echelon-dc.hirehive.com (6; LIVE_VERIFIED)  |
| Hireology | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| HiringThing | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| iCIMS | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| iSolvedHire | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| JazzHR | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 119 | 2026-11-06T03:41:01.947707+00:00 | https://lapmasterwolters.applytojob.com/apply (6; LIVE_VERIFIED); https://belaytechnologies.applytojob.com/apply (113; LIVE_VERIFIED)  |
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
| Personio | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 51 | 2026-11-05T16:49:55.782699+00:00 | https://matrix42.jobs.personio.de (34; LIVE_VERIFIED); https://planqc-gmbh.jobs.personio.de (17; LIVE_VERIFIED)  |
| Phenom People | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| Pinpoint | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 49 | 2026-11-06T03:20:57.181056+00:00 | https://intermedia.pinpointhq.com (43; LIVE_VERIFIED); https://workwithus.pinpointhq.com (6; LIVE_VERIFIED)  |
| Polymer | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Recooty | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Recruitee | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 29 | 2026-11-06T01:42:58.731786+00:00 | https://natilik.recruitee.com (6; LIVE_VERIFIED); https://bunq.recruitee.com (23; LIVE_VERIFIED)  |
| Rippling | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Rival | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| SAP SuccessFactors | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| SmartRecruiters | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 90 | 2026-11-05T16:49:50.960317+00:00 | https://careers.smartrecruiters.com/SmartRecruiters (2; LIVE_VERIFIED); https://careers.smartrecruiters.com/Colliers (88; LIVE_VERIFIED)  |
| talentReef | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Taleo | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| Teamtailor | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 26 | 2026-11-06T03:09:11.551818+00:00 | https://clearroute.teamtailor.com (22; LIVE_VERIFIED); https://omny.teamtailor.com (4; LIVE_VERIFIED)  |
| Trakstar | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| TriNet | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| UltiPro | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| WeRecruit | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Workable | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 4 | 2026-11-06T03:14:41.352483+00:00 | https://apply.workable.com/careers/ (1; LIVE_VERIFIED); https://apply.workable.com/learnworlds/ (3; LIVE_VERIFIED)  |
| Workday | ats | IMPLEMENTED | LIVE_VERIFIED | HIGH | 43 | 2026-11-06T01:43:52.166289+00:00 | https://imf.wd5.myworkdayjobs.com/IMF (14; LIVE_VERIFIED); https://gatesfoundation.wd1.myworkdayjobs.com/Gates (29; LIVE_VERIFIED)  |
| Zoho Recruit | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Niceboard | job_board | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| WP Job Manager | job_board | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| JobKit | job_board | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| Jobboardly | job_board | IMPLEMENTED | FAILED | HIGH | 31 | 2026-11-06T03:56:21.828213+00:00 | https://recruiter-jobs.jobboardly.com/jobs (31; LIVE_VERIFIED); https://pennsylvania-communications.jobboardly.com/jobs (0; FAILED) ValueError: JobBoardly exceeds 400-detail budget; snapshot incomplete |
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

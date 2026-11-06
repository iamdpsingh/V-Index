# Provider coverage

Exactly 58 ATS + 20 job-board platforms. Risk is a planning estimate, not a verified access limitation.

IMPLEMENTED means code exists. LIVE_VERIFIED means the latest smoke run retrieved non-empty, complete jobs for all configured example tenants. This is a point-in-time connector check, not full production acceptance. FAILED and BLOCKED retain genuine limitations. NOT_STARTED providers have no connector.

| Platform | Kind | Implementation | Evidence | Risk | Count (sum) | Last run | Examples / failures |
|---|---|---|---|---|---|---|---|
| ADP | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| ApplicantPro | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 5 | 2026-11-06T08:53:36.755511+00:00 | https://farbank.applicantpro.com/jobs/ (2; LIVE_VERIFIED); https://clarke.applicantpro.com/jobs/ (3; LIVE_VERIFIED)  |
| Ashby | ats | IMPLEMENTED | LIVE_VERIFIED | LOW | 243 | 2026-11-05T16:42:19.453089+00:00 | https://jobs.ashbyhq.com/Ashby (72; LIVE_VERIFIED); https://jobs.ashbyhq.com/ramp (171; LIVE_VERIFIED)  |
| Avature | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| BambooHR | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 25 | 2026-11-06T03:18:07.998376+00:00 | https://anaergia.bamboohr.com/careers (20; LIVE_VERIFIED); https://concept2.bamboohr.com/careers (5; LIVE_VERIFIED)  |
| BrassRing | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| Breezy HR | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 81 | 2026-11-06T03:16:14.203649+00:00 | https://vald.breezy.hr (75; LIVE_VERIFIED); https://subscribe.breezy.hr (6; LIVE_VERIFIED)  |
| CareerPlug | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 10 | 2026-11-06T12:34:45.510649+00:00 | https://app.careerplug.com/accounts/576036 (2; LIVE_VERIFIED); https://app.careerplug.com/accounts/579908 (8; LIVE_VERIFIED)  |
| Comeet | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 33 | 2026-11-06T17:26:30.311458+00:00 | https://www.comeet.com/jobs/oriient/EA.005 (7; LIVE_VERIFIED); https://www.comeet.com/jobs/webbing/46.00E (26; LIVE_VERIFIED)  |
| CSOD | ats | IMPLEMENTED | LIVE_VERIFIED | HIGH | 49 | 2026-11-06T17:50:13.376323+00:00 | https://portstephens.csod.com/ux/ats/careersite/1/home?c=portstephens (8; LIVE_VERIFIED); https://nswconnect.csod.com/ux/ats/careersite/1/home?c=nswconnect (41; LIVE_VERIFIED)  |
| Dayforce | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| Deel | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Dover | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Eightfold AI | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| FirstStage | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 4 | 2026-11-06T17:28:28.660502+00:00 | https://firststage.firststage.co/jobs (1; LIVE_VERIFIED); https://quantumbase.firststage.co/jobs (3; LIVE_VERIFIED)  |
| Freshteam | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 49 | 2026-11-06T12:12:34.049462+00:00 | https://sequoiaat.freshteam.com/jobs (26; LIVE_VERIFIED); https://talent360.freshteam.com/jobs (23; LIVE_VERIFIED)  |
| Gem.com | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| GoHire | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 45 | 2026-11-06T07:43:13.012881+00:00 | https://jobs.gohire.io/dineamic-hospitality-fniota1h/ (22; LIVE_VERIFIED); https://jobs.gohire.io/digital-shift-o0hrqw5o/ (23; LIVE_VERIFIED)  |
| Greenhouse | ats | IMPLEMENTED | LIVE_VERIFIED | LOW | 1226 | 2026-11-05T16:41:54.721525+00:00 | https://job-boards.greenhouse.io/stripe (762; LIVE_VERIFIED); https://job-boards.greenhouse.io/cloudflare (464; LIVE_VERIFIED)  |
| HiBob | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| HireBridge | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 29 | 2026-11-06T17:04:11.749891+00:00 | https://recruit.hirebridge.com/v3/Jobs/list.aspx?cid=8484 (14; LIVE_VERIFIED); https://recruit.hirebridge.com/v3/Jobs/list.aspx?cid=8427 (15; LIVE_VERIFIED)  |
| HireHive | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 65 | 2026-11-06T06:55:14.734024+00:00 | https://amcsgroup.hirehive.com (59; LIVE_VERIFIED); https://echelon-dc.hirehive.com (6; LIVE_VERIFIED)  |
| Hireology | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 7 | 2026-11-06T13:05:16.366235+00:00 | https://careers.hireology.com/beachchevrolet (4; LIVE_VERIFIED); https://careers.hireology.com/pipprinting01151 (3; LIVE_VERIFIED)  |
| HiringThing | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 5 | 2026-11-06T12:04:24.524963+00:00 | https://math-learning-center.hiringthing.com/ (2; LIVE_VERIFIED); https://rtrjobs.hiringthing.com/ (3; LIVE_VERIFIED)  |
| iCIMS | ats | IMPLEMENTED | LIVE_VERIFIED | HIGH | 74 | 2026-11-06T18:04:06.601240+00:00 | https://careers-iomart.icims.com/jobs/search (10; LIVE_VERIFIED); https://careers-fedwriters.icims.com/jobs/search (64; LIVE_VERIFIED)  |
| iSolvedHire | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 5 | 2026-11-06T08:53:54.959321+00:00 | https://uasystem.isolvedhire.com/jobs/ (2; LIVE_VERIFIED); https://verifiedcredentials.isolvedhire.com/jobs/ (3; LIVE_VERIFIED)  |
| JazzHR | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 119 | 2026-11-06T03:41:01.947707+00:00 | https://lapmasterwolters.applytojob.com/apply (6; LIVE_VERIFIED); https://belaytechnologies.applytojob.com/apply (113; LIVE_VERIFIED)  |
| Jobvite | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 58 | 2026-11-06T08:36:44.397712+00:00 | https://jobs.jobvite.com/iboss/jobs (35; LIVE_VERIFIED); https://jobs.jobvite.com/optimas/jobs (23; LIVE_VERIFIED)  |
| JOIN.com | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 5 | 2026-11-06T12:57:06.795590+00:00 | https://join.com/companies/2open (3; LIVE_VERIFIED); https://join.com/companies/joinit (2; LIVE_VERIFIED)  |
| Kula.ai | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 59 | 2026-11-06T12:29:47.538605+00:00 | https://careers.kula.ai/fwg-internal (2; LIVE_VERIFIED); https://careers.kula.ai/massive-bio (57; LIVE_VERIFIED)  |
| Lever.co | ats | IMPLEMENTED | LIVE_VERIFIED | LOW | 394 | 2026-11-05T16:42:17.172545+00:00 | https://jobs.lever.co/spotify (87; LIVE_VERIFIED); https://jobs.lever.co/palantir (307; LIVE_VERIFIED)  |
| Manatal | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 12 | 2026-11-06T08:00:22.119713+00:00 | https://www.careers-page.com/quantilehealth (2; LIVE_VERIFIED); https://www.careers-page.com/munich-ventures-2 (10; LIVE_VERIFIED)  |
| Oracle Recruiting | ats | IMPLEMENTED | LIVE_VERIFIED | HIGH | 53 | 2026-11-06T17:42:06.317144+00:00 | https://eoja.fa.ap1.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX/jobs (28; LIVE_VERIFIED); https://eifn.fa.us6.oraclecloud.com/hcmUI/CandidateExperience/en/sites/ExternalCareerSite/jobs (25; LIVE_VERIFIED)  |
| PageUp | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Paradox | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| Paycom | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| Paycor | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Paylocity | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 3 | 2026-11-06T13:16:41.489756+00:00 | https://recruiting.paylocity.com/Recruiting/Jobs/All/a387d706-ac6f-4e58-b47b-be05001923ea (1; LIVE_VERIFIED); https://recruiting.paylocity.com/Recruiting/Jobs/All/be178b00-f3fb-452e-9aef-dce1ef7fcdba (2; LIVE_VERIFIED)  |
| Personio | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 51 | 2026-11-05T16:49:55.782699+00:00 | https://matrix42.jobs.personio.de (34; LIVE_VERIFIED); https://planqc-gmbh.jobs.personio.de (17; LIVE_VERIFIED)  |
| Phenom People | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| Pinpoint | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 49 | 2026-11-06T03:20:57.181056+00:00 | https://intermedia.pinpointhq.com (43; LIVE_VERIFIED); https://workwithus.pinpointhq.com (6; LIVE_VERIFIED)  |
| Polymer | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 6 | 2026-11-06T07:47:46.726853+00:00 | https://jobs.polymer.co/chemfinitytech (4; LIVE_VERIFIED); https://jobs.polymer.co/gencores-inc (2; LIVE_VERIFIED)  |
| Recooty | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 28 | 2026-11-06T08:33:21.660966+00:00 | https://careerspage.io/augusto-digital (2; LIVE_VERIFIED); https://careerspage.io/recooty-inc (26; LIVE_VERIFIED)  |
| Recruitee | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 29 | 2026-11-06T01:42:58.731786+00:00 | https://natilik.recruitee.com (6; LIVE_VERIFIED); https://bunq.recruitee.com (23; LIVE_VERIFIED)  |
| Rippling | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 11 | 2026-11-06T12:24:45.518767+00:00 | https://ats.rippling.com/realwork/jobs (5; LIVE_VERIFIED); https://ats.rippling.com/sas/jobs (6; LIVE_VERIFIED)  |
| Rival | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| SAP SuccessFactors | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| SmartRecruiters | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 90 | 2026-11-05T16:49:50.960317+00:00 | https://careers.smartrecruiters.com/SmartRecruiters (2; LIVE_VERIFIED); https://careers.smartrecruiters.com/Colliers (88; LIVE_VERIFIED)  |
| talentReef | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Taleo | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| Teamtailor | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 26 | 2026-11-06T03:09:11.551818+00:00 | https://clearroute.teamtailor.com (22; LIVE_VERIFIED); https://omny.teamtailor.com (4; LIVE_VERIFIED)  |
| Trakstar | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 14 | 2026-11-06T12:16:37.653365+00:00 | https://bsglaw.hire.trakstar.com/ (3; LIVE_VERIFIED); https://worksuites.hire.trakstar.com/ (11; LIVE_VERIFIED)  |
| TriNet | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 18 | 2026-11-06T12:45:46.787947+00:00 | https://app.trinethire.com/companies/69740-ark-investment-management/jobs (6; LIVE_VERIFIED); https://app.trinethire.com/companies/665804-stridepath-consulting/jobs (12; LIVE_VERIFIED)  |
| UltiPro | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| WeRecruit | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 19 | 2026-11-06T17:24:52.410926+00:00 | https://careers.werecruit.io/fr/epec (1; LIVE_VERIFIED); https://careers.werecruit.io/fr/ctlog-international (18; LIVE_VERIFIED)  |
| Workable | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 4 | 2026-11-06T03:14:41.352483+00:00 | https://apply.workable.com/careers/ (1; LIVE_VERIFIED); https://apply.workable.com/learnworlds/ (3; LIVE_VERIFIED)  |
| Workday | ats | IMPLEMENTED | LIVE_VERIFIED | HIGH | 43 | 2026-11-06T01:43:52.166289+00:00 | https://imf.wd5.myworkdayjobs.com/IMF (14; LIVE_VERIFIED); https://gatesfoundation.wd1.myworkdayjobs.com/Gates (29; LIVE_VERIFIED)  |
| Zoho Recruit | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 47 | 2026-11-06T13:33:08.086608+00:00 | https://mywork.zohorecruit.eu/jobs/Careers (11; LIVE_VERIFIED); https://global.zohorecruit.com/jobs/Careers (36; LIVE_VERIFIED)  |
| Niceboard | job_board | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| WP Job Manager | job_board | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| JobKit | job_board | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| Jobboardly | job_board | IMPLEMENTED | LIVE_VERIFIED | HIGH | 1355 | 2026-11-06T08:31:19.986009+00:00 | https://recruiter-jobs.jobboardly.com/jobs (31; LIVE_VERIFIED); https://pennsylvania-communications.jobboardly.com/jobs (1324; LIVE_VERIFIED)  |
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

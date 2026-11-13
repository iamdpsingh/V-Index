# Provider coverage

Exactly 58 ATS + 20 job-board platforms. Risk is a planning estimate, not a verified access limitation.

IMPLEMENTED means code exists. LIVE_VERIFIED means the latest smoke run retrieved non-empty, complete jobs for all configured example tenants. This is a point-in-time connector check, not full production acceptance. FAILED and BLOCKED retain genuine limitations. NOT_STARTED providers have no connector.

| Platform | Kind | Implementation | Evidence | Risk | Count (sum) | Last run | Examples / failures |
|---|---|---|---|---|---|---|---|
| ADP | ats | IMPLEMENTED | FAILED | HIGH | 0 | 2026-11-13T07:29:27.959364+00:00 | https://myjobs.adp.com/signatureperformancecareers/cx/job-listing (0; FAILED); https://myjobs.adp.com/wesbancocareers/cx/job-listing (0; FAILED) ValueError: ADP detail identity mismatch for 5001235761306; ValueError: ADP detail identity mismatch for 5001237621006 |
| ApplicantPro | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 5 | 2026-11-06T08:53:36.755511+00:00 | https://farbank.applicantpro.com/jobs/ (2; LIVE_VERIFIED); https://clarke.applicantpro.com/jobs/ (3; LIVE_VERIFIED)  |
| Ashby | ats | IMPLEMENTED | LIVE_VERIFIED | LOW | 243 | 2026-11-05T16:42:19.453089+00:00 | https://jobs.ashbyhq.com/Ashby (72; LIVE_VERIFIED); https://jobs.ashbyhq.com/ramp (171; LIVE_VERIFIED)  |
| Avature | ats | IMPLEMENTED | LIVE_VERIFIED | HIGH | 48 | 2026-11-06T18:28:04.539290+00:00 | https://careers.avature.net/en_US/main/SearchJobs (19; LIVE_VERIFIED); https://metrobank.avature.net/amazingcareers/SearchJobs (29; LIVE_VERIFIED)  |
| BambooHR | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 25 | 2026-11-06T03:18:07.998376+00:00 | https://anaergia.bamboohr.com/careers (20; LIVE_VERIFIED); https://concept2.bamboohr.com/careers (5; LIVE_VERIFIED)  |
| BrassRing | ats | IMPLEMENTED | LIVE_VERIFIED | HIGH | 43 | 2026-11-12T15:14:40.886192+00:00 | https://sjobs.brassring.com/TGnewUI/Search/home/HomeWithPreLoad?partnerid=25749&siteid=5764&PageType=searchResults (33; LIVE_VERIFIED); https://sjobs.brassring.com/TGnewUI/Search/home/HomeWithPreLoad?partnerid=25633&siteid=5440&PageType=searchResults (10; LIVE_VERIFIED)  |
| Breezy HR | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 81 | 2026-11-06T03:16:14.203649+00:00 | https://vald.breezy.hr (75; LIVE_VERIFIED); https://subscribe.breezy.hr (6; LIVE_VERIFIED)  |
| CareerPlug | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 10 | 2026-11-06T12:34:45.510649+00:00 | https://app.careerplug.com/accounts/576036 (2; LIVE_VERIFIED); https://app.careerplug.com/accounts/579908 (8; LIVE_VERIFIED)  |
| Comeet | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 33 | 2026-11-06T17:26:30.311458+00:00 | https://www.comeet.com/jobs/oriient/EA.005 (7; LIVE_VERIFIED); https://www.comeet.com/jobs/webbing/46.00E (26; LIVE_VERIFIED)  |
| CSOD | ats | IMPLEMENTED | LIVE_VERIFIED | HIGH | 49 | 2026-11-06T17:50:13.376323+00:00 | https://portstephens.csod.com/ux/ats/careersite/1/home?c=portstephens (8; LIVE_VERIFIED); https://nswconnect.csod.com/ux/ats/careersite/1/home?c=nswconnect (41; LIVE_VERIFIED)  |
| Dayforce | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| Deel | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 34 | 2026-11-07T02:13:38.251589+00:00 | https://jobs.deel.com/dott (16; LIVE_VERIFIED); https://jobs.deel.com/offsec (18; LIVE_VERIFIED)  |
| Dover | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Eightfold AI | ats | IMPLEMENTED | LIVE_VERIFIED | HIGH | 189 | 2026-11-07T02:12:28.099811+00:00 | https://app.eightfold.ai/careers (46; LIVE_VERIFIED); https://insight.eightfold.ai/careers (143; LIVE_VERIFIED)  |
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
| PageUp | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 163 | 2026-11-06T18:12:03.850825+00:00 | https://careers.pageuppeople.com/1220/cw/en/listing/ (35; LIVE_VERIFIED); https://careers.pageuppeople.com/1132/cw/en-us/listing/ (128; LIVE_VERIFIED)  |
| Paradox | ats | IMPLEMENTED | LIVE_VERIFIED | HIGH | 120 | 2026-11-12T16:11:02.000277+00:00 | https://flynnrgcareers.com/ (12; LIVE_VERIFIED); https://careers.mwg.aaa.com/ (108; LIVE_VERIFIED)  |
| Paycom | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| Paycor | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Paylocity | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 3 | 2026-11-06T13:16:41.489756+00:00 | https://recruiting.paylocity.com/Recruiting/Jobs/All/a387d706-ac6f-4e58-b47b-be05001923ea (1; LIVE_VERIFIED); https://recruiting.paylocity.com/Recruiting/Jobs/All/be178b00-f3fb-452e-9aef-dce1ef7fcdba (2; LIVE_VERIFIED)  |
| Personio | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 51 | 2026-11-05T16:49:55.782699+00:00 | https://matrix42.jobs.personio.de (34; LIVE_VERIFIED); https://planqc-gmbh.jobs.personio.de (17; LIVE_VERIFIED)  |
| Phenom People | ats | IMPLEMENTED | LIVE_VERIFIED | HIGH | 129 | 2026-11-12T16:24:29.497802+00:00 | https://careers.phenom.com/global/en/search-results (78; LIVE_VERIFIED); https://careers.bloodcancerunited.org/us/en/search-results (51; LIVE_VERIFIED)  |
| Pinpoint | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 49 | 2026-11-06T03:20:57.181056+00:00 | https://intermedia.pinpointhq.com (43; LIVE_VERIFIED); https://workwithus.pinpointhq.com (6; LIVE_VERIFIED)  |
| Polymer | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 6 | 2026-11-06T07:47:46.726853+00:00 | https://jobs.polymer.co/chemfinitytech (4; LIVE_VERIFIED); https://jobs.polymer.co/gencores-inc (2; LIVE_VERIFIED)  |
| Recooty | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 28 | 2026-11-06T08:33:21.660966+00:00 | https://careerspage.io/augusto-digital (2; LIVE_VERIFIED); https://careerspage.io/recooty-inc (26; LIVE_VERIFIED)  |
| Recruitee | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 29 | 2026-11-06T01:42:58.731786+00:00 | https://natilik.recruitee.com (6; LIVE_VERIFIED); https://bunq.recruitee.com (23; LIVE_VERIFIED)  |
| Rippling | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 11 | 2026-11-06T12:24:45.518767+00:00 | https://ats.rippling.com/realwork/jobs (5; LIVE_VERIFIED); https://ats.rippling.com/sas/jobs (6; LIVE_VERIFIED)  |
| Rival | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 45 | 2026-11-12T15:49:08.609081+00:00 | https://jobs.silkroad.com/RSCS/Careers (2; LIVE_VERIFIED); https://jobs.silkroad.com/BlandLandscaping/Careers (43; LIVE_VERIFIED)  |
| SAP SuccessFactors | ats | IMPLEMENTED | LIVE_VERIFIED | HIGH | 17 | 2026-11-08T12:17:29.883037+00:00 | https://careers.icbc.com/search/ (9; LIVE_VERIFIED); https://careers.kaust.edu.sa/search/ (8; LIVE_VERIFIED)  |
| SmartRecruiters | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 90 | 2026-11-05T16:49:50.960317+00:00 | https://careers.smartrecruiters.com/SmartRecruiters (2; LIVE_VERIFIED); https://careers.smartrecruiters.com/Colliers (88; LIVE_VERIFIED)  |
| talentReef | ats | NOT_STARTED | NOT_STARTED | MEDIUM | None | None | Not tested  |
| Taleo | ats | IMPLEMENTED | LIVE_VERIFIED | HIGH | 135 | 2026-11-07T01:53:19.592777+00:00 | https://phf.tbe.taleo.net/phf03/ats/careers/v2/jobSearch?org=GRAYBARCANADA&cws=42 (32; LIVE_VERIFIED); https://phg.tbe.taleo.net/phg01/ats/careers/v2/jobSearch?org=GATEWAYVENT&cws=72 (103; LIVE_VERIFIED)  |
| Teamtailor | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 26 | 2026-11-06T03:09:11.551818+00:00 | https://clearroute.teamtailor.com (22; LIVE_VERIFIED); https://omny.teamtailor.com (4; LIVE_VERIFIED)  |
| Trakstar | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 14 | 2026-11-06T12:16:37.653365+00:00 | https://bsglaw.hire.trakstar.com/ (3; LIVE_VERIFIED); https://worksuites.hire.trakstar.com/ (11; LIVE_VERIFIED)  |
| TriNet | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 18 | 2026-11-06T12:45:46.787947+00:00 | https://app.trinethire.com/companies/69740-ark-investment-management/jobs (6; LIVE_VERIFIED); https://app.trinethire.com/companies/665804-stridepath-consulting/jobs (12; LIVE_VERIFIED)  |
| UltiPro | ats | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| WeRecruit | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 19 | 2026-11-06T17:24:52.410926+00:00 | https://careers.werecruit.io/fr/epec (1; LIVE_VERIFIED); https://careers.werecruit.io/fr/ctlog-international (18; LIVE_VERIFIED)  |
| Workable | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 4 | 2026-11-06T03:14:41.352483+00:00 | https://apply.workable.com/careers/ (1; LIVE_VERIFIED); https://apply.workable.com/learnworlds/ (3; LIVE_VERIFIED)  |
| Workday | ats | IMPLEMENTED | LIVE_VERIFIED | HIGH | 43 | 2026-11-06T01:43:52.166289+00:00 | https://imf.wd5.myworkdayjobs.com/IMF (14; LIVE_VERIFIED); https://gatesfoundation.wd1.myworkdayjobs.com/Gates (29; LIVE_VERIFIED)  |
| Zoho Recruit | ats | IMPLEMENTED | LIVE_VERIFIED | MEDIUM | 47 | 2026-11-06T13:33:08.086608+00:00 | https://mywork.zohorecruit.eu/jobs/Careers (11; LIVE_VERIFIED); https://global.zohorecruit.com/jobs/Careers (36; LIVE_VERIFIED)  |
| Niceboard | job_board | IMPLEMENTED | LIVE_VERIFIED | HIGH | 29 | 2026-11-08T03:25:18.002538+00:00 | https://jobs.aiacolorado.org/ (14; LIVE_VERIFIED); https://jobs.medicalalley.org/ (15; LIVE_VERIFIED)  |
| WP Job Manager | job_board | IMPLEMENTED | LIVE_VERIFIED | HIGH | 5 | 2026-11-08T12:16:58.227605+00:00 | https://oliver-walters.com/job-listings/ (3; LIVE_VERIFIED); https://pearlstreetsystems.com/careers/ (2; LIVE_VERIFIED)  |
| JobKit | job_board | IMPLEMENTED | LIVE_VERIFIED | HIGH | 39 | 2026-11-08T03:25:49.097273+00:00 | https://jobs.rubyonrails.org/ (13; LIVE_VERIFIED); https://welpora.jobkit.io/ (26; LIVE_VERIFIED)  |
| Jobboardly | job_board | IMPLEMENTED | LIVE_VERIFIED | HIGH | 1355 | 2026-11-06T08:31:19.986009+00:00 | https://recruiter-jobs.jobboardly.com/jobs (31; LIVE_VERIFIED); https://pennsylvania-communications.jobboardly.com/jobs (1324; LIVE_VERIFIED)  |
| Jobiqo | job_board | IMPLEMENTED | FAILED | HIGH | 99 | 2026-11-12T21:47:57.483634+00:00 | https://www.agrajo.com/job (99; LIVE_VERIFIED); https://careers.unitedway.org/jobs (0; FAILED) TimeoutError:  |
| JBoard.io | job_board | IMPLEMENTED | LIVE_VERIFIED | HIGH | 78 | 2026-11-07T04:16:03.139570+00:00 | https://jobs.aame.org/jobs (30; LIVE_VERIFIED); https://jobs.cisontario.ca/jobs (48; LIVE_VERIFIED)  |
| JobBoardFire | job_board | IMPLEMENTED | LIVE_VERIFIED | HIGH | 24 | 2026-11-12T20:37:39.050902+00:00 | https://jobs.trellis.net/ (18; LIVE_VERIFIED); https://lpjc.jobboardfire.com/ (6; LIVE_VERIFIED)  |
| SmartJobBoard | job_board | IMPLEMENTED | LIVE_VERIFIED | HIGH | 105 | 2026-11-08T03:31:39.192415+00:00 | https://americanbath.mysmartjobboard.com/jobs/ (28; LIVE_VERIFIED); https://jobs.psychologicalscience.org/jobs/ (77; LIVE_VERIFIED)  |
| JobBoard.io | job_board | IMPLEMENTED | LIVE_VERIFIED | HIGH | 63 | 2026-11-07T07:07:19.433685+00:00 | https://www.nifajobs.com/ (2; LIVE_VERIFIED); https://www.cancercareers.org/ (61; LIVE_VERIFIED)  |
| Wiley Madgex | job_board | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| Talenetic | job_board | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| JobMount | job_board | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| CareerSiteCloud | job_board | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| JobBoard.com | job_board | IMPLEMENTED | LIVE_VERIFIED | HIGH | 22 | 2026-11-08T12:15:42.598392+00:00 | https://jobs.acevo.org.uk/ (15; LIVE_VERIFIED); https://www.gradsouthwest.com/ (7; LIVE_VERIFIED)  |
| Artha | job_board | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| jobboardsoftware.com | job_board | IMPLEMENTED | LIVE_VERIFIED | HIGH | 4 | 2026-11-12T15:54:29.204254+00:00 | https://agconnect.exenzo.nl/ (3; LIVE_VERIFIED); https://vacatures.ecommerce.nl/vacatures (1; LIVE_VERIFIED)  |
| jobBoardHQ | job_board | IMPLEMENTED | LIVE_VERIFIED | HIGH | 199 | 2026-11-12T15:51:51.973792+00:00 | https://jobboardhq.esc17.net/search (47; LIVE_VERIFIED); https://resume.absc.org/search (152; LIVE_VERIFIED)  |
| Nodex | job_board | IMPLEMENTED | LIVE_VERIFIED | HIGH | 50 | 2026-11-08T12:16:39.627724+00:00 | https://www.emotivtech.co.uk/search (35; LIVE_VERIFIED); https://www.geckotravelrecruitment.co.uk/search (15; LIVE_VERIFIED)  |
| eJobBoard | job_board | NOT_STARTED | NOT_STARTED | HIGH | None | None | Not tested  |
| ejobsitesoftware.com | job_board | IMPLEMENTED | FAILED | HIGH | 7 | 2026-11-12T15:38:00.089174+00:00 | https://seasonaljobs.co.nz/job-search/ (0; FAILED); https://gurushrconsultancy.com/jobboard/job-search/ (7; LIVE_VERIFIED) UpstreamStatusError: Upstream HTTP 302 |

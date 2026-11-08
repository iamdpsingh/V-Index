# November 8 backend integration review

Antigravity's local branch `review/antigravity-backend` is preserved at `072a18b`. It proposed 13 new verified rows over the previous 50 and documented access issues for 15 more. Independent review checked the published rosters, connector code, live sources and tests. The acceptance rule is a nonempty, complete enumeration on two independently operated supported sites. The live provider matrix is the source of truth. [Coverage matrix](COVERAGE.md)

**54 of 78 platforms verified live.** There are 45 ATS and nine job-board platforms verified, with 24 remaining. The four new platforms passed eight complete independent site runs on executable revision `9accbb0`. The service-backed suite passed 1,100 tests. Ruff, formatting and mypy passed. [Dated live evidence](../evidence/20261108T121730Z-smoke.json)

## What passed

| Platform | Independent live examples | Review decision |
|---|---|---|
| JobBoard.com | ACEVO 15, Gradsouthwest 7 | Require the single advertised sitemap, all canonical job details and an exact same-ID apply link. |
| Nodex | Emotiv 35, Gecko Travel Recruitment 15 | Corrected the first-page extraction. Confirmed 4 and 2 native pages, respectively, checked the exact source totals, then repeated the whole roster. Emotiv listing 769 has only a reference and apply control where the description belongs. It is flagged as missing a source description. |
| WP Job Manager | Oliver Walters 3, Pearl Street Systems 2 | Routed the read-only listing POST through bounded public HTTP. Require the native payload to report a complete single page and reject malformed, duplicate or out-of-scope active rows. |
| SAP SuccessFactors | ICBC 9, KAUST 8 | Added a public Career Site Builder connector. Verify the unfiltered total against the whole single-page roster, then check all canonical postings and same-ID application links. Respect job detail indexing opt-outs. |

SAP's direct recruiting interface and Career Site Builder are different surfaces. The selected employer sites use the latter. The connector reads the anonymous search pages and indexes their individually indexable job detail pages. [SAP Career Site Builder settings](https://help.sap.com/docs/successfactors-recruiting/setting-up-and-maintaining-sap-successfactors-recruiting/site-configuration-in-career-site-builder-settings)

## What remains from the 13 proposed additions

These ten prototypes and their original evidence remain on the local review branch. They are excluded from main until the relevant issues are resolved.

| Platform | Review finding | Remaining work |
|---|---|---|
| BrassRing | U.S. Steel's embedded payload advertised 319 jobs and returned 50. Infosys advertised and returned 8. | Prove the full public roster on a second portal or implement the permitted native pager. |
| Gem.com | The independent access probes for the two proposed public feeds returned HTTP 403. The reviewed connector also checked robots on the job site rather than on the API origin. | Confirm permitted access at the API origin and two successful full feeds. [Gem Job Board API](https://api.gem.com/job_board/v0/reference) |
| Phenom People | The embedded results contained 10 jobs each against totals of 1,705 and 784. Both pages advertised next links. | Implement complete public pagination and try suitable boards within the job budget. |
| Rival | The two boards advertised 9 and 8 pages. The connector read the first page on each. | Verify a permitted native pager and reconcile the complete roster. |
| talentReef | The adapter requested exactly 10 hits and never reconciled the search total. It targets a host with an internal service name. | Confirm the service is a supported public interface before any further requests, then prove the active roster and all pages. |
| Wiley Madgex | Inside Higher Ed showed 23,333 jobs and Science Careers showed 530. Both provided a next link. | Identify two manageable boards with a full public roster, or a permitted complete feed. |
| JobMount | JobsRUs and National Diversity Network advertised 829 and 12,248 results. Each had a next page. | Find bounded independent boards or a permitted complete feed, then validate pagination. |
| jobBoardHQ | Both actual search pages showed 20 first-page rows and additional page controls. | Validate public pagination and exact total or terminal-page proof. |
| jobboardsoftware.com | The adapter explicitly sliced each API response to 10 and never checked source paging or total metadata. | Enumerate the supported native roster without truncation and reconfirm its full set. |
| ejobsitesoftware.com | The proposed source URLs were homepage lists. Their public Search Jobs pages returned no roster for the unfiltered GET used in review. | Identify the documented public full roster action and verify both boards. |

## Follow-up on the original blocker audit

SAP SuccessFactors is resolved above. The other 14 remain open. These are observations about the tested paths and sites.

| Platform | Latest review position |
|---|---|
| ADP | The reviewed Workforce Now route had a session or redirect constraint. The public ADP Careers Portal is a separate candidate surface. Establish the platform identity and two independent employers before counting it. |
| Dayforce | The documented JobFeeds integration requires an authorized account. The public career UI is a distinct surface that still needs a permitted complete roster. [Dayforce developer guide](https://help.dayforce.com/r/documents/Dayforce-RESTful-Web-Services-Developer-Guide/RESTful-Get-Job-Postings) |
| Dover | The researched jobs-host API is disallowed by robots. Look for a separately published, permitted employer feed. |
| HiBob | The tested service API requires credentials. A public hosted collection remains unverified. |
| Paradox | The vendor links real public branded career sites. Flynn displayed 10 results. TruGreen displayed 480 and 48 pages. Extra Space advertised a sitemap containing 602 job URLs, while its linked MCP discovery URL returned tool metadata. These are useful permitted paths, pending a complete connector and two end-to-end runs. [Paradox Career Site Studio](https://www.paradox.ai/products/career-site-studio) |
| Paycom | The reviewed posting service requires a session credential. Seek a separate authorized public listing export. |
| Paycor | The tested recruiting host disallowed automated access and redirected to login. A separately permitted public career-board variant remains to be verified. |
| UltiPro | The public shell was reachable. The tested search endpoint was disallowed by robots. |
| Jobiqo | The reviewed boards presented an interactive challenge. Look for an independently published permitted feed or another official tenant. |
| JobBoardFire | The handoff encountered challenge responses on the tested paths. Earlier Trellis discovery showed a public sitemap, but there is no second independently verified complete board. |
| Talenetic | Medical Update Jobs Online identifies Talenetic, but its robots policy denied the request. OilFinity returned a redirect and was not followed. Look for vendor-published job XML on a verified customer site. [Talenetic features](https://www.talenetic.com/features/) |
| CareerSiteCloud | The tested host returned an access or upstream error. Obtain a verifiable active tenant and permitted collection. |
| Artha | The tested TalentBridge sitemap loaded, but its detail pages returned an access challenge. Find an authorized feed or another vendor-identified board. |
| eJobBoard | The tested domain failed DNS resolution. Confirm the exact vendor or a live installation. This is a separate required platform from ejobsitesoftware.com. |

Hosted refresh, deployment and the release gates remain separate from the live coverage evidence. [Production release requirements](PRODUCTION_RELEASE_REQUIREMENTS.md)

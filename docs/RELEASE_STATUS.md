# Rolewisp release status

Updated November 20, 2026. This document distinguishes the integrated software,
local validation, platform evidence, and public launch work.

## Integrated product

- Consistent public salary/employment/workplace output across search, detail, and
  recommendations, with original values preserved and provenance timestamps.
- Search by keyword, company, and location with pagination and original links.
  The web client requests summary records and loads full details on selection.
  Existing API consumers keep the default full response.
- PostgreSQL trigram indexes support the existing substring search. Active-job
  lookup and due-source scheduling have dedicated indexes.
- Scheduled refreshes use source leases, transactions, cooldowns, and existing
  completeness/closure rules. PostgreSQL workers default to four simultaneous
  independent source refreshes. SQLite refreshes remain serial.
- Candidate and Employer onboarding, private manual profiles, qualification
  categories, profile photos, encrypted résumé storage, and recommendations.
- Employer drafts, editing, publishing, and closing with ownership enforcement.
  Publishing requires a verified email.
- Email verification and recovery code flows, plus configurable Google,
  LinkedIn, and GitHub OAuth callbacks. Live provider activation needs configured
  accounts and callback URLs.
- Privacy, terms, cookie, and refund pages, with policy links during signup.
  The owner supplied operator details and a public contact address. Final legal review and contact delivery verification are still needed.
- Free/Plus regional catalogue. Paid checkout remains deferred.
- Repeatable registration of 142 reviewed source examples across the 71
  live-verified platforms. Source registration schedules fresh work.

## Validation recorded locally

- 1,209 backend tests passed with PostgreSQL and Redis enabled. One
  PostgreSQL-specific planner test was skipped in its SQLite fixture.
- 176 browser checks passed. Ten device-specific cases were intentionally
  skipped. Coverage includes search/detail navigation, private profile editing,
  employer drafts, pricing display, keyboard operation, and operator views. Browser fixtures and screenshots use synthetic data and are separate from live connector evidence.
- Production frontend build, Ruff checks, Ruff format checks, and mypy passed.
- Private account/profile/qualification/resume and employer draft checks passed
  through the production web proxy against PostgreSQL and Redis.
- A 25-job response from the local index shrank from 111,068 to 22,638 bytes when
  requesting summaries, a 79.6% reduction. This is payload measurement on the
  local dataset, not a claim about hosted latency or load capacity.
- Python dependency audit checked 48 packages and reported no known
  vulnerabilities. npm reported zero known vulnerabilities during installation.
- HTML headers were checked on the production build. The CSP currently protects
  framing, object embedding, base URLs, and form targets. Script nonce/hash CSP
  enforcement and deployed security validation remain launch work.
- Current tracked-file and reachable-history heuristic scans were run. Historical
  OpenAI-key-shaped matches were public Workday job-path fragments. No confirmed
  credential was identified in the reviewed scope. This is not a security
  certification or proof covering external systems, backups, or every leak form.

GitHub reruns backend, browser/build, and full Compose checks on push. Read the
actual result for the submitted revision in the [Verify workflow](https://github.com/iamdpsingh/V-Index/actions/workflows/ci.yml).

## Platform acceptance remains open

The registry records 71 fully verified platforms, comprising 54 ATS platforms
and 17 job-board platforms. The coverage workflow additionally records partial
extracts on Paycom, Dover, Paycor, and UltiPro. Talenetic has one fully indexed board and an incomplete second board.
Third-party samples do not establish upstream completeness or freshness.

Gem.com completed full live runs on Nabla Bio (3 jobs) and nclusion (7 jobs),
then committed matching results through the real worker. Its public hosted-board
GraphQL interface is separate from the blocked API host examined earlier.

TalentReef completed full runs on JC Resorts (87 jobs) and the On the Border
board (24 jobs), then committed both through the worker. It uses the native
public app's production gateway with tenant-scoped external-only queries,
complete pagination, successful shard checks, and a second full collection read.

Dayforce completed MAAS Energy Works (22 jobs) and SILK (38 jobs), including
full public details and final roster reconfirmation, then committed both through
the worker. The public app obtains a server-issued anonymous CSRF token/cookie
pair before read-only search POSTs. Earlier requests omitted that handshake.
No login, challenge bypass, or private candidate session is used.

Talenetic has a resumable connector for two branded boards. Medical Update
Online committed 2,844 active jobs after examining all 2,900 sitemap entries,
validating 56 explicitly expired pages, and reconfirming the full sitemap.
All active records carry the publisher-supplied company label “Partner Jobs”
and are flagged accordingly; actual hiring-company names are not inferred.
Final counts are audited in `evidence/20261120-talenetic-committed-record-audit.json`.
The fresh Pro Contract Jobs sitemap had 36,523 candidate URLs, but the run
stopped on a removed/invalid detail. It remains incomplete and unreconciled.

CareerSiteCloud and eJobBoard are on hold at the owner’s request pending usable
installation URLs. They are still required by the original challenge.

All seven remaining platforms still need full reusable connector acceptance. The original
78-platform requirement is open. See [coverage](COVERAGE.md) and
[coverage workflow](COVERAGE_WORKFLOW.md).

## Public release needs external configuration

- A Vercel/v0 frontend deployment and a reachable API, PostgreSQL, Redis, and
  persistent worker. Hosting, quotas, and actual operating costs need validation
  within the owner's budget.
- The approved public origin/domain, HTTPS, gateway/proxy rate behaviour,
  secret injection, private caching checks, backups, and a restore drill.
- Live SMTP delivery and inbox verification. Each configured OAuth provider
  needs a browser login test using its real application registration.
- Verify delivery to the supplied contact address, `example@rolewisp.in`. The owner supplied Dhruv Pratap Singh as operator. Privacy/legal and consent/tracking review against the deployed site remain open.
- The Vaya project/repository/demo connection and submission. The public
  leaderboard request redirected to sign-in, so ranking was not verified.

## Competitor findings

JobSweep's public coverage page reported 76 live platforms out of 78. Its
definition of live requires a connector and an enabled site. Paycom and UltiPro
are explicitly described as sampled coverage, while CareerSiteCloud showed no
active jobs or successful crawl. Its public API returns compact summaries,
separate job details, and cursor pagination.

JobIndex returned an automated-access restriction for the homepage and the
suggested jobs API page. Its current coverage and implementation could not be
verified in this pass. Public endpoints do not disclose either site's private
database design, infrastructure configuration, or implementation source.

Sources are the [JobSweep coverage page](https://jobsweep.works/coverage),
[public API schema](https://jobsweep.works/openapi.json), and
[Vaya leaderboard](https://vayahq.com/leaderboard?challenge=build-a-job-board-indexer-for-10000).


## Consistent-record acceptance, November 20

The shared public serializer and stricter input validation are implemented.
Merged first-seen/last-changed timestamps preserve source history and cannot move
backwards on an older-source refresh. Public output includes last-checked times
and each original source/application link. Source observations remain unchanged.
Salary currencies, pay periods, employer names and missing descriptions are
never guessed. See [the connector contract](CONNECTOR_CONTRACT.md#consistent-public-records-november-20).

A strict audit of the isolated worker-committed Dayforce, Gem.com and talentReef
validation database passed all **181 open records**: required fields, typed
public output, timestamps, links and populated optional-field retention.
[Recorded audit](../evidence/20261120-record-quality-new-platforms.json).
This database is separate from the local demo population; the counts must not
be added together.

Talenetic remains incomplete. MedicalUpdate's committed 2,844 jobs use the
publisher's generic “Partner Jobs” company label, and 102 lack structured
location. Its 2,900-candidate run also observed 56 explicitly expired pages.
The second ProContract board still advertises a removed detail: an allowed
fresh read again returned HTTP 410. No partial snapshot was published, and no
closure was inferred from that failure. Completing the second board would
resolve the additional-board gate, but required employer/location quality
would still need resolution for full challenge acceptance.
[Record audit](../evidence/20261120-record-quality-talenetic.json),
[fresh failing-detail recheck](../evidence/20261120-talenetic-second-board-recheck.json).

The consistent-record acquisition criterion remains open while required source
fields are missing. The audit reports these gaps explicitly; structural schema
success must not be presented as complete source data or full 78-platform
acceptance.


The final local audit inspected **8,109 open observations** and their canonical
records across 66 connector keys. Typed public contracts and optional-field
retention passed with zero contract failures. It still found **74 blank
descriptions and 182 blank locations**. The population includes 202 last-known
observations retained while closure confirmation is pending. This is not a
fresh upstream job census or an audit of every historically verified platform.
[Local audit](../evidence/20261120-record-quality-local.json).

Both reviewed Jobboardly boards (21 and 1,493 jobs) and both Nodex boards (35 and
15 jobs) passed new full live runs and matching worker commits. Native-page
fallback recovered three Jobboardly locations; other absent native fields
remain flagged. Nodex now captures source salary and all supplied locations/
employment types. [Live runs](../evidence/20261120T111115Z-smoke.json),
[worker results](../evidence/20261120-record-enrichment-worker.json).

A Talenetic detail also exposed a native employment label absent from JSON-LD.
The parser now preserves that explicit field and its original HTML. One freshly
fetched detail verified the recovery of “Permanent”. This is not a full board
refresh; the earlier committed 2,844-job audit predates that recovery.
[Native field check](../evidence/20261120-talenetic-native-field-recheck.json).


A later November 20 investigation checked ProContract's unfiltered native
search as an alternative to its stale sitemap. The current robots policy
rejects `/job-search-results`; no request was sent to that route. Another
possible installation, Oilfinity, is listed by recruitment integration provider
[idibu](https://www.idibu.com/network/oilfinity/), but both reviewed HTTPS origins
returned HTTP 302 on robots.txt and provided no validated current board.
Neither investigation grants coverage or an alternate complete feed.
[Search policy evidence](../evidence/20261120-talenetic-active-search-policy.json),
[Oilfinity checks](../evidence/20261120-talenetic-oilfinity-research.json).

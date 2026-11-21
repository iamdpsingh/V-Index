# Internal release checklist

November 21, 2026. **Fifteen recorded passes, one partial area and four held/open areas** in
an internally authored twenty-check review. These checks were chosen for the
release pass; Vaya did not supply this denominator. They have unequal scope,
effort and risk. Row 18 alone contains multiple separate tasks. **Do not use
this as an overall project-completion percentage or an official challenge score.**
A critical open gate can prevent acceptance regardless of how many others pass.

Coverage is separate: 71/78 historically live-verified platforms, 91.0%.
Historical connector verification does not guarantee current source health.
See [the original challenge criteria](ACCEPTANCE_TESTS.md) and [explanation](../handoff/07_ACCEPTANCE_AND_EVIDENCE.md).

| # | Check | Status and evidence |
| --- | --- | --- |
| 1 | Hosted web and API | Passed: production search and real-data UI review |
| 2 | Persistent hosted worker | Passed: ready/alive Vercel daemon and heartbeat |
| 3 | Complete initial success on every registered source | Open: latest follow-up 130/142 initially successful; twelve still lack an initial success |
| 4 | Second native production fetch | Passed: Ashby 77 to 78 jobs, operator-triggered; a full unattended six-hour cycle is not yet observed |
| 5 | Failure/partial fetch lifecycle safety | Passed: transactional guards, cancellation tests and reviewer replay; failures are not closures |
| 6 | Duplicate merge with provenance | Passed: deterministic replay plus separately labelled historical live example |
| 7 | Distinct roles remain separate | Passed: replay and live same-title/different-requisition examples |
| 8 | Search filters and pagination | Passed: hosted desktop/mobile interactions |
| 9 | Documented public API and handoff | Passed: actual production base, API/OpenAPI and reviewer walkthrough |
| 10 | Private ownership and operator authorization | Passed: hosted two-account isolation and denied operator endpoints |
| 11 | Login/signup limits through deployed proxy | Passed: 429/Retry-After and verified signed metadata |
| 12 | Private caching and session cookies | Passed: hosted no-store, Secure and HttpOnly checks |
| 13 | Script CSP and scoped security/dependency review | Passed: strict nonce policy, offline heuristic history review, dependency audits; not an exhaustive certification |
| 14 | Internal monitoring and failure/stale diagnostics | Passed: independent heartbeat, Redis alert state, safe logs/private report |
| 15 | External uptime/alert delivery | Partially implemented: independent GitHub probe/check-run alerts; notification delivery remains unverified with retained placeholder |
| 16 | Encrypted offsite snapshot and full isolated restore | Passed: actual 16-table production snapshot, private upload, anonymous 403, provider seven-day expiry |
| 17 | Desktop/mobile/profile/keyboard/contrast review | Passed: production real-data/profile review and browser suite |
| 18 | Final operator/privacy/provider/recovery gates | Owner-held/open: placeholder inbox, SMTP/OAuth activation and domain/legal review; key custody/deletion reconciliation/issuer rotation remain unverified. Preview mappings were isolated and restored authentication is now revoked |
| 19 | Measured provider operating costs and quota window | Open: provider billing data unavailable; short-window function CPU measured, daemon/DB/Redis usage and actual operating bill unmeasured |
| 20 | Vaya profile/repo/demo/evidence submission | Owner-held: explicitly leave submission open; draft prepared, no submission/ranking claimed |

Evidence: [hosted checks](../evidence/20261121-hosted-release-review.json),
[backup](../evidence/20261121-hosted-backup.json),
[production UI](../evidence/20261121-production-product-review.json),
[private profile](../evidence/20261121-production-private-profile-review.json),
[validation](../evidence/20261121-release-validation.json).


## November 21 follow-up

The owner explicitly retained the placeholder support inbox and left provider
activation/submission open. Those holds do not turn into passes. The independent
GitHub monitor passed a real live probe and produced a controlled, labelled
failed run/error annotation without disrupting the site. Email/SMS delivery
remains unverified, so check 15 is partial. Future preview mappings were isolated,
restored snapshot authentication is now revoked automatically, and a fresh
PostgreSQL drill verified source authentication remains untouched.

Current follow-up: 9,180 jobs, 128/142 initial successes, fourteen pending, nineteen
consecutive-failure sources, zero stale/abandoned sources at the checked time.
Billing information was unavailable; the permitted function CPU sample does
not establish daemon/DB/Redis or monthly cost. Full 20/20 is not verified.
[External monitoring](../evidence/20261121-external-monitor-verification.json),
[isolation/cost inquiry](../evidence/20261121-release-gate-progress.json),
[recovery drill](../evidence/20261121-recovery-auth-revocation.json).


## Final checked state of this pass, November 21

Hireology's two repaired sources were successfully ingested by the hosted
worker (4 and 3 jobs). Current recorded probe: **9,187 jobs, 130/142 initial
successes, twelve pending, eighteen consecutive-failure sources and five stale
sources**. All five stale sources reported upstream access denial. The real
monitor is correctly failing for stale data; it has not been muted or passed
off as a drill. LPJC's local nine-job probe did not establish hosted success,
and the narrow startup retry correctly skipped its noneligible access failure.

There are still fifteen recorded passes, one partial notification-delivery area
and four held/open groups. Those include unresolved native-source work as well
as upstream access and explicit owner holds. Full **20/20 is not verified**.
[Current outcomes](../evidence/20261121-current-release-gate-outcomes.json),
[actual Hireology ingestion](../evidence/20261121-hireology-production-repair.json).

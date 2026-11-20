# Internal release checklist

November 21, 2026. **Fifteen recorded passes and five grouped open areas** in
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
| 3 | Complete initial success on every registered source | Open: 127/142 initially successful at the recorded snapshot |
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
| 15 | External uptime/alert delivery | Open: no verified destination; placeholder retained |
| 16 | Encrypted offsite snapshot and full isolated restore | Passed: actual 16-table production snapshot, private upload, anonymous 403, provider seven-day expiry |
| 17 | Desktop/mobile/profile/keyboard/contrast review | Passed: production real-data/profile review and browser suite |
| 18 | Final operator/privacy/provider/recovery gates | Open: placeholder inbox, live SMTP/OAuth, domain/legal review, independent key custody/deletion reconciliation and issuer-side credential rotation not verified |
| 19 | Measured provider operating costs and quota window | Open: free-tier limits documented; actual CPU/DB/Redis usage and final bill unmeasured |
| 20 | Vaya profile/repo/demo/evidence submission | Open: authenticated access unavailable; submission draft prepared, no submission/ranking claimed |

Evidence: [hosted checks](../evidence/20261121-hosted-release-review.json),
[backup](../evidence/20261121-hosted-backup.json),
[production UI](../evidence/20261121-production-product-review.json),
[private profile](../evidence/20261121-production-private-profile-review.json),
[validation](../evidence/20261121-release-validation.json).

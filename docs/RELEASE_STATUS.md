# Rolewisp release status

Updated November 21, 2026. [Rolewisp](https://rolewisp.vercel.app) is deployed
with a persistent indexing worker. Coverage expansion remains paused at
**71/78 platforms (91.0%)**. The [internal release checklist](RELEASE_CHECKLIST.md)
records fifteen passes and five grouped open areas; this is not an overall
completion percentage or Vaya score.
The challenge criteria are not all complete.

## Measured production results

- Public index: **7,937 jobs** at the recorded hosted review. Fresh initial
  collection, not a copied local development database.
- **142** registered sources; **127** with an initial complete success,
  **15** without one, **14** with consecutive failures, zero stale/abandoned
  sources at that snapshot. Counts overlap by definition. A running interrupted
  source can appear in failed-run diagnostics while its next attempt is active.
- A second real Ashby fetch completed with **78 jobs**, versus **77** initially;
  the index increased by one. This was an operator-triggered native refresh,
  not a claim that six hours of unattended operation were observed.
- Hosted checks passed: private profile/resume ownership, employer ownership and
  unverified-publish denial, operator authorization, login/signup limits with
  Retry-After, signed proxy metadata, no-store and Secure/HttpOnly cookies.
- Production backup: **42,387,200 encrypted bytes**, all **16 tables** restored
  and count-matched in an isolated PostgreSQL 18 instance. Anonymous archive
  access returned **403**; provider-confirmed expiry is **seven days**.
- Actual desktop/mobile search, pagination, combined filters, details/apply links,
  favicon and profile editing passed with no observed overflow or page errors.

[Hosted review](../evidence/20261121-hosted-release-review.json),
[backup](../evidence/20261121-hosted-backup.json),
[production UI](../evidence/20261121-production-product-review.json),
[profile review](../evidence/20261121-production-private-profile-review.json).

## Integrated implementation and validation

Candidate/Employer onboarding, private manual profiles and qualification
categories, encrypted resume/photo storage, recommendations, owned employer
drafts, verification/recovery and OAuth backend are integrated. Live provider
activation is a separate gate. Resume parsing was removed by owner request;
paid checkout remains intentionally deferred.

Baseline CI passed **1,244 backend tests**, one skipped, with PostgreSQL
and Redis enabled. The preceding local full run passed 1,237 followed by seven
classification cases; the original evidence preserves those separate scopes. Browser suite: **192 passed, 10 skipped**. Frontend build, Ruff and
mypy passed. Production Python audit checked **44 packages** with zero known
vulnerabilities; npm audit also returned zero. Offline heuristic secret/history
review found no confirmed credential in the reviewed scope, which is not a
proof that all leak forms or all external systems are safe.
[Validation](../evidence/20261121-release-validation.json). Read actual CI for
the submitted revision in [Verify](https://github.com/iamdpsingh/V-Index/actions/workflows/ci.yml).

## Remaining exceptions

Current fetch failures include robots denials, HTTP 429 cooldowns, a removed
route, a redirect, publisher/schema mismatches, incomplete native enumeration,
conflicting descriptions and a deployment-interrupted attempt. They retain
observations and never imply closure. Full initial-source success is open.

Full platform acceptance remains open: Paycom, Dover, Paycor and UltiPro have
partial extraction; Talenetic has one complete board and an incomplete second
board with required-field gaps. CareerSiteCloud and eJobBoard have no usable
integrated live coverage. [Coverage matrix](COVERAGE.md),
[workflow](COVERAGE_WORKFLOW.md), [record audit](../evidence/20261120-record-quality-local.json).
These historical audits are not a current hosted census.

External alerts, verified support, real provider email/OAuth checks, independent
recovery-key custody, deletion reconciliation, credential rotation confirmation,
custom-domain/legal review, measured bills/quotas and authenticated Vaya submission
remain open. The owner explicitly retains example@rolewisp.in as an unverified
placeholder. No leaderboard rank, full compliance or acquisition is claimed.

[Handoff](RELEASE_HANDOFF.md), [operations](OPERATIONS.md),
[privacy](PRIVACY_REVIEW.md), [backlog](BACKLOG.md), [submission draft](SUBMISSION.md).

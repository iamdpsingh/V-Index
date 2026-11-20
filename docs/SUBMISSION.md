# Vaya submission preparation

Draft only. The owner paused production and external submission. No founder
profile, repository connection, public demo connection or challenge submission
has been changed by this release pass.

Startup name: **Rolewisp**

Tagline: **Find your next opening.**

Operator/founder name supplied: **Dhruv Pratap Singh**

Repository: https://github.com/iamdpsingh/V-Index

Public demo: **deferred; use the verified deployment URL when production resumes**

Public support address supplied: example@rolewisp.in, delivery unverified.
Do not invent a founder email, LinkedIn profile, location, revenue or users.
GitHub is the only established social link: https://github.com/iamdpsingh.

## Pitch draft

Rolewisp brings public job listings into a searchable index with original
application links and visible source provenance. Its backend normalizes source
records, refreshes boards on a schedule, records changes and failures, and
reconciles closures conservatively. Duplicate observations retain their source
links, while distinct requisitions and locations stay separate. The product
also includes private manual candidate profiles, encrypted resume storage,
explainable recommendations and an employer drafting workspace. The handoff
includes source evidence, API documentation, operating tools and a tested
PostgreSQL backup/restore procedure. The current registry records 71 of the
required 78 platforms with independent live examples; the remaining platform
and source-data limitations are disclosed for review.

## Technical review package

- [Release walkthrough](RELEASE_HANDOFF.md), [API reference](API.md) and
  [OpenAPI specification](openapi.json).
- [Coverage matrix](COVERAGE.md), backend/providers.json and timestamped evidence.
  Preserve the exact names of JBoard.io and JobBoard.io.
- [Local refresh/index measurements](../evidence/20261120-local-release-snapshot.json)
  with unresolved failures, repeated successful runs and scope limitations.
- [Dedupe replay](../evidence/20261120-reviewer-dedup-replay.json) and the separately
  labelled [historical live duplicate](../evidence/cohort5-live-deduplication.json).
- [Restore drill](../evidence/20261120-backup-restore-drill.json),
  [local security review](../evidence/20261120-local-security-review.json),
  [real-data UI review](../evidence/20261120-real-data-product-review.json),
  [private-profile review](../evidence/20261120-private-profile-product-review.json).
- [Operations](OPERATIONS.md), [privacy review](PRIVACY_REVIEW.md),
  deployment/recovery instructions, source constraints and dependencies.

Before submitting, resume production explicitly, connect the actual healthy
public demo, verify hosted refreshes and private/proxy behavior, verify support
and provider flows, and record actual service bills/quotas. Copy only established
founder facts into Vaya. Review the exact challenge/acquisition terms and
coverage limitations before the final submission. A draft, local demo, historical
CI result or imported Vercel repository does not establish submission or ranking.

# Current release backlog

Owner update: November 20, 2026. Coverage expansion is paused. Production,
external configuration and challenge submission are explicitly on hold.
[Release handoff](RELEASE_HANDOFF.md) is the current walkthrough. Earlier cohort
notes are [archived](archive/BACKLOG_BEFORE_RELEASE_FINALIZATION.md), not current
assignments or claims that integrated features remain unbuilt.

Completed locally:

- Integrated search, details, pagination, filters and source/application links.
- Candidate/Employer roles, manual private profiles, qualification categories,
  profile photos, encrypted resume storage, recommendations and employer drafts.
- OAuth backend, email verification/recovery and authorization tests. Live
  OAuth/SMTP activation is separate and remains deferred.
- Scheduled refreshes, transactions, cooldowns, cancellation recovery and
  hourly abandoned-run/auth-artifact cleanup. Failed/partial fetches never close jobs.
- Independent worker heartbeat, authenticated operations API, failure/staleness
  alerts and local watch process. External alert delivery is not configured.
- Conservative deduplication, preserved source links and active-field enrichment
  with field provenance. Reviewer replay and historical live example documented.
- Per-response script CSP, private no-store responses, logout data clearing,
  signed proxy IP metadata and authorization/rate-limit regression checks.
- Encrypted PostgreSQL backup tooling, 30-day pruning and an isolated restore
  drill including encrypted private files and tamper/overwrite rejection.
- Desktop/mobile real-data and private-profile review, keyboard/contrast browser
  checks, favicon and policy links. No resume parsing or payment activation.

Open operational exceptions:

- The local source audit records 132/143 initial successes, 11 sources without
  an initial complete success, 13 failing sources and one stale source at the
  recorded snapshot. Four old-source failures were repaired this pass. Current
  metrics are available through the authenticated operations endpoint.
- Current source schema/availability failures remain explicit; they are not
  successful empty snapshots and are not resolved by the historical 71/78
  platform count. See evidence/20261120-local-release-snapshot.json.
- The source-required-field gaps recorded in the record audit remain open.
- Full immutable before/after job snapshots, broader custom domains and
  distributed cross-host request budgets are not added by this release pass.

Deferred with production:

- Verify actual Vercel project/domain, backend/worker/PostgreSQL/Redis hosting,
  quotas, proxy signatures, deployed caching and rate limits, external alerts,
  off-site backups and actual operating costs. No new spending authorized.
- Verify real SMTP/OAuth provider flows and support-inbox delivery. The supplied
  public address remains example@rolewisp.in, unverified.
- Final legal/operator review against actual hosting, retention and jurisdiction.
  Trusted Types remains report-only pending framework compatibility review.
- Connect a public working demo to Vaya, complete the founder profile and submit
  evidence. The submission package is drafted; no submission has occurred.
- Full original 78-platform acceptance remains unmet at 71/78. Pausing expansion
  does not waive the remaining platforms or guarantee acquisition.

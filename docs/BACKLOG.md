# Current release backlog

Updated November 21, 2026. Production work and the GitHub push are authorized.
Coverage expansion is paused at 71/78; full 78-platform acceptance remains unmet.
[Handoff](RELEASE_HANDOFF.md) and [release checklist](RELEASE_CHECKLIST.md) replace
older local-only/pause notes as the current instructions.

## Implemented and checked

- Hosted Next.js/API and independent Vercel indexing worker, PostgreSQL/Redis,
  durable source schedules, safe failure/partial-snapshot lifecycle handling.
- Search/detail/filter/pagination, original application links, public API docs.
- Candidate/Employer accounts, read-only/manual profile editing, qualification
  categories, encrypted photo/resume storage, recommendations, owned job drafts.
- Verification/recovery/OAuth implementation; provider activation is separate.
- Deployed profile/resume isolation, operator authorization, secure cookies,
  no-store caching, signed trusted proxy metadata, login/signup rate checks.
- Strict nonce script CSP, secret/history/dependency review and private-upload
  exclusions. These checks are not a guarantee of no security vulnerability.
- Independent heartbeat/internal monitoring, seven-day private diagnostic reports,
  daily encrypted offsite backup and full isolated PostgreSQL restore check.
- Desktop/mobile real-data interactions, profile editing, keyboard/contrast suite,
  favicon/policy links and default-off analytics with withdrawal/GPC/DNT support.
- Reviewer examples for merged provenance and distinct roles; handoff and draft
  submission package. Neither draft nor CI is a submitted challenge entry.

## Open or owner-held gates

- Initial indexing is not successful for every registered source. Current native
  policy/HTTP/schema/completeness failures remain visible with cooldowns. Never
  drop sources or publish partial snapshots to improve the percentage.
- Historical platform evidence and required-field gaps remain documented;
  public source data cannot be fabricated. Coverage expansion stays paused.
- External uptime monitoring and delivered alerts need a real destination.
- The owner retains example@rolewisp.in as an unverified placeholder. Do not send
  user recovery/support promises to a nonexistent verified inbox. Live SMTP and
  Google/LinkedIn/GitHub sign-in still need credentials and real flow tests.
- Independent recovery-key custody and post-snapshot account-deletion reconciliation
  need operator completion. Rotate any credential previously pasted in chat at its
  issuing provider; changing local text alone is not credential rotation.
- Actual provider usage and bills are unmeasured. Free-tier quotas can stop service.
  No paid upgrade/purchase is authorized. Twenty-day uptime is not guaranteed.
- Custom-domain ownership, final operator/legal/DPDP/jurisdiction review and real
  support verification remain release gates; vercel.app is the working demo.
- Authenticated Vaya founder/startup profile, repo/demo connection, coverage evidence
  submission and technical-review result remain unverified. No rank/acquisition claim.
- Paid checkout remains intentionally deferred. Resume parsing was removed by request.

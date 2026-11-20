# 06 · Security and privacy handover

Technical review, not an exhaustive security or legal certification. Detailed
[account contract](../docs/ACCOUNTS_API.md), [privacy review](../docs/PRIVACY_REVIEW.md)
and [production controls evidence](../evidence/20261121-hosted-release-review.json).

## Implemented boundaries

- Argon2 password hashes, random hashed sessions, Secure/HttpOnly production
  cookies, trusted Origin checks for mutations and server-side ownership/role checks.
- Candidate access does not confer operator rights. Employer drafts are owner-only;
  publishing requires email verification. Resume/photo download is owner-only.
- Redis-backed login/signup, upload/recommendation, public query and operator
  budgets with 429/Retry-After. Public gateway metadata uses fresh method/path/IP
  HMAC signatures; forged client forwarding headers do not select trusted buckets.
- API/private responses and nonce-bearing HTML use no-store. Strict nonce script
  CSP is enforced; Trusted Types is report-only, not fully enforced.
- Source URLs are validated; bounded collectors use explicit allowed destinations,
  disabled environment proxies/redirect following and typed plain-text job output.
- Private files are encrypted; no external resume/AI parsing service is used.
  Backups use a separate encryption key and private provider-expiring storage.
- Original API keys/private data are excluded from Git/build uploads; dependency
  and heuristic secret/history checks are scoped evidence, not proof of absence.

## Data and retention summary

| Data | Treatment |
| --- | --- |
| Profile, education, skills, links | Manual owner-managed private data; edit/delete supported |
| Resume and photo | Encrypted private storage, replace/delete, no parsing |
| Session | Seven-day expiry, logout revocation and scheduled expiry maintenance |
| Verification/recovery | Fifteen-minute code expiry, hashes only, maintenance cleanup |
| OAuth state | Temporary Redis state, ten-minute expiry |
| Backup | Hosted encrypted archive expires at provider after seven days |
| Analytics preference | Necessary choice cookie, six months |
| Optional Vaya analytics | Off until affirmative allowance; GPC/DNT keep off; withdrawal reloads old document |
| Public source observations/change events | May remain after listing closes; not candidate application records |

Our Vaya integration forwards no account/profile/resume fields or identify calls.
The reviewed script transmits page path/referrer and ordinary network metadata.
Consent controls do not certify future third-party script behavior. Original job
application sites have their own policies. Do not send tests into real telemetry.

## Mandatory receiving-team review

- Verify live environment target isolation. Existing Vercel shared variables do
  not establish per-service least privilege or independent preview databases.
- Confirm rotation of any previously chat-pasted credential at its issuer.
  Preserve encryption keys unless a migration/re-encryption plan is executed.
- Secure independent recovery-key custody and reconcile post-snapshot deletions
  before a restored database is exposed.
- Configure real SMTP/OAuth only with live delivery/callback tests. Placeholder
  support example@rolewisp.in was deliberately retained and is unverified.
- Review actual business identity, privacy/terms/cookies/refund language, DPDP
  commencement/applicability, processor locations, rights/grievance handling,
  children's data and incident response with an appropriate legal/operator review.
- Retain third-party licenses and source-content permissions. Copyright attribution
  to Dhruv Pratap Singh does not transfer ownership of job listings/dependencies.

No payments are accepted. Plus must remain unavailable until genuine billing,
verified events, entitlements, taxes/refunds and updated disclosures exist.

# 04 · Configuration and access transfer

Never put secret values, connection URLs, resume files, passwords or private
account records in this package. Transfer account invitations and keys through
an approved private channel/password manager. The recipient is not yet assigned.

## Accounts and resources

| Resource | Known identifier | Transfer/check required |
| --- | --- | --- |
| GitHub | iamdpsingh/V-Index, main | Repository access, branch protection, Actions and integration permissions |
| Vercel | mandtechyt-1124/v-index | Team/project permissions, linked GitHub app, production domain, builds and daemon |
| Public demo | rolewisp.vercel.app | Alias/HTTPS and public gateway checks; custom domain remains open |
| PostgreSQL | Existing hosted database; observed major 18 | Provider ownership, billing/quotas, TLS, least-privilege roles, migrations and backups |
| Redis | Existing hosted Redis | Provider ownership, TCP/TLS endpoint, memory/command quotas and isolation |
| Vercel Blob | rolewisp-production-backups, iad1, private | Token access, private mode, seven-day expiry, storage/operation budgets |
| Vaya | Owner's challenge/startup account | Authenticated founder/profile/repo/demo/evidence submission not verified |
| SMTP and OAuth | Not activated end to end | Register real providers, callbacks and sender; complete real tests |
| Public support | example@rolewisp.in | Placeholder intentionally retained; no delivery claim |

The Vercel project currently shares environment variables across services;
“server-only” does not imply least-privilege isolation between those runtimes.
Do not expose them through NEXT_PUBLIC variables, props, debug output or bundles.
Audit target scopes during transfer: previews must not inherit production data,
keys or Redis rate counters. Scope isolation is a verification task, not assumed.

## Environment inventory

| Variable | Consumer / purpose | Transfer rule |
| --- | --- | --- |
| DATABASE_URL | API/worker PostgreSQL URI | Secret; provider TLS settings; no SQLite/Compose host in production |
| REDIS_URL | API/worker Redis protocol URI | Secret; use provider TCP/TLS, not REST URL |
| ADMIN_TOKEN | Operator API authorization | Secret; strong random value; rotate on operator access transfer |
| PUBLIC_WEB_ORIGIN | Account mutation trust | Exact `https://rolewisp.vercel.app` origin, no path; update after domain changes |
| ACCOUNT_REGISTRATION_ENABLED | New account switch | Explicit true/false; false blocks new signup |
| RESUME_ENCRYPTION_KEY | Fernet encryption for stored photos/resumes | Preserve for existing data; independent recovery copy required |
| PROXY_SHARED_SECRET | Web/API signed client-IP metadata | Secret of at least 32 characters; both runtimes agree |
| PUBLIC_JOB_RATE_LIMIT_ENABLED | Public query budget | true in production |
| ADMIN_RATE_LIMIT_ENABLED | Operator budget | true in production |
| WORKER_CONCURRENCY | Source slots | Cloud launcher defaults 2; generic PostgreSQL worker defaults 4; SQLite 1 |
| BACKUP_ENCRYPTION_KEY | AES-256-GCM archive encryption | Separate 32-byte base64 key; preserve independently from archives/resume key |
| BLOB_READ_WRITE_TOKEN | Worker backup/report access | Production secret for dedicated private store |
| BLOB_STORE_ID | Worker store identifier | Required with token; not a browser setting |
| RELEASE_REVIEW_ID | One-shot deployed control probe | Change only intentionally; runs disposable-account tests, marker lasts seven days |
| BACKEND_URL | Web-to-app service binding | Vercel injects it; do not set manually or read during build/middleware |
| API_INTERNAL_URL | Local/Compose fallback | Unset in the production services project |
| POSTGRES_PASSWORD | Local Compose database | Not the hosted DATABASE_URL; changing env text does not rotate a DB role |

SMTP: SMTP_HOST, SMTP_PORT (465 default), SMTP_FROM, SMTP_USERNAME, SMTP_PASSWORD.
OAuth: OAUTH_GOOGLE_CLIENT_ID/SECRET, OAUTH_LINKEDIN_CLIENT_ID/SECRET and
OAUTH_GITHUB_CLIENT_ID/SECRET. Callback:
`<PUBLIC_WEB_ORIGIN>/api/v1/auth/oauth/<provider>/callback` with lowercase names.
Live provider activation requires real sender/inbox and browser callback tests.

## Transfer sequence

1. Owner invites the named recipient to each required service; do not share an
   owner's personal login. Recipient records access without recording secrets.
2. Verify environment targets and service reachability. Keep production separate
   from preview/development and use disposable accounts for tests.
3. Copy backup and resume keys to independent secured recovery custody, then
   verify recovery in an isolated target. Do not replace encryption keys casually.
4. Rotate operator/proxy/Blob/provider credentials deliberately after transfer,
   checking dependent runtimes. Database credentials rotate at the DB provider.
   Previously chat-pasted credentials require issuer-side rotation confirmation.
5. Verify deployed private flows and worker health, then remove obsolete access.
   Record recipient, time and evidence in the transfer checklist.

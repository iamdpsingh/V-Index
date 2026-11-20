# Vercel deployment reference

Current configuration, November 21, 2026. The working demo is
https://rolewisp.vercel.app, project `mandtechyt-1124/v-index`. Production work
and reviewed pushes are authorized. No paid upgrade/purchase is authorized.
[Configuration source](../vercel.json), [complete handoff](../handoff/README.md).

## Services and routing

| Component | Root / entry | Exposure and responsibility |
| --- | --- | --- |
| web | apps/web, Next.js | Public catch-all, UI/policies and same-origin API gateway |
| app | repository root, FastAPI app:app | Internal service; no public rewrite |
| worker | repository root, Dockerfile.worker | Persistent production daemon, not an HTTP service; one 1 GiB instance in iad1 |

Project Root Directory is `.`. Keep service-specific build/runtime settings in
the service definitions; remove incompatible dashboard single-app overrides.
Top-level rewrite `/(.*)` targets `web`. Its caller-side service binding targets
`app` and injects BACKEND_URL at runtime. Do not set BACKEND_URL manually, expose
it as NEXT_PUBLIC, bake it into builds or use it in middleware.

`web` forwards `/api/v1/*` to the app. `/health`, `/docs` and `/openapi.json` are
not public gateway routes; public search is `/api/v1/jobs`. API/ownership/rate
checks still run in Python. The gateway preserves query strings, Origin,
separate cookies and manual OAuth redirects, bounds bodies to 6 MiB, uses
no-store and generic upstream failures. Actual provider limits may impose a
smaller usable file size than local acceptance; test before promising uploads.

## Environment and isolation

Use [the complete variable/access inventory](../handoff/04_CONFIGURATION_AND_ACCESS.md)
and [.env.example](../.env.example). Required production settings include hosted
DATABASE_URL/REDIS_URL, ADMIN_TOKEN, exact PUBLIC_WEB_ORIGIN, account opt-in,
original resume encryption key, shared proxy secret and enabled public/admin
limits. SMTP/OAuth settings are optional until real activation and end-to-end tests.

Hosted backups additionally require BACKUP_ENCRYPTION_KEY, BLOB_READ_WRITE_TOKEN
and BLOB_STORE_ID. Preserve backup/resume keys independently. RELEASE_REVIEW_ID
requests a one-shot disposable-account security/native-refresh probe; do not
change it casually or generate repeated review traffic. It is marked in Redis
for seven days. No real email or analytics is needed for this probe.

Vercel project variables are shared between server runtimes unless separately
isolated; worker-only intent is not proof of enforced per-service secret scope.
Keep private values server-only. Preview/Development must have separate data,
Redis and keys. Audit current target scopes; no claim of completed environment
isolation follows from the successful production tests. API_INTERNAL_URL is a
local/Compose fallback and should be unset in this services project.

## Database and worker activation

Apply Alembic once from secured operator tooling against the selected DB.
Do not run shared-database migrations at function import or in a preview build.
The actual production empty-schema error was repaired in the recorded release;
that history is not permission to recreate a populated database.

`worker` runs `scripts.start_production_worker`, validates PostgreSQL/Redis,
serializes idempotent reviewed-source registration, and starts the scheduler.
At the baseline the catalogue contains 142 URLs across 71 historically verified
platforms. Registration schedules native work, not successful extraction. Source
schedules, failures and last complete snapshots survive restarts in PostgreSQL.

Cloud concurrency defaults two; generic PostgreSQL defaults four; SQLite one.
Slots refill as collections finish. Source interval defaults six hours; no
instant detection SLA. Cancellation records failed attempts without closures.
Termination grace is 180 seconds. Keep the daemon when promoting/rolling back;
frontend/API deployment alone does not maintain the index.

## Monitor, stop and recover

```sh
npx vercel@latest daemons inspect worker --project v-index
npx vercel@latest logs --project v-index --query 'source:daemon' --since 15m
# Stop without deleting persistent data, if necessary:
npx vercel@latest daemons scale worker iad1=0 --project v-index
```

Independent heartbeat: 15 seconds, 90-second TTL. Redis/API operations are
operator-protected. Private Blob status reports update every thirty minutes;
daily encrypted backups restore/count-check all tables in a disposable loopback
PostgreSQL 18 instance before upload. Archives provider-expire after seven days.
[Operations/recovery](OPERATIONS.md), [hosted backup evidence](../evidence/20261121-hosted-backup.json).

Dockerfile.worker installs official PGDG PostgreSQL 18 tools and runs as a
non-root user. The bundled server is used only for the temporary restore drill,
never as production persistence. The Python Blob TTL bridge validates provider
expiry; inspect it when upgrading SDKs. External alert delivery and post-snapshot
deletions/key custody remain receiving-team gates.

## Build/upload and release checks

Explicit .vercelignore replaces automatic exclusions. Preserve rules excluding
.cache, .env variants, .vercel, local databases/sidecars, keys and dependencies.
Never upload the local development dataset, personal resumes or raw account data.
Inspect actual uploaded files and safe logs; do not weaken Secret types to export
production credentials. CLI/GitHub deployments can restart in-flight collections.

Local Services tooling: supply private Development variables, then run
`npx vercel@latest dev --local --listen 127.0.0.1:3100`. Standard local/Compose
setup is documented separately. Bindings are runtime function values, not build
or middleware discovery variables.

After deployment, verify both CI and Vercel readiness, actual daemon/heartbeat,
public search/detail/policies, private ownership/no-store/cookies, login/signup
rates, trusted proxy metadata, failed-source preservation and backup age.
A root page 200 is insufficient. Record exact SHA/deployment/time/exceptions.

## Budget and observed proof

The recorded account is Hobby. One 1 GiB daemon consumes roughly 24 GB-hours/day;
recorded free allowance is 420 GB-hours memory and five active CPU-hours/calendar
month, with stop-at-cap behavior. Twenty days across November/December can fit
memory allowance if other usage is absent, but CPU and DB/Redis/Blob limits can
stop it sooner. Private Blob budget and measured first snapshot are in
[costs](COSTS.md). Actual bills and steady-state usage remain unmeasured.

Baseline production checks reached 7,937 jobs, proved an additional native
opening on refresh, passed deployed private/proxy checks and restored a real
16-table encrypted snapshot before private upload. These dated observations do
not guarantee current all-source health. [Hosted checks](../evidence/20261121-hosted-release-review.json),
[UI review](../evidence/20261121-production-product-review.json),
[release status](RELEASE_STATUS.md).

Primary references: [Services](https://vercel.com/docs/services),
[daemon limits](https://vercel.com/docs/daemons/limits),
[daemon configuration](https://vercel.com/docs/daemons/config-reference),
[Blob limits](https://vercel.com/docs/vercel-blob/usage-and-pricing).

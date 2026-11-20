# Vercel services setup

Confirmed by the owner November 20, 2026: service names `web` and `app`, public
routing through `web`, private `app`, and the `web` → `app` binding through
`BACKEND_URL`. The owner authorized the GitHub push. No hosted deployment was
verified or provider provisioned; the push may trigger the connected Vercel
project automatically. Account changes, purchases and external submission
remain outside this authorization.

## Routing

Project Root Directory must be the repository root (`.`), not `apps/web`.
Remove dashboard build/output/install overrides intended for a single Next app;
`vercel.json` defines two independently detected framework services:

- `web`: Next.js in `apps/web`, the only directly public service. Catch-all
  public routing includes the UI and same-origin `/api/v1/*` gateway.
- `app`: FastAPI in the repository root, entry point `app:app`. It has no
  public rewrite. `/health`, `/docs` and `/openapi.json` are not exposed through
  the Next gateway. Public API access still uses `/api/v1/*` through `web`;
  Python continues to enforce authentication, ownership, origin and rate rules.
- `web` calls `app` with a caller-side binding named `BACKEND_URL`. Vercel
  generates its URL at runtime. Do not manually set it, bake it into a build,
  read it in middleware, or add a `NEXT_PUBLIC_` equivalent.

The gateway bounds request bodies to 6 MiB and streams responses. It retains query strings, original Origin,
credentials, separate Set-Cookie values and manual OAuth redirects. Target hosts
come only from server configuration. Caller-supplied proxy identity is removed
by Next proxy; the existing signed metadata mechanism is retained. The gateway
uses no-store and returns a generic 502 if its upstream is unavailable.

## Environment variables to enter in Vercel

Add server-side values in Settings → Environment Variables. Scope Production,
Preview and Development separately. Preview must not share a production database,
Redis counters, encryption keys or real user data. Do not paste secrets in chat.

| Variable | Value / purpose |
|---|---|
| `DATABASE_URL` | Hosted PostgreSQL connection URI: `postgresql+psycopg://USER:PASSWORD@HOST:5432/DB?sslmode=require`. Use provider-supplied values and TLS settings; no Compose hostname or local SQLite. |
| `REDIS_URL` | Hosted Redis TCP/TLS URI, typically `rediss://...`; this app uses the Redis protocol, not an HTTP REST API URL. |
| `ADMIN_TOKEN` | Private random operator token, at least 32 random bytes. |
| `PUBLIC_WEB_ORIGIN` | Exact HTTPS browser origin, e.g. `https://YOUR-PROJECT.vercel.app`, with no path. Set to the selected canonical domain when it changes. |
| `ACCOUNT_REGISTRATION_ENABLED` | `true` to allow signup; `false` to disable new accounts. |
| `RESUME_ENCRYPTION_KEY` | Fernet key for saved resumes/photos. Preserve the existing key when migrating existing private files. |
| `PROXY_SHARED_SECRET` | A private random string of at least 32 characters. Identical for both services and any existing gateway/API counterpart. |
| `PUBLIC_JOB_RATE_LIMIT_ENABLED` | `true` |
| `ADMIN_RATE_LIMIT_ENABLED` | `true` |

Generate a new Fernet key only for a fresh environment:

```sh
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Optional features need real provider configuration:

- Email: `SMTP_HOST`, `SMTP_PORT` (465 by default), `SMTP_FROM`,
  `SMTP_USERNAME`, `SMTP_PASSWORD`. A placeholder public contact address does
  not supply SMTP or prove delivery.
- Google: `OAUTH_GOOGLE_CLIENT_ID`, `OAUTH_GOOGLE_CLIENT_SECRET`.
- LinkedIn: `OAUTH_LINKEDIN_CLIENT_ID`, `OAUTH_LINKEDIN_CLIENT_SECRET`.
- GitHub: `OAUTH_GITHUB_CLIENT_ID`, `OAUTH_GITHUB_CLIENT_SECRET`.
- Register each callback as
  `<PUBLIC_WEB_ORIGIN>/api/v1/auth/oauth/<provider>/callback`.

Do not set `BACKEND_URL` yourself. `API_INTERNAL_URL` is only a legacy
Docker/local fallback and should be unset in this Services project.
`POSTGRES_PASSWORD` belongs to a self-hosted PostgreSQL setup, not this hosted
connection configuration. Vercel supplies its own `VERCEL` runtime flag.
No credentials should use a `NEXT_PUBLIC_` prefix.

## Database and continuous indexing are separate release steps

Run Alembic migrations once from a secured operator environment against the
selected database before serving traffic. Do not migrate the shared database
on every function import or preview build. Preserve backups and the existing
private-file key when moving data.

The two request services do not start the scheduler. The November 21 owner
request added the separate production daemon documented below. It uses the
same hosted PostgreSQL and Redis and maintains freshness independently of web
requests or the operator computer. Removing that daemon from a later deployment
stops the worker, so preserve the committed daemon configuration.

`BACKUP_ENCRYPTION_KEY` is required on the separate backup operator host, not
needed by the web request services. Keep it separate from the private-file key.
Monitoring, offsite backups and provider verification remain release gates.
Vercel function body/duration limits must be checked for the selected plan;
local 5 MiB upload acceptance is not proof of the hosted upload limit.

## Local checks

Run from the repository root:

```sh
uv sync --frozen
npm --prefix apps/web ci
# Supply private Development variables locally first.
npx vercel@latest dev --local --listen 127.0.0.1:3100
```

No Vercel account linking is needed in `--local` mode. Bindings are injected
by the CLI. Stop it before running Playwright, which also reserves port 3100.
For the production-build gateway regression:

```sh
npm --prefix apps/web run build
node scripts/check_web_binding.mjs
```

The regression uses a synthetic private upstream at a runtime-only URL with a
base prefix, verifies mutations/uploads/cookies/redirects/spoof stripping, early authentication rejection and upload limits, and
removes its local processes. CI runs it after the frontend build.

References: [Services](https://vercel.com/docs/services),
[bindings](https://vercel.com/docs/services/bindings),
[configuration](https://vercel.com/docs/services/config-reference),
[FastAPI](https://vercel.com/docs/frameworks/backend/fastapi).

## Jobs endpoint returns ProgrammingError

A successful deployment does not create database tables. `ProgrammingError`
alone does not prove which query failed: missing tables/columns, insufficient
permissions and SQL errors can share that class. Runtime API diagnostics now
include a bounded PostgreSQL SQLSTATE when available, while omitting SQL,
parameters and credential-bearing exception messages. That diagnostic addition
only applies after its code is deployed.

From the local repository root, inspect the same database configured by Vercel:

```sh
uv run python -m scripts.check_database --prompt
```

Paste the complete PostgreSQL URI into the hidden Terminal prompt, without a
`psql` prefix or surrounding quotes. Nothing is written to an environment file.
The helper accepts both `postgresql://` and `postgresql+psycopg://` and selects
the repository's installed psycopg driver. It reports schema revision status
and missing known tables/columns without reading personal records.

If pending migrations are reported, apply them explicitly:

```sh
uv run python -m scripts.check_database --prompt --migrate
```

Use the existing backup/recovery process before upgrades to a populated
production database. The helper runs the repository's versioned migrations;
it does not delete/recreate the database, stamp over missing migrations, or
start a worker. If it fails, retain the result and investigate the reported
SQLSTATE instead of resetting the database. A current but incompatible schema
is reported as not ready rather than silently repaired.

Expected final output contains `"schema_at_head": true`, empty missing-table
and missing-column arrays, and `"ready": true`. Only after this succeeds should
the public jobs endpoint be checked again. An empty newly migrated database
will contain no indexed jobs until data is transferred or a worker indexes it.
The local helper was checked against a disposable PostgreSQL database; this
is not evidence that the production database was migrated.


### Production repair recorded November 20

After owner-authorized Vercel sign-in and a privately supplied database URL,
the production PostgreSQL connection succeeded. The database contained zero
public tables and no Alembic revision. All project migrations were applied once
from the operator process. The subsequent check reported migration head, all
expected tables/columns and `ready: true`.

Public HTTPS checks then returned 200 for the homepage, jobs summary, filtered
jobs search, provider catalogue and OAuth configuration. Unauthenticated `/me`
returned the expected 401. Both search requests returned zero jobs. No deployment
rebuild was needed for this schema repair. Source registration, initial indexing
and continuous production worker operation remain open. Evidence is in
[evidence/20261120-production-database-recovery.json](../evidence/20261120-production-database-recovery.json).

The connection password was pasted into chat and should be rotated with Neon,
then updated in Vercel and every other client using it. The temporary local
connection/configuration copies used for this investigation were removed;
credentials are absent from the committed evidence.

## Persistent production indexing worker

Owner update November 21: initial indexing and persistent refreshes are now
requested for the existing Vercel project. `vercel.json` declares a production
`worker` daemon using the existing root Dockerfile, one `1Gi` instance in
`iad1`, and `scripts.start_production_worker` as its process. The API and web
services retain their public routing and binding.

The daemon receives Vercel's production Secret variables directly at runtime;
credentials are not exported locally or baked into the image. Startup validates
PostgreSQL/Redis configuration, serializes reviewed-source registration with a
Redis lease, registers missing sources idempotently, and starts the existing
scheduler. Existing source schedules/failures are preserved on restart. This
process does not run migrations. All fetch completeness, cooldown, original
observation and two-miss closure safeguards remain in the worker.

The small instance defaults to two simultaneous PostgreSQL source fetches;
`WORKER_CONCURRENCY` can override that value. Reviewed sources retain their
six-hour default refresh schedule. Source HTTP failures are recorded and retried
with cooldowns; they are not successful empty results. Worker heartbeats and
source metrics remain available through the authenticated operations endpoint.

Operator checks:

```sh
npx vercel@latest daemons inspect worker --project v-index
npx vercel@latest logs --project v-index --query 'source:daemon' --since 5m
```

Stop the hosted worker without deleting indexed data:

```sh
npx vercel@latest daemons scale worker iad1=0 --project v-index
```

### Free-tier window

The account was verified as active Hobby. Vercel currently includes 420
GB-hours of daemon provisioned memory and five active CPU-hours per calendar
month. It stops Hobby daemons at either quota, with no daemon overage billing.
One `1Gi` worker consumes about one GB-hour per running hour, even when waiting.
November 21 through December 11 crosses the December 1 UTC reset: approximately
ten running days fall in each month, fitting the memory allowance if there is
no other daemon usage. Active CPU and database/Redis allowances must also remain
within their limits; twenty days of uninterrupted operation is not guaranteed
by a successful deployment. This configuration does not authorize an upgrade.

References: [Vercel daemon quotas](https://vercel.com/docs/daemons/limits),
[daemon configuration](https://vercel.com/docs/daemons/config-reference).


### Hosted verification, November 21

Deployment `dpl_E9yyFGqMYF89rJPUns9SupdXFbR7` promoted the worker and shared-head
Vaya script to rolewisp.vercel.app. Vercel reported one ready/alive 1Gi instance
in iad1. Fresh public job totals increased through 154, 235, 348 and 641 during
the review. Search, filters, details and original application links passed
on desktop and mobile, with no horizontal overflow or JavaScript page errors.
The worker continues the first pass; the full source-success count has not
been asserted. The local operator database connection was unavailable during
this later progress check, so public observations and Vercel readiness are the
verification sources. Runtime usage metrics were also unavailable; no measured
CPU-consumption or twenty-day uptime claim is made.

The analytics tag was verified in the head of home/privacy/terms. Its image
beacon is blocked by the existing img-src policy. The owner has been asked to
approve the exact beacon path; no policy change has been made without that
answer. Test browsing blocked Vaya requests to avoid synthetic analytics.

A deployment-input inspection caught a local database/cache inclusion. The
initial upload was cancelled before promotion; an explicit .vercelignore was
added and the final input list verified at 199 files / 1,979,669 bytes without
local databases, private env files, keys or build caches. No public exposure
was confirmed. The protected local database was retained unchanged.

Evidence: [hosted worker](../evidence/20261121-production-worker.json),
[product review](../evidence/20261121-production-product-review.json),
[deployment packaging](../evidence/20261121-deployment-package-check.json).
The deployment used the CLI from local commit ef9dc2d. GitHub pushing remains
on the owner's established cadence; no early push was made in this pass.


### Approved Vaya beacon allowance, November 21

The owner explicitly approved the exact image endpoint
`https://vayahq.com/api/beacon/cda76eb26359277eec5b1dff04e1bc96`.
Deployment `dpl_BNJnVmQiVHLGTgQbQw8Ec9FqmmyT` adds only that path to img-src.
Eight desktop/mobile security checks passed and the production build passed.
A production browser loaded the real Vaya script and observed its page-view
image request reaching the approved path; a different tracker ID and an
unrelated Vaya image path were blocked. All beacon requests were intercepted
in this verification context so no synthetic visits were sent to Vaya. Provider
storage/dashboard ingestion is not asserted. The production indexing daemon
remained ready with one alive instance after rollout.

See [production CSP verification](../evidence/20261121-vaya-beacon-csp.json).

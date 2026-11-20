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

These two request services do not start `python -m vindex.worker`. A continuous
worker/daemon needs separately confirmed hosting and budget, the same PostgreSQL
and Redis, `PYTHONPATH=backend`, and optionally `WORKER_CONCURRENCY=4`. No new
worker service, cron or daemon was guessed into this configuration. Without a
running worker the website can search saved data but cannot maintain freshness.

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

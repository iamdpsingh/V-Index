# Deployment and local setup

Current reference, November 21, 2026. Rolewisp is running at
https://rolewisp.vercel.app. Earlier deployment holds and v0-only plans are
historical. Coverage expansion remains paused at 71/78; no paid purchase or
upgrade is authorized.

## Choose the correct path

| Need | Authoritative procedure |
| --- | --- |
| Fresh development checkout | [Development and release runbook](../handoff/03_DEVELOPMENT_AND_RELEASE.md) |
| Existing Vercel project/deployment | [Vercel reference](VERCEL_SERVICES.md), root vercel.json and Dockerfile.worker |
| Variables, credentials and service transfer | [Configuration/access inventory](../handoff/04_CONFIGURATION_AND_ACCESS.md), .env.example |
| Monitoring, incidents and isolated recovery | [Operations](OPERATIONS.md), [operating runbook](../handoff/05_OPERATIONS_AND_RECOVERY.md) |
| Actual tests/evidence and open release gates | [Release status](RELEASE_STATUS.md), [acceptance](ACCEPTANCE_TESTS.md) |

## Local baseline

Python 3.12+, uv, Node 24+, PostgreSQL and Redis are required for the full stack.
SQLite is a local single-process evaluation alternative. `uv sync --frozen`,
private configuration, Alembic upgrade, API/worker and npm ci/dev are separate
steps. Plain uvicorn/worker commands do not automatically load `.env`; inject
settings with your secured environment manager. The web's local API fallback
is different from Vercel's runtime binding.

Compose reads compose.yaml and the ignored .env. Set a fresh URL-safe
POSTGRES_PASSWORD and private keys before `docker compose up --build -d`.
The migrate service runs once. API/worker share SQL state; web proxies to API;
DB/Redis remain internal. Dockerfile.web uses the repository build context and
.dockerignore. CI boots Compose, verifies health/migrations/Redis/web proxy and
the synthetic private flow. [Baseline green CI](https://github.com/iamdpsingh/V-Index/actions/runs/44828958174).

## Deployment invariants

- Never replace or delete an existing database/volume to fix configuration drift.
  Updating password text does not rotate the actual database role.
- Back up before risky changes and preserve the original resume/backup keys.
  Migrations run once from a secured operator environment, not shared imports/builds.
- Root Vercel directory is `.`; public web routes to internal app with BACKEND_URL;
  a persistent daemon must stay configured for ongoing ingestion.
- Production/preview/development data and rate state must be isolated and verified.
- Reviewed source registration is idempotent; keep the worker running. Registration,
  a queued refresh, CI or a successful frontend build does not establish live coverage.
- Source HTTP/policy/partial failures preserve the last complete index. Keep cooldowns,
  source identity checks and the two-complete-miss/24-hour closure requirement.
- Protect private files, credentials and local databases with both Git and upload
  exclusions. No raw secret export, browser-visible private settings or fake activation.

A code rollback does not reverse migrations, recover data or rotate keys.
Review schema compatibility before promotion; restore only to a separate empty
validated target and reconcile post-snapshot deletions before cutover.

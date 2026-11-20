# 03 · Development and release runbook

Use the canonical Git repository and a clean checkout. Never work in two tools
inside the same worktree. Preserve local data and unrelated work. Read
[AGENTS.md](../AGENTS.md), [deployment](../docs/DEPLOYMENT.md) and
[Vercel reference](../docs/VERCEL_SERVICES.md).

## Reproduce the local product

Prerequisites: Git, Python 3.12+, uv, Node 24+, PostgreSQL and Redis; Docker is
needed for the full Compose alternative. Production uses PostgreSQL 18; CI uses
17. Match PostgreSQL client tools to the actual server major for backup/restore.

```sh
uv sync --frozen
cp .env.example .env
```

Set private values in the ignored file; placeholders are not working credentials.
The ordinary uvicorn/worker commands do not automatically load `.env`. Inject
variables with your secured shell/service manager. Compose reads its `.env`.
Use separate development databases and Redis namespaces, never production data.

```sh
uv run alembic upgrade head
PYTHONPATH=backend uv run uvicorn vindex.api:app --host 127.0.0.1 --port 8000
# Separate terminal with the same private development configuration:
PYTHONPATH=backend uv run python -m vindex.worker
# Another terminal:
cd apps/web
npm ci
npm run dev
```

Open http://localhost:3000. Account endpoints require that exact trusted origin,
registration opt-in and a resume key for private uploads. The web's local API
fallback is documented in the gateway configuration; production uses its binding.
For a reproducible full local stack use `docker compose up --build -d` after
supplying fresh private development settings. Never use `down -v` on persisted
user data as a troubleshooting shortcut.

## Validate a change

```sh
uv run pytest
uv run ruff check backend scripts
uv run ruff format --check backend scripts
uv run mypy
cd apps/web
npm ci
npm run build
npm run test:browser
```

Set TEST_DATABASE_URL and TEST_REDIS_URL to disposable test services for the
service-backed tests. Without them, relevant tests skip. Browser fixtures are
synthetic interaction tests, not live connector evidence. Run targeted native
smoke harnesses only when necessary; respect source cooldowns and policy.
GitHub Verify additionally builds/boots Compose and exercises the private API
through the real web proxy. Read results for the exact submitted SHA.

## Deploy or upgrade

1. Review diff, migrations, environment changes and current health. Confirm a
   usable encrypted backup and independent key custody before risky data changes.
2. Preserve the root Vercel services/daemon configuration. Root Directory is `.`.
   `web` routes all public traffic and calls internal `app` through BACKEND_URL.
3. Apply reviewed Alembic migrations once from a secured operator environment.
   Do not run shared-database migrations at function import or preview build.
4. Push a substantive reviewed commit to canonical main. The connected Vercel
   project may deploy automatically. Never upload .cache, .env, keys or local DBs.
5. Wait for CI and deployment completion; inspect the actual worker instance,
   not just a successful frontend build. Test search, filters, detail, policies,
   anonymous denial on operator routes and private account isolation.
6. Check operations, failures and source last-success times. Expect interrupted
   in-flight collections to retain last good data and resume safely.

## Rollback and release record

Prefer the previous known-good Vercel deployment after reviewing schema
compatibility. A code rollback does not reverse migrations, restore data or
rotate credentials. Do not blindly downgrade a populated database. Escalate
incompatible schema changes to a planned forward fix or isolated recovery.
Preserve source schedules and include the worker when promoting a deployment.
Record code SHA, deployment identifier, migration head, UTC timestamp, checks,
exceptions and responsible operator in the receiving team's release log.

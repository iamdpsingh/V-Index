# Deployment

The owner now targets v0 publishing with no additional spending and no purchased domain. See [V0_RELEASE_PLAN.md](V0_RELEASE_PLAN.md) for the canonical repository/worktree explanation, frontend import settings, required backend integration and unresolved hosting eligibility/budget gates. Compose below remains the tested integration baseline, not evidence of a hosted v0 release.

Docker Compose is the intended production-like local path. Install Docker first. Copy `.env.example` to `.env` and replace every placeholder. Choose a long random ADMIN_TOKEN and a private URL-safe POSTGRES_PASSWORD (for example, generated with secrets.token_urlsafe). Compose requires the latter and derives its internal connection URL from it. Run `docker compose up --build -d`; migrate is a one-shot dependency. API health: http://localhost:8000/health. Web: http://localhost:3000. Database and Redis are internal only.

Local SQLite: `uv sync --frozen && uv run alembic upgrade head`; set PYTHONPATH=backend, ADMIN_TOKEN, optionally DATABASE_URL and REDIS_URL. Start API with uvicorn and worker with python -m vindex.worker. PostgreSQL URL format is postgresql+psycopg://user:password@host:5432/db. SQLite is for single-process development/tests, not concurrent production workers.

Before internet exposure add HTTPS, gateway request limits, secrets storage, network egress policy and backups. Compose is a single-host baseline, not a fully hardened deployment. Container/service execution must be tested where Docker is installed. Do not deploy the example credentials publicly.

The web container uses root-context Dockerfile.web so the repository .dockerignore excludes host node_modules and .next files. Compose uses this recipe; apps/web/Dockerfile is the original frontend scaffold recipe and is not selected by Compose. CI also builds and boots the full Compose stack, checks API/database health, Redis, migrations, the web page and API proxy. Read its actual run result before claiming deployment verification.

Full-stack baseline passed in CI on f4cf0ef: https://github.com/iamdpsingh/V-Index/actions/runs/42069063452. The web waits for API health; startup checks tolerate bounded TCP readiness resets. Live provider ingestion and hosted production operation are separate acceptance checks.

## Account feature configuration

Run migrations before the new API. PUBLIC_WEB_ORIGIN is opt-in and must match the exact browser origin; HTTP is allowed only for loopback development. ACCOUNT_REGISTRATION_ENABLED defaults false. Generate RESUME_ENCRYPTION_KEY privately using the command in .env.example; do not commit or expose it as NEXT_PUBLIC configuration. Compose forwards private settings only to the API. See ACCOUNTS_API.md for the supported flow, backup/key implications and remaining production gates. CI creates its own ephemeral key and test account and exercises the private flow through the web proxy; it does not configure a real user account or resume in the local demo.


November 7 credential handling: do not change POSTGRES_PASSWORD against an existing persisted PostgreSQL volume without coordinating an actual database password rotation and backup/recovery plan. Updating environment alone does not rotate the database password. Fresh CI volumes use a generated ephemeral value. Do not delete existing volumes to make a credential mismatch disappear. .env variants, key files, local DB sidecars and caches are excluded from Git/build contexts; verify the actual deployment artifact and secret injection before publication.


Register the reviewed platform examples after migrations with
`PYTHONPATH=backend uv run python -m scripts.register_verified_sources` to review
the count, then repeat with `--apply` to schedule their initial indexing. The
command preserves existing sources and can be repeated. Keep the worker running
to fetch jobs and maintain freshness. Source registration records configuration
and schedules work.

For PostgreSQL, `WORKER_CONCURRENCY` controls parallel source refreshes, defaults
to four, and accepts one through sixteen. Each source retains its Redis lease,
transaction, retry schedule, and closure safeguards. SQLite uses a single
refresh at a time.


Inside Compose, registration is available through
`docker compose exec api /app/.venv/bin/python -m scripts.register_verified_sources --apply`.

PostgreSQL search uses the bundled `pg_trgm` extension. The migration role needs
permission to install this trusted extension, or an operator can install it
before running migrations. Existing extension installations in other schemas
are detected. The application runtime role can then use the prepared indexes.

Run `python3 scripts/check_private_stack.py` against a dedicated local test
deployment at localhost:3000 to verify the private flow through the actual web
proxy. It creates and deletes synthetic accounts and a synthetic employer draft.

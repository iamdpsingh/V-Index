# V-Index

A job index with source provenance, scheduled refreshes and conservative closure detection. This repository is an initial working vertical slice, not a complete 78-platform submission.

## Local backend

Requires Python 3.12+, uv. SQLite is supported for a quick local evaluation; production uses PostgreSQL.

```sh
uv sync --frozen
uv run alembic upgrade head
export PYTHONPATH=backend
export ADMIN_TOKEN=local-review-token
uv run uvicorn vindex.api:app --reload
```

For the web UI: `cd apps/web && npm ci && npm run dev`; open http://localhost:3000. Node 24+ is required.

Open http://localhost:8000/docs for the API. In a second terminal start Redis and run `PYTHONPATH=backend uv run python -m vindex.worker`. Redis is required for refreshes. Without Redis you can run the connector smoke harness but scheduled ingestion does not run.

```sh
curl -X POST http://localhost:8000/api/v1/sources -H 'Authorization: Bearer local-review-token' -H 'Content-Type: application/json' -d '{"url":"https://jobs.ashbyhq.com/Ashby","company":"Ashby"}'
curl 'http://localhost:8000/api/v1/jobs?keyword=engineer&limit=10'
```

The worker finds due sources every 30 seconds. Creating a source schedules its first refresh immediately. A refresh request sets it due; it does not claim a successful fetch. `GET /api/v1/runs` records success/failure and counts.

## Validation

```sh
uv run pytest
uv run ruff check backend scripts
uv run mypy
PYTHONPATH=backend uv run python scripts/smoke.py
# Focus on a cohort:
PYTHONPATH=backend uv run python scripts/smoke.py --provider SmartRecruiters --provider Personio
```

Smoke requests public provider APIs and writes timestamped evidence. Inspect failures rather than treating all requests as successful. See [coverage](docs/COVERAGE.md), [deployment](docs/DEPLOYMENT.md), [frontend handoff](docs/ANTIGRAVITY_HANDOFF.md) and [backlog](docs/BACKLOG.md).

## Status and limits

Greenhouse, Lever (including EU endpoint support), Ashby, SmartRecruiters and Personio are implemented. Actual evidence is separate from implementation status. Other 73 entries are planning records, not connectors. PostgreSQL/Redis integration tests run when TEST_DATABASE_URL and TEST_REDIS_URL are configured; full container deployment still needs verification. No hosted demo or remote push is implied by local files. Acquisition readiness requires all acceptance criteria in docs/ACCEPTANCE_TESTS.md.

### Service-backed tests

Set `TEST_DATABASE_URL` to a PostgreSQL database where the test user may create schemas, and `TEST_REDIS_URL` to a dedicated test Redis database (for example database 15). Run `uv run pytest`. Each SQL test creates, migrates and removes only its own randomly named schema; existing tables are not modified. Without these variables, service-dependent cases are explicitly skipped. CI provisions PostgreSQL and Redis. Tests do not fetch live jobs; use the separate smoke harness for actual provider evidence.

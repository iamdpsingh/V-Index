# V-Index

**Rolewisp — Find your next opening.** Rolewisp is the owner-selected public product brand; V-Index remains this project's repository and folder name. See [branding](docs/BRANDING.md) for the identity direction and naming convention.

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

41 of the 78 required platforms have point-in-time live evidence across two independent employers or boards. The owner’s current target is **45 live-verified platforms**, with frontend on hold and new commits kept local until 45 is verified. Implementation, live evidence and production readiness remain separate. See the authoritative examples and limitations in [coverage](docs/COVERAGE.md).

Codex prioritizes today's 45-platform coverage target. Frontend work remains on hold, with existing Antigravity work preserved. See [the frontend execution brief](docs/ANTIGRAVITY_START_HERE.md) and [continuous-index requirements](docs/LIVE_INDEX_REQUIREMENTS.md). The November 6 IST target is 45 total verified platforms; it is not achieved coverage. PostgreSQL/Redis integration tests run when TEST_DATABASE_URL and TEST_REDIS_URL are configured. The full container stack passes the documented CI startup/proxy checks; hosted operation is not yet verified. New commits remain local at the owner’s instruction; do not push until 45 platforms are live-verified. No hosted reviewer demo has been deployed. Acquisition readiness requires all acceptance criteria in docs/ACCEPTANCE_TESTS.md.

### Service-backed tests

Set `TEST_DATABASE_URL` to a PostgreSQL database where the test user may create schemas, and `TEST_REDIS_URL` to a dedicated test Redis database (for example database 15). Run `uv run pytest`. Each SQL test creates, migrates and removes only its own randomly named schema; existing tables are not modified. Without these variables, service-dependent cases are explicitly skipped. CI provisions PostgreSQL and Redis. Tests do not fetch live jobs; use the separate smoke harness for actual provider evidence.

Workday currently rejects boards above 400 jobs and reported totals at/above its observed 2,000 ceiling. It supports hosted myworkdayjobs.com URLs, not every Workday URL variant. These restrictions are visible failures rather than partial successful snapshots. Recruitee uses its XML feed to avoid relying on unauthenticated JSON calls that are scheduled to require tokens in February 2027. See docs/CONNECTOR_CONTRACT.md for exact scope.

## Optional private job-seeker features

The backend now includes signup/login, saved profiles, encrypted saved PDF/DOCX/TXT resumes and explainable job recommendations. These APIs are separate from operator ADMIN_TOKEN access. Account routes require an explicit PUBLIC_WEB_ORIGIN; registration is disabled by default and resume operations require a privately generated RESUME_ENCRYPTION_KEY. Apply migrations before startup. Read [the private API contract](docs/ACCOUNTS_API.md) for configuration, limits and remaining production gates.

The owner retained the frontend with Antigravity. Its account/profile/upload/recommendation screens and browser tests are pending; [the concrete frontend handoff](docs/ANTIGRAVITY_ACCOUNTS_HANDOFF.md) lists every route, payload and required flow. Do not treat working backend APIs as a completed public account release.

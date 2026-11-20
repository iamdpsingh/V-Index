# V-Index · Rolewisp

**Rolewisp · Find your next opening.** V-Index is the engineering repository;
Rolewisp is the public product. Owner: Dhruv Pratap Singh.

A source-backed job index with scheduled native collection, conservative
lifecycle handling, deduplication, searchable records and private candidate/
employer workspaces. [Working demo](https://rolewisp.vercel.app).

## Start here

- **Taking over the project:** [complete handoff package](handoff/README.md).
- **Engineering reference:** [documentation register](docs/README.md).
- **Actual results and gaps:** [release status](docs/RELEASE_STATUS.md),
  [challenge acceptance](docs/ACCEPTANCE_TESTS.md), [coverage matrix](docs/COVERAGE.md).
- **Operations:** [deployment](docs/DEPLOYMENT.md), [monitoring/recovery](docs/OPERATIONS.md).
- **Ownership:** [copyright](COPYRIGHT.md),
  [Dhruv Pratap Singh on LinkedIn](https://www.linkedin.com/in/dhruvpratapsingh30/).

## Current scope and evidence

The registry records **71/78 platforms (91.0%)** with independent live examples.
Seven requirements remain unmet; coverage expansion is paused, not waived.
Production runs on Vercel with public Next.js `web`, internal FastAPI `app`,
PostgreSQL, Redis and a persistent two-slot indexing worker. Private Blob holds
encrypted backups and operator reports. Last reviewed public index: 7,937 jobs;
142 sources, 127 initial successes. These are dated November 21 observations,
not a live count or proof all sources currently succeed.

Search supports keyword/company/location, pagination, summaries and full details
with original source/application links. Accounts support Candidate/Employer,
manual private profiles and qualification categories, photos, encrypted resume
storage, recommendations and owned employer drafts. Resume parsing was removed
by request. SMTP/OAuth backend exists but real providers need activation/tests.
Free/Plus is a regional catalogue; paid checkout is unavailable.

The internal 20-check release matrix is a verification aid, **not an overall
project-completion percentage or official Vaya score**. Missing coverage,
source-data quality and external gates still prevent complete challenge acceptance.

## Local evaluation

Requires Python 3.12+, uv, Node 24+ and Redis. PostgreSQL is the production store;
SQLite is a single-process local alternative. Inject private settings from the
ignored `.env` or your service manager; never use production data for evaluation.
The example file does not automatically configure every command.

```sh
uv sync --frozen
# Configure a private development environment, then:
uv run alembic upgrade head
PYTHONPATH=backend uv run uvicorn vindex.api:app --host 127.0.0.1 --port 8000
# Separate terminal, same backend configuration:
PYTHONPATH=backend uv run python -m vindex.worker
# Web terminal:
cd apps/web
npm ci
npm run dev
```

Open http://localhost:3000. Enable registration only with a trusted
PUBLIC_WEB_ORIGIN; resume/photo operations require the original private key.
For full Compose setup, source registration, migration and rollback see
[the development/release runbook](handoff/03_DEVELOPMENT_AND_RELEASE.md).

## Validation and contracts

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

Service-backed tests need disposable TEST_DATABASE_URL and TEST_REDIS_URL;
otherwise relevant tests skip. Fixtures/tests do not count as native coverage.
[Baseline CI](https://github.com/iamdpsingh/V-Index/actions/runs/44828958174)
passed 1,244 backend tests, one skipped, plus frontend/full-stack checks.

[Public API](docs/API.md), [private API](docs/ACCOUNTS_API.md),
[OpenAPI](docs/openapi.json), [collector contract](docs/CONNECTOR_CONTRACT.md).
Interactive debug/schema endpoints are disabled in the product.

No closures from failures or partial pagination. Closure needs complete
enumeration plus two misses separated by 24 hours. No access-control bypass,
fake metrics, committed secrets/resumes or paid upgrades. Source-specific limits
remain explicit in the coverage/connector references. Support remains the
unverified placeholder example@rolewisp.in. External alerts, real provider flows,
independent key custody/deletion reconciliation, legal/domain/cost checks and
Vaya submission remain open; consult the [risk register](handoff/08_RISKS_AND_NEXT_ACTIONS.md).

Copyright © 2026 Dhruv Pratap Singh. Third-party notices remain applicable.

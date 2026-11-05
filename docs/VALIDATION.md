# Validation record — 2026-11-05

## Initial slice checks (historical)

- `uv run pytest`: 30 passed. One dependency deprecation warning: Starlette TestClient warns about its httpx transport. No failing tests.
- `uv run ruff check backend scripts`; `uv run ruff format --check backend scripts`; `uv run mypy` (7 modules).
- `npm run build --prefix apps/web`: Next.js 16.4.5 production compilation and TypeScript checks passed. npm installation audit reported zero vulnerabilities at installation time.
- `uv run alembic upgrade head` against local SQLite.
- Actual API + Redis (localhost:6397) + worker + SQLite: create three sources via authenticated API; fetch Stripe 760, Palantir 307, Ashby 72; successful fetch_run records and 1,139 active canonical results. Actual company/keyword filter returned 57 Ashby rows matching engineer in title or description.
- Latest smoke checked Stripe/Cloudflare, Spotify/Palantir and Ashby/Ramp: all six non-empty, complete enumerations. Separate timestamped evidence contains counts, digests and genuine earlier failure. This proves point-in-time connector behavior only.
- Interactive browser on the production web build: 1,139 jobs displayed; company+keyword search returned 56 Ashby roles matching support in title or description; next page showed 26–50; role selection exposed plain-text description, original application link and provenance. Admin source status showed three successful fetch runs. Coverage differentiated implemented, live verified and not started. At 390x844, form controls stacked and document width equaled viewport (390px). Viewport reset after check.

## Cohort 2 checks

- `TEST_DATABASE_URL=postgresql+psycopg:///postgres TEST_REDIS_URL=redis://127.0.0.1:6397/15 uv run pytest`: 80 passed, one existing Starlette TestClient/httpx deprecation warning.
- PostgreSQL 17 was installed and running but was missed during the first PATH-only inspection. Tests now create an isolated random schema, run Alembic migrations, exercise API filtering and lifecycle transitions, and remove only that schema.
- Real Redis integration tests prove serialization of stale due selections and rollback of index writes when reconciliation fails. These tests run against both SQLite and PostgreSQL. Existing source data remains open on errors.
- Shared transport adds response-size/host/redirect checks and bounded Retry-After handling. Parser regressions use actual SmartRecruiters and Personio fixtures, including optional non-text video sections and empty default-language descriptions.
- Live smoke reran the original three providers across six tenants successfully. Personio completed two tenant enumerations (Matrix42 34, planqc 17) with descriptions filled from English feed translations. SmartRecruiters self-board completed two jobs; Colliers exposed an explicitly empty role-description source field. Earlier complete-enumeration attempts failed and remain recorded. The connector now distinguishes missing schema from an explicit empty source value and exposes quality_flags without inventing role text; the corrected full live check succeeded: all 88 Colliers postings completed, with one role_description_missing flag. The latest smoke for this cohort is tied to code commit 1e9d1f0, a clean tree and an explicit source-code digest.
- Actual add-source -> scheduled worker -> stored jobs -> search path succeeded for SmartRecruiters (2 jobs) and planqc (17 jobs), using local SQLite and Redis. Evidence: evidence/cohort2-live-pipeline.json. The local demo now has 1,158 active jobs across five sources.
- GitHub Actions for implementation commit 4ca9ea0 passed backend (PostgreSQL/Redis services, lint, typing, tests and migration) and frontend production build: https://github.com/iamdpsingh/V-Index/actions/runs/42067157504. This run predates the optional-section fix; final revision CI must be checked separately.

## Not verified / incomplete

The first full-stack CI run built and started the Compose services but its readiness check failed on an early TCP connection reset. API health gating and bounded retry-all-errors startup checks were added; the corrected run must pass before stack verification is claimed. Deployment restart recovery and wider distributed concurrency remain unverified. No hosted demo, acquisition submission or all-platform coverage claim. Enterprise API documentation/research is not platform coverage. Browser checks above are historical; a reusable browser suite remains to be written. Structured location/salary normalization, original posting-date enrichment, custom domains and broader dedupe remain backlog.

# Validation record — 2026-11-05

## Passed locally

- `uv run pytest`: 30 passed. One dependency deprecation warning: Starlette TestClient warns about its httpx transport. No failing tests.
- `uv run ruff check backend scripts`; `uv run ruff format --check backend scripts`; `uv run mypy` (7 modules).
- `npm run build --prefix apps/web`: Next.js 16.4.5 production compilation and TypeScript checks passed. npm installation audit reported zero vulnerabilities at installation time.
- `uv run alembic upgrade head` against local SQLite.
- Actual API + Redis (localhost:6397) + worker + SQLite: create three sources via authenticated API; fetch Stripe 760, Palantir 307, Ashby 72; successful fetch_run records and 1,139 active canonical results. Actual company/keyword filter returned 57 Ashby rows matching engineer in title or description.
- Latest smoke checked Stripe/Cloudflare, Spotify/Palantir and Ashby/Ramp: all six non-empty, complete enumerations. Separate timestamped evidence contains counts, digests and genuine earlier failure. This proves point-in-time connector behavior only.
- Interactive browser on the production web build: 1,139 jobs displayed; company+keyword search returned 56 Ashby roles matching support in title or description; next page showed 26–50; role selection exposed plain-text description, original application link and provenance. Admin source status showed three successful fetch runs. Coverage differentiated implemented, live verified and not started. At 390x844, form controls stacked and document width equaled viewport (390px). Viewport reset after check.

## Not verified / incomplete

No PostgreSQL server or Docker binary was available. Compose images, PostgreSQL migration/query behavior, distributed concurrency and service restart recovery remain untested. No hosted demo, remote GitHub CI run, acquisition submission or all-platform coverage claim. Browser checks are manual interactions through automation tooling; a reusable browser test suite remains to be written. Structured locations/salary normalization, original posting-date enrichment, custom domains and fuzzy dedupe remain backlog.

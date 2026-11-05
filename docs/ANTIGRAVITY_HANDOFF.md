# Antigravity frontend handoff

Read AGENTS.md and this file before implementation. Work from a separate worktree and branch `feat/frontend`, based on a reviewed backend commit. Do not run Antigravity and Codex in the same worktree. No frontend agent is assumed running. Codex bootstraps apps/web only for an initial local demo; after handoff Antigravity owns that directory and browser tests. Request shared backend/spec changes via documented commits/PRs. Review merges; no force pushes.

## Stable API v1

FastAPI `/openapi.json` is executable truth. Use same-origin `/api/v1` via Next rewrite to API_INTERNAL_URL (default http://localhost:8000). Generate TypeScript types from the checked-in docs/openapi.json before expanding the UI. Jobs list: GET /api/v1/jobs?keyword=&company=&location=&limit=25&offset=0 -> total/limit/offset/items. Each item includes id,title,company,description,location,source_url,application_url,salary,employment_type,remote_status,published_at,first_seen_at,last_changed_at,sources. Source provenance includes source_id,source_url,application_url,status,last_checked_at. GET /api/v1/jobs/{id} provides observation details.

Admin bearer token is user-entered in memory; never bake it into NEXT_PUBLIC_ or persist in localStorage. POST /sources accepts url,company,refresh_minutes (60..10080). POST /sources/{id}/refresh schedules a fetch. GET /sources and /runs require auth. Handle 401,409,422,503 and network errors. GET /providers returns exact 78-entry matrix with separate implementation/evidence status, counts, timestamps and limitations. Never show implemented count as verified count.

## Product direction

Read [PRODUCT_DESIGN.md](PRODUCT_DESIGN.md) before frontend work. The owner requires a distinctive product identity and deliberate interaction design; the current scaffold is not the final visual standard. That brief extends the direction below and includes the required review gate.

A restrained editorial search workspace: warm off-white, dark ink, clear typography, green status accents with labels, compact useful controls. Avoid decorative metrics, fake logos, stock marketing filler and dashboard chrome. Search results lead with job/company/location and real source metadata; show honest empty/loading/error states. Descriptions render as text. Original apply links must be HTTPS and use rel=noopener noreferrer. Mobile controls stack with visible labels. Coverage page must show actual provider names and limitations, including unimplemented providers.

Required browser checks: mobile and desktop, keyboard search/filter/pagination, source submission errors and duplicate sources, sync failure display, detail/apply links, long descriptions/locations, empty index, coverage differentiation, contrast and focus states. Initial scaffold browser behavior is not considered verified until actual browser tests run. Do not remove production gaps from backlog merely to polish the demo.

## Backend cohort 2 integration note

The API now also accepts SmartRecruiters and Personio hosted boards. Supported-source copy should follow the actual implemented provider inventory rather than hardcoding the original three. No frontend files were changed during this backend cohort. The owner's latest clarification limits the design change to appearance; the objective and required functionality are unchanged. Enterprise investigation is in ENTERPRISE_RESEARCH.md and does not imply platform coverage.

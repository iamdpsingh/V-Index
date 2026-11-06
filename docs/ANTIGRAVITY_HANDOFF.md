# Antigravity frontend handoff

Publishing update: use the existing repository and reviewed `main` as the single release source; v0 is the owner's preferred publishing workflow, with no additional spending or purchased domain. See [V0_RELEASE_PLAN.md](V0_RELEASE_PLAN.md). The frontend worktree is temporary editing isolation, not a separate product. Preserve its work until reviewed integration and editor shutdown; do not create another repository for v0.

Latest priority: frontend expansion/polish is paused until full live coverage. A real indexed duplicate now retains two observations from the same source: see evidence/cohort5-live-deduplication.json. When frontend work resumes, provenance rows need a key including their source URL, rather than source_id alone; the current key can collide for this valid data. Retain both original links. Previously reviewed badge/history/error-state follow-ups are recorded in DELIVERY_PLAN.md.

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

Job list items now include additive `quality_flags: string[]` (default empty). A source can explicitly omit its role text; `role_description_missing` records that fact while preserving the other source-provided ad sections. If all description text is blank, `description_missing` is also present. Include these facts in the existing job-detail metadata treatment; do not imply the role text was extracted when the source left it empty. The OpenAPI snapshot includes this field.

## Backend cohort 3 integration note — 2026-11-06

Two more source types are available through the existing source form/API: Recruitee hosted tenant URLs and bounded Workday myworkdayjobs.com URLs (including locale-prefixed career-site links). Source configuration is derived server-side; do not ask users to enter the internal tenant~data-center~site key. Surface the existing run failure/error when Workday exceeds its 400-detail budget, reports the unsafe 2,000 ceiling, disallows robots access or returns inconsistent pages. The seven implemented providers and their live evidence/limitations remain authoritative in /api/v1/providers. No frontend files changed. Appearance changes remain separate from the unchanged product objective and required functionality.

## Explicit new feature handoff — 2026-11-06

The owner retained frontend ownership with Antigravity and requested account/profile/resume/recommendation screens. Read [ANTIGRAVITY_ACCOUNTS_HANDOFF.md](ANTIGRAVITY_ACCOUNTS_HANDOFF.md) and [ACCOUNTS_API.md](ACCOUNTS_API.md). This is an explicit feature expansion; the original indexing objective and coverage requirements remain unchanged.

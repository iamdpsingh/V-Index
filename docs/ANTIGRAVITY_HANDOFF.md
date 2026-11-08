# Antigravity frontend handoff

**Latest owner release requirements (November 7):** read [PRODUCTION_RELEASE_REQUIREMENTS.md](PRODUCTION_RELEASE_REQUIREMENTS.md). Coverage remains first. Public launch now requires a verified custom domain on the free-tier plan, favicon, permitted badge removal, reviewed legal/privacy pages, accessibility and a full security review. Older preview-only vercel.app guidance does not authorize launch. No spending or automatic deployment is authorized.

**Frontend delivery review:** 66baef8 independently passes dependency install, build and typecheck. Preserve that implementation. Before release, fix swallowed logout errors and the hardcoded India default, and actually test logout rather than only opening Profile. See [FRONTEND_REVIEW_66baef8.md](FRONTEND_REVIEW_66baef8.md). This is a documented handoff, not an assumption that an agent has been notified.

**Latest owner update — November 7:** coverage first, then remaining backend work. Batch pushes every 12 hours; maintain the frontend handoff alongside connector/API additions. Antigravity's implementation is present at `66baef8` and remains in its separate worktree pending reviewed integration. See [COVERAGE_WORKFLOW.md](COVERAGE_WORKFLOW.md).

**Latest product revision — November 7:** public UI is a finished product experience: no test/CI totals, smoke labels, acquisition progress or raw configuration errors. Codex supplied an original ribbon R logo and Free/Plus pricing design/API. Read PLANS_AND_PRICING.md and SECURITY_REVIEW_2026-11-07.md along with the current design specification. Preserve every coverage, API, privacy and backend requirement.

**Latest owner instruction — November 7:** Codex supplies the frontend design; **Antigravity implements it** in its existing separate frontend worktree. This supersedes the frontend hold and earlier Codex-frontend takeover notes. Read [ROLEWISP_FRONTEND_DESIGN.md](ROLEWISP_FRONTEND_DESIGN.md) and [ANTIGRAVITY_DESIGN_TASK.md](ANTIGRAVITY_DESIGN_TASK.md) first. Preserve frontend commit `3bc0a54` and existing API wiring; no external agent is assumed launched or notified. Codex continues backend and coverage. The original 78-platform objective is unchanged.


**Latest milestone, November 7: frontend remains ON HOLD.** The 45/78 live-verified coverage milestone passed, satisfying the owner’s condition for pushing accumulated commits. Continue coverage/backend and preserve the frontend worktree. This supersedes earlier 35-target/resume notes below. Future design resource: https://github.com/nutlope/hallmark; also AnimasterLib, Skiper UI, Vengence UI, Scrolltide, Navbar/CTA galleries, Footer Design, Refero Styles, Superhero, 3D icons and getlayers.ai. These are research references for later, not approved assets already incorporated.

**Superseding owner update, November 6:** Codex takes over frontend ownership after today's 35-total-platform coverage target. Preserve existing Antigravity commits/worktree; the design, API and test requirements below remain applicable reference material. Earlier assignment/resume instructions below are historical and no longer assign work to Antigravity.


Owner-selected brand: **Rolewisp**, tagline **Find your next opening.** The repository/folder remain V-Index. **Frontend work is explicitly resumed in parallel with Codex coverage work. Start with [ANTIGRAVITY_START_HERE.md](ANTIGRAVITY_START_HERE.md)**, then [BRANDING.md](BRANDING.md) and [LIVE_INDEX_REQUIREMENTS.md](LIVE_INDEX_REQUIREMENTS.md). The latest owner instruction supersedes earlier frontend-pause notes.

Publishing update: use the existing repository and reviewed `main` as the single release source; v0 is the owner's preferred publishing workflow, with no additional spending or purchased domain. See [V0_RELEASE_PLAN.md](V0_RELEASE_PLAN.md). The frontend worktree is temporary editing isolation, not a separate product. Preserve its work until reviewed integration and editor shutdown; do not create another repository for v0.

Codex owns coverage and backend/shared API support; Antigravity owns premium frontend execution, brand assets, existing documented account flows and browser tests. A real indexed duplicate retains two observations from the same source: see evidence/cohort5-live-deduplication.json. Provenance rows need a key including their source URL, rather than source_id alone; retain both original links. Frontend commit 4fc8fb4 addresses earlier badge/history/error-state findings; review and preserve that work when synchronizing main.

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

## GoHire, Polymer and Manatal integration — November 6

The existing source form now accepts GoHire jobs.gohire.io/{board}, Polymer jobs.polymer.co/{organization}, and Manatal www.careers-page.com/{tenant} URLs. No new frontend configuration fields are needed. Use the live provider matrix for counts/limits: GoHire is English/hosted/bounded, Polymer requires explicit complete single-page metadata, and Manatal supports its legacy hosted template and validated pagination. A failed/unsupported source must show its actual run error, never an empty-success or closed-all state. Salary objects retain source text or source currency/range fields; do not invent a unit or period. Optional metadata remains unknown when absent. No frontend files changed in this cohort.

## JBoard.io coverage — November 7 (formal live runs passed)

Source registration accepts the reviewed JBoard origins jobs.aame.org and jobs.cisontario.ca, root or /jobs, through the existing API. No new source fields. The source company field is a company/board label; a multi-employer board's jobs preserve their actual employers, so do not use the board label as each job's employer or an automatic company filter. Additional arbitrary custom domains are not supported.

The additive source_expiry_elapsed_while_listed quality flag means the complete public roster includes a job whose source closing timestamp has passed. Render a human-readable note such as “The source lists this role, but its closing date has passed. Check the original listing.” Do not turn it into an automatic closed status or show the raw identifier as consumer copy. Use a concise human explanation for unknown quality flags too. Coverage remains matrix-driven; this handoff does not itself grant live coverage.

JBoard.io now has complete formal live evidence for AAME 30 and CIS Ontario 48, at connector revision 814a873. Matrix status is 46/78 (44 ATS, two job-board platforms). JBoard.io remains distinct from JobBoard.io. The formal coverage result supersedes the earlier under-validation note; supported-origin and source-quality limitations still apply. No API schema change is required for the new source type.

## JobBoard.io source entry

The source form can accept `https://www.nifajobs.com/` and `https://www.cancercareers.org/` as reviewed JobBoard.io board roots. No API schema change. Keep the original public job link and API-provided Apply link; they can be the same when the board opens an application form on the listing. Render descriptions as text, including any protected contact placeholders. Keep source quality flags and connector checks in the review surface.

Both reviewed JobBoard.io sources passed formal live verification on November 7: NIFA 2 jobs and AACR CancerCareers 61. Current matrix is 47/78. This count belongs on the reviewer surface and in the evidence, not in hardcoded public product copy.

The owner added Anti-Slop as a frontend review reference on November 8. Use it alongside the Rolewisp design specification. [Anti-Slop repository](https://github.com/miqdadbadjuber/anti-slop)

Reviewed November 8 source URLs include the Niceboard roots `https://jobs.aiacolorado.org/` and `https://jobs.medicalalley.org/`, and the JobKit roots `https://jobs.rubyonrails.org/` and `https://welpora.jobkit.io/`. SmartJobBoard accepts `https://americanbath.mysmartjobboard.com/jobs/` and `https://jobs.psychologicalscience.org/jobs/`. Continue to render the API-provided source and application links. No client schema change is required.

The reviewed backend accepts the public ACEVO and Gradsouthwest JobBoard.com roots, Emotiv and Gecko Travel Nodex search pages, Oliver Walters and Pearl Street Systems WP Job Manager boards, and ICBC and KAUST SAP SuccessFactors career search pages. The existing API shape is sufficient. The verified list, site limits and remaining cases are documented for reviewers. [Backend integration review](ANTIGRAVITY_BACKEND_REVIEW_2026-11-08.md)

# Antigravity: Rolewisp frontend execution brief

**Latest owner instruction — November 7:** Codex supplies the frontend design; **Antigravity implements it** in its existing separate frontend worktree. This supersedes the frontend hold and earlier Codex-frontend takeover notes. Read [ROLEWISP_FRONTEND_DESIGN.md](ROLEWISP_FRONTEND_DESIGN.md) and [ANTIGRAVITY_DESIGN_TASK.md](ANTIGRAVITY_DESIGN_TASK.md) first. Preserve frontend commit `3bc0a54` and existing API wiring; no external agent is assumed launched or notified. Codex continues backend and coverage. The original 78-platform objective is unchanged.


**Superseding owner update, November 6:** Codex takes over frontend ownership after today's 35-total-platform coverage target. Preserve existing Antigravity commits/worktree; the design, API and test requirements below remain applicable reference material. Earlier assignment/resume instructions below are historical and no longer assign work to Antigravity.


Latest owner instruction, November 6, 2026 IST. Frontend work is explicitly resumed in parallel with Codex's coverage work. This supersedes earlier frontend-pause instructions.

## Ownership and checkout

- Antigravity owns `apps/web/`, its product identity/assets and browser tests. Codex owns backend connectors, ingestion, API contracts, migrations, deployment and CI. Do not edit each other's areas without a reviewed change request.
- Use the existing `/Volumes/Work/daemons-lab/p.automation/V-Index-frontend` worktree on `feat/frontend`. It is the same repository, not another product. Never run Antigravity inside Codex's canonical `V-Index` worktree.
- Inspect status before changes; preserve uncommitted work. Synchronize the latest canonical `main` into the frontend branch through a reviewed merge and resolve conflicts deliberately. Do not reset the branch or force-push. At handoff inspection it was clean at `4fc8fb4`; that commit already addresses error-state separation, case-insensitive status checks and selected-job history state. Verify those fixes rather than reimplementing them blindly.
- Make substantive commits and provide a reviewable frontend PR/merge. No external agent is assumed launched or notified merely because this document exists.

Read `AGENTS.md`, `BRANDING.md`, `PRODUCT_DESIGN.md`, `ANTIGRAVITY_HANDOFF.md`, `ANTIGRAVITY_ACCOUNTS_HANDOFF.md` and `ACCOUNTS_API.md`. Use the current `docs/openapi.json` and actual API responses as contracts.

## Brand and premium design requirement

Public name: **Rolewisp**. Tagline: **Find your next opening.** Repository/folder/package identifiers stay V-Index/vindex. Create the public wordmark, favicon and a coherent visual identity within the frontend checkout; do not rename infrastructure.

The owner requires a distinctive, premium product with deliberate composition, typography and interaction craft. The current scaffold is a starting point, not the final design. Build the reference-index concept into something recognizable: a legible index of openings, a generous reading surface for the selected role, and a quiet source rail explaining its origin and freshness. On mobile, provide a focused detail view and a reliable return to preserved results/scroll position.

Develop one strong search/detail composition against real API records before extending the system. Show desktop and mobile evidence and describe the design decisions. A token color swap, renamed header or generic component-library dashboard is insufficient. Use a custom wordmark/notation system, consistent type roles, optical spacing, refined rules, intentional density and carefully designed states. Build logo assets as appropriate code-native SVGs; respect font/asset licensing and the zero-additional-spend budget.

Avoid stock dashboard cards, decorative KPI rows, giant empty hero sections, fake company logos, invented testimonials/activity, AI sparkles, gratuitous gradients/glass effects and ornamental animation. Distinctiveness must support finding and reading real jobs. Maintain accessible contrast, keyboard focus, readable long content, comfortable touch targets and reduced-motion behavior.

## Deliver these flows

1. Public search, keyword/company/location filters, pagination, URL/back/forward state, selected-job reading and original application links. Search remains available without an account.
2. Rolewisp source/provenance treatment: distinct original links, honest timestamps, optional salary/workplace/publication data, missing-description and email-application explanations. Multiple observations may share a source_id; use a stable composite row key rather than source_id alone. Never render descriptions as HTML.
3. Coverage: all 78 exact platform names, with separate implemented/live-evidence states, example runs, timestamps and limitations. Load counts from `/api/v1/providers`; never hardcode the current count or present a daily target as achieved coverage.
4. Operator source submission and refresh/run inspection. Admin token stays in memory. Source/run statuses are lowercase (`running`, `success`, `failed`, `open`, `closed`). A refresh request schedules work; it is not proof of completed indexing.
5. Signup/sign-in/session restoration, profile persistence, resume upload/replacement/download/removal, recommendations with reasons, logout/password change/account deletion. Implement the existing documented backend contract; missing email verification/recovery and disabled account configuration must remain honest unavailable states. Do not build fake recovery flows or claim private features are production-enabled.

## A continuously updated index, not a frozen demo

Read `LIVE_INDEX_REQUIREMENTS.md`. Always request jobs from the same-origin `/api/v1` database-backed API. Do not ship a static JSON export, copied smoke samples, seeded vacancies or hardcoded listing arrays as the product's data source. Fixtures belong only in isolated tests.

Refresh visible search data on a modest interval (initial target: 60 seconds while the tab is visible), on returning focus, and through an explicit refresh control. Abort superseded requests and pause polling in background tabs. Preserve filters, selection and reading position; if new results would move the user's page, show a concise “New results available” action instead of jumping the list. Avoid stacked timers and polling retries that hammer a failed API. Private data must not enter shared caches.

Browser polling reloads the current index; it does not scrape upstream sites. The worker independently refreshes sources on their configured schedules. Show “Results refreshed” separately from each listing's actual `last_checked_at`. Never label every job “just fetched” when only the browser API request succeeded. Source platform smoke-test dates are also separate from listing freshness. There is no current push/SSE/WebSocket contract or guaranteed instant upstream detection.

If a selected job disappears from a polled result page, do not infer closure: filters, offset pagination or new records can move it off that page. Preserve the reader and inspect the backend's explicit observation statuses before showing a closed state. Test a job changing/closing while selected. Bookkeeping timestamps are normalized to UTC by the backend, including SQLite; format them for the viewer without discarding timezone information. Original source publication dates may have less precision and are a separate fact.

Last attempt and last success are distinct. Do not invent a last-success timestamp from `last_changed_at`, `/health`, the browser clock or a failed run. The current paginated `/runs` response may not contain the last success; show unknown if unavailable and request a backend contract change through documentation/PR. Job-list source projections and `/jobs/{id}` observation objects have different shapes; adapt them deliberately.

## Verification and handoff

Run `npm ci`, `npm run build`, `npm run typecheck` and the browser suite in the frontend worktree. Add meaningful browser cases for the new account flows and live-result refresh behavior. Verify search/filter/pagination/back state, two-account isolation, upload errors and failed replacement, expired sessions, source failures, incoming jobs/changed records and preserved reader position. Test desktop/mobile, keyboard, reduced motion, long/missing content and no horizontal overflow.

Save real-data visual evidence separately from mocked test screenshots and label both accurately. Never use fixtures/screenshots as provider coverage. Report actual commands, outcomes, unresolved issues and the exact frontend commit. A build pass alone is not interaction or premium-design acceptance.

The public hostname/deployment remains a Codex responsibility with unresolved budget/hosting gates. Use the current same-origin rewrite contract and request backend changes through reviewed commits. Do not purchase domains, upgrade plans, register paid services or publish a new independent repository.

## Latest production/product additions — November 7

Read PLANS_AND_PRICING.md and SECURITY_REVIEW_2026-11-07.md. Use the original ribbon R mark and updated product-only studies; remove test/acquisition diagnostics from consumer navigation and copy. Coverage stays separately inspectable for reviewers. Implement the real plans API, country selector and exact money formatting; Plus has no connected provider and must not simulate payment. Job detail now shares JobOut/provenance fields with search; raw source/observation data is private. Preserve current account/resume/recommendation/polling work and all 78 platform requirements. HTML security headers and the actual production bundle require frontend verification; no frontend agent was launched or messaged here.

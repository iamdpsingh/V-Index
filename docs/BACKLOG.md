# Execution backlog

**Latest owner update — November 7:** coverage first, then remaining backend work. Batch pushes every 12 hours; maintain the frontend handoff alongside connector/API additions. Antigravity's implementation is present at `66baef8` and remains in its separate worktree pending reviewed integration. See [COVERAGE_WORKFLOW.md](COVERAGE_WORKFLOW.md).

## Current coverage-first status

58 of 78 platforms have complete, nonempty live runs on two independent sites. 11 ATS and nine job-board platforms remain. Antigravity's local coverage batch was reviewed and selectively integrated. Read the [backend review](ANTIGRAVITY_BACKEND_REVIEW_2026-11-08.md) for the remaining platform list, verified results and next actions. Older cohort numbers below are historical.

## First slice
- [x] Inspect empty folder/remote; initialize canonical main without replacing history.
- [x] Contracts, exact 78-provider inventory and isolated frontend handoff.
- [x] Initial three public API connectors, persisted observations, lifecycle, conservative dedupe, API and worker baseline.
- [x] SmartRecruiters and Personio implemented with two live tenants each (5/78 platform evidence).
- [x] Recruitee and bounded hosted Workday implemented; two live employers each (7/78 point-in-time evidence).
- [x] Add Teamtailor, Breezy HR, Workable, BambooHR, Pinpoint and JazzHR with two independent live employers each (13/78 point-in-time evidence).
- [x] Add HireHive public structured templates; AMCS Group 59 and Echelon DC 6 complete live jobs (14/78 point-in-time evidence).
- [x] GoHire: DineAmic Hospitality 22 and Digital Shift 23 full live jobs; scheduled Digital Shift ingestion/search verified. Count now 15/78.
- [x] Polymer: ChemFinity Technologies 4 and Gencores 2 complete live jobs; scheduled ChemFinity ingestion/search verified. Count now 16/78.
- [x] Recooty: Augusto Digital 2 and Recooty Inc. 26 complete live jobs.
- [x] Jobvite: iboss 35 and Optimas Solutions 23 complete live jobs; current point-in-time total 20/78.
- [x] Manatal: Quantile Health 2 and Munich Ventures 10 complete live jobs; point-in-time total now 17/78.
- [x] Jobboardly multi-board verification via documented full XML feeds plus twice-enumerated HTML rosters; 31 Recruiter Jobs and 1,324 Pennsylvania Communications jobs. Earlier HTML failures remain recorded.
- [x] First enterprise risk investigation recorded in docs/ENTERPRISE_RESEARCH.md.
- [x] Verify full Compose/PostgreSQL/Redis/web startup and proxies in GitHub Actions.
- [ ] Deploy a hosted reviewer demo and verify live ingestion there.
- [ ] Frontend redesign against docs/PRODUCT_DESIGN.md; browser tests for existing source/run management, preserved search state and responsive job details.

## Immediate acquisition risks (planning order, not verified access claims)
- Investigate Workday, Oracle Recruiting/Taleo, SAP SuccessFactors, iCIMS, ADP, BrassRing and CSOD early: tenant variations, pagination, public accessibility and complete enumeration.
- Identify official documentation and two real independent tenants for every platform. Investigate obscure job-board vendors early; establish exact product identity rather than conflating similarly named boards.
- Prototype an auditable HTML/JSON-LD connector base only after access/robots/SSRF controls are designed; no generic parser counts as platform coverage.

## Hardening and correctness
- [x] PostgreSQL migrations/API/lifecycle and real Redis serialization/transaction rollback integration tests; CI provisions both services.
- [ ] Wider transaction races, process termination/restart recovery and automated stale-run finalization.
- Immutable run snapshots, before/after event data, conflict-aware canonical field enrichment and richer conservative dedupe.
- Provider publication timestamps/detail enrichment; structured locations and salary unit normalization, without inferring missing facts.
- [x] Honor bounded Retry-After delays and fail into source cooldown for longer delays.
- [ ] Distributed per-host request budgets, structured logs, heartbeat and stale-source alerts.
- Gateway auth/rate limits, egress DNS/IP controls, non-root web image, deployment security review, backup restore drill.
- PostgreSQL full-text search and measured indexes when benchmark warrants.

## Remaining cohorts
- Next ATS candidates: GoHire and HiringThing, alongside the enterprise investigation. Candidate priority only; access and endpoint support unverified.
- Other medium/high risk ATS: work through every NOT_STARTED row in coverage matrix; no stubs.
- Jobboardly has accepted bounded multi-board live evidence; the other 18 job-board platforms are unimplemented. Need multiple installations, complete pagination, detail extraction and tenant-independent detection. Preserve distinct JBoard.io and JobBoard.io entries. Niceboard findings and platform identity research are documented separately.

## Delivery
- [x] Verify page deadline: November 30, 2026 at 23:59 UTC (December 1 at 05:29 IST).
- [ ] Confirm submission/acquisition terms with organizer.
- Complete founder profile/submission only with user-provided account/profile details and authorization.
- Sanitize fixtures, run multi-tenant smoke checks, reconcile all 78 evidence entries, document genuine blockers.
- Reviewer walkthrough, deployment cost measurements, final technical handoff.

## Workday follow-up
- Extend enumeration beyond the current 400-detail budget and investigate safe completeness above the observed reported-total ceiling. No partial enumeration may close jobs.
- Support myworkdaysite.com and verified custom-domain entry points after strict URL/egress controls.
- Continue testing independent tenants/locales and source schema variations; current evidence is IMF and Gates only.

## Owner expansion — November 7 internal target
- [x] Add accounts, hashed/expiring sessions, private saved profiles and lifecycle tests.
- [x] Add owner-only encrypted resume storage, bounded document extraction, replacement, download and deletion.
- [x] Add open-job recommendations from explicit professional role/skill signals and optional resume keywords, with reasons and candidate-scope disclosure.
- [x] Exercise private flows through the real Docker web proxy in CI.
- [ ] Antigravity signup/login/profile/resume/recommendation screens and browser tests (owner explicitly retained frontend ownership there).
- [ ] Email ownership verification, identity recovery, parser isolation/abuse testing and hosted HTTPS release checks.
- [ ] Remaining 58 provider implementations and bounded connector expansion. These remain Codex's priority and acquisition acceptance gates before Codex begins frontend implementation.

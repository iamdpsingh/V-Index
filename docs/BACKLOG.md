# Execution backlog

## First slice
- [x] Inspect empty folder/remote; initialize canonical main without replacing history.
- [x] Contracts, exact 78-provider inventory and isolated frontend handoff.
- [x] Initial three public API connectors, persisted observations, lifecycle, conservative dedupe, API and worker baseline.
- [x] SmartRecruiters and Personio implemented with two live tenants each (5/78 platform evidence).
- [x] First enterprise risk investigation recorded in docs/ENTERPRISE_RESEARCH.md.
- [ ] Verify full Compose/PostgreSQL/Redis path and deploy a reviewer demo.
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
- Public structured ATS candidates: Recruitee, Personio, SmartRecruiters, BambooHR, Breezy HR, Workable, Teamtailor. Candidate priority only; access and endpoint support unverified.
- Other medium/high risk ATS: work through every NOT_STARTED row in coverage matrix; no stubs.
- All 20 job-board platforms: multiple custom-domain installations each, complete pagination, detail extraction and tenant-independent detection.

## Delivery
- [x] Verify page deadline: November 30, 2026 at 23:59 UTC (December 1 at 05:29 IST).
- [ ] Confirm submission/acquisition terms with organizer.
- Complete founder profile/submission only with user-provided account/profile details and authorization.
- Sanitize fixtures, run multi-tenant smoke checks, reconcile all 78 evidence entries, document genuine blockers.
- Reviewer walkthrough, deployment cost measurements, final technical handoff.

# V-Index product design standard

## Owner direction

Scope clarification: the requested change is visual presentation only. The challenge objective, required functionality and backend requirements remain unchanged. Candidate interaction ideas below do not expand implementation scope; preserve the existing workflows while designing their appearance.

The objective remains the 78-platform job indexer challenge. The owner explicitly requires a distinctive frontend, deliberate visual craft and excellent backend engineering. The current interface is a working scaffold; it is not the final design. Treat visual identity, interaction quality and data reliability as release requirements alongside coverage.

## Product concept: an index you can inspect

Build an identifiable job-search instrument whose distinguishing interaction is following an opening back through its sources and refresh history. A visitor should understand the job, its origin and the limits of its freshness without learning the ingestion architecture. Operators get deeper run diagnostics in source management.

The defining composition is a searchable index on the left and an inspectable job record on the right. Each record has a quiet provenance rail: original listing, application destination and last successful observation. These are useful controls, not decoration. On mobile, selection opens a focused detail view with a clear return to the preserved results and scroll position.

Design candidate: reference numbers, fine rules, carefully aligned metadata and an editorial type hierarchy suggest a maintained reference index. Develop a custom V-Index wordmark and a small, consistent notation system around index entries and source relationships. Prove the composition with real jobs before adding ornamental assets. This is a proposed direction for execution and critique, not a claim of a finalized unique design.

## Screen requirements

1. Search: useful results appear immediately. Keep keyword/company/location controls compact, preserve filters and pagination in the URL, support browser back and shareable searches. Visually separate job title, employer, location and freshness. Missing metadata gets an honest concise label.
2. Job detail: make description and original application action easy to reach. Explain multiple sources in a compact provenance view. Reserve salary, remote status and publication date space only when the source supplies them. Avoid turning a long description into an inaccessible nested scroll trap.
3. Source management: adding a source leads into visible scheduled/running/completed/failed states. Show last successful refresh separately from last attempt, with an actionable failure explanation. A queue request must never look like completed indexing.
4. Coverage: provide a navigable 78-platform inventory grouped by ATS/job-board, with explicit implementation and evidence states. Let reviewers inspect tenant examples, timestamps, extraction counts and limitations. Never animate unverified entries as active integrations.

## Visual and interaction craft

Choose a coherent typography system with distinct display, reading and metadata roles; verify font licensing and loading behavior before adopting assets. Use a consistent spacing scale, restrained palette and purposeful accent color. The current off-white/dark-green palette is a starting point rather than a fixed identity. Design focus, hover, selection, loading, error, empty and disabled states as part of the same system.

Use motion only to explain selection, loading progress or a source-state transition. Honor prefers-reduced-motion. Preserve keyboard access, semantic controls, readable contrast and comfortable touch targets. Long titles, international locations and missing salaries must feel designed, not broken. Differentiate through composition and behavior rather than unusual controls that slow search.

Reject decorative KPI tiles, generic giant hero copy, invented activity, gratuitous gradients, glass effects, unrelated illustrations, fake logos and repeated rounded cards as a default layout. Do not add AI-themed decoration or vague marketing claims. Explain the product through actual source-backed records.

## Backend excellence that the interface can rely on

Priority contracts: source completeness; no closures from errors; conservative dedupe with provenance; distinct last attempt and last success; immutable run/change evidence; restart-safe scheduling; predictable pagination; explicit optional-field semantics. Prove these with PostgreSQL/Redis integration and failure/recovery tests before claiming production readiness.

Measure refresh duration, source age, failure frequency, search latency and index size with documented workloads. Set performance budgets from those measurements, rather than displaying invented uptime or speed claims. Distributed rate budgets, Retry-After support, worker health, structured logs, gateway limits and tested restore procedures remain required hardening work.

Additional provenance timeline, change-diff and live progress UI require backend contracts first. Do not synthesize historical snapshots, progress percentages or last-success timestamps from insufficient API data. Current API fields and known gaps are documented in CONNECTOR_CONTRACT.md and ARCHITECTURE.md.

## Review gate and ownership

Antigravity owns frontend implementation in its separate branch/worktree; Codex owns backend and API support. Read ANTIGRAVITY_HANDOFF.md. No frontend agent is presumed to have received this brief until it actually reads the repository.

Before frontend acceptance, review one representative search/detail composition with real jobs, then implement responsive states and test them in a browser. Required evidence: desktop/mobile screenshots; keyboard traversal; URL/back-state behavior; long/missing content; source failure/retry behavior; reduced motion; original apply destinations. A screenshot or successful build alone does not satisfy interaction acceptance.

A distinctive design must stay recognizable across search, details, source operations and coverage. The product is only ready when that design quality and the backend/78-provider acceptance requirements both pass. This document records requirements; it does not assert that the redesign or hardening has been completed.

## November 6 scope clarification

The visual redesign remains a presentation change. Separately, the owner explicitly requested new account/profile/resume/recommendation functionality and set a November 7 internal target. The owner retained those screens with Antigravity. This new feature authorization supersedes the earlier appearance-only scope for these specific flows; it does not change the acquisition objective or waive the coverage/reliability criteria. Follow ANTIGRAVITY_ACCOUNTS_HANDOFF.md.

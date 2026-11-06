# V-Index shared engineering instructions

Develop only in this repository. Preserve existing work and canonical remote https://github.com/iamdpsingh/V-Index. Primary branch: main. No force pushes or secrets. Do not count stubs, fixtures or unit tests as live coverage.

Latest owner update (2026-11-06): Codex owns backend/, scripts/, database migrations, deployment, CI, shared API specifications and, after today's coverage target, apps/web/ and browser tests. This explicitly supersedes earlier Antigravity frontend ownership. Preserve its existing branch/worktree and review existing commits before frontend integration. Read docs/ANTIGRAVITY_HANDOFF.md first. Never run both tools in the same worktree. Coordinate through commits and reviewed merges; no assumption of agent messaging. No external agent has been launched by this repository setup.

Before editing, inspect git status and relevant files. Tests: uv run pytest; uv run ruff check backend scripts; uv run mypy. Web: cd apps/web && npm ci && npm run build. Keep lockfiles committed. Document real failures, do not invent evidence.

Never infer closures from failures, malformed payloads or partial pagination. Require complete enumeration plus two misses separated by 24 hours. Keep original observations and links. Validate URLs, use fixed public API hosts, disable redirects and environment proxies, bound response sizes and retries. Never bypass access controls. UI renders descriptions as text.

All 78 platform names must remain distinct (JBoard.io and JobBoard.io are different). Coverage evidence belongs in evidence/ and backend/providers.json. Do not mark the acquisition criteria complete while blockers remain.

Product quality: read docs/PRODUCT_DESIGN.md for the owner’s frontend identity and backend quality requirements. The current UI is a scaffold, not the final design. Require real-data visual and interaction review; never replace engineering correctness or coverage evidence with visual polish.

Owner update (2026-11-06): target November 7 IST; add private accounts, saved profiles/resumes and professional-term job recommendations without replacing the indexer challenge. The owner explicitly retained frontend work with Antigravity. See docs/ANTIGRAVITY_ACCOUNTS_HANDOFF.md. Make small substantive commits; do not inflate counts with empty commits. Never commit credentials, personal resumes or account data.

Latest owner priority (2026-11-06, superseding the previous frontend pause): Codex prioritizes coverage; Antigravity resumes the premium Rolewisp frontend, branding assets, account/profile/resume/recommendation screens and browser tests in parallel in its existing separate worktree. Read docs/ANTIGRAVITY_START_HERE.md. Production must keep indexing new/changed jobs on a running scheduler, not serve a frozen development dataset; follow docs/LIVE_INDEX_REQUIREMENTS.md. Target November 6 IST: 35 total fully verified platforms (21 additional from the current 14), not a promised result or permission to count partial runs. Preserve all 78-platform acceptance gates and report actual progress. Hosting/budget and production release gates remain unresolved; no paid purchases are authorized.

Latest sequencing (2026-11-06): finish today's target of 35 total live-verified platforms before frontend implementation. Current verified baseline is 17/78, requiring 18 more. Codex will then take over Rolewisp frontend design, brand assets, account screens and browser verification. Existing Antigravity briefs remain requirements/reference material, not current task assignment. No frontend agent is assumed running, and no frontend changes should be made concurrently in the same worktree.

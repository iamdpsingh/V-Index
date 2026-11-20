# V-Index shared engineering instructions

Current instructions reconciled November 21, 2026. Earlier changing ownership,
coverage targets and deployment holds are preserved in Git history at 74c0b08;
they do not override the latest owner scope below.

## Workspace, ownership and authorization

- Develop in the canonical V-Index repository only. Preserve other worktrees and
  unrelated user changes. Remote: https://github.com/iamdpsingh/V-Index; branch main.
  No force-push, secret commits, personal resumes/account data or empty commits.
- Inspect git status and relevant files before editing. Never run concurrent editing agents/tools in the same worktree. No external agent is assumed active or notified.
- Integrated backend, scripts, migrations, CI/deployment and apps/web are maintained
  in canonical main. Old Antigravity briefs are historical requirements/reviews;
  preserve their branches/commits rather than assuming an unreviewed merge is needed.
- Current scope: production/product/operations/handoff work. Production and reviewed
  pushes are authorized for the existing Vercel project. Coverage expansion is
  paused at 71/78, without waiving the original 78-platform acceptance requirement.
- No paid purchase, upgrade or domain purchase is authorized. Keep existing-provider
  failure repairs honest; never count partial/blocked runs or third-party samples
  as complete reusable platform coverage. No promise of challenge rank/acquisition.

## Engineering invariants

- No closures from exceptions, malformed payloads or partial pagination. Require
  complete enumeration and two misses separated by at least 24 hours. Preserve
  original observations, source/application links, failure records and timestamps.
- Validate URLs and source identity, use fixed public API hosts or explicitly reviewed
  installations, disable redirects/environment proxies, bound responses/retries/
  pages/timeouts and respect native robots/rate/access policy. Never bypass controls.
- All 78 names stay distinct, especially JBoard.io and JobBoard.io. Evidence belongs
  in evidence/ and backend/providers.json. Stubs/fixtures/tests are not live coverage.
- UI descriptions remain text. Private payloads, secrets and raw candidate data
  never enter logs/evidence, public responses, browser bundles or deployment uploads.
- Preserve account ownership, role, exact-Origin and operator authorization checks;
  rate limits, private caching and signed proxy metadata must survive changes.
- Keep production indexing on a persistent scheduler, not a frozen development DB.
  Browser polling is not provider ingestion. Declare freshness and platform limits.

## Product decisions and release gates

- Public brand: Rolewisp; internal repo/folder: V-Index. Owner/copyright: Dhruv Pratap
  Singh; LinkedIn https://www.linkedin.com/in/dhruvpratapsingh30/.
- Read docs/PRODUCT_DESIGN.md and docs/BRANDING.md for the restrained original UI.
  No fake metrics/reviews, purple gradients, generic slop or acquisition/testing
  diagnostics in consumer flows. Require real-data visual/interaction review.
- Candidate/Employer onboarding, manual profiles/qualification categories, encrypted
  resume/photo storage and recommendations are integrated. Resume parsing was
  intentionally removed. Keep private data owner-only. Employer publish needs
  verified email. SMTP/OAuth are not live without real configuration and tests.
- Free/Plus is a regional catalogue; no payment gateway, fake activation or paid
  entitlement. Keep paid checkout unavailable pending separately approved work.
- example@rolewisp.in is an owner-retained unverified placeholder. External alerts,
  real provider delivery, key custody/deletion reconciliation, credential rotation,
  domain/legal/cost checks and authenticated Vaya submission remain explicit gates.
- The authored twenty-check matrix is not a project-completion percentage or Vaya
  score. Use actual criteria, scoped evidence and named open tasks.

## Verification and documentation

- Backend: uv run pytest; uv run ruff check backend scripts;
  uv run ruff format --check backend scripts; uv run mypy.
  Service-backed tests need disposable TEST_DATABASE_URL and TEST_REDIS_URL.
- Web: cd apps/web && npm ci && npm run build; run relevant browser checks.
  Keep lockfiles committed. Follow apps/web/AGENTS.md and local Next.js docs.
- Validate actual CI/deployment/daemon after release. Document real failures and
  exact evidence scopes; never fabricate success or treat historical checks as new.
- Start with handoff/README.md and docs/README.md. Update affected current references
  with contract/infrastructure/retention/scope changes. Preserve historical run
  evidence and third-party licenses. Do not rewrite old evidence to look current.

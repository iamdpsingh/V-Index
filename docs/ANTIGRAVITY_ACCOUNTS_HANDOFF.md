# Antigravity account/profile/recommendation handoff — November 6

Latest owner instruction explicitly resumes these frontend screens alongside the premium Rolewisp design work while Codex focuses on coverage. Start with ANTIGRAVITY_START_HERE.md; backend release gates below still apply. Frontend implementation authorization does not enable public registration or eliminate missing identity/recovery work.

The owner explicitly retained frontend ownership with Antigravity on November 6. Internal delivery target: November 7, 2026 IST. The objective is still the acquisition challenge and its 78-platform coverage. The owner has now added accounts, saved profiles, saved resumes and personalized recommendations; this explicitly extends the earlier appearance-only scope for these features.

Read AGENTS.md, ANTIGRAVITY_HANDOFF.md, PRODUCT_DESIGN.md and ACCOUNTS_API.md first. Use a separate frontend branch/worktree based on the latest canonical main; do not run both tools in the same worktree. Own apps/web/ and browser tests. Backend/API changes go through coordinated reviewed commits. No external agent or frontend worktree was launched by Codex for this handoff.

## Deliver the complete user flow

1. Signup/sign-in screens with email/password, honest inline validation and session restoration from GET /me. Never persist passwords or tokens. Passwords are 12–128 characters; email is not yet verified, and there is no working forgot-password flow to link to.
2. Profile screen: name/headline/location/bio, desired roles, skills, preferred locations, remote-only and resume-derived matching toggle. Experience years can be saved but currently does not affect ranking. Load existing profile, preserve unsaved edits, submit complete PUT payload and confirm saved state.
3. Resume section: show current filename/date/detected keywords; upload/replace readable PDF/DOCX/TXT up to 5 MiB, download original, remove file. Upload raw File bytes with encoded X-Filename; no base64/multipart. Keep prior file visible after a rejected replacement. Show genuine uploading/processing/error states; do not manufacture progress percentages. Explain unsupported scans/password-protected files briefly.
4. Recommendations screen: consume /me/recommendations and render genuine indexed jobs, matching reasons, original application links, source freshness and existing filters/preferences. No invented match percentages or hiring-fit guarantees. Include useful empty states: no profile signals, no matching indexed jobs, expired login, API unavailable, and bounded/truncated candidate scope.
5. Logout, current-password change and reauthenticated account deletion. Deletion must clearly state that the live profile/resume are removed; do not promise immediate deletion from backups. Preserve a straightforward path back to public job search.

Suggested routes: /account/sign-in, /account/sign-up, /profile and /for-you. Keep public search usable without signup. Personal login does not grant admin source-management access. Keep operator controls separate.

## API integration

Use the existing same-origin /api/v1 rewrite and browser-managed cookies. API route/schema truth is docs/openapi.json. PUBLIC_WEB_ORIGIN must match the browser origin exactly, including localhost versus 127.0.0.1. Mutations enforce Origin. Never expose RESUME_ENCRYPTION_KEY or ADMIN_TOKEN via NEXT_PUBLIC variables. Return 401 -> session expired/sign in; 403 -> origin/configuration issue; 409 -> duplicate account; 413 -> too large; 415/422 -> unsupported/unreadable input; 429 -> temporary rate/busy state; 503 -> unavailable/disabled configuration. All private API responses are no-store.

For a local integration environment, the backend operator must explicitly configure origin, registration and a private encryption key, and run migrations. There are no seeded accounts or sample personal resumes. Use isolated test-only accounts/fixtures for browser tests, not fabricated content in the reviewer demo. Do not add arbitrary default credentials.

## Design and checks

Apply the existing distinctive reference-index visual direction across the new screens. Use the same typography, spacing, provenance treatment, focus states and responsive conventions. Render user text as escaped text, never raw HTML. Keep technical scores, crypto/parser internals and admin tokens out of ordinary job-seeker flows.

Verify desktop/mobile, keyboard/labels/focus, signup/login/logout/expiry, profile persistence, cross-account isolation, upload/replacement failure/download/delete, resume matching opt-out, recommendation links/reasons and empty/error states. Check no private page leaks into static/public caches and no token/profile data appears in browser console logs. Save real screenshots and test results. A frontend build alone is not flow verification.

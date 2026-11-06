# Delivery target — November 7, 2026 (IST)

## Superseding owner priority — November 6

Complete and evidence live coverage across all 78 required platforms before resuming accounts, frontend polish or hosting work. The owner explicitly moved coverage ahead of the other features after discussing Sunday, November 8. Sunday is a target, not a guaranteed completion date. Preserve existing account and frontend work; do not expand it during the coverage push. Count only real successful multi-tenant indexing runs, disclose bounded implementations and genuine access blockers, and keep every platform distinct. The earlier execution priorities below record the previous plan and are suspended where they conflict with this instruction.

The previously pending frontend integration was completed as merge `1429a34`: production build/type check passed, browser suite excluding screenshot capture reported 116 passed/8 skipped using mocked API data, and 155 backend tests passed with PostgreSQL/Redis. These results are not provider live evidence. Review found lowercase API status values versus uppercase badge comparisons, stale selected-job state on some history navigation, and a provider-error banner shared with search errors; these remain frontend follow-up items, not coverage work.

The owner has set tomorrow, November 7, as the internal completion target and explicitly expanded scope to accounts, saved profiles, private resumes and profile/resume-based job recommendations. The original acquisition objective and required 78-platform coverage remain unchanged. This is a target, not a claim that 71 remaining platforms can be completed and verified in one day.

Commit policy: make small coherent commits for contracts, schema, account security, resume processing, recommendations, tests and handoff. Every commit must have a substantive reviewable purpose. Do not add empty commits, split arbitrary lines or rewrite history to inflate the count.

## Execution priorities

1. Preserve verified indexing, lifecycle safety and source provenance. Continue expanding the 7/78 live platform coverage; unimplemented or bounded providers remain explicit.
2. Implement account/profile persistence and private resume APIs with owner-only access, secure sessions, rate limits, request bounds, encrypted resume storage, replacement and deletion.
3. Recommend existing open indexed jobs using explicit professional skills, desired roles and location/remote preferences. Explain the matching signals. Do not invent fit percentages, infer protected traits or transmit resume content to external services.
4. Hand the stable contracts to the frontend owner for signup/login/profile/upload and recommendation views within the established design direction.
5. Run database/service/security tests and full stack CI, then verify the actual frontend flows and hosted demo before calling the expanded product complete.

## Release gates

Accounts will be disabled unless an explicit trusted web origin is configured. Resume upload requires a separate valid encryption key. Production requires HTTPS, tested identity recovery/email verification and an operational review of private-data handling. Do not auto-create demo users or seed personal files. Passwords, session tokens, keys and resume content must not enter logs, evidence or commits.

A backend milestone is reviewable progress; it does not replace the full 78-provider acceptance criteria or imply the frontend/hosted release is ready. Report remaining work against the owner's target candidly.

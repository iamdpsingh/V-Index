# Delivery target — November 7, 2026 (IST)

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

# Release acceptance status

November 20, 2026. The owner paused production/deployment and submission, and
paused coverage expansion. Local proof does not satisfy deferred hosted checks.
[Release handoff](RELEASE_HANDOFF.md) is the current reviewer walkthrough.

| Requirement | Local evidence | Public acceptance |
| --- | --- | --- |
| Exact 78-platform inventory and live coverage | 71/78 with independent live examples | Incomplete; remaining platforms not waived |
| Consistent required/optional records | Shared normalization and audits; source gaps disclosed | Incomplete while required source fields are absent |
| Automatic refreshes | Running scheduler, repeated real refreshes, heartbeat and diagnostics | Deployed refresh proof deferred; 11 sources await initial success |
| Lifecycle safety | Complete-enumeration/two-miss-24h guards, cancellation and failure tests | Hosted observation window deferred |
| Deduplication | Historical live duplicate plus isolated replay; links and richer active fields preserved; distinct requisitions/locations separate | Reviewer walkthrough prepared |
| Search and API | Real local build, required filters, deterministic pagination, documented schema | Public deployment/reliability deferred |
| Private product | Candidate/Employer, profiles, resume storage, drafts, OAuth/SMTP backend and ownership tests | Real provider flows and inbox verification deferred |
| Security | Authorization/rate/cancellation checks, nonce CSP, no-store, signed proxy IPs, scoped scans | Actual deployed gateway/caching/secrets review deferred; Trusted Types report-only |
| Operations | Local heartbeat/alerts, backup tools and successful synthetic PostgreSQL restore | External notification, off-site backups and deployed restore deferred |
| Product review | Desktop/mobile real-data and profile editing; keyboard/focus/contrast tests; favicon and policy links | Public-domain browser review deferred |
| Handoff and costs | Code, specs, measured local resources/timing, dependencies and reviewer guide | Actual hosting setup/bills unmeasured while paused |
| Submission | Founder/startup pitch and evidence package drafted | Repository/demo connection and final submission unverified |

Failed or partial requests must never close jobs. Do not substitute fixtures,
unit tests, historic CI, a GitHub import or a synthetic restore for live platform
coverage, hosted operation or completed challenge submission.

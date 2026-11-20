# Rolewisp release handoff

> Documentation reconciled November 21, 2026. This is an active reference; dated evidence retains its original scope. [Documentation register](README.md) · [Complete handoff](../handoff/README.md).

Updated November 21, 2026. Production is authorized and running at
https://rolewisp.vercel.app. Coverage expansion is paused at **71/78 (91.0%)**;
this does not waive the remaining acquisition requirements. Earlier November 20
pause/local-only notes are historical, not the current operating instruction.

## Actual hosting

Vercel project `mandtechyt-1124/v-index` deploys Next.js `web`, internal FastAPI
`app`, and a persistent `worker` daemon in iad1 with 1 GiB memory and two fetch
slots. Public `/api/v1/*` requests pass through the same-origin web gateway;
`BACKEND_URL` is a runtime service binding, not a manually entered secret.
PostgreSQL and Redis hold durable index state and leases. The worker runs
independently of the owner's computer. See [Vercel setup](VERCEL_SERVICES.md)
and [operations](OPERATIONS.md). Never upload a local development database.

Initial registration schedules 142 reviewed sources. Initial indexing and
platform verification are different measurements: a historically verified
connector can still fail against a current upstream installation. Latest
production evidence and remaining gates are in [release status](RELEASE_STATUS.md).

## Reviewer walkthrough

1. Open the live demo. Combine keyword, company and location; paginate and
   inspect a role. Follow original listing/application links and inspect source
   provenance/check times. Missing source fields remain explicitly missing.
2. API: `https://rolewisp.vercel.app/api/v1/jobs?view=summary&limit=2&offset=0`.
   Change `offset`, then request `/api/v1/jobs/{id}` for full details. Read
   [API reference](API.md) and [OpenAPI](openapi.json). Interactive debug/schema
   routes are disabled; documented APIs are not secrets.
3. Operator-only sources, runs and operations require ADMIN_TOKEN. Keep it in
   memory/server settings, never URLs, screenshots or public update posts.
   Scheduling returns 202; it does not mean collection completed. Operations
   distinguishes last attempt, last success, failures, stale sources and heartbeat.
4. Create a disposable Candidate account. Profile begins read-only; Edit profile
   opens manual fields and qualification categories. Save, reload, upload/download
   a private resume, and delete the account after review. Parsing is intentionally
   absent. Resume and photo storage is encrypted and owner-only.
5. Employer accounts can draft/edit/close their own jobs. Unverified email blocks
   publishing. Live verification/recovery email and OAuth need real provider
   configuration and end-to-end delivery/login checks; no fake activation.
6. Run `PYTHONPATH=backend uv run python -m scripts.reviewer_replay --output .cache/reviewer-replay.json`.
   Four synthetic observations yield three jobs. Tracking variants merge with both
   links and useful metadata; distinct requisitions/locations stay separate.
   Partial snapshots reject without closures. This deterministic replay is not
   platform coverage. [Historical real duplicate](../evidence/cohort5-live-deduplication.json)
   is separate from the [latest hosted review](../evidence/20261121-hosted-release-review.json).
7. Review [hosted backup evidence](../evidence/20261121-hosted-backup.json) and
   [recovery instructions](OPERATIONS.md). Never restore directly over production.

## Handoff dependencies and open gates

Python 3.12, uv, Node 24, PostgreSQL (production major 18), Redis, Vercel services/
Daemons/private Blob, third-party public career pages and optional future SMTP/
OAuth providers are dependencies. Lockfiles, Dockerfile.worker, migrations and
connector evidence are committed. The worker contains matching PostgreSQL 18
client/server tools solely for disposable loopback restore drills.

No paid purchases/upgrades are authorized. Read the documented quota model,
measure actual provider usage/bills and stop before free-tier caps. Do not promise
20 days of uninterrupted service or a zero-dollar monthly cost without usage data.

The owner explicitly retains example@rolewisp.in as an unverified placeholder.
External notification delivery, real provider activation, legal/domain review,
post-snapshot deletion reconciliation, actual provider cost measurement and Vaya
submission remain gates. [Submission package](SUBMISSION.md), [backlog](BACKLOG.md),
[privacy review](PRIVACY_REVIEW.md), [release checklist](RELEASE_CHECKLIST.md).

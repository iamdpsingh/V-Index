# Rolewisp release handoff

Current hosted status, November 21: [Rolewisp](https://rolewisp.vercel.app) has
an active production worker and fresh live listings. The observed open-job count
increased from zero to 154, 235, 348 and 641 during verification. Initial
indexing is still in progress; all-source completion has not been claimed.
The same hosted worker continues scheduled refreshes independently of the
operator computer. See [worker evidence](../evidence/20261121-production-worker.json)
and [desktop/mobile production review](../evidence/20261121-production-product-review.json).
The Vaya script is in the shared head; its image beacon still needs the owner's
requested CSP decision. The free-tier window and monthly limits are documented
in [Vercel setup](VERCEL_SERVICES.md#persistent-production-indexing-worker).

The November 20 entries below are historical snapshots of the release pass.


Production troubleshooting update, November 20: the owner authorized Vercel
access and database repair. The production database was empty and is now
migrated; public search returns 200 with zero jobs. Initial indexing and a
continuous production worker are still open. See the [recorded repair](VERCEL_SERVICES.md#production-repair-recorded-november-20).
Earlier pause/status notes below describe the preceding release pass.


Updated November 20, 2026. This is the current release entry point. The owner
paused coverage expansion and all production/deployment/submission actions.
The existing GitHub repository has been imported into Vercel, but no hosted
project URL or running backend was verified in this pass. No paid service was
provisioned. Keep the original 78-platform requirement open at 71/78.

## Run the integrated product

Use canonical `main` in this repository. Python 3.12+, uv, Node 24+, PostgreSQL
17 and Redis 7 are the production-stack dependencies. The current local demo
uses SQLite with a serial worker. Do not replace an existing database or its
resume key to reproduce a fresh installation.

- Open `http://localhost:3000` for the local product.
- API/database liveness is `http://127.0.0.1:8000/health`.
- Start from a new checkout using [deployment instructions](DEPLOYMENT.md).
- Developer API contract: [API reference](API.md), [OpenAPI](openapi.json).
  Interactive schema/debug routes are intentionally disabled in the product.
- Runtime operations, backups and recovery: [operations](OPERATIONS.md).
- Exact source support and limitations: [coverage matrix](COVERAGE.md).

The local API, worker, web server and monitor run separately. Stopping the web
server does not run indexing elsewhere. Source schedules and observations are
persistent in SQL; Redis holds expiring leases, rate counters and heartbeats.

## Reviewer walkthrough

1. Open the job index. Search by keyword, company and location. Next/Previous
   updates the URL; selecting a role shows the original listing, application
   destination, source status and check times. Application links stay HTTPS.
2. Review `/?tab=coverage` for the exact provider inventory and evidence limits.
   Open `/?tab=sources` only with the private operator token entered in memory.
   Adding/refreshing a source schedules work; it is not presented as completed.
3. Inspect the authenticated `GET /api/v1/operations` and recorded local
   [release snapshot](../evidence/20261120-local-release-snapshot.json). It shows
   a live worker, repeated successful local refreshes and genuine source errors.
   Repeated local refreshes are not evidence of a deployed service.
4. Run the isolated deterministic dedupe/lifecycle walkthrough:

   ```sh
   PYTHONPATH=backend uv run python -m scripts.reviewer_replay --output .cache/reviewer-replay.json
   ```

   Four observations produce three jobs: tracking variants merge with both
   source links, while different requisitions and locations remain separate.
   A sparse duplicate borrows useful active-source metadata with `field_sources`
   provenance. Original observations are unchanged. A partial snapshot is
   rejected and changed descriptions are visible. This replay is synthetic,
   never platform coverage. A separate historical real-board duplicate is
   documented in [the November 6 evidence](../evidence/cohort5-live-deduplication.json).
5. Create a temporary Candidate account. Complete the manual profile and
   qualification categories, upload a resume for private storage, and open
   recommendations. The profile starts read-only; Edit profile opens the form.
   Resume parsing is intentionally removed. Photo/resume data is encrypted.
6. Choose Employer on a separate temporary account. Create/edit/close a draft.
   Publishing requires verified email; unverified publication is rejected.
   SMTP and social-provider credentials remain unconfigured for production.
7. Inspect [the PostgreSQL restore drill](../evidence/20261120-backup-restore-drill.json).
   It restored all 16 tables, decrypted a synthetic resume/photo, and rejected
   tampering, same-database restoration and nonempty target replacement.

## Validation and operating measurements

- Backend verification uses PostgreSQL and Redis, plus SQLite fixtures. Read
  the current test output and CI for the exact revision. The release status
  records the final totals rather than treating earlier green CI as new CI.
- Browser tests cover desktop/mobile, keyboard/focus, contrast, search/detail,
  profile editing, private flows, employer drafts, policies and CSP enforcement.
- [Real-data product review](../evidence/20261120-real-data-product-review.json)
  used the production Next build against the running local index, with no
  horizontal overflow or page errors. [Private-profile review](../evidence/20261120-private-profile-product-review.json)
  used a synthetic account that was deleted afterward.
- The recorded local snapshot had 8,410 open canonical jobs, a 294,219,776-byte
  SQLite database, and ten successful 25-job summary requests. Median loopback
  response time was 12.61 ms; maximum 429.02 ms. These are local samples, not an
  internet latency, uptime or load-capacity promise.
- No new paid services were used. Existing hardware, power and internet were
  not metered. Hosted operating cost is unmeasured because deployment is paused.
  Do not publish a fictitious zero-dollar monthly operating-cost claim.

## Remaining limits

The recorded local source audit has 132/143 initial successes, 11 pending
initial successes, 13 failing sources and one stale source. Four existing-source
failures were repaired: Rippling's English locale query key, SmartJobBoard's
accented slugs and JBoard's native pipe-containing slug. These are runtime
repairs, not additional platform claims. Remaining errors are preserved and
monitored. The latest additional failure is a Personio translated-feed identifier mismatch, which is retained as incomplete enumeration. No source was silently dropped to improve the count.

Required source-field gaps also remain documented. Source failures and missing
fields prevent full challenge acceptance, even though local search works.
Deployment-specific authorization/proxy/caching checks, real SMTP/OAuth,
support-inbox verification, external alerts, off-site backup setup, legal
review and Vaya submission are deferred. The address `example@rolewisp.in`
remains as supplied; successful delivery has not been claimed.

See [privacy review](PRIVACY_REVIEW.md), [local security review](../evidence/20261120-local-security-review.json),
[current backlog](BACKLOG.md) and [submission draft](SUBMISSION.md).

Final validation is summarized in [local checks](../evidence/20261120-local-validation.json). The four existing-source repairs have [worker-run evidence](../evidence/20261120-source-refresh-repairs.json).

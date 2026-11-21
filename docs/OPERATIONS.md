# Runtime operations and recovery

> Documentation reconciled November 21, 2026. This is an active reference; dated evidence retains its original scope. [Documentation register](README.md) · [Complete handoff](../handoff/README.md).

November 21: the Vercel worker is deployed. PostgreSQL/Redis are the production
state/lease services; local SQLite is separate. Coverage expansion stays paused.
The cloud worker fills either of its two slots as soon as a source finishes.

## Hosted supervision and backup

`HOSTED_OPERATIONS_ENABLED=true` is set by the production launcher. Monitoring
runs independently of source fetches, caches current diagnostics in Redis, records
bounded failure/staleness alert transitions for seven days and emits safe logs.
Private Blob `operations/latest.json` updates every thirty minutes; it is an
operator report, not a public endpoint. API `/api/v1/operations` requires the
operator token. A worker cannot notify anyone after its entire host stops;
independent external uptime/alert delivery still needs a real receiver.

The daily hosted backup exports a consistent PostgreSQL snapshot, encrypts with
a separate AES-256-GCM key, fully restores into a temporary PostgreSQL 18 instance
on loopback, compares all table counts, and uploads only after success. The
restore child environment excludes production credentials. Temporary database,
plaintext dump and test instance are removed. No live production restore occurs.

Dedicated private Vercel Blob `rolewisp-production-backups` (iad1) stores the
archives. Anonymous downloads are denied. Provider-enforced seven-day expiry
continues even if the worker stops; successful uploads require the provider to
confirm expiry. Local inventory pruning also keeps recognized archive names
within a 512 MiB budget, with a 128 MiB maximum per archive. Oversized snapshots
fail visibly rather than exceed the budget. A Redis lock prevents overlapping
daily backups; failures retry hourly and appear in monitoring.

Required server-only variables: BLOB_READ_WRITE_TOKEN, BLOB_STORE_ID and
BACKUP_ENCRYPTION_KEY. Keep backup and resume encryption keys in an independent
secured recovery location. The project settings alone are not independent key
custody. Do not rotate either encryption key without a data migration/recovery plan.
Private reports `operations/backup-latest.json` and `operations/release-review.json`
contain backup/probe outcomes, not credentials or private resume contents.

Python Blob SDK 0.6 lacks TTL arguments. The narrow fixed-host upload hook uses
the official @vercel/blob 2.9.0 wire headers `x-ttl-days: 7`, API version 13 and
checks the returned `expiresAt`. See the [provider TTL announcement](https://vercel.com/changelog/vercel-blob-now-supports-ttls-for-automatic-deletion).
Recheck this bridge when upgrading either SDK. No uncontrolled outbound host or
environment proxy is used.

## Refreshes and failures

Keep the worker running with `PYTHONPATH=backend uv run python -m vindex.worker`.
It polls due sources every 30 seconds. PostgreSQL supports 1 to 16 simultaneous
sources (default 4); SQLite stays serial. Each source has a Redis lease and an
atomic ingestion transaction. Schedules persist in SQL across restarts.

Never infer job closure from an exception, malformed response or partial page.
Only complete enumeration permits absence checks, and closure requires two
misses separated by at least 24 hours. Interrupted refreshes become failed
runs without changing observations; checkpointed source work remains resumable.
Hourly maintenance retires abandoned running attempts older than an hour,
beyond all current fetch/lease budgets, without changing job lifecycle.

Source failures back off, preserve detailed operator-only diagnostics and never
become successful empty results. Retry-After and transient failures respect
stored cooldown. Inspect the native site/schema and access policy; don't bypass
restrictions or remove a source merely to make the dashboard green.

## Health and alerts

`/health` proves API/database liveness only. Authenticated
`GET /api/v1/operations` reports initial indexing, latest attempt, latest success,
consecutive failures, staleness, abandoned attempts, live workers and CSP counts.
No candidate/profile data or raw security-report samples enter these metrics.

A worker updates its own Redis heartbeat every 15 seconds with a 90-second TTL,
independently of long network fetches. Missing workers/Redis, any failing source,
a success older than max(2 hours, twice its configured interval), and abandoned
runs produce explicit alert classifications. Original attempt errors remain
behind operator authorization. Worker event logs contain IDs/counts/error types,
not request URLs, source payloads, emails, resume text or credentials.

```sh
PYTHONPATH=backend uv run python -m scripts.monitor --output .cache/monitor.json
PYTHONPATH=backend uv run python -m scripts.monitor --watch --interval 60 --output .cache/monitor.json
```

One-shot monitoring exits 1 for an alert, 0 for healthy. Watch mode atomically
updates a private local file and logs state changes without repeating identical
alerts. It does not send emails or webhooks. Connect a verified notification
channel; the example support address is not a receiver.
`ops/rolewisp-monitor.service` is a hardened Linux template, not installed here.
Host log retention and notification delivery still need deployment validation.

## Backups and restore

Use PostgreSQL client tools matching the database major version and the project
Python environment. The API image does not include pg_dump. Run these tools on
a secured operator host. DATABASE_URL and RESTORE_DATABASE_URL stay in private
environment files, never CLI arguments or evidence. The backup role needs read
access to all application tables; use a separate empty restore database.

Generate BACKUP_ENCRYPTION_KEY privately as a 32-byte base64 key, separately
from RESUME_ENCRYPTION_KEY. Retain both in an independent secured recovery
location. A database backup without the original resume key cannot decrypt
stored resumes/photos. Rotating environment text does not rotate persisted
database passwords or re-encrypt existing private data.

```sh
PYTHONPATH=backend uv run python -m scripts.backup_database backup --directory /secure/backups
PYTHONPATH=backend uv run python -m scripts.backup_database restore --archive /secure/backups/rolewisp-EXAMPLE.rwbackup
PYTHONPATH=backend uv run python -m scripts.backup_database prune --directory /secure/backups
```

Backups use an exported consistent PostgreSQL snapshot, compressed pg_dump,
streamed authenticated AES-256-GCM, authenticated count manifest, exclusive file
creation and mode 0600. The temporary plaintext dump stays in a private temporary
directory and is removed afterward. Restore verifies authentication before
running pg_restore, refuses the source database or nonempty target, restores in
one transaction, and compares every public-table count with the snapshot.

Pruning removes only this tool's recognized archives older than 30 days.
`ops/rolewisp-backup.service` and `.timer` prepare a daily UTC schedule plus
pruning; they are not installed or enabled. Replicate encrypted archives to an
approved independent storage location before calling this an off-site backup.
These local systemd templates are alternatives to the deployed cloud routine,
not installed services. The cloud routine above uses seven-day provider TTL;
the manual local prune command below retains its older thirty-day default.
Never use that local default for public production retention promises.

Test recovery without touching user data:

```sh
PYTHONPATH=backend uv run python -m scripts.check_backup_restore --pg-bin /usr/bin --output .cache/restore-drill.json
```

Set TEST_DATABASE_URL to a disposable local PostgreSQL instance whose user can
create/drop databases. The drill creates only randomly named databases,
restores synthetic data, checks private file decryption and tamper/overwrite
rejection, then removes those disposable databases. Its encryption keys are
intentionally ephemeral. [Recorded drill](../evidence/20261120-backup-restore-drill.json).
The hosted routine above now verifies an actual production snapshot separately.
This synthetic test also exercises private-file decryption and tamper guards.

## Privacy retention and recovery gates

Sessions expire after seven days; email/recovery codes after fifteen minutes.
Independent hourly maintenance removes expired sessions and clears expired code
hashes even when indexing is busy. OAuth state expires in Redis after ten minutes.
Live account deletion removes owned profile/resume/session records; public
employer postings follow the documented account-deletion lifecycle.

Before reopening a restored production backup, reconcile account deletions
made after its snapshot, rotate/revoke sessions as appropriate, run migrations,
verify private-file keys and permissions, inspect source schedules/leases and
perform the private/API/search walkthrough. A separate durable post-snapshot
deletion ledger/operating procedure remains a production privacy gate.

Measure the running local index with `scripts.release_snapshot`; do not use
local loopback timing or a synthetic restore as hosted SLA evidence.

November 21 hosted-worker configuration: the existing Vercel project now has a
single 1Gi `worker` daemon configuration with idempotent source registration and
the persistent scheduler. Read [VERCEL_SERVICES.md](VERCEL_SERVICES.md#persistent-production-indexing-worker)
for inspection, stopping, the November/December free-tier window and quota
limits. A configured daemon becomes operational evidence only after its actual
instance and successful production fetches are verified.


## Independent external probe, November 21

`.github/workflows/production-monitor.yml` checks from GitHub runners twice an
hour (cron minutes 17/47) and supports manual dispatch. It uses a separately
generated `MONITOR_TOKEN` in Vercel Production and GitHub Actions Secrets. This
token accesses only `/api/v1/monitoring` aggregate health; it cannot authorize
operator/source/private-account APIs. Do not copy ADMIN_TOKEN into Actions.

The probe checks public search, no-store, live worker/Redis, monitoring timestamp,
backup success/age (36-hour budget), stale sources and abandoned runs. Source
failures are warnings, never automatic closures. Critical conditions fail the
workflow and create GitHub check-run error annotations. `exercise_alert=true`
produces an explicitly labelled controlled failed run after live checks; it
does not stop services or pretend a real outage occurred.

The scheduled/manual workflow is an independent probe, not guaranteed email/SMS
delivery. A real notification receiver remains unverified at the owner's request.
GitHub scheduling can be delayed; this is not an uptime/SLA guarantee.
[Schedule semantics](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

Restore now verifies original table counts first, then invalidates sessions and
verification/recovery codes only in the isolated target. Result counts describe
the authenticated pre-sanitization snapshot; target session count subsequently
becomes zero. The source is unchanged. Post-snapshot account-deletion
reconciliation remains mandatory and is not automated by session revocation.
[Actual isolated drill](../evidence/20261121-recovery-auth-revocation.json).

## Snapshot churn retry correction

A JobBoardFire roster/sitemap disagreement or a roster changing during collection
is now a distinct SnapshotChangedError. The attempt still fails without ingestion
or closures, but retries follow the bounded transient schedule (2/4/8/16, then at
most 30 minutes) instead of backing off like a persistent schema/policy failure
up to 24 hours. This prevents a short native-index inconsistency from leaving a
recovered board unchecked for most of a day. Robots denial and HTTP 429 retain
policy/cooldown/Retry-After handling; no complete-enumeration guard is waived.

A fresh full LPJC native probe collected nine jobs while public provenance showed
its production source was stale. A one-time startup recovery may reschedule only
that reviewed board's prior JobBoardFire ValueError, not policy/rate failures.
Actual production recovery must be recorded separately.

Monitoring source-issue entries include source ID/provider, classified cause,
last success and next check (at most 200, with an explicit truncation flag).
They intentionally exclude URLs/raw errors/private records. This makes a failed
external check actionable without exposing ADMIN_TOKEN or expanding the monitor
token into operator authorization. A successful local native probe alone does
not prove a source succeeds from the hosted worker's network.

# Runtime operations and recovery

November 20: production is on hold. These are tested local tools and future
installation instructions, not a claim of active cloud monitoring or backups.
The local demo uses SQLite; PostgreSQL 17/Redis are the intended production
store/lease services. Coverage expansion remains paused.

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
channel when production resumes; the example support address is not a receiver.
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
No off-site destination, cloud backup bill or actual notification receiver is
configured in this pass.

Test recovery without touching user data:

```sh
PYTHONPATH=backend uv run python -m scripts.check_backup_restore --pg-bin /usr/bin --output .cache/restore-drill.json
```

Set TEST_DATABASE_URL to a disposable local PostgreSQL instance whose user can
create/drop databases. The drill creates only randomly named databases,
restores synthetic data, checks private file decryption and tamper/overwrite
rejection, then removes those disposable databases. Its encryption keys are
intentionally ephemeral. [Recorded drill](../evidence/20261120-backup-restore-drill.json).
This does not replace restoring an actual hosted backup after deployment.

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

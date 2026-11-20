# 05 · Operations and recovery runbook

Detailed commands and semantics: [operations](../docs/OPERATIONS.md).

## Daily operating checks

| Check | Expected signal | Response if abnormal |
| --- | --- | --- |
| Public demo/API | Search/detail 200 with valid source/application links | Inspect gateway/API deployment, DB health and safe error logs |
| Worker | One ready/alive daemon plus fresh Redis heartbeat | Inspect daemon status, restart cause, DB/Redis reachability and quotas |
| Initial collection | Source initial-success and pending counts | Investigate each pending source; registration alone is not indexing |
| Freshness | Last success separately from last attempt | Inspect cooldowns, queue/source age and native restrictions |
| Failures | Categories and Retry-After/cooldown preserved | Treat as failed fetches; never empty successful snapshots |
| Backups | Last success within intended daily window, restore/count proof | Inspect safe error type, key/store config, PG tools and storage budget |
| Resources | Vercel/DB/Redis/Blob usage below caps | Reduce permitted load or stop before caps; no paid upgrade authorized |

Commands from an authenticated operator checkout:

```sh
npx vercel@latest daemons inspect worker --project v-index
npx vercel@latest logs --project v-index --query 'source:daemon' --since 15m
```

Operator `/api/v1/operations` requires ADMIN_TOKEN; `/health` is API/DB liveness,
not complete source freshness, and is internal on Vercel. Use provider dashboards
and private reports rather than exposing tokens in URLs or public screenshots.
Private Blob `operations/latest.json` updates every thirty minutes; Redis/API
status is more current. Reports and bounded alert history expire after seven
days. Internal monitoring cannot notify after the entire host stops. External
uptime monitoring/delivered alerts still need a verified receiver.

## Incident response

1. Record UTC time, deployment/SHA, affected service and safe error class. Do not
   copy secrets, raw private data or credential-bearing URLs into tickets/logs.
2. Identify scope: frontend, gateway/API, PostgreSQL, Redis, worker, source or quota.
   An upstream failure is not proof every listing closed.
3. For a source issue, preserve last good observations and cooldown; check native
   policy/schema/identity/completeness. Respect robots and 429. No challenge bypass.
4. For API ProgrammingError, check migration head/schema with secured operator
   tooling; never destroy/recreate the database as a shortcut. Match schema to code.
5. For quota or runaway worker, stop the daemon without deleting data:
   `npx vercel@latest daemons scale worker iad1=0 --project v-index`.
   Resume deliberately after the root cause/limits are understood.
6. Restore service, repeat public/private checks, verify heartbeat/source schedules
   and record cause, impact, mitigation and follow-up. Do not declare recovery from
   a frontend build alone.

## Backup contract

Daily consistent PostgreSQL snapshot → compressed dump → authenticated AES-256-GCM
archive → full restore in disposable loopback PostgreSQL 18 → all-table count
comparison → private Blob upload. Plaintext/temp database are removed afterward.
A 128 MiB per-archive cap and 512 MiB retained-archive budget fail visibly if
exceeded. Provider-confirmed seven-day TTL expires backups even if worker stops.
The manual local prune utility has a thirty-day default; it is not the hosted
retention policy. Never confuse these two modes.

First production proof: 42,387,200 encrypted bytes, 16 matching restored tables,
anonymous archive access HTTP 403. This is a successful snapshot drill, not
proof of an independently retained key, legal compliance or every failure mode.
See [recorded backup](../evidence/20261121-hosted-backup.json).

## Actual disaster recovery

1. Identify the selected private archive, snapshot time, expected hash and manifest.
   Retrieve using authenticated storage tooling into a restricted directory.
2. Obtain the original BACKUP_ENCRYPTION_KEY and RESUME_ENCRYPTION_KEY from
   independent custody. Missing resume key makes stored private files unreadable.
3. Create a separate empty PostgreSQL target. Match client tools to the server.
   Keep DATABASE_URL identifying the source and RESTORE_DATABASE_URL the isolated
   recovery target. The restore utility refuses source or nonempty targets.
4. Run `PYTHONPATH=backend uv run python -m scripts.backup_database restore --archive /secure/recovery/selected.rwbackup`.
   Verify authentication, manifest/table counts, schema head and private-file keys.
5. Reconcile account deletions made after the snapshot, revoke sessions as needed,
   inspect source schedules/leases, test authorization/search and get responsible
   operator acceptance before exposing recovered data. A durable deletion ledger
   is not implemented; do not skip this privacy gate.
6. Switch the application only through a planned cutover. Record recovery point,
   elapsed recovery time and lost/reconciled changes. RPO/RTO are not measured SLAs.

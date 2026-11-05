# Operations

Use /health for API/database liveness; it does not claim worker or provider health. Authenticated /api/v1/runs shows source failures. /api/v1/sources shows due times and consecutive failures. Provider implementation/evidence is exposed separately at /api/v1/providers. Worker logs include source/run IDs, counts and failure type. Structured JSON logging and worker heartbeat alerting remain backlog.

A failing source backs off to a maximum 24-hour interval. Investigate the run error, upstream changes and access policy. Never convert failure into a successful empty enumeration. Mark blocked providers honestly and do not bypass restrictions. Source refresh endpoint schedules a retry. Redis unavailable prevents refreshes and produces infrastructure errors; existing jobs stay searchable.

Back up PostgreSQL using pg_dump and restore into an isolated instance before promoting. Retain evidence and migrations with source. Run `alembic upgrade head` on deployment. Snapshot database before migration; initial downgrade is destructive. Redis is only lease state; source schedules live in PostgreSQL. Crash-held leases expire in 15 minutes. Running runs left by process termination need operator reconciliation; automatic stale-run handling is a backlog item.

Monitor source age, consecutive failures, abnormal count drops, stale running runs, database size and API latency. Sudden successful empty snapshots are protected by two-miss/24h grace but still need alerting. Evidence has no job applicant data; avoid collecting candidate/application submissions.

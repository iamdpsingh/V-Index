# Architecture

Current reference, November 21, 2026. See [system diagram and component inventory](../handoff/02_SYSTEM_ARCHITECTURE.md).

## Runtime and data flow

Next.js `web` is public; its same-origin gateway calls internal FastAPI `app`
through the runtime BACKEND_URL binding. A separate persistent Vercel `worker`
collects due sources. PostgreSQL stores durable index/private data and schedules;
Redis stores leases, rate/state/heartbeat/monitoring information. Alembic owns
schema changes. SQLite/Compose are local alternatives, not production storage.

Validated source URL → provider/tenant detection → bounded native public fetch →
complete enumeration → typed records → conservative identity and atomic ingestion
→ canonical jobs/source observations/change events → search/detail API.
71 platforms have independent historical live verification; registry contains all
78 required names. Do not infer connector acceptance from module presence.

## Correctness and search

Redis source leases plus PostgreSQL row locking serialize reconciliation.
Partial/failed collection never publishes a successful replacement or closes
jobs. Closure requires two complete misses at least 24 hours apart; reappearance
can reopen observations. SQL checkpoints support staged Jobiqo, Madgex and
Talenetic collection. A stage is not a published complete snapshot.

Identity combines normalized application URL/company/title/location, stripping
known tracking parameters and retaining unknown ones. Active-source enrichment
preserves useful metadata with field provenance; original observations remain
private. Full immutable per-run observation snapshots are not implemented.

Public serializers expose normalized fields, flags and source/provenance
tracking times while leaving raw source payloads private. Descriptions render
as text. Parameterized substring filters use pg_trgm indexes on PostgreSQL,
active-job/due-source indexes and descending-ID offset pagination. A changing
index can change pages; no snapshot cursor or full-text ranking is claimed.

## Scheduling and recovery

Generic PostgreSQL concurrency defaults four (configurable 1–16); hosted launcher
defaults two; SQLite uses one. Free slots refill when a fetch completes, with a
30-second due-work polling ceiling. Sources default six-hour intervals. Most
attempts allow 600 seconds with 900-second leases; JobMount uses 1,800/2,100
seconds. Bounded request retries respect Retry-After. Transient failures use
shorter exponential cooldowns; other failures can back off to 24 hours.

Independent 15-second heartbeats expire after 90 seconds. Hourly maintenance
retires abandoned runs and expired authentication artifacts. Monitoring caches
status, logs alert changes and publishes private reports every thirty minutes.
Daily encrypted PostgreSQL backups undergo full disposable loopback restore
before private upload, with provider-enforced seven-day expiry. External alert
delivery and independent key custody remain open.

## Trust boundaries

Operator routes require a private bearer token; private account routes require
sessions, exact mutation Origin and ownership/role checks. Redis-backed limits
and fresh HMAC proxy metadata protect deployed budgets. API/private HTML uses
no-store; nonce script CSP is enforced and Trusted Types is report-only.

Outbound destinations are restricted/validated by the reviewed connector rules,
with fixed API hosts or explicitly permitted installations, disabled environment
proxies/redirect following, bounded response sizes/pages/timeouts and robots
handling. Custom hosts are supported only where explicitly reviewed; arbitrary
URL fetching, private-network access and access-control bypass are forbidden.
Network-level egress defense and broad distributed host budgets still require
review before scaling. [Collector details](CONNECTOR_CONTRACT.md),
[security/privacy](../handoff/06_SECURITY_AND_PRIVACY.md).

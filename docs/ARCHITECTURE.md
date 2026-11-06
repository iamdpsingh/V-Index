# Architecture

FastAPI exposes versioned JSON and OpenAPI. SQLAlchemy targets PostgreSQL; SQLite supports local tests. Alembic owns schema deployment. Redis leases serialize workers by source, a PostgreSQL source-row lock protects reconciliation, and the entire index update commits atomically. A worker polls the durable due time in sources; a crash before commit leaves the source due for replay. Crashed running fetch records currently require operator investigation.

## Data flow

Source URL -> exact provider/tenant detection -> fixed-host API request -> complete enumeration -> typed normalization -> conservative identity -> canonical job and source observation -> search.

Five platform connectors are implemented: Greenhouse, Lever, Ashby, SmartRecruiters and Personio. Provider definitions (78 required entries) live in backend/providers.json. Source rows represent individual boards with independent schedule, company label and failure state. Canonical jobs hold representative normalized data. Observations retain each source's original payload and metadata. Change events record create/update/close/reopen. Fetch runs retain source, time, count and errors.

Only exact application URL plus normalized company/title/location merges observations. Known attribution parameters are removed; all unknown parameters remain. No fuzzy title matching. This sacrifices recall to avoid merging distinct requisitions. Old unreferenced canonical rows are retained for audit and excluded from active search. Conflict-aware field enrichment and immutable per-run observation history remain backlog.

Descriptions become plain text. Original payloads remain in observations. Search currently uses parameterized case-insensitive JSON-field contains queries with literal wildcard escaping and deterministic descending IDs. PostgreSQL full-text indexes are planned once representative volume is measured; current filters are correct but will scan at scale.

## Security boundary

User URLs are parsed as identifiers only; exact hosted-domain allowlist and restricted slug characters map to fixed HTTPS API hosts or a validated single Personio tenant label under its documented jobs.personio.de/com domains. User input cannot select outbound hosts, ports, headers, paths outside a tenant segment, or redirects. Proxy environment is disabled; HTTPS certificate verification remains enabled. Response decompressed bytes, page counts, timeouts and refresh execution are bounded. A network egress allowlist remains necessary for defense against DNS compromise; do not enable arbitrary custom-domain fetching until DNS pinning and private-IP checks are implemented.

Source mutation/status requires a configured bearer admin token. Public job queries remain read-only. Use TLS and rate limits at a gateway before exposure. No authentication, CAPTCHA or anti-bot bypass. Only documented public APIs are requested; custom HTML scraping and robots handling are not yet implemented. Raw payload access via job details should be reviewed before public production exposure.

## Reliability limits

Retries are bounded to three attempts with jitter for transport errors, 429 and 5xx. Per-source cooldown grows exponentially to 24 hours. Worker processes sources sequentially (global concurrency one); Lever pages are separated by 0.5 seconds. Redis lease is 15 minutes; refresh is bounded to ten minutes. Retry-After is honored within the inline retry budget; add per-host distributed limits before scaling workers. PostgreSQL migrations, API/lifecycle behavior, real Redis worker serialization and rollback after reconciliation failure have service-backed tests. Wider distributed concurrency, deployment recovery and migration rollback remain unverified. Workers recheck the persisted due time after acquiring a lease, so a stale scheduler selection does not repeat a completed refresh.

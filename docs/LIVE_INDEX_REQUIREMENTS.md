# Rolewisp continuous index and freshness contract

Owner clarification, November 6, 2026: production must discover new openings, update changed records and recognize removals continuously. The jobs collected during development are not a fixed production dataset.

## Current behavior

The API reads persisted database records on each request. Registering a supported source schedules its first refresh immediately; the worker checks due sources in batches every 30 seconds. A successful complete refresh updates observations, adds newly seen jobs, preserves original links, records a fetch run and schedules the next check. Source schedules live in SQL and survive worker restarts; Redis leases prevent simultaneous refreshes of the same source.

The default source interval is 360 minutes (six hours). The current API permits 60–10,080 minutes. These are refresh settings, not a measured production freshness SLA: upstream latency, run duration, backlog, rate limits and failures add delay. The worker currently runs selected sources serially, so capacity must be measured before promising an hourly or minute-by-minute freshness guarantee. The current `/health` endpoint proves API/database reachability, not successful ingestion or worker health.

Failed, malformed, oversized, redirected, robots-denied or incomplete fetches must record failure without closing existing listings. Missing jobs close only after at least two complete misses separated by 24 hours. Reappearance reopens them. Failure cooldown can delay the next attempt up to 24 hours; surface source age honestly while preserving the last good data.

## Browser behavior

The frontend uses live API queries, not bundled snapshots. It refreshes results periodically while visible and on focus/manual request, preserves query/selection/scroll state, and differentiates browser refresh time from upstream listing checks. Cache-Control must prevent API data from being frozen by browser/shared intermediary caching; deployment must not override that policy with static exports or forced CDN caching. A page reload or poll does not itself trigger provider ingestion.

Use exact available timestamps. `first_seen_at` is when this index first observed the record; `last_changed_at` is a content/lifecycle change, not proof of a successful recent fetch. `sources[].last_checked_at` is the observation's last complete check, which may include a missing-listing check during closure grace. Do not relabel it as “last seen open.” A platform's evidence `last_run_at` concerns a connector smoke run, not the freshness of every job on that platform.

No instant upstream push protocol is implemented. If sub-hour ingestion or push updates become requirements, first define per-provider permitted access, webhook availability, rate/capacity budgets and API contracts. Do not fabricate live progress, notifications or timestamps in the interface.

## Production acceptance still required

- Deploy the API, persistent PostgreSQL, Redis and an independently running worker/scheduler; publishing only the frontend does not create a continuously updated index.
- Verify a newly registered source, repeat complete refreshes, a real or controlled changed/new job observation, searchable updates without a frontend rebuild, and failure preservation. Controlled regression tests do not count as platform live coverage.
- Establish per-source freshness objectives from measured run duration, source volume and permitted rates; monitor overdue sources, consecutive failures, queue age and worker heartbeat. Select schedules that the deployed capacity can meet.
- Exercise worker restart/crash recovery, expired leases, stale running-run reconciliation and backup restore. Automated stale-run recovery/heartbeat monitoring remain backlog; do not describe them as implemented.
- Demonstrate the browser sees updated database data, avoids stale shared caches, retains current reading state and presents unknown/stale/error states truthfully.

Continuous production operation has not yet been established by local scheduled runs or CI. The coverage objective and budget remain unchanged.

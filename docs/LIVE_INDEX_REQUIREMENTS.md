# Continuous indexing and freshness contract

Current reference, November 21, 2026. Production is an active pipeline, not a
bundled development dataset. [Worker evidence](../evidence/20261121-hosted-release-review.json).

## Executable behavior

Supported source registration schedules work immediately. Persistent SQL due
times survive restarts. A separate worker fills available slots when a source
finishes, polling for due work at most every thirty seconds when idle. Hosted
PostgreSQL defaults two slots, generic worker four, SQLite one. Redis source
leases and a SQL transaction protect reconciliation. Staged collectors checkpoint
without exposing a partial replacement snapshot.

Source default interval is 360 minutes; API permits 60–10,080. Successful complete
runs add new jobs, update observations/change records and schedule the next run.
Transient failures use shorter exponential cooldowns and honor Retry-After;
other failures can back off to 24 hours. A six-hour setting is not a freshness SLA:
queue time, native rate/policy, collection duration and failures all add delay.
Most attempts have a ten-minute fetch budget; JobMount uses thirty minutes.

A failure, malformed/oversized payload, redirect or incomplete enumeration never
closes listings. Closure requires two complete misses at least 24 hours apart.
Reappearance can reopen. Interrupted attempts and abandoned-run cleanup record
failures and retain the last good index. Independent heartbeat and hourly
maintenance operate even during long fetches.

## Browser and timestamp semantics

The UI queries live persisted data, periodically refreshes while visible and on
focus/manual action, and preserves filters/selection/navigation state. No-store
API/private HTML prevents a static shared cache from freezing the index. Browser
polling does not itself fetch upstream sources or establish instant job detection.

First-seen, last-changed and last-checked timestamps mean different things.
A source check during absence grace is not proof the role remained open. A
platform smoke-run timestamp is not the freshness of every job on that platform.
Unknown/stale/error states must remain honest. No upstream webhook/push protocol
or minute-level freshness promise is implemented.

## Observed proof and remaining gates

The actual hosted worker collected fresh data; the recorded repeat native Ashby
fetch moved from 77 to 78 jobs and increased public search total to 7,937 without
a frontend rebuild. It was an operator-triggered refresh, not a completed
six-hour unattended cycle. At that snapshot 127/142 registered sources had an
initial success, fifteen lacked one and fourteen had consecutive failures.

Independent 15-second heartbeat/90-second expiry, internal failure/stale diagnostics,
private status reports and actual isolated backup restore are implemented.
External host-down/delivered alerts, measured freshness objectives/capacity and
complete initial success across all sources remain open. See [operations](OPERATIONS.md).

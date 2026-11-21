# Operating costs and external dependencies

Baseline November 21, 2026. **No paid purchase/upgrade is authorized.** The
current Vercel account was checked as Hobby. Actual monthly invoice, CPU usage,
PostgreSQL/Redis allowances and complete steady-state cost remain unmeasured.
Do not advertise a guaranteed free service window or invent monthly spend.

## Actual resource model

| Resource | Deployed/required configuration | Cost or limit evidence |
| --- | --- | --- |
| Vercel web/API | Next.js and FastAPI services, same project | Subject to project plan/function/transfer limits; inspect dashboard |
| Indexing daemon | One 1 GiB worker, iad1, two slots | Recorded Hobby allowance: 420 GB-hours memory and five active CPU-hours per calendar month; stops at caps |
| PostgreSQL | Existing hosted production DB, observed major 18 | Provider plan, storage/compute/transfer bills not verified here |
| Redis | Existing hosted TCP/TLS service | Provider memory/command/connection allowances not verified here |
| Private Blob | Dedicated iad1 store, seven-day TTL | Recorded Hobby allowance: 1 GB, 2,000 advanced ops, 10 GB transfer/month; stops at caps |
| Email/OAuth | Optional future real providers | No live provider activation or measured charges claimed |
| Domain | Working rolewisp.vercel.app demo | No purchased/custom domain recorded |
| Listing extraction | Allowed native APIs/feeds/pages | No paid extraction/anti-bot service; availability and permissions remain dependencies |

At the measured 42,387,200-byte snapshot, seven daily archives project about
297 MB before growth. The worker enforces 128 MiB per archive and 512 MiB retained
archive budget. Thirty-minute private status uploads imply roughly 1,440 PUTs
per thirty days, before daily backups/review reports, retries and manual work.
Provider accounting and other usage still need monitoring; this is not a bill.

One 1 GiB daemon uses roughly 24 GB-hours/day even while waiting. Twenty days
use roughly 480 GB-hours across the November/December reset if started November
21; monthly memory allowance alone cannot guarantee availability. Active CPU,
DB/Redis, storage and transfer can be exhausted earlier. No upgrade is authorized.

## Software and data dependencies

Python 3.12, uv, FastAPI/Uvicorn, SQLAlchemy/Alembic, psycopg/PostgreSQL,
Redis, httpx/httpx2, BeautifulSoup/defusedxml, cryptography, Argon2/pwdlib,
Pillow, Babel/CLDR and Vercel Blob SDK; Node 24, Next.js/React/TypeScript and
Playwright. Exact versions are in uv.lock and apps/web/package-lock.json.
PostgreSQL 18 tools in Dockerfile.worker use the official PGDG repository.
Local fonts retain their OFL notices. Private files add SQL/storage/backup volume;
no external resume or recommendation AI API is called.

The Python Blob SDK lacks TTL arguments at the recorded version, so a narrow
fixed-host upload hook uses official JS SDK wire headers and validates provider
expiry. Recheck that bridge on SDK upgrades. Source-native endpoints, schema,
robots policies, rate limits and source-content permissions can change. Connector
limits are part of the [contract](CONNECTOR_CONTRACT.md), not hidden cost savings.

## Cost measurement handover

Receiving operator should record monthly dashboard usage/bills for each provider,
source/job counts, request/byte volume, collection durations, DB/file sizes,
backup size/operations and retention, then set a stop/alert threshold below caps.
Assign an owner for renewals and domain/provider dependencies. Existing hardware,
power, internet and engineering time are not zero merely because unmetered here.

References checked for the recorded baseline: [daemon limits](https://vercel.com/docs/daemons/limits),
[Blob pricing/limits](https://vercel.com/docs/vercel-blob/usage-and-pricing),
[Blob TTL](https://vercel.com/changelog/vercel-blob-now-supports-ttls-for-automatic-deletion).


## Actual provider inquiry, November 21 follow-up

Vercel confirms Hobby/active, but billing-usage retrieval for November 1–21
returned data unavailable, explicitly not zero usage. A 24-hour function CPU
query was rejected as requiring a paid Observability tier; no upgrade occurred.
A permitted short-window query measured **976 ms of request-function CPU**
from 08:43–09:09 UTC (14:13–14:39 IST). This excludes daemon CPU and is not a
monthly cost/capacity projection. DB/Redis actual costs remain unmeasured.
[Sanitized inquiry and isolation evidence](../evidence/20261121-release-gate-progress.json).

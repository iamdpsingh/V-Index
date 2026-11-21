# Developer API reference

> Documentation reconciled November 21, 2026. This is an active reference; dated evidence retains its original scope. [Documentation register](README.md) · [Complete handoff](../handoff/README.md).

The versioned contract is [openapi.json](openapi.json). The local browser uses
same-origin `/api/v1` through the web proxy. Direct local API origin is
`http://127.0.0.1:8000`. Production base URL is `https://rolewisp.vercel.app`; use the same `/api/v1` paths. Public Swagger,
ReDoc and schema-serving routes are disabled; this is not a substitute for
authentication or authorization.

| Endpoint | Access | Behavior |
| --- | --- | --- |
| `GET /health` | API liveness; internal on Vercel | Database/API only; not exposed by the public web gateway or proof of worker health |
| `GET /api/v1/jobs` | Public, rate limited when enabled | Paginated open-job search |
| `GET /api/v1/jobs/{id}` | Public, same job-rate limiter | Full job and source provenance |
| `GET /api/v1/monitoring` | Dedicated MONITOR_TOKEN, read-only/rate-limited | Aggregate worker/source/backup health; no source URLs, private records or admin rights |
| `GET /api/v1/providers` | Public | Exact inventory, point-in-time evidence and limitations |
| `GET, POST /api/v1/sources` | Operator bearer token | Inspect/register a supported source |
| `POST /api/v1/sources/{id}/refresh` | Operator bearer token | Schedule a refresh, return 202 |
| `GET /api/v1/runs` | Operator bearer token | Paginated attempts, status, count and failure |
| `GET /api/v1/operations` | Operator bearer token | Last success, initial indexing, stale/failure alerts and heartbeats |
| `POST /api/v1/security/csp-report` | Public, bounded/rate limited | Aggregate directive/disposition only; no URL/sample retention |

Search accepts `keyword`, `company`, `location`, `limit` (1 to 100), `offset`
(nonnegative), and `view` (`full` or `summary`). Filters are combined. Results
include `total`, `limit`, `offset` and `items`; ordering is deterministic by job
ID, newest first. Summary omits descriptions; fetch full detail when selected.
A changing index can change totals between page requests; pagination is not a
transactional snapshot cursor.

```sh
curl 'https://rolewisp.vercel.app/api/v1/jobs?keyword=engineer&limit=25&offset=0&view=summary'
```

Each record preserves title, employer, description, location, original listing
and application link, optional salary/employment/workplace/publication fields,
quality flags, first-seen/last-changed/last-checked timestamps and `sources[]`.
Salary has stable min/max/currency/period/text/ranges/source fields. Unknown
values stay null; source omissions are not fabricated. Date-only source dates
do not acquire an invented timezone. See [connector contract](CONNECTOR_CONTRACT.md).

Duplicates retain each source URL/application URL and source lifecycle status.
The newest changed active observation is primary. Blank optional fields can
borrow nonempty data from another active observation; `field_sources` maps
borrowed field names to their original listing URL. Closed observations do not
supply fields while any active observation remains. Source observations remain
unchanged, and the searchable canonical projection uses the same merge rule.
Distinct requisitions/locations are not merged merely for sharing a title.

Private APIs are documented in [ACCOUNTS_API.md](ACCOUNTS_API.md). They require
HttpOnly session cookies and exact mutation Origin checks. Each user accesses
only their own profile, resume, photo and postings. All API/private responses
are no-store, including errors. OAuth providers need configured applications;
adding placeholders does not activate sign-in. Paid checkout is unavailable.

Auth/signup, recommendations, uploads, public search and configured admin
operations have Redis-backed limits. 429 includes Retry-After; missing Redis
fails closed for protected rate checks. Forged forwarding headers do not change
rate buckets. The Vercel-side proxy can sign client IP/method/path/time with the
server-only PROXY_SHARED_SECRET; the backend accepts only a fresh valid HMAC.
Do not enable unrestricted Uvicorn forwarded-header trust. Hosted proxy verification is recorded in the November 21 production review;
repeat it after changes to the gateway, shared secret or hosting proxy.

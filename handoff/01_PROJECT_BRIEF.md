# 01 · Project brief

Baseline: November 21, 2026. Owner: Dhruv Pratap Singh.

## Objective and success definition

Rolewisp collects public job openings from the challenge's exact 58 applicant
tracking systems and 20 job-board platforms into a consistent, searchable,
continuously maintained index. Each opening must retain original listing and
application links. Reusable connectors, refresh safety, deduplication, search/API
and a reproducible handoff are the original acceptance requirements. Acquisition
is competitive; no acceptance, ranking or purchase is guaranteed.

The repository/folder name remains V-Index. The public brand is Rolewisp and the
tagline is “Find your next opening.” The owner operates the project and controls
release, spending and submission decisions. No receiving organization, support
team or external frontend agent is assumed to be active.

## Delivered scope

| Area | Delivered behavior | Limit |
| --- | --- | --- |
| Indexing | Reviewed source registration, native extraction, typed normalization, source links and timestamps | 71/78 platforms historically live-verified; seven unmet |
| Refresh | Persistent worker, schedules/leases, cooldowns, staged collectors, failure tracking and conservative closure | Some current sources fail; no instant upstream push or freshness SLA |
| Search | Keyword/company/location filters, pagination, summary/detail API and application links | Offset pages can change while the index changes |
| Candidate | Signup/login/logout, manual private profile, qualification categories, photo, encrypted resume storage, recommendations | Resume parsing intentionally removed; no opaque fit percentage |
| Employer | Role selection, owned drafts/edit/publish/close | Publishing requires verified email |
| Identity | Verification/recovery and Google/LinkedIn/GitHub OAuth backend | Real SMTP/OAuth credentials and delivery/login tests remain open |
| Plans | Free/Plus regional price catalogue | No checkout, paid activation or entitlement claims |
| Operations | Heartbeat, internal failure/stale monitoring, encrypted offsite backup and isolated restore drill | External notifications, key custody and deletion reconciliation need completion |
| Product | Responsive UI, read-only profile until Edit, favicon, policies and analytics choice | Legal/domain/support verification remains open |

## Last recorded production snapshot

- Demo: https://rolewisp.vercel.app.
- 7,937 open canonical jobs; 142 registered sources; 127 initial successes,
  15 without an initial success and 14 with consecutive failures. These source
  categories overlap; source count is not platform count.
- A repeat native Ashby refresh collected 78 jobs versus the initial 77 and
  increased the public index by one. This was operator-triggered, not proof of a
  completed six-hour unattended cycle.
- Latest scoped CI at the baseline passed backend, frontend and full stack.

See [evidence](07_ACCEPTANCE_AND_EVIDENCE.md); counts must be remeasured before
being advertised as current. Coverage expansion is paused by the owner, which
does not waive the missing platform or source-field requirements.

## Delivery restrictions

No paid purchases or upgrades are authorized. Do not bypass robots/access
controls, infer missing data or closes from failures, publish fake reviews or
inflate commits. The placeholder example@rolewisp.in is deliberately retained
with inbox verification open. Payments and resume parsing remain outside the
current activation scope. Preserve third-party licenses and content rights.

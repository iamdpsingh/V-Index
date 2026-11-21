# 08 · Risks, dependencies and next actions

Baseline November 21, 2026. Owners below are **proposed responsibilities**, not
claims that a receiving team or provider has accepted them. Dhruv Pratap Singh
retains product decisions until named recipients take over. No due dates or
completed actions are invented.

| ID / priority | Risk or gap | Proposed owner | Next action / exit criterion |
| --- | --- | --- | --- |
| R01 · Critical | Original 78-platform acceptance unmet at 71 | Product owner + connector engineer | When coverage work resumes, obtain allowed sources and full reusable multi-site proof for all seven; preserve required names |
| R02 · High | 15 registered sources lacked initial success at last snapshot | Backend operator | Classify current policy/429/route/schema/publisher/completeness failures, preserve cooldowns/data; prove full native success or record blocker |
| R03 · High | External probe configured; notification delivery unverified | Operations owner | GitHub independent probe/check-run alerts added; verify a real notification receiver and delivered failure/stale alerts |
| R04 · High | Keys/credential rotation not independently verified | Owner + security/operator | Confirm issuer-side rotation of exposed credentials; place resume/backup keys in independent recovery custody; prove isolated recovery |
| R05 · High | Post-snapshot deletions may reappear on restore | Privacy + database operator | Define durable deletion reconciliation and revoke sessions before cutover; record completion |
| R06 · High | Placeholder support and inactive SMTP/OAuth | Owner + backend engineer | Owner retained placeholder; when resumed, supply working inbox/sender/providers and verify email/recovery/social flows |
| R07 · High | Free-tier caps may stop service | Operations owner | Measure Vercel CPU/memory, DB/Redis/Blob budgets; set permitted load/stop plan; no paid upgrade without owner authorization |
| R08 · High | Custom domain and legal/DPDP review unresolved | Owner + appropriate reviewer | Verify domain/control and actual notice/retention/rights/processor obligations; working vercel.app demo is not domain completion |
| R09 · High | Vaya connection/submission unverified | Founder | Log in, verify founder profile, connect canonical repo/live demo, disclose gaps and submit evidence; retain confirmation |
| R10 · Medium | Upstream sources change or restrict access | Connector maintainer | Monitor failures, review native contracts and policy; never bypass restrictions or count third-party samples as complete coverage |
| R11 · Medium | Preview settings isolated; future configurations need review | Deployment owner | Production mappings removed from previews; no existing preview deployments observed. Configure dedicated preview resources and recheck future integrations |
| R12 · Medium | Broad snapshots/scale/performance limits | Technical lead | Decide measurable capacity/freshness objectives; immutable per-run observation snapshots and wider cross-host budgets are not implemented |
| R13 · Intentional deferral | Plus billing and resume parsing | Product owner | Billing stays unavailable; parser intentionally removed. Require new approved scope before activation/reintroduction |

## Platform exceptions retained

Paycom, Dover, Paycor and UltiPro have partial extraction, not complete reusable
coverage. Talenetic has one complete board and an incomplete second board with
required-field quality gaps. CareerSiteCloud and eJobBoard lack usable integrated
live coverage. Holds and missing URLs do not remove them from the required 78.

## Recommended execution order

1. Secure receiving access, recovery keys, production/preview isolation and quotas.
2. Establish external monitoring/real contact and verify actual current source health.
3. Complete operator/legal/provider gates required for the intended public release.
4. Run the acceptance walkthrough and complete authenticated Vaya submission with
   transparent limitations; the original coverage gap remains regardless of sequencing.
5. Resume remaining connector work only when the owner changes the current hold.

Do not collapse this register into a completion percentage. Effort, impact and
external dependencies differ substantially between rows.

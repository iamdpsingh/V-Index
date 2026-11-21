# 07 · Acceptance and evidence register

## What “15 of 20” meant

The prior release pass introduced twenty **internal engineering and operational
checks**. Fifteen passed and five grouped areas remained open. The denominator
was authored for that pass, not supplied by Vaya. Equal weighting cannot measure
remaining effort or acquisition readiness; one critical blocker can outweigh
many passed checks. **Do not call this “75% of the project complete.”**

The five open areas were all-source initial collection, external alerts, final
operator/privacy/provider/recovery gates, measured operating costs and Vaya
submission. Row 18 grouped several distinct tasks, so even “five open checks”
is not the number of individual tasks remaining. The detailed internal matrix
remains in [release checklist](../docs/RELEASE_CHECKLIST.md).

The original challenge has six proposed technical criteria plus submission.
Its coverage metric is separate: **71/78 = 91.0%** historically live-verified
platforms, with limits documented. No defensible overall project-completion
percentage or official Vaya score has been established.

## Requirement-to-evidence mapping

| Requirement | Evidence | Acceptance status |
| --- | --- | --- |
| All 78 platforms with reusable independent examples | providers.json, COVERAGE.md, timestamped native runs | Open: seven unmet; coverage expansion paused |
| Consistent records and provenance | Shared serializer, connector contract, record audits | Implemented; source-required-field gaps remain |
| Automatic updates and safe closure | Hosted worker/refresh proof, lifecycle tests, operations | Running; some sources fail; unattended full interval not evidenced in last review |
| Dedupe with links and distinct roles | Reviewer replay, historical real duplicate, live distinct IDs | Demonstrated with explicitly separate evidence scopes |
| Search/interface/API | Production UI, API/OpenAPI, CI/browser checks | Deployed; performance/load SLA not established |
| Complete handoff | This package and active technical documentation | Prepared; access/key transfer and recipient sign-off remain open |
| Founder/repo/demo/evidence submission | Submission draft only | Authenticated submission/review status unverified |

## Primary evidence links

| Evidence | Scope / limitation |
| --- | --- |
| [Coverage matrix](../docs/COVERAGE.md), [registry](../backend/providers.json) | Point-in-time multi-site proof; not current health of every installation |
| [Hosted controls/refresh](../evidence/20261121-hosted-release-review.json) | Actual HTTPS, temporary accounts deleted, source counts and native refresh |
| [Hosted backup](../evidence/20261121-hosted-backup.json) | Actual production snapshot, isolated restore, no live DB replacement |
| [Production UI](../evidence/20261121-production-product-review.json) | Real-data desktop/mobile search/filter/details/apply review |
| [Production profile](../evidence/20261121-production-private-profile-review.json) | Temporary synthetic account, read-only/edit/save flows |
| [Validation](../evidence/20261121-release-validation.json) | Local suite/dependency/heuristic scan scopes; not a certification |
| [Baseline CI](https://github.com/iamdpsingh/V-Index/actions/runs/44828958174) | SHA 74c0b08: 1,244 backend tests passed, one skipped; frontend and stack green |
| [Deterministic replay](../evidence/20261120-reviewer-dedup-replay.json) | Synthetic four observations to three jobs; not platform coverage |
| [Historical real duplicate](../evidence/cohort5-live-deduplication.json) | Real earlier source evidence; not a newly found hosted duplicate |
| [Record quality audit](../evidence/20261120-record-quality-local.json) | Local dated population, including documented field gaps; not hosted census |

Before technical acceptance, the receiving team should repeat critical checks
at the transferred revision/environment and record exceptions. A document,
unit test, smoke fixture or successful frontend build cannot replace missing
native runs, real delivery or authenticated challenge submission.


## Follow-up after the initial twenty-check review

The current matrix records fifteen passes, one partial area and four held/open
areas. Independent GitHub live/controlled-alert probes and preview isolation were
verified; restored authentication is revoked in the recovery target. Actual
email/SMS notification, provider activation, support, submission and remaining
source/cost/recovery-owner gates have not been relabelled as complete.
[New monitoring proof](../evidence/20261121-external-monitor-verification.json),
[recovery drill](../evidence/20261121-recovery-auth-revocation.json),
[isolation/cost review](../evidence/20261121-release-gate-progress.json).

# Technical privacy and policy review

November 21 runtime update: the owner added Vaya's shared analytics script and
approved its exact image beacon path. Earlier observations of no third-party
analytics describe the preceding review. The script sends pathname/referrer
page-view data; this integration adds no calls to its identify API. Consumer
policy copy was not revised in this narrowly scoped change, so previous
no-analytics wording requires reconciliation in the product privacy review.


November 20, 2026. Production is paused. This records application behavior and
remaining release checks; it is not a legal-compliance certification.

| Data | Purpose and access | Current retention/control |
| --- | --- | --- |
| Account email and Argon2 password hash | Login; private account only | Until account deletion; password is never returned |
| Random session-token hash | Authenticate a private session | Seven days; expiry maintenance and logout revocation |
| Verification/recovery code hash | Email ownership and recovery | Fifteen minutes; expired hashes cleared hourly |
| OAuth identity and temporary state | Optional provider sign-in | Linked identity until deletion; Redis state ten minutes |
| Manual profile, education, skills, experience, projects and links | User-controlled profile and explicit recommendations | Edit/replace/delete; no resume parsing |
| Resume and profile photo | Private storage/download | Encrypted with the server resume key; owner-only; removed on replacement/deletion |
| Employer draft/published job | Employer posting | Owner-only draft, public published job; role/ownership and verification checks |
| Public source jobs/observations | Search and source history | Can remain after closure; no candidate submissions fetched |
| Rate counters | Prevent abuse | Hashed bucket identifiers; bounded Redis windows |
| CSP classifications | Detect policy regressions | Directive/disposition counters expire after seven days; no URLs, code samples or report bodies stored |

User deletion removes live private rows through foreign-key cascades. Expiry
maintenance runs independently of long indexing fetches. The public policy
reflects these practices, including conditional 30-day encrypted backup
retention when backups are enabled. The backup timer/pruner is supplied but not
installed. Restoring an old backup can restore deleted records; reconcile
post-snapshot deletions before reopening. A durable deletion-ledger procedure
and off-site backup configuration remain production gates.

## Browser data and consent

The application uses necessary HttpOnly session and temporary OAuth-state
cookies. Mutations require the exact configured Origin. Logout revokes the
session and sends Clear-Site-Data for cookies, storage and cache. Private/API
responses and nonce-bearing HTML are no-store.

The source contains no advertising/analytics SDK or third-party embed. The
real-data local browser review recorded no third-party browser origins. Based
on this application behavior, no optional-cookie consent banner was added.
This does not establish that future hosting injects no tooling or that every
jurisdiction has identical notice/consent requirements. Recheck the deployed
network, actual analytics switches and hosting disclosures before launch.
Adding optional tracking requires a fresh assessment and meaningful choice.

Email, profile and resume data is not sent to an AI parsing service. Social
sign-in contacts a chosen provider only when configured and initiated. A job
application navigates to the original site, whose own policies apply.

## Operator, policies and assets

The supplied operator is Dhruv Pratap Singh. The supplied public address remains
example@rolewisp.in at the owner's instruction; mailbox delivery is unverified.
Privacy, cookie, terms and refund pages are linked in the footer. Rolewisp
currently takes no payments, so the refund page does not promise nonexistent
checkout or refunds. Do not activate Plus without a real provider and updated
payment/tax/refund disclosures.

The Rolewisp logo/favicon are repository SVG/code assets; no stock/AI photograph
was added. Local Albert Sans and Hanken Grotesk fonts include their OFL license
files under apps/web/public/fonts. Trademark/domain clearance and third-party
job-content permissions are separate release reviews, not established by a
successful build. Native source descriptions remain text, not executable HTML.

## India DPDP timing and review

Official notifications provide phased commencement. The November 13, 2025
[Act commencement notification](https://www.meity.gov.in/static/uploads/2025/11/c56ceae6c383460ca69577428d36828b.pdf)
sets immediate provisions, a one-year stage and an eighteen-month stage. The
[notified Rules](https://www.meity.gov.in/static/uploads/2025/11/53450e6e5dc0bfa85ebd78686cadad39.pdf)
and [official rules publication](https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa)
should be checked against the actual launch date and processing. Do not claim
that all substantive obligations were already effective, or that phased
commencement removes existing privacy/security obligations.

Before public release, review the actual operator/hosting processors, locations,
notice/consent and withdrawal, access/correction/erasure/grievance handling,
children's data and age policy, retention/backups, incident response and
cross-border processing. Current edit/delete controls are useful engineering
measures; they are not a completed legal assessment. Production and support
verification remain explicitly deferred.

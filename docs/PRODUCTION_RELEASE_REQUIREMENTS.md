# Rolewisp production release requirements

Owner instructions recorded November 7, 2026 (IST). **Coverage comes first:** finish all 78 required platform verifications before expanding the remaining product/backend work. Continue updating frontend documentation alongside connector/API changes. Batch reviewed pushes every 12 hours. This file records launch requirements, not completed verification or permission to deploy.

## Product and visual requirements

- Use clear, specific hero copy and ordinary, descriptive button labels. Keep the original Rolewisp identity and deliberate typography, layout, spacing and contrast.
- Never use purple gradients, pill-shaped buttons, emoji icons, em dashes in public copy, exaggerated scroll effects or animated cursors. No generic generated photos or copy, fake reviews, fake metrics, fake customer counts or unsupported claims.
- Keep testing, CI, acquisition progress, repository names and raw technical errors outside the public product. Preserve actual reviewer evidence separately. Use licensed images and fonts, with appropriate attribution and meaningful alt text for informative images. Decorative assets should not create screen-reader noise.
- Check desktop/mobile, no overflow, keyboard interaction, visible focus, form labels/errors, readable contrast and reduced motion. Test actual interactions and real data before describing the interface as production ready.

## Hard launch gates

- Connect a **custom domain** to the Vercel/v0 deployment and verify ownership, DNS, HTTPS, redirects, canonical origin and account/cookie behavior on that actual domain. The previous assigned vercel.app-only plan is for preview only and does not satisfy the owner's launch requirement.
- Keep deployment within the free-tier/budget constraint. No domain purchase, paid upgrade or other spending is authorized. If no eligible domain is available, keep launch blocked while coverage continues; do not substitute a preview URL and call it launched.
- Verify the original favicon loads in the production browser. Remove the optional “Made with AI” badge from the product where permitted; preserve any required attribution or truthful disclosures and treat a conflicting required badge as a launch blocker rather than hiding it improperly.
- Publish reviewed privacy and terms pages, plus the cookie policy and refund policy appropriate to the actual product. Link them from the footer and relevant forms/checkout. No invented business identity or copied generic policies.
- Confirm full coverage and the existing acquisition/reliability checks, hosted refreshes, search and source links. Frontend delivery on a branch, a local build or a screenshot does not replace release acceptance.

## Security review and release checks

- Inspect environment-variable names, scope and required configuration without printing values. Store API, billing and encryption keys in approved server-side secret storage. No secrets in public variables, client bundles, Git, logs, screenshots or responses. Check deployed files, source maps, build contexts, caches, public storage and server/debug routes. Turn off production debug behavior.
- Protect administrative routes with proper privileged authentication and authorization. Verify anonymous, ordinary-user and administrator boundaries; test ownership isolation across profiles, resumes, recommendations, billing and source management. Preserve secure session cookies, mutation protections, real logout/revocation, password hashing and appropriate recovery controls.
- Validate and sanitize form inputs and file uploads server-side; escape output, render descriptions as text and test XSS. Check request/body limits, anti-abuse and rate limits for auth, search, uploads, admin and payments. Review CORS allowlists, credential handling, Origin/CSRF checks and deployed security headers. No permissive wildcard credentials or unreviewed third-party scripts.
- Verify database network restrictions, least privilege, secret rotation, encrypted private data, backups, restore procedures and operational logs. Review ingress and egress, DNS/IP restrictions, upstream abuse and parser isolation. Check dependencies for security issues, remove unused packages, update only with reviewed lockfiles and meaningful tests.
- Scan the current repository and relevant Git history for leaked credentials, then audit the actual deployed backend, frontend bundle and data flows. Revoke/rotate any real exposed credential before further publication. Record scope, findings, fixes and remaining risks without leaking values. The earlier scoped scan and raw job-detail fix are useful evidence, not a full deployed security audit.

## Privacy, legal and accessibility review

- Inventory the actual data collected and why it is needed: account/profile, resume, recommendations, support, logs, analytics, cookies and eventual billing. Minimize fields and retention. Check access, correction/deletion, consent withdrawal and support paths. Do not collect unnecessary data for pricing or outreach.
- Verify current Indian DPDP Act and applicable rules, commencement dates and obligations using official sources at release review. Determine the real operator, processing roles, jurisdiction, notices, consent requirements, rights, retention and security obligations; obtain appropriate review before publishing legal claims. No legal-compliance assertion is granted by this checklist.
- Assess cookie consent against the actual cookies, audience and applicable law. Distinguish necessary session cookies from optional analytics/marketing. Audit third-party embeds and tracking, obtain consent where required before optional processing, and provide meaningful choice/withdrawal. Review forms for the necessary, clear notice/consent; do not bundle optional marketing with required terms.
- Use verified business/contact details, actual features and accurate pricing/refund terms. Review copyright and permissions for assets and source content. No fake reviews or unsupported employer, customer, coverage, uptime or product claims. Plus remains unavailable until real checkout, entitlements and truthful refund/tax disclosures are ready.
- Test keyboard navigation, accessible names, errors and focus, informative image alt text and sufficient contrast. Document any other material legal/security/accessibility risk and its resolution or release blocker.

All remaining checks are pending unless independently evidenced. Confirmed source coverage and the 12-hour push cadence remain separate from public launch permission.

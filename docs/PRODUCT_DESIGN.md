# Rolewisp product design standard

Current reference, November 21, 2026. The integrated UI is maintained in canonical
main. Older Antigravity assignments/holds are historical; no external agent is
assumed active. [Brand](BRANDING.md), [product scope](PRODUCT_REQUIREMENTS.md).

## Identity and composition

Build a clear job-search instrument with an editorial hierarchy, restrained
paper/ink/green/coral palette, original ribbon R and local licensed fonts.
Search/result list and inspectable detail work together on desktop; mobile uses
a focused detail with a clear return to preserved results and scroll state.
Differentiate through useful provenance, deliberate spacing and readable data,
not generic KPI cards, gratuitous gradients or decorative motion.

## Required workflows

- Search combines keyword/company/location, shareable URL filters and pagination.
  Separate employer/location/freshness clearly; missing salary/fields stay honest.
- Details show readable plain-text descriptions, original listing/application,
  source provenance and distinct check/change timestamps. Avoid nested scroll traps.
- Profiles look like profiles until Edit is selected. Keep manual fields,
  qualification categories, skills/projects/links/photo and private resume controls
  spacious and keyboard accessible. No parsing UI or fake recommendation score.
- Employer drafts and publication state reflect actual role, ownership and email
  verification; visible buttons cannot grant permissions.
- Policies/copyright remain in the shared footer on application and policy pages.
  Optional analytics is off until explicit permission and supports withdrawal.
- Operator/coverage controls show scheduling/running/failure/complete states,
  never fake progress. Do not treat a queued request as completed indexing.

## Owner constraints and acceptance

No purple gradients, pill-shaped defaults, fake reviews/metrics, vague hero copy,
emoji icons, em-dash marketing copy, AI-slop photos/copy, cursor animation or
excessive scroll effects. Use original/permitted assets, semantic landmarks,
visible labels/focus, keyboard navigation, adequate contrast and reduced motion.

Review desktop/mobile with real records, long/missing content, search/history,
profile edit/save, loading/error and private-data interactions. Synthetic browser
tests and screenshots are separate from live source evidence. [Production UI](../evidence/20261121-production-product-review.json),
[profile](../evidence/20261121-production-private-profile-review.json).
A build or attractive screenshot alone cannot establish product correctness,
78-platform acceptance, legal readiness or a secure deployment.

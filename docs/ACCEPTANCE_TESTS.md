# Acceptance checklist

- [ ] All 78 exact platforms have reusable connectors and successful live runs across multiple independent tenants (or explicitly documented blockers; blockers do not meet full coverage).
- [ ] Live smoke evidence has URL, timestamp, count, completeness, connector revision, payload digest and failure reasons.
- [ ] Full API/worker/PostgreSQL/Redis/Next.js stack starts from clone with migrations.
- [ ] Add a source, fetch genuine jobs, search keyword/company/location and paginate deterministically.
- [ ] Changed content updates; two completed misses over 24h close; reappearance reopens.
- [ ] Failed/partial/malformed/paginated-error fetches leave lifecycle unchanged.
- [ ] Cross-source duplicate merges preserve provenance; different requisitions never merge based only on title.
- [ ] Refresh schedules survive restart; concurrent workers do not ingest the same source; crashed-run recovery tested.
- [ ] SSRF, HTML/script injection, oversized payload, bad token, invalid URL and rate-limit behavior tested.
- [ ] Desktop/mobile keyboard-accessible UI and original application navigation pass browser checks.
- [ ] Handoff includes costs, dependencies, credentials inventory, backup/restore, migration/recovery procedures.

Current automated results must be read from actual test output and CI; unchecked items remain unverified.

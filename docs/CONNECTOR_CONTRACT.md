# Connector contract

`detect(url) -> (provider, slug)` is deterministic and rejects unknown hosts. `PublicConnector(provider, slug, company, client)` holds only validated tenant configuration. `fetch(cursor=0)` performs one bounded request and returns JSON. `parse(payload) -> list[JobInput]` validates every record; errors reject the enumeration. `discover() -> Enumeration` traverses every page, rejects repeated identifiers and confirms totals where provided. Normalization is performed during typed JobInput construction; original fields stay in raw.

`complete=True` is required for any reconciliation. Missing arrays, invalid required fields, exceeded response/page limits, repeated pages and total mismatches raise errors. Greenhouse and Ashby expose full arrays; Lever uses skip/limit until a short page (including a final empty page after an exact page multiple). Missing/unlisted Ashby jobs are intentionally excluded when isListed=false. Network failures do not yield empty successful batches.

Required fields: external_id, title, company, description, location, source_url, application_url. Optional fields: employment_type, remote_status, salary object, published_at. Empty descriptions from a successful API remain empty; do not invent content. Greenhouse updated_at is not publication date. Ashby publishedAt is last publication, not guaranteed original creation. Lever source timestamps remain raw unless semantically established.

Provider API references:
- https://docs.greenhouse.io/job-board.html
- https://github.com/lever/postings-api
- https://developers.ashbyhq.com/docs/public-job-posting-api

Adding a provider requires schema fixtures, completeness/pagination tests, failure tests, multiple live tenants, coverage evidence, constraints and documentation. Structured public API first, feed/JSON-LD second, HTML third, browser only with evidence of necessity. Custom-domain detection is backlog.

## Cohort 2

Detection and construction now live in `vindex.connectors.registry`; only implemented providers have factory entries. Provider codes personio-de/personio-com select the documented hosted-domain variant but count as one Personio platform. SmartRecruiters detects careers.smartrecruiters.com and jobs.smartrecruiters.com. Personio detects exactly one validated tenant label under jobs.personio.de/com. Arbitrary custom domains remain unsupported.

SmartRecruiters rejects changed totals/offsets, repeated IDs, non-public listings, mismatched detail IDs and any failed/missing detail. Descriptions combine source job-ad sections as plain text. Publication retains releasedDate, which is source release time, not necessarily original creation.

Personio reads the full default XML feed using defusedxml with DTD/entities disabled. If descriptions are empty, it tries documented en/de/fr/es/nl/it/pt feed translations; enrichment retains original XML and the chosen translation language. Translation IDs cannot expand the original snapshot. If descriptions remain missing, the run fails. createdAt is retained as source metadata without relabelling it publication date. Salary source text and multiple offices are preserved; no salary currency/unit or remote inference is invented.

All implemented connectors use bounded PublicHTTP reads with provider-controlled hosts, HTTPS, no redirects, 20 MB decompressed response limits and three-attempt retry budgets. Retry-After up to 30 seconds is honored inline; longer waits fail into durable source cooldown.

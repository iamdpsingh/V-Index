# Scoped credential and data-exposure review — November 7

This is engineering/reviewer documentation, not public product copy or a security certification. Baseline: a6b2308 and reachable refs including feat/frontend. No hosted deployment was available to audit. No credential values or private resumes are included in this report.

## Findings addressed

1. **Public job detail returned raw ingestion objects and full observation rows.** The route now uses the same allowlisted JobOut contract as public search. Source entries contain only source_id, source_url, application_url, status and last_checked_at. Raw payloads, fingerprints and internal reconciliation fields remain in the database and are not serialized publicly. A canary regression verifies exclusion from both detail and search while preserving the original stored observation. Private account/profile/resume routes retain their own authentication and ownership guards.
2. **Ignore rules covered .env but not its variants or local build caches.** Git and Docker ignore rules now exclude environment variants, local database sidecars and private key files; Docker also excludes .cache and nested host build/dependency directories. .env.example remains trackable as a placeholder-only template. This prevents accidental inclusion; it does not retroactively remove an already tracked file. Tracked sensitive filename checks found only the intended .env.example template.
3. **Compose used a fixed, public example PostgreSQL password.** Compose now requires POSTGRES_PASSWORD from private configuration. Fresh CI stacks generate an ephemeral random value without printing it. Existing persisted databases require a coordinated password rotation; changing an environment variable alone does not change their database credential. No existing volume was deleted or password silently rotated.
4. **Response hardening.** API responses now include nosniff and no-referrer headers; private and indexed API responses retain no-store. The Next.js HTML layer must also implement appropriate headers and tested CSP in Antigravity's worktree; API headers alone do not protect HTML navigation/referrers.

## Credential scan and scope

Used detect-secrets 1.5.0 on tracked files and 926 reachable text blobs across all refs, including the frontend branch. The historical pass skipped 29 binary blobs and no text blob for size. The explicit offline historical scan used --no-verify and sent no candidates to verification services. Local detailed scanner reports remain in ignored .cache; only aggregate findings are recorded in evidence/security-review-20261107.json.

The historical heuristic pass flagged 5,472 candidate findings in 195 text blobs: 5,128 hex-entropy, 313 base64-entropy, 19 Basic Auth, six secret-keyword and six AWS-key-pattern matches. These are candidate counts, not leaked credentials. Reviewed contexts were evidence payload/code hashes and revisions, package integrity checksums, public source identifiers/paths, test-only passwords/tokens, documentation examples, and font data embedded in SVGs. The six AWS-pattern matches occurred in embedded font base64, not access keys. One Basic Auth-looking public job-ad link was a malformed mailto contact link, not an authentication password. Compose's known example credential was treated as a configuration issue and removed as a default.

No confirmed live deployment credential was identified in this scope. This does not prove absence of every secret, cover unreachable Git objects, external systems, host memory, backups, deployed JavaScript bundles or all future changes. Do not claim “nothing can leak” or “production security passed.” If an actual deployed credential is identified later, revoke/rotate it at its issuer before arranging any necessary repository cleanup; do not force-rewrite history silently.

## Private-data and frontend review

Reviewed password hashing, hashed session storage, HttpOnly cookies, Origin validation, private response caching, authenticated resume/profile ownership, public projections, Docker build context and the frontend branch for browser credential storage, raw HTML rendering, logging and NEXT_PUBLIC secret use. The inspected frontend source had no localStorage/sessionStorage credential handling, dangerouslySetInnerHTML, console.log/debug or NEXT_PUBLIC usage. Automated account/resume isolation and parser tests remain the executable checks; source inspection alone is not complete browser or penetration testing.

Resume bytes and extracted text remain encrypted at rest with the private key; profile fields and filenames are not individually encrypted. No private account data is mixed into job search. Backend upload validation is not a malware scanner or a complete parser sandbox. These limitations must remain in engineering documentation and deployment decisions, rather than be hidden by polished product copy.

## Release work still required

A real HTTPS deployment and edge/request/rate policy, trusted-proxy configuration, parser process isolation, identity verification/recovery, key/backup restore drills, dependency/abuse and penetration testing, actual frontend header/bundle review, and payment/webhook/entitlement validation when billing is implemented. Neither a heuristic scan nor the 996 passing regression tests substitutes for these release gates.

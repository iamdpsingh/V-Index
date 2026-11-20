# 09 · Ownership, assets and transfer checklist

## Current ownership record

- Product/brand: Rolewisp. Engineering repository: V-Index.
- Owner and copyright attribution: **Dhruv Pratap Singh**.
- Owner-supplied public LinkedIn: https://www.linkedin.com/in/dhruvpratapsingh30/.
- Source: https://github.com/iamdpsingh/V-Index, primary branch main.
- Working demo: https://rolewisp.vercel.app. No purchased/custom domain is recorded.
- Public support: example@rolewisp.in, intentionally retained and unverified.
- No acquisition, receiving organization, account transfer or formal acceptance
  has occurred merely because this handoff exists.

## Asset inventory

| Asset | Location / treatment |
| --- | --- |
| Application and collectors | backend/, apps/web/, scripts/, app.py |
| Migrations and data model | backend/migrations/, alembic.ini; preserve migration history |
| Infrastructure | vercel.json, Dockerfile.worker, Dockerfile, Dockerfile.web, compose.yaml, ops/ |
| Dependency locks | uv.lock and apps/web/package-lock.json |
| Provider inventory and evidence | backend/providers.json, docs/COVERAGE.md, evidence/; preserve original failures/timestamps |
| API contracts | docs/openapi.json, API.md, ACCOUNTS_API.md, CONNECTOR_CONTRACT.md |
| Brand assets | RolewispLogo.tsx, app/icon.svg, docs/design/rolewisp/; concepts are not shipped UI evidence |
| Font licenses | apps/web/public/fonts/*-OFL.txt and docs/design/rolewisp/fonts/*-OFL.txt |
| Operating procedures | handoff/, docs/OPERATIONS.md, VERCEL_SERVICES.md and DEPLOYMENT.md |
| Restricted assets | Provider accounts, database contents, keys, resume files and backups: transfer privately, never commit |

The owner requested [copyright attribution](../COPYRIGHT.md). It applies to
original project materials and does not claim third-party software/font/source
job content. Existing third-party notices remain intact. Any contractual title,
licensing or acquisition terms require the actual parties' separate review;
this package is not a signed assignment or legal clearance.

## Transfer and acceptance record

Leave a row open until the named recipient can demonstrate it. Record dates,
people and evidence privately where access details are sensitive.

| Transfer item | State at preparation | Recipient / evidence to record |
| --- | --- | --- |
| Named receiving lead and operator | Open | Names, responsibilities and accepted escalation route |
| Repository access and clean clone | Open | Correct repo/main and reproducible checkout SHA |
| Local setup and CI walkthrough | Procedure prepared | Receiving-team run/build result, exact revision |
| Vercel, DB, Redis and Blob access | Open | Account invitations accepted; least privilege/target scope checked |
| Keys and credential rotation | Open | Independent custody plus successful recovery, no secret values in record |
| Production demo and source health | Baseline verified, repeat required | Receiving-team date/counts/failures and accepted exceptions |
| Backup and isolated recovery | Baseline drill passed, repeat required | Selected snapshot, count match, deletion reconciliation and key recovery |
| Privacy/support/provider/monitoring gaps | Open | Explicit acceptance or closure evidence for each risk |
| Challenge evidence and Vaya submission | Draft prepared, submission unverified | Actual authenticated connection/submission confirmation |
| Final acceptance | Not signed | Owner, receiving lead, date, revision, accepted exceptions |

## First-day knowledge-transfer agenda

1. Product/search/profile/employer walkthrough, scope and intentional deferrals.
2. One source from registration to native enumeration, transaction and search.
3. Failed/partial run, cooldown, closure safeguards and provenance/dedupe examples.
4. Private authorization/rates, policies and analytics preference behavior.
5. Deployment, migration, monitoring, backup and isolated recovery demonstration.
6. Review risks, assign real owners, agree acceptance evidence and record sign-off.

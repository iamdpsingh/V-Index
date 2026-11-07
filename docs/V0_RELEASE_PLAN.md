# One repository, v0 release target, zero-spend budget

**Latest owner release requirements (November 7):** read [PRODUCTION_RELEASE_REQUIREMENTS.md](PRODUCTION_RELEASE_REQUIREMENTS.md). Coverage remains first. Public launch now requires a verified custom domain on the free-tier plan, favicon, permitted badge removal, reviewed legal/privacy pages, accessibility and a full security review. Older preview-only vercel.app guidance does not authorize launch. No spending or automatic deployment is authorized.

Owner update, November 6, 2026: use v0 for the publishing workflow; available budget is the owner's existing $5 v0 credit and no additional spending. Do not buy a domain, upgrade a plan or provision a paid service. This changes the deployment target, not the acquisition objective or frontend ownership.

## Which folder is the project?

`/Volumes/Work/daemons-lab/p.automation/V-Index` is the canonical checkout on `main`. Its remote is https://github.com/iamdpsingh/V-Index. Deploy reviewed `main`, not an independent copy or a second repository.

The sibling `V-Index-frontend` is a Git worktree of that same repository on `feat/frontend`, required by the existing Antigravity isolation instructions. At inspection it was clean at `f0bb86e`, with unmerged frontend components and browser tests. It is a temporary editing workspace, not another product or deployment. Preserve it until its work has been reviewed, merged, and the frontend editor has stopped using it. Then remove it with Git's worktree tooling; do not delete it manually. Do not create more checkouts to publish the product.

## v0/Vercel preparation

1. Review and integrate the frontend branch into canonical `main`, retaining the backend and private-account contracts. Build and verify the integrated product before publishing.
2. Connect the existing GitHub repository to v0 rather than regenerate the app. For a Vercel frontend project, select `apps/web` as the Next.js root directory and use its committed npm lockfile. Do not copy secrets or private resume data into prompts.
3. The existing Next.js rewrites require `API_INTERNAL_URL` at build time. A hosted frontend cannot use the default `127.0.0.1:8000`: configure a reachable HTTPS backend and verify the proxy. Keep backend credentials and resume encryption keys on the backend only. Set `PUBLIC_WEB_ORIGIN` to the exact stable deployed frontend origin before enabling accounts.
4. Use the assigned `vercel.app` hostname; no purchased domain is needed. Verify API requests, cookies, mutation Origin checks, uploads/downloads, and private cache behavior on that actual hostname.
5. Resolve hosting eligibility and a genuinely zero-cost backend plan before claiming a public production release. PostgreSQL, Redis, the Python API, scheduled worker, encrypted data persistence and backups are still required. The Compose stack is not deployed merely by publishing the Next.js app.

## Verified constraints and unresolved gates

Official documentation checked November 6, 2026:

- [v0 pricing](https://v0.app/docs/pricing): credits pay for generation; the applicable free allowance/expiry depends on the account. The owner's reported $5 is not a measured infrastructure budget.
- [v0 Vercel integration](https://v0.app/docs/vercel-integration): publishing deploys through Vercel. The editor and hosting have separate plan considerations.
- [v0 domains](https://v0.app/docs/custom-domains): deployments receive a unique `vercel.app` URL; a custom domain is optional.
- [Vercel Hobby](https://vercel.com/docs/plans/hobby): free Hobby is restricted to personal, non-commercial use. Do not assume a startup built for acquisition is eligible; resolve this before choosing the public hosting plan. No paid upgrade is authorized.
- [Vercel Daemons](https://vercel.com/docs/daemons): background daemons are documented on all plans, with CPU/memory quotas. Do not claim Vercel cannot run workers; assess the actual worker, storage, quota and plan requirements. No deployment of this worker there has been tested.

No hosted deployment, account entitlement check, free backend capacity measurement or production cost verification has been completed by this document. Keep local development and CI available while these gates remain open.

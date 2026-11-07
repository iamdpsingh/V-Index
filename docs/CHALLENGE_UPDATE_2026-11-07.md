# Ready-to-post challenge update

Draft only. Not published or sent to the challenge host.

**Title:** Rolewisp: 45 platforms verified on real career sites

**Body:**

I'm building Rolewisp: a searchable job index that brings scattered company career pages and job boards into one consistent dataset, with original source and application links.

This week, I reached 45 of the challenge's 78 required platforms, with successful, non-empty live runs across at least two independent employers or boards for each verified platform. Recent additions include Taleo, Eightfold AI and Deel. The repository includes dated evidence and connector limitations, rather than counting fixtures or stubs as coverage.

The backend supports scheduled refreshes, deduplication that retains original source links and a paginated search API. Failed fetches are recorded as failures, not treated as proof that jobs have closed. The latest full suite passed 972 tests with PostgreSQL and Redis integration enabled, and GitHub CI passed backend, frontend build and Docker stack checks.

Next: complete the remaining 33 platforms, ship Rolewisp's new frontend and validate the hosted, continuously updated demo. The design handoff is ready; full coverage and production acceptance are still in progress.

**Optional image:** `docs/design/rolewisp/weekly-update.png` (1200 × 630; under 5 MB). This is a milestone graphic, not a screenshot of a deployed frontend.

**Suggested image caption:** Rolewisp engineering milestone: 45 of 78 platforms live-verified, with dated evidence and 972 passing tests.

**Evidence:** [Coverage](COVERAGE.md), [latest live pipeline](../evidence/cohort12-live-pipeline.json), [CI](https://github.com/iamdpsingh/V-Index/actions/runs/42328442107).

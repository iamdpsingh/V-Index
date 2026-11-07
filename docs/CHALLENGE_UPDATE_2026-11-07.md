# Ready-to-post challenge update

Draft only. Not published or sent to the challenge host.

**Title:** Rolewisp: 45 platforms, one searchable job index

**Body:**

I'm building Rolewisp: a searchable job index that brings scattered company career pages and job boards into one consistent dataset, with original source and application links.

This week, I reached 45 of the challenge's 78 required platforms, with successful, non-empty live runs across at least two independent employers or boards for each verified platform. Recent additions include Taleo, Eightfold AI and Deel. The repository includes dated evidence and connector limitations, rather than counting fixtures or stubs as coverage.

The backend supports scheduled refreshes, deduplication that retains original source links and a paginated search API. Failed fetches are recorded as failures, not treated as proof that jobs have closed. The focus is practical job discovery: consistent job details, original application destinations and a dataset that updates without rebuilding the frontend.

Next: complete the remaining 33 platforms, ship Rolewisp's new frontend and validate the hosted, continuously updated demo. The design handoff is ready; full coverage and production acceptance are still in progress.

**Optional image:** `docs/design/rolewisp/weekly-update.png` (1200 × 630; under 5 MB). This is a milestone graphic, not a screenshot of a deployed frontend.

**Suggested image caption:** Rolewisp brings jobs from 45 of the 78 required platforms into a searchable index with original source links.

**Evidence:** [Coverage](COVERAGE.md), [latest live pipeline](../evidence/cohort12-live-pipeline.json), [CI](https://github.com/iamdpsingh/V-Index/actions/runs/42328442107).

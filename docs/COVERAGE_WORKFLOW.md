# Coverage-first workflow — November 7

**Latest owner release requirements (November 7):** read [PRODUCTION_RELEASE_REQUIREMENTS.md](PRODUCTION_RELEASE_REQUIREMENTS.md). Coverage remains first. Public launch now requires a verified custom domain on the free-tier plan, favicon, permitted badge removal, reviewed legal/privacy pages, accessibility and a full security review. Older preview-only vercel.app guidance does not authorize launch. No spending or automatic deployment is authorized.

The owner has set the next priority: finish all 78 required live platform verifications before expanding the remaining backend/product work. Start with the largest gap: 19 job-board platforms; 14 ATS platforms also remain at the 45/78 baseline. A parser, fixture, blocked request, empty board or partial roster does not count. Preserve failed evidence and the acquisition acceptance criteria.

Work and commit locally in substantive batches. Push reviewed changes no more frequently than once per 12 hours, measured from the last successful push. The previous main release is `40d4f8d`; its push CI was created at 08:24:43 IST on November 7. The next eligible batch is at or after **20:25 IST on November 7**. Do not push early or create empty commits just to fill a window. This is a working cadence, not an unattended push automation.

Update the provider matrix, dated live evidence and connector contract as each platform qualifies. In parallel, note additive source URL/API behavior in the frontend handoff; do not change public UI copy to show development diagnostics or hardcoded counts.

Antigravity's frontend implementation is present in the existing `feat/frontend` worktree at `66baef8`, on top of the earlier account/profile/resume/recommendation work. Its commit reports 166 browser tests passed. Preserve its work; reported test output is distinct from independent verification and hosted acceptance. No automatic merge, push or deployment follows from a completed implementation report. Review integration in the proper release batch.

Existing account functionality includes signup, sign-in, session restoration, profile, resume controls, recommendations and logout. Preserve it while working on coverage; the remaining identity/recovery/privacy/hosting gates still apply. The Free/Plus price catalogue is already implemented. No payment provider is connected; do not simulate checkout or grant paid access from the browser. Real billing, remaining backend hardening and hosted validation follow the coverage milestone unless a necessary correctness/security fix arises during connector work.

Current progress update: JBoard.io passed formal runs on two independent reviewed boards (AAME 30 jobs, CIS Ontario 48), bringing the matrix to 46/78: 44 ATS and two job-board platforms. Remaining: 14 ATS and 18 job-board platforms. The earlier 45/78 figure above is the start-of-pass baseline. New commits remain local until the eligible push batch.

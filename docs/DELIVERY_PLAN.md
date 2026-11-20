# Current delivery plan

Updated November 21, 2026. Supersedes early November milestone targets and
frontend assignments preserved in Git history. The integrated product is in
canonical main; no external agent is assumed active. Production is authorized
and running. Coverage expansion is paused at 71/78, not accepted as 78/78.

## Current work sequence

1. Maintain the deployed index and private-data/security/lifecycle invariants.
   Investigate existing-source failures without dropping sources or bypassing policy.
2. Keep [handoff](../handoff/README.md), [technical references](README.md),
   [release status](RELEASE_STATUS.md) and evidence consistent with actual code.
3. Assign/complete external monitoring, key custody, target isolation, credential
   rotation, support/provider/legal/domain and cost checks in the [risk register](../handoff/08_RISKS_AND_NEXT_ACTIONS.md).
4. Complete receiving-team acceptance and authenticated Vaya connection/submission
   with disclosed coverage and data limitations. No rank/acquisition guarantee.
5. Resume remaining platform expansion only on owner direction; the original
   requirement remains open regardless of this sequencing.

Commit substantive reviewed changes, preserve remote/main and other worktrees,
never inflate counts or force-push. Owner-authorized pushes may trigger Vercel;
verify CI and the actual daemon after a release. No spend is authorized.

Use explicit delivered/verified/open/held states rather than a generic overall
completion percentage. [Challenge acceptance](ACCEPTANCE_TESTS.md) is distinct
from the authored twenty-check internal release review.

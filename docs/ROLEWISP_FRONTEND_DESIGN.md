# Rolewisp: Opening Lines

Owner instruction, November 7, 2026: **Codex designs; Antigravity implements the frontend.** Backend coverage remains Codex's responsibility. This supersedes the frontend hold and earlier Codex-implementation notes. The acquisition objective and all 78 platform requirements are unchanged.

## Open these first

- [Desktop search and reader](design/rolewisp/01-search-desktop.png)
- [Mobile search](design/rolewisp/05-search-mobile.png)
- [Mobile reader](design/rolewisp/02-reader-mobile.png)
- [Coverage](design/rolewisp/03-coverage-desktop.png)
- [Profile and resume](design/rolewisp/04-profile-desktop.png)
- [Design tokens](design/rolewisp/tokens.css)
- [Copy-ready implementation task](ANTIGRAVITY_DESIGN_TASK.md)

Editable SVGs sit beside the PNGs. These are **design concepts, not implemented frontend screenshots**. Search examples were captured from the actual local API on November 7. Private fields are empty. The description is explicitly an excerpt in the studies; production must expose the complete escaped text. Nothing in these studies counts toward live connector or browser-test evidence.

## The idea

Rolewisp turns a scattered job listing into an opening someone can inspect. Its visual signature is a custom continuous-ribbon R mark, an active entry in an index, and a wide reader with its original source attached. The user moves from opening to source without losing the search.

The public product starts with search, not a separate marketing funnel. The selected role gets more room than the results list. Brand character comes from confident type, a deep petrol masthead, cool mist surfaces and a small coral signal. Source facts remain legible and quiet. Testing/CI and acquisition progress do not appear in job-seeker screens. No globe, stock photography or decorative background is needed.

Three directions considered:

1. **Career atlas:** geographic browsing and a large navigable map. Rejected for now: location normalization and country-level counts are not reliable enough to lead the product, and the competitor already leads with a globe.
2. **Personal career magazine:** large editorial typography, warm paper, aspirational stories. Rejected: introduces content we do not have and is too close to the current cream/serif treatment.
3. **Opening Lines:** a useful search instrument with generous job reading and inspectable source records. Selected because actual data and the existing backend support its core interaction today.

The latest owner request replaces the old corner-frame logo. Use the custom ribbon R in design/rolewisp/logo-symbol.svg; do not keep the old frame or source a similar-looking stock icon. The public wordmark is Rolewisp. V-Index belongs in repository/about documentation, not as a competing logo in the primary masthead.

## What the competitor review established

Reviewed https://jobindex.space/, /jobs and /sources in a browser on November 7, including mobile and desktop layouts. The homepage combines a large headline, globe, search, category/location browsing, indexed totals and recent listings. Search exposes substantial filters, source application links and save controls. Sources shows per-platform counts and reading ages. These are observed interface features; advertised volume, platform coverage, deduplication and operational correctness were not independently audited. Do not publish a claim that Rolewisp already outranks it.

Our direction should make search-to-reading faster, show source evidence clearly and keep coverage claims inspectable. These are design objectives to validate, not measured competitive wins. Full required coverage, hosted continuous operation, data quality and handoff readiness still determine whether the product is competitive.

## Composition and typography

At 1440px the public content occupies a centered 1344px container with 48px side gutters. Cap that measure on larger screens. Use a 80px masthead, compact introduction and a 112px search strip. On the search screen the index takes approximately 38% of the workspace and the reader 62%, separated by one quiet rule. The reader's text measure is 60–72 characters, never a wall of full-width prose.

Use **Albert Sans 700** for the wordmark and display headings, **Hanken Grotesk 400/700** for controls, job titles and reading. Licensed static instances and their OFL notices are in `design/rolewisp/fonts/`; self-host only the necessary weights. No external paid font, icon set or image service is required. Font sources: https://github.com/google/fonts/tree/main/ofl/albertsans and https://github.com/google/fonts/tree/main/ofl/hankengrotesk. Preserve license notices. Use font-display: swap, metric-aware fallbacks, no synthesized weights.

Desktop type: primary heading 56–68px, selected title 40–44px, section heading 23–26px, list title 18px, prose 17px/27px, controls 16px, metadata 13–14px. Mobile: headline/title 32–36px, body 17px/27px, metadata at least 13px. Use normal sentence-case labels. No tracked-capital eyebrows or monospace decoration.

Spacing: 4, 8, 12, 16, 24, 32, 48, 64px. Radius: 4px for fields and tags, 5px for buttons/selected surface. Job entries are rows, not a stack of floating cards. Use solid surfaces and rules; no gradient, glass, glow, parallax, fake activity dots or stock logo wall. Source status always has a text label.

## Color roles

The machine-readable source is `design/rolewisp/tokens.css`. The references below explain usage, not additional independent tokens.

| Role | Reference | Use |
| --- | --- | --- |
| Field | #153C43 | Masthead and strong structural areas |
| Paper | #EDF3F4 | Workspace ground |
| Sheet | #F8FBFC | Controls and elevated functional surfaces |
| Ink | #19343B | Main reading text |
| Muted | #51666C | Secondary readable text |
| Coral | #F28B75 | Primary action and wordmark mark; always dark text |
| Selected | #DCE9EB | Current result, paired with aria-current |
| Success | #245C48 on #E1EEE6 | Explicit explicit index-status labels |
| Caution | #875320 on #F6EBDD | Unverified, stale or incomplete context |

Primary buttons use coral with ink, never white text on coral. A dedicated high-contrast focus ring appears instantly. Use focus-on-dark on the petrol header, not the dark focus color intended for light surfaces. Field borders must stay distinguishable; pale divider rules are not field boundaries. Color alone never communicates status. Do not auto-apply dark mode by inverting the palette.

## Search and reading

The three supported search inputs are keyword, company and location. Do not add working-looking salary, seniority, date or remote filters without a matching API contract. A clear icon clears only its own field; the form submits through Search/Enter. Encode filters, pagination and selected-job identity in browser history. Preserve existing back/forward and request-cancellation behavior.

Result rows lead with title, employer and source-provided location. If structured salary/workplace data exists, display it concisely; do not infer it from prose. Do not guess whether a role is eligible for a visitor's country. Default sorting must describe the API's actual ordering; no unsupported sort menu. The board shows six rows for composition, not a mandated production page size; use the existing API pagination contract and return limit.

Selecting a result updates the reader without navigating away on desktop. The entire title control is keyboard accessible. Selection does not scroll the user back to the header. The reader opens with company, title, provided location/workplace/pay and the original application action. The source record identifies each distinct source link, application destination, explicit status and available checked timestamp. Multiple observations from one source are distinct rows; source_id alone is not a React key.

The study's `Read the complete description` represents in-place expansion of the full fetched text, not a missing page or source-site redirect. Prefer the full description by default in production if the page remains readable. Always render as escaped text with preserved whitespace, never inject source HTML. The mobile concept shows an excerpt only to expose the source treatment; the shipped mobile reader must include the entire description and an ordinary path to the source record. A compact provenance anchor can jump to that section.

Use `Open application` with a short visible destination hostname. Open only validated original HTTPS links with appropriate external-link semantics. No automated submission or application progress is implied. If the source uses the posting itself as the application entry, show that same original URL.

## Freshness must mean what it says

Keep these separate: browser results refresh, source observation check, source publication date, first seen and platform evidence run. A successful API response must not turn all jobs into “just fetched.” The current API does not guarantee instantaneous upstream detection or offer SSE/WebSocket events.

Preserve the existing 60-second visible-tab polling, focus refresh, manual refresh, cancellation and background pause. Do not move the user's results or reader when polling finds changes: show a small `New results available` action. Preserve the complete last usable results on a refresh failure with an inline retry. An initial API failure has a separate error state.

Do not label an observation's last_checked value “last successfully checked” unless the backend contract guarantees it. Operator last attempt and last success are distinct; request an additive backend field if the available /runs page cannot establish the latter. An omitted job or failed fetch is never frontend proof of closure.

## Mobile and responsive behavior

- 320–767px: 20–24px gutters, stacked search inputs, one result column. Selected detail is a focused view with a clear Back action restoring query, pagination, selection and scroll position. Navigation becomes a labelled Menu control. Minimum tap area 44px.
- 768–1099px: retain the useful list and open details as a full reading view; do not squeeze two unusable columns onto a tablet.
- 1100px and above: list plus reader. Avoid nested scrolling inside the long description. A sticky application control may remain available if it does not obscure content or keyboard focus.
- Respect safe-area insets for the mobile application bar. Add bottom content padding equal to the bar height. Do not truncate job titles, foreign place names or long file names to make the mockup fit.
- At 1920px, gutters grow while the workspace stays capped. No horizontal overflow at 320px.

## Separate reviewer coverage and evidence

Load all 78 exact names from /api/v1/providers. JBoard.io and JobBoard.io stay separate. Derive current verified numerator from evidence_status, independently of implementation_status; never hardcode 45. The board's seven rows are an illustrative excerpt, not the inventory.

Use ATS/job-board group navigation, a platform-name search and explicit status labels. Opening a row exposes original example URLs, UTC timestamps formatted for the viewer, counts, failed-run explanations and connector limitations. `Live verified` means point-in-time supported-template extraction, not universal employer coverage or hosted uptime. Show the observed count and timestamp together. An unimplemented platform has an honest state, not a disabled “connected” badge.

## Profile, resumes and recommendations

Reuse the existing frontend account implementation at **3bc0a54**. That branch already contains signup/sign-in, profile, resume and recommendation components. Preserve API calls and error handling; this is a design pass and reviewed integration, not permission to discard their wiring. Review the current frontend branch status before changing it.

The profile study is an authenticated layout with an empty profile, not a populated fake account. Its top-right control is Your profile. Add all existing documented profile fields and preferences; the study is a composition, not authority to delete bio, desired locations or the remote-only setting. Use the same input, validation and save states across tabs. Dirty edits survive failures and confirmation appears only after a real response.

Resume uses the current raw-byte upload contract, not multipart. Show filename, date, download, replace and remove when a real resume exists. Failed replacement preserves the old file. Use indeterminate uploading/processing labels, not invented percentages. Clearly distinguish the **5 MiB resume limit** from the challenge update's separate **5 MB image limit**.

Recommendations show real backend reasons in plain language and original-source metadata. Never convert rank scores to fit percentages. Expose bounded/truncated ranking scope when returned. Empty preferences offer a concrete link to profile; no matches offer edit preferences or public search; disabled/private configuration and expired session have separate states. Use resume skills only according to the saved toggle. No private profile or resume belongs in shared caches or public screenshots.

Sign-in/up follow the same restrained typography and labelled form controls. Retain proper dialogs/focus handling if the current application uses dialogs; new route architecture is optional, not required by the studies. No fake password-reset or email-verification success flow. Public search never requires an account.

## Source operations

Preserve the operator workflow, but place it outside the main job-seeker navigation (footer/operator link or existing authenticated operator area). Candidate login does not grant admin access. Tokens remain in memory.

A source row shows employer, platform, configured interval, next scheduled check and explicit status. Run detail shows actual start/end, count and sanitized failure. Queued, running, success and failure are different states; queued does not mean indexed. A failed run leaves existing jobs intact. Show last success only when established by actual run data. Source submission must handle invalid/unsupported URLs, duplicates and backend unavailability. Preserve the source form's existing contract rather than adding per-platform manual settings.

## State and interaction acceptance

| Area | Required states |
| --- | --- |
| Search | Initial load, results, selected result, empty index, no matches, initial error, refresh failure with old results retained, incoming-results notice |
| Reader | Loading, detail unavailable, source open/closed/unknown, missing text/pay/date, very long content, multiple original links |
| Coverage | Loading, inventory failure, unimplemented, implemented/unverified, live verified, failed example, open evidence panel |
| Profile | Loading, empty, persisted, dirty, saving, saved, field errors, expired session, service disabled |
| Resume | Empty, selected file, uploading, processing, saved, replacement failure with prior resume retained, unsupported/oversize, remove failure |
| Recommendations | Needs preferences, matches with reasons, no matches, truncated scope, unavailable, expired session |
| Operators | Empty, source added/queued, running, success, fetch failure, retry queued, duplicate/invalid source |

Focus outline must be instantaneous; hover can change contrast over 120ms. Selection/detail transitions may use opacity or transform for up to 180ms. Reduced motion removes transition movement. No scroll hijacking, animated counters or loading placeholders pretending to be real jobs. Use accessible live regions for short status notices; do not announce the entire results list on every poll.

## Delivery order and review gate

1. Read the existing frontend branch and merge/review current main in that separate worktree. Preserve 3bc0a54 and earlier fixes. No force pushes.
2. Apply tokens, typography, mark and the **search/reader pair first**, with real local API data. Capture desktop and mobile before expanding the design.
3. Extend coverage, existing account/profile/resume/recommendation screens and source operations without dropping controls or contracts.
4. Test 320, 390, 768, 1100, 1440 and 1920px, keyboard-only operation, reduced motion, loading/error/long content and browser history. Avoid hardcoded demo data. Measure accessibility and layout; do not claim a score without running the tool.
5. Run npm ci, npm run build, npm run typecheck and the existing browser suite, including auth/data isolation and refresh failure cases. Report real failures. Deliver exact commit plus screenshot paths and reviewed merge instructions.

Design references: the owner's Hallmark link and custom-direction/font/craft guidance informed the critique. These SVG studies have not run Hallmark's production HTML/render lint or the application browser acceptance suite; do not report either as passed. Antigravity may use a library for a useful interaction after checking its license, cost and accessibility, but must not assemble unrelated visual styles from the resource list. No paid assets or plan upgrades.


## Superseding product/identity/pricing update — November 7

Consumer navigation is Find jobs, For you, Pricing and account control. Coverage diagnostics, tests/CI counts, API implementation status, acquisition progress and repository identifiers belong in reviewer/operator documentation rather than the public product header. This separation changes presentation, not the required 78-platform scope or truthful coverage evidence. Do not hide failures or mark unsupported platforms complete.

The new symbol is an independently drawn open-counter ribbon R, supplied in logo-symbol.svg and 07-logo-identity.png with scale/monochrome studies. It replaces the prior bracket mark. Use the SVG geometry, not a stock icon or a traced third-party design. Independent creation is not a guarantee of worldwide trademark exclusivity. Fonts remain licensed assets with accompanying notices.

See 06-pricing-desktop.png and PLANS_AND_PRICING.md for the Free/Plus screen and working country/currency API. India currently proposes INR 399/month; USD reference is 6/month. The 13-currency catalogue uses real minor-unit amounts and an explicit USD fallback. No payment provider exists; Plus is Coming soon, with no fake purchase/success interaction or invented paid benefits. A future paid release needs actual implemented benefits and payment/entitlement verification. Never show card forms or secret configuration in public UI.

The new public detail response is the same JobOut schema as public search. sources[] contains normalized original/application URLs and last_checked_at, never raw ingestion or observation data. The source-level checked timestamp can include a complete missing-listing check during grace; display Index status/Open in index, not Open at last check. See SECURITY_REVIEW_2026-11-07.md.

Public errors should explain the user's next action (retry, sign in, choose another file), not show stack traces, environment-variable names, parser internals, raw source payloads or request credentials. Configure HTML-layer nosniff, Referrer-Policy and a compatible tested CSP; self-host fonts, avoid third-party trackers and do not log private form data. API headers alone are not a substitute for HTML response headers. Test private-data caching and actual production bundles before release.

# Private accounts, profiles, resumes and recommendations

Implemented backend contracts; frontend integration remains with Antigravity. This feature expansion does not change the 78-platform indexing requirement. Do not call this a production account release until the remaining identity/recovery and UI gates below pass.

## Configuration

- `PUBLIC_WEB_ORIGIN`: exact browser origin, e.g. `http://127.0.0.1:3000` for local evaluation, or an HTTPS origin in production. Empty/invalid values disable private account endpoints. HTTP is accepted only for loopback development hosts.
- `ACCOUNT_REGISTRATION_ENABLED=true`: explicitly enables signup; default false. Login remains available for existing accounts when the origin is configured.
- `RESUME_ENCRYPTION_KEY`: privately generated Fernet key; required for resume encryption/decryption. Never put it in Git, browser code, screenshots or evidence. Back it up separately from the database. Losing it makes saved resumes unreadable. Key rotation requires re-encryption/migration; changing the variable alone is not rotation.
- Redis is required for credential/upload/recommendation rate budgets and the global parser lease. Failures return 503; the API does not bypass those controls.

Run `uv run alembic upgrade head` before starting the new API. The additive revision creates accounts, hashed sessions, profiles and encrypted resumes. Production/database upgrades must retain the existing index. Only the API receives the private resume key in Compose; index workers do not need it.

## Authentication

| Method/path | Body | Result |
|---|---|---|
| POST `/api/v1/auth/register` | email, password (12–128 characters) | 201 AccountOut + new session cookie |
| POST `/api/v1/auth/login` | email, password | AccountOut + rotated session cookie |
| POST `/api/v1/auth/logout` | none | 204, revoke current session and clear cookie |
| GET `/api/v1/me` | none | current account only |
| POST `/api/v1/auth/password-reset` | email | 204. Sends a code if the address is verified and mail is configured. |
| POST `/api/v1/auth/password-reset/confirm` | email, code, password | 204. Consumes the code and revokes all sessions. |
| DELETE `/api/v1/me` | password | 204, remove own live account/profile/resume/session rows |

Use JSON for credentials. Browser mutations must carry Origin equal to PUBLIC_WEB_ORIGIN; same-origin browser fetches supply this automatically. Use same-origin `/api/v1` through Next's existing rewrite. Do not expose session tokens to JavaScript or store passwords/tokens in localStorage. Production uses a Secure/HttpOnly/SameSite=Lax `__Host-vindex_session` cookie; loopback HTTP uses a separate development cookie. Sessions expire after seven days, are hashed in SQL, and are capped at ten per account. Profile identity is separate from the existing ADMIN_TOKEN operator authorization. Personal login does not grant source-management permissions.

`email_verified` is explicitly false: there is no email-ownership verification, password-reset mail or federated login yet. Email is currently a private login identifier, not a verified identity or communication destination. Signup returns 409 for duplicates, which remains an account-enumeration consideration despite credential rate limits. No mail is sent.

## Profile

GET/PUT `/api/v1/me/profile` uses `ProfileInput`/`ProfileOut` in docs/openapi.json. Fields: full_name, headline, location, bio, desired_titles, skills, preferred_locations, remote_only, use_resume_skills and experience_years. PUT replaces the profile, including defaults for omitted fields; load current values before submitting a complete form. Inputs are bounded, unknown fields are rejected, and all content is plain text. Profiles and resume metadata are private database rows; profile fields/filenames are not individually encrypted by the resume key.

## Resume

One resume per account. No account ID is accepted in these paths; ownership comes exclusively from the current session.

- PUT `/api/v1/me/resume`: raw File bytes (not multipart or base64), at most 5 MiB. Send `X-Filename: encodeURIComponent(file.name)` and `Content-Type: application/octet-stream`. Supported readable formats: PDF, DOCX and UTF-8 TXT. The extension selects the parser and content must parse successfully. Existing resumes are replaced only after successful extraction; failed uploads preserve the previous file.
- GET `/api/v1/me/resume`: metadata, detected professional keywords and updated_at; never the raw extracted text. 404 means none saved.
- GET `/api/v1/me/resume/download`: own original bytes as an attachment with no-store/nosniff headers.
- DELETE `/api/v1/me/resume`: remove own saved file/text; idempotent 204. Removing live data does not purport to erase retained database backups.

Original bytes and extracted text use authenticated Fernet encryption in SQL. The parser runs in a separate process with a ten-second wall limit, five-second CPU limit, 100,000-character output limit, 20 PDF pages, and a 20 MiB expanded-DOCX budget. Linux also enforces a 512 MiB address-space limit; macOS has CPU/wall limits but no claimed equivalent memory limit. Two parser leases are allowed globally per Redis. PDF encryption/forms/known active features, XML DTD/entities, macro/embedded binary DOCX entries and unreadable/scanned text are rejected. No OCR or external resume service is used.

Resource/process separation is not a security sandbox or malware scan. Before accepting public untrusted uploads at scale, isolate parser egress/filesystem/privileges and apply edge request/concurrency limits. The child inherits no application credentials, but still runs as the container user. Do not claim universal malware detection or guaranteed parsing of every resume layout.

## Recommendations

GET `/api/v1/me/recommendations?limit=20&offset=0` returns only currently open indexed jobs, source provenance, ordering scores and readable reasons. Explicit desired-role matches in titles weigh seven; professional skill/keyword matches weigh three. Contact URLs/emails and the ambiguous plain verb “go” are excluded from resume keyword detection. `use_resume_skills=false` disables resume-derived matching while retaining the file. Names, email, bio, age/protected traits and experience-year heuristics are not ranking inputs. No data is transmitted to external models or matching services.

The method is literal, explainable keyword matching; it does not validate qualifications, visa eligibility or hiring fit. Scores are sorting signals, not percentages. Missing preferences/recognized keywords yields needs_preferences=true and an empty list. Remote-only requires an explicit source remote label; unknown/hybrid roles are excluded. Location matching is text-based and does not establish country/work authorization.

Ranking considers at most the newest 1,000 SQL candidate jobs, then applies token checks and deterministic rank/ID sorting. total_candidates, candidates_ranked, candidate_limit and truncated disclose that scope. They are not a global match-count promise. Preserve these facts in the UI when truncated. Pagination applies to the ranked candidate set.

## Verified backend milestone

155 automated tests passed locally with PostgreSQL and Redis enabled. Executable revision 2d54f7f passed backend, frontend build and the real Docker/private web-proxy flow in GitHub Actions: https://github.com/iamdpsingh/V-Index/actions/runs/42151836186. The test account and document were ephemeral synthetic fixtures; no personal data or credentials are in the evidence artifact.

## Remaining release work

Antigravity screens and browser tests; email verification and identity recovery; trusted edge client-IP/rate policy (the current app uses the direct peer, so a shared proxy shares IP budgets); parser isolation/abuse testing; HTTPS deployment; encrypted-key/backup recovery drills; independent security review and production load validation. These are actual implementation gaps, not completed capabilities.

Resume metadata includes editable suggestions in `suggestions.education`, `suggestions.experience`, `suggestions.projects`, and `suggestions.links`. Suggested skills remain in `detected_skills`. Entries are extracted from explicitly labeled sections and may require editing. Uploading or replacing a resume leaves the saved profile alone.

Profile reads and writes support `education`, `experience`, and `projects` as arrays of up to 30 lines each. The `links` array accepts up to 12 objects with an editable `label` and an HTTPS `url`. Rolewisp does not fetch submitted links. Omitted new fields preserve saved values for older clients. Send an empty array to clear a field.

New passwords use 15 to 128 characters. Passphrases and spaces are allowed. Existing users can still sign in with their current passwords.

A signed-in user can request a verification code from Account Security. `POST /api/v1/me/email/verification` sends an eight-digit code and `POST /api/v1/me/email/verification/confirm` accepts `{"code":"12345678"}`. Codes expire after 15 minutes. Confirmation clears the stored code and updates `email_verified`. Configure SMTP over TLS with `SMTP_HOST`, `SMTP_FROM`, optional `SMTP_PORT` (465 by default), and credentials in `SMTP_USERNAME` and `SMTP_PASSWORD` if the relay requires them. Keep credentials server-side.

Profile photos use authenticated `GET`, `PUT`, and `DELETE` at `/api/v1/me/profile/photo`. Upload raw JPEG, PNG, or WebP bytes up to 2 MB. The server limits decoded dimensions, resizes to at most 384 pixels on each side, removes metadata, and encrypts the stored JPEG with the existing private-file encryption key. Reads are private and use `Cache-Control: no-store`.

Signup and login use independent Redis buckets. Signup allows 20 attempts per connecting IP per hour and five per email per hour. Login allows 60 attempts per connecting IP per minute and ten per email per minute. Both return HTTP 429 with Retry-After when the budget is exhausted. Confirm trusted proxy behavior in the hosted environment before relying on per-visitor IP limits.

Resume suggestions can also include `full_name`, `headline`, and `bio`. The parser looks for a name and professional title near the top of the document and a labeled Summary, Profile, or About Me section for the bio. The profile editor fills blank fields for review and leaves existing entries intact. No profile fields are persisted until the user saves.

## Role onboarding and job postings

Choose an account role with `PUT /api/v1/me/role` and a JSON body containing
`role` set to `candidate` or `employer`.
Employers can list and create drafts at `/api/v1/me/postings` and
edit their own postings at `PUT /api/v1/me/postings/{id}`. Post to
`/api/v1/me/postings/{id}/publish` or `/close` to change visibility.
Publishing requires a verified email. Employer submissions have their own
index identity so an employer account cannot overwrite an imported listing.

## Social sign-in setup

Set a provider's `OAUTH_*_CLIENT_ID` and `OAUTH_*_CLIENT_SECRET` on the API
service and restart. Replace `*` with `GOOGLE`, `LINKEDIN`, or `GITHUB`.
Use the public frontend origin as `PUBLIC_WEB_ORIGIN` and register
`<PUBLIC_WEB_ORIGIN>/api/v1/auth/oauth/<provider>/callback` with the provider,
using lowercase provider names. Enable Sign In with LinkedIn using OpenID
Connect on the LinkedIn app. Redis is required for temporary sign-in state.
Keep callback query strings out of proxy and application access logs.

First-time social sign-in requires `ACCOUNT_REGISTRATION_ENABLED=true`.
Accounts use the provider's stable account ID. If an email is already
registered, use the original sign-in method. Account linking is unavailable.

Before launch, test each configured social provider in a fresh browser
session. For email, send a verification code to a controlled inbox, confirm
it, then request and confirm a password reset. Check that the old password and
old session no longer work.

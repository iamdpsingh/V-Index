# Product requirements

Current scope, November 21, 2026. Original challenge requirements remain intact;
[project brief](../handoff/01_PROJECT_BRIEF.md) and [acceptance status](ACCEPTANCE_TESTS.md)
separate delivered behavior from remaining gates.

## Original challenge

- Exact 58 ATS and 20 job-board platforms, reusable across independent employers/
  boards, with real complete native indexing evidence. All 78 names stay distinct.
- Consistent title/company/description/location/source/application fields, optional
  source salary/employment/remote/publication details and tracking timestamps.
- Scheduled new/changed/removed-job handling, explicit failures, safe conservative
  closure and retained last complete observations.
- Dedupe with preserved provenance/useful data while keeping distinct roles separate.
- Working searchable UI and documented API with pagination and keyword/company/
  location filters; source/deployment/operations/cost/dependency handoff.
- Founder/startup profile, connected source/demo and coverage evidence submitted
  for technical review. Acquisition is competitive, not guaranteed.

The official page was captured November 5 with deadline November 30, 2026
23:59 UTC (December 1, 05:29 IST); see [captured deadline](../evidence/challenge-deadline.json).
This is historical capture, not a newly verified deadline or submission status;
reconfirm actual organizer terms before relying on it. Airflow was mentioned in
the invitation as experience, not established as required infrastructure.

## Owner-approved product additions

Candidate/Employer onboarding, authentication/logout, email verification/recovery,
configurable Google/LinkedIn/GitHub OAuth, manual private profiles with qualification
categories, profile photos, encrypted saved resumes, transparent recommendations
and owned employer posting workflows. Resume parsing was subsequently removed
by owner request. SMTP/OAuth live activation requires real providers and tests.

Free/Plus regional catalogue remains display-only for paid plans; checkout,
subscriptions and paid entitlements are deferred. Privacy/terms/cookie/refund
pages, default-off optional analytics, accessibility and restrained Rolewisp
branding are required. Consumer flows must not expose repo/testing/acquisition
controls or unsupported metrics. Copyright credits Dhruv Pratap Singh.

## Current execution constraint

Coverage expansion is paused at 71/78, without waiving the original requirement.
Production is running on Vercel; the current priority is truthful operation,
remaining release gates and a reproducible handoff. No spend, access-control
bypass, fabricated evidence or commit inflation is authorized. Historical
milestone dates and frontend assignments do not override this scope.

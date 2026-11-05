# Product requirements

Source: https://vayahq.com/challenge/build-a-job-board-indexer-for-10000, fetched successfully on 2026-11-05. The official page embeds entryDeadline="November 30, 2026" and endsAt="2026-11-30T23:59:00.000Z". This converts to 2026-12-01 05:29 IST. Use November 30 as the internal delivery date and reconfirm with the organizer before submission. The visible page says 26 days left. See evidence/challenge-deadline.json.

Required outcome: a continuously refreshed search index spanning exactly 58 ATS and 20 job-board platforms, reusable across multiple employers/boards per platform. User provides a supported career URL, sees genuine jobs, provenance and application links, and can search by keyword/company/location with pagination. Preserve optional source salary, employment type, remote status and publication date without inventing missing values.

Source lifecycle must distinguish complete snapshots, partial results, access restrictions and transport failures. Closure requires documented grace/reconfirmation. Same opening across sources retains provenance; distinct roles remain separate. Reviewer gets repository, working demo, live coverage checklist, sanitized fixtures, run timestamps/counts/errors, deployment/runbooks/costs and dependency inventory.

No fake demo data or counts, no superficial connector stubs, no placeholder claims. The acquisition offer and conditions require verification with the organizer; this repository does not assert guaranteed acceptance.

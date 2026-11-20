# Rolewisp project handoff

| Document control | Value |
| --- | --- |
| Package | Version 1.0, prepared November 21, 2026 (IST) |
| Product / repository | Rolewisp / V-Index |
| Owner and copyright holder | Dhruv Pratap Singh |
| Intended readers | Incoming technical lead, developer, operator and acquisition reviewer |
| Delivery state | Deployed working demo; exceptions remain open, not unconditional release acceptance |
| Evidence baseline | Executable revision `74c0b08`; [successful CI](https://github.com/iamdpsingh/V-Index/actions/runs/44828958174) |
| Demo / source | https://rolewisp.vercel.app / https://github.com/iamdpsingh/V-Index |
| Receiving owner / acceptance date | Not yet assigned / not yet signed off |

This package explains what is delivered, how to operate and transfer it, what
has been verified and what remains. It contains no credentials, personal resumes
or account records. Measurements are dated observations, not a live dashboard.

## Reading order

| Document | Purpose |
| --- | --- |
| [01 Project brief](01_PROJECT_BRIEF.md) | Objective, scope, stakeholders and delivered features |
| [02 System architecture](02_SYSTEM_ARCHITECTURE.md) | Components, data flows, storage and design constraints |
| [03 Development and release](03_DEVELOPMENT_AND_RELEASE.md) | Setup, tests, migrations, deployment and rollback |
| [04 Configuration and access](04_CONFIGURATION_AND_ACCESS.md) | Variable inventory and secure service/account transfer |
| [05 Operations and recovery](05_OPERATIONS_AND_RECOVERY.md) | Daily checks, incident response, backups and restore |
| [06 Security and privacy](06_SECURITY_AND_PRIVACY.md) | Controls, data lifecycle and remaining security/privacy gates |
| [07 Acceptance and evidence](07_ACCEPTANCE_AND_EVIDENCE.md) | Requirement-to-evidence mapping and checklist explanation |
| [08 Risks and next actions](08_RISKS_AND_NEXT_ACTIONS.md) | Priorities, owners and exit criteria |
| [09 Ownership and transfer](09_OWNERSHIP_AND_TRANSFER.md) | Asset inventory, knowledge transfer and sign-off record |

## Source of truth and document precedence

1. Runtime configuration and reviewed code describe executable behavior.
2. [Coverage registry](../backend/providers.json) plus [coverage evidence](../docs/COVERAGE.md)
   define platform claims. Tests and fixtures never count as live platform coverage.
3. [Release status](../docs/RELEASE_STATUS.md) and timestamped production evidence
   describe the last checked deployment, not guaranteed current health.
4. This handoff and active [technical references](../docs/README.md) explain operation.
5. Dated historical briefs/reviews remain reference material, not current assignments.

Update affected docs with every change to public APIs, infrastructure, keys,
retention, source support or release status. Preserve original evidence and
historical failures. The receiving team should record its new code revision,
review date and actual acceptance results before signing off.

Copyright © 2026 Dhruv Pratap Singh. See [copyright and third-party notices](../COPYRIGHT.md).

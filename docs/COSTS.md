# Costs and dependencies

No paid extraction service is required by the initial connectors. Dependencies: public Greenhouse/Lever/Ashby APIs; Python/PyPI, Node/npm, PostgreSQL and Redis. No API keys needed for these public listing endpoints. Availability and terms can change. No authenticated extraction or anti-bot service is used.

Planning assumptions, not vendor quotes: one small host for API/worker/web plus PostgreSQL/Redis; 20-50 USD/month host budget, 5-15 USD/month backups/storage, domain extra. Validate current vendor prices before purchase. Browser-rendered enterprise connectors could change compute costs substantially and are not included. No production benchmark or measured monthly cost exists yet.

Record requests, bytes, index size, source count, refresh cadence and runtime before selecting infrastructure. At 1,000 sources refreshed every six hours, minimum base enumerations are 4,000/day; pagination/details add requests. Limit per-provider traffic and cache based on permitted semantics. Staff time and access/licensing constraints are the main 78-provider risks.

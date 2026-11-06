# Enterprise ATS investigation — 2026-11-05

These are research findings, not verified connectors. None of these platforms is added to the live coverage count. No authentication, access-control or anti-bot bypass was attempted.

| Platform | Evidence examined | Finding | Next implementation step |
|---|---|---|---|
| Workday | NVIDIA public board, robots.txt, siteMap.xml and one read-only career-search POST; evidence/workday-research.json | Hosted board and career search returned HTTP 200. The first search response reported total=2000 and returned 20 postings. The examined sitemap returned 100 URLs. These observations do not prove full enumeration or a provider-wide cap. | Validate complete pagination and detail extraction across two tenants, including large-board enumeration limits, total drift and duplicate pages. Add strict tenant/data-center/site validation before production fetching. |
| Oracle Recruiting | Official recruitingCEJobRequisitions REST reference | Oracle labels this resource category internal-use. Its existence is not evidence of a supported public integration. | Investigate public career-site pages/feeds and their access constraints. Keep tenant/site identity explicit; do not call private integration endpoints or count documentation as live evidence. |
| SAP SuccessFactors | Official career-portal and recruiting-system integration documentation | External career microsites exist; the documented integration flow uses authenticated roles/OAuth. This does not establish a freely available generic jobs API. | Identify two public external sites and permissible structured HTML/feed paths; distinguish Recruiting Management and Career Site Builder variants. |
| iCIMS | Official Job Portal API documentation | Search examples use Basic authorization and detail extraction delegates to the Profiles API. No customer credentials have been supplied. | Investigate public hosted portal search/sitemaps/structured job pages with robots handling; verify pagination and detail completeness on two tenants. |
| Taleo | Oracle career-section configuration and implementation guides | Career sections support public search, with customer-specific section names and optional Sourcing redirects. | Identify two live employer sections and inspect their public structured data/feed options. Treat Taleo and Oracle Recruiting as separate provider entries. |

## Primary references

- Workday observed board: https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite
- Oracle resource scope: https://docs.oracle.com/en/cloud/saas/human-resources/farws/api-recruiting-ce-job-requisitions.html
- SAP external portals: https://help.sap.com/docs/SAP_SUCCESSFACTORS_RECRUITING/8477193265ea4172a1dda118505ca631/4a2d9268d4c145e18768a351551b12cb.html
- SAP integration authentication: https://help.sap.com/docs/CPS/76dfec72e18e4f5aa9e56a2fb4d39944/b71bdfc7a4ae461eb3911348ea10d627.html
- iCIMS Job Portal API: https://developer-community.icims.com/applications/applicant-tracking/job-portal?sort_by=changed
- Taleo sections: https://docs.oracle.com/en/cloud/saas/taleo-enterprise/20a/otrcg/central-configuration.html
- Taleo implementation: https://docs.oracle.com/en/cloud/saas/taleo-enterprise/24b/otcug/implementing-career-section.pdf

## Cohort selected for implementation

SmartRecruiters documents a public Posting API with list pagination and separate detail requests. Personio documents opt-in XML career feeds. These are implemented as reusable tenant connectors while enterprise enumeration research continues. SmartRecruiters details must all succeed, and list offset/total/IDs must remain consistent. An explicitly empty source role-description field is preserved and flagged; it is distinct from a missing/malformed detail response. Personio's default-language feed can omit descriptions, so missing descriptions are enriched from supported translated feeds without replacing the default ID universe. Remaining gaps fail the enumeration rather than silently producing a complete snapshot.

References: https://developers.smartrecruiters.com/docs/endpoints and https://developer.personio.de/v1.0/reference/get_xml and https://support.personio.de/hc/en-us/articles/207576365-Integrate-jobs-from-Personio-into-your-website-via-XML

## 2026-11-06 Workday update

A reusable bounded hosted-site connector has been implemented. IMF and Gates public searches and detail records were accessible with their robots directives. IMF returned the first page again for offsets 14, 20 and 40 despite advertising 14 jobs; the raw path/count comparisons are in evidence/workday-imf-boundary.json. NVIDIA returned a page at offset 2000 while reporting total=2000, so that reported boundary is not accepted as proof of complete enumeration. The connector rejects reported totals at that ceiling and boards above its 400-detail budget. Formal provider evidence status is in COVERAGE.md; these implementation/research notes alone do not establish live coverage.

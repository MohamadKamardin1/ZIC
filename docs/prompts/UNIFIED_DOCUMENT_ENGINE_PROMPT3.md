# Unified Document Engine Series

This checkpoint continues the unified platform print-engine series after `UNIFIED_DOCUMENT_ENGINE_PROMPT2.md`. It executes only the complete QUOTATION document-template prompt.

## [x] Prompt 3 — Implement complete quotation printout template

- [x] Build a complete QUOTATION context with company branding, repository logo, quotation metadata, expiry, agent/intermediary and branch labels, prospect details, and draft watermark state.
- [x] Render per-plan sections with codes, names, descriptions, plan-type badges, policy and payment terms, quote basis, sums assured, maturity and bonus values, and Joint Life/Mortgage/PA/WP indicators.
- [x] Render optional member coverage, riders and benefits, investment-fund allocations, financial totals, premium amounts in figures and words, policy-year projections, and installment payout schedules.
- [x] Render validity/disclaimer terms, terms reference, non-offer notice, customer/agent/company signature blocks, and generated-by/template-version/page-number footer metadata.
- [x] Enforce the registered template variable schema and make optional sections collapse without blank output gaps.
- [x] Make tables multi-page safe with repeating table headers and no row splitting where practical.
- [x] Add pypdf regression coverage for required block text, PDF page count, repository logo image resources, multi-plan pagination/header repetition, draft watermark, and schema validation.
- [x] Preserve legacy OL quotation print labels while delegating all HTML/PDF generation to the unified documents engine.

## Verification

- Unified document tests: 10 passed.
- Existing OL quotation print/document regressions: 10 passed.
- Full backend suite: 695 passed, 12 existing non-blocking warnings.
- Django system checks: passed with no issues.
- Migration drift check: no changes detected.

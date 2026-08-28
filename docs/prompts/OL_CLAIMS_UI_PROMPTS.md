# OL CLAIMS UI — FULL SERIES (10 Prompts)

## [ ] Prompt 1 — Save Series File + Foundation + Contract-First API Layer

You are a senior frontend engineer for the ZIC Life Insurance Platform. The OL Claims backend is complete. Build the Claims UI. The user pasted the FULL 10-prompt series at once.

META-INSTRUCTION (HIGHEST PRIORITY):
1. Before coding, create docs/prompts/OL_CLAIMS_UI_PROMPTS.md and save ALL 10 prompts EXACTLY as provided, each with a checkbox "[ ] Prompt N — title".
2. Commit and push that file immediately.
3. Execute ONLY Prompt 1 now; when green, tick its checkbox, commit, then proceed to Prompt 2. Never merge or skip prompts.

MANDATORY RULES:
- Use the established design system, DataTable, SmartSelect, ErrorCoach, and StatusBadge kits.
- Names never UUIDs; every failure teaches the user what happened and how to resolve it.
- Commit and push at the end of each prompt.

SCOPE:
1. Register route Ordinary Life > Claims gated by `ol_claims.view`.
2. Implement API hooks (TanStack Query) for the full Claims contract:
   - list, kpis, options
   - register_claim, upload_document, list_documents
   - medical_require, medical_result, assess_claim
   - add_file_note, list_notes
   - financial_summary, raise_requisition, settle_claim
   - print_discharge_voucher
   - detail (with nested tabs: overview, documents, assessment, financials, requisition, audit)
3. Build Claim-specific primitives:
   - ClaimStatusBadge (REGISTERED, PENDING_MEDICAL, ASSESSED, REQUISITIONED, APPROVED, SETTLED, REJECTED, CANCELLED)
   - ClaimantBadge (POLICYHOLDER, INSURED, DEPENDENT)
   - MoneyCell (formats calculated, approved, net payout)
   - ProgressionGuardBanner (blocks actions when mandatory steps are incomplete)
4. Implement MSW mock handlers mirroring the backend contract.
5. Unit tests for primitives rendering and ErrorCoach integration.

GIT:
- commit: "feat(web): claims UI foundation and contract-first API layer"
- push; if blocked create feature/web-claims-foundation and push; tick checkbox

FINAL OUTPUT: hooks, primitives, tests, commit hash, pushed branch.

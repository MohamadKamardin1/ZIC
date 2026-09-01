# GC PARAMETERS — PROMPT SERIES (6 prompts, backend)

- [x] Prompt 1 — Save Series File + GC Parameters Foundation & Scheme Models
- [x] Prompt 2 — GC Product Setup & Rider Setup Models
- [x] Prompt 3 — GC Medical U/W & Claim Setup Models
- [ ] Prompt 4 — APIs, Options Endpoints & Validation Services
- [ ] Prompt 5 — Full Seed Data & Documentation
- [ ] Prompt 6 — Backend Integration & Release Verification

> **Note on fidelity:** the full 6-prompt series was pasted at once. Each prompt is
> saved `EXACTLY as provided` below, then executed strictly one at a time, ticking
> each checkbox after its commit and push. Prompt 1 is executed first.

---

## Prompt 1/6 — Save Series File + GC Parameters Foundation & Scheme Models

```text
You are a senior Django insurance platform engineer. Build the ZIC Group Credit Parameters backend. The user pasted the FULL series of prompts for this module at once.

META-INSTRUCTION (HIGHEST PRIORITY):
1. Before coding, create docs/prompts/GC_PARAMETERS_PROMPTS.md and save ALL prompts in this series EXACTLY as provided, each with a checkbox "[ ] Prompt N — title".
2. Commit and push that file immediately.
3. Execute ONLY Prompt 1 now; when green, tick its checkbox, commit, then proceed to Prompt 2. Never merge or skip prompts.

MANDATORY RULES:
- No blocking questions; make senior insurance assumptions and document them.
- Everything must be parameterized.
- Every material change must be audited with actor, before/after, reason, source channel.
- Commit and push at the end of each prompt.

OBJECTIVE:
Create the GC Parameters bounded context and the "Scheme Setup" models.

BUSINESS CONTEXT:
Group Credit schemes are linked to Banks or Corporate Partners. Parameters must define the types of schemes (e.g., Mortgage, Personal Loan, Corporate), their rates (Unit/Flat), statuses, and health questionnaires.

SCOPE:
1. Produce docs/GC_PARAMETERS_DESIGN.md covering:
   - The 5 categories: Scheme Setup, Product Setup, Rider Setup, Medical U/W, Claim Setup.
   - The relationship to the Partner Model (Banks/Employers).
   - Integration map: Quotations, Schemes, Members, Loans.
2. Create Django app `gc_parameters`.
3. Implement **Scheme Setup** models:
   - GCSchemeType: code, name, description, partner_type_restriction (e.g., BANK only), is_active.
   - GCSchemePremiumRate: scheme_type, product_ref, rate_type (UNIT/FLAT), rate_value, currency, effective_from, effective_to.
   - GCSchemeMemberStatus: code, name, is_active, is_terminal, allows_claims, display_order.
   - GCSchemeStatus: code, name, is_active, is_terminal, display_order.
   - GCSchemeRenewalStatus: code, name, is_active, display_order.
   - GCHealthQuestion: code, question_text, answer_type (BOOLEAN, TEXT, CHOICE), required, category.
   - GCHealthQuestionnaire: code, name, scheme_type_ref, version, items (JSON or M2M to questions), threshold_trigger_amount, effective_from.
4. Register permissions: gc_parameters.view, manage, configure.
5. Register permission codes for specific entities (e.g., gc_parameters.scheme_types.create).
6. Add audit logging for all creates/updates.
7. Add admin table-first registration.
8. Seed realistic data (e.g., "Mortgage Protection", "Bank Loan", "Standard Rates", "Active", "Pending Medical").

TESTS:
- model creation and relationships
- status enum validation
- audit logging
- permissions registered

GIT:
- commit: "feat(gc-parameters): save prompt series and create GC foundation & scheme models"
- push; if blocked create feature/gc-parameters-foundation and push; tick checkbox

FINAL OUTPUT: design summary, models, permissions, seeds, tests, commit hash, pushed branch.
```

---

## Prompt 2/6 — GC Product Setup & Rider Setup Models

```text
You are a senior Django insurance engineer. Continue the ZIC GC Parameters backend. Execute ONLY Prompt 2 from the saved series file.

MANDATORY RULES:
- No blocking questions; document assumptions.
- Commit and push; tick checkbox.

OBJECTIVE:
Implement "GC Product Setup" and "GC Rider Setup" models.

SCOPE:
1. **GC Product Setup** models:
   - GCSubProduct: code, name, parent_product_ref (if hierarchy exists), description, is_active.
   - GCProduct: code, name, scheme_type_ref (FK to GCSchemeType), insurance_class, currency, min_entry_age, max_entry_age, min_loan_term, max_loan_term, free_cover_limit, premium_basis (SINGLE/LEVEL), requires_medical, is_active.
   - Product must support "Sub-products" (e.g., a product can have variants).
2. **GC Rider Setup** models:
   - GCRider: code, name, rider_category (e.g., DISABILITY, ACCIDENTAL_DEATH), benefit_type (FIXED, PERCENTAGE), requires_underwriting, is_active.
   - GCRiderRate: rider_ref, product_ref, rate_value, rate_type (PERCENTAGE, FIXED), currency, effective_from, effective_to, is_active.
3. Validation:
   - Product must belong to a valid Scheme Type.
   - Rider Rates must be consistent (positive values).
4. Update admin views to show hierarchical relationships (Product -> Scheme Type).
5. Add structured error registry: SCHEME_NOT_FOUND, PRODUCT_INVALID_SCHEME, RATE_MISMATCH.

TESTS:
- Product creation links to Scheme Type
- Rider creation links to Product
- Validation enforces valid relationships
- audit rows created

GIT:
- commit: "feat(gc-parameters): implement product and rider setup models"
- push; tick checkbox

FINAL OUTPUT: models, validation rules, tests, commit hash, pushed branch.
```

---

## Prompt 3/6 — GC Medical U/W & Claim Setup Models

```text
You are a senior Django insurance engineer. Continue the ZIC GC Parameters backend. Execute ONLY Prompt 3 from the saved series file.

MANDATORY RULES:
- No blocking questions; document assumptions.
- Commit and push; tick checkbox.

OBJECTIVE:
Implement "GC Medical U/W" and "GC Claim Setup" models.

SCOPE:
1. **GC Medical U/W** models:
   - GCMedicalCode: code, name, description, category (e.g., ICD_10), is_active.
   - GCMedicalLimit: scheme_type_ref, medical_code_ref, limit_amount, age_min, age_max, is_active.
   - GCUnderwritingDecision: code, name, description, requires_review, is_active, display_order (e.g., STANDARD, LOADING, DECLINE).
   - GCPersonalHabit: code, name, habit_category (SMOKING, ALCOHOL, OCCUPATION), underwriting_impact, is_active.
   - GCMedicalHistory: code, name, condition_category, severity, waiting_period_days, exclusion_flag, is_active.
   - GCMedicalFacility: partner_ref (linked to Partner model), facility_code, name, type, approval_status, is_active.
   - GCMedicalPractitioner: partner_ref, practitioner_code, first_name, last_name, specialty, license_number, facility_ref, approval_status, is_active.
2. **GC Claim Setup** models:
   - GCClaimType: code, name, category (DEATH, CRITICAL_ILLNESS, PERMANENT_DISABILITY, TEMPORARY_DISABILITY), calculation_basis, requires_document_check, is_active.
   - GCClaimReason: code, name, claim_type_ref, category, description, is_active.
   - GCClaimStatus: code, name, is_terminal, display_order, is_active.
   - GCDischargeType: code, name, template_code, variables, is_active.
   - GCCorrespondentType: code, name, category, communication_channel, purpose, is_active.
3. Ensure all Medical/Claim models link to the Scheme context where necessary (e.g., Medical Limits).

TESTS:
- Medical codes and limits CRUD
- Underwriting decisions CRUD
- Claim types and reasons CRUD
- Partner linkage for Facilities/Practitioners
- audit rows created

GIT:
- commit: "feat(gc-parameters): implement medical UW and claim setup models"
- push; tick checkbox

FINAL OUTPUT: models, relationships, tests, commit hash, pushed branch.
```

---

## Prompt 4/6 — APIs, Options Endpoints & Validation Services

```text
You are a senior Django API engineer. Continue the ZIC GC Parameters backend. Execute ONLY Prompt 4 from the saved series file.

MANDATORY RULES:
- Table-first API responses.
- Names never UUIDs.
- Commit and push; tick checkbox.

OBJECTIVE:
Implement APIs and Options Endpoints for the GC Parameters.

SCOPE:
1. Implement List/Detail APIs for all parameter entities:
   - GET /api/v1/gc/parameters/scheme-types/
   - GET /api/v1/gc/parameters/scheme-rates/
   - GET /api/v1/gc/parameters/products/
   - GET /api/v1/gc/parameters/riders/
   - GET /api/v1/gc/parameters/medical/...
   - GET /api/v1/gc/parameters/claims/...
   - Include pagination, filtering, and search for all.
2. Implement Options Endpoints (for frontend SmartSelects):
   - GET /api/v1/gc/options/scheme-types/
   - GET /api/v1/gc/options/products/?scheme_type=
   - GET /api/v1/gc/options/questionnaires/
   - GET /api/v1/gc/options/claim-types/
   - Return standard payload: { value, label, meta }.
3. Validation Services:
   - SchemeRateValidator: Checks effective date overlaps.
   - ProductValidator: Checks age limits and free cover limits.
   - ClaimTypeValidator: Checks for duplicate active types.
4. Update all serializers to use `display_name` fields instead of UUIDs.
5. Add CSV export capability for all list endpoints.

TESTS:
- APIs return correct paginated data
- Options endpoints return labeled data
- Validation services catch errors
- CSV export works

GIT:
- commit: "feat(gc-parameters): implement APIs and options endpoints"
- push; tick checkbox

FINAL OUTPUT: endpoints, serializers, validation services, tests, commit hash, pushed branch.
```

---

## Prompt 5/6 — Full Seed Data & Documentation

```text
You are a senior Django engineer. Continue the ZIC GC Parameters backend. Execute ONLY Prompt 5 from the saved series file.

MANDATORY RULES:
- No blocking questions; document assumptions.
- Commit and push; tick checkbox.

OBJECTIVE:
Seed realistic data and document the GC Parameters Engine.

SCOPE:
1. Seed Data for all categories:
   - Scheme Types: "Mortgage Protection", "Bank Loan", "Corporate Salary", "Hire Purchase".
   - Rates: Standard Unit Rates for various terms (1-30 years).
   - Products: "Credit Life Plan A", "Credit Life Plan B" linked to schemes.
   - Riders: "Accidental Death Benefit", "Permanent Disability".
   - Medical: Codes (Hypertension, Diabetes), Facilities (General Hospital), Practitioners.
   - Claims: Types (Death, PTD), Reasons (Accident, Illness).
2. Documentation:
   - docs/GC_PARAMETERS_API.md
   - docs/GC_PARAMETERS_DATA_DICTIONARY.md
   - docs/GC_PARAMETERS_SEEDING.md
3. Ensure the seed data supports the "Group Credit" workflow (e.g., has products with loan term limits).

TESTS:
- Seed script runs successfully without errors
- Data exists in database after seed
- API returns seeded data

GIT:
- commit: "feat(gc-parameters): seed data and documentation"
- push; tick checkbox

FINAL OUTPUT: seed script, documentation, tests, commit hash, pushed branch.
```

---

## Prompt 6/6 — Backend Integration & Release Verification

```text
You are a senior Django QA engineer. Complete the ZIC GC Parameters backend. Execute ONLY Prompt 6.

MANDATORY RULES:
- Verify all modules work together.
- Commit and push; tick final checkbox; all 6 checkboxes ticked at the end.

OBJECTIVE:
Final verification of the GC Parameters Backend.

SCOPE:
1. Integration Tests:
   - Create Scheme Type -> Create Product linked to Scheme -> Create Rider linked to Product.
   - Verify all links exist and are queryable.
2. Permission Tests:
   - Verify unauthorized user cannot access parameter APIs.
   - Verify authorized user can access all APIs.
3. Audit Tests:
   - Create a parameter change.
   - Verify Audit Log captures actor, before, after, reason.
4. Final Cleanup:
   - Ensure no TODOs.
   - Ensure all models have `created_at`, `updated_at`, `created_by`, `updated_by`.
   - Run full lint/typecheck/test suite.

GIT:
- commit: "feat(gc-parameters): backend integration tests and release verification"
- push; if blocked create feature/gc-parameters-backend-complete and push
- tag v2.0.0-gc-parameters-backend if tagging convention exists

FINAL OUTPUT:
Return the FULL GC Parameters backend summary:
- models implemented
- endpoints implemented
- seeds added
- tests passed
- all 6 checkboxes ticked
- commit hash/tag
- pushed branch
- next recommended module: GC Parameters Frontend.
```

---

## If manus gives partial work

```text
Follow the saved series file strictly: execute only the current prompt, complete it fully with production-quality code, migrations, APIs, validation, tests, documentation, audit logging, and GitHub push, then tick its checkbox before continuing. Do not merge prompts, do not skip tests, and do not leave placeholders. If anything is ambiguous, make senior-level insurance and engineering assumptions, document them, and continue.
```

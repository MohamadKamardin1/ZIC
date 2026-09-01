# GC Parameters — Design

The **GC Parameters** bounded context parameterizes the ZIC Group Credit module
(scheme-based, loan-driven credit life). It lives in the `group_credit` Django
app as **Layer 1 — Setup & Parameters**, extending the lookup models that were
already load-bearing for `GCQuotation`, `GCScheme`, `GCSchemeMember`, and
`GCClaim`. This document covers the five parameter categories, the relationship
to the Partner model, and how the parameters integrate with the rest of Group
Credit.

> **Note on scope:** the original prompt asked to "Create Django app
> `gc_parameters`". Because the `group_credit` app already owned the equivalent
> lookup models and every Group Credit runtime model FK'd into them, the agreed
> approach is to **extend `group_credit` in place** — the GC Parameters bounded
> context is realized as `group_credit`'s Layer 1. The permission namespace used
> by the context is `gc_parameters.*` regardless of the hosting app label.

## 1. The five parameter categories

| # | Category | Owner models | Purpose |
|---|----------|--------------|---------|
| 1 | **Scheme Setup** | `GCSchemeType`, `GCSchemePremiumRate`, `GCSchemeStatus`, `GCSchemeMemberStatus`, `GCSchemeRenewalStatus`, `GCHealthQuestion`, `GCHealthQuestionnaire` | Defines the types of schemes (Mortgage, Personal Loan, Corporate), their unit/flat premium rates, lifecycle statuses, and the health questionnaire used for credit-life underwriting. |
| 2 | **Product Setup** | `GCProduct`, `GCSubProduct` | Products (Credit Life Plan A/B) scoped to a scheme type with entry ages, loan-term limits, free-cover limits, and premium basis. |
| 3 | **Rider Setup** | `GCRider`, `GCRiderRate` | Riders (Accidental Death, Permanent Disability) with benefit types and product-scoped rates. |
| 4 | **Medical U/W** | `GCMedicalCode`, `GCMedicalLimit`, `GCUnderwritingDecision`, `GCPersonalHabit`, `GCMedicalHistory`, `GCMedicalFacility`, `GCMedicalPractitioner` | Medical evidence codes, scheme-scoped limits, underwriting decisions, personal habits, condition history, and approved facilities/practitioners. |
| 5 | **Claim Setup** | `GCClaimType`, `GCClaimReason`, `GCClaimStatus`, `GCDischargeType`, `GCCorrespondentType` | Claim categories (Death, PTD, CI, Temporary Disability), reasons, statuses, discharge templates, and correspondent channels. |

## 2. Relationship to the Partner model

Group Credit schemes are written for **Banks** and **Corporate Employers**
(`apps/partners.Partner`). The relationship is expressed at two levels:

- **`GCSchemeType.partner_type_restriction`** — restricts a scheme type to a
  partner category (e.g. `BANK` only for `MORTGAGE_PROTECTION`,
  `CORPORATE` for `CORPORATE_SALARY`). Valid codes mirror the Partner
  categories (`BANK`, `CORPORATE`, both, or any).
- **Runtime linkage** — `GCQuotation.partner` and `GCScheme.partner` (both
  `PROTECT` FKs) bind a quotation/scheme to the actual partner. The parameter
  layer constrains what kind of partner may use a scheme type; the runtime
  layer records which partner did.

Medical facilities and practitioners optionally link back to a Partner via
`partner_ref`, so a bank's preferred hospital network can be parameterized.

## 3. Scheme Setup models (Prompt 1)

All parameter models inherit `GCParameterAuditMixin`, giving `created_by` /
`updated_by` audit fields and `save() → full_clean()` validation. The audit
receivers (`apps/group_credit/audit_receivers.py`) write an `AuditLog` row on
every create and update with before/after state and a reason.

| Model | Key fields | Notes |
|-------|-----------|-------|
| `GCSchemeType` | `code`, `name`, `description`, `partner_type_restriction`, `is_active` | `partner_type_restriction` ∈ {BANK, CORPORATE, BANK_AND_CORPORATE, ANY}. |
| `GCSchemePremiumRate` | `name`, `scheme_type`, `product_ref`, `rate_type` (UNIT/FLAT/BASE/LOADING/DISCOUNT), `rate_value`, `currency`, `effective_from`, `effective_to`, `is_active` | `rate_value` must be non-negative; effective window must be valid. Legacy `rate_per_mille`/`flat_rate`/`effective_date`/`expiry_date` retained for compatibility. |
| `GCSchemeStatus` | `code`, `name`, `display_order`, `is_terminal`, `is_active` | `display_order` drives ordering; legacy `sort_order` retained. |
| `GCSchemeMemberStatus` | `code`, `name`, `display_order`, `is_terminal`, `allows_claims`, `is_active` | `allows_claims` gates claim eligibility (e.g. `DECEASED` allows claims, `PENDING_MEDICAL` does not). |
| `GCSchemeRenewalStatus` | `code`, `name`, `display_order`, `is_active` | |
| `GCHealthQuestion` | `code`, `question_text`, `answer_type` (BOOLEAN/TEXT/CHOICE), `required`, `category`, `options`, `sort_order` | `answer_type` is the canonical spec field; legacy `question_type`/`is_required` retained. |
| `GCHealthQuestionnaire` | `code`, `name`, `version`, `scheme_type_ref`, `questions` (M2M), `threshold_trigger_amount`, `effective_from` | `items` from the prompt is realized by the `questions` M2M. `threshold_trigger_amount` escalates above-cover questionnaires. |

## 4. Product & Rider models (Prompt 2)

Extends Layer 2 in place. Like Prompt 1, all four models inherit
`GCParameterAuditMixin` and are added to the audit receivers.

| Model | Key fields | Notes |
|-------|-----------|-------|
| `GCSubProduct` | `code`, `name`, `description`, `is_active` | `parent_product_ref` from the prompt is realized by the existing `GCProduct.sub_product` FK (a product belongs to a sub-product family); a second, inverted parent pointer would create a circular hierarchy, so it is intentionally not added. |
| `GCProduct` | `code`, `name`, `scheme_type_ref`, `sub_product`, `insurance_class` (CREDIT_LIFE/GROUP_LIFE/GROUP_CREDIT/MEDICAL/ASSET/OTHER), `currency`, `premium_basis` (SINGLE/LEVEL), `requires_medical`, `min_entry_age`/`max_entry_age`, `min_loan_term`/`max_loan_term` (months), `min_loan_amount`/`max_loan_amount`, `free_cover_limit`, `is_active` | `scheme_type_ref` is `PROTECT` and nullable at the DB layer but required at the validation layer (matches the `GCSchemePremiumRate.scheme_type` pattern). `clean()` raises `PRODUCT_INVALID_SCHEME` when the scheme type is missing or inactive, and validates the age band and loan-term windows. `GCQuotation.product`, `GCScheme.product`, and `GCMedicalLimit.product` keep FK'ing into `GCProduct`. |
| `GCRider` | `code`, `name`, `rider_category` (DISABILITY/ACCIDENTAL_DEATH/CRITICAL_ILLNESS/FUNERAL/RETRENCHMENT/OTHER), `benefit_type` (FIXED/PERCENTAGE), `requires_underwriting`, `is_active` | Legacy `rider_type`/`is_mandatory` retained. |
| `GCRiderRate` | `rider`, `product_ref` (optional), `rate_value`, `rate_type` (PERCENTAGE/FIXED), `currency`, `effective_from`/`effective_to`, `is_active` | `product_ref` is optional so a rate may apply product-wide. `clean()` raises `RATE_MISMATCH` for negative values, a `PERCENTAGE` outside `(0, 100]`, or an invalid effective window. Legacy `rate_per_mille`/`flat_amount`/`effective_date`/`expiry_date` retained. |

**Validation rules** — a product must reference an existing, active scheme type;
rider rates must be positive, a `PERCENTAGE` rate must be `0 < value <= 100`, and
the effective window must be valid. The structured error registry in
`apps/group_credit/errors.py` exposes `SCHEME_NOT_FOUND` (404),
`PRODUCT_INVALID_SCHEME` (422), `RATE_MISMATCH` (422), plus `PRODUCT_NOT_FOUND`,
`RIDER_NOT_FOUND`, and `PRODUCT_CODE_CONFLICT`, with `GCParameterError` and
`registry_error()` helpers for the API/service layer (used from Prompt 4).

## 5. Medical U/W & Claim Setup models (Prompt 3)

Extends Layer 4 (Medical U/W) and Layer 5 (Claim Setup) in place. All twelve
models inherit `GCParameterAuditMixin` and are registered with the audit
receivers. Legacy fields on pre-existing models are retained for compatibility
but made optional, so spec-canonical records (scheme-scoped medical limits,
partner-linked facilities/practitioners) save without legacy baggage.

**Medical U/W** (Layer 4):

| Model | Key fields | Notes |
|-------|-----------|-------|
| `GCMedicalCode` | `code`, `name`, `description`, `category` (ICD_10/INTERNAL/OTHER), `is_active` | Legacy `icd10_code` retained for compatibility. |
| `GCMedicalLimit` | `scheme_type_ref`, `medical_code_ref`, `limit_amount`, `age_min`/`age_max`, `is_active` | `scheme_type_ref` required at validation (`SCHEME_NOT_FOUND`); `limit_amount` non-negative (`RATE_MISMATCH`); age window validated. Legacy `product`, `age_from`/`age_to`, `sum_assured_from`/`sum_assured_to`, `required_tests` retained and optional. |
| `GCUnderwritingDecision` | `code`, `name`, `description`, `requires_review`, `display_order`, `is_active` | e.g. STANDARD, LOADING, DECLINE. Legacy `sort_order` retained. |
| `GCPersonalHabit` | `code`, `name`, `habit_category` (SMOKING/ALCOHOL/DRUGS/SPORTS/OCCUPATION/OTHER), `underwriting_impact` (LOW/MEDIUM/HIGH), `is_active` | Legacy `category`/`risk_level` retained. |
| `GCMedicalHistory` | `code`, `name`, `condition_category` (CARDIOVASCULAR/RESPIRATORY/NEUROLOGICAL/ONCOLOGY/METABOLIC/OTHER), `severity` (LOW/MEDIUM/HIGH/CRITICAL), `waiting_period_days`, `exclusion_flag`, `is_active` | Waiting period must be non-negative. Legacy `category`/`risk_impact` retained. |
| `GCMedicalFacility` | `partner_ref` (FK → `Partner`), `code`, `name`, `facility_type` (HOSPITAL/CLINIC/LABORATORY/SPECIALIST), `approval_status` (PENDING/APPROVED/REJECTED), `is_active` | `partner_ref` lets a bank's preferred hospital network be parameterized. Legacy `is_approved`/`approved_date` and contact fields retained and optional. |
| `GCMedicalPractitioner` | `partner_ref` (FK → `Partner`), `code`, `first_name`/`last_name`, `name`, `specialization`, `license_number`, `facility` (FK → `GCMedicalFacility`), `approval_status`, `is_active` | Requires a name (or first/last). `name` is the legacy full-name field, optional. |

**Claim Setup** (Layer 5):

| Model | Key fields | Notes |
|-------|-----------|-------|
| `GCClaimType` | `code`, `name`, `category` (DEATH/CRITICAL_ILLNESS/PERMANENT_DISABILITY/TEMPORARY_DISABILITY/OTHER), `calculation_basis` (SUM_ASSURED/PERCENTAGE_OF_SUM_ASSURED/FIXED/OTHER), `requires_document_check`, `is_active` | Legacy `requires_medical_report` retained. |
| `GCClaimReason` | `code`, `name`, `claim_type` (FK → `GCClaimType`), `category` (ACCIDENT/ILLNESS/OTHER), `description`, `is_active` | A reason always belongs to a claim type. |
| `GCClaimStatus` | `code`, `name`, `display_order`, `is_terminal`, `is_active` | Legacy `sort_order` retained. |
| `GCDischargeType` | `code`, `name`, `template_code` (default DISCHARGE_DEFAULT), `variables` (JSON), `is_active` | Template code guarded against an explicit empty value. |
| `GCCorrespondentType` | `code`, `name`, `category` (PARTNER/MEMBER/FAMILY/LEGAL/MEDICAL/OTHER), `communication_channel` (EMAIL/SMS/MAIL/PHONE/OTHER), `purpose` (CLAIM_NOTIFICATION/DOCUMENT_REQUEST/PAYMENT_NOTICE/OTHER), `is_active` | |

**Validation** — medical limits must reference a scheme type (`SCHEME_NOT_FOUND`),
limits and waiting periods must be non-negative, and age windows must not be
inverted. Covered by `tests/test_medical_claims.py` (47 group_credit tests
across the three prompt files).

## 6. Permissions

Registered idempotently by `manage.py seed_gc_parameters_permissions`:

- Module codes: `gc_parameters.view`, `gc_parameters.manage`,
  `gc_parameters.configure`.
- Entity codes per parameter entity (`scheme_types`, `scheme_rates`,
  `member_statuses`, `scheme_statuses`, `renewal_statuses`,
  `health_questions`, `health_questionnaires`, `sub_products`, `products`,
  `riders`, `rider_rates`, `medical_codes`, `medical_limits`,
  `underwriting_decisions`, `personal_habits`, `medical_histories`,
  `medical_facilities`, `medical_practitioners`, `claim_types`,
  `claim_reasons`, `claim_statuses`, `discharge_types`,
  `correspondent_types`): `view`, `create`, `update`,
  `deactivate` (e.g. `gc_parameters.claim_types.create`). 95 permission
  codes in total (3 module + 23 entities × 4).
- `PermissionGroup` `GC_PARAMETERS` plus three roles:
  `GC_PARAMETER_VIEWER`, `GC_PARAMETER_MANAGER`, `GC_PARAMETER_ADMINISTRATOR`.
- Enforcement helper: `apps/group_credit/permissions.py`
  (`HasGCParameterPermission`). Existing Group Credit viewsets keep
  `permissions.IsAuthenticated`; fine-grained parameter gating is layered in
  the API prompt.

## 7. Audit logging

`apps/group_credit/audit_receivers.py` connects `pre_save`/`post_save` for all
24 Layer-1 parameter models, writing `AuditLog` records with actor, before/after
state, changed fields, reason, and source channel via `AuditService`. Seeds run
under the `SYSTEM` source channel (no request actor).

## 8. Integration map

```
GCSchemeType ──┬── GCSchemePremiumRate (rates per scheme type / product)
               ├── GCProduct (scheme_type_ref) ── GCSubProduct
               ├── GCHealthQuestionnaire (scheme_type_ref) ── GCHealthQuestion
               ├── GCMedicalLimit (scheme_type_ref) ── GCMedicalCode
               └── GCClaimReason (claim_type)

GCQuotation ── GCProduct / GCSchemeType / GCSchemePremiumRate  (rating)
GCScheme    ── GCProduct / GCSchemeType / GCSchemeStatus / Partner
GCSchemeMember ── GCSchemeMemberStatus / GCHealthQuestionnaire
GCClaim     ── GCClaimType / GCClaimReason / GCClaimStatus / GCDischargeType
GCMedicalCase ── GCMedicalCode / GCMedicalFacility / GCMedicalPractitioner
GCSchemeRenewal ── GCSchemeRenewalStatus
GCMedicalFacility / GCMedicalPractitioner ── Partner (partner_ref)
```

The parameter layer constrains and rates the runtime layer; the runtime layer
never hardcodes a rate, status, or limit — every branch resolves through a
parameter row, so the module is fully parameterizable and auditable.

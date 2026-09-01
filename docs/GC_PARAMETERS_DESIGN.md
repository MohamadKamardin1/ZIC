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

## 4. Permissions

Registered idempotently by `manage.py seed_gc_parameters_permissions`:

- Module codes: `gc_parameters.view`, `gc_parameters.manage`,
  `gc_parameters.configure`.
- Entity codes per Scheme Setup entity (`scheme_types`, `scheme_rates`,
  `member_statuses`, `scheme_statuses`, `renewal_statuses`,
  `health_questions`, `health_questionnaires`): `view`, `create`, `update`,
  `deactivate` (e.g. `gc_parameters.scheme_types.create`).
- `PermissionGroup` `GC_PARAMETERS` plus three roles:
  `GC_PARAMETER_VIEWER`, `GC_PARAMETER_MANAGER`, `GC_PARAMETER_ADMINISTRATOR`.
- Enforcement helper: `apps/group_credit/permissions.py`
  (`HasGCParameterPermission`). Existing Group Credit viewsets keep
  `permissions.IsAuthenticated`; fine-grained parameter gating is layered in
  the API prompt.

## 5. Audit logging

`apps/group_credit/audit_receivers.py` connects `pre_save`/`post_save` for all
Layer-1 parameter models, writing `AuditLog` records with actor, before/after
state, changed fields, reason, and source channel via `AuditService`. Seeds run
under the `SYSTEM` source channel (no request actor).

## 6. Integration map

```
GCSchemeType ──┬── GCSchemePremiumRate (rates per scheme type / product)
               ├── GCProduct (scheme_type_ref) ── GCSubProduct
               ├── GCHealthQuestionnaire (scheme_type_ref) ── GCHealthQuestion
               └── GCMedicalLimit (scheme_type_ref) ── GCMedicalCode

GCQuotation ── GCProduct / GCSchemeType / GCSchemePremiumRate  (rating)
GCScheme    ── GCProduct / GCSchemeType / GCSchemeStatus / Partner
GCSchemeMember ── GCSchemeMemberStatus / GCHealthQuestionnaire
GCClaim     ── GCClaimType / GCClaimReason / GCClaimStatus / GCDischargeType
GCMedicalCase ── GCMedicalCode / GCMedicalFacility / GCMedicalPractitioner
GCSchemeRenewal ── GCSchemeRenewalStatus
```

The parameter layer constrains and rates the runtime layer; the runtime layer
never hardcodes a rate, status, or limit — every branch resolves through a
parameter row, so the module is fully parameterizable and auditable.

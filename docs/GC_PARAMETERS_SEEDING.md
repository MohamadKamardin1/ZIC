# GC Parameters — Seeding Guide

Two idempotent management commands seed the GC Parameters bounded context.
Run them from the `backend/` directory with the project virtualenv.

## Commands

| Command | Seeds |
|---------|-------|
| `python manage.py seed_gc_parameters` | Prompt-1 scheme setup: scheme types, scheme/member/renewal statuses, base premium rates, health questions, the credit-life questionnaire. |
| `python manage.py seed_gc_parameters_full` | **Everything** — runs the scheme-setup base, then products + product rates, riders + rider rates, medical UW catalogs, facilities/practitioners, and claim setup. |

`seed_gc_parameters_full` is the entry point for standing up a working Group
Credit demo: scheme types and rates already exist, plus the products, riders,
medical panel and claim catalogue that the runtime (`GCQuotation`, `GCScheme`,
`GCClaim`) resolves against.

## Idempotency

Both commands are safe to run repeatedly. Rows are looked up by natural key
(`code`, `partner_number`, `rider`+`product_ref`, …) and then updated to the
payload, so re-running **converges** rather than duplicates. All dated rows
(`effective_from`, `effective_date`) anchor to a fixed reference date
(`2026-01-01`) so a second run never appends a second effective window.

Seeds run under the **SYSTEM** audit actor: audit receivers log CREATE/UPDATE
rows with `created_by`/`updated_by` pointing at the system, never at a request
user.

## What `seed_gc_parameters_full` seeds

### Scheme Setup (base — via `seed_gc_parameters`)
- **Scheme types** — `MORTGAGE_PROTECTION`, `BANK_LOAN`, `CORPORATE_SALARY`,
  `HIRE_PURCHASE` with partner restrictions.
- **Statuses** — 4 scheme, 4 member, 4 renewal statuses.
- **Base rates** — one `UNIT` rate per scheme type plus a `FLAT` bank-loan rate.
- **Questionnaire** — `GC_CREDIT_LIFE_HQ_V1` (5 health questions incl.
  HYPERTENSION / DIABETES) bound to `BANK_LOAN`.

### Products & Riders
- **Sub-product** — `GROUP_CREDIT_LIFE`.
- **Products**
  - `CREDIT_LIFE_A` — **Credit Life Plan A** under `BANK_LOAN`, loan terms
    6–240 months (≤ 20 years), ages 18–65, free cover TZS 2,000,000.
  - `CREDIT_LIFE_B` — **Credit Life Plan B** under `CORPORATE_SALARY`, loan
    terms 12–360 months (≤ 30 years), ages 18–60, free cover TZS 5,000,000,
    requires medical underwriting.
- **Product-scoped unit rates** — a standard `UNIT` (per-mille) rate bound to
  each flagship product.
- **Riders** — `ACCIDENTAL_DEATH_BENEFIT` (Accidental Death Benefit) and
  `PERMANENT_DISABILITY` (Permanent Disability), each with a 100%-of-sum-assured
  `PERCENTAGE` rate on both flagship products.

> **Assumption on rates and terms.** The `GCSchemePremiumRate` model is
> term-independent — a unit rate prices the sum assured across any loan term.
> The 1–30 year loan-term window is therefore carried by the **products'**
> `min_loan_term`/`max_loan_term` (in months), not by the rate table. Plan A
> spans ≤ 20 years and Plan B ≤ 30 years. A per-term rate ladder would require a
> new rate dimension (e.g. `loan_term_months`) and is intentionally deferred
> until the rating engine / frontend series locks the rate-table shape.

### Medical Underwriting
- **Conditions** (`GCMedicalHistory`) — HYPERTENSION (medium), DIABETES (high),
  ISCHAEMIC_HEART_DISEASE (high), CANCER (critical, exclusion).
- **ICD-10 codes** (`GCMedicalCode`) — `I10` hypertension, `E11` type-2
  diabetes, `I21` myocardial infarction, `C50` breast cancer.
- **Limits** (`GCMedicalLimit`) — BANK_LOAN-scoped: I10 → TZS 5,000,000,
  E11 → TZS 3,000,000 (ages 18–65).
- **UW decisions** — `STANDARD`, `LOADING`, `DECLINE`.
- **Habits** — `SMOKING` (high impact), `ALCOHOL` (medium impact).
- **Facilities** — `DSM-GENERAL-HOSP` (Dar es Salaam General Hospital) and
  `UHURU-CLINIC`, each backed by a Partner row.
- **Practitioners** — `DR-J-MWANZA` (cardiology) and `DR-P-KAVISHE` (general
  practice), each attached to a facility.

### Claim Setup
- **Claim types** — `DEATH` (Death, sum assured) and `PTD` (Permanent Total
  Disability, % of sum assured).
- **Reasons** — Accident and Illness reasons per claim type
  (`DEATH_NATURAL`, `DEATH_ACCIDENT`, `PTD_ACCIDENT`, `PTD_ILLNESS`).
- **Statuses** — `REGISTERED`, `UNDER_REVIEW`, `APPROVED`, `PAID` (terminal),
  `REJECTED` (terminal).
- **Discharge types** — `SETTLEMENT`, `REJECTION`.
- **Correspondent types** — `MEMBER_EMAIL`, `PARTNER_EMAIL`.

## Permissions seed

`seed_gc_parameters_permissions` registers the `gc_parameters.*` permission
codes (3 module + entity × view/create/update/deactivate), the
`GC_PARAMETERS` permission group, and the `GC_PARAMETER_VIEWER` /
`GC_PARAMETER_MANAGER` / `GC_PARAMETER_ADMINISTRATOR` roles. Run it once when
standing up an environment.

## Workflow check

After seeding, the following chain is resolvable for a demo:

```
GCSchemeType (BANK_LOAN)
  → GCProduct (CREDIT_LIFE_A, term ≤ 240 months)
  → GCSchemePremiumRate (unit rate) · GCRider + GCRiderRate
  → GCMedicalLimit / GCMedicalFacility / GCMedicalPractitioner (when UW needed)
  → GCClaimType DEATH/PTD + GCClaimReason + GCClaimStatus
```

API smoke check: `GET /api/v1/gc/options/products/?scheme_type=BANK_LOAN`
returns `CREDIT_LIFE_A — Credit Life Plan A`.

# GC Parameters — Data Dictionary

Field-level dictionary for the GC Parameters bounded context (`group_credit`
Layer-1 parameter models), covering the categories seeded by
`seed_gc_parameters_full`. Runtime models (`GCQuotation`, `GCScheme`,
`GCSchemeMember`, `GCClaim`, …) are out of scope here.

Every parameter model extends the **audit mixin** which adds four bookkeeping
fields: `created_at`, `updated_at`, `created_by`, `updated_by` (the last two are
audit actors — SYSTEM for seeds). All rows are served through serializers that
also emit a `display_name` (`CODE — Name`) and a `<fk>_display` field per
foreign key.

---

## 1. Scheme Setup

### GCSchemeType
Defines the kind of scheme written and restricts which partner category can use it.

| Field | Type | Notes / seed values |
|-------|------|---------------------|
| `code` | Char(50) unique | Canonical code, e.g. `BANK_LOAN`. |
| `name` | Char(200) | Human name. |
| `description` | Text | Free text. |
| `partner_type_restriction` | Char(30) | `BANK`, `CORPORATE`, `BANK_AND_CORPORATE`, `ANY`. |

### GCSchemePremiumRate
Premium rate for a scheme type (and optionally a product). **Term-independent**:
a single unit/flat rate prices any loan term inside the product's 1–30 year
window.

| Field | Type | Notes / seed values |
|-------|------|---------------------|
| `name` | Char(200) | e.g. `Credit Life Plan A - Standard Unit Rate`. |
| `scheme_type` | FK → GCSchemeType | Required scope. |
| `product_ref` | FK → GCProduct (null) | Optional product scope. |
| `rate_type` | Char(20) | `UNIT`, `FLAT`, `BASE`, `LOADING`, `DISCOUNT`. |
| `rate_value` | Decimal(14,6) | Unit rate per mille, or fixed amount for FLAT. |
| `currency` | Char(3) | `TZS`. |
| `age_band_start` / `age_band_end` | Int | Entry-age band the rate applies to. |
| `gender` | Char(10) | `M`, `F`, `U` (Unisex). |
| `effective_from` / `effective_to` | Date | Effective window (`None` = open). |
| `effective_date` / `expiry_date` | Date | Legacy retained fields. |
| `is_active` | Bool | |

### GCSchemeStatus
Lifecycle status of a scheme.

| Field | Notes / seed values |
|-------|---------------------|
| `code` | `PENDING_MEDICAL`, `ACTIVE`, `INACTIVE`, `TERMINATED`. |
| `is_terminal` | `TERMINATED` is terminal. |

### GCSchemeMemberStatus
Status of an individual member.

| Field | Notes / seed values |
|-------|---------------------|
| `code` | `PENDING_MEDICAL`, `ACTIVE`, `INACTIVE`, `DECEASED`. |
| `is_terminal` | `DECEASED` is terminal. |
| `allows_claims` | Only `ACTIVE`/`DECEASED` allow claims. |

### GCSchemeRenewalStatus
| Field | Notes / seed values |
|-------|---------------------|
| `code` | `PENDING`, `APPROVED`, `DECLINED`, `RENEWED`. |

### GCHealthQuestion
| Field | Notes / seed values |
|-------|---------------------|
| `code` | `SMOKING`, `ALCOHOL`, `HYPERTENSION`, `DIABETES`, `OCCUPATION`. |
| `question_text` | Text. |
| `answer_type` | `BOOLEAN`, `TEXT`, `CHOICE`. |
| `category` | `GENERAL`, `LIFESTYLE`, `FAMILY`, `SPECIFIC`. |
| `required` / `sort_order` | Flag / ordering. |

### GCHealthQuestionnaire
| Field | Notes / seed values |
|-------|---------------------|
| `code` | `GC_CREDIT_LIFE_HQ_V1`. |
| `version` | `1.0`. |
| `scheme_type_ref` | FK → GCSchemeType (`BANK_LOAN`). |
| `questions` | M2M → GCHealthQuestion (5 questions). |
| `threshold_trigger_amount` | Decimal — above this cover UW is required. |

---

## 2. Product Setup

### GCSubProduct
| Field | Notes / seed values |
|-------|---------------------|
| `code` | `GROUP_CREDIT_LIFE`. |
| `name` | `Group Credit Life`. |

### GCProduct
A sellable credit-life plan, scoped to a scheme type. **Loan terms in months**
define the 1–30 year cover window.

| Field | Notes / seed values |
|-------|---------------------|
| `code` | `CREDIT_LIFE_A`, `CREDIT_LIFE_B`. |
| `name` | `Credit Life Plan A`, `Credit Life Plan B`. |
| `sub_product` | FK → GCSubProduct (required). |
| `scheme_type_ref` | FK → GCSchemeType (required at validation). |
| `insurance_class` | `CREDIT_LIFE`, `GROUP_LIFE`, `GROUP_CREDIT`, `MEDICAL`, `ASSET`, `OTHER`. |
| `currency` | `TZS`. |
| `min_loan_term` / `max_loan_term` | Int months. Plan A `6–240` (≤ 20y); Plan B `12–360` (≤ 30y). |
| `min_loan_amount` / `max_loan_amount` | Decimal. |
| `min_entry_age` / `max_entry_age` | Entry-age band. |
| `max_cover_age` | Oldest age cover continues to. |
| `free_cover_limit` | Decimal — sum assured covered without medical evidence. |
| `premium_basis` | `SINGLE`, `LEVEL`. |
| `requires_medical` | Bool — Plan B requires UW. |
| `is_active` | Bool. |

---

## 3. Rider Setup

### GCRider
| Field | Notes / seed values |
|-------|---------------------|
| `code` | `ACCIDENTAL_DEATH_BENEFIT`, `PERMANENT_DISABILITY`. |
| `rider_category` | `DISABILITY`, `ACCIDENTAL_DEATH`, `CRITICAL_ILLNESS`, `FUNERAL`, `RETRENCHMENT`, `OTHER`. |
| `benefit_type` | `FIXED`, `PERCENTAGE`. |
| `requires_underwriting` | Bool — PTD requires UW. |

### GCRiderRate
| Field | Notes / seed values |
|-------|---------------------|
| `rider` | FK → GCRider. |
| `product_ref` | FK → GCProduct (null = product-wide). |
| `rate_type` | `PERCENTAGE`, `FIXED`. |
| `rate_value` | Decimal — `100.000000` % of sum assured for ADB/PTD. |
| `age_band_start` / `age_band_end` | Int. |
| `currency`, `gender`, `effective_from/to`, `is_active` | As standard. |

---

## 4. Medical Underwriting

### GCMedicalHistory
Named conditions used for underwriting.

| Field | Notes / seed values |
|-------|---------------------|
| `code` | `HYPERTENSION`, `DIABETES`, `ISCHEMIC_HEART_DISEASE`, `CANCER`. |
| `condition_category` | `CARDIOVASCULAR`, `RESPIRATORY`, `NEUROLOGICAL`, `ONCOLOGY`, `METABOLIC`, `OTHER`. |
| `severity` | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`. |
| `waiting_period_days` | Int. |
| `exclusion_flag` | Bool — `CANCER` is an exclusion. |

### GCMedicalCode
ICD-10 evidence codes recorded on medical examinations.

| Field | Notes / seed values |
|-------|---------------------|
| `code` | `I10`, `E11`, `I21`, `C50`. |
| `name` | ICD-10 description. |
| `icd10_code` | Legacy ICD-10 field. |
| `category` | `ICD_10`, `INTERNAL`, `OTHER`. |

### GCMedicalLimit
Scheme-scoped cover limit per condition.

| Field | Notes / seed values |
|-------|---------------------|
| `scheme_type_ref` | FK → GCSchemeType (required). |
| `medical_code_ref` | FK → GCMedicalCode. |
| `limit_amount` | Decimal — `I10` TZS 5,000,000; `E11` TZS 3,000,000. |
| `age_min` / `age_max` | Int window. |

### GCUnderwritingDecision
| Field | Notes / seed values |
|-------|---------------------|
| `code` | `STANDARD`, `LOADING`, `DECLINE`. |
| `requires_review` | Bool — LOADING/DECLINE route to senior UW. |

### GCPersonalHabit
| Field | Notes / seed values |
|-------|---------------------|
| `code` | `SMOKING`, `ALCOHOL`. |
| `habit_category` | `SMOKING`, `ALCOHOL`, `DRUGS`, `SPORTS`, `OCCUPATION`, `OTHER`. |
| `underwriting_impact` | `LOW`, `MEDIUM`, `HIGH`. |

### GCMedicalFacility
| Field | Notes / seed values |
|-------|---------------------|
| `code` | `DSM-GENERAL-HOSP`, `UHURU-CLINIC`. |
| `name` | e.g. `Dar es Salaam General Hospital`. |
| `facility_type` | `HOSPITAL`, `CLINIC`, `LABORATORY`, `SPECIALIST`. |
| `approval_status` | `PENDING`, `APPROVED`, `REJECTED`. |
| `partner_ref` | FK → partners.Partner (operating entity). |
| `address`, `city`, `region`, `phone`, `email`, `contact_person` | Contact details. |

### GCMedicalPractitioner
| Field | Notes / seed values |
|-------|---------------------|
| `code` | `DR-J-MWANZA`, `DR-P-KAVISHE`. |
| `first_name` / `last_name` / `name` | Name fields. |
| `specialization` | e.g. `CARDIOLOGY`. |
| `license_number` | e.g. `TZ-MED-001234`. |
| `facility` | FK → GCMedicalFacility. |
| `approval_status` | `PENDING`, `APPROVED`, `REJECTED`. |
| `partner_ref` | FK → partners.Partner (optional). |

---

## 5. Claim Setup

### GCClaimType
| Field | Notes / seed values |
|-------|---------------------|
| `code` | `DEATH`, `PTD`. |
| `name` | `Death`, `Permanent Total Disability`. |
| `category` | `DEATH`, `CRITICAL_ILLNESS`, `PERMANENT_DISABILITY`, `TEMPORARY_DISABILITY`, `OTHER`. |
| `calculation_basis` | `SUM_ASSURED`, `PERCENTAGE_OF_SUM_ASSURED`, `FIXED`, `OTHER`. |
| `requires_document_check` / `requires_medical_report` | Bool flags. |

### GCClaimReason
| Field | Notes / seed values |
|-------|---------------------|
| `code` | `DEATH_NATURAL`, `DEATH_ACCIDENT`, `PTD_ACCIDENT`, `PTD_ILLNESS`. |
| `claim_type` | FK → GCClaimType (related `reasons`). |
| `category` | `ACCIDENT`, `ILLNESS`, `OTHER`. |

### GCClaimStatus
| Field | Notes / seed values |
|-------|---------------------|
| `code` | `REGISTERED`, `UNDER_REVIEW`, `APPROVED`, `PAID`, `REJECTED`. |
| `is_terminal` | `PAID`/`REJECTED` are terminal. |

### GCDischargeType
| Field | Notes / seed values |
|-------|---------------------|
| `code` | `SETTLEMENT`, `REJECTION`. |
| `template_code` | Document template key, e.g. `DISCHARGE_DEFAULT`. |
| `variables` | JSON template variables. |

### GCCorrespondentType
| Field | Notes / seed values |
|-------|---------------------|
| `code` | `MEMBER_EMAIL`, `PARTNER_EMAIL`. |
| `category` | `PARTNER`, `MEMBER`, `FAMILY`, `LEGAL`, `MEDICAL`, `OTHER`. |
| `communication_channel` | `EMAIL`, `SMS`, `MAIL`, `PHONE`, `OTHER`. |
| `purpose` | `CLAIM_NOTIFICATION`, `DOCUMENT_REQUEST`, `PAYMENT_NOTICE`, `OTHER`. |

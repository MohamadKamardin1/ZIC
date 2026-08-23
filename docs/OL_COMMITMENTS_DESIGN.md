# OL Commitments — Design Document

Status: **Foundation (Prompt 1 of 12)**
Module: Ordinary Life > Ordinary Life Commitments
Canonical parameter source: `apps.ol_parameters` (OL Policy Setup group)
Companion prompts: `docs/prompts/OL_COMMITMENTS_PROMPTS.md`

---

## 1. Purpose and Scope

The OL Commitments module owns the Ordinary Life **premium obligation** lifecycle:

1. **Proposal first premium** — a payment-ready proposal produces a single first-premium commitment which must be settled before a policy can be issued.
2. **Policy renewal schedule** — an issued policy produces the full recurring premium schedule derived from payment frequency, payment period, and policy term.

A commitment is a **scheduled, parameter-validated obligation to pay a due premium amount on a due date**. It is not a financial ledger: the ledger boundary remains the future finance / `OLPaymentObligation` + `OLPaymentAllocation` contract described in `docs/ORDINARY_LIFE_PHASE2_DOMAIN_CONTRACT.md`. Commitments provide the operationally visible obligation, allocation, grace, and notification context; receipts post against commitments through `OLCommitmentAllocation` rows that balance to the due amount (SRS business rule: *receipts and payments must balance to their allocations*).

### 1.1 Why a dedicated app

The repository already carries legacy placeholder tables (`apps.ordinary_life.OLCommitment`, table `ol_commitment`) that are proposal-only, non-typed, and do not satisfy the SRS commitment requirements (due/grace/lapse dates, allocations, reversals, notifications, parameter-validated status). Per `docs/ORDINARY_LIFE_PHASE2_DOMAIN_CONTRACT.md`, those legacy rows remain readable as a bridge and are **not** the source of truth. The new `apps.ol_commitments` app is the module source of truth and uses table prefix `ol_commitments_*` to avoid collision.

### 1.2 Traceability to specification

| Spec / rule | Where satisfied |
| --- | --- |
| SRS §2.3.1 — "Commitments shall track due premium or benefit commitments and settlement status." | `OLCommitment` (due dates, premium, paid, balance, status), lifecycle actions (Prompt 3). |
| SRS §2.6 — "Receipts shall record incoming funds and allocate them to policies, schemes, invoices, claims, or partner accounts." | `OLCommitmentAllocation`; `receipt_reference` seam to front office `FOReceipt` (Prompt 10). |
| SRS Business rules — "Receipts and payments must balance to their allocations or requisitions." | `OLCommitment.balance` invariant; `COMMITMENT_OVERPAYMENT` structured error; reversal restores balance. |
| SRS §2.3.3 — OL Commitment Statuses, OL Grace Period, Grace Period Notification Schedule | Status validated against `ol_parameters.OLCommitmentStatus`; grace/lapse from `OLGracePeriod`; notifications from `OLGracePeriodNotificationSchedule`. |
| SRS §2.9 / §3.2 — permission and audit control | Module permission codes; every action audited with actor, before/after, reason, source channel. |
| BR-01 (quotation to proposal eligibility), BR-02 (quotation version preservation) | Consumed boundaries; commitments consume finalized quotations via proposals. See §10. |
| **BR-03 (assumed)** — *A policy is issued only after the first-premium commitment is settled (first-premium gate).* | `OLCommitment.source_type=PROPOSAL` first-premium commitment; the issue gate consumes a settled first premium (Prompt 10 listener). See §10. |
| **BR-05 (assumed)** — *A premium transaction/receipt is complete when its allocations balance exactly to the due commitment amount; unmatched or over-allocated receipts are rejected or flagged for reversal.* | Allocation balance invariant; `COMMITMENT_OVERPAYMENT` structured error; reversal model. See §10. |
| **Premium transaction/receipt entity (assumed)** — the canonical receipt entity is `apps.front_office.FOReceipt`; until it exposes allocation endpoints, allocations carry a manual `receipt_reference` + source channel. | §7; Prompt 10 contracts the reader seam. |

> Assumption notation: items marked **(assumed)** fill verified gaps where the repository-shipped ZIC spec documents do not carry a complete BR listing. Assumptions are explicit, parameter-driven, and revisable by the business.

---

## 2. Commitment Concept

A **commitment** is created in one of three ways (`source_type`):

| `source_type` | Meaning | Example |
| --- | --- | --- |
| `PROPOSAL` | First-premium obligation from a payment-ready approved proposal | Proposal `OLP-2026-000123` approved to first premium `TZS 2,400,000.00` |
| `POLICY` | A row of the recurring renewal schedule from an issued policy | Policy `OLP-2026-000234`, monthly, installment #7 of 120 |
| `MANUAL` | Authorized operator-created obligation / adjustment | Arrears bill, catch-up premium, correction |

Every commitment carries:

- an **idempotency identity** = `source_type + source content-type + source id + installment_number`, unique per source;
- a **due amount** (`premium_amount`), **amount paid** (`amount_paid`), optional **amount waived** (`amount_waived`), and a derived, persisted **balance**;
- a **parameter-validated status**, a grace/lapse envelope (`grace_date`, `lapse_date`), reason fields for lifecycle changes, and an approval flag (`approval_required`);
- **audit provenance** (actor, timestamps) and an explicit `source_channel` (`SYSTEM | API | IMPORT | MANUAL | BATCH | PORTAL | ADMIN`) recorded on the obligation row itself and replicated onto every audit row and domain event.

### 2.1 Balance invariant

```
balance = premium_amount - amount_paid - amount_waived
```

`balance` is stored and recomputed on every save so tables can filter and sort on it, and enforced by model constraints:

- `amount_paid >= 0`, `amount_waived >= 0`
- `premium_amount > 0`
- `balance == premium_amount - amount_paid - amount_waived`

An allocation larger than the current balance is rejected with `COMMITMENT_OVERPAYMENT` (Prompt 3). When `balance == 0` and payments were received, status moves to the parameter-terminal completed state and `CommitmentCompleted` fires.

---

## 3. Status State Machine (parameter-driven)

### 3.1 Parameter source

Status codes are read from `apps.ol_parameters.models.OLCommitmentStatus` (`applies_to="COMMITMENT"`, `is_active=True`, effective dates respected, `is_terminal` flag, `display_order` for ordering). Seeded catalogs (Zanzibar seed + policy setup seed):

| Code | Meaning | Terminal |
| --- | --- | --- |
| `PENDING` / `ZIC_COMMITMENT_PENDING` | Due, awaiting payment | No |
| `PARTIALLY_PAID` / `ZIC_COMMITMENT_PARTIAL` | Balance outstanding | No |
| `COMPLETED` / `ZIC_COMMITMENT_COMPLETE` | Fully settled | Yes |
| `CANCELLED` / `ZIC_COMMITMENT_CANCELLED` | Closed by cancellation | Yes |

Operational add-on states (Prompt 3/4) may be configured by adding parameter rows: `OVERDUE`, `SUSPENDED`, `WAIVED`, `ACTIVE`.

### 3.2 Rules applied by the module

1. **Initial status** is resolved from parameters, never hardcoded: the first active `COMMITMENT` status by `display_order ASC, code ASC` (seeded `PENDING`). An empty catalog raises `PARAMETER_MISSING`.
2. **Every persisted status is validated** against the active parameter catalog at `clean()` time; a status code that is not present in the catalog (or is inactive/out of effective window) is rejected.
3. **Terminal statuses are final**: no further transition (except read-only views); derived from the parameter `is_terminal` flag. Completion and cancellation are the seeded terminal states.
4. **Transition authority**: lifecycle actions (record_payment, reverse, suspend, waive, cancel, reschedule — Prompt 3) derive allowed next-states from:
   - the parameter `is_terminal` flag,
   - an optional per-status `allowed_transitions` JSON metadata the business can add to `OLCommitmentStatus` (forward-compatible; the seed schema already follows the `OLPolicyStatus` precedent), and
   - intrinsic guards (e.g. you cannot pay a cancelled commitment; you cannot reverse a completed commitment without permission).
   Invalid transitions raise `COMMITMENT_INVALID_TRANSITION` whose `resolution_steps` include the allowed next states.

**Intended transition matrix** (Prompt 3 will implement and test the full matrix against parameters):

| From state | Allowed next states (actions) |
| --- | --- |
| `PENDING` | `PARTIALLY_PAID` (payment), `COMPLETED` (full payment), `SUSPENDED`, `WAIVED`, `CANCELLED`, `OVERDUE` (batch) |
| `PARTIALLY_PAID` | `COMPLETED` (full payment), `PARTIALLY_PAID` (further payment), `SUSPENDED`, `WAIVED`, `CANCELLED`, `OVERDUE` (batch) |
| `OVERDUE` | `PARTIALLY_PAID` (payment), `COMPLETED` (full payment), `LAPSED`/review flag, `CANCELLED`, `SUSPENDED` |
| `SUSPENDED` | `PENDING` (reactivate), `CANCELLED` |
| `WAIVED` | `COMPLETED` via approval workflow |
| `COMPLETED` (terminal) | none |
| `CANCELLED` (terminal) | none |

State entries for `OVERDUE`/`SUSPENDED`/`WAIVED`/`ACTIVE`/`LAPSED` must exist as `OLCommitmentStatus` parameter rows before Prompt 3/4 can transition into them.

---

## 4. Generation Rules

### 4.1 Inputs (all parameterized)

| Input | Source |
| --- | --- |
| `premium_frequency` | Quotation plan configuration (`OLQuotationPlanConfiguration.premium_frequency`) |
| `payment_period_years` | Quotation plan configuration (`payment_period_years`), validated `<= term_years` |
| `policy_term` (`term_years`) | Quotation plan configuration (`term_years`) |
| `premium_amount` per frequency | Quotation plan configuration `premium_amount` (per-frequency annualized premium is `premium_amount * frequency_factor`) |
| `currency` | Quotation / policy currency (default `TZS`) |
| `start_date` / `first_due_date` | Proposal payment-ready date or policy `start_date` |
| `grace_days`, `lapse_days`, `warning_days`, `pre_lapse_days` | `ol_parameters.OLGracePeriod` scoped match (see §5) |
| initial status | `ol_parameters.OLCommitmentStatus` catalog (see §3) |

### 4.2 Frequency factor

| Frequency | Factor (periods / year) |
| --- | --- |
| `ANNUAL` | 1 |
| `SEMI_ANNUAL` | 2 |
| `QUARTERLY` | 4 |
| `MONTHLY` | 12 |

Unknown / unparameterized frequencies raise `PARAMETER_MISSING`.

### 4.3 Installment count

For a **policy renewal schedule**:

```
installment_count = payment_period_years * frequency_factor
```

- When the policy pays for the whole term, `payment_period_years == term_years`.
- The last installment's `due_date` must not exceed `end_date`; any surplus period is dropped and documented in the `grace/lapse` window of the final obligation.
- When payment period is not configured, the module assumes `payment_period_years = term_years` (documented assumption, arXiv: recurring premiums for the entire cover term).

For a **proposal first premium**, `installment_number = 1`, `installment_count = 1`.

### 4.4 Due-date stepping

Period length per frequency (calendar months): `MONTHLY=1, QUARTERLY=3, SEMI_ANNUAL=6, ANNUAL=12`.

```
installment i  ->  due_date_i = first_due_date + (i - 1) * period_length_months
```

The full schedule is generated idempotently; `source_type + content-type + source-id + installment_number` is the unique key. Duplicate attempts return the **existing** commitment and raise the structured `COMMITMENT_DUPLICATE` error (Prompt 2) with a reference to it.

### 4.5 Regeneration on premium change

- **Pending / partially paid** commitments are **superseded** (never deleted) — a supersede reason is written to the audit log and a replacement row carries the corrected amounts.
- **Paid / terminal** commitments are never regenerated (money already allocated).

---

## 5. Grace, Overdue and Lapse Behavior

### 5.1 Parameter source and scoped resolution

`ol_parameters.OLGracePeriod` rows carry `product`, `plan`, `premium_frequency`, `grace_days`, `warning_days`, `pre_lapse_days`, `lapse_days`, `minimum_due_amount`.

Resolution order (most specific first, effective dates respected, `is_active=True`):

1. `product + plan + premium_frequency`
2. `plan + premium_frequency` (product unset)
3. `product + premium_frequency` (plan unset)
4. `premium_frequency` only
5. global row (product, plan, and frequency unset)

No matching row raises `PARAMETER_MISSING` (`resolution_steps` includes the OL Parameters > Policy Setup > OL Grace Period navigation path).

### 5.2 Envelope dates and state windows

```
grace_date     = due_date + grace_days
warning_date   = due_date + warning_days
pre_lapse_date = due_date + pre_lapse_days
lapse_date     = due_date + lapse_days
```

| Window (relative to `due_date`) | Behavior |
| --- | --- |
| `(due_date, grace_date]` | Still payable without penalty; status remains non-terminal. Grace start triggers `GRACE_START` notifications. |
| `(grace_date, lapse_date]` | **Overdue** — batch `process_commitment_overdue` (Prompt 4) marks the commitment `OVERDUE` and issues `warning` / `pre-lapse` notifications. |
| `> lapse_date` | Lapse recommendation — a policy-level lapse review event is raised; the commitment remains collectable until cancelled. |

`minimum_due_amount`: a commitment whose `balance <= minimum_due_amount` is treated as satisfied for batch purity (documented assumption; seeded value `TZS 25,000.00` applies to the Zanzibar seed).

Batch processing (Prompt 4) is **idempotent**: repeated runs never duplicate notification logs or re-fire events for the same (commitment, event_type, schedule row).

---

## 6. Notification Behavior

### 6.1 Parameter source

`ol_parameters.OLGracePeriodNotificationSchedule`: `event_type` (`PREMIUM_DUE`, `GRACE_START`, `GRACE_WARNING`, `PRE_LAPSE`, `LAPSE`), `days_offset` (relative to `due_date` when negative, relative to grace/lapse when positive — see matrix), `notification_channel` (`SYSTEM`, `EMAIL`, `SMS`, `PORTAL`, `OTHER`), `recipient_type` (`POLICYHOLDER`, `AGENT`, `STAFF`, `PARTNER`), `template_code`.

Zanzibar seed examples: `ZIC_NOTIFY_RENEWAL_DUE` (PREMIUM_DUE, −10 days, SYSTEM/EMAIL), `ZIC_NOTIFY_GRACE_START` (GRACE_START, +1 day, SMS, POLICYHOLDER).

### 6.2 Scheduling semantics

For each commitment, the overdue batch (Prompt 4) walks active schedule rows that apply to the occurrence date:

```
dispatch_on = due_date + days_offset          (days_offset measured from due_date)
```

Rows with `days_offset < 0` fire **before** the due date (PREMIUM_DUE reminders); rows with `days_offset >= 0` fire after due (grace warnings, pre-lapse, lapse). One `OLCommitmentNotificationLog` row is written per matched (commitment, schedule, occurring date); the log stores `event_type`, `channel`, `recipient_type`, `recipient_identifier`, `template_code`, intended `dispatch_on`, and dispatch `status` (`PENDING`, `DISPATCHED`, `FAILED`, `SKIPPED`).

Dispatch itself is a **clean integration seam**: Prompt 4 provides stubs only (`SYSTEM` channel logs inside the platform); email/SMS/portal adapters plug in without changing business logic.

---

## 7. Data Model

### 7.1 `OLCommitment`

| Field | Type | Notes |
| --- | --- | --- |
| `commitment_number` | str unique | Parameter-driven numbering (`NumberingEngine` `OL_COMMITMENT` code, Prompt 2) |
| `idempotency_key` | str nullable unique | `sha256(source_type\|ct_pk\|source_pk\|installment)` (Prompt 2) |
| `source_type` | `PROPOSAL | POLICY | MANUAL` | required |
| `source_content_type` / `source_object_id` / `source` | generic FK | proposal or policy object; null for MANUAL |
| `source_reference` | str | human reference, e.g. `OLP-2026-000123` |
| `partner` + `partner_name_snapshot` | FK + str | display partner (proposal/policy holder) |
| `product` + `product_name_snapshot` | FK + str | `ol_parameters.OLProduct` |
| `plan` + `plan_name_snapshot` | FK + str | `ordinary_life.OLPlan` |
| `currency` | str(3) | default `TZS` |
| `installment_number` / `installment_count` | int | schedule position and total |
| `due_date` | date | |
| `premium_amount` | decimal(18,2) | > 0 |
| `amount_paid` | decimal(18,2) | default 0 |
| `amount_waived` | decimal(18,2) | default 0 |
| `balance` | decimal(18,2) | derived, persisted (invariant in §2.1) |
| `status` | str | validated against parameter catalog (§3) |
| `grace_date`, `lapse_date` | date | from `OLGracePeriod` (§5) |
| `reason_code`, `reason_text` | str / text | lifecycle/change reasons |
| `approval_required` | bool | flagged by waive and other approval hooks |
| `source_channel` | str | `SYSTEM | API | IMPORT | MANUAL | BATCH | PORTAL | ADMIN` |
| audit | timestamps + actor | `created_at/updated_at`, `created_by/updated_by` |

### 7.2 `OLCommitmentAllocation`

| Field | Notes |
| --- | --- |
| `commitment` FK | `PROTECT` |
| `receipt_reference` | front office receipt number or manual reference; unique within commitment |
| `amount` | > 0 |
| `payment_mode` | e.g. `CASH`, `BANK_TRANSFER`, `M-PESA` — parameterized from front office |
| `currency` | allocation currency |
| `exchange_rate` | decimal(12,6), default 1 |
| `reason` | required for reversals |
| `reversal_of` | self FK to the original allocation (null except for reversal rows) |
| `allocated_at`, `allocated_by`, `source_channel`, audit | provenance |

Cross-currency rule: allocating in a currency different from the commitment requires an explicit `exchange_rate`; a mismatch without a rate raises `CURRENCY_MISMATCH` (Prompt 3).

### 7.3 `OLCommitmentNotificationLog`

`commitment` FK, `event_type`, `dispatch_on`, `channel`, `recipient_type`, `recipient_identifier`, `template_code`, `status`, `payload` (JSON), `dispatched_at`, `created_by`, `source_channel`.

### 7.4 Permission codes

`ol_commitments.view | create | generate | record_payment | reverse | suspend | waive | cancel | reschedule`. Registered as `users.UserPermission` rows (module `ol_commitments`), grouped into a `PermissionGroup`, and offered as default role groups (Viewer / Handler / Administrator). Action-to-code mapping and a DRF `HasOLCommitmentPermission` accompany them (Prompt 5+ consume them).

---

## 8. Domain Events

Every material state change publishes a durable outbox event on `apps.common.models.DomainEvent` and an `AuditLog` row. Initial event surface (Prompt 1 wires the outbox + audit for the model receivers; Prompt 3/4 fire per action):

| Event | Trigger (future) |
| --- | --- |
| `CommitmentGenerated` | generation engine creates a commitment (Prompt 2) |
| `CommitmentPaymentAllocated` | `record_payment` / allocation posted (Prompt 3) |
| `CommitmentOverdue` | overdue batch marks commitment overdue (Prompt 4) |
| `CommitmentSuspended` | suspend action (Prompt 3) |
| `CommitmentWaived` | waive action (Prompt 3) |
| `CommitmentCancelled` | cancel action (Prompt 3) |
| `CommitmentCompleted` | balance reaches zero (Prompt 3) |

Payload convention: `commitment_number`, `aggregate_id`, `from_status`, `to_status`, `actor_id`, `reason`, `source_channel`, `metadata`.

---

## 9. Global Structured Error Shape

All API faults render through the shared handler `apps.core.exceptions.custom_exception_handler`. The shaped payload (world `error_code` contract) is:

```json
{
  "error_code": "COMMITMENT_OVERPAYMENT",
  "message": "The payment amount exceeds the outstanding balance of the commitment.",
  "resolution_steps": ["Review the outstanding balance of the commitment.", "Adjust the payment amount, or", "Raise a credit/overpayment handling request per documented assumption."],
  "field_errors": { "amount": ["Amount cannot exceed balance of 100,000.00."] },
  "doc_ref": "docs/OL_COMMITMENTS_USER_GUIDE.md"
}
```

Compatibility: the legacy `success / status_code / error{code,message,details} / meta{timestamp, request_id, version}` envelope is retained so the existing `apiClient.ts` keeps working while the new flat keys feed the Error Coach (Prompt 7–9). Django/DRF validation, permission, and not-found faults are mapped automatically into the same shape. The full code taxonomy (12+ codes) is Prompt 6.

---

## 10. Integration Map

| Boundary | Seam | Direction |
| --- | --- | --- |
| **Proposals** (`ol_proposals.OLProposal` / legacy `ordinary_life.OLProposal`) | `PROPOSAL` source; first-premium commitment generated on proposal reaching payment-ready (Prompt 2), consumed for policy issue (BR-03, Prompt 10). | in (generation) |
| **Policies** (`ordinary_life.OLPolicy`) | `POLICY` source; renewal schedule generated on issue (Prompt 2, Prompt 10 listener). Lapse review feeds policy status. | in (generation), out (lapse) |
| **Front office receipts** (`apps.front_office.FOReceipt`) | `OLCommitmentAllocation.receipt_reference`; balanced allocations against commitment (Prompt 10 reader seam; until FO exposes allocation endpoints, manual reference + `source_channel`). | in (receipt allocation) |
| **Reports** | Report category "Ordinary Life Commitments" and a commitment dataset (number, source, partner, product/plan, due/paid/balance, currency, status, grace/lapse); KPI fields for total due/outstanding, overdue, collected (Prompt 10). | out (read) |
| **Partner portal** (`Partners Portal Modules Menus.xlsx`) | Read-only endpoints scoped strictly to the linked partner via `User.visible_partners()` / `can_access_partner` (Prompt 10). | out (read, scoped) |
| **Dashboard** | Overdue-commitment and approvals-pending KPI hooks (Prompt 10). | out (KPI) |
| **OL Parameters** (`apps.ol_parameters`) | Status, grace, notification, and (future) numbering catalog consumption. No OL Parameters row is owned here. | in (read only) |
| **Governance** | Audit writer `AuditService` and outbox `DomainEvent`. | in (write) |

### 10.1 Receipt / premium-transaction contract (Prompt 10 target)

```
FOReceipt (front office) ──receipt_reference──▶ OLCommitmentAllocation
                                                        │ amount
                                                        ▼
                                          OLCommitment.balance (invariant)
```

- A receipt is **matched** when one or more allocations fully cover a commitment (`balance == 0`).
- Unmatched or over-allocated receipts are rejected (`COMMITMENT_OVERPAYMENT`) or flagged for reversal — BR-05.
- Reversal rows reproduce the original reference (`reversal_of`) and restore balance; reversal after grace window expiry is guarded (`GRACE_EXPIRED_REVERSAL_BLOCKED`).

### 10.2 BR-03 / BR-05 traceability detail (assumed rules)

- **BR-03** — first-premium gate: a proposal converts to an issued policy only once its `source_type=PROPOSAL` commitment is `COMPLETED`. The implementation follows the existing wording in `docs/OL_QUOTATIONS_ARCHITECTURE.md` ("BR-01 is enforced by convert-to-proposal ...") by analogy and links approval at prompt 10.
- **BR-05** — receipt/commitment balance: mirrored by the SRS bullet *"Receipts and payments must balance to their allocations or requisitions."* The `premium transaction / receipt entity` is `FOReceipt` (+ its allocation rows). This design keeps the obligation context (`OLCommitment`) and the future ledger (`OLPaymentObligation`/`OLPaymentAllocation`, `docs/ORDINARY_LIFE_PHASE2_DOMAIN_CONTRACT.md`) as peer concepts bridged at Prompt 10.

---

## 11. Audit Contract

Every material change writes an `AuditLog` row through `apps.governance.services.audit_service.AuditService` with:

- `actor` (request user resolved via `AuditContext`, or the system user / `SYSTEM` actor for batch),
- **before / after** snapshots (`changed_fields` from `AuditService.changed_fields`),
- `reason` (mandatory reason string for reverse/suspend/waive/cancel/reschedule; a descriptive default for generation/batch),
- `source_channel` (`SYSTEM | API | IMPORT | MANUAL | BATCH | PORTAL | ADMIN`).

Model receivers (`audit_receivers`) cover `OLCommitment`, `OLCommitmentAllocation`, `OLCommitmentNotificationLog` saves so no path can skip auditing (Prompt 10 adds the consistency checker).

---

## 12. Assumptions Register

| # | Assumption | Basis | Revisit |
| --- | --- | --- | --- |
| A1 | BR-03 gates policy issue on settled first premium. | SRS §2.3.1 commitments bullet; analogy to BR-01 handoff rules. | Prompt 10 with business |
| A2 | BR-05 = receipts balance to allocations. | SRS §2.6 + Business rules (receipts/payments must balance). | Prompt 10 |
| A3 | Canonical receipt entity is `FOReceipt`; manual `receipt_reference` accepted until FO exposes allocation endpoints. | `apps/front_office/models.py`. | Prompt 10 |
| A4 | Missing `payment_period_years` implies payment over entire term. | Quotation plan config makes payment period optional. | Prompt 2 schema |
| A5 | `minimum_due_amount` (Zanzibar seed TZS 25,000) satisfies a commitment for batch purity when balance ≤ threshold. | `OLGracePeriod.minimum_due_amount`. | Prompt 4 |
| A6 | Initial status = first active COMMITMENT status by display_order/code. | OL Parameters catalog (seeded PENDING). | Prompt 2 |
| A7 | Allowed transitions may be carried in optional `OLCommitmentStatus.allowed_transitions` JSON (precedent: `OLPolicyStatus`). | Parameter schema precedent. | Prompt 3 |
| A8 | Reversal after grace expiry is blocked by default. | Guard rail for finance; configurable later. | Prompt 3 |
| A9 | Monthly premium schedules step on calendar months; no day-of-month normalization beyond the first due date. | Standard insurance practice. | Prompt 2 |
| A10 | Overpayment beyond balance is an error, not an automatic credit, until credit handling is parameterized. | SRS data integrity + balance rule. | Prompt 3 |

---

## Appendix A — Permissions

| Code | Action stream |
| --- | --- |
| `ol_commitments.view` | list, retrieve, export |
| `ol_commitments.create` | MANUAL creation |
| `ol_commitments.generate` | proposal/policy generation, regeneration |
| `ol_commitments.record_payment` | allocation posting |
| `ol_commitments.reverse` | allocation reversal |
| `ol_commitments.suspend` | suspend / reactivate |
| `ol_commitments.waive` | waive (flags approval) |
| `ol_commitments.cancel` | cancel |
| `ol_commitments.reschedule` | due-date reschedule |

## Appendix B — Parameters consumed (read-only)

| Parameter app | Models consumed |
| --- | --- |
| `apps.ol_parameters` | `OLCommitmentStatus`, `OLGracePeriod`, `OLGracePeriodNotificationSchedule` (Prompt 4), `OLProduct`/`OLPlan` for display |
| `apps.system_parameters` | `NumberingEngine` `OL_COMMITMENT` numbering config (Prompt 2) |
| `apps.front_office` | `FOReceipt` references (Prompt 10) |

## Appendix C — Glossary

- **Commitment** — scheduled parameter-validated premium obligation.
- **Allocation** — a receipt amount posted to a commitment; reversals are inverse allocations linked by `reversal_of`.
- **Grace window** — `(due_date, grace_date]`, payable without penalty.
- **Overdue** — `(grace_date, lapse_date]`, pending, batch-flagged.
- **Lapse** — beyond `lapse_date`; policy-level review event raised.
- **Source channel** — provenance of the operation (`SYSTEM | API | IMPORT | MANUAL | BATCH | PORTAL | ADMIN`).
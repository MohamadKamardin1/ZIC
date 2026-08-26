# Front Office Receipts — Administrator Guide

**Module:** `apps.front_office.receipts` · **Design:** [FRONT_OFFICE_RECEIPTS_DESIGN.md](FRONT_OFFICE_RECEIPTS_DESIGN.md)
**Audience:** system administrators, finance leads, and the operations team.

This guide covers the parameterized configuration surface of the receipts
module, the permission model, seed/release tooling, and operational duties such
as reversing a locked receipt and monitoring the audit trail.

---

## 1. Configuration surface (everything is parameterized)

The module does not hard-code branches, currencies, payment modes, numbering, or
bank accounts. Administrators control behavior through the following records.

### 1.1 Receipt numbering rules — `ReceiptNumberingRule`

| Field | Meaning |
| --- | --- |
| `code` | Rule key, e.g. `RCT_DEFAULT` (receipts) and `RVR_DEFAULT` (reversals). |
| `prefix` | Human prefix, e.g. `RCT`, `RVR`. |
| `sequence_padding` | Zero-padding width, e.g. `6` → `RCT-2026-000001`. |
| `next_sequence` | Next number to allocate; concurrency-safe (atomic claim). |
| `reset_frequency` | `NEVER`, `YEARLY`, `MONTHLY`, `DAILY`. Default `YEARLY`. |
| `effective_from` / `effective_to` | Optional activation window. |
| `is_active` | Inactive rules are never used. |

The numbering service claims a number **atomically** so concurrent postings
never collide; the claim is **idempotent** on retry.

### 1.2 Company bank accounts — `CompanyBankAccount`

Used to identify the **company-side** account on printed receipts.

| Field | Meaning |
| --- | --- |
| `code` | e.g. `TZS_MAIN`. |
| `bank_name`, `account_name`, `account_number` | Account identity; **account number is masked in API responses**. |
| `currency`, `branch` | Optional currency/branch scoping. |
| `is_default`, `is_active` | Default account used when none is chosen. |

### 1.3 Payment-mode rules — `ReceiptPaymentModeRule`

Controls what posting validates for each mode:

| Field | Meaning |
| --- | --- |
| `payment_mode` | `CASH`, `BANK_TRANSFER`, `CHEQUE`, `MOBILE_MONEY`, `CARD`, `OTHER`. |
| `requires_reference` | Whether a payment reference is mandatory. |
| `requires_bank_account` | Whether the payer's bank account is mandatory. |
| `allows_cash` / `allows_card` / `allows_mobile_money` / `allows_bank_transfer` / `allows_cheque` | Capability flags. |
| `min_amount` / `max_amount` | Optional amount bounds enforced at posting. |
| `is_active` | Inactive modes cannot be posted. |

> **Known M-PESA quirk:** receipts store mobile money as the choice value
> `M-PESA`, while the baseline seed keys the rule `MOBILE_MONEY`. The seed flow
> adds an `M-PESA` rule alias so mobile-money receipts post. If you rebuild
> parameters from scratch, re-add the `M-PESA` alias (or record mobile money as
> `MOBILE_MONEY`).

### 1.4 Exchange rates — `ExchangeRate`

`from_currency`, `to_currency`, `rate`, `effective_date`, `source`, `is_active`.
Used to resolve cross-currency allocations when no explicit rate is supplied on
the allocation request. Missing → `RECEIPT_CURRENCY_MISMATCH`.

### 1.5 System parameters consumed

| Parameter | Purpose |
| --- | --- |
| `RECEIPT_REVERSAL_LOCK_DAYS` | Reversal lock window in days (`INTEGER`). `0` disables the lock. |
| `RECEIPT_DEFAULT_CURRENCY` | Default receipt currency (functional currency, `TZS`). |
| `RECEIPT_NUMBERING_CODE` | Which numbering rule to use for receipts. |
| `RECEIPT_EXCHANGE_RATE_STALE_DAYS` | Stale-rate warning threshold. |
| `RECEIPT_BRANCHES`, `RECEIPT_CURRENCIES`, `RECEIPT_PAYMENT_MODES`, `RECEIPT_PARTNERS`, `RECEIPT_SOURCE_MODULES` | Reference-data catalogs surfaced in options; missing/inactive → `RECEIPT_PARAMETER_MISSING` with deep links. |
| `RECEIPT_NUMBERING_RULE`, `RECEIPT_COMPANY_BANK_ACCOUNTS` | Navigation targets for parameter-missing errors. |

---

## 2. Permission model

Nine permissions, namespaced under `front_office.receipts`:

`view`, `create`, `post`, `allocate`, `reverse`, `cancel`, `print`, `import`,
`configure`.

Seed via:

```bash
python manage.py seed_receipt_permissions
```

Three role groups are created (all idempotent):

| Role | Code | Permissions |
| --- | --- | --- |
| Receipt Viewer | `RECEIPT_VIEWER` | `view` |
| Receipt Handler | `RECEIPT_HANDLER` | `view`, `create`, `post`, `allocate`, `print` |
| Receipt Administrator | `RECEIPT_ADMINISTRATOR` | all nine |

`configure` is required for parameter/rule administration. Every money action is
permission-controlled (`HasReceiptPermission`), and unauthorized actors receive
the structured `RECEIPT_PERMISSION_DENIED` error.

---

## 3. Release tooling (Prompt 12)

Three management commands seed and prove the module idempotently. They are safe
to re-run — each fixture is keyed and skipped once present.

```bash
python manage.py seed_receipt_scenarios   # 10 realistic scenarios
python manage.py receipt_failure_proofs   # 5 captured failure proofs (JSON)
python manage.py verify_br03_release      # BR-03 gate verification
```

### 3.1 Seed scenarios

| # | Scenario | Idempotency key | Resulting status |
| --- | --- | --- | --- |
| 1 | Draft manual | `SEED-RCT-01-DRAFT` | `DRAFT` |
| 2 | Posted unallocated cash | `SEED-RCT-02-POSTED` | `POSTED` |
| 3 | Posted partially allocated | `SEED-RCT-03-PARTIAL` | `PARTIALLY_ALLOCATED` |
| 4 | Fully allocated first premium (OL proposal) | `SEED-RCT-04-FIRST-PREMIUM` | `FULLY_ALLOCATED` |
| 5 | Bank transfer with payment reference | `SEED-RCT-05-BANK` | `FULLY_ALLOCATED` |
| 6 | Mobile money (M-PESA) | `SEED-RCT-06-MOBILE` | `POSTED` |
| 7 | Multi-currency allocation (USD → TZS) | `SEED-RCT-07-USD` | `FULLY_ALLOCATED` |
| 8 | Reversed receipt | `SEED-RCT-08-REVERSED` | `REVERSED` |
| 9 | Cancelled draft | `SEED-RCT-09-CANCELLED` | `CANCELLED` |
| 10 | CSV-imported | narration marker `SEED-10-CSV-IMPORT` | `POSTED` |

### 3.2 Failure proofs

Each proof builds a minimal fixture, attempts the operation through the real
service layer, and captures the structured error:

| Proof | Attempted operation | Expected error code |
| --- | --- | --- |
| Missing payment reference | Post `BANK_TRANSFER` without a reference | `RECEIPT_PAYMENT_REFERENCE_REQUIRED` |
| Over-allocation | Allocate more than the unallocated balance | `RECEIPT_OVERALLOCATION` |
| Cross-currency without rate | Allocate KES → TZS with no exchange rate | `RECEIPT_CURRENCY_MISMATCH` |
| Allocation to completed commitment | Allocate to a settled commitment (balance 0) | `RECEIPT_OVERALLOCATION` |
| Reversal after lock period | Reverse a 10-day-old receipt with lock = 5 days | `RECEIPT_REVERSAL_LOCKED` |

### 3.3 BR-03 verification

`verify_br03_release` proves the gate end-to-end:

1. A linked-but-unallocated proposal **cannot convert** →
   `PROPOSAL_FIRST_PREMIUM_NOT_POSTED`.
2. After the first-premium receipt fully allocates the commitment, the proposal
   **converts** to a policy.
3. Reversing that receipt makes the guard **`False` again** — but the issued
   policy is **not** revoked; a re-conversion returns the existing policy.

**Documented operational assumption (post-policy reversal):** reversing a
first-premium receipt after policy issue restores the commitment balance and
resets the guard, but does **not** revoke the policy. Conversion is idempotent
(`converted_policy_id` check precedes the guard). Operators must not reverse
first-premium receipts after policy issue without a compensating adjustment —
this is a documented assumption, not an enforced block.

---

## 4. Operational duties

### 4.1 Adjusting the reversal lock

Set the lock to 5 days:

```python
from apps.system_parameters.models import ParameterGroup, SystemParameter
from apps.system_parameters.services.config_service import ConfigurationService

group, _ = ParameterGroup.objects.get_or_create(
    code="FRONT_OFFICE_RECEIPTS", defaults={"name": "Front Office Receipts"}
)
SystemParameter.objects.update_or_create(
    code="RECEIPT_REVERSAL_LOCK_DAYS",
    defaults={
        "group": group,
        "name": "Receipt reversal lock (days)",
        "value_type": "INTEGER",
        "integer_value": 5,
        "is_active": True,
    },
)
ConfigurationService.invalidate_parameter("RECEIPT_REVERSAL_LOCK_DAYS")
```

Set to `0` to disable the lock, or set `is_active=False` to remove it.

### 4.2 Handling a locked reversal

If an operator must reverse a receipt beyond the lock window, temporarily raise
`RECEIPT_REVERSAL_LOCK_DAYS` (or disable it), reverse, then restore the value.
The reversal and its reason are fully audited.

### 4.3 Monitoring the audit trail

Every lifecycle action writes a governance `AuditLog` row:
`create` (draft), `update`, `post`, `allocate`, `reverse`, `cancel`, `import`
(dry-run / commit), and `print` (generate / download). Events are also emitted to
the durable outbox (`DomainEvent`):

`ReceiptCreated`, `ReceiptPosted`, `ReceiptAllocated`, `ReceiptFullyAllocated`,
`ReceiptReversed`, `ReceiptCancelled`, `ReceiptPrintGenerated`,
`PremiumReceived`, `FirstPremiumReceived`.

### 4.4 Reference-data hygiene

- Keep branches, currencies, payment modes, and partners **active** — posting
  validates reference data and returns `RECEIPT_PARAMETER_MISSING` with a deep
  link when a required catalog entry is missing/inactive.
- Keep company bank accounts `is_active=True` and one `is_default=True`.
- Maintain `ExchangeRate` rows ahead of cross-currency collection days.

---

## 5. Final release verification checklist

- `python manage.py makemigrations --check` — no pending migrations.
- `ruff check apps/front_office` — lint clean.
- `python manage.py seed_receipt_scenarios` — 10/10 scenarios, re-run safe.
- `python manage.py receipt_failure_proofs` — 5/5 caught.
- `python manage.py verify_br03_release` — `BR-03 verification: PASSED`.
- Full backend test suite + PDF receipt tests green.

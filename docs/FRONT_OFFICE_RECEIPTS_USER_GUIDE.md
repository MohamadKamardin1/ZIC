# Front Office Receipts — User Guide

**Module:** `apps.front_office.receipts` · **Design:** [FRONT_OFFICE_RECEIPTS_DESIGN.md](FRONT_OFFICE_RECEIPTS_DESIGN.md)
**Audience:** front-office cashiers, payment handlers, and their supervisors.

This guide explains how to record premium collections as receipts, allocate them
to commitments, reverse mistakes, and print official receipts. It is the
day-to-day companion to the receipts module.

---

## 1. What a receipt is

A receipt records a **collection of money** from a payer (partner) at a branch.
It is not an invoice — it is evidence that money has been received. Receipts are
the vehicle through which premium payments are applied to commitments, including
the **first premium** that unlocks a proposal's conversion to a policy (BR-03).

Every receipt carries:

| Concept | Meaning |
| --- | --- |
| Receipt number | Human identifier, assigned at posting (e.g. `RCT-2026-000001`). Drafts have none. |
| Receipt date | Business date of the collection. |
| Branch | Where the money was received. |
| Payer / partner | Who paid. The partner record is preferred; a payer name is mandatory. |
| Payment mode | `CASH`, `BANK_TRANSFER`, `CHEQUE`, `M-PESA`, `OTHER`. |
| Payment reference | Reference from the payer (bank reference, M-PESA transaction ID). Required by some modes. |
| Currency + exchange rate | Collection currency; foreign collections carry an exchange rate to TZS. |
| Amount | The collection amount in the receipt currency. |
| Status | One of `DRAFT`, `POSTED`, `PARTIALLY_ALLOCATED`, `FULLY_ALLOCATED`, `REVERSED`, `CANCELLED`. |

### Receipt lifecycle

```
DRAFT ──post──▶ POSTED ──allocate──▶ PARTIALLY_ALLOCATED ──allocate──▶ FULLY_ALLOCATED
  │                 │                       │                              │
  └─cancel──▶ CANCELLED                    └────────reverse───────────────▶ REVERSED
```

- **DRAFT** — captured but not yet confirmed. Editable.
- **POSTED** — money confirmed, numbered, immutable core fields.
- **PARTIALLY_ALLOCATED / FULLY_ALLOCATED** — money applied to commitments.
- **REVERSED** — the receipt was reversed (closed, history preserved).
- **CANCELLED** — a draft that was cancelled before posting (closed).

---

## 2. Recording a receipt (draft → post)

1. Open **Front Office → Receipts → New receipt**.
2. Fill in:
   - **Branch** (auto-suggested from the operator's branch).
   - **Payer** — search and select the partner; the payer name is captured.
   - **Receipt date** — defaults to today.
   - **Payment mode** — e.g. `CASH`, `BANK_TRANSFER`, `M-PESA`.
   - **Amount** — the confirmed collection amount (in the receipt currency).
   - **Currency** — defaults to the functional currency `TZS`.
   - **Payment reference** — required for modes that demand one (see validation below).
   - **Narration** — optional context.
3. Save as **Draft**. You can return to edit the draft.
4. Confirm the money and **Post**. Posting:
   - assigns the receipt number,
   - validates the payment-mode rule, active currency, branch, partner,
   - records `posted_by` / `posted_at`,
   - emits a `ReceiptPosted` event and writes an audit trail.
5. Once posted, the core fields (payer, amount, currency, payment mode, receipt
   date, branch) are **immutable**. Further edits are limited to allocation,
   reversal, and print actions.

### Payment-mode validation you will hit

| Payment mode | Requires reference? | Requires bank account? | Minimum amount |
| --- | --- | --- | --- |
| CASH | No | No | 1,000 |
| BANK_TRANSFER | **Yes** | **Yes** | 5,000 |
| M-PESA | **Yes** | No | 1,000 |
| CHEQUE | Yes | No | — |
| CARD | Yes | No | 1,000 |

> Values come from payment-mode rules (`ReceiptPaymentModeRule`), not hard-coded
> code. An administrator can tune them.

---

## 3. Allocating a posted receipt

Allocation applies a receipt's money to a **commitment**. A receipt can be split
across several commitments, but never more than its **unallocated balance**.

1. Open the posted receipt → **Allocate**.
2. The **allocation options** list the payer's open commitments with:
   `commitment_number`, source (proposal / policy), product/plan, due date,
   amount due, amount paid, balance, currency, and status.
3. Enter the **amount** to allocate and an optional narration.
4. Submit. The receipt's allocated/unallocated balance and the commitment's
   balance are both updated, and a `PremiumReceived` event is emitted.

### Rules you will hit

- You cannot allocate more than the receipt's unallocated balance →
  `RECEIPT_OVERALLOCATION`.
- You cannot allocate more than the commitment's outstanding balance →
  `RECEIPT_OVERALLOCATION` (commitment balance check).
- Same-currency allocation needs no exchange rate.
- **Cross-currency** allocation needs an explicit exchange rate (or an active
  configured rate from the `ExchangeRate` table). Missing → `RECEIPT_CURRENCY_MISMATCH`.
- The receipt must be `POSTED` or `PARTIALLY_ALLOCATED` to allocate further.

### First premium (BR-03)

When a commitment is the **first-premium commitment** of an OL proposal and the
allocation brings its balance to zero, the proposal's `first_premium_posted`
guard turns **true**. That is the gate that permits the proposal to convert to a
policy. See [OL_PROPOSALS_RECEIPTS_SEAM.md](OL_PROPOSALS_RECEIPTS_SEAM.md).

---

## 4. Reversing a receipt or an allocation

Reversals never delete history — they write a linked reversal record and restore
commitment balances.

- **Reverse a receipt** (`POSTED` / `PARTIALLY_ALLOCATED` / `FULLY_ALLOCATED`):
  reverses all its allocations, restores each commitment's balance/status, marks
  the receipt `REVERSED`, and emits `ReceiptReversed`.
- **Reverse a single allocation**: reverses one allocation, recalculates the
  receipt's allocated/unallocated amounts and status, and restores the
  commitment balance.
- **Cancel a draft**: a `DRAFT` receipt is cancelled (status `CANCELLED`) with a
  mandatory reason.

Constraints:

- **Reason is mandatory** for every reversal and cancellation.
- A receipt already reversed cannot be reversed again.
- **Lock period**: receipts older than `RECEIPT_REVERSAL_LOCK_DAYS` days cannot
  be reversed → `RECEIPT_REVERSAL_LOCKED`. Operations may override for genuine
  corrections.
- **Post-policy caution**: if a receipt was the first premium that let a proposal
  convert to a policy, reversing it makes the BR-03 guard evaluate `False` again,
  **but it does not revoke the issued policy**. Do not reverse first-premium
  receipts after policy issue without a compensating adjustment.

---

## 5. Printing a receipt

- `POST /receipts/{id}/print/` generates an official PDF through the unified
  print engine and records a `ReceiptDocument`.
- Print rendering depends on status:
  - `DRAFT` — preview only (if permitted).
  - `POSTED` / `PARTIALLY_ALLOCATED` / `FULLY_ALLOCATED` — official receipt.
  - `REVERSED` — official receipt with a **REVERSED** watermark.
  - `CANCELLED` — document with a **CANCELLED** watermark.
- Download uses a signed ticket that expires, so shared links must be regenerated
  from the print screen.

The PDF includes company details, receipt number/date, branch, payer, payment
mode and reference, currency, amount in figures and words, the allocated
commitments table, the unallocated amount, source reference, cashier, posted by,
generated-by timestamp, signature lines, and the template version footer.

---

## 6. Bulk import (CSV)

1. Download the **CSV template** from **Receipts → Import → Template**.
2. Columns: `receipt_date`, `branch_code`, `payer_partner_number`,
   `currency_code`, `payment_mode_code`, `amount`, `payment_reference`,
   `source_module`, `target_commitment_number` (optional), `narration`.
3. **Dry-run** first: the system validates every row and reports row-level and
   field-level errors **without creating anything**.
4. Review the errors, fix the CSV, and re-run the dry-run until clean.
5. **Commit** the batch. Receipts are created and (depending on import mode)
   posted and allocated. Rows are idempotent per `batch_number + row hash`, so
   reprocessing a failed batch is safe.

---

## 7. Common questions

**Q: Can I edit a posted receipt?**
No. Posted receipts are immutable except allocation, reversal, and print
actions. Create a new draft for a corrected collection.

**Q: Why can't I allocate to this commitment?**
The commitment is either already settled (balance `0.00`) or the amount exceeds
its outstanding balance. Check the allocation options list for the real balance.

**Q: Why does the M-PESA receipt fail to post?**
The payment-mode rule requires a **payment reference** for M-PESA. Provide the
M-PESA transaction ID.

**Q: What does "the proposal cannot convert yet" mean?**
BR-03 requires the first premium to be **fully allocated** (the linked
commitment `COMPLETED` with balance zero). Record and allocate the receipt, then
retry the conversion.

**Q: Is a reversed receipt deleted?**
No. Reversals preserve history. The receipt status becomes `REVERSED` and a
linked reversal record is retained for audit.

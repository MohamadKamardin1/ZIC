# OL PROPOSALS — RECEIPTS SEAM CONTRACT

Status: **Contract v1** · Applies to: `apps.ol_proposals` + future `apps.receipts`

This document defines the integration contract between the **proposals** module
and the **future receipts** module for the first-premium payment lifecycle
(BR-03). The goal is a clean ownership boundary: **receipts write allocations;
proposals only read status.**

---

## 1. Ownership boundary

| Capability | Owner | Detail |
| --- | --- | --- |
| Create/link the first-premium commitment | Proposals | `link_first_premium_commitment` on `ProposalPaymentReady` |
| Post a receipt | Receipts (future) | Writes `OLCommitmentAllocation` rows |
| Reverse an allocation | Receipts (future) | Reversals link to the original allocation (`reversal_of`) |
| Recompute commitment amounts | Commitments | `OLCommitment.save` → `recompute_balance()` |
| Read payment status | Proposals / Policies | `first_premium_posted`, `first_premium_status` (read-only) |

The proposals module never writes to a commitment after linkage. All payment
status surfaced to proposals flows is read directly from the linked
`OLCommitment` and its `OLCommitmentAllocation` children.

---

## 2. Linked first-premium commitment

On a successful `POST .../mark-payment-ready/` (all checklist items pass) the
proposal module:

1. Emits `ProposalPaymentReady` (durable outbox `DomainEvent`).
2. Calls `link_first_premium_commitment` which creates (idempotently) an
   `OLCommitment` with:
   - `source_type = "PROPOSAL"`
   - `source_content_type / source_object_id` → the `OLProposal`
   - `source_reference` → the proposal number
   - `installment_number = 1`, `installment_count = 1`
   - `premium_amount` from the selected plan config (fallback: financial snapshot)
   - `due_date = today`
3. Stores the reference on `OLProposal.first_premium_commitment`.
4. Emits `CommitmentGenerated` so downstream consumers observe the creation.

Reading lanes:

```python
from apps.ol_proposals.services.first_premium_service import (
    first_premium_posted,     # bool — BR-03 airtight guard
    first_premium_status,     # dict — UI/API payload
    ensure_first_premium_posted,  # raises PROPOSAL_FIRST_PREMIUM_NOT_POSTED
)
```

---

## 3. BR-03 guard

`first_premium_posted(proposal)` returns `True` **only** when the linked
first-premium commitment satisfies:

- `status == "COMPLETED"` **and**
- `amount_paid + amount_waived >= premium_amount` (fully allocated /
  zero balance).

Partial payments, reversals, and missing commitments all evaluate `False`.
The guard is deliberately allocation-aware: it never trusts a status string
alone. It is the single source of truth reused by the receipt flow (to decide
when a receipt fully discharges the commitment) and by the future policies
module (to gate conversion via BR-03).

---

## 4. Receipts write path (future module)

The receipts module will allocate money to a commitment by creating

```
OLCommitmentAllocation
  commitment          -> linked first-premium commitment
  receipt_reference   -> unique receipt number (unique per commitment)
  amount              -> positive decimal > 0
  payment_mode        -> CASH / M-PESA / BANK_TRANSFER / ...
  currency            -> ISO 4217 code
  allocated_at        -> payment timestamp
  allocated_by        -> actor who posted the receipt
  reversal_of         -> original allocation being reversed (for reversals)
```

`OLCommitmentAllocation` constraints guarantee: positive amounts, positive
exchange rate, unique non-reversal receipt per commitment, and reversal
self-linking prohibition. After each write the receipts module must re-save the
parent commitment (or call `recompute_balance`) so `balance` stays consistent —
or rely on the commitments module to recompute on next save.

---

## 5. PremiumReceived event contract

The future receipts module emits one durable outbox event on every allocation.
Proposals, policies, reports, and the portal consume it asynchronously.

### Contract

```json
{
  "event_type": "PremiumReceived",
  "aggregate_type": "OLCommitment",
  "aggregate_id": "<commitment-uuid>",
  "payload": {
    "proposal_number": "OLP-2026-00001",
    "commitment_number": "OLC-2026-00001",
    "receipt_reference": "RCT-2026-00042",
    "amount": "50000.00",
    "currency": "TZS",
    "payment_mode": "M-PESA",
    "allocated_at": "2026-08-23T10:00:00Z",
    "allocated_by": "<actor-id or null>",
    "source_channel": "PORTAL",
    "reason": "",
    "reverse_of": null,
    "from_status": "PARTIALLY_PAID",
    "to_status": "COMPLETED"
  },
  "status": "PENDING",
  "occurred_at": "2026-08-23T10:00:00Z"
}
```

### Field meaning

| Field | Meaning |
| --- | --- |
| `premium_amount` / `amount_due` | Outstanding premium for the commitment (from `OLCommitment.premium_amount`) |
| `amount_paid` | Cumulative paid on the commitment |
| `balance` | `premium_amount − amount_paid − amount_waived` |
| `from_status` | Commitment status before allocation, `to_status` after |
| `reverse_of` | Non-null when the event reverses an earlier allocation |

### Publishing rule

Receipts MUST publish `PremiumReceived` in the same database transaction that
inserts the `OLCommitmentAllocation` so the outbox and ledger stay consistent.
Reversals publish the same event with `reverse_of` populated and a negative
effect on `amount_paid`.

---

## 6. Status payload surfaced to proposals

`GET /api/v1/ol-proposals/proposals/{id}/first-premium/` and the proposal detail
payload (`first_premium`) expose only read-only summary:

```json
{
  "linked": true,
  "commitment": {
    "commitment_number": "OLC-2026-00001",
    "status": "COMPLETED",
    "amount_due": "50000.00",
    "amount_paid": "50000.00",
    "balance": "0.00",
    "payment_modes": ["M-PESA"],
    "payment_mode": "M-PESA",
    "last_payment_date": "2026-08-23T10:00:00Z",
    "allocations": [
      {
        "receipt_reference": "RCT-2026-00042",
        "amount": "50000.00",
        "payment_mode": "M-PESA",
        "currency": "TZS",
        "allocated_at": "2026-08-23T10:00:00Z"
      }
    ]
  },
  "first_premium_posted": true,
  "next_actions": ["Proceed to policy conversion (first premium is fully allocated)."]
}
```

`next_actions` guides the operator: record a receipt in Front Office while the
commitment is unsettled, or proceed to conversion once fully allocated.
# ZIC OL Commitments — User Guide

## What is a commitment?

A commitment is a scheduled premium obligation for an Ordinary Life policy or proposal:

- **Proposal first premium** — created when a payment-ready proposal approves; must be settled before the policy issues.
- **Policy renewal schedule** — one commitment row per instalment across the renewal schedule.
- **Manual** — operator-created obligation (arrears, corrections).

Every commitment carries a due date, amount due, amount paid, balance, grace/lapse dates, a parameter-driven status, and its own audit trail.

## UI references (frontend)

- **Register** — `Ordinary Life → Commitments`: overview cards, filters (status/source/product/currency/due-date/balance>0), quick chips (Overdue, In Grace, Outstanding), CSV export, bulk import.
- **Run Overdue Processing** — safe, idempotent batch: marks past-grace commitments overdue, writes grace notifications, flags lapse reviews. Results show processed / marked overdue / notifications created / lapse reviews flagged.
- **Lapse review queue** — commitments past their lapse date needing a policy review.
- **Detail** — payments/allocation history, status history (actor, reason, channel), notifications; actions available only when the state+permission allow them.
- **Partner portal** (`Portal → Commitments`) — read-only, partner-scoped; to pay or dispute, contact your ZIC representative or raise a ticket.

## Error codes and how to resolve

| Code | Meaning | What to do |
| --- | --- | --- |
| `PARAMETER_MISSING` | Required OL parameter (e.g. grace period) not configured. | Use the deep link to **Ordinary Life Parameters > Policy Setup**, enable the row, retry. |
| `COMMITMENT_DUPLICATE` | The source already generated this commitment. | Open the existing commitment and pay against it. |
| `COMMITMENT_OVERPAYMENT` | Payment above the outstanding balance. | Adjust the amount, or record the surplus as a credit. |
| `COMMITMENT_INVALID_TRANSITION` | Action not allowed from the current state. | Follow the allowed actions listed in the error. |
| `COMMITMENT_ALREADY_COMPLETED` | Commitment fully settled. | No payment is due; review allocation history. |
| `COMMITMENT_NOT_FOUND` | Record does not exist. | Check the number and filters. |
| `CURRENCY_MISMATCH` | Cross-currency receipt without a rate. | Provide the exchange rate (1 receipt currency in commitment currency). |
| `RECEIPT_REFERENCE_INVALID` | Receipt reference not recognised. | Use a valid front-office receipt or the manual reference format. |
| `GRACE_EXPIRED_REVERSAL_BLOCKED` | Reversal after the grace window. | Raise a finance review instead. |
| `PERMISSION_DENIED` | Missing `ol_commitments.*` permission. | Ask an administrator to assign the role. |

## Audit

Every status change, payment, reversal, and batch action writes an audit entry with actor, before/after state, reason, and source channel (`API`, `ADMIN`, `IMPORT`, `BATCH`, `PORTAL`, etc.), and publishes a domain event (e.g. `CommitmentGenerated`, `CommitmentPaymentAllocated`, `CommitmentOverdue`, `CommitmentCompleted`) to the outbox.

Detailed engineering contract: `frontend/docs/COMMITMENTS_UI_GUIDE.md` and `docs/OL_COMMITMENTS_DESIGN.md`.
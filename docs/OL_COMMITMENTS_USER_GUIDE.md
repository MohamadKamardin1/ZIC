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

## Print Commitment Statement

From a commitment detail page, open **Documents** and choose **Generate commitment PDF** when a new statement is required. Existing instances show the approved template version, generating actor, generation time, and page count. Use **Preview** to view the PDF inside the authenticated application, **Download** to save it through the secure document client, or **Open in new tab** when a short-lived signed ticket is available.

Do not copy the protected `/api/v1/documents/instances/.../download/` URL into a browser tab. If a session has expired, the application refreshes the access token once and retries automatically. If the retry fails, sign in again and reopen the Documents tab. A stale signed ticket should be replaced by returning to the instance list and generating a fresh link. Branding or pending-template messages link to System Parameters → Document Branding.

| Print message | Meaning | Resolution |
| --- | --- | --- |
| `TEMPLATE_PENDING` | The Commitment Statement or requested future document has no approved active layout. | Complete the document template/branding setup in System Parameters, then generate again. |
| `BRANDING_NOT_CONFIGURED` | No usable active branding version or legacy fallback value is available. | Save company details, logo, and colors at System Parameters → Document Branding. |
| `Session expired — sign in again` | Bearer authentication failed after one refresh retry. | Sign in again; never work around the protection with a raw URL. |
| `The document download ticket has expired` | The signed five-minute ticket is no longer valid. | Generate a new instance link from the Documents tab. |

The generated statement records `DOCUMENT_GENERATED` and the later preview/download event with the actor, source transaction, template version, correlation ID, and API source channel. The short-lived ticket path additionally records ticket issuance and ticket download.

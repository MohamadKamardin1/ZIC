# Ordinary Life Loans UI Guide

## Scope and navigation

The Ordinary Life Loans workspace is available at `/ordinary-life/loans` for staff users with the `ol_loans.view` permission. A staff user can open a row from the server-side Loans register and continue to `/ordinary-life/loans/{loanId}`. The identifier in that route is a resource key used for API resolution; all visible loan, policy, partner, product, agent, and branch values are rendered from human-readable display fields such as `loan_number`, `policy_number`, and `*_display`.

Partner users use the scoped read-only workspace at `/portal/loans`. The portal lists only loans belonging to the authenticated partner and exposes a detail view by loan number at `/portal/loans/{loanNumber}`. Staff-only servicing controls are not rendered in the partner portal, even when a partner can view balances or repayment schedules.

## Staff screens

The Loans list provides server-side search, status/date/default filters, KPI cards, CSV export, and a row action menu. Row actions are available only when both conditions are true: the backend includes the action in `allowed_actions`, and the current IAM metadata grants the corresponding `ol_loans.*` permission.

| Staff action | Route/API | Required permission | UI result |
| --- | --- | --- | --- |
| View | `/ordinary-life/loans/{id}` | `ol_loans.view` | Opens the loan detail workspace. |
| Request Loan | `/ordinary-life/loans` | `ol_loans.request` | Opens the three-step policy selection, loan details, and summary modal. |
| Disburse | `/ordinary-life/loans/{id}?action=disburse` | `ol_loans.disburse` | Opens the settlement preview and strict confirmation modal. |
| Repay | `/ordinary-life/loans/{id}?action=repay` | `ol_loans.repay` | Opens the verified repayment form and immutable-history confirmation. |
| Offset | `/ordinary-life/loans/{id}?action=offset` | `ol_loans.offset` | Opens claim, surrender, or maturity payout reconciliation. |
| Print | `/ordinary-life/loans/{id}?tab=documents` | `ol_loans.print` | Opens the authenticated branded PDF Documents tab. |

The detail page contains Overview, Repayment Schedule, Repayment History, Interest Accrual History, and Documents tabs. Schedule and history data are read-only, paginated, and sourced from the backend. The Documents tab uses the shared authenticated document pipeline for both the Loan Agreement and Repayment Schedule. Preview is loaded as an authenticated blob; Download uses the authenticated client; Open in new tab uses the short-lived signed ticket returned by the print endpoint.

## Controlled financial actions

Financial forms are intentionally explicit. Each modal displays the current loan status and relevant balance or settlement details, validates the input before making a request, sends an idempotency key, and requires a confirmation checkbox before submission. A successful mutation closes the modal, invalidates the loan detail and list queries, updates the status/balance view, and shows a success toast.

### Request Loan

The request flow starts by searching for a policy. The backend eligibility preflight supplies the policy status, cash-value snapshot, available limit, minimum and maximum amounts, repayment modes, and approval requirement. The client uses that response for guidance only; the final request service remains authoritative. A request above the available limit displays `Loan amount exceeds available cash value limit.` with steps to reduce the amount and review the cash-value/setup configuration. A lapsed or otherwise ineligible policy displays `Policy is not eligible for loans.` with steps to choose an eligible policy or resolve the lifecycle/configuration issue.

### Disbursement

Disbursement shows the approved loan amount and the backend-selected settlement destination. The user must choose an active outgoing payment mode and confirm that the approved amount may be released to the displayed destination. The backend rechecks approval state, payment configuration, currency, idempotency, and duplicate settlement protection.

### Repayment

Repayment requires a positive amount no greater than the current outstanding balance, a verified payment mode, and a receipt or approved manual reference. Partial repayment leaves the loan in a partially repaid state; repayment of the remaining balance transitions the loan to settled when the backend rules permit it. The posted payment is retained in immutable repayment history with allocation and source-channel metadata.

### Offset

Offset requires a source type (`CLAIM`, `SURRENDER`, or `MATURITY`), a source transaction reference, a positive payout amount, and strict confirmation. The backend caps the applied offset at the outstanding balance and preserves any remaining payout. The source reference is used for idempotency and audit traceability.

## Error Coach resolution codes

The UI presents backend errors as an Error Coach with an explanation and concrete resolution steps. The following codes are expected in the Loans workflows.

| Error code or message | Meaning | Recommended resolution |
| --- | --- | --- |
| `LOAN_EXCEEDS_LIMIT` | Requested amount is greater than the effective available loan limit. | Reduce the amount and review the policy cash value and Loan System Setup. |
| `LOAN_INELIGIBLE` | The policy status, product capability, or effective setup does not permit a loan. | Select an Active or Paid-up eligible policy, or ask Loan Operations to correct configuration. |
| `LOAN_OVERBALANCE` | Repayment or offset exceeds the current outstanding balance. | Refresh the detail page and enter an amount no greater than the displayed balance. |
| `LOAN_NOT_APPROVED` | Disbursement was attempted before approval or after a lifecycle transition. | Review approval status and retry only after the loan is approved. |
| `LOAN_ALREADY_DISBURSED` | A second disbursement was attempted for the same loan. | Review the disbursement and settlement records; do not retry blindly. |
| `LOAN_INVALID_SOURCE` | Offset source type or reference cannot be linked to the loan/policy. | Choose the correct claim, surrender, or maturity reference. |
| `AUTHENTICATION_REQUIRED` | The session is expired or the authenticated request was rejected. | Sign in again and retry; the document client performs one refresh retry where supported. |
| `DOCUMENT_RENDER_FAILED` / `TEMPLATE_PENDING` | A branded loan document could not be rendered or is not yet configured. | Ask an authorized administrator to configure the active document template and branding, then retry. |

## Permissions and audit behavior

The frontend never treats a visible button as sufficient authorization. For staff actions it intersects the backend `allowed_actions` array with IAM permission metadata. The backend repeats the authorization check and records the action with actor, before/after state, correlation ID, reason, and source channel. Browser actions use `WEB`; partner-originated requests use `PORTAL`; scheduled or settlement-originated writes use the backend-defined system or batch source channel.

Every financial action should be traceable in the loan audit timeline. The release regression suite also asserts that request, disbursement, repayment, offset, and document-generation actions produce an auditable source-channel entry and that user-facing URLs and labels do not expose UUIDs where a loan number, policy number, or display label is available.

## Verification

Run the focused browser release coverage from the frontend workspace:

```bash
cd insurance-dashboard-ui
pnpm exec playwright test e2e/ol-loans-prompt10.spec.ts --reporter=line
```

Run all browser scenarios, including quotation, policy, commitment, portal, and unified print regressions:

```bash
pnpm test:e2e
```

The deterministic E2E fixture mirrors the real API envelope, permission matrix, action payloads, Error Coach messages, secure PDF response, and audit source-channel evidence. Backend verification must be run against the seeded OL Loans scenarios before release; the browser suite then verifies the user-visible contract and action gating.

## Accessibility and responsive behavior

Action forms use labeled controls, visible focus rings, keyboard-operable buttons, strict confirmation checkboxes, and error regions that remain associated with the relevant field. The shared legacy modal now exposes `role="dialog"`, `aria-modal="true"`, a title association, and an accessible close label. Loan action footers use flex wrapping so controls remain usable on narrow screens. The portal intentionally keeps the same readable labels and schedule tables while removing staff-only actions.

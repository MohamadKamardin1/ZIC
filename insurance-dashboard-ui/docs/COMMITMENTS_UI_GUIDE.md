# ZIC Commitments — UI Guide

Applies to the Ordinary Life Commitments module UI (frontend). Companion backend design: `docs/OL_COMMITMENTS_DESIGN.md`; user-facing rules: `docs/OL_COMMITMENTS_USER_GUIDE.md`.

## Screen map

| Route | Screen | Notes |
| --- | --- | --- |
| `/ordinary-life/commitments` | Commitments register | KPIs (total due, outstanding, overdue, collected) + staff oversight cards; DataTable (filters: status, source type, product, currency, due-date range, balance>0; quick chips Overdue/In Grace/Outstanding; search by commitment/partner/policy; Export CSV); Import CSV (dry-run first), Generate Commitments, Create New Commitment, Run Overdue Processing (permission-gated), lapse-review queue, import history. |
| `/ordinary-life/commitments/:id` | Commitment detail | Header (number, partner, product/plan, status, currency, balance, due/grace/lapse warning); payment progress + allowed-action bar; tabs Overview / Allocations / History / Notifications. |
| `/portal/commitments` , `/portal/commitments/:id` | Partner portal (read-only, partner-scoped) | No actions; help banner + "Raise Ticket" link to `/tickets`; errors sanitized. |
| App dashboard | `CommitmentDashboardCards` | Overdue count, outstanding premium, approvals pending (waivers); deep links to filtered registers. |
| Top-bar bell | Notification center | `CommitmentOverdue` feed items with deep links to commitment details. |

## Error-code resolution table

| Code | What it means | Resolution (UI) |
| --- | --- | --- |
| `PARAMETER_MISSING` | Required OL parameter missing (grace period, status). | ErrorCoach → "Open configuration" deep link to OL Parameters > Policy Setup. |
| `COMMITMENT_DUPLICATE` | Commitment already exists for the source/installment. | ErrorCoach → "View existing" link to the existing commitment. |
| `COMMITMENT_OVERPAYMENT` | Payment exceeds the outstanding balance. | Adjust amount, or record the surplus as a credit; ErrorCoach lists steps. |
| `COMMITMENT_INVALID_TRANSITION` | Action not allowed from the current status. | ErrorCoach lists `resolution_steps` (allowed transitions). |
| `COMMITMENT_NOT_FOUND` | Commitment does not exist. | Verify the number/filters; portal errors are sanitized to a generic message. |
| `CURRENCY_MISMATCH` | Cross-currency payment without a rate. | Provide an exchange rate in the Record Payment modal. |
| `RECEIPT_REFERENCE_INVALID` | Receipt reference not recognized. | Use a front-office receipt or the documented manual reference. |
| `GRACE_EXPIRED_REVERSAL_BLOCKED` | Reversal attempted beyond the grace window. | Raise a finance review instead. |
| `PERMISSION_DENIED` / `FORBIDDEN` | Missing `ol_commitments.*` permission. | Request the role under User Management. |

## Accessibility

- ErrorCoach: `role="alert"`, `aria-live="assertive"`.
- Toasts: `aria-live="polite"` region.
- Modals: `role="dialog"`, `aria-modal`, focus-first on open, Tab trap, Escape closes, scroll lock.
- ReasonField / SmartSelect / SearchableSelect: `aria-invalid`, `aria-describedby`, labelled controls.
- Dark theme: all screens use design tokens that re-map under `[data-theme="dark"]`.

## E2E

`e2e/ol-commitments.spec.ts` covers list KPIs/filters/chips/export, generation dry-run + execute, PARAMETER_MISSING deep link, import dry-run errors + commit, detail tabs + payment, overpayment ErrorCoach, invalid-transition ErrorCoach, overdue processing + bell deep link, and portal read-only scoping (API-mocked, no backend required).

# Ordinary Life Withdrawals UI Guide

## Purpose

The Ordinary Life Withdrawals workspace supports controlled withdrawal servicing from policy discovery through request submission, approval, payout, reversal, partner-portal review, and authenticated statement printing. The UI is backend-driven: policy eligibility, available limits, fees, net payout, status transitions, permissions, and audit evidence are calculated or authorized by the Django APIs rather than duplicated in the browser.

## Staff routes

| Route | Purpose | Required access |
|---|---|---|
| `/ordinary-life/withdrawals` | Staff register with KPIs, server-side search/filtering, row actions, and request entry | `ol_withdrawals.view` |
| `/ordinary-life/withdrawals/new?policy_id=<internal-id>` | Three-step request wizard: policy selection, amount and fees, summary and policy impact | `ol_withdrawals.request` |
| `/ordinary-life/withdrawals/:id` | Master-detail workspace with Overview, Breakdown, Payments, Documents, and Audit tabs | `ol_withdrawals.view` |
| `/ordinary-life/withdrawals/:id?action=<action>` | Opens a controlled lifecycle confirmation dialog | Action-specific permission |

The browser may use an internal resource identifier in a route or API request, but all visible labels are sourced from backend display fields. Withdrawal numbers, policy numbers, policyholder names, product names, branch names, agent names, and payment-mode labels are shown instead of UUIDs.

## List and KPI flow

The register loads KPI data and the paginated withdrawal table independently. Search, status, product, branch, agent, requested-date range, and pending-approval filters are forwarded to the backend. The KPI query is refreshed when the active filter set changes, so the cards remain aligned with the table scope.

Each row displays the withdrawal number, policy, policyholder, product, gross amount, fee amount, net payout, status, requested date, and backend-provided allowed actions. The action menu is the intersection of the row’s server-provided action matrix and the user’s access metadata. `View` is available to viewers; approval, rejection, payout, cancellation, reversal, and print actions require their corresponding permissions.

## Request flow

1. Select **Request Withdrawal** and search active policies returned by the withdrawal options endpoint.
2. Select a human-readable policy result. The wizard requests eligibility from the policy finance API and shows policy status, cash value, loan balance, and the backend-computed Available Limit.
3. Continue to **Amount & Fees**. Enter a positive amount no greater than Available Limit and provide a reason. The fee and estimated net payout are calculated by the backend estimate endpoint. The UI does not treat its display fallback as authoritative.
4. Continue to **Summary & Impact**. Review gross amount, estimated fee, net payout, policy status, reason, and the cash-value impact alert.
5. Submit the request. The client sends an idempotency key and navigates to the returned withdrawal detail resource after a successful `201` response.

The backend revalidates eligibility, cash value, active loans, fee parameters, permissions, and duplicate-submission protection. A failed submission returns an ErrorCoach with the backend message, field-level guidance where available, and actionable resolution steps.

## Lifecycle actions

| Status | Typical actions |
|---|---|
| Requested | Approve, Reject, Cancel, Print |
| Approved | Process Payout, Cancel, Print |
| Processing | Cancel, Print |
| Paid | Reverse, Print |
| Reversed | View, Print |
| Declined | View, Print |
| Cancelled | View, Print |

Approval and rejection require controlled reasons. Payout processing requires a payment mode and receipt reference. Cancellation and reversal require reasons; reversal also displays an explicit warning that policy cash value will be restored. After a successful mutation, the detail page refreshes and presents a status-specific success toast. Backend action responses and audit events are the source of truth.

## Detail workspace

The detail header shows the withdrawal number, status badge, policy link, policyholder, product, currency, gross amount, fee amount, net payout, and lifecycle timestamps. The **Overview** tab shows policy context and the status timeline. **Breakdown** shows cash-value before/after, gross withdrawal, fee rate and basis, net payout, sum-assured adjustment, and calculation audit events. **Payments** is read-only. **Audit** shows actor, source channel, reason, and timestamp for recorded events.

If the withdrawal is `REVERSED`, the workspace displays a visible Reversed watermark and the restored cash-value state. Empty or failed subresources use teachable loading, empty, or ErrorCoach states rather than blank panels.

## Documents and print

The **Documents** tab uses the unified authenticated document pipeline. **Print Statement** requests an `OL_WITHDRAWAL_STATEMENT` document, stores the source transaction and template version, and returns a preview URL/blob and short-lived signed download ticket. Preview renders an authenticated blob-backed PDF. Download fetches the PDF through the authenticated client. Open in New Tab is allowed only when the backend supplies a signed ticket URL.

The UI never opens a protected raw `/api/` URL as a normal unauthenticated navigation. Missing templates, branding, storage failures, expired tickets, and session expiry are surfaced through ErrorCoach resolution steps. Cancelled and reversed statements carry a visible status watermark.

## Partner portal

Partner users access `/portal/withdrawals`. The backend scopes results to visible partner relationships; client-side filtering is not used as a security boundary. Portal records expose policy-safe financial values and human-readable labels. Sensitive fee fields are omitted unless the backend explicitly authorizes disclosure. Portal users may review their own scoped requests and use the limited request flow where `request_allowed` is true, but cannot approve, reject, process payouts, cancel staff requests, reverse withdrawals, or access staff-only audit controls.

## Common errors

| Error or state | Meaning | User action |
|---|---|---|
| `WITHDRAWAL_LIMIT_EXCEEDED` | Requested amount is above the backend Available Limit | Reduce the amount to the displayed limit and retry. |
| `REASON_REQUIRED` | A controlled action was submitted without its mandatory reason | Enter a clear operational reason in the confirmation dialog. |
| `POLICY_NOT_ELIGIBLE` | Policy status, cash value, loan, or parameter rules prevent a withdrawal | Review policy status and servicing configuration. |
| `TEMPLATE_PENDING` | Approved withdrawal statement template is unavailable | Ask System Administration to activate the document template. |
| `DOCUMENT_RENDER_FAILED` | HTML/PDF rendering or storage failed | Retry; if persistent, provide the correlation ID to System Administration. |
| Session expired | Authenticated document request could not be authorized | Sign in again and retry; no raw protected URL is exposed. |

## Accessibility and interaction standards

All primary controls are native buttons or links with visible focus rings and descriptive names. Tables include captions, status labels remain textual in addition to color, modal actions are keyboard reachable, and responsive action groups wrap rather than overlap. Financial values preserve decimal precision and include their currency code for screen-reader clarity.

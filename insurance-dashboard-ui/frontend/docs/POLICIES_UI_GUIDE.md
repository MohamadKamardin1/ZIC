# Ordinary Life Policies UI Guide

This guide describes the Ordinary Life Policies staff workspace and the partner portal delivered by the OL Policies UI series. The frontend is a React, TypeScript, TanStack Query, and React Router application that uses the shared ZIC design system and the authenticated `/api/v1/` API client.

## Staff routes

| Route | Purpose | Access |
| --- | --- | --- |
| `/ordinary-life/policies` | Table-first policy register with KPI cards, filters, search, export, and server-authorized row actions | `ol_policies.view` |
| `/ordinary-life/policies/new` | Two-step policy issuance from a proposal that has passed the first-premium gate | `ol_policies.create` |
| `/ordinary-life/policies/:policyId` | Master-detail contract view with Overview, Members & Riders, Endorsements, Financials, Documents, and Audit tabs | `ol_policies.view` |

The policy list and detail pages never render raw foreign-key UUIDs. Human-readable `*_display` values are preferred, and the shared `renderFk` utility suppresses UUID-like values when a display label is unavailable.

## Detail page behavior

The detail header shows the policy number, lifecycle status, currency, term, commencement and maturity dates, policyholder, agent/intermediary, linked proposal, and contract snapshot. Status history and audit entries are displayed as a timeline. Members, riders, benefits, endorsement history, loans, withdrawals, and generated documents are loaded through typed query hooks and refresh after successful mutations.

Action visibility is intentionally two-dimensional. A control is shown only when the backend response includes the action in `allowed_actions` **and** the signed-in user has the matching IAM permission. The canonical mappings are `endorse → ol_policies.endorse`, `loan`, `withdraw`, and `surrender → ol_policies.service`, `paid-up → ol_policies.service`, `cancel → ol_policies.cancel`, `reinstate → ol_policies.reinstate`, and `print → ol_policies.print`.

### Terminal actions

Surrender, paid-up conversion, and cancellation are presented as explicit confirmation dialogs. Surrender and cancellation require a reason; all three terminal flows require a strong confirmation checkbox. Surrender is described as a server-valued request and correctly presents `SURRENDER_PENDING` until settlement rather than claiming that payment has completed. Paid-up conversion is limited to lapsed policies and explains that the configured paid-up rate can reduce remaining cover. Cancellation displays the returned free-look refund or requisition metadata when supplied by the server.

Loan and withdrawal requests also validate amounts in the browser for immediate guidance, while the backend remains authoritative for product flags, cash value, outstanding balances, and configured limits. Errors use `ErrorCoach` so the user receives the server message, resolution steps, field details, and configuration deep links when available.

## Authenticated policy documents

The `Print Contract` action opens `PolicyPrintPreviewModal`. It calls the canonical policy print mutation, expects a document instance and short-lived signed URL, then retrieves the PDF through the authenticated document client. The result is rendered in an object URL-backed iframe; it is never loaded by navigating a raw `/api/` URL without authentication.

The Documents tab uses the shared document-instance panel to show generated policy documents, template name/version, actor, generated time, page count, and authenticated preview/download actions. A missing template, branding configuration, storage failure, expired ticket, or session expiry is surfaced through `ErrorCoach` rather than a blank preview. Cancelled policies receive a visible `CANCELLED` watermark in the preview.

## Partner portal

The read-only partner routes are `/portal/policies` and `/portal/policies/:id`. They call the partner-scoped policy endpoints and therefore do not reuse the unrestricted staff register. The backend filters both list and detail responses to `request.user.visible_partners()`; a policy identifier is included in the safe portal payload only to support navigation to the scoped detail route.

The portal contains a table of the partner’s policies and a read-only detail view with Overview, Members, and Documents sections. Staff-only controls such as Endorse, Loan, Withdraw, Surrender, Paid-Up, Cancel, Reinstate, and Print are not rendered in the portal. The page includes the exact guidance **“Contact agent for changes.”** and a ticket link for support.

## Issuance flow

Staff select an eligible proposal from the New Policy wizard. Only proposals in `AWAITING_FIRST_PREMIUM` or `PAYMENT_READY` are displayed. The wizard repeats the first-premium readiness check in the interface, but the server performs the final BR-03 validation at `POST /api/v1/ol/policies/issue/`. Success navigates to the immutable policy detail page and refreshes the policy register and KPI queries.

## Verification and troubleshooting

The Prompt 10 browser suite covers proposal-to-policy issuance, policy detail rendering, endorsement creation, loan validation and success, surrender confirmation, authenticated contract preview, and partner read-only behavior. Unit and MSW tests cover portal normalization, secure document metadata, policy print response envelopes, lifecycle handlers, and UUID-safe rendering.

| Symptom | Resolution |
| --- | --- |
| Policy actions are missing | Confirm the backend `allowed_actions` value and the matching IAM permission. Superuser status does not replace a malformed backend action response. |
| Issuance button remains disabled | Select a proposal, advance to Confirm & Issue, and ensure the first-premium commitment is fully posted. |
| Loan request is rejected | Reduce the amount to the displayed available loan limit or reinstate a lapsed policy first. |
| Surrender value is not shown | The issued snapshot did not supply an estimate. Submit the request only when appropriate; the server confirms the payable value. |
| PDF preview reports no secure URL | Retry once. If the issue persists, check active template, branding, storage, and `ol_policies.print` permission. |
| Portal policy is not found | The policy is not linked to the signed-in partner account, or the portal session has expired. |

All list/detail and portal data is fetched through shared API and query layers. No business calculations are performed in the client beyond display formatting and immediate input validation.

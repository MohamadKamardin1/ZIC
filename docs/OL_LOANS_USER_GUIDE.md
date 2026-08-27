# ZIC Ordinary Life Loans User Guide

## Purpose

The Ordinary Life (OL) Loans module allows an authorized ZIC user to request, approve, disburse, service, settle, default, and offset a policy-backed loan. The policy, product, OL Loan System Setup, and OL Loan Interest Control records remain authoritative. The screen does not infer eligibility from hardcoded client-side rules.

> A loan is secured against the policy value available at the time of request. Every financial action is atomic, idempotent, permission-controlled, and auditable.

## Loan lifecycle

| State | Meaning | Typical next action |
| --- | --- | --- |
| Requested | The request passed policy and parameter checks and is waiting for approval or disbursement workflow. | Approve or reject |
| Approved | An authorized approver accepted the request. | Disburse |
| Active | Funds were released and a contractual repayment schedule exists. | Repay, accrue interest, detect default, or offset |
| Partially repaid | One or more repayments reduced but did not clear the balance. | Repay the remaining balance |
| Settled | Repayment reduced the outstanding balance to zero. | No further financial action |
| Defaulted | A scheduled amount exceeded the effective grace period plus penalty period. | Reconcile, collect, or offset |
| Offset on surrender, maturity, or claim | A policy payout was used to deduct the loan balance. | Review the remaining payout and settlement record |
| Closed | The loan was fully cleared through an offset or an approved closure workflow. | No further financial action |
| Rejected | The request was declined with a recorded reason. | Create a new request only after the underlying issue is resolved |

`DISBURSED` is a recorded release event. `ACTIVE` is the operating state after the repayment schedule has been generated.

## Requesting a loan

Open the policy’s loan action and confirm that the policy is Active or Paid-up, the product permits loans, and the current cash value is sufficient. Select a repayment mode and term offered by the active Loan System Setup. Enter a positive amount and a clear business reason. Submit the request with the user interface; the platform supplies an idempotency key so a network retry does not create a second request.

If the effective setup requires approval, the request remains in **Requested** and a shared approval item is created. The approver must review the amount, policy, cash-value snapshot, repayment terms, and reason before choosing Approve or Reject.

## Disbursing an approved loan

The disbursement action uses the configured outgoing payment mode and active company bank account. The module creates one front-office requisition, one immutable disbursement record, and the complete repayment schedule in one transaction. A successful response includes the human-readable loan number, release amount, requisition number, schedule count, and resulting Active state.

Retrying the same disbursement returns the existing release and schedule. It does not create another requisition, payment, or schedule row.

## Posting a repayment

Repayments are allocated in this order:

1. Penalty and fees.
2. Accrued or scheduled interest.
3. Principal.

The repayment screen shows the original amount and currency, exchange rate where applicable, converted amount, and allocation breakdown. A repayment in a currency different from the loan currency requires an approved positive exchange rate. An amount above the current outstanding balance is rejected; the Error Coach response tells the user the maximum accepted amount and the steps to resolve it.

When the outstanding balance reaches zero, the loan becomes Settled. A settled loan cannot receive a repayment or another offset through the normal action endpoint.

## Default and policy payout offsets

The default batch examines Active and Partially Repaid loans with unpaid schedule rows. A row becomes eligible only when its overdue days are strictly greater than the configured grace days plus penalty period days. The batch records the as-of date, overdue installment numbers, threshold, actor, source channel, and correlation ID.

When a surrender, maturity, or death claim is paid, the policy servicing integration sends the human-readable source reference and gross payout to the shared offset service. The deduction is:

`offset amount = minimum(current outstanding balance, gross payout)`

`net payout = gross payout - offset amount`

The same source tuple cannot be offset twice. A replay returns the original result without deducting the balance again.

## Viewing and reporting

The loan list supports search by loan number, policy number, and policyholder, together with status, currency, product, agent, branch, date, overdue, and positive-balance filters. The detail view contains the loan terms, schedules, repayments, accruals, offsets, allowed actions, and audit timeline. KPI and CSV export responses use human-readable display values and apply the same filters as the list.

The partner portal is read-only and shows only loans belonging to partners visible to the signed-in user. It never exposes lifecycle actions, internal UUIDs as labels, or another partner’s loan data.

## Documents and notifications

Authorized staff can generate a branded loan agreement or repayment schedule through the unified document engine. Generated instances retain the source loan, template code and version, checksum, page count, actor, and correlation metadata. Preview uses the authenticated document flow; the short-lived signed ticket is supplementary and expires after five minutes.

Loan disbursement, default, settlement, and offset events feed the notification center. Email, SMS, and dashboard deliveries use a stable loan-event key so retries do not duplicate user notifications.

## Common user resolutions

| Message situation | Resolution |
| --- | --- |
| Policy is not eligible | Confirm that the policy is Active or Paid-up and that the product allows loans. |
| Amount exceeds the limit | Reduce the amount to the maximum shown in the response, or ask an administrator to review the effective cash-value percentage and maximum amount. |
| Repayment mode is unavailable | Ask Parameter Administration to activate a supported mode and term in OL Parameters > Loan Setup. |
| Payment mode or bank account is missing | Ask Finance Administration to activate the outgoing payment rule and a matching company account. |
| Repayment is an overpayment | Enter no more than the current outstanding balance. Confirm the balance before retrying. |
| Settlement cannot offset the loan | Review whether the loan is already Settled or Closed and verify the source payout reference. |
| Session or permission error | Sign in again or ask User Management for the appropriate `ol_loans.*` permission. |

All user-facing failures follow the structured Error Coach shape and include a clear error code, field guidance where relevant, resolution steps, and a documentation reference.

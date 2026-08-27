# ZIC Ordinary Life Claims User Guide

## Purpose

The Ordinary Life Claims module provides a controlled workflow for registering, validating, assessing, approving, settling, and monitoring life-insurance claims. The workflow is parameter-driven: claim types, reasons, waiting periods, benefit rules, mandatory documents, medical thresholds, approval requirements, loan-offset behavior, and policy updates are configured by authorized staff rather than by the browser.

A claim is identified to users by its **claim number**. A policy is identified by its **policy number**, and a person is identified by the recorded name. Internal UUIDs are machine keys only and are not user-facing labels.

## Staff workflow

| Step | User action | Completion evidence |
|---|---|---|
| 1. Register | Select an eligible policy, claim type, claim date, reason, claimant, and benefit. Submit with an idempotency key. | Claim number and `ClaimRegistered` event |
| 2. Evidence | Upload each required document and review completeness. | Mandatory-document checklist is complete |
| 3. Medical review | Require review when parameters or thresholds demand it; record Cleared, Loading, or Rejected. | Medical result, reviewer, date, and reason |
| 4. Assessment | Enter assessment notes, approved benefit amounts, fraud decision, and any waiver-of-premium period. | Item-level approved amounts and `ClaimAssessed` event |
| 5. Financial review | Open Financial Summary to inspect gross approved amount, active-loan balance, planned/applied offset, and net payout. | Read-only finance calculation and offset evidence |
| 6. Requisition | Confirm positive net payable amount and claimant/partner bank details. Raise the payment requisition. | Claim requisition number, Front Office payment reference, and approval link |
| 7. Approval | Complete the linked governance approval when the configured payment threshold requires it. | Approved or Rejected requisition outcome |
| 8. Settlement | Submit the confirmed Front Office payment status and reference. | Payment reference, settlement date, `ClaimSettled`, and policy update snapshot |
| 9. Documents | Print the branded discharge voucher or inspect uploaded evidence. | Stored document instance, template version, and signed short-lived download URL |

The system prevents skipping a required preceding step. Repeated registration requests with the same idempotency key and unchanged payload return the original claim rather than creating another claim. A changed payload with the same key is rejected for review.

## Partner portal

The partner portal is available at `/api/v1/portal/claims/`. A linked partner user can list only claims for policies belonging to that partner, open a claim by claim number, and register a claim through the restricted portal form. Portal registration delegates to the same validation and audit service used by staff and records `PORTAL` as the source channel.

The portal accepts policy number, claim type, claim date, cause, description, benefit type, member reference, and claimant details. It does not accept staff-only status changes, assessment amounts, approval decisions, payment confirmations, or policy updates. A portal user attempting to access another partner’s claim receives a generic not-found response so the existence of the claim is not disclosed.

## Claim states

| State | Meaning | Typical next action |
|---|---|---|
| Registered | Claim was accepted for processing. | Complete documents and medical requirements. |
| Pending medical review | Medical evidence or review is outstanding. | Record the medical decision. |
| Assessment | The claim is ready for financial assessment. | Enter assessment findings and benefit amounts. |
| Assessed | Benefit amount and controls have been recorded. | Raise the payment requisition. |
| Requisition / Requisitioned | Payment request is being prepared or has been submitted. | Complete approval and Front Office payment processing. |
| Approved | Payment has passed the configured approval path. | Confirm payment and settle. |
| Settled | Payment is confirmed and policy/reinsurance updates are recorded. | Review the voucher and audit timeline. |
| Rejected | Claim cannot proceed under the recorded decision. | Review the reason and follow governance escalation. |
| Cancelled | Claim was withdrawn or cancelled through an authorized action. | Retain the audit evidence. |

## Financial summary and loan offset

Financial Summary is read-only until a positive approved item amount exists. The gross amount is the sum of approved claim item amounts. Active policy-loan balances include outstanding interest and principal. At settlement, the system applies the offset transactionally, interest first and principal second, creates a loan repayment ledger row for every touched loan, reduces balances, and marks a loan `REPAID` when its remaining balance is zero. The net payout is never negative.

> **Important:** Users must not edit the gross amount, loan balance, offset amount, or net payout in the browser. The server calculates and records the authoritative values.

## Documents and notifications

Uploaded evidence is stored against the claim and retains its document type, upload date, uploader, and file reference. The discharge voucher is rendered through the unified Documents app using the active branded template. The response includes a stored instance, preview URL, and short-lived signed download URL. The URL is single-purpose and expires after the configured short lifetime.

Claim registration, assessment, and settlement events fan out to the existing notification center and available email/SMS outboxes. Event retries are safe: stable external keys prevent duplicate dashboard notifications and duplicate channel rows. Dashboard links use the human-readable claim number.

## Common recovery actions

When Error Coach displays a structured error, follow its resolution steps instead of changing data blindly. Refresh the claim before retrying a state-changing action, complete the named missing requirement, and confirm that the current claim status still permits the action. Staff should use the claim timeline and audit record to determine whether a previous attempt already succeeded.

## Everyday checks

Before final settlement, confirm that the claim number and policy number are correct, all mandatory documents are present, the medical result is compatible with the claim, every item has a defensible approved amount, any fraud or waiver reason is recorded, the financial summary is positive or intentionally zero, the linked requisition is approved, and the payment reference came from Front Office. Finally, open the discharge voucher preview and confirm the template version and generation metadata.

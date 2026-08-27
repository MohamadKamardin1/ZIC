# ZIC Ordinary Life Loans Administrator Guide

## Scope and operating principle

This guide is for Parameter Administration, Loan Operations, Finance, and system administrators responsible for the OL Loans bounded context. The module must be operated through the configured services and management commands. Administrators must not edit balances, repayment allocations, offsets, or status history directly in the database.

Financial data is preserved rather than flushed. Natural keys and idempotency keys make the release seed and operational retries repeatable.

## Required configuration

Before enabling loan actions, verify the following effective-dated records:

| Configuration | Required values |
| --- | --- |
| OL Product | `allow_loans=True`, permitted currency, active product and policy-value support |
| OL Loan System Setup | Loan basis, percentage and amount limits, repayment options, payout effect rules, approval setting |
| OL Loan Interest Control | Rate, compounding frequency, interest basis, grace days, penalty period, penalty rate, capitalization |
| Receipt Payment Mode Rule | Active outgoing mode and allowed instrument; bank account requirement where applicable |
| Company Bank Account | Active account in the loan currency; default account or explicit account code |
| IAM | `ol_loans.view`, `request`, `approve`, `disburse`, `repay`, `reverse`, `offset`, `print`, and `configure` as appropriate |

Effective dates are evaluated as of the operation date. A missing or inactive configuration produces a teachable `LOAN_PARAMETER_MISSING` or action-specific Error Coach response; the module does not apply an undocumented fallback.

## Bootstrap and release seed

Run commands from the backend directory after migrations have been applied:

```bash
python3 manage.py migrate --noinput
python3 manage.py seed_zanzibar_ol_complete
python3 manage.py seed_ol_loan_release --json > /tmp/ol_loan_release_seed.json
```

`seed_zanzibar_ol_complete` owns the full Zanzibar OL parameter graph and reference data. `seed_ol_loan_release` adds exactly ten loans in the `OL-RELEASE-` namespace, creates policy/proposal lineage, exercises production loan services, and prints structured failure proofs. The release command does not flush or delete existing data.

The command is idempotent. Re-running it reuses the same request, disbursement, repayment, offset, policy, and partner natural keys. A successful run must report `loan_count: 10`, `idempotent: true`, and the ten scenario labels in the release matrix.

## Release scenario matrix

| Scenario | Expected state | Evidence |
| --- | --- | --- |
| Standard active loan | `ACTIVE` | One disbursement, schedule, request/approval/disbursement audit trail |
| Partially repaid | `PARTIALLY_REPAID` | One repayment and reduced outstanding balance |
| Fully settled | `SETTLED` | Full repayment, zero balance, settlement event and audit |
| Defaulted overdue | `DEFAULTED` | Batch default detection, overdue schedule numbers, threshold and correlation ID |
| Offset on surrender | `OFFSET_ON_SURRENDER` | One surrender offset with gross payout and remaining payout |
| Offset on death claim | `OFFSET_ON_CLAIM` | One claim offset with gross payout and remaining payout |
| Multi-currency repayment | `PARTIALLY_REPAID` | USD original amount, approved exchange rate, TZS applied amount |
| Rejected request | `REJECTED` | Rejection reason, actor, timestamp, and audit record |
| Pending approval | `REQUESTED` | Pending shared `ApprovalRequest` and `approval_required=true` |
| CSV/imported loan | `ACTIVE` | `source_channel=IMPORT`; manual batch path is used because no loan CSV import contract exists |

The command currently uses explicit release dates of 2026-01-15 for disbursement and 2026-08-27 for as-of verification. This makes the financial result reproducible and avoids dependence on the wall clock in test and release evidence.

## Verification commands

Run the targeted release test and the complete affected backend matrix:

```bash
python3 manage.py test apps.ol_loans.tests.test_release_seed --keepdb --verbosity 1
python3 manage.py test apps.ol_loans apps.ol_policies apps.documents --keepdb --verbosity 1
python3 manage.py makemigrations --check --dry-run
python3 manage.py check
python3 -m compileall -q apps/ol_loans apps/ol_policies
python3 manage.py verify_loan_audit --json
```

A release is not green unless the tests, migration check, system check, compile check, audit consistency command, and `git diff --check` all pass. The audit command is read-only and should be run before and after operational migrations or data corrections.

## Failure-proof review

The release seed captures five negative or retry paths:

| Proof | Expected result |
| --- | --- |
| Ineligible policy | `LOAN_INELIGIBLE`; cancelled policy is rejected before a loan is created |
| Exceeds cash-value limit | `LOAN_EXCEEDS_LIMIT`; response includes cash value, percentage, available limit, and field guidance |
| Overpayment | `LOAN_REPAYMENT_OVERPAYMENT`; response includes current outstanding balance and a maximum accepted amount |
| Offset on settled loan | `LOAN_OFFSET_INVALID`; response explains that settled and closed loans cannot be offset |
| Duplicate disbursement | Idempotent replay; existing immutable release and schedule returned without a second requisition |

A proof is valid only when its operation fails or replays as expected and no unintended financial row is committed. The JSON result is suitable for attaching to a release ticket or CI artifact.

## Audit and event monitoring

Every financial write should have a central `AuditLog` record with actor, action, object reference, before state, after state, reason, source channel, and correlation/request metadata. `DomainEvent` is the durable outbox for LoanRequested, LoanApproved, LoanDisbursed, LoanRepaid, LoanSettled, LoanDefaulted, and LoanOffset events.

Monitor failed or repeated events by aggregate ID and event type. Notification and settlement receivers are idempotent. An unexpected settlement offset error is surfaced transactionally rather than swallowed, because silently publishing a policy payout without a required loan deduction would create a financial integrity gap.

## Safe correction procedure

When a balance or status appears incorrect, first inspect the loan detail, schedule, repayment, accrual, offset, audit, and event rows. Confirm the source channel and correlation ID. Do not update the balance directly. Use the approved reversal or correction workflow, preserve the original audit trail, and record the reason and authorizing actor.

When a parameter is incorrect, create or activate a new effective-dated row rather than modifying historical rows used by a completed financial action. Re-run the targeted service test and the audit consistency command after the change.

# FRONT OFFICE RECEIPTS BACKEND — PROMPT SERIES (12 prompts)

- [x] Prompt 1 — Save Prompt Series + Front Office Receipts Domain Foundation
- [x] Prompt 2 — Implement Receipt Parameters, Numbering & Reference Data
- [x] Prompt 3 — Implement Receipt Creation, Draft Editing, Validation & Posting
- [x] Prompt 4 — Implement Receipt Allocation to OL Commitments & First Premium
- [x] Prompt 5 — Implement Multi-Currency Receipt & Allocation Behavior
- [x] Prompt 6 — Implement Receipt Reversal, Allocation Reversal & Draft Cancellation
- [x] Prompt 7 — Implement Receipt List, Detail, Work Queue & Export APIs
- [ ] Prompt 8 — (pending: prompt text will be appended `EXACTLY as provided` when supplied)
- [ ] Prompt 9 — (pending: prompt text will be appended `EXACTLY as provided` when supplied)
- [ ] Prompt 10 — (pending: prompt text will be appended `EXACTLY as provided` when supplied)
- [ ] Prompt 11 — (pending: prompt text will be appended `EXACTLY as provided` when supplied)
- [ ] Prompt 12 — (pending: prompt text will be appended `EXACTLY as provided` when supplied)

> **Note on fidelity:** only Prompt 1 was included in the pasted series message for
> this session. Prompts 2–12 will be appended `EXACTLY as provided` when the user
> supplies them, then executed strictly one at a time, ticking each checkbox after
> its commit and push. Prompt 1 below is saved verbatim.

---

## Prompt 1/12 — Save Prompt Series + Front Office Receipts Domain Foundation

```text
You are a senior Django insurance finance engineer. Build the ZIC Front Office Receipts backend. The user pasted the FULL 12-prompt series at once.

META-INSTRUCTION — HIGHEST PRIORITY:
1. Before coding, create docs/prompts/FRONT_OFFICE_RECEIPTS_BACKEND_PROMPTS.md.
2. Save ALL 12 prompts of this series EXACTLY as provided, each with a checkbox "[ ] Prompt N — title".
3. Commit and push that file immediately.
4. Execute ONLY Prompt 1 now.
5. After Prompt 1 is fully implemented, tested, committed, and pushed, tick Prompt 1 in the saved file, commit that tick, then proceed to Prompt 2.
6. Never execute two prompts at once. Never skip prompts. Never leave placeholders.

MANDATORY RULES:
- Do not ask blocking questions. Make senior insurance/finance assumptions and document them.
- Use the ZIC system specification and all existing modules: IAM, partners, audit, system parameters, OL parameters, OL quotations, OL proposals, OL commitments, documents.
- Everything must be parameterized.
- Names must be shown instead of UUIDs in all API responses.
- Every financial action must be idempotent, permission-controlled, and audited.
- All user-facing errors must use the existing structured Error Coach shape with resolution steps.
- Commit and push at the end.

OBJECTIVE:
Create the Front Office Receipts bounded context and domain foundation.

BUSINESS CONTEXT:
The vendor demo shows front-office users creating receipts for proposal premium deposits. A receipt includes branch, partner, receipt mode/payment mode, currency, amount, allocations, account details, printable receipt, and reversal capability. Receipts are required to post first premium before a proposal can convert to a policy.

SCOPE:
1. Create or extend Django app:
   - front_office
   - or receipts
   - or finance_receipts if repo convention prefers
2. Produce docs/FRONT_OFFICE_RECEIPTS_DESIGN.md covering:
   - receipt concept
   - first premium flow
   - allocation flow
   - reversal flow
   - multi-currency assumptions
   - payment mode assumptions
   - government control number future seam
   - bank/payment gateway future seam
   - ERP/GL future seam
   - integration with OL Commitments and OL Proposals
3. Implement core models:
   - Receipt
   - ReceiptAllocation
   - ReceiptReversal
   - ReceiptDocument
   - ReceiptStatusHistory if useful
4. Receipt fields:
   - receipt_number unique
   - receipt_date
   - branch
   - partner / payer
   - payer_name snapshot
   - payer_identity snapshot optional
   - source_module: OL_PROPOSAL, OL_POLICY, GROUP_CREDIT, MANUAL, OTHER
   - source_reference_type
   - source_reference_id
   - currency
   - exchange_rate
   - receipt_amount
   - allocated_amount
   - unallocated_amount
   - payment_mode
   - payment_reference
   - bank_account optional
   - narration
   - status: DRAFT, POSTED, PARTIALLY_ALLOCATED, FULLY_ALLOCATED, REVERSED, CANCELLED
   - posted_at / posted_by
   - reversed_at / reversed_by
   - cancellation_reason
   - created_by / updated_by / timestamps
5. ReceiptAllocation fields:
   - receipt
   - target_type: OL_COMMITMENT, OL_PROPOSAL, OL_POLICY, MANUAL
   - target_id
   - target_display
   - amount
   - currency
   - exchange_rate
   - allocation_status
   - reversal_of optional
   - narration
   - audit fields
6. ReceiptReversal fields:
   - receipt
   - reversal_number
   - reason
   - reversed_allocations JSON snapshot
   - created_by / created_at
7. Register permissions:
   - front_office.receipts.view
   - front_office.receipts.create
   - front_office.receipts.post
   - front_office.receipts.allocate
   - front_office.receipts.reverse
   - front_office.receipts.cancel
   - front_office.receipts.print
   - front_office.receipts.import
   - front_office.receipts.configure
8. Register domain events:
   - ReceiptCreated
   - ReceiptPosted
   - ReceiptAllocated
   - ReceiptFullyAllocated
   - ReceiptReversed
   - ReceiptCancelled
   - FirstPremiumReceived
9. Add admin table-first registration.
10. Add base API skeleton:
   - list
   - create draft
   - retrieve
   - update draft
11. Add structured receipt error registry:
   - RECEIPT_NOT_FOUND
   - RECEIPT_INVALID_STATUS
   - RECEIPT_AMOUNT_INVALID
   - RECEIPT_ALLOCATION_INVALID
   - RECEIPT_OVERALLOCATION
   - RECEIPT_ALREADY_POSTED
   - RECEIPT_ALREADY_REVERSED
   - RECEIPT_CURRENCY_MISMATCH
   - RECEIPT_PERMISSION_DENIED
   - RECEIPT_PARAMETER_MISSING

TESTS:
- model creation
- amount computations
- receipt status enum behavior
- permissions registered
- structured error shape
- audit on create/update

GIT:
- commit: "feat(receipts): save prompt series and create receipts domain foundation"
- push; if blocked create feature/front-office-receipts-foundation and push
- tick Prompt 1 checkbox after completion and commit

FINAL OUTPUT:
Return design summary, models, permissions, events, tests, assumptions, commit hash, pushed branch.
```

---

## Prompt 2/12 — Implement Receipt Parameters, Numbering & Reference Data

```text
You are a senior Django finance configuration engineer. Continue the Front Office Receipts backend. Execute ONLY Prompt 2 from docs/prompts/FRONT_OFFICE_RECEIPTS_BACKEND_PROMPTS.md.

MANDATORY RULES:
- All receipt behavior must be parameterized.
- Do not hardcode branches, currencies, payment modes, numbering, statuses, or bank accounts.
- Commit and push; tick Prompt 2 after completion.

OBJECTIVE:
Implement receipt parameters, receipt numbering, and reference-data integration.

SCOPE:
1. Create receipt configuration models or extend system_config:
   - ReceiptNumberingRule
   - ReceiptStatusParameter if not using model choices only
   - CompanyBankAccount
   - ReceiptPaymentModeRule
2. ReceiptNumberingRule fields:
   - code
   - name
   - branch optional
   - prefix
   - sequence_padding
   - next_sequence
   - reset_frequency: NEVER, YEARLY, MONTHLY, DAILY
   - effective_from
   - effective_to
   - is_active
3. CompanyBankAccount fields:
   - code
   - bank_name
   - account_name
   - account_number masked in responses
   - currency
   - branch optional
   - is_default
   - is_active
4. ReceiptPaymentModeRule fields:
   - payment_mode
   - requires_reference
   - requires_bank_account
   - allows_cash
   - allows_card
   - allows_mobile_money
   - allows_bank_transfer
   - allows_cheque
   - min_amount optional
   - max_amount optional
   - active status
5. Seed baseline data:
   - at least one receipt numbering rule
   - active company bank account
   - rules for CASH, BANK_TRANSFER, MOBILE_MONEY, CARD, CHEQUE if payment modes exist
6. Implement receipt number service:
   - branch-aware
   - concurrency-safe
   - idempotent on retry
7. Implement options endpoints:
   - branches
   - currencies
   - payment modes
   - company bank accounts
   - receipt statuses
8. All option payloads must be:
   - value
   - label
   - meta
9. Add structured PARAMETER_MISSING errors with deep links to:
   - System Parameters > Branches
   - System Parameters > Currencies
   - System Parameters > Payment Modes
   - Front Office Parameters > Receipt Numbering
   - Front Office Parameters > Company Bank Accounts
10. Admin tables for all receipt parameters.

TESTS:
- receipt number generation
- concurrent uniqueness
- missing numbering rule error
- masked bank account response
- option endpoint labels
- payment mode rule validation

GIT:
- commit: "feat(receipts): implement receipt parameters numbering and reference data"
- push; tick Prompt 2 checkbox

FINAL OUTPUT:
Return parameter models, seed data, numbering contract, options endpoints, tests, commit hash, pushed branch.
```

---

## Prompt 3/12 — Implement Receipt Creation, Draft Editing, Validation & Posting

```text
You are a senior Django finance transaction engineer. Continue the Front Office Receipts backend. Execute ONLY Prompt 3.

MANDATORY RULES:
- Receipt creation and posting must be idempotent.
- Drafts can be edited; posted receipts are immutable except allocation/reversal actions.
- Commit and push; tick Prompt 3 after completion.

OBJECTIVE:
Implement robust receipt creation, draft editing, validation, and posting.

SCOPE:
1. API endpoints:
   - POST /api/v1/front-office/receipts/
   - PATCH /api/v1/front-office/receipts/{id}/
   - POST /api/v1/front-office/receipts/{id}/post/
2. Create receipt as DRAFT by default.
3. Posting should:
   - assign receipt number if not already assigned
   - validate payment mode rule
   - validate receipt amount > 0
   - validate currency active
   - validate branch active
   - validate partner active
   - validate reference required by payment mode
   - set POSTED status
   - set posted_at and posted_by
   - emit ReceiptPosted
   - audit before/after
4. Posted receipts cannot have core fields edited:
   - payer
   - amount
   - currency
   - payment mode
   - receipt date
   - branch
5. Support idempotency key header:
   - X-Idempotency-Key
   - duplicate POST returns same receipt
6. Response payload must include display fields:
   - branch_display
   - partner_display
   - currency_display
   - payment_mode_display
   - bank_account_display
   - created_by_display
   - posted_by_display
7. Structured errors:
   - RECEIPT_ALREADY_POSTED
   - RECEIPT_AMOUNT_INVALID
   - RECEIPT_PARAMETER_MISSING
   - RECEIPT_INVALID_STATUS
8. Admin action to post draft receipt with reason/comment.

TESTS:
- create draft receipt
- edit draft
- post receipt assigns number
- posted receipt immutable
- idempotent create
- missing payment reference blocked when mode requires it
- audit/event assertions

GIT:
- commit: "feat(receipts): implement receipt creation draft editing and posting"
- push; tick Prompt 3 checkbox

FINAL OUTPUT:
Return endpoints, validation rules, idempotency behavior, tests, commit hash, pushed branch.
```

---

## Prompt 4/12 — Implement Receipt Allocation to OL Commitments & First Premium

```text
You are a senior Django insurance finance engineer. Continue the Front Office Receipts backend. Execute ONLY Prompt 4.

MANDATORY RULES:
- Allocation must integrate with OL Commitments and close BR-03 for OL Proposals.
- Commit and push; tick Prompt 4 after completion.

OBJECTIVE:
Implement allocation of posted receipts to OL commitments, including first premium commitments for proposals.

SCOPE:
1. API endpoints:
   - GET /api/v1/front-office/receipts/{id}/allocation-options/
   - POST /api/v1/front-office/receipts/{id}/allocate/
   - POST /api/v1/front-office/receipts/{id}/auto-allocate/
2. Allocation options should return open commitments for the receipt partner/payer:
   - commitment_number
   - source_type
   - source_display
   - proposal_number if applicable
   - policy_number if applicable
   - product/plan display
   - due_date
   - amount_due
   - amount_paid
   - balance
   - currency
   - status
3. Manual allocation payload:
   - target_type = OL_COMMITMENT
   - target_id
   - amount
   - narration
4. Allocation logic:
   - receipt must be POSTED or PARTIALLY_ALLOCATED
   - cannot allocate more than unallocated receipt amount
   - cannot allocate more than commitment balance
   - call existing OLCommitment allocation service instead of duplicating logic
   - create ReceiptAllocation linked to OLCommitmentAllocation
   - update receipt allocated_amount and unallocated_amount
   - if unallocated_amount = 0, status FULLY_ALLOCATED
   - otherwise PARTIALLY_ALLOCATED
5. First premium behavior:
   - if commitment source_type = PROPOSAL and installment_number = 1
   - and commitment becomes completed
   - emit FirstPremiumReceived and/or PremiumReceived
   - proposal first_premium_posted guard must return true
6. Auto-allocation:
   - allocate oldest due commitments first by due date
   - same currency first
   - stop when amount exhausted
   - return detailed allocation result
7. Structured errors:
   - RECEIPT_OVERALLOCATION
   - RECEIPT_ALLOCATION_INVALID
   - RECEIPT_INVALID_STATUS
   - RECEIPT_CURRENCY_MISMATCH
8. Audit receipt and commitment side consistently.

TESTS:
- allocate full amount to one commitment
- partial allocation
- over-allocation blocked
- allocation updates commitment balance
- first premium completion unlocks proposal guard
- auto-allocation oldest-first
- audit/event assertions

GIT:
- commit: "feat(receipts): implement allocation engine to commitments and first premium"
- push; tick Prompt 4 checkbox

FINAL OUTPUT:
Return allocation contract, BR-03 integration evidence, tests, commit hash, pushed branch.
```

---

## Prompt 5/12 — Implement Multi-Currency Receipt & Allocation Behavior

```text
You are a senior Django insurance finance engineer. Continue the Front Office Receipts backend. Execute ONLY Prompt 5.

MANDATORY RULES:
- Multi-currency handling must be explicit and auditable.
- Commit and push; tick Prompt 5 after completion.

OBJECTIVE:
Implement multi-currency receipt and allocation behavior.

SCOPE:
1. Integrate with Currency and ExchangeRate parameters if they exist; create minimal ExchangeRate model if absent.
2. ExchangeRate fields:
   - from_currency
   - to_currency
   - rate
   - effective_date
   - source
   - is_active
3. Receipt allocation rules:
   - same currency requires no exchange rate
   - cross-currency allocation requires explicit exchange_rate
   - converted amount must be shown in allocation response
   - store original amount and converted amount
4. Add endpoint:
   - GET /api/v1/front-office/exchange-rate/?from=&to=&date=
5. Validation:
   - missing exchange rate returns RECEIPT_CURRENCY_MISMATCH with resolution steps
   - zero/negative rate blocked
   - stale rate warning if configured
6. Add audit fields:
   - exchange_rate_used
   - exchange_rate_source
   - converted_amount
7. Update allocation endpoint to support:
   - allocation_amount_in_receipt_currency
   - allocation_amount_in_target_currency
8. Document assumptions in docs/FRONT_OFFICE_RECEIPTS_DESIGN.md.

TESTS:
- same-currency allocation
- cross-currency allocation with explicit rate
- missing rate error
- exchange-rate endpoint
- converted amount math
- audit values captured

GIT:
- commit: "feat(receipts): implement multi-currency exchange rate handling"
- push; tick Prompt 5 checkbox

FINAL OUTPUT:
Return exchange model/endpoint, conversion rules, tests, commit hash, pushed branch.
```

---

## Prompt 6/12 — Implement Receipt Reversal, Allocation Reversal & Draft Cancellation

```text
You are a senior Django financial controls engineer. Continue the Front Office Receipts backend. Execute ONLY Prompt 6.

MANDATORY RULES:
- Reversal must never delete history.
- Reasons are mandatory.
- Reversal must restore commitment/proposal states consistently.
- Commit and push; tick Prompt 6 after completion.

OBJECTIVE:
Implement receipt reversal, allocation reversal, and draft cancellation.

SCOPE:
1. API endpoints:
   - POST /api/v1/front-office/receipts/{id}/reverse/
   - POST /api/v1/front-office/receipts/{id}/allocations/{allocation_id}/reverse/
   - POST /api/v1/front-office/receipts/{id}/cancel/
2. Rules:
   - DRAFT receipts can be cancelled with reason
   - POSTED/PARTIALLY_ALLOCATED/FULLY_ALLOCATED receipts can be reversed with reason
   - reversed receipt status = REVERSED
   - cancellation status = CANCELLED
   - no hard delete
3. Full receipt reversal:
   - reverse all allocations
   - call OLCommitment reversal service for each linked commitment allocation
   - restore commitment balance/status
   - if first premium was reversed, proposal first_premium_posted guard becomes false
   - emit ReceiptReversed
4. Single allocation reversal:
   - creates reversal allocation row
   - updates receipt allocated/unallocated amounts
   - updates commitment balance/status
   - receipt status recalculated
5. Reversal constraints:
   - already reversed blocked
   - reversal after configured lock period returns RECEIPT_REVERSAL_LOCKED
   - permission required
6. Audit:
   - before/after state
   - actor
   - reason
   - linked commitment allocation reversal references

TESTS:
- cancel draft
- reverse fully allocated receipt
- reverse one allocation
- proposal guard false after first premium reversal
- already reversed blocked
- lock-period blocked
- audit/event assertions

GIT:
- commit: "feat(receipts): implement receipt reversal allocation reversal and cancellation"
- push; tick Prompt 6 checkbox

FINAL OUTPUT:
Return reversal behavior, constraints, tests, commit hash, pushed branch.
```

---

## Prompt 7/12 — Implement Receipt List, Detail, Work Queue & Export APIs

```text
You are a senior Django API engineer. Continue the Front Office Receipts backend. Execute ONLY Prompt 7.

MANDATORY RULES:
- Table-first API responses.
- Names never UUIDs.
- Allowed actions must be state-aware and permission-aware.
- Commit and push; tick Prompt 7 after completion.

OBJECTIVE:
Implement complete receipt list/detail/work queue APIs.

SCOPE:
1. List endpoint columns:
   - receipt_number
   - receipt_date
   - payer_display
   - branch_display
   - payment_mode_display
   - currency_display
   - receipt_amount
   - allocated_amount
   - unallocated_amount
   - status badge
   - source_module
   - created_by_display
   - posted_by_display
   - created_at
   - allowed_actions
2. Filters:
   - status
   - branch
   - currency
   - payment_mode
   - payer
   - source_module
   - date range
   - unallocated_only
   - reversed_only
3. Search:
   - receipt number
   - payer name
   - payment reference
   - source reference
4. KPI endpoint:
   - total_received_period
   - total_allocated_period
   - total_unallocated
   - receipt_count
   - reversed_amount
5. Detail endpoint:
   - receipt header
   - allocations
   - reversal history
   - documents
   - audit timeline
   - allowed actions
6. CSV export respecting filters.
7. Admin list mirrors key columns and filters.

TESTS:
- list columns and display names
- filters/search
- KPI math
- allowed actions by status/permission
- CSV export respects filters
- detail includes allocations/reversal/audit timeline

GIT:
- commit: "feat(receipts): implement receipt list detail work queue and export APIs"
- push; tick Prompt 7 checkbox

FINAL OUTPUT:
Return endpoint contract, KPI rules, tests, commit hash, pushed branch.
```

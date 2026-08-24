# FRONT OFFICE RECEIPTS BACKEND — PROMPT SERIES (12 prompts)

- [x] Prompt 1 — Save Prompt Series + Front Office Receipts Domain Foundation
- [ ] Prompt 2 — (pending: prompt text will be appended `EXACTLY as provided` when supplied)
- [ ] Prompt 3 — (pending: prompt text will be appended `EXACTLY as provided` when supplied)
- [ ] Prompt 4 — (pending: prompt text will be appended `EXACTLY as provided` when supplied)
- [ ] Prompt 5 — (pending: prompt text will be appended `EXACTLY as provided` when supplied)
- [ ] Prompt 6 — (pending: prompt text will be appended `EXACTLY as provided` when supplied)
- [ ] Prompt 7 — (pending: prompt text will be appended `EXACTLY as provided` when supplied)
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

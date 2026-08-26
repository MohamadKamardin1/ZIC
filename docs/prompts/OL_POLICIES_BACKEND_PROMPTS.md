# OL POLICIES BACKEND — FULL PROMPT SERIES (12 Prompts)

## [x] Prompt 1/12 — Save Series File + Policy Domain Foundation

```text
You are a senior Django insurance platform engineer. Build the ZIC Ordinary Life Policies backend. The user pasted the FULL 12-prompt series at once.

META-INSTRUCTION (HIGHEST PRIORITY):
1. Before coding, create docs/prompts/OL_POLICIES_BACKEND_PROMPTS.md and save ALL 12 prompts EXACTLY as provided, each with a checkbox "[ ] Prompt N — title".
2. Commit and push that file immediately.
3. Execute ONLY Prompt 1 now; when green, tick its checkbox, commit, then proceed to Prompt 2. Never merge or skip prompts.

MANDATORY RULES:
- No blocking questions; make senior insurance assumptions and document them.
- The Policy model must be a snapshot of the contract at issuance. It is the source of truth for servicing.
- Every material change must be audited with actor, before/after, reason, source channel.
- Commit and push at the end of each prompt.

OBJECTIVE:
Create the OL Policy bounded context and core domain models.

BUSINESS CONTEXT:
A Policy is created from a Proposal once the first premium is posted (BR-03). It holds the definitive contract terms: Sum Assured, Premium, Term, Benefits, Riders, Members, and Dates. It must support a complex lifecycle: Active, Lapsed, Paid-Up, Surrendered, Matured, Expired, Cancelled.

SCOPE:
1. Produce docs/OL_POLICIES_DESIGN.md defining:
   - Policy lifecycle state machine (parameterized via OL Policy Status parameters).
   - Relationship with Proposal (Policy references Proposal; Proposal references Policy).
   - Relationship with Commitments (Policy owns renewal commitments).
   - Endorsement concept (audit trail of changes).
   - Integration map: Proposals, Receipts, Commitments, Claims, Loans.
2. Create Django app `ol_policies`.
3. Implement core models:
   - Policy: policy_number (unique, generated), proposal_ref, partner (policyholder), agent, product_plan_ref, currency, sum_assured, premium_amount, premium_frequency, term_years, risk_commencement_date, maturity_date, status, first_premium_receipt_ref, audit fields.
   - PolicyMember: policy, member relation, name, dob, gender, benefit_amount, audit fields.
   - PolicyRider: policy, rider_code, sum_assured/amount, premium, audit fields.
   - PolicyBenefit: policy, benefit_type, calculation_basis, amount, audit fields.
   - PolicyEndorsement: policy, endorsement_number, type (CHANGE_BENEFIT, ADDRESS, BENEFICIARY, SURRENDER, ETC), effective_date, description, status, audit fields.
   - PolicyAuditLog: global log for policy state changes.
4. Register permissions:
   - ol_policies.view, create, service, endorse, cancel, reinstate, print, configure.
5. Implement global structured error registry for policies:
   - POLICY_NOT_FOUND, POLICY_ALREADY_ISSUED, POLICY_INVALID_STATUS, POLICY_SURRENDER_BLOCKED, POLICY_LOAN_BLOCKED, POLICY_LAPSED, POLICY_NOT_MATURED, POLICY_ENDORSEMENT_INVALID.
6. Add base API skeleton: list, retrieve.
7. Add admin table-first registration.

TESTS:
- model creation and relationships
- policy number uniqueness
- status validation
- structured error shapes

GIT:
- commit: "feat(ol-policies): save prompt series and create policy domain foundation"
- push; if blocked create feature/ol-policies-foundation and push; tick checkbox

FINAL OUTPUT: design summary, models, permissions, error codes, tests, commit hash, pushed branch.
```

---

## [x] Prompt 2/12 — Policy Issuance Engine (Proposal to Policy Conversion)

```text
You are a senior Django insurance engineer. Continue the ZIC OL Policies backend. Execute ONLY Prompt 2 from the saved series file.

MANDATORY RULES:
- Issuance must be atomic: Proposal becomes Policy in one transaction.
- Policy data must be immutable snapshots of the agreed terms.
- Commit and push; tick checkbox.

SCOPE:
1. Implement issuance service: issue_policy_from_proposal(proposal_id).
   - Validation:
     - Proposal status must be AWAITING_FIRST_PREMIUM or PAYMENT_READY (depending on strictness; use BR-03 guard).
     - First premium commitment must be COMPLETED (fully paid).
     - Proposal must not already be converted.
   - Action:
     - Generate Policy Number (using parameterized numbering rule if available, or sequence).
     - Create Policy record:
       - Snapshot: Sum Assured, Premium, Term, Dates (Commencement = today or proposal date).
       - Copy Members, Riders, Benefits from Proposal to Policy tables.
       - Link First Premium Receipt reference for audit.
     - Update Proposal status to CONVERTED; set policy_ref.
     - Emit Domain Event: PolicyIssued.
   - Idempotency: If proposal already has policy_ref, return existing policy.
2. Create API endpoint:
   - POST /api/v1/ol/policies/issue/
   - Payload: { proposal_id: string }
3. Generate initial Policy Commitments:
   - If the policy has renewal premiums, create the first renewal commitment in OL Commitments module (or trigger event).
4. Audit the issuance with actor, proposal_ref, policy_number, timestamp.

TESTS:
- successful issuance creates Policy + Members + Riders + Benefits
- proposal status updates to CONVERTED
- policy number is unique
- first premium guard enforced (fails if premium not paid)
- idempotency check

GIT:
- commit: "feat(ol-policies): implement policy issuance engine"
- push; tick checkbox

FINAL OUTPUT: service contract, endpoint, event emission, tests, commit hash, pushed branch.
```

---

## [x] Prompt 3/12 — Policy List, Search, & KPI Dashboard

```text
You are a senior Django API engineer. Continue the ZIC OL Policies backend. Execute ONLY Prompt 3.

MANDATORY RULES:
- Table-first responses; names never UUIDs.
- High-performance search for large policy volumes.
- Commit and push; tick checkbox.

SCOPE:
1. GET /api/v1/ol/policies/ list endpoint:
   - Columns: policy_number, policyholder_name, product_name, plan_name, sum_assured, premium, status badge, commencement_date, maturity_date, agent_name, allowed_actions.
   - Filters: status, product, agent, branch, date range (commencement/maturity), currency.
   - Search: policy_number, policyholder_name, national_id, phone.
   - Pagination & Sorting.
2. GET /api/v1/ol/policies/{id}/ detail endpoint:
   - Header info.
   - Snapshot data: members, riders, benefits, installments.
   - Linked proposal ref.
   - Linked commitments (active ones).
   - History/Audit log snippet.
   - Allowed actions based on status.
3. GET /api/v1/ol/policies/kpis/ dashboard endpoint:
   - Total Active Policies.
   - Total Sum Assured.
   - New Policies (This Month).
   - Lapsed Policies (Count & Value).
   - Policies Maturing Soon (Next 30 Days).
4. CSV Export endpoint respecting filters.

TESTS:
- list returns correct columns with display names
- filters and search work efficiently
- KPI math is correct
- detail includes all snapshot children

GIT:
- commit: "feat(ol-policies): implement policy list search and dashboard APIs"
- push; tick checkbox

FINAL OUTPUT: endpoint contract, KPI rules, tests, commit hash, pushed branch.
```

---

## [x] Prompt 4/12 — Policy Servicing & Endorsements Framework

```text
You are a senior Django insurance engineer. Continue the ZIC OL Policies backend. Execute ONLY Prompt 4.

MANDATORY RULES:
- Endorsements must not destroy history; they create new version records.
- Commit and push; tick checkbox.

SCOPE:
1. Implement Endorsement creation:
   - POST /api/v1/ol/policies/{id}/endorsements/
   - Types: PREMIUM_CHANGE, TERM_CHANGE, MEMBER_ADD, MEMBER_REMOVE, BENEFICIARY_CHANGE, ADDRESS_CHANGE.
   - For PREMIUM_CHANGE: validate new premium using OL Product Rating parameters; calculate difference; generate commitment adjustment.
   - For MEMBER_ADD/REMOVE: validate against Product Plan limits (min/max members).
   - Create PolicyEndorsement record with effective_date and description.
   - Update Policy header if necessary (e.g., total premium changes).
   - Emit PolicyEndorsed event.
2. Implement Endorsement retrieval:
   - GET /api/v1/ol/policies/{id}/endorsements/ list.
   - Detail of specific endorsement showing before/after values.
3. Validation:
   - Cannot endorse a Lapsed/Cancelled/Expired policy without Reinstatement.
   - Premium changes must be within allowed bands from parameters.

TESTS:
- create premium change endorsement
- create member add endorsement
- validation blocks invalid changes
- endorsement history retrievable
- policy header updates correctly

GIT:
- commit: "feat(ol-policies): implement policy servicing and endorsements"
- push; tick checkbox

FINAL OUTPUT: endorsement logic, validation rules, tests, commit hash, pushed branch.
```

---

## [x] Prompt 5/12 — Lapse, Reinstatement & Expiry Logic

```text
You are a senior Django insurance engineer. Continue the ZIC OL Policies backend. Execute ONLY Prompt 5.

MANDATORY RULES:
- Lifecycle transitions must be rule-based (OL Parameters).
- Batch processing must be idempotent.
- Commit and push; tick checkbox.

SCOPE:
1. Implement Lapse Logic:
   - Management command: process_policy_lapses
   - Checks OL Commitments: if a policy has overdue commitments past the grace period (from OL Grace Period parameters), mark Policy status to LAPSED.
   - Emit PolicyLapsed event.
   - Audit entry.
2. Implement Reinstatement Logic:
   - POST /api/v1/ol/policies/{id}/reinstate/
   - Validation:
     - Policy status must be LAPSED.
     - Must be within Reinstatement Window (from OL Reinstatement parameters).
     - Must pay all outstanding premiums + interest (from OL Parameters).
     - May require medical underwriting clearance (check flag).
   - Action:
     - Create commitments for outstanding premiums.
     - Change status to ACTIVE.
     - Emit PolicyReinstated event.
3. Implement Expiry Logic:
   - Management command: process_policy_expiry
   - If policy reaches maturity_date and no claim/maturity action taken, move to EXPIRED.

TESTS:
- lapse command moves policy to LAPSED after grace period
- reinstatement succeeds with payment and fails without
- reinstatement blocked outside window
- expiry command works

GIT:
- commit: "feat(ol-policies): implement lapse reinstatement and expiry logic"
- push; tick checkbox

FINAL OUTPUT: lifecycle commands, validation rules, tests, commit hash, pushed branch.
```

---

## [x] Prompt 6/12 — Surrender, Paid-Up & Cancellation

```text
You are a senior Django insurance engineer. Continue the ZIC OL Policies backend. Execute ONLY Prompt 6.

MANDATORY RULES:
- Financial calculations must be precise and auditable.
- Surrender payouts must trigger payment processes.
- Commit and push; tick checkbox.

SCOPE:
1. Implement Surrender Logic:
   - POST /api/v1/ol/policies/{id}/surrender/
   - Validation:
     - Policy must be eligible (min years/premiums paid from OL Surrender Setup parameters).
     - Cannot surrender if there is an active loan (unless loan settled).
   - Calculation:
     - Compute Surrender Value using OL Surrender Value Rates table based on policy duration, sum assured, and product.
     - Deduct outstanding loans + interest if applicable.
   - Action:
     - Create Surrender Request record.
     - Generate Payment Requisition for the net surrender value.
     - Set Policy status to SURRENDER_PENDING until paid, then SURRENDERED.
     - Emit PolicySurrenderRequested event.
2. Implement Paid-Up Logic:
   - If policy is lapsed and not eligible for reinstatement but has cash value, convert to PAID_UP status.
   - Reduce Sum Assured based on OL Paid-Up Rates.
   - Stop future premium commitments.
3. Implement Cancellation:
   - POST /api/v1/ol/policies/{id}/cancel/
   - Free-look period cancellation (full refund) vs. standard cancellation.
   - Reason mandatory.

TESTS:
- surrender value calculation correct
- surrender blocked with active loan
- paid-up conversion reduces sum assured and stops commitments
- cancellation works within free-look period

GIT:
- commit: "feat(ol-policies): implement surrender paid-up and cancellation"
- push; tick checkbox

FINAL OUTPUT: financial logic, status transitions, tests, commit hash, pushed branch.
```

---

## [x] Prompt 7/12 — Policy Loans, Repayments & Withdrawals

```text
You are a senior Django insurance engineer. Continue the ZIC OL Policies backend. Execute ONLY Prompt 7.

MANDATORY RULES:
- Loans are financial transactions against the policy cash value.
- Commit and push; tick checkbox.

SCOPE:
1. Implement Loan Request:
   - POST /api/v1/ol/policies/{id}/loans/
   - Validation:
     - Policy must allow loans (OL Product Setup flag).
     - Loan amount <= Max Loan % of Cash Value (OL Loan Setup parameters).
     - Policy must be in force (Active or Paid-Up).
   - Action:
     - Create Loan record (amount, interest rate, term, start_date).
     - Create Commitment for loan repayment (if structured).
     - Create Disbursement Requisition (payment out).
     - Emit PolicyLoanRequested event.
2. Implement Loan Repayment:
   - Allocate payments to Loan principal + interest.
   - Update Loan balance.
3. Implement Withdrawal:
   - Partial cash withdrawal (if product supports).
   - Validation against minimum cash value retention.
   - Create payment requisition.

TESTS:
- loan request validation (max limit check)
- loan creation generates repayment commitments
- repayment reduces loan balance
- withdrawal blocked if insufficient cash value

GIT:
- commit: "feat(ol-policies): implement policy loans and withdrawals"
- push; tick checkbox

FINAL OUTPUT: loan logic, repayment tracking, tests, commit hash, pushed branch.
```

---

## [x] Prompt 8/12 — Maturity Processing & Payout Transitions

Django insurance engineer. Continue the ZIC OL Policies backend. Execute ONLY Prompt 8.

MANDATORY RULES:
- Maturity is a claim-like event that pays out the maturity value.
- Commit and push; tick checkbox.

SCOPE:
1. Implement Maturity Logic:
   - Management command: process_maturities
   - Finds policies where maturity_date <= today and status is ACTIVE.
   - Action:
     - Create Maturity Claim record (linked to policy).
     - Calculate Maturity Value (Sum Assured + Bonuses if With Profit).
     - Set Policy status to MATURED_PENDING_PAYMENT.
     - Emit PolicyMatured event.
2. Implement Maturity Payment:
   - Once Maturity Claim is settled via Claims module or direct payment:
     - Update Policy status to MATURED.
     - Audit trail.

TESTS:
- maturity command finds eligible policies
- maturity value calculation
- status transition to MATURED

GIT:
- commit: "feat(ol-policies): implement policy maturity processing"
- push; tick checkbox

FINAL OUTPUT: maturity logic, event emission, tests, commit hash, pushed branch.
```

---

## [x] Prompt 9/12 — Policy Documents & Print Engine Integration

```text
You are a senior Django document engineer. Continue the ZIC OL Policies backend. Execute ONLY Prompt 9.

MANDATORY RULES:
- Policy Contract PDF must be legally accurate.
- Use the unified print engine from previous modules.
- Commit and push; tick checkbox.

SCOPE:
1. Implement Policy Contract Template:
   - Variables: Policy Number, Date, Parties, Product, Terms, Schedule (Members/Benefits), Premium Schedule, Signatures.
   - Must include legal clauses from Parameters.
2. Implement Print Endpoints:
   - POST /api/v1/ol/policies/{id}/print-contract/
   - Generates PDF with watermark (DRAFT/ISSUED/SURRENDERED).
   - Returns document instance and download URL.
3. Implement Schedule of Benefits Printout:
   - Simple table of coverage details.
4. Audit all document generations.

TESTS:
- contract PDF generates with correct data
- watermark works for different statuses
- audit log created

GIT:
- commit: "feat(ol-policies): implement policy document printing"
- push; tick checkbox

FINAL OUTPUT: template vars, print endpoints, tests, commit hash, pushed branch.
```

---

## [ ] Prompt 10/12 — Integrations: Portal, Claims, Reinsurance, Notifications

```text
You are a senior Django integration engineer. Continue the ZIC OL Policies backend. Execute ONLY Prompt 10.

MANDATORY RULES:
- Clean seams; no tight coupling.
- Commit and push; tick checkbox.

SCOPE:
1. Claims Integration:
   - Expose policy data for claim registration (active coverage details).
   - Listen to ClaimSettled event; if claim exhausts policy (e.g., Death), update Policy status to CLAIM_SETTLED/TERMINATED.
2. Reinsurance Integration:
   - Expose Policy risk details (Sum Assured, Age, Occupation) for treaty allocation.
   - Emit PolicyIssued event with risk data.
3. Partner Portal:
   - Read-only access for linked partner: view policies, status, maturity date, basic details.
   - No sensitive financial data exposed unless authorized.
4. Notifications:
   - PolicyIssued (Email/SMS to client).
   - PolicyLapsed (Warning).
   - PolicyMaturingSoon (Reminder).
5. Dashboard Hooks:
   - Active Policy Count, Premium Income (Annualized), Lapsed Ratio.

TESTS:
- portal scoping denies unauthorized access
- claim settlement updates policy status
- notifications emitted

GIT:
- commit: "feat(ol-policies): integrate claims reinsurance portal and notifications"
- push; tick checkbox

FINAL OUTPUT: integration map, events, tests, commit hash, pushed branch.
```

---

## [ ] Prompt 11/12 — Full Lifecycle Test Matrix & Audit

```text
You are a senior Django QA engineer. Continue the ZIC OL Policies backend. Execute ONLY Prompt 11.

MANDATORY RULES:
- Every policy path must be tested.
- Audit consistency is mandatory.
- Commit and push; tick checkbox.

SCOPE:
1. Integration Test Matrix:
   - Happy Path: Quote -> Proposal -> Payment -> Policy Issued -> Endorsement -> Maturity.
   - Lapse Path: Policy -> Missed Premium -> Lapsed -> Reinstated -> Active.
   - Termination Path: Policy -> Surrender -> Paid Out -> Terminated.
   - Loan Path: Policy -> Loan -> Repayment -> Closure.
2. Permission Matrix:
   - Verify actions gated by ol_policies permissions.
3. Audit Matrix:
   - Verify every state change has an audit row.
   - Verify immutable snapshot integrity.
4. Idempotency Tests:
   - Issuance retry.
   - Command retries (lapse/maturity).

GIT:
- commit: "test(ol-policies): full lifecycle test matrix and audit verification"
- push; tick checkbox

FINAL OUTPUT: coverage summary, audit evidence, test results, commit hash, pushed branch.
```

---

## [ ] Prompt 12/12 — Seed Scenarios, Docs, & Release Verification

```text
You are a senior Django release engineer. Complete the ZIC OL Policies backend. Execute ONLY Prompt 12.

MANDATORY RULES:
- Seed realistic data covering all states.
- Document everything.
- Commit and push; tick final checkbox; all 12 checkboxes ticked at the end.

SCOPE:
1. Seed 8 Policies via different paths:
   - Active Policy (Freshly Issued).
   - Lapsed Policy (Past Grace Period).
   - Reinstated Policy (History preserved).
   - Surrendered Policy (With payout history).
   - Matured Policy (Completed term).
   - Policy with Active Loan.
   - Cancelled Policy (Free-look period).
   - Paid-Up Policy.
2. Attempt failure scenarios:
   - Issue Policy without First Premium (Must fail BR-03).
   - Reinstate outside window (Must fail).
   - Surrender within first year (Must fail per parameters).
3. Documentation:
   - docs/OL_POLICIES_USER_GUIDE.md
   - docs/OL_POLICIES_ADMIN_GUIDE.md
   - docs/OL_POLICIES_API.md
   - docs/OL_POLICIES_STATE_MACHINE.md
4. Final verification: Backend lint/typecheck/tests green.

GIT:
- commit: "feat(ol-policies): seed scenarios docs and release"
- push; if blocked create feature/ol-policies-complete and push
- tag v1.2.0-ol-policies-backend if tagging convention exists

FINAL OUTPUT:
Return the FULL policies backend summary:
- models
- endpoints
- lifecycle logic
- BR-03/BR-04 enforcement
- integration points
- seed results
- failure proofs
- audit consistency
- docs added
- all 12 checkboxes ticked
- commit hash/tag
- pushed branch
- next recommended module: OL Policies UI + Group Life Backend.
```

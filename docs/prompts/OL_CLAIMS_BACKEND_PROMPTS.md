OL CLAIMS BACKEND — FULL PROMPT SERIES (12 Prompts)
## [x] Prompt 1 — Save Series File + Claim Domain Foundation
You are a senior Django insurance platform engineer. Build the ZIC Ordinary Life Claims backend. The user pasted the FULL 12-prompt series at once.

META-INSTRUCTION (HIGHEST PRIORITY):
1. Before coding, create docs/prompts/OL_CLAIMS_BACKEND_PROMPTS.md and save ALL 12 prompts EXACTLY as provided, each with a checkbox "[ ] Prompt N — title".
2. Commit and push that file immediately.
3. Execute ONLY Prompt 1 now; when green, tick its checkbox, commit, then proceed to Prompt 2. Never merge or skip prompts.

MANDATORY RULES:
- No blocking questions; make senior insurance/finance assumptions and document them.
- Every material state change must be audited with actor, before/after, reason, source channel.
- All user-facing errors must use the structured Error Coach shape with resolution steps.
- Commit and push at the end of each prompt.

OBJECTIVE:
Create the OL Claims bounded context and core domain foundation.

BUSINESS CONTEXT:
The Claim lifecycle involves Registration (Notification), Documentation, Assessment, Requisition, Approval, and Settlement. Claims must interact with Policies (status updates), Loans (offsets), Reinsurance (recovery), and Finance (payments).

SCOPE:
1. Produce docs/OL_CLAIMS_DESIGN.md defining:
   - Claim lifecycle state machine (REGISTERED -> ASSESSMENT -> REQUISITION -> APPROVED -> SETTLED).
   - Claimant types (Policyholder, Insured, Dependent).
   - Integration map: Policies, Members, Loans, Reinsurance, Front Office (Payments), Approvals.
2. Create Django app `ol_claims`.
3. Implement core models:
   - OLClaim: claim_number unique, policy_ref, claim_type, claimant_ref, claim_date, admitted_date, status, cause_of_claim, description, assessment_notes, fraud_flag, registered_by, admitted_by, settled_date.
   - OLClaimant: type (POLICYHOLDER, INSURED, DEPENDENT), relationship, name, identity_number, age, gender, audit fields.
   - OLClaimItem: claim_ref, benefit_type, sum_assured, calculated_amount, approved_amount, adjustment_reason, audit fields.
   - OLClaimDocument: claim_ref, document_type, file_reference, mandatory_flag, uploaded_by, upload_date.
   - OLClaimFileNote: claim_ref, note_text, created_by, created_at.
   - OLClaimRequisition: claim_ref, requisition_number, amount, bank_details_json, status.
4. Register permissions: ol_claims.view, register, assess, requisition, approve, settle, cancel, print.
5. Register domain events: ClaimRegistered, ClaimAssessed, ClaimDocumentUploaded, ClaimRequisitioned, ClaimApproved, ClaimSettled, ClaimCancelled.
6. Add structured error registry: CLAIM_POLICY_INACTIVE, CLAIM_DUPLICATE, CLAIM_WAITING_PERIOD_ACTIVE, CLAIM_BENEFIT_NOT_COVERED, CLAIM_MANDATORY_DOC_MISSING, CLAIM_AMOUNT_EXCEEDS_LIMIT.
7. Add base API skeleton: list, retrieve.
8. Add admin table-first registration.

TESTS:
- model creation and relationships
- status enum validation
- error shape contract
- permissions registered

GIT:
- commit: "feat(ol-claims): save prompt series and create claim domain foundation"
- push; if blocked create feature/ol-claims-foundation and push; tick checkbox

FINAL OUTPUT: design summary, models, permissions, events, error codes, tests, commit hash, pushed branch.

## [x] Prompt 2 — Claim Parameters & Validation Engine
You are a senior Django insurance configuration engineer. Continue the ZIC OL Claims backend. Execute ONLY Prompt 2 from the saved series file.

MANDATORY RULES:
- Claim behavior must be driven by OL Claim Setup parameters.
- Commit and push; tick checkbox.

OBJECTIVE:
Implement parameter consumption and the validation engine for claim registration.

SCOPE:
1. Implement Claim Validation Service:
   - validate_eligibility(policy, member, claim_type, claim_date):
     - Checks Policy Status (Active, Lapsed with grace, Paid-up).
     - Checks Claim Type compatibility with Product (e.g., Death claim on Accident-only policy).
     - Checks Waiting Period (from OL Parameters): if claim_date < policy_start_date + waiting_period_days, raise CLAIM_WAITING_PERIOD_ACTIVE.
     - Checks Duplicate (from OL Parameters): queries DB for existing settled claims of same type for same member. Raise CLAIM_DUPLICATE.
2. Implement Options Endpoints:
   - GET /api/v1/ol/claims/options/types/
   - GET /api/v1/ol/claims/options/reasons/
   - GET /api/v1/ol/claims/options/benefits/?policy_id=
   - GET /api/v1/ol/claims/options/members/?policy_id=
3. Benefit Calculation Base Service:
   - calculate_max_claimable(policy, benefit_type): returns the theoretical max based on sum assured, ratios, loadings, and discount rules from OL Product/Rider setup.
4. Audit all validation checks for compliance.

TESTS:
- duplicate detection works
- waiting period enforcement
- ineligible policy blocking
- benefit calculation base returns correct max value
- options endpoints return labeled data

GIT:
- commit: "feat(ol-claims): implement claim validation engine and parameters"
- push; tick checkbox

FINAL OUTPUT: validation logic, options endpoints, tests, commit hash, pushed branch.

## [x] Prompt 3 — Claim Registration & Creation
You are a senior Django insurance engineer. Continue the ZIC OL Claims backend. Execute ONLY Prompt 3.

MANDATORY RULES:
- Registration creates the initial claim record and claimant info.
- Idempotency is required.
- Commit and push; tick checkbox.

OBJECTIVE:
Implement the claim registration endpoint with full validation.

SCOPE:
1. POST /api/v1/ol/policies/{policy_id}/claims/
   - Payload: claim_type, claim_date, cause_of_claim, claimant_details (if dependent), description.
   - Idempotency Key: X-Idempotency-Key.
2. Processing Steps:
   - Run Validation Service (Prompt 2).
   - Create OLClaim in status REGISTERED.
   - Create OLClaimant record.
   - Create initial OLClaimItem(s) with `calculated_amount` derived from Benefit Calculation Base Service.
   - If "Waiver of Premium" claim: set policy-level flag to suspend future premium commitments (integration seam).
   - Emit ClaimRegistered event.
3. Return structured error on failure with resolution steps.
4. Audit creation with actor, claim_date, claim_type.

TESTS:
- successful creation populates claim, claimant, and items
- validation errors return teachable shape
- duplicate claim blocked
- idempotency check returns existing claim
- audit row created

GIT:
- commit: "feat(ol-claims): implement claim registration and creation"
- push; tick checkbox

FINAL OUTPUT: endpoint, validation logic, tests, commit hash, pushed branch.

## [x] Prompt 4 — Documents & Mandatory Progression Blocking
You are a senior Django insurance engineer. Continue the ZIC OL Claims backend. Execute ONLY Prompt 4.

MANDATORY RULES:
- Mandatory documents must block progression to Assessment/Requisition.
- Commit and push; tick checkbox.

OBJECTIVE:
Implement document upload and verification logic.

SCOPE:
1. Document Requirements Engine:
   - get_required_documents(claim_type): returns list of document types from OL Claim Setup parameters.
   - Check Mandatory Status: Query OLClaimDocument for uploaded files matching required types.
   - Return `all_mandatory_uploaded: boolean`.
2. API Endpoints:
   - POST /api/v1/ol/claims/{id}/documents/: Upload file, link to claim.
   - GET /api/v1/ol/claims/{id}/documents/: List with mandatory status.
3. Progression Guard:
   - Service `can_proceed_to_assessment(claim_id)` returns false if mandatory docs are missing, raising CLAIM_MANDATORY_DOC_MISSING.
4. Audit document uploads.

TESTS:
- upload creates record
- missing mandatory doc blocks progression
- completed doc list allows progression
- audit log captures upload

GIT:
- commit: "feat(ol-claims): implement documents and mandatory blocking"
- push; tick checkbox

FINAL OUTPUT: document endpoints, progression guard, tests, commit hash, pushed branch.

## [x] Prompt 5 — Medical & Underwriting Integration
You are a senior Django insurance engineer. Continue the ZIC OL Claims backend. Execute ONLY Prompt 5.

MANDATORY RULES:
- Some claims require medical review before assessment.
- Commit and push; tick checkbox.

OBJECTIVE:
Implement medical requirement triggering and status updates.

SCOPE:
1. Medical Trigger Service:
   - evaluate_medical_requirements(claim):
     - Based on Claim Type, Age, Amount, and OL Parameters.
     - Sets `medical_status` on claim (NONE, PENDING, CLEARED, REJECTED).
2. API Endpoints:
   - POST /api/v1/ol/claims/{id}/medical/require/: Flags claim for medical.
   - POST /api/v1/ol/claims/{id}/medical/result/: Records outcome (Cleared/Rejected/Loading).
3. Integration:
   - If Medical is PENDING, block transition to ASSESSMENT.
   - If Rejected, transition claim to REJECTED status.
   - If Loading, update `calculated_amount` on claim items based on underwriting rules.

TESTS:
- medical trigger sets status correctly
- pending medical blocks assessment
- medical result updates claim calculation or status
- integration with OL Underwriting module (if present) or standalone handling

GIT:
- commit: "feat(ol-claims): implement medical and underwriting integration"
- push; tick checkbox

FINAL OUTPUT: medical logic, endpoints, tests, commit hash, pushed branch.

## [x] Prompt 6 — Assessment & Fraud Logic
You are a senior Django insurance engineer. Continue the ZIC OL Claims backend. Execute ONLY Prompt 6.

MANDATORY RULES:
- BR-11: Claim amount cannot be revised above the calculated maximum.
- Commit and push; tick checkbox.

OBJECTIVE:
Implement the assessment phase, fraud flagging, and amount adjustment.

SCOPE:
1. POST /api/v1/ol/claims/{id}/assess/
   - Payload: assessed_amount, assessment_notes, fraud_flag_reason, waiver_of_premium_days (optional).
   - Permission: ol_claims.assess.
   - Validation: `assessed_amount` <= `calculated_amount` (max). Raise CLAIM_AMOUNT_EXCEEDS_LIMIT if breached.
2. Actions:
   - Update `approved_amount` = `assessed_amount`.
   - Update status -> ASSESSED.
   - Set fraud flags if provided.
   - Apply "Waiver of Premium" logic: update policy status or create specific premium waiver commitment entries.
3. File Notes:
   - POST /api/v1/ol/claims/{id}/notes/: Add internal notes visible only to staff.
4. Emit ClaimAssessed event.

TESTS:
- assessment updates amount and status
- amount exceeding limit blocked
- fraud flag recorded
- waiver of premium integration triggers policy update
- audit row created

GIT:
- commit: "feat(ol-claims): implement assessment and fraud logic"
- push; tick checkbox

FINAL OUTPUT: assessment endpoint, validation rules, tests, commit hash, pushed branch.

## [x] Prompt 7 — Loan Offset & Financial Interaction
You are a senior Django finance engineer. Continue the ZIC OL Claims backend. Execute ONLY Prompt 7.

MANDATORY RULES:
- Outstanding policy loans must be deducted from the claim payout.
- Commit and push; tick checkbox.

OBJECTIVE:
Implement loan offset logic within the claim assessment/settlement flow.

SCOPE:
1. Loan Offset Service:
   - calculate_net_payout(claim_id):
     - Fetches `approved_amount` from claim items.
     - Queries OL Loans module for `active_loan_balance` on the policy.
     - Net Payout = Approved Amount - Active Loan Balance.
     - If Loan Balance > Approved Amount, Net Payout = 0; Loan becomes fully offset/closed.
2. Integration:
   - During Settlement, trigger loan offset transaction.
   - Create Loan Offset record in OL Loans module.
   - Reduce Loan Principal to zero.
3. API Endpoint:
   - GET /api/v1/ol/claims/{id}/financial-summary/: returns Gross Amount, Loan Offset, Net Payout.

TESTS:
- loan balance correctly deducted
- net payout calculated accurately
- loan offset transaction created in OL Loans module
- summary endpoint returns correct breakdown

GIT:
- commit: "feat(ol-claims): implement loan offset and financial interaction"
- push; tick checkbox

FINAL OUTPUT: offset logic, financial summary, tests, commit hash, pushed branch.

## [x] Prompt 8 — Requisition & Payment Link
You are a senior Django finance engineer. Continue the ZIC OL Claims backend. Execute ONLY Prompt 8.

MANDATORY RULES:
- Claims must raise a Requisition for payment.
- Requisition links to Front Office payment seam.
- Commit and push; tick checkbox.

OBJECTIVE:
Implement claim requisition generation and payment approval hook.

SCOPE:
1. POST /api/v1/ol/claims/{id}/raise-requisition/
   - Payload: bank_details (partner or claimant), narration.
   - Validation: Status must be ASSESSED. Net Payout > 0.
   - Action:
     - Create OLClaimRequisition record.
     - Link to Front Office payment module (event or direct API call depending on architecture).
     - Status -> REQUISITIONED.
2. Approval Integration:
   - Trigger approval workflow if Net Payout > Threshold.
   - Listen for Approval Approved event -> Update claim status -> APPROVED.
   - Listen for Approval Rejected event -> Update claim status -> REJECTED.

TESTS:
- requisition creation links to payment seam
- approval event updates claim status
- rejection event updates claim status
- audit trail captures requisition details

GIT:
- commit: "feat(ol-claims): implement requisition and payment link"
- push; tick checkbox

FINAL OUTPUT: requisition endpoint, approval integration, tests, commit hash, pushed branch.

## [x] Prompt 9 — Settlement, Discharge & Policy Updates
You are a senior Django insurance engineer. Continue the ZIC OL Claims backend. Execute ONLY Prompt 9.

MANDATORY RULES:
- Settlement is the final state; updates policy status.
- Commit and push; tick checkbox.

OBJECTIVE:
Implement claim settlement and policy lifecycle updates.

SCOPE:
1. POST /api/v1/ol/claims/{id}/settle/
   - Triggered after Payment Confirmation from Front Office.
   - Action:
     - Status -> SETTLED.
     - Settled Date = Now.
     - Emit ClaimSettled event.
2. Policy Update Service:
   - on_claim_settled(claim):
     - If Death/Maturity: Update Policy Status -> CLAIM_SETTLED or MATURITY_SETTLED.
     - If Partial (e.g., Critical Illness): Update Benefit Rider status -> EXHAUSTED.
     - Update Policy Sum Assured if required by product rules.
3. Reinsurance Linkage:
   - Emit ClaimSettled event with data needed for Reinsurance Treaty calculation (Retention, Ceded Amount).

TESTS:
- settlement updates claim status and date
- policy status updates correctly based on claim type
- reinsurance data payload emitted
- audit row created

GIT:
- commit: "feat(ol-claims): implement settlement discharge and policy updates"
- push; tick checkbox

FINAL OUTPUT: settlement endpoint, policy updates, tests, commit hash, pushed branch.

## [x] Prompt 10 — List, Detail, KPI & Export APIs
You are a senior Django API engineer. Continue the ZIC OL Claims backend. Execute ONLY Prompt 10.

MANDATORY RULES:
- Table-first; names never UUIDs.
- KPIs must be real-time and filterable.
- Commit and push; tick checkbox.

OBJECTIVE:
Implement complete claim list, detail, dashboard, and export APIs.

SCOPE:
1. GET /api/v1/ol/claims/ list:
   - Columns: claim_number, policy_number, policyholder_name, claim_type, claim_date, admitted_date, amount, status badge, allowed_actions.
   - Filters: status, claim_type, product, branch, date range, fraud_flag.
   - Search: claim_number, policy_number, name.
2. GET /api/v1/ol/claims/{id}/ detail:
   - Header, claimant info, items, documents, file notes, assessment, financial summary, audit timeline.
   - Allowed actions based on status/permission.
3. GET /api/v1/ol/claims/kpis/ dashboard:
   - Total Claims, Outstanding Amount, Settled Amount (Period), Pending Assessment Count.
4. CSV export respecting filters.

TESTS:
- list columns and display names
- filters/search work
- KPI math correct
- detail includes children and allowed actions
- export respects filters

GIT:
- commit: "feat(ol-claims): implement claim list detail KPI and export APIs"
- push; tick checkbox

FINAL OUTPUT: endpoint contract, KPI rules, tests, commit hash, pushed branch.

## [ ] Prompt 11 — Integrations: Portal, Notifications & Documents
You are a senior Django integration engineer. Continue the ZIC OL Claims backend. Execute ONLY Prompt 11.

MANDATORY RULES:
- Clean seams; no tight coupling.
- Portal strictly read-only and scoped.
- Commit and push; tick checkbox.

OBJECTIVE:
Complete integrations around claims.

SCOPE:
1. Partner Portal:
   - Read-only endpoints scoped to linked partner.
   - Allow claim registration via portal (with restricted fields).
   - Sanitized errors.
2. Notifications:
   - ClaimRegistered, ClaimAssessed, ClaimSettled events.
   - Hook into notification center for SMS/Email alerts.
3. Documents:
   - Discharge Voucher generation (print endpoint).
   - Uses unified print engine.
   - Watermark logic for CANCELLED/REJECTED.

TESTS:
- portal scoping denies other partners
- notification events emitted once
- discharge voucher generates PDF
- watermark logic correct

GIT:
- commit: "feat(ol-claims): integrate portal notifications and documents"
- push; tick checkbox

FINAL OUTPUT: integration map, events, tests, commit hash, pushed branch.

## [ ] Prompt 12 — Seed Scenarios, Full Test Matrix, Docs & Release
You are a senior Django release engineer. Complete the ZIC OL Claims backend. Execute ONLY Prompt 12.

MANDATORY RULES:
- Seed realistic data covering all states.
- Prove every error path and business rule is enforced.
- Commit and push; tick final checkbox; all 12 checkboxes ticked at the end.

OBJECTIVE:
Seed scenarios, run full test matrix, document, and release.

SCOPE:
1. Seed exactly 10 claims via different paths:
   1 Death claim (Full Settlement)
   2 Critical Illness (Partial Settlement)
   3 Pending Medical
   4 Rejected (Missing Docs)
   5 Rejected (Waiting Period)
   6 Duplicate Claim (Blocked)
   7 Fraud Flagged
   8 Loan Offset Claim
   9 Waiver of Premium Claim
   10 Reversed/Cancelled
2. Attempt and catch failure scenarios with proof payloads:
   - Inactive policy
   - Duplicate claim
   - Waiting period violation
   - Amount exceeding limit
3. Documentation:
   - docs/OL_CLAIMS_USER_GUIDE.md
   - docs/OL_CLAIMS_ADMIN_GUIDE.md
   - docs/OL_CLAIMS_API.md
   - docs/OL_CLAIMS_ERROR_CODES.md
4. Final verification: backend lint/typecheck/tests green; mark series complete in saved prompt file.

GIT:
- commit: "feat(ol-claims): seed scenarios docs and release"
- push; if blocked create feature/ol-claims-complete and push
- tag v1.8.0-ol-claims-backend if tagging convention exists

FINAL OUTPUT:
Return the FULL claims backend summary:
- models
- endpoints
- validation rules
- integration points
- seed results
- failure proofs
- audit consistency
- docs added
- all 12 checkboxes ticked
- commit hash/tag
- pushed branch
- next recommended module: OL Claims UI, then Group Credit Backend.

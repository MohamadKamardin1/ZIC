# Ordinary Life Phase 6 — Policy Issuance and Servicing

## Scope

Phase 6 implements the service-owned post-underwriting lifecycle for Ordinary Life. The service layer now covers first-premium readiness, policy issuance, immutable issuance snapshots, premium schedules, installment obligations, payment allocation, endorsements, renewals, cancellations, lapse and grace handling, reinstatement, reactivation, and maturity.

The implementation preserves the legacy lifecycle service for compatibility while exposing `OrdinaryLifePolicyService` as the production workflow surface. All material transitions are executed inside database transactions and are protected by row locks, state guards, explicit actor validation, and idempotency keys where the operation creates a financial or policy transaction.

## Issuance contract

A proposal can be issued only when it has approved underwriting, business approval, a settled first-premium obligation, and a valid canonical party relationship. Issuance creates the following records atomically:

| Record | Purpose |
| --- | --- |
| `OLPolicy` | Current policy aggregate and product-version reference |
| `OLPolicyParty` | Effective-dated policy party links and identity snapshots |
| `OLPolicySnapshot` | Immutable product, plan, benefits, riders, and rating snapshot |
| `OLBeneficiary` and `OLBeneficiaryAllocation` | Beneficiary declarations and effective allocations |
| `OLPremiumSchedule` | Current frequency, total, currency, and installment count |
| `OLPremiumInstallment` | Due-date and amount schedule, including final rounding adjustment |
| `OLPaymentObligation` | Policy-owned installment obligations |
| `OLPolicyTransaction` | Issuance provenance and before/after aggregate state |
| `OLPolicyStatusHistory` and `OLWorkflowEvent` | Local lifecycle history |
| Central audit event | Cross-platform compliance record |

The service rejects duplicate policy issuance and requires active beneficiary allocations to total exactly 100 percent. The policy uses the selected quotation version and stores a product snapshot so later configuration changes cannot rewrite historical coverage or premium facts.

## Payment allocation

Payment allocation is exact and receipt-reference idempotent. A receipt cannot allocate more than the obligation’s outstanding balance, cannot use a mismatched currency, and cannot be allocated twice under the same external reference. Allocation updates the obligation and, when linked to an installment, the installment status and allocated amount in one transaction. The first-premium obligation must be fully paid before issuance; subsequent installment obligations are linked directly to the generated installment record.

## Endorsements

Endorsements are requested, submitted, approved, and applied through explicit service methods. The original issuance snapshot is never mutated. Each applied endorsement records before and after snapshots, effective date, actor, reason, transaction provenance, and an idempotency key. Future-dated endorsements are represented as effective-dated records and do not silently rewrite the current policy before their effective date.

## Renewals and reinstatements

Renewal and reinstatement requests have explicit statuses and are linked to their generated payment obligations. A request must be submitted and approved before application. The service requires the related renewal or arrears obligation to be fully paid before applying the request. Successful application updates the policy only through a policy transaction and retains the request, payment, status-history, workflow, and audit records.

## Status transitions

Policy status changes are restricted to service-owned operations. Lapse requires an overdue unpaid policy obligation; cancellation requires a valid effective date and a non-empty reason; maturity cannot occur before the contractual end date; and reactivation requires an eligible grace/lapsed state with no outstanding due obligations. Every transition writes a status-history record, workflow event, central audit event, and a typed policy transaction in one atomic unit.

| Operation | Guard | Transaction type |
| --- | --- | --- |
| Issue | Approved proposal, settled first premium, valid snapshots and allocations | `ISSUANCE` |
| Lapse | Overdue unpaid obligation | `STATUS_CHANGE` |
| Grace / Reactivation | Eligible current status and payment conditions | `STATUS_CHANGE` |
| Cancellation | Active, grace, or lapsed policy; valid date and reason | `CANCELLATION` |
| Maturity | Current date at or after contractual end date | `MATURITY` |
| Endorsement | Approved request and effective-date rules | `ENDORSEMENT` |
| Renewal | Approved request and paid renewal obligation | `RENEWAL` |
| Reinstatement | Approved request and paid arrears obligation | `REINSTATEMENT` |

## Schema additions

The additive Phase 6 migration adds installment linkage to payment obligations, transaction source/correlation/external provenance, endorsement snapshots and applied transaction linkage, and explicit renewal and reinstatement request aggregates. The payment-obligation constraint remains exactly-one-parent: an obligation belongs to either a proposal or a policy, never both or neither.

## Compatibility and assumptions

The existing legacy lifecycle service remains available under its original module and is exported as `LegacyOrdinaryLifeWorkflowService`. The new service is exported as `OrdinaryLifePolicyService` and the compatibility alias `OrdinaryLifeWorkflowService`. Legacy proposal and commitment records are not silently converted into the new payment-obligation model; new production issuance uses the Phase 5 approved-proposal and first-premium path.

Policy transitions return the updated policy aggregate, while payment, endorsement, renewal, reinstatement, and transaction-oriented operations return their respective domain records. This keeps caller state coherent while preserving access to the detailed transaction history through related managers.

## Verification

The Phase 6 service module contains 22 focused tests covering issuance artifacts, first-premium and beneficiary gates, payment allocation idempotency, endorsement approval and snapshots, lapse and cancellation, renewal payment gating, reinstatement, maturity, and transaction persistence. Django checks and migration consistency checks pass, Ruff passes on all Phase 6 files, and the complete backend regression suite passes with **409 tests**.

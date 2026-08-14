# Ordinary Life Phase 5 — Application, Quotation, Underwriting, and Approval Services

## Scope

Phase 5 implements the service-owned Ordinary Life intake and risk workflow on top of the Phase 3 domain schema and Phase 4 reference-data controls. The service layer is the only supported owner of application, quotation, underwriting, medical-evidence, and proposal-approval transitions. Serializers and views must not mutate lifecycle state directly.

## Service surface

`OrdinaryLifeApplicationService` provides the following operations:

| Operation | Responsibility |
| --- | --- |
| `create_application` | Creates an intake record using canonical `partners.Partner` references for intermediary, policyholder, life assured, and optional payer. |
| `submit_application` | Validates active canonical parties and required declarations, then moves `DRAFT` to `SUBMITTED`. |
| `create_quotation` | Creates a legacy-compatible quotation projection and immediately calculates immutable quotation version 1. |
| `calculate_quotation` | Validates product version, plan, age, term, frequency, rate band, and riders; creates or reuses a deterministic immutable quotation version. |
| `submit_quotation` | Requires a current immutable quotation version and moves `DRAFT` to `SUBMITTED`. |
| `convert_quotation_to_proposal` | Converts only a submitted, unexpired quotation and preserves the selected quotation version as the proposal snapshot reference. |
| `start_underwriting` | Opens a one-to-one underwriting case and materializes medical requirements from product underwriting rules. |
| `record_medical_result` | Records medical evidence against a requirement while leaving verification to a separate action. |
| `verify_medical_requirement` | Moves uploaded evidence to `VERIFIED` only when a result exists. |
| `record_health_declaration` | Creates a versioned declaration and response set with duplicate-question protection. |
| `assess_risk` | Enforces medical evidence completion, records an append-only decision event, and updates proposal underwriting state. |
| `submit_proposal_for_approval` | Uses the shared approval engine and configuration-driven approval requirement. |
| `approve_proposal` | Moves an approved underwriting proposal to business-approved state and creates the first-premium obligation idempotently. |
| `complete_business_approval` / `reject_business_approval` | Bridges shared `ApprovalRequest` decisions back to the proposal workflow. |
| `reopen_underwriting` | Reopens a declined or postponed case only with a reason and preserves the previous decision in decision history. |

## Transition guards

The following guards are enforced transactionally:

- An application must contain declarations before submission.
- All canonical application parties must be active and available.
- A quotation can only be calculated or revised while it is `DRAFT`.
- Product version effective dates, age limits, term limits, payment frequencies, plan limits, and rate-band coverage are validated before calculation.
- A quotation must have a current immutable version before submission or proposal conversion.
- Conversion rejects expired quotations and records the exact quotation version on the proposal.
- An underwriting case cannot approve while any medical requirement is unresolved.
- Medical requirements cannot be verified without a recorded result.
- Underwriting decisions are restricted to `APPROVED`, `REFERRED`, `DECLINED`, and `POSTPONED`.
- Reopening is limited to declined or postponed cases and requires a non-empty reason.
- First-premium obligation creation is idempotent under a proposal row lock.

## Quotation calculation contract

The baseline calculation is a deterministic level-premium calculation:

```text
annual base premium = sum assured × selected rate-band rate
annual rider premium = sum assured × each selected rider premium rate
annual premium = annual base premium + annual rider premium
installment premium = annual premium ÷ payment-frequency divisor
```

All monetary values are rounded to two decimal places using `ROUND_HALF_UP`. The hash input includes normalized inputs, calculated outputs, and a product-version snapshot. Repeating identical inputs reuses the existing version; changing a material input creates a new version and never rewrites the prior snapshot.

## Approval integration

The service uses the shared `ApprovalService` with:

```text
module: ORDINARY_LIFE
entity_type: OLProposal
action: APPROVE
```

The configurable key is:

```text
APPROVAL_REQUIRED_ORDINARY_LIFE_OLPROPOSAL_APPROVE
```

If the setting is absent or false, the service completes business approval directly after underwriting approval. If true, a pending `ApprovalRequest` is created and the proposal remains pending until the request is approved or rejected through the service bridge.

## Audit and workflow history

Every material service transition writes `OLWorkflowEvent` history. The service also calls the central audit framework with actor, action, before-state, after-state, reason, correlation context, and source channel inherited from the current request context. Underwriting decision changes additionally write append-only `OLUnderwritingDecisionEvent` rows.

## Migration

Migration `0005_olunderwritingdecisionevent.py` adds the append-only underwriting decision history table and an index on underwriting case and event time.

## Verification

The Phase 5 test module contains seven tests covering canonical intake validation, deterministic quotation-version reuse and revision, rate/frequency guards, unresolved medical evidence blocking, configurable approval integration, underwriting reopen history, and central audit evidence.

The full backend suite passes with **387 tests** passing.

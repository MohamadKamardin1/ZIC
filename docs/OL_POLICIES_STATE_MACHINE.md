# ZIC Ordinary Life Policies — State Machine

## State model

The policy status is a controlled catalog value. The status graph is parameterized by OL Policy Status records, while the services below enforce the business guards that cannot be represented by a simple transition list.

```text
Proposal + fully funded first premium
                 |
                 v
              ACTIVE
        ________|____________________________
       |        |       |         |          |
       v        v       v         v          v
    LAPSED   SURRENDER_  MATURED_  CLAIM_   CANCELLED
       |      PENDING    PENDING   SETTLED      |
       |        |        PAYMENT                |
       |        |           |                    |
       |        v           v                    |
       |    SURRENDERED   MATURED               |
       |
       +--> ACTIVE       (reinstatement)
       +--> PAID_UP

ACTIVE -- maturity without action --> EXPIRED
```

`TERMINATED` is a terminal status used by an authorized terminal business process. `CANCELLED`, `EXPIRED`, `MATURED`, `SURRENDERED`, and `CLAIM_SETTLED` are terminal from the policy servicing perspective unless a separately authorized business process explicitly reopens the contract.

## Transition guards

| From | To | Guard | Audit/domain event |
| --- | --- | --- | --- |
| Eligible proposal | `ACTIVE` | Proposal status eligible, selected plan exists, first-premium commitment is completed and fully funded, and no existing policy link | `PolicyIssued` |
| `ACTIVE` | `LAPSED` | An unpaid policy commitment has passed its parameterized lapse date | `PolicyLapsed` |
| `LAPSED` | `ACTIVE` | Within active reinstatement window, payment of outstanding premium/interest/penalty is sufficient, and medical clearance exists when required | `PolicyReinstated` |
| `LAPSED` | `PAID_UP` | Active paid-up setup permits conversion, eligibility thresholds are met, and a paid-up rate applies | `PolicyPaidUp` |
| `ACTIVE` | `SURRENDER_PENDING` | Surrender setup exists, minimum tenure/premium ratio is met, no active loan remains, and a surrender-value factor applies | `PolicySurrenderRequested` |
| `SURRENDER_PENDING` | `SURRENDERED` | Surrender payment requisition is settled by the payment-owning workflow | `PolicySurrenderPaid` |
| `ACTIVE` | `MATURED_PENDING_PAYMENT` | Maturity date is due, maturity setup permits creation, and maturity claim has not already been created | `PolicyMaturityClaimCreated` |
| `MATURED_PENDING_PAYMENT` | `MATURED` | Required documents and approval gates are complete, payment reference is supplied, and maturity requisition is paid | `PolicyMaturityPaid` |
| `ACTIVE` | `EXPIRED` | Maturity date is reached and no maturity action is taken | `PolicyExpired` |
| `ACTIVE` | `CANCELLED` | A reason is supplied; free-look refund is calculated when within the configured period | `PolicyCancelled` |
| Any permitted active state | `CLAIM_SETTLED` | Claims integration submits an exhausting claim type and the event has not already been applied | `PolicyClaimSettledApplied` |
| Active policy | `TERMINATED` | Authorized terminal business process completes | Terminal process event |

## Commands and timing

`process_policy_lapses` evaluates active unpaid commitments against the grace envelope and is safe to rerun. `process_policy_expiry` moves eligible active policies to `EXPIRED` when the maturity date is reached and no maturity action exists. `process_policy_maturity` creates maturity claims for policies at or near maturity according to the active maturity setup. All commands accept `--as-of YYYY-MM-DD` for reproducible operations and testing.

## Endorsement overlay

An endorsement does not replace a status transition. It is an immutable material-change record layered on the current policy state. Premium, term, member, address, beneficiary, and benefit changes retain before/after snapshots and are blocked in lapsed, expired, and cancelled states unless the relevant reinstatement guard has been satisfied.

## Idempotency rules

| Operation | Retry behavior |
| --- | --- |
| Issue policy | Returns the existing policy linked through proposal `policy_ref`; no duplicate children or `PolicyIssued` event |
| Lapse batch | A non-active policy is skipped; one `PolicyLapsed` event and audit row remain |
| Reinstatement | Only a lapsed policy can be reinstated; settled commitments and one transition audit are retained |
| Maturity batch | Existing non-declined maturity claim is returned; no duplicate claim or creation event |
| Surrender request | Existing pending-payment surrender request is returned |
| Claim settled ingress | The external claim key/event id is applied once |
| Notification/reminder enqueue | Stable external keys and unique notification constraints prevent duplicates |

## Audit invariant

Every material change must produce a `PolicyAuditLog` row with policy, actor, before snapshot, after snapshot, reason, source channel, and correlation id when available. The corresponding central governance audit entry records the action and state change. Domain events use the policy UUID as aggregate identity and carry the policy number and human-readable references for consumers.

A release is not complete if a state changes without a policy audit row, if a before snapshot is missing for a material change, if a terminal state has an allowed outgoing transition, or if an idempotent retry creates an additional domain event or child record.

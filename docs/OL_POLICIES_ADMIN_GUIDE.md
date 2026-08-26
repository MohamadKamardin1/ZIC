# ZIC Ordinary Life Policies — Administrator Guide

## Module ownership

The OL Policies bounded context owns the issued policy contract, its snapshot children, servicing endorsements, lifecycle transitions, policy finance records, maturity claims, policy audit history, and policy-facing integration seams. It does not replace the proposal, commitment, front-office payment, claims, or unified document engines. Those systems remain linked through stable references and domain events.

## Required configuration

Administrators should configure the following before enabling production policy operations. All rules are effective-dated and should be changed by creating or activating a new parameter version rather than modifying historical values used by an issued contract.

| Configuration area | Operational purpose |
| --- | --- |
| OL Policy Status and transitions | Defines allowed lifecycle transitions and terminal states |
| OL Grace Period | Defines warning, grace, pre-lapse, and lapse dates by premium frequency |
| OL Reinstatement Window | Defines the permitted period, payment requirement, medical clearance, interest, and penalty |
| OL Surrender Setup and Surrender Value Rates | Defines eligibility, charges, payout calculation, and product dimensions |
| OL Paid-Up Setup and Paid-Up Rates | Defines lapse conversion eligibility and reduced sum assured |
| OL Loan System Setup and Loan Interest Control | Defines loan eligibility, limits, repayment choices, interest, and capitalization |
| Maturity Claim Setup | Defines automatic claim creation, document/approval gates, and payout method |
| OL product and plan configuration | Supplies plan scope, premium frequency, product flags, and policy snapshot inputs |
| Document templates and branding | Supplies active contract/schedule layouts and company identity for PDFs |
| Numbering rules | Supplies policy, commitment, and front-office requisition numbering where configured |

A parameter must be active and effective for the processing date. If more than one row applies, the resolver uses the most specific matching product/plan scope and the latest effective version. Keep scopes unambiguous; overlapping active rows in the same scope are rejected by model validation.

## Permissions

The permission seed command registers the standard policy actions:

```bash
python manage.py seed_ol_policy_permissions
```

| Permission | Use |
| --- | --- |
| `ol_policies.view` | List, retrieve, KPI, export, and read-only history access |
| `ol_policies.create` | Issue a policy from an eligible proposal |
| `ol_policies.service` | Lifecycle servicing and operational policy actions |
| `ol_policies.endorse` | Create and retrieve servicing endorsements |
| `ol_policies.cancel` | Cancel a policy and initiate any configured refund |
| `ol_policies.reinstate` | Reinstate a lapsed policy |
| `ol_policies.print` | Generate and retrieve policy contract and schedule documents |
| `ol_policies.configure` | Manage policy-specific configuration and administration |

Superusers bypass the module permission checks. Normal users should be assigned only the actions required for their role. API permissions are enforced server-side and must not be inferred from hidden frontend buttons.

## Batch operations

Run lifecycle commands with an explicit processing date for controlled backfills or with the default local date for daily jobs:

```bash
python manage.py process_policy_lapses --as-of 2026-08-26
python manage.py process_policy_expiry --as-of 2026-08-26
python manage.py process_policy_maturity --as-of 2026-08-26
```

Each command is idempotent. Repeating a run does not create a second lifecycle event, duplicate maturity claim, or duplicate transition audit row. Batch jobs should be scheduled by the platform operations layer with monitoring and a persisted run log.

## Release seed and verification

The full demonstration dataset is created with:

```bash
python manage.py seed_ol_policy_scenarios --json
```

The command creates an operator user, seeds permissions and baseline policy parameters when needed, issues policies through the BR-03 service path, and exercises the available lifecycle services. It returns the eight policy numbers, their final states, and failure-proof objects. It is safe to run repeatedly because stable business keys are used for seed records and existing policy numbers are reused.

The surrender scenario intentionally models the boundary between policy valuation and payment ownership: it creates a `SurrenderRequest` and front-office requisition, then marks the seeded requisition as paid so the sample policy is `SURRENDERED`. Production settlement should be performed by the payment-owning workflow, not by bypassing policy controls.

## Audit and incident controls

For every material change, verify both the domain `PolicyAuditLog` and the central governance `AuditLog`. The policy audit row must contain the policy, event type, source channel, reason, before snapshot, after snapshot, and actor when a user initiated the action. Domain events should have the same aggregate policy identifier and should be unique for idempotent operations.

If a batch or API retry reports success but changes no data, inspect the corresponding event and audit counts. If a retry creates a second policy, maturity claim, surrender request, or loan record, stop the job and treat it as a release-blocking integrity incident.

## Snapshot integrity

Never update an issued policy by copying current quotation or proposal values. Upstream records remain useful for provenance, but the policy contract snapshot and policy child records are the source of truth. Use an endorsement for a material change. Before approving a migration or data repair, compare the policy `contract_snapshot` and relevant child rows with the signed document instance and audit history.

## Document operations

`POLICY_CONTRACT` and `POLICY_SCHEDULE` use the shared document engine. Before enabling print actions, confirm that the active templates are present, the branding configuration is complete, `ol_policies.print` is assigned to the operator role, and the storage backend is writable. Generated instances must retain the source policy, template version, generator, timestamp, checksum, and page count.

## Troubleshooting

| Symptom | First checks | Corrective action |
| --- | --- | --- |
| Issuance is blocked | Proposal status, selected plan, first-premium commitment status and balance | Complete the first-premium posting path; do not force policy creation |
| Lapse did not occur | Commitment due date, balance, frequency, active grace row | Correct the commitment or effective-dated grace configuration, then rerun with `--as-of` |
| Reinstatement is blocked | Window dates, medical flag, outstanding amount, interest/penalty | Complete the configured payment and clearance requirements |
| Surrender is blocked | Minimum months/premiums, payment ratio, active loan, rate row | Resolve eligibility or configure the product/plan rate scope |
| Loan is blocked | Product flag, cash value, configured percentage/amount limits | Correct product cash value or loan setup; never override the service guard |
| Maturity is not created | Maturity date, policy status, active maturity setup and gates | Activate the correct maturity setup and process again |
| PDF generation is blocked | Active template, branding, print permission, storage | Fix configuration and retry; preserve the failed correlation ID |

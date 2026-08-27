# ZIC Ordinary Life Claims Administrator Guide

## Administration model

The Claims module is a controlled bounded context. Administrators configure business behavior in OL Claim Setup and maintain the operational permissions used by staff, rather than changing claim data directly in the database. The browser can request an action, but the backend remains authoritative for eligibility, document requirements, medical rules, fraud controls, amount limits, loan offsets, approval thresholds, settlement, and policy updates.

The Claims permission family is:

| Permission | Responsibility |
|---|---|
| `ol_claims.view` | View claim lists, details, timelines, financial summaries, and evidence metadata. |
| `ol_claims.register` | Register claims and upload evidence. |
| `ol_claims.assess` | Perform medical and financial assessment, fraud review, notes, and waiver capture. |
| `ol_claims.requisition` | Raise and review payment requisitions. |
| `ol_claims.approve` | Approve or reject claim payment decisions where the workflow grants that action. |
| `ol_claims.settle` | Confirm payment and settle a claim. |
| `ol_claims.cancel` | Cancel an eligible claim. |
| `ol_claims.print` | Render and download the branded discharge voucher. |

The idempotent permission seeder is `python3 manage.py seed_ol_claim_permissions`. It is safe to rerun and should be executed as part of deployment or environment bootstrap. Use least privilege for operational groups; superuser access is a troubleshooting capability, not a replacement for role design.

## Parameter governance

Configure the following through OL Claim Setup before opening the module to users: claim type and category, calculation basis, duplicate-check rule, waiting period, payable-to rules, mandatory document types, approval requirement, claim reasons, medical limits, claim statuses and transitions, discharge types, and correspondent types. Every effective-dated change should have an effective start date, an optional end date, an active flag, a clear description, and an approval trail where the organization’s governance policy requires it.

A parameter change should be made prospectively. Do not edit historical values in a way that changes the meaning of an already assessed or settled claim. The claim stores snapshots for material decisions, including settlement amounts, policy updates, reinsurance retention/cession data, waiver periods, and loan-offset allocations.

The payment approval threshold is read from the configured system parameter `OL_CLAIM_PAYMENT_APPROVAL_THRESHOLD`. If the amount requires approval, the requisition links to a Governance `ApprovalRequest`; it must not be manually marked approved in the claim record.

## Operational controls

| Control | Administrator action |
|---|---|
| Duplicate protection | Keep duplicate rules aligned with the claim event and claimant identity recorded in the policy. Test a sample duplicate before activating a new claim type. |
| Waiting periods | Confirm the period is measured from the policy risk commencement date and test a boundary date on both sides of the threshold. |
| Mandatory documents | Require only documents that staff can actually upload and review. Test missing and uploaded cases before activation. |
| Medical thresholds | Confirm medical limits and review outcomes are effective-dated and compatible with the claim type. |
| Fraud controls | Require an explanation whenever the fraud flag is enabled and retain the decision in the audit timeline. |
| Financial controls | Reconcile approved item amounts, loan offsets, repayments, requisitions, and payment references before settlement. |
| Policy updates | Review the policy update snapshot after settlement, including terminal status, partial benefit reduction, and rider exhaustion. |
| Documents | Keep exactly one approved active discharge-voucher template for the Claims document type and verify the branding configuration. |

## Audit and event review

Every material claim state change is written to the central append-only `AuditLog` with actor, before state, after state, reason, source channel, correlation/request context, and readable claim representation. Durable `DomainEvent` rows record lifecycle events including `ClaimRegistered`, `ClaimAssessed`, `ClaimMedicalRequired`, `ClaimLoanOffsetApplied`, `ClaimRequisitioned`, `ClaimApproved`, `ClaimRejected`, `ClaimSettled`, and `ClaimCancelled`.

For an investigation, begin with the claim number and inspect the claim detail timeline, then correlate the requisition number, Front Office payment reference, document instance, governance approval, loan repayment number, and policy update snapshot. UUIDs are internal correlation keys only; operational reports should use claim and policy numbers.

## Integrations

Claims reads the issued policy and OL Claim Setup parameters. Payment requests are linked to the Front Office requisition model. Approval-required payments use the Governance approval service. Loan offsets use OL Policies `PolicyLoan` and `PolicyLoanRepayment` ledger records. Discharge vouchers use the unified Documents app and its branding/template version. Claim domain events feed the notification center and email/SMS outbox integrations.

Each integration is designed to be retry-safe. Before retrying a failed request, inspect the claim, requisition, approval, and audit state. A successful earlier attempt should be returned as an idempotent result rather than repeated as a second financial mutation.

## Seed and verification operations

The final realistic scenario command is:

```bash
cd /home/ubuntu/ZIC_git/backend
python3 manage.py seed_ol_claim_scenarios --json
```

The command creates or reuses exactly ten claims identified by the `OL-CLAIM-SEED-` prefix and demonstrates full settlement, partial settlement, pending medical review, missing-document rejection, waiting-period rejection, duplicate blocking, fraud review, loan offset, waiver of premium, and cancellation. It also captures failure proofs for inactive policy, duplicate claim, waiting-period violation, and amount exceeding the calculated limit. It is idempotent and does not create a second claim or apply a second loan offset on rerun.

Use the following release checks:

```bash
python3 manage.py check
python3 manage.py makemigrations --check --dry-run
python3 -m compileall -q apps/ol_claims apps/documents
python3 manage.py test apps.ol_claims.tests.test_foundation --noinput --verbosity 1
```

The command output is an operational evidence record. Retain it with deployment notes, especially the `failure_proofs`, `claim_count`, `states`, and `loan_offset` fields.

## Incident response

If the claim list is empty, first verify `ol_claims.view`, active policy visibility, and database migrations. If an action is blocked, read the structured `error_code`, field errors, and resolution steps before changing parameters. If a document says the template is pending, activate an approved template and configure company branding. If a settlement appears duplicated, stop processing, inspect the requisition and settlement event, and reconcile Front Office payment status before taking further action.

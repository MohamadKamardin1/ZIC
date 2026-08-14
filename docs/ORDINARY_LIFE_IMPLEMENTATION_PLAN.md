# ZIC Ordinary Life Insurance Implementation Plan

## Purpose

This plan defines the full implementation sequence for the Ordinary Life Insurance module. The module will be delivered from the existing partial backend outward: first the bounded-context foundation and lifecycle services, then the complete API and test surface, followed by the Lit-enhanced frontend workspaces. Each phase must leave the repository in a coherent, testable state and must not mix unrelated module changes into its commits.

## Delivery principles

The implementation will use explicit state machines instead of scattered status mutations. All material transitions will pass through service methods that enforce permissions, partner scope, validation, idempotency, audit logging, and transaction boundaries. Financial values will use decimal arithmetic with currency and rounding rules made explicit. Historical records, approval decisions, documents, notes, and policy servicing events will remain traceable and will not be overwritten by convenience updates.

The existing ZIC response envelope, IAM permissions, report-category visibility, partner linkage, central audit framework, dashboard workspace, and partner workflows are integration foundations. Ordinary Life will extend those foundations rather than create parallel authorization, audit, notification, or navigation systems.

## Phase roadmap

| Phase | Scope | Exit criteria |
|---|---|---|
| 1. Baseline | Reconcile the written specification, full video workflow, existing Ordinary Life files, dashboard navigation, shared models, and integration boundaries. | A verified gap register, source-of-truth field map, dependency map, and list of existing partial work are documented. |
| 2. Domain design | Define terminology, actors, lifecycle states, transition guards, invariants, ownership rules, partner scope, and assumptions. | State diagrams and transition tables exist for quotation, application, underwriting, approval, policy, endorsement, renewal, cancellation, and reinstatement. |
| 3. Core models | Complete product and plan configuration, applications, applicants/lives, nominees, risk answers, quotations, documents, notes, approvals, policies, insured members, premium schedules, endorsements, renewals, and servicing records. | Models have correct relations, constraints, indexes, validation, historical fields, and safe deletion behavior. |
| 4. Migrations and administration | Generate/apply migrations, seed controlled reference data, add model validation, register audit hooks, and configure read/write-safe Django admin interfaces. | `check`, migration drift, seed verification, admin smoke checks, and audit creation checks pass. |
| 5. Intake and underwriting | Implement application creation, duplicate detection, quotation calculation, risk capture, document requirements, underwriting review, referral rules, approval routing, rejection/return, and resubmission. | Every transition is service-owned, permission-aware, auditable, idempotent, and covered by acceptance tests. |
| 6. Policy and financial lifecycle | Implement issuance, policy numbering, premium schedules, installment allocation, receipts/hooks for payments, commission integration hooks, endorsements, renewals, cancellations, lapses, and reinstatement. | Decimal calculations, rounding, effective dates, pro-rata rules, financial status transitions, and concurrency behavior are tested. |
| 7. Supporting operations | Implement document metadata and storage hooks, notes, approvals, tasks, notifications, audit history, partner visibility, reporting-category hooks, and operational timeline views. | Users see only permitted and partner-scoped records; every material action has history and operational follow-up. |
| 8. API surface | Build serializers, queryset scoping, filters, ordering, permissions, views, routes, bulk actions, and consistent response envelopes for the full workflow. | API contracts are documented and verified with authenticated, unauthorized, cross-partner, invalid-transition, and pagination tests. |
| 9. Backend quality | Add model, service, state-machine, calculation, permission, API, audit, concurrency, and end-to-end journey tests. | Full backend suite passes with no migration drift, targeted coverage is strong for transition and money paths, and lint is clean. |
| 10. Frontend design | Define Ordinary Life navigation, list/detail/application/underwriting/policy workspaces, Lit component boundaries, table contracts, form patterns, timeline patterns, and white/charcoal ZIC visual rules. | Screen map, interaction map, API-to-screen data contract, and responsive/accessibility decisions are documented. |
| 11. Frontend implementation | Build product and quotation screens, application wizard, document and nominee panels, underwriting queue, approval workspace, policy detail, premium schedule, endorsement/renewal/cancellation forms, and activity timeline. | All visible actions call real APIs, have loading/error/empty/success states, and deep-link to canonical records. |
| 12. Integration and delivery | Validate complete journeys, run frontend/backend gates, document the module, review the diff, commit in coherent increments, and push to `sultan`. | Full journey passes from quotation to issued policy and servicing; final branch, commit hashes, tests, migrations, and known assumptions are reported. |

## Required state machines

### Quotation and application

The expected path is `DRAFT → QUOTED → APPLICATION_STARTED → SUBMITTED → UNDER_REVIEW`. A submission may transition to `RETURNED`, `REJECTED`, or `APPROVED`; a returned application may be corrected and resubmitted, while a rejected application requires an explicit re-open or new application policy rather than an implicit status reset.

### Underwriting and approval

Underwriting will distinguish automated validation, manual review, referral, decision, and approval. High-risk or incomplete records cannot be issued. Approval decisions will capture actor, timestamp, reason, conditions, and any required follow-up task.

### Policy lifecycle

The initial policy path will support `PENDING_ISSUANCE → ACTIVE`, with controlled paths for `LAPSED`, `CANCELLED`, `EXPIRED`, and `REINSTATED`. Effective dates, premium status, payment allocation, and servicing events must remain consistent with the policy state.

### Servicing

Endorsements, renewals, cancellations, and reinstatements will use separate transaction records with effective dates, reasons, approval requirements, before/after snapshots, and audit references. Historical policy states will remain queryable.

## Functional coverage checklist

The completed module must support product configuration, quotation, application intake, individual-life details, beneficiaries/nominees, risk questions, required documents, document metadata and file hooks, duplicate checks, underwriting referrals, approval queues, policy issuance, policy number generation, premium schedules, installments, payment allocation hooks, commission hooks, policy documents, notes, activity history, endorsements, renewals, cancellation, lapse, reinstatement, notifications, tasks, audit events, role permissions, partner scope, search, filters, pagination, exports/hooks, and reporting-category integration points.

## Non-functional gates

Every backend phase must pass Django system checks, migration drift detection, relevant tests, Ruff on changed files, and `git diff --check`. Every frontend phase must pass TypeScript compilation, production bundling, route checks, responsive review, loading/error/empty-state review, and keyboard-accessibility review. Sensitive actions must require the existing permission and confirmation patterns. Financial operations must be transaction-safe and must not use floating-point arithmetic for money.

## Assumptions

The current platform uses Django and DRF for the backend, React with Lit-enhanced components for the frontend, the existing ZIC response envelope, UUID-backed records where established, and the central audit framework already delivered. Ordinary Life will use the existing partner master and linkage authorization rather than duplicate partner records. External payment, document storage, notification, and reporting providers will be integrated through adapter hooks until their dedicated connectors are enabled. Where the video demonstrates behavior without a complete written rule, the implementation will select the safest auditable behavior, document it, and keep the rule configurable where future business confirmation may be required.

## Commit strategy

The implementation should be committed in coherent increments, for example: `feat(ordinary-life): complete domain foundation`, `feat(ordinary-life): implement underwriting and approvals`, `feat(ordinary-life): implement policy and servicing lifecycle`, `feat(ordinary-life): add APIs and backend acceptance tests`, and `feat(ordinary-life): build interactive frontend workflows`. Each commit must exclude unrelated Ordinary Life experiments, generated databases/logs, and changes from other modules unless they are explicitly required integration changes.

## Definition of done

Ordinary Life is complete when a permitted user can create a quote, convert it to an application, capture all required applicant/nominee/risk/document data, submit it, route it through underwriting and approval, issue a policy, view premium and payment status, and perform approved endorsement, renewal, cancellation, lapse, and reinstatement actions. A permitted supervisor can inspect the full timeline and audit history. A partner-scoped user sees only eligible records. All actions are represented in the frontend with real API calls and durable backend state, and the complete regression and build gates pass before delivery to `sultan`.

## References

The implementation baseline is the authoritative ZIC system specification at `/home/ubuntu/ZIC_full_system_context_specification.md`, the full Vimeo walkthrough supplied by the user, and the existing repository contracts in `backend/` and `insurance-dashboard-ui/`.

---

**Document owner:** Manus AI
**Module:** ZIC Ordinary Life Insurance
**Status:** Planning baseline before implementation

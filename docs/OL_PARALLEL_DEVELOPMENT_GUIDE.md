# ZIC Ordinary Life Parallel Development Guide

## Purpose

This guide is the common starting point for seven parallel development chats working on the ZIC Ordinary Life module. The current OL Quotations work remains exclusively in this chat. It must not be edited by the seven parallel workstreams described below. One separate workstream explicitly owns OL Commitments, in addition to its closely related proposal and operations lifecycle. The goal is to complete each bounded module professionally while preserving a clean integration path, consistent permissions, parameter-driven behavior, auditability, accessibility, and project continuity.

Each chat must work in a separate Git worktree and branch. No chat may edit the same working directory as another chat, and no workstream may push directly to `sultan`.

> **Operating rule:** one chat, one worktree, one branch, one clearly bounded module scope.

## Repository baseline and security

The repository is the ZIC codebase:

```text
Repository: git@github.com:MohamadKamardin1/ZIC.git
Local baseline worktree: /home/ubuntu/ZIC_git
Backend: /home/ubuntu/ZIC_git/backend
Frontend: /home/ubuntu/ZIC_git/insurance-dashboard-ui
Integration branch: sultan
```

The configured SSH private key is already available in the development environment at:

```text
/home/ubuntu/.ssh/id_ed25519_zic
```

Do **not** print, copy, or paste the private key into chat, source files, logs, documentation, or commits. Use it only through `GIT_SSH_COMMAND`. The public key may be inspected locally if GitHub access needs to be diagnosed, but credentials and tokens must never be committed.

Before starting, every chat must fetch the latest integration branch:

```bash
cd <WORKTREE>
GIT_SSH_COMMAND='ssh -i /home/ubuntu/.ssh/id_ed25519_zic' git fetch origin
GIT_SSH_COMMAND='ssh -i /home/ubuntu/.ssh/id_ed25519_zic' git log -1 --oneline origin/sultan
```

The latest known shared baseline at the time this guide was written is:

```text
ea6f97d5e549c6ed660f145574ef8bf67c4038fe
fix(ol-quotations): complete finalization prerequisites
```

Always trust the freshly fetched `origin/sultan` over this recorded hash if another workstream has already been integrated.

## Important: separate chats do not share filesystem worktrees

A worktree created in one chat or sandbox is **not automatically visible in another chat or sandbox**. Therefore, every new module chat must bootstrap its own local clone and assigned worktree before reading or editing files. Do not assume that `/home/ubuntu/ZIC_ol_product` or any other path created by the coordinator exists in the new chat.

Paste and run the following shared bootstrap block in each new chat, replacing only `WORKTREE_PATH` and `FEATURE_BRANCH` with the values from the ownership table. It is safe to rerun: it refuses to overwrite an existing unrelated directory, reuses a correctly registered worktree, fetches the latest `origin/sultan`, and verifies that the assigned worktree is clean.

```bash
set -euo pipefail

WORKTREE_PATH=/home/ubuntu/ZIC_ol_product
FEATURE_BRANCH=feature/ol-product
REPO_PATH=/home/ubuntu/ZIC_git
REMOTE_URL=git@github.com:MohamadKamardin1/ZIC.git
SSH_KEY=/home/ubuntu/.ssh/id_ed25519_zic

if [ -f "$SSH_KEY" ]; then
  export GIT_SSH_COMMAND="ssh -i $SSH_KEY"
fi

if [ ! -d "$REPO_PATH/.git" ] && [ ! -f "$REPO_PATH/.git" ]; then
  if [ -e "$REPO_PATH" ]; then
    echo "Repository path exists but is not a Git repository: $REPO_PATH" >&2
    exit 1
  fi
  mkdir -p "$(dirname "$REPO_PATH")"
  git clone "$REMOTE_URL" "$REPO_PATH"
fi

cd "$REPO_PATH"
git fetch origin sultan

if git worktree list --porcelain | grep -Fq "worktree $WORKTREE_PATH"; then
  test "$(git -C "$WORKTREE_PATH" branch --show-current)" = "$FEATURE_BRANCH"
elif [ -e "$WORKTREE_PATH" ]; then
  echo "Path exists but is not a registered worktree: $WORKTREE_PATH" >&2
  exit 1
elif git show-ref --verify --quiet "refs/heads/$FEATURE_BRANCH"; then
  git worktree add "$WORKTREE_PATH" "$FEATURE_BRANCH"
elif git ls-remote --exit-code --heads origin "$FEATURE_BRANCH" >/dev/null 2>&1; then
  git worktree add "$WORKTREE_PATH" "$FEATURE_BRANCH"
else
  git worktree add -b "$FEATURE_BRANCH" "$WORKTREE_PATH" origin/sultan
fi

test "$(git -C "$WORKTREE_PATH" branch --show-current)" = "$FEATURE_BRANCH"
test -z "$(git -C "$WORKTREE_PATH" status --porcelain)"
printf 'Ready: %s on %s at %s\n' "$WORKTREE_PATH" "$FEATURE_BRANCH" "$(git -C "$WORKTREE_PATH" rev-parse --short HEAD)"
```

If the SSH key is not present in a separate chat, do **not** copy or paste a private key into chat. Instead, use the repository access method already approved for that environment, or ask the coordinator to attach/provision the repository. The module work must not start until the assigned branch and clean worktree have been verified.

## Worktree and branch setup

Run the following from the existing repository worktree. If a worktree already exists, do not delete it; coordinate with the owner instead.

```bash
cd /home/ubuntu/ZIC_git
GIT_SSH_COMMAND='ssh -i /home/ubuntu/.ssh/id_ed25519_zic' git fetch origin

git worktree add ../ZIC_ol_foundation -b feature/ol-foundation origin/sultan
git worktree add ../ZIC_ol_product -b feature/ol-product origin/sultan
git worktree add ../ZIC_ol_policy -b feature/ol-policy origin/sultan
git worktree add ../ZIC_ol_rating -b feature/ol-rating origin/sultan
git worktree add ../ZIC_ol_rider-agent-loan -b feature/ol-rider-agent-loan origin/sultan
git worktree add ../ZIC_ol_medical-claim -b feature/ol-medical-claim origin/sultan
git worktree add ../ZIC_ol-commitments-proposals-operations -b feature/ol-commitments-proposals-operations origin/sultan
```

Each chat must work only in its assigned directory:

| Chat | Worktree | Branch | Scope key |
|---|---|---|---|
| OL Foundation | `/home/ubuntu/ZIC_ol_foundation` | `feature/ol-foundation` | Core metadata, defaults, reference registries, shared OL infrastructure |
| OL Product | `/home/ubuntu/ZIC_ol_product` | `feature/ol-product` | Plan types, products, funds, product capabilities and target-market setup |
| OL Policy | `/home/ubuntu/ZIC_ol_policy` | `feature/ol-policy` | Surrender, paid-up, rate tables, health-questionnaire lifecycle, commitment status |
| OL Rating | `/home/ubuntu/ZIC_ol_rating` | `feature/ol-rating` | Premium, mortality, bonus, surrender-value, reserve, interest, charge and financial-rating setup |
| OL Rider/Agent/Loan | `/home/ubuntu/ZIC_ol_rider-agent-loan` | `feature/ol-rider-agent-loan` | Riders, rider rates, commissions, loans and loan interest controls |
| OL Medical/Claim | `/home/ubuntu/ZIC_ol_medical-claim` | `feature/ol-medical-claim` | Medical underwriting catalogs, facilities, practitioners, claim setup and transitions |
| OL Commitments/Proposals/Operations | `/home/ubuntu/ZIC_ol-commitments-proposals-operations` | `feature/ol-commitments-proposals-operations` | Commitment management, proposal conversion/lifecycle, approvals, documents and operational integrations |
| Current OL Quotations chat | `/home/ubuntu/ZIC_git` | coordinator-controlled | Quotation wizard, finalization, quotation lifecycle and quotation-specific fixes |

Push only to the assigned feature branch:

```bash
cd <WORKTREE>
GIT_SSH_COMMAND='ssh -i /home/ubuntu/.ssh/id_ed25519_zic' git push origin HEAD:<YOUR_FEATURE_BRANCH>
```

Never run `git push origin HEAD:sultan` from a parallel workstream. The coordinator will merge feature branches into an integration branch, run full gates, and push the verified result to `sultan`.

## Shared engineering contract

All seven chats must first inspect the existing implementation, tests, migrations, seed commands, permission registry, audit framework, frontend UI kit, option registry, SmartSelect, and documentation. Extend existing patterns instead of creating a second competing architecture.

The backend is Django 5 with Django REST Framework. The frontend is React, TypeScript, Vite, TanStack Query, React Hook Form/Zod patterns where already established, and the existing ZIC UI kit. All APIs are under `/api/v1/` and must use the existing authentication, permission, error-envelope, audit, pagination, and response-normalization conventions.

All user-facing foreign keys must expose human-readable display values. No OL page, table, badge, modal, error, API response, or E2E page may display a raw UUID. Use the existing display-field and `renderFk` conventions. All selectable reference data must be API-driven and parameter-driven; do not hardcode business choices in React components.

All mutations must be permission-gated, auditable, and validated on the server. A superuser is not a reason to remove permission checks. Before implementing a new permission, inspect the existing IAM metadata and permission constants. If a permission is missing, add it through the established permission registry, expose it through `/api/v1/iam/me/access`, enforce it in the backend view/service, and gate the frontend action with the same code.

Use the following permission categories as guidance, but confirm exact existing codes in the repository before coding:

| Operation | Required behavior |
|---|---|
| View/list/detail | Existing module/submodule view permission; unauthorized users receive 403 and do not see protected navigation/actions. |
| Create | Existing `ol_parameters.create` or the module-specific create permission. |
| Update | Existing module-specific update/manage permission. |
| Delete/deactivate | Existing delete/manage permission; prefer deactivation where the domain is effective-dated or referenced. |
| Approve/finalize/convert | Dedicated lifecycle permission, separate from edit permission. |
| Export/import | Dedicated export/import permission when present; validate every imported row. |
| Audit visibility | Existing governance/audit view permission; audit entries must not be editable by normal users. |

Every new or changed model must preserve effective dating, active/inactive state, uniqueness, overlap rules, decimal precision, foreign-key integrity, and transaction safety. Do not change seed data or unrelated onboarding behavior unless the module genuinely owns the data and the change is required for integrity.

## Required implementation sequence for every chat

### 1. Inventory before editing

Record the current state of the module: models, migrations, admin, serializers, services, URLs, permissions, audit events, seed commands, frontend routes, tables, forms, SmartSelect fields, tests, docs, and known gaps. Search before adding a duplicate model or endpoint.

### 2. Define the module contract

Write down the entities, relationships, fields, effective-date rules, statuses, permission codes, API endpoints, response shapes, option sources, and lifecycle transitions. Confirm whether an existing API is used by quotations, proposals, rating, claims, or other workstreams.

### 3. Implement backend first

Implement or complete models and migrations, serializers, service-level validation, API endpoints, admin management, permission enforcement, audit events, and parameter-driven seed data. Use clear field-level errors that explain the configured rule and the corrective action. Keep database writes transactional and idempotent.

### 4. Implement frontend second

Use the existing shell, DataTable, FilterBar, Modal/Drawer, FormGrid, DecimalInput, EditableGrid, Wizard, SmartSelect, toast, and error-normalization components. Add lazy-loaded routes, responsive layouts, dark-theme parity, keyboard support, loading/empty/error states, accessible labels, and permission-aware actions. Show names instead of IDs.

### 5. Add tests and documentation

Add backend model/service/API/permission/audit/seed tests and frontend rendering/form/permission/API/error tests. Add Playwright coverage for at least one complete module workflow. Document the API and operational management path. Do not claim a screen or endpoint is complete without a test or an explicit documented limitation.

### 6. Verify and hand off

Run focused tests first, then all applicable repository gates. Review `git diff --check`, inspect the changed-file list, remove temporary scripts and generated artifacts, write the handoff document, commit, and push the feature branch.

## Standard test gates

The exact commands may vary if package scripts differ, but every chat must report the commands actually run and their results. The normal gates are:

```bash
# Backend
cd <WORKTREE>/backend
python3 -m compileall apps/<owned_apps>
pytest -q apps/<owned_tests>
pytest -q

# Frontend
cd <WORKTREE>/insurance-dashboard-ui
pnpm exec tsc --noEmit
pnpm run lint
pnpm vitest run
pnpm run build
pnpm exec playwright test
```

If a full suite exceeds the available execution window, run it in a resumable shell and wait for completion. Never replace a failed gate with a claim that it was not relevant. Report unrelated pre-existing failures separately and prove that the owned focused suite passes.

## Module prompts

Copy one of the following prompts into the corresponding chat **after** creating its worktree. Each prompt includes the common rules but keeps the implementation scope isolated.

---

# Chat 1 — OL Foundation, Default Setup, and Shared Reference Infrastructure

```text
You are the senior Django/React engineer responsible only for the OL Foundation workstream.

WORKTREE AND BRANCH
Work only in /home/ubuntu/ZIC_ol_foundation on feature/ol-foundation. Start by fetching origin/sultan. Never edit another worktree and never push to sultan. Push only with:
GIT_SSH_COMMAND='ssh -i /home/ubuntu/.ssh/id_ed25519_zic' git push origin HEAD:feature/ol-foundation

MISSION
Complete the shared Ordinary Life foundation that all other OL workstreams depend on. Audit the existing OL parameter base classes, default setup, effective-date/status mixins, option-provider registry, quick-create registry, permission registry, audit integration, seed conventions, and shared frontend parameter infrastructure. Extend existing implementations; do not create competing registries or duplicate entities.

SCOPE
1. OL default setup and system/reference catalogs used by OL forms, including currencies, identity types, locations/regions, payment frequencies, payment modes, quote bases, premium factors, member relations, cover types, benefit types, and other existing shared choices.
2. Common parameter metadata: code, name, labels, descriptions, active flags, effective dates, ordering, currency and display conventions.
3. Server-side options and quick-create registry contracts, including labeled `{value, label, meta}` responses, search, pagination, inactive/effective-date filtering, duplicate detection, and permission-aware quick-create.
4. Shared audit source-channel behavior, especially QUICK_CREATE and normal CRUD audit events.
5. Admin and frontend OL Parameters navigation for the shared catalogs and a clean Drop Down Configuration management screen if the existing implementation is incomplete.
6. Seed command(s) for complete baseline shared data. Seeds must be idempotent, parameter-driven, realistic for Zanzibar Insurance Corporation, and safe to run repeatedly.

PERMISSIONS
Inspect the real IAM registry first. Enforce view/list, create, update, deactivate/delete, import/export, and audit-view permissions separately. Use the established system_parameters and ol_parameters permission codes where applicable, but do not assume a code without checking the repository. The frontend must read /api/v1/iam/me/access and hide mutation controls when permission is absent.

NON-OWNED AREAS
Do not implement product-specific screens, rating tables, policy setup, riders, loans, medical/claims, proposals, or quotation wizard behavior. Do not alter partner onboarding location semantics unless a shared location contract is demonstrably broken; document any required integration note instead.

DELIVERY
Implement backend models/API/admin/permissions/audit/seeds, then frontend route/table/modal/SmartSelect integration. Add tests for labels, active/effective filtering, search/pagination, quick-create validation and permission denial, idempotent seeds, CRUD/deactivation, audit records, and no-UUID rendering. Document the registry contract and seed command. Finish with full focused and repository gates, a handoff file at docs/parallel/OL_FOUNDATION_HANDOFF.md, a professional commit, and a pushed feature branch.
``` 

---

# Chat 2 — OL Product and Product Setup

```text
You are the senior Django/React engineer responsible only for OL Product Setup.

WORKTREE AND BRANCH
Work only in /home/ubuntu/ZIC_ol_product on feature/ol-product. Fetch origin/sultan first. Never edit another worktree or push to sultan. Push only with:
GIT_SSH_COMMAND='ssh -i /home/ubuntu/.ssh/id_ed25519_zic' git push origin HEAD:feature/ol-product

MISSION
Complete the parameter-driven OL product catalog and product setup so products and plans are usable by quotation, rating, rider, policy, and proposal services without hardcoded frontend choices.

SCOPE
1. Plan Types catalog and management.
2. OL Product setup: product code/name, plan type, insurance class, currency, entry ages, policy-term range, sum-assured range, premium frequencies, effective dates, active/status fields, and all capability toggles.
3. Product capability metadata: riders, loans, withdrawals, surrender, paid-up, bonus, investment-linked, joint-life, mortgage, PA, premium waiver, and any existing configured feature flags.
4. Plan tax configurations, target-market rules, risk categories, occupation risk limits, investment fund types, and investment funds where these belong to the existing product setup architecture.
5. Product/plan search APIs and option payloads used by OL quotations. Responses must include readable plan/product fields and authoritative constraints/defaults.
6. Admin, permission-aware frontend tables, detail forms, range validation, effective-date overlap validation, and realistic idempotent product seeds.

PERMISSIONS
Inspect and use existing ol_parameters view/create/update/deactivate/manage permissions. Product activation, deactivation, effective-date changes, and capability changes must be separately auditable. Do not bypass permissions because the user is a superuser.

NON-OWNED AREAS
Do not implement rate tables, policy surrender/paid-up rules, rider rate logic, claims, medical questions, proposal conversion, or quotation wizard behavior. Do not invent product choices in React; consume shared option APIs from the foundation workstream.

INTEGRATION CONTRACT
Preserve the product/version/plan identifiers and display fields consumed by quotation and rating code. If a contract is incomplete, add backward-compatible fields and document the exact endpoint and response shape rather than modifying quotation logic. Product minimums and maximums must be the same constraints exposed to OL quotation Step 2.

DELIVERY
Add/complete models, migrations, serializers, services, APIs, admin, permissions, audit, seeds, frontend routes/forms/tables, and tests. Cover CRUD, toggles, range validation, effective dates, option labels, inactive filtering, product search/pagination, and no UUID leakage. Write docs/parallel/OL_PRODUCT_HANDOFF.md, commit professionally, run focused and full gates, and push feature/ol-product.
```

---

# Chat 3 — OL Policy Setup and Policy Lifecycle Parameters

```text
You are the senior Django/React engineer responsible only for OL Policy Setup and policy lifecycle parameters.

WORKTREE AND BRANCH
Work only in /home/ubuntu/ZIC_ol_policy on feature/ol-policy. Fetch origin/sultan first. Never edit another worktree or push to sultan. Push only with:
GIT_SSH_COMMAND='ssh -i /home/ubuntu/.ssh/id_ed25519_zic' git push origin HEAD:feature/ol-policy

MISSION
Complete the OL policy-setup parameter screens and lifecycle configuration with effective-dated, overlap-safe, auditable rules that can be consumed by policy and quotation services.

SCOPE
1. Surrender Setup with minimum premiums, ratios, charge type/value, partial-surrender and approval controls.
2. Paid-Up Setup with eligibility rules, minimum requirements, and conversion basis.
3. Surrender Value Rate and Paid-Up Rate versioned tables with dimensions, row editors, CSV import/export, row-level errors, overlap warnings, totals, and filters.
4. Health Questions catalog and Health Questionnaire Builder with catalog selection, sequence/reordering, mandatory and trigger-medical flags, versioning, scope badges, threshold fields, effective dates, unsaved-change protection, and live preview.
5. Grace Period Notification Schedule with event, offset, channel, recipient.
6. Reinstallment/Reinstatement Window with lapse days, medical requirement, interest/penalty rates.
7. Commitment Status catalog and transition editor where present in the existing architecture.

PERMISSIONS
Use the existing ol_parameters and policy-setup permission codes after inspecting the IAM registry. Separate view, create/update, deactivate, import/export, version-create, and transition-management permissions. Audit all rate imports, version creation, rule changes, and transition edits.

NON-OWNED AREAS
Do not implement product setup, rating engine tables outside surrender/paid-up rates, riders, loans, medical/claims, proposals, or quotation wizard logic. Do not hardcode status, event, channel, or basis choices; use the authoritative option registry.

DATA INTEGRITY
Enforce effective-date overlap rules, version status transitions, decimal precision, dimension uniqueness, row-level validation, and transactional CSV imports. Preserve existing API contracts used by downstream policy and quotation services.

DELIVERY
Finish backend models/services/APIs/admin/audit/seeds and frontend DataTable/EditableGrid/modal/builder screens. Add tests for rate row CRUD, CSV error rendering, version creation, overlap warnings, questionnaire reorder/mandatory behavior, schedule/window validation, and permission gates. Write docs/parallel/OL_POLICY_HANDOFF.md, run focused and full gates, commit, and push feature/ol-policy.
```

---

# Chat 4 — OL Rating and Pricing Parameters

```text
You are the senior Django/React engineer responsible only for OL Product Rating and pricing parameters.

WORKTREE AND BRANCH
Work only in /home/ubuntu/ZIC_ol_rating on feature/ol-rating. Fetch origin/sultan first. Never edit another worktree or push to sultan. Push only with:
GIT_SSH_COMMAND='ssh -i /home/ubuntu/.ssh/id_ed25519_zic' git push origin HEAD:feature/ol-rating

MISSION
Complete the OL rating parameter module and rate-table editors so the backend rating engine remains the sole authority for premiums, benefits, projections, and financial calculations.

SCOPE
1. Premium Rates: version list, product/plan/effective-date/status metadata, dimension filters, row editor, CSV import/export, overlap warnings, version creation.
2. Mortality Rates by age/gender/smoker/year.
3. Joint Life Setup.
4. Reinstatement Interest Rate.
5. Bonus Rate.
6. Mortgage Interest Factor.
7. Installment Charge Rate.
8. Cash Surrender Value rate editor.
9. Reserve Loadings.
10. Any existing product-rating part-one or part-two entities not already covered above, including effective-date/status, product/plan relations, decimal precision, and calculation-basis metadata.

PERMISSIONS
Inspect and use existing rating view/create/update/deactivate/import/export/version permissions. Rate publication, activation, version creation, and imports must be permission-gated and audited. Do not allow frontend users to change calculated premiums directly.

NON-OWNED AREAS
Do not modify the core rating engine algorithm unless a proven contract defect prevents the parameter module from working. Do not implement product setup, policy setup, riders, loans, medical/claims, proposals, or quotation UI. If the quotation rating API needs a missing display/constraint field, document the contract request and make only a backward-compatible change owned by rating.

DATA INTEGRITY
Enforce row dimensions, effective-date overlaps, version statuses, precision, nonnegative/range rules, transactional CSV import, row-level errors, and deterministic ordering. Use backend calculation outputs in all tests; never duplicate premium formulas in React.

DELIVERY
Complete backend/API/admin/audit/seed data and frontend version lists, filters, EditableGrid editors, import/export, banners, precision inputs, and permission-aware actions. Add tests for each catalog, rate CRUD, CSV failures, overlap warnings, version creation, and no-UUID display. Write docs/parallel/OL_RATING_HANDOFF.md, run full gates, commit, and push feature/ol-rating.
```

---

# Chat 5 — OL Riders, Agent Commission, and Loan Setup

```text
You are the senior Django/React engineer responsible only for OL Rider Setup, Agent Management/Commission, and Loan Setup.

WORKTREE AND BRANCH
Work only in /home/ubuntu/ZIC_ol_rider-agent-loan on feature/ol-rider-agent-loan. Fetch origin/sultan first. Never edit another worktree or push to sultan. Push only with:
GIT_SSH_COMMAND='ssh -i /home/ubuntu/.ssh/id_ed25519_zic' git push origin HEAD:feature/ol-rider-agent-loan

MISSION
Complete rider, commission, and loan parameter setup with product/plan applicability, effective dating, overlap validation, audit, and parameter-driven frontend forms.

SCOPE
1. OL Riders catalog and detail form: category, benefit type, entry ages, terms, sum-assured limits, waiting period, standalone flag, underwriting requirement, effective dates, active/status.
2. OL Rider Rate version/table editor with CSV import/export and row-level validation.
3. Agent Commission Setup: agent/partner, product/plan, commission type/rate, priority, effective dates, overlap warnings, filters, and permission-gated CRUD.
4. OL Loan System Setup: basis, maximum percentage, minimum/maximum amounts, repayment options, effect on claim/surrender/maturity, approval toggle.
5. OL Loan Interest Control: rate, compounding frequency, grace days, penalty rate, capitalization toggle.
6. Partner/agent/product/plan/fund/rider display labels and option integration used by downstream quotation and proposal flows.

PERMISSIONS
Inspect the existing ol_parameters, partners, agent-management, and loan permission mappings. Separate view, create/update, deactivate/delete, import/export, and approval permissions. Commission and loan changes must be audited with actor, effective period, source, and before/after values.

NON-OWNED AREAS
Do not implement quotation wizard UI, product setup, policy setup, rating tables unrelated to riders/loans, medical/claims, or proposals. Reuse foundation and product option APIs; do not hardcode product, plan, agent, rider, benefit, or loan choices.

DATA INTEGRITY
Validate applicability, age/term/sum ranges, percentages, decimal precision, effective-date overlaps, rider synchronization flags, and product capability constraints. Preserve backward-compatible API contracts and use transactions for imports and multi-row mutations.

DELIVERY
Finish backend models/services/APIs/admin/audit/seeds and frontend DataTables, filters, modals, SmartSelect fields, rider/rate editors, import/export, and responsive/dark-theme UI. Add tests for rider validation, commission overlap warnings, loan percentage/toggle rules, CSV errors, permission visibility, labels, and audit events. Write docs/parallel/OL_RIDER_AGENT_LOAN_HANDOFF.md, run focused and full gates, commit, and push feature/ol-rider-agent-loan.
```

---

# Chat 6 — OL Medical Underwriting and Claims

```text
You are the senior Django/React engineer responsible only for OL Medical Underwriting and Claim Setup.

WORKTREE AND BRANCH
Work only in /home/ubuntu/ZIC_ol_medical-claim on feature/ol-medical-claim. Fetch origin/sultan first. Never edit another worktree or push to sultan. Push only with:
GIT_SSH_COMMAND='ssh -i /home/ubuntu/.ssh/id_ed25519_zic' git push origin HEAD:feature/ol-medical-claim

MISSION
Complete the OL medical underwriting and claims parameter module with human-readable catalogs, effective-dated rules, approval/status transitions, partner linkage, and auditable management screens.

SCOPE
1. Medical Codes catalog.
2. Medical Limits by code, age/sum-assured bands, limit type/amount, mandatory flag.
3. Personal Habit catalog and underwriting impact.
4. Medical History with severity, waiting period, exclusion/loading flags.
5. Medical Facility with facility type, registration, location/region, approval status, and partner linkage.
6. Medical Practitioners with specialty, license, facility relation, approval status, and partner linkage.
7. Claim Types with category, calculation basis, waiting period, document/approval flags.
8. Claim Reasons.
9. Claim Status with order, color, terminal flag, and transition editor.
10. Discharge Types with template code and variables.
11. Correspondent Types with channel and purpose.

PERMISSIONS
Inspect existing medical, claims, partner-linkage, and ol_parameters permissions. Separate view, create/update, deactivate, approve, transition-edit, and audit-view permissions. Facility/practitioner approval and claim-status transitions must not be available to users without the relevant permission.

NON-OWNED AREAS
Do not change partner onboarding location behavior, quotation wizard forms, rating formulas, policy setup, riders, loans, or proposal conversion. Use shared location/region and option APIs. Do not render raw partner, facility, practitioner, medical-code, or claim UUIDs.

DATA INTEGRITY
Validate codes, licenses, ranges, effective dates, status transitions, terminal-state rules, template variables, and partner linkage. Ensure inactive/expired options are excluded from selection endpoints while historical records remain readable.

DELIVERY
Complete backend models/services/APIs/admin/audit/seeds and frontend catalog tables, modals, status/transition editor, SmartSelect relations, approval badges, partner linkage display, and responsive accessibility behavior. Add tests for all screen render/save flows, transitions, facility/practitioner linkage, permission denial, inactive filtering, and no-UUID output. Write docs/parallel/OL_MEDICAL_CLAIM_HANDOFF.md, run focused and full gates, commit, and push feature/ol-medical-claim.
```

---

# Chat 7 — OL Commitments, Proposals, Conversion, Approvals, Documents, and Operations

```text
You are the senior Django/React engineer responsible only for OL Commitments, OL Proposals, and quotation-adjacent operational lifecycle behavior after quotation completion.

WORKTREE AND BRANCH
Work only in /home/ubuntu/ZIC_ol-commitments-proposals-operations on feature/ol-commitments-proposals-operations. Fetch origin/sultan first. Never edit another worktree or push to sultan. Push only with:
GIT_SSH_COMMAND='ssh -i /home/ubuntu/.ssh/id_ed25519_zic' git push origin HEAD:feature/ol-commitments-proposals-operations

MISSION
Complete the OL Commitments module and the OL proposal/operational lifecycle that consumes finalized quotations, without changing the OL quotation wizard’s plan, installment, funds, rider, financial, or finalization implementation owned by the current quotations chat.

SCOPE
1. OL Commitment setup and work queue: commitment types, statuses, due-date rules, required actions, assignment/ownership, priority, escalation, notification hooks, and links to proposal/policy/partner records. Extend existing commitment entities if present; do not create duplicates.
2. Commitment lifecycle UI/API with search, filters, pagination, status badges, due dates, overdue handling, completion/cancellation/return transitions, permission-aware actions, audit history, and operational dashboards.
3. Proposal list/work queue with search, filters, pagination, status badges, version and dates, agent/partner display fields, and permission-aware actions.
4. Conversion handoff from finalized quotation to proposal, including eligibility checks, partner verification/compliance requirements, duplicate prevention, idempotency, and clear errors.
5. Proposal detail/master-detail page with overview, applicant, plans, members, installments, funds, riders/benefits, financial snapshot, underwriting, documents, versions, approvals, commitments, and audit timeline.
6. Proposal lifecycle statuses, revise/version flow, approval-required routing, approve/reject/return actions, and state-transition validation.
7. Proposal print/document generation, template/version display, preview, PDF download, and document audit trail.
8. Operational integrations owned by commitments/proposals, including notifications, queues, dashboards, SLA/overdue indicators, and conversion audit evidence where existing architecture supports them.

PERMISSIONS
Inspect real IAM permissions and separate proposal view/create/update, convert, approve/reject/return, print/download, revise, delete, and audit permissions. Enforce both backend and frontend. A user may view a finalized quotation without necessarily being allowed to convert, approve, or print it.

NON-OWNED AREAS
Do not rewrite quotation wizard steps, quotation finalization prerequisite forms, rating calculations, product setup, policy parameters, riders/loans, medical/claims, or quotation-owned conversion behavior. Consume stable quotation APIs and document any contract gap. Never silently create a commitment or proposal when a transition fails; use idempotency and transactions.

DATA INTEGRITY
Preserve finalized quotation snapshots, version immutability, conversion links, partner verification rules, approval thresholds, document template versions, and audit source/channel. All FK fields need readable display values. Do not expose UUIDs in tables, detail tabs, errors, or generated documents.

DELIVERY
Complete backend models/services/APIs/admin/permissions/audit and frontend routes, commitment work queue/detail/lifecycle screens, proposal work queue/detail tabs, approval actions, conversion handoff contract, document preview/download, and responsive accessible UI. Add tests for commitment CRUD and transitions, due/overdue behavior, permissions, audit evidence, conversion success/blocked paths, duplicate/idempotency behavior, approval transitions, print generation, version snapshots, and no-UUID rendering. Write docs/parallel/OL_COMMITMENTS_PROPOSALS_OPERATIONS_HANDOFF.md, run focused and full gates, commit, and push feature/ol-commitments-proposals-operations.
```

## Continuity and handoff requirements

Every chat must create or update its own unique handoff file. Do not update a shared progress file from multiple worktrees because that creates avoidable merge conflicts. The handoff file must contain the following sections:

```markdown
# <Workstream> Handoff

## Status
Complete / partial / blocked.

## Branch and commit
Branch name, commit hash, push result, and baseline hash.

## Scope delivered
Backend entities, endpoints, permissions, audit, admin, seed commands, frontend routes/components, and documentation.

## API contract
Endpoints, request/response examples, pagination, display fields, option sources, error envelope, and compatibility notes.

## Permission matrix
View, create, update, deactivate/delete, import/export, approve/transition, print, and audit permissions.

## Seed and migration instructions
Exact commands, idempotency behavior, expected counts or labels, and any required environment setup.

## Tests and gates
Focused tests, full tests, typecheck, lint, build, E2E, and any warnings/failures.

## Integration dependencies
Contracts consumed from other workstreams and contracts exposed to downstream modules.

## Known gaps and follow-up work
Only verified gaps; do not hide failures.

## Manual QA path
Exact URL and steps for a user with the required permission and for a user without it.
```

Before committing, each chat must inspect its own diff:

```bash
cd <WORKTREE>
git diff --check
git status --short
git diff --stat
```

Do not commit temporary debug scripts, local databases, screenshots, `node_modules`, build output, credentials, or test artifacts. Use a focused commit message that names the workstream, for example:

```text
feat(ol): complete <workstream> parameter and lifecycle module
```

If the branch contains unrelated changes from another workstream, stop and report them instead of committing them. After pushing, report the exact branch and commit hash to the coordinator. Do not merge another chat’s branch yourself.

## Coordinator integration procedure

The coordinator should fetch and inspect each feature branch independently:

```bash
cd /home/ubuntu/ZIC_git
GIT_SSH_COMMAND='ssh -i /home/ubuntu/.ssh/id_ed25519_zic' git fetch origin
GIT_SSH_COMMAND='ssh -i /home/ubuntu/.ssh/id_ed25519_zic' git log --oneline --decorate -5 origin/feature/ol-foundation
```

Create an integration branch from the latest `sultan`, then merge in dependency order:

```bash
GIT_SSH_COMMAND='ssh -i /home/ubuntu/.ssh/id_ed25519_zic' git switch -c integration/ol-complete origin/sultan
GIT_SSH_COMMAND='ssh -i /home/ubuntu/.ssh/id_ed25519_zic' git merge --no-ff origin/feature/ol-foundation
git merge --no-ff origin/feature/ol-product
git merge --no-ff origin/feature/ol-policy
git merge --no-ff origin/feature/ol-rating
git merge --no-ff origin/feature/ol-rider-agent-loan
git merge --no-ff origin/feature/ol-medical-claim
git merge --no-ff origin/feature/ol-commitments-proposals-operations
```

Resolve conflicts only in the integration worktree. Preserve the most complete implementation, keep migrations ordered, and rerun the full backend/frontend gates after each conflict resolution. Verify that the OL Quotations chat’s APIs and frontend still pass their focused and E2E tests before pushing the final integration result to `sultan`.

## Final coordinator checklist

The integration is ready only when every workstream has a pushed branch and handoff file, migrations apply from a clean database, idempotent seeds run successfully, API options return labeled active/effective records, permissions deny unauthorized mutations, audit entries contain actor/action/source/reason, all OL tables and forms show names rather than UUIDs, frontend typecheck/lint/tests/build pass, backend full pytest passes, Playwright E2E passes, and the integrated working tree contains no temporary files.

The coordinator must record the final merge commit, test totals, seed command, tag if the project convention requires one, and any remaining verified gaps in the main OL project documentation.

## How to use this file

For each new chat, first paste the **shared repository kickoff and bootstrap block** from this document. The chat must clone or locate the repository in its own sandbox, create only its assigned worktree, fetch `origin/sultan`, and verify the assigned branch and clean state. Then paste exactly one module prompt from the sections above. Do not rely on worktree directories created by another chat.

At the start of every chat, require the agent to acknowledge its assigned worktree, branch, scope, non-owned areas, permissions, tests, and handoff file before editing. At the end, require the exact commit hash, pushed branch, test results, and known gaps. The coordinator should integrate the pushed feature branches only after reviewing their handoff files and running the full gates.

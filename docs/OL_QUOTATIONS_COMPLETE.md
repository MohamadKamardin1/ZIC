# Ordinary Life Quotations — Complete Module Summary

## Scope and bounded-context boundary

The **Ordinary Life Quotations** module owns the customer-specific quotation transaction from draft creation through parameter-driven rating, finalization, printable output, partner verification, and conversion readiness for the OL Proposals bounded context. It does not own product configuration, actuarial tables, partner master data, policy issuance, claims, or payment settlement. Those concerns remain in their respective bounded contexts and are consumed through stable model and event contracts.

The quotation aggregate is deliberately snapshot-oriented. Wizard changes remain editable while the quotation is a draft, while finalized versions preserve the values used for customer-facing calculations and documents. The proposal handoff carries immutable references and JSON snapshots so the next bounded context can begin without re-reading mutable quotation state.

## Wizard and handoff steps

| Step | Key | Primary endpoint | Completion rule |
|---|---|---|---|
| 1 | `1_personal_details` | `POST/PATCH /quotations/{id}/personal-details/` | Identity, date of birth, age, gender, smoker status, location, agent, and address are valid. |
| 2 | `2_plan_and_sub_products` | `POST /quotations/{id}/plans/` and plan configuration `PATCH` | At least one active product/plan is selected and every section passes product and parameter validation. |
| 3 | `3_member_coverage` | `GET/POST/PATCH/DELETE /quotations/{id}/members/` | Principal member is synchronized automatically; required dependents are valid and configured. |
| 4 | `4_installments` | `GET /installments/`, template, and configure endpoints | Each required installment configuration is either not applicable or configured with rate rows totaling 100%. |
| 5 | `5_investment_funds` | `GET/POST /quotations/{id}/investment-funds/` | Not applicable for non-investment-linked plans; otherwise each applicable plan has allocations totaling 100%. |
| 6 | `6_riders_and_benefits` | `GET/POST /quotations/{id}/riders/` | Optional rider and benefit selections pass effective-date, applicability, and benefit-basis rules. |
| 7 | `7_financial_details` | `POST /calculate/` and `GET /financial-details/` | A current premium calculation exists and its input fingerprint matches the quotation state. |
| 8 | `8_partner_verification` | `GET /partner-verification/` and `POST /partner-completion/` | A matching compliant partner is linked, or a completed individual onboarding application is converted to a compliant partner. |
| Handoff | Proposal conversion | `POST /convert-to-proposal/` | Quotation is finalized, unexpired, partner verified, and has no unresolved approval requirement. |

The `wizard-summary` endpoint remains the authoritative completion view for the frontend. Partner verification is a separate handoff readiness step and does not create a partner during Personal Details entry.

## Parameter-driven behavior

The module resolves all option lists and rating values from existing system and OL parameter/master-data models. Identity choices, gender, smoker status, quote basis, premium factor, payment frequencies, plan applicability, joint-life factors, mortgage factors, funds, riders, benefits, installment templates, paid-up values, surrender values, taxes, loadings, and expiry/approval defaults are not hardcoded in quotation API responses.

Product and plan applicability is effective-dated. When a configuration is scoped to both a product and plan, it takes precedence over product-only or global configuration. Inactive or expired master data is excluded from selection and rating. Missing mandatory rating data produces a clear blocking validation error rather than a silent actuarial fallback.

## Lifecycle and versioning

| Status | Meaning | Allowed transition |
|---|---|---|
| `DRAFT` | Editable quotation with zero or more completed wizard steps. | `FINALIZED`, `EXPIRED` |
| `FINALIZED` | Validated, calculated, reproducible quotation. | `CONVERTED`, `EXPIRED` |
| `CONVERTED` | Quotation handed off to an OL proposal skeleton. | None |
| `EXPIRED` | Quotation no longer eligible for customer-facing lifecycle actions. | None |

Finalization requires applicable wizard steps, a current financial summary, and a matching calculation fingerprint. Revisions create an immutable `OLQuotationVersion`, preserve the prior values, increment the active version, and return the quotation to editable draft state with recalculation required.

**BR-02** is enforced by version snapshots. Changes do not destroy the finalized values used by prior calculations, documents, or proposal handoffs.

Expiry is controlled by `OL_QUOTATION_DEFAULT_EXPIRY_DAYS`. Read operations expose effective expiry, while the batch expiry command persists eligible transitions and emits an expiry event.

## Partner verification and completion

Partner verification matches the quotation’s `identity_type`, `identity_number`, and `date_of_birth` against the partner master. The response includes the following values:

| Field | Meaning |
|---|---|
| `partner_exists` | A partner matched all three identity criteria. |
| `partner_id` | Matching partner UUID, or `null`. |
| `partner_number` | Matching partner number, or `null`. |
| `partner_display_name` | Display name assembled from the master record, or `null`. |
| `compliant` | `true` only when the matched partner has `status=ACTIVE` and `is_active=true`. |
| `missing_fields` | Fields present in the quotation but blank on the matched partner. |

A match links the partner to the quotation and sets `partner_verified=true` only when the partner is compliant. A non-compliant match remains visible to the user but cannot satisfy BR-01.

When no usable partner exists, the partner-completion endpoint accepts individual KYC values, merges them with quotation Personal Details, and delegates creation to the onboarding application service. The bridge creates an active onboarding draft, attaches the configured individual partner type, submits the application, runs review and compliance transitions, approves it with an explicit audit note, and invokes the canonical onboarding conversion method. Duplicate email, identity, or TIN checks remain owned by onboarding. The resulting partner is linked to both `partner` and the legacy-compatible `linked_partner` relationship on the quotation.

Completion is transactional. If onboarding validation, configured nested requirements, duplicate checks, or conversion fails, the quotation remains unverified and no partial quotation link is committed.

## BR-01 proposal conversion

A quotation can be converted only when all of the following are true:

1. The effective quotation status is `FINALIZED`.
2. The quotation is not expired.
3. `partner_verified=true` and a partner is linked.
4. `approval_required=false`.
5. The caller has `ol_quotations.convert` permission, unless the caller is a superuser.

Conversion locks the quotation, creates one `OLProposal` handoff record for the current finalized quotation version, and stores:

- the quotation foreign key;
- the immutable `OLQuotationVersion` foreign key;
- a canonical proposal number from the numbering engine;
- prospect details snapshot;
- selected plan/configuration snapshot;
- financial summary snapshot;
- creator and timestamps.

The proposal starts in `DRAFT` status because the full OL Proposals workflow is a separate bounded context. The quotation changes to `CONVERTED` only after proposal creation succeeds. A unique quotation/version constraint prevents duplicate handoffs for the same finalized version.

The conversion emits `QuotationConverted` and `ProposalCreated`, and central audit logging records the before state, after state, actor, source request metadata, and proposal identifier. The existing `/convert/` action remains as a compatibility alias for `/convert-to-proposal/`.

## Rating, print, and handoff provenance

The premium engine resolves effective rate rows by product, plan, gender, smoker status, age, term, frequency, and optional sum-assured bands. Joint-life, mortgage, rider, installment, loading, discount, tax, surrender, paid-up, bonus, and projection values come from configured OL data. Monetary values use Decimal arithmetic and explicit rounding.

Printable documents reference the quotation and source version plus the exact print-template version. A proposal handoff similarly references the finalized quotation version and copies the prospect, plans, and financial summary into JSON snapshots. These two provenance mechanisms ensure that later quotation edits or configuration changes cannot rewrite an already generated customer document or converted proposal handoff.

## Permissions and events

| Action | Permission code | Endpoint examples |
|---|---|---|
| View | `ol_quotations.view` | List, detail, verification, documents, versions |
| Update | `ol_quotations.update` | Wizard updates, partner completion, financial calculation |
| Print | `ol_quotations.print` | Print generation and draft preview |
| Finalize | `ol_quotations.finalize` | Finalize quotation |
| Revise | `ol_quotations.revise` | Revise finalized quotation |
| Expire | `ol_quotations.expire` | Persist expiry |
| Convert | `ol_quotations.convert` | Proposal conversion |

The seed command creates or updates the quotation permission catalog and role groups idempotently. Non-superusers remain subject to the platform’s visible-partner authorization scope.

The transactional outbox emits lifecycle events including `QuotationCreated`, `QuotationUpdated`, `QuotationPremiumCalculated`, `QuotationFinalized`, `QuotationExpired`, `QuotationVersionCreated`, `QuotationApprovalRequested`, `QuotationConverted`, `PartnerVerified`, `PartnerCompleted`, and `ProposalCreated`. Events carry aggregate identifiers, actor metadata, status transitions, and relevant snapshot/proposal references.

## Operational commands and quality gates

```bash
python manage.py migrate
python manage.py check
python manage.py seed_ol_quotations
python manage.py seed_ol_quotations
pytest -q apps/ol_quotations/tests/test_quotations.py
pytest -q
python manage.py makemigrations --check --dry-run
git diff --check
```

The second seed invocation is intentionally required to verify idempotency. SQLite development files remain excluded from version control by the repository `.gitignore` protection.

## Module boundary after this milestone

The OL Quotations module is complete through proposal handoff. The next recommended bounded context is the full **OL Proposals** workflow, which should consume `OLProposal`, `ProposalCreated`, the immutable quotation version, and the copied handoff snapshots without mutating the quotation aggregate.

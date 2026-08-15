# Partner Onboarding Parameter Catalog

## Purpose

Partner onboarding is governed by a backend-owned parameter catalogue. The Settings workspace is the administration surface for those values, while onboarding consumes the published configuration projection. This separation prevents form components from becoming the source of truth for business rules.

> **Source of truth:** system parameters, choice lists, and partner-type requirement records stored by the backend. Frontend fallback values exist only to keep a temporarily unavailable configuration service usable; they do not replace persisted configuration.

## Configuration domains

| Domain | Backend owner | Used by onboarding |
|---|---|---|
| Workflow and lifecycle | System parameter groups and workflow configuration | Status labels, allowed transitions, terminal states, review and approval actions |
| Choice catalogues | Choice lists and active choice options | Titles, identification types, genders, marital status, nationalities, industries, risk levels, document types, partner types, regions, branches, and locations |
| Numbering and schedules | System parameters | Application numbering, partner numbering, sequence formatting, draft cleanup, reminders, and scheduled compliance windows |
| Base-field validation | System parameters | Required individual fields, required corporate fields, age and uniqueness rules, validation policies, and default values |
| Compliance and risk | System parameters and choice lists | Political risk, AML risk, screening thresholds, high-risk industries, and compliance decision behavior |
| Documents by partner type | Partner-type document requirement records | Document code, description, required status, mandatory status, multiple-upload rule, display order, and active state |
| Attributes by partner type | Partner-type field configuration records | Field name/code, type, default, required status, validation rules, visibility rules, order, and active state |
| Contacts by partner type | Partner-type contact requirement records | Contact type, required status, multiplicity, display order, and active state |
| Banks by partner type | Partner-type bank requirement records | Bank type, required status, multiplicity, validation rules, display order, and active state |

## Consolidated read contract

The Settings landing page and onboarding wizard consume:

```text
GET /api/v1/system-parameters/configuration/partner-onboarding/
```

The response contains the configuration version, grouped scalar parameters, active choice lists with options, and active partner types with their document, attribute, contact, and bank requirements. Requirement metadata remains attached to the partner type that owns it, so different partner types can expose different onboarding forms without frontend code changes.

## Canonical scalar values used by onboarding

The following parameter codes are consumed directly by the current onboarding wizard:

| Code | Runtime effect |
|---|---|
| `DEFAULT_CURRENCY` | Default currency for new bank-account drafts and assignment bank setup |
| `INDIVIDUAL_REQUIRED_FIELDS` | Required information fields for individual applicants |
| `CORPORATE_REQUIRED_FIELDS` | Required information fields for corporate applicants |
| Choice-list codes for titles, identification, gender, marital status, nationality, industry, risk, document type, and partner type | Populate the corresponding onboarding controls |

Parameter values may be stored as strings, numbers, booleans, or JSON. The typed system-parameter serializer accepts a single `value` payload and clears stale type-specific storage columns before persisting the new value.

## Runtime precedence

Onboarding resolves values in this order:

1. Active options and parameters from the consolidated partner-onboarding configuration payload.
2. Existing protected choice-list endpoints, retained as a backward-compatible loading fallback.
3. Minimal UI fallback values only when the configuration service is unavailable or an installation has not yet been seeded.

Partner-type documents, attributes, contacts, and banks are resolved from the partner type selected or assigned in the current application. Inactive requirement records are excluded, and active requirements are sorted by their configured display order.

## Mutation and audit behavior

Settings mutations continue through the existing protected CRUD endpoints. Parameter groups, parameters, choice lists, choice options, and partner-type requirement records are backend-owned resources. Mutation hooks invalidate the runtime configuration cache and create audit events with actor, action, object reference, and before/after state where the audit service is available.

After a successful save, the Settings UI refreshes its summary and onboarding screens fetch the current projection after cache invalidation. Existing applications preserve their saved values; changing a parameter affects new input, validation, and unsatisfied requirements without silently rewriting previously saved application data.

## Operational guidance

Administrators should create or update a choice list before assigning it to an onboarding field. Partner-type requirement records should be configured as inactive while being prepared, then activated only after their metadata and validation rules are complete. Required documents, contacts, banks, and dynamic attributes should be tested using a draft application before the configuration is used for submitted applications.

Configuration changes should be reviewed through the central audit log. Production deployments should apply migrations before enabling newly seeded parameters, and each environment should maintain its own local SQLite database or managed database instance rather than committing database files to Git.

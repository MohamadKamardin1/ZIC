# Add Partner final 400 diagnosis

## Frontend flow

`insurance-dashboard-ui/src/pages/onboarding/ApplicationForm.tsx` has six steps: client type, information, partner roles, contact/risk, documents, review/submit.

Current behavior:

- `toPayload()` sends scalar application fields only.
- `handleSave()` creates a new application only when explicitly saving; for new applications it navigates to `/onboarding/{id}` after create.
- `handleSaveAndSubmit()` creates a new application, saves selected partner types and dynamic field values, and immediately calls submit.
- The Documents step disables uploads when `isEdit` is false and explicitly tells users to save first.
- No contact or bank-account records are created by the wizard, even though API helpers exist in `src/lib/api.ts`.
- Client-side validation is incomplete: individual validation only checks first name and surname; corporate validation only checks company name, TIN, and contact person.

## Backend submission gate

`backend/apps/partner_onboarding/services/application_service.py`:

- Individual required scalar fields: `identification_type`, `identification_number`, `first_name`, `surname`, `email`, `mobile_number`, `date_of_birth`, `nationality`, `gender`.
- Corporate required scalar fields: `company_name`, `tin_number`, `incorporation_date`, `industry`, `email`, `mobile_number`, `contact_person`, `contact_person_phone`, `contact_person_email`, `physical_address`.
- Submission requires at least one active application partner type assignment.
- For selected partner types, required documents must exist and be verified; required contacts and banks must exist; required dynamic fields must exist.

## Seeded partner-type requirements observed in the local DB

- `CLIENT`: documents `PROOF_OF_ADDRESS`, `IDENTITY_DOCUMENT`; no contacts, banks, or dynamic fields.
- `AGENT`: documents `TIRA_AGENT_LICENSE`, `COMMISSION_AGREEMENT`, `TAX_CLEARANCE_CERT`, `PROFESSIONAL_INDEMNITY`, `NID`, `BANK_DETAILS_FORM`, `COP_CERTIFICATE`; contact `PRIMARY`; bank `COMMISSION`; several dynamic fields.
- `AGENCY`: eight required documents; contacts `PRIMARY`, `TECHNICAL`, `BILLING`, `COMPLIANCE`; banks `OPERATIONS`, `COMMISSION`; multiple dynamic fields.
- `BROKER`: two required documents; contact `BILLING`; three dynamic fields.
- Several other seeded partner types have similar nested requirements.

## Exact root cause

The final 400 is expected when submitting directly from the new wizard because the wizard bypasses required intermediate persistence: it cannot upload documents for a new application, never creates contacts or bank accounts, and does not mirror backend scalar validation. A direct `handleSaveAndSubmit()` therefore creates a mostly scalar draft, attaches roles/dynamic fields only, and calls the submit gate with missing prerequisites.

## Relevant accepted contracts

- `POST /api/v1/partner-onboarding/applications/` accepts scalar application fields.
- `POST /applications/{id}/partner-types/` accepts UUID `partner_type`, UUID branch list, UUID location, region, and `share_data_externally`.
- `POST /applications/{id}/documents/` accepts multipart `document_type`, optional `document_name`, and `file`; uploaded documents begin unverified.
- `POST /applications/{id}/contacts/` accepts model fields `contact_type`, `first_name`, `last_name`, `email`, `phone`, `mobile`, `designation`, `is_primary`, `notes`.
- `POST /applications/{id}/bank-accounts/` accepts `bank_name`, `branch_name`, `account_name`, `account_number`, `swift_code`, `iban`, `currency`, `is_primary`, `notes`.
- Dynamic field batch update uses `field_config` and `value_json`.

## Intended repair direction

Persist a draft before the wizard reaches the document phase, keep the user in the wizard with the new ID, enable document uploads during the same flow, add contact and bank-account capture/persistence, align client validation with backend required scalar fields, and prevent direct submit until all known prerequisites are present. Preserve backend submission validation and surface detailed field-level errors rather than a generic 400.

# Frontend Assumptions

## OL Default Setup

The Default Setup page is implemented as one access-controlled master-detail workspace with four tabs: **Default System Parameters**, **Override Commission Setup**, **Computation Approach**, and **Maturity Claim Setup**. Each tab uses the backend table response contract and sends create, update, and deactivate operations to the corresponding resource under `/api/v1/ol-parameters/`.

The server remains authoritative for effective-date overlap checks, foreign-key validity, decimal precision, and domain-specific validation. The frontend performs only immediate usability validation for required fields, non-negative commission rates, valid JSON fields, and effective-date ordering. This keeps the screens responsive without duplicating the backend policy engine.

## Permissions

The page maps its table and mutation actions to the existing `ol_parameters` module. The `view` permission controls table visibility, `create` and `update` control the New setup and Edit actions, and `deactivate` controls the Deactivate action. If the access payload is unavailable, the existing access provider fallback behavior is preserved; when explicit permissions are returned, action visibility is exact and permission-gated.

## Parameter Values

Default parameter values are edited through a typed value field. The value type selector controls whether the editor renders a text, decimal, date, boolean, or JSON input. The submitted payload preserves typed values where the frontend can safely coerce them and leaves final validation to Django/DRF.

Partner, product, plan, rider, branch, currency, and channel fields are represented as backend identifiers or configured values. They are intentionally not populated with hardcoded business catalogs. Subsequent setup screens should replace the identifier inputs with searchable controls sourced from their respective master-data endpoints.

## Navigation Placeholders

The Ordinary Life Parameters submenu exposes the nine requested groups. Default Setup is fully implemented. The remaining eight groups have explicit routes and a neutral placeholder page so navigation is stable while their table-first API screens are delivered in isolated commits. Placeholder pages do not create or imply business configuration data.

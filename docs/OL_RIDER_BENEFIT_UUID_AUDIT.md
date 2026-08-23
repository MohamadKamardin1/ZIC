# OL Rider and Benefit UUID Error Audit

## Reported UI error

The Riders & Benefits step shows a selected benefit label such as `Maturity benefit`, but saving fails with a validation response equivalent to:

- `selections[...].beneficial_type_id`: Must be a valid UUID.
- `benefits[...].beneficial_type_id`: Must be a valid UUID.

## Traced contract

The quotation rider API expects the `beneficial_type_id` field to contain the UUID of an `OLBeneficialType` catalog record. The frontend SmartSelect displays a human-readable label but must retain the option value as the catalog UUID. A benefit code such as `MATURITY`, a label such as `Maturity benefit`, or a legacy enum value is not valid for this UUID field.

The current wizard stores the first benefit as `benefits[0].beneficial_type_id`, but some existing rider payloads and backend option data can expose a non-UUID benefit value. The correction must normalize catalog option values to canonical UUIDs, preserve labels only for display, and avoid serializing the display label into `beneficial_type_id`.

Rider selection itself uses `rider_id` and is already a UUID field. `beneficial_type_id` is a separate foreign key and must not be inferred from the rider's `benefit_type` string.

## Required regression coverage

1. A valid rider and benefit selection submits UUID values for both `rider_id` and `beneficial_type_id`.
2. The displayed labels remain human-readable and never show UUIDs.
3. A raw benefit code/label is rejected or normalized before submission with a clear field error.
4. The backend response exposes a `beneficial_type_display` field for rendered labels where applicable.

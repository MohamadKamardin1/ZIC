# Zanzibar OL Complete Master-Data Seed

The `seed_zanzibar_ol_complete` management command provisions the full Zanzibar Insurance Company Ordinary Life master-data graph required by the OL Parameters screens and quotation wizard. It is intended for a fresh environment, a controlled development/UAT environment, or a repeatable reference-data refresh. It does not flush tables, delete user data, or create transactional quotations, policies, claims, or payments.

## Usage

```bash
cd backend
python manage.py seed_zanzibar_ol_complete
```

The command is wrapped in a database transaction and uses deterministic natural keys with `update_or_create`-style updates. Existing records are updated in place, and records outside the seeded natural-key set are preserved. The effective date for the ZIC reference configuration is **1 January 2026**, with open-ended active records unless the relevant setup requires an end date.

To validate the current database without writing rows, run:

```bash
python manage.py seed_zanzibar_ol_complete --verify-only
```

## Seed order and coverage

The command first invokes the established baseline seeders for ChoiceLists, permissions, quotation configuration, partner/location master data, and the legacy Ordinary Life operational product graph. It then reapplies the parameter release after the operational products exist, which ensures product-dependent baseline rows are present during the first complete run. The command completes the remaining parameter graph in dependency order.

| Configuration group | Covered master data and dependent rows |
|---|---|
| Defaults and servicing | System parameters, override and agent commission setup, computation approaches, maturity-claim setup |
| Policy lifecycle | Anticipated-endowment installment rates, grace periods, policy/renewal/commitment statuses and transitions, beneficial types, member-cover rules, surrender and paid-up setup/rates, reinstatement windows |
| Health underwriting | Health questions, effective/versioned questionnaires and ordered items, medical codes, limits, personal habits, medical history, facilities, practitioners |
| Product setup | Plan types, parameter products, tax configurations, target markets, risk categories, occupation risk limits, investment fund types, investment funds |
| Rating | Premium tables and rows, mortality tables and rows, joint-life setup, reinstatement interest, bonus, mortgage factor, installment charge, cash surrender value, reserve loadings |
| Riders and loans | Rider setups, rider-rate tables and rows, loan system setup, loan-interest controls |
| Claims | Claim types, reasons, statuses and transitions, discharge types/templates, correspondent types |
| Operational quotation graph | Zanzibar branches and locations, active agent partner, operational products and versions, six selectable plans, rate bands, benefits, riders, and TZS investment funds |
| Dropdown providers | Identity types, locations, agents, products, plan types, payment frequencies, quote bases, premium factors, member relations, cover types, payment modes, investment funds, fund types, riders, benefit types, and currencies |

All seeded foreign keys are created in dependency order. Plan-scoped parameter rows use the operational Ordinary Life plan relationship required by their validators, while product-scoped rating/loan rows use the parameter-product relationship required by those model families. Global questionnaire records intentionally leave product, plan, and scheme scope empty, as required by the questionnaire validator.

## Quotation readiness

After seeding, the quotation option registry should return active, effective, human-readable options for every wizard entity:

```text
GET /api/v1/ol/options/<entity>/
```

The supported entities are `identity-types`, `locations`, `agents`, `products`, `plan-types`, `payment-frequencies`, `quote-bases`, `premium-factors`, `member-relations`, `cover-types`, `payment-modes`, `investment-funds`, `investment-fund-types`, `riders`, `benefit-types`, and `currencies`. Responses use the standard `{ value, label, meta }` option shape. The plan search and quotation-specific fund/rider endpoints consume the same seeded product graph.

## Verification

The focused regression test runs the complete command twice and asserts stable active/effective counts for every concrete OL parameter model listed by the command. It also asserts that rating tables have rows, rider tables have rows, funds have active fund types, questionnaires have active questions, and all 16 quotation option entities return labeled results.

```bash
python -m pytest -q apps/ol_parameters/tests/test_zanzibar_complete_seed.py
python -m pytest -q apps/ol_parameters/tests/test_zanzibar_seed.py
python manage.py seed_zanzibar_ol_complete --verify-only
```

The values are production-shaped Zanzibar reference data for development and UAT. Actuarial rates, underwriting limits, commission rules, and claims workflow assumptions remain configuration data and must be reviewed through the corresponding OL Parameters screens before being used for a regulated production portfolio.

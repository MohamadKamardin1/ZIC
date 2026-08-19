# Zanzibar Insurance Ordinary Life Demo Seed

The `seed_zanzibar_ol_demo` management command provisions a realistic, parameter-driven Ordinary Life dataset for local quotation and frontend testing. It is **idempotent** and does not flush, recreate, or delete existing database records.

## Run

```bash
cd backend
python3 manage.py seed_zanzibar_ol_demo
```

The command first runs the complete OL parameter release seed and the Ordinary Life operational reference-data seed. It then adds or updates the Zanzibar demo catalog:

| Domain | Seeded data |
|---|---|
| Products | `OL_TERM_LIFE`, `OL_EDUCATION_SAVINGS`, `OL_INVESTMENT_LINKED` |
| Product versions | One active TZS version per product, effective from 1 January 2026 |
| Plans | Six active plans across term assurance, education savings, and investment-linked products |
| Rating | Three age/term rate bands per seeded plan |
| Riders | Product-scoped accidental-death and premium-waiver riders |
| Investment funds | Money market, balanced, and equity growth TZS funds |
| OL parameters | Default setup, policy setup, product setup, rating, riders, agent, loans, medical underwriting, claims, permissions, and registry tables |

The seed uses Tanzanian Shillings (`TZS`), Tanzania-specific descriptions and underwriting metadata, active effective-dated rows, standard payment frequencies, and realistic age, term, sum-assured, rider, and fund-allocation constraints.

## Verify

```bash
python3 manage.py validate_ordinary_life_reference_data
pytest -q apps/ol_parameters/tests/test_zanzibar_seed.py
pytest -q apps/ol_quotations/tests/test_quotations.py -k 'plan_search or investment_fund or rider_option'
```

The regression test runs the command twice and asserts that the seeded product, version, plan, rider, and fund counts remain stable. The quotation option tests verify that the data is usable by plan search, investment-fund options, and rider-option flows.

## Frontend smoke test

After starting Django and Vite, authenticate as a local superuser and open the quotation wizard. The plan search endpoint is:

```text
GET /api/v1/ol/plans/search/?quotation_id=<quotation-id>&limit=200
```

The seeded plans populate the Plan & Sub-Products step. Investment-linked plans expose the seeded TZS funds through:

```text
GET /api/v1/ol-quotations/quotations/<quotation-id>/investment-funds/options/
```

Rider and benefit options are available through:

```text
GET /api/v1/ol-quotations/quotations/<quotation-id>/riders/options/
```

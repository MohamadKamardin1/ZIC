# OL Default Setup Frontend

## Scope

The page at `/ordinary-life/parameters` provides table-first administration for four Ordinary Life parameter entities. It uses the shared `MasterDetailPage`, `DataTable`, `FilterBar`, form controls, modal overlays, status badges, toast notifications, and IAM access metadata from the frontend design system.

| Tab | API resource | Main table fields |
| --- | --- | --- |
| Default System Parameters | `/api/v1/ol-parameters/default-system-parameters/` | Code, name, category, parameter key, value type, typed value, effective dates, status |
| Override Commission Setup | `/api/v1/ol-parameters/override-commission-setups/` | Partner/agent, product, plan, channel, rate type/value, priority, effective dates, status |
| Computation Approach | `/api/v1/ol-parameters/computation-approaches/` | Module, basis, formula key, sequence, effective dates, status |
| Maturity Claim Setup | `/api/v1/ol-parameters/maturity-claim-setups/` | Product/plan scope, auto-create flag, days before maturity, payout method, approval flag, effective dates, status |

## API Contract

The table fetcher sends `page`, `page_size`, `search`, `ordering`, and the active filter values as query parameters. It accepts the standard table envelope:

```json
{
  "results": [],
  "count": 0,
  "page": 1,
  "page_size": 20
}
```

Create requests use `POST` on the collection URL. Editing uses `PATCH` on `/{id}/`. Deactivation uses `POST` on `/{id}/deactivate/`. After a successful mutation, the table refreshes through its controlled `refreshKey`, and the user receives a success or error toast.

## Validation

The editor requires code, name, and effective-from for every tab. Default System Parameters additionally require parameter key, category, and typed value. Computation Approach requires module, basis, and formula key. Maturity Claim Setup requires payout method and the target claim status. Commission rates must be numeric and non-negative. JSON value and computation configuration fields must parse successfully, and effective-to cannot precede effective-from.

The frontend validation is deliberately narrow. The backend remains responsible for uniqueness, foreign-key existence, scope overlap rules, date-effective conflicts, decimal precision, and any configuration-specific constraints.

## Access and actions

The route is mapped to the `ol_parameters` module. The page renders the view-access notice when `ol_parameters.view` is absent. Mutation controls are exact permission matches:

| Control | Permission | Record rule |
| --- | --- | --- |
| New setup | `ol_parameters.create` | Always visible to create-authorized users |
| Edit | `ol_parameters.update` | Available for rows returned by the active table |
| Deactivate | `ol_parameters.deactivate` | Visible only while `is_active` is true |

CSV export is provided by the shared `DataTable` and exports the currently loaded page using the active tab’s column labels.

## Navigation

The sidebar path is **Ordinary Life → Ordinary Life Parameters**. It exposes Default Setup, Policy Setup, Product Setup, Product Rating, Rider Setup, Agent Management, Loan Setup, Medical U/W, and Claim Setup. Only Default Setup is implemented in this commit; the other paths are explicit placeholders and do not submit business data.

## Test coverage

`OLDefaultSetup.test.tsx` covers API-backed table rendering, required-field blocking before a create request, confirmation-gated deactivation, and hiding mutation actions for view-only users. The tests mock the API, access metadata, and toast service while exercising the real page and shared table/modal components.

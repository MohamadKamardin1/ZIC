# ZIC Frontend UI Kit Catalog

The reusable UI kit lives under `src/components/ui` and is designed for the OL Parameters and OL Quotations modules. The living demonstration is available at `/ui-kit` after authentication.

## Component inventory

| Component | Primary contract | Intended use |
|---|---|---|
| `DataTable<T>` | `metadata`, `fetcher`, `filters`, `actions`, `permissions` | Server-side parameter tables, quotation work queues, and searchable records. |
| `FilterBar` | `definitions`, `value`, `onChange`, `onApply`, `onReset` | Search, selects, multi-select filters, and date ranges. |
| `StatusBadge` | `value`, optional `tone` | Consistent workflow and master-data status display. |
| `Modal` / `FormModal` | `open`, `title`, `children`, `footer`, `onClose` | Form dialogs and confirmation flows. |
| `Drawer` | `open`, `title`, `children`, `onClose` | Master-detail inspection and side forms. |
| `ConfirmModal` | `description`, `onConfirm`, `tone` | Destructive or consequential actions. |
| `InfoBanner` | `title`, `children` | Parameter rules, wizard guidance, and warning context. |
| Form primitives | `label`, `required`, `error`, `hint`, value props | Typed, accessible form controls with inline validation. |
| `EditableGrid<T>` | `rows`, `columns`, `createRow`, `onChange`, `total` | Rate rows, installment rows, and allocation tables. |
| `Wizard` | `steps`, `validate`, `onAutosave`, `onComplete` | Seven-step OL quotation flow with validation gates. |
| `MasterDetailPage` | `title`, `status`, `stats`, `tabs`, `children` | Detail pages with summary header, cards, tabs, and tables. |
| `KPIStat` / `SimpleAreaChart` | backend-derived values/data | Dashboard summaries and trend visualization. |
| `ToastProvider` / `useToast` | `toast({ title, message, tone })` | Non-blocking save, error, and workflow feedback. |

## DataTable backend contract

A module screen supplies metadata rather than hardcoding a table layout:

```ts
const metadata: TableMetadata<Quotation> = {
  pageSize: 10,
  columns: [
    { key: "quote_number", label: "Quote number", field: "quote_number", sortable: true },
    { key: "status", label: "Status", field: "status", sortable: true },
  ],
}
```

The fetcher receives `page`, `pageSize`, `search`, `ordering`, and serialized filters, then returns `{ results, count, next, previous }`. The sandbox uses the live `/api/v1/ol/quotations/` endpoint. API envelopes and legacy `items`/`total` payloads are normalized by `normalizeTableResponse`.

Row actions are visible only when the caller’s `permissions` include the action permission and the optional `isVisible(row)` predicate returns true. This keeps backend permission policy and state policy separate and testable.

## Wizard contract

A wizard is configured with an ordered `WizardStep[]`. Each step includes an icon, label, content, and optional synchronous or asynchronous validation function. The framework blocks forward navigation when validation returns false, marks the step invalid, and calls `onAutosave` whenever the active step changes. The sandbox includes seven steps matching the quotation flow: personal details, plans, members, installments, funds, riders, and review.

## Accessibility behavior

Dialog and drawer surfaces expose `role="dialog"` and `aria-modal`, close on Escape, and provide labelled close buttons. Tables use semantic `caption`, `thead`, and `scope` attributes. Required fields expose a visible asterisk and invalid controls use `aria-invalid` with linked error text. Toggles use `role="switch"` and `aria-checked`; wizard tabs expose `aria-current`; toast notifications use a polite live region. Focus-visible outlines are defined globally in `src/index.css`.

## Integration rules

Business options must be passed into form controls from backend catalogs or parameter endpoints. The UI kit does not define insurance rates, product options, statuses, or underwriting rules. The sandbox uses only structural labels and the live OL quotations list endpoint; production screens should replace demonstration controls with their corresponding API-driven options.

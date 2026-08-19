# OL Quotations List

## Purpose

The Ordinary Life Quotations page is the table-first work queue for reviewing and progressing quotations. It uses the existing ZIC section-header, KPI card, FilterBar, DataTable, StatusBadge, and confirmation-modal patterns.

## Routes

| Route | Behavior |
|---|---|
| `/ordinary-life/quotations` | API-backed quotations work queue |
| `/ordinary-life/quotations/new` | Create-quote wizard placeholder route reserved for the next quotation increment |
| `/ordinary-life/quotations/:id` | Quotation master-detail placeholder route opened by View |
| `/ordinary-life/quotations/:id/edit` | Edit/detail placeholder route opened by Edit |

## API contract

The list page consumes the quotation viewset under `/api/v1/ol/quotations/quotations/` and the summary action at `/api/v1/ol/quotations/quotations/summary/`. The table request uses the shared `page`, `page_size`, `search`, `ordering`, and filter query conventions. The `quote_date` range is translated into `quote_date_from` and `quote_date_to` before the request is sent.

The list response is expected to contain `results` and `count`. Each quotation row may include `row_actions` metadata. The frontend preserves backend action URLs when supplied and only uses documented action fallbacks for revise, finalize, print, convert, and delete.

## Table columns

The work queue displays quote number, quote name, prospect, plan count and summary, total premium, currency, status badge, version, quote date, agent, and created by. Total premium is formatted with the row currency and two decimal places when numeric. Dates are presented in a readable English-UK format while filtering continues to use ISO dates.

## KPI cards

The summary endpoint supplies `drafts`, `finalized`, `converted`, and `expired` counts. The page displays these as KPI cards with short operational descriptions. The values refresh after successful mutations.

## Filters and search

The quotation filter band supplies server-side text filters for status, plan, agent, and location, while the shared FilterBar supplies search and quote-date range controls. The DataTable also provides its standard table search, ordering, pagination, refresh, and CSV export controls. Search values are not interpreted client-side; they are passed to the quotations API so identity number and other backend-supported fields remain searchable.

## Row-action rules

Backend `row_actions` metadata is authoritative when present. The frontend additionally enforces the state and permission fallback rules below when metadata is absent.

| Action | State rule | Permission fallback |
|---|---|---|
| View | Available for an accessible row | `ol_quotations.view` |
| Edit | `DRAFT` only | `ol_quotations.update` |
| Revise | `FINALIZED` only | `ol_quotations.update` |
| Finalize | `DRAFT` only | `ol_quotations.finalize` |
| Print | `FINALIZED` or `CONVERTED` | `ol_quotations.print` |
| Convert to Proposal | `FINALIZED` only and backend state checks must pass | `ol_quotations.convert` |
| Delete | `DRAFT` only | `ol_quotations.destroy` |

Finalize, revise, conversion, and deletion require confirmation. Successful mutations refresh both the table and KPI summary. Print opens the backend-provided print URL in a new browser tab.

## Option and permission policy

Quotation workflow states are treated as backend workflow values rather than editable master-data options. The page does not create or maintain business catalogs. Product, agent, location, identity, and other quotation options remain owned by the backend quotation and parameter APIs. Workspace visibility uses `canAccess("ol_quotations")`; row actions use backend metadata and permission keys.

## Assumptions

The quotation list backend exposes action URLs where state-specific behavior requires additional checks. The create and detail routes are intentionally lightweight placeholders until the quotation wizard and master-detail increments are implemented. The frontend does not duplicate server-side eligibility rules for partner verification, approval, expiry, or conversion; it only hides actions when the backend metadata or current state says they are unavailable.

# SmartSelect and Quick-Create Guide

## Purpose

`SmartSelect` is the reusable foreign-key selector for the ZIC frontend. It provides one consistent interaction for loading, searching, selecting, clearing, and creating reference data across Ordinary Life and future modules. The component displays human-readable labels while form state and submitted payloads retain the selected backend IDs or codes.

The component is intentionally metadata-driven. Screens should pass the backend option entity name and should not hardcode option lists that are managed by the platform.

## Component API

```tsx
<SmartSelect
  entity="locations"
  name="location"
  label="Location"
  required
  value={locationId}
  onChange={setLocationId}
  onOptionChange={setLocationOption}
  placeholder="Select a location"
/>
```

| Prop | Type | Description |
| --- | --- | --- |
| `entity` | `string` | Canonical option entity used in the options and quick-create URLs. |
| `name` | `string` | Stable field ID used by labels, error text, and automated tests. |
| `label` | `string` | Visible field label. |
| `value` / `onChange` | `string` / callback | Single-select value and change handler. The value is the backend ID or option code. |
| `onOptionChange` | callback | Receives the complete normalized option, including `label` and `meta`. |
| `values` / `onValuesChange` | `string[]` / callback | Multi-select value and change handler when `multiple` is enabled. |
| `multiple` | `boolean` | Enables multi-select behavior for riders, funds, or other future collections. |
| `required` | `boolean` | Adds the required marker to the field label. |
| `error` | `string` | Inline validation message. |
| `hint` | `string` | Supporting field guidance. |
| `placeholder` | `string` | Empty-state trigger text. |
| `pageSize` | `number` | Page size sent to the options endpoint; defaults to 30. |
| `createPermission` | `string` | Optional permission override. If omitted, the canonical entity registry is used. |
| `manageHref` | `string` | Optional override for the full parameter screen link. |
| `manageLabel` | `string` | Link label; defaults to `Manage…`. |
| `disabled` | `boolean` | Disables the trigger and create action. |
| `emptyEntityLabel` | `string` | Human-readable entity name used in empty-state and toast copy. |

## Data contract

The list endpoint is:

```text
GET /api/v1/ol/options/<entity>/?q=<search>&page=1&page_size=<n>
```

The preferred response shape is:

```json
{
  "items": [
    {
      "value": "uuid-or-code",
      "label": "008 — Boresha Elimu",
      "meta": {
        "code": "008",
        "name": "Boresha Elimu"
      }
    }
  ],
  "count": 1,
  "has_next": false
}
```

`SmartSelect` also tolerates `results` and `options` collections, and normalizes legacy `id`, `code`, `name`, or `display_name` fields. New endpoints should use `value`, `label`, and `meta` directly. The UI must never render a raw UUID as a label.

The component sends the selected `value` in the form payload. `meta` is presentation or context data only and must not replace the submitted identifier.

## Permission-aware controls

The create button and `Manage…` link are rendered only when the current access metadata contains the canonical permission for the entity. A superuser receives these permissions through explicit IAM metadata; the frontend does not use a superuser shortcut.

| Entity group | Permission |
| --- | --- |
| `identity-types`, `payment-frequencies`, `quote-bases`, `premium-factors`, `member-relations`, `cover-types`, `payment-modes`, `benefit-types`, `currencies` | `system_parameters.manage` |
| `locations`, `products`, `plan-types`, `investment-funds`, `investment-fund-types`, `riders`, `benefit-types-catalog` | `ol_parameters.create` |
| `agents` | `partners.create` |

When permission is absent, the field remains a normal searchable select and no `+` or `Manage…` affordance is mounted. This prevents accidental privilege escalation and keeps the visual state honest.

## Entity registry and Manage links

`src/lib/optionMetadata.ts` is the canonical frontend registry. It contains the permission code, human-readable label, and parameter-screen deep link for each entity. A screen should normally pass only `entity`; custom permission or link props are reserved for shared components used outside the registry.

The registry currently covers the Ordinary Life wizard entities: identity types, locations, agents, products, plan types, payment frequencies, quote bases, premium factors, member relations, cover types, payment modes, investment funds, investment fund types, riders, benefit types, currencies, and the catalog benefit type entity used by rider configuration.

## Quick-create flow

Selecting `+` opens `QuickCreateModal`. The modal first loads:

```text
GET /api/v1/ol/options/<entity>/quick-create-schema/
```

The schema returns the minimal fields required for a selectable record:

```json
{
  "entity": "products",
  "permission": "ol_parameters.create",
  "fields": [
    {"name": "code", "type": "string", "required": true, "choices": [], "default": null},
    {"name": "name", "type": "string", "required": true, "choices": [], "default": null},
    {"name": "plan_type", "type": "select", "required": true, "choices": [], "default": null, "nested_entity": "plan-types"}
  ],
  "defaults": {}
}
```

The modal renders fields from the schema rather than from a screen-specific form. Select fields use choices supplied by the backend. A nested entity is created in a nested modal when the schema declares `nested_entity`; the nested result is returned to and selected by the parent form.

Submitting the modal calls:

```text
POST /api/v1/ol/options/<entity>/quick-create/
```

The backend applies the same permission, validation, duplicate detection, active-record rules, and audit service used by full parameter creation. On success the response includes `value`, `label`, and `meta`. `SmartSelect` invalidates its options query, merges the created option immediately, selects it, remembers it for the current browser session, and displays `<Entity> created and selected`.

The modal always explains that the record is minimal:

> This creates a minimal record. Complete full configuration in the corresponding parameter screen.

Errors are shown inline. Field-specific duplicate errors remain attached to the relevant field, while general errors are presented in the modal error region.

## Accessibility and interaction behavior

The trigger is a real button with `aria-haspopup="listbox"`, `aria-expanded`, and `aria-invalid`. The search input receives focus when the menu opens. `Escape` closes the menu. Options expose `role="option"` and `aria-selected`. The `+` button has an accessible name, visible focus ring, and activates on both `Enter` and `Space`.

Loading uses a visible skeleton with a status label. Empty results say: `No results found. Use + to add a new <entity>.` Search input is debounced by 300 milliseconds to avoid excessive requests for large option collections. The select, menu, modal, create button, and manage link use the shared light/dark design tokens.

Toast notifications are non-blocking: the notification surface does not intercept clicks intended for an underlying modal, while its dismiss button remains keyboard and pointer accessible.

## Usage rules for OL screens

Every editable foreign-key field in the quotation wizard and OL parameter screens should use `SmartSelect`. Fixed business enums remain ordinary controlled enum controls when they are not managed reference data. This includes gender, smoker, joint life, mortgage, personal accident, premium waiver, and other explicit Yes/No or fixed enum fields.

Read-only computed fields such as age, policy term inherited from the selected plan, and computed installment totals must not be converted into selects. Plans in parameter editors remain read-only where the backend model defines them as contextual or inherited values.

Screens must use the backend option value for submissions and a display field or normalized option label for rendering. A raw foreign-key UUID is never a valid user-facing fallback.

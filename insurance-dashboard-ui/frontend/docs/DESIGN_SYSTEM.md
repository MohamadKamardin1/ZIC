# ZIC Frontend Design System

## Visual direction

The shell uses a calm insurance-operations aesthetic: white and pale slate surfaces, charcoal typography, indigo/purple primary actions, and blue gradient section headers. The visual language is intentionally structured rather than decorative so high-density tables and parameter forms remain easy to review.

## Tokens

The canonical tokens live in `src/theme/tokens.css`. Components must consume semantic variables instead of introducing isolated business colors.

| Token group | Usage |
|---|---|
| Canvas and surfaces | `--background`, `--card`, `--muted`, `--sidebar` for page, card, muted, and navigation surfaces. |
| Typography | `--foreground`, `--muted-foreground`, and semantic on-color variables. |
| Brand | `--primary`, `--primary-foreground`, `--accent`, and `--ring` for actions and focus. |
| Feedback | `--success`, `--warning`, `--destructive`, and blue info variables for badges and alerts. |
| Section headers | `--section-from` and `--section-to` for the blue gradient header treatment. |
| Radius | 8–12px component radii, with 12px as the default card and shell surface radius. |
| Elevation | `--shadow-card`, `--shadow-card-hover`, and `--shadow-card-elevated`. |

The dark theme overrides the same variables under `[data-theme="dark"]`, allowing React and Lit components to change together without duplicate theme logic.

## Components

`surface-card` is the standard bordered card. `section-header` is reserved for module titles and contextual hero panels. `button-primary` is used for the main action in a view, while `button-secondary` is used for neutral or reversible actions. The semantic badge classes are `badge-success`, `badge-info`, `badge-warning`, `badge-danger`, and `badge-neutral`.

All controls have a minimum 40px interactive height in the shell and use 10–12px radii. Focus-visible states use the semantic ring token and are not removed. Tables should use visible row separators, compact headers, sortable column affordances, and responsive horizontal scrolling rather than truncating financial or policy values.

## Shell layout

The desktop shell is a fixed navigation rail plus a flexible content column. The topbar remains visible while content scrolls. On narrow viewports, the navigation rail transforms off-canvas and the topbar uses icon buttons with accessible labels. The footer exposes task access, the current backend exchange-rate status, connection state, AI assistant access, and the platform attribution.

## Status language

| State | Visual treatment |
|---|---|
| Success / active / completed | Green semantic badge or status dot. |
| Information / selected / in progress | Blue semantic badge or indigo primary treatment. |
| Warning / pending / attention | Amber semantic badge or status dot. |
| Error / restricted / rejected | Red semantic badge and explicit explanatory copy. |
| Neutral / draft / unavailable | Muted slate badge; never imply a successful backend value. |

## Typography and spacing

Inter is the preferred font, with a system sans-serif fallback. Page titles use strong weight and restrained tracking. Body copy uses 14–15px in operational screens, with 12px metadata. The spacing scale follows Tailwind’s 4px base; page sections generally use 20–24px gaps and cards use 16–24px internal padding.

## Accessibility

Every icon-only button has an accessible label. Color is not the only signal for status; labels and text remain present. Forms use explicit validation messages and preserve backend field errors. Loading states are announced by visible status text, and unavailable backend data is represented explicitly instead of replaced with guessed or hardcoded business values.

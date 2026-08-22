# OL Quotation Remaining Screen Audit

This audit covers every supplied screenshot for the post-creation OL quotation experience. The screenshots are treated as the visual contract for the quotation list/detail experience and the printout preview/PDF output.

## Shared shell and detail header

All detail screenshots retain the ZIC shell: the left navigation rail with Ordinary Life expanded and Ordinary Life Quotations selected; the top bar with the ZIC logo, account-period indicator, search, language, notifications, theme control, signed-in user, and avatar; the breadcrumb `Home > Quotations > Quote Details`; and the lower task/exchange-rate/connection/AI/powered-by status bar.

The quotation detail page is a wide white card on the pale grey workspace. The summary header shows a purple document icon, the prospect name `Zachary Musa Otieno`, quotation number/version `Q2026020006-v1`, a green `Latest` badge, a dark neutral `Not Converted` badge, and the date `12/02/2026`. Right-aligned actions are `Back to Quote Listing`, `Edit`, `Convert to Proposal`, and `Print Quote`. A green success toast appears in the first detail screenshot at the top-right with the message `Quote created successfully`, a green progress bar, and a close control.

## Summary KPI cards

The detail header contains four equal-width pastel KPI cards. They are ordered left to right as follows:

| Card | Icon/accent | Value | Caption |
|---|---|---|---|
| Total Sum Assured | Green money/card icon | `TZS 10,000,000.00` | `Total Sum Assured` |
| Total Basic Premium | Blue money/card icon | `TZS 50,914.67` | `Total Basic Premium` |
| Total Rider Premium | Purple plus icon | `TZS 2,025,000.00` | `Total Rider Premium` |
| Total Premium | Amber shield icon | `TZS 3,116,759.72` | `Total Premium` |

A `More Details` text link sits at the lower-right of the summary card.

## Detail tab navigation

The tab strip appears below the summary card and keeps the screenshot order:

`Plans & Sub-Products`, `Member Coverage`, `Riders`, `Projections`, `Installment Payouts`, `Quote Versions`.

The selected tab has a white elevated tab shape and darker text; inactive tabs use muted purple-grey text. These six labels are the screenshot-facing detail contract. Internal route naming may use `plans`, `members`, `riders`, `financials`, `installments`, and `versions`, but the rendered labels must remain the screenshot labels.

## Plans & Sub-Products tab

The tab contains a table card with a page-size selector showing `10 entries`, a right-aligned `Search...` field, and pagination at the bottom. The table columns are:

`NO.`, `PLAN`, `SUB-PRODUCT`, `POLICY TERM`, `PAYMENT PERIOD`, `SUM ASSURED`, `PREMIUM`, `TOTAL PREMIUM`, `ACTIONS`.

The example row shows number `1`, plan `DUAL PROTECTION AND SAVINGS ENDOWNMENT PLAN`, sub-product `-`, policy term `10 (Years)`, payment period `10 (years)`, sum assured `TZS 10,000,000.00`, premium `TZS 311,675.97 (Annually)`, total premium `TZS 3,116,759.72`, and actions `-`. The footer reads `Showing Page 1 of 1`, with `Previous`, current page `1` in purple, and `Next`.

## Member Coverage tab

The tab contains a plan subsection headed `DUAL PROTECTION AND SAVINGS ENDOWNMENT PLAN`, followed by a compact table with:

`Member Name`, `Age`, `Gender`, `Coverage %`, `Sum Assured`, `Basic Premium`, `Rider Premium`, `Total Premium`.

The example row is `Zachary Musa Otieno` with a purple `Principal` badge, age `31`, gender `Male`, coverage `100%`, sum assured `TZS 10,000,000.00`, basic premium `TZS 50,914.67`, rider premium `TZS 2,025,000.00`, and total premium `TZS 2,075,914.67`.

## Riders tab

The Riders screenshot has the same page-size and search controls and a paginated table with:

`NO.`, `RIDER`, `PLAN`, `SUB PRODUCT`, `RIDER BENEFIT`.

The example contains two rows. `Accidental Benefit` belongs to `DUAL PROTECTION AND SAVINGS ENDOWNMENT PLAN`, with rider benefit `3,000,000.00 (Fixed Benefit)`. `Critical Illness` belongs to the same plan and shows `-` plus `Ratio based (100.000%)`. The table footer uses the same `Showing Page 1 of 1`, `Previous`, `1`, `Next` controls.

## Installment Payouts tab

The tab contains a plan heading `DUAL PROTECTION AND SAVINGS ENDOWNMENT PLAN`. On the right of the heading are `1 installments (Annually)` and `Annuity Period: 1 years`.

The metadata row displays `Estimated Maturity Value` with a green value `TZS 10,000,000.00` and `Payment Schedule` with an amber `After Maturity` badge. The payout table columns are:

`#`, `Description`, `Installment Rate`, `Installment Payout`, `Paid Up Rate`.

The example row is `1`, `Installment 1`, `100.00%`, `TZS 10,000,000.00`, and `100.00%`.

## Quote Versions tab

The versions tab uses the same page-size selector, search field, and pagination pattern. Columns are:

`VERSION`, `QUOTE NUMBER`, `SUM ASSURED`, `GROSS PREMIUM`, `CREATED DATE`, `CREATED BY`, `ACTIONS`.

The example row shows a green `v1` badge, a yellow star, `(Current)`, quote number `Q2026020006-v1`, sum assured `10,000,000.00`, gross premium `3,116,759.72`, created date `12/02/2026`, created by `Irvine Sunday`, and action `Current View`.

## Projections tab

The projections tab has a collapsible plan header with a down chevron, `DUAL PROTECTION AND SAVINGS ENDOWNMENT PLAN`, a green `Whole Life` badge, and a dark `10 Payments` badge. The table columns are:

`Payment`, `Year`, `Date`, `Basic Premium`, `Adjusted Basic`, `Rider Premium`, `Adjusted Rider`, `Savings`, `Commission`, `Net Premium`.

The example displays ten policy-year rows. Dates start at `12/02/2026` and increment annually. Basic premium rises from `TZS 3,935.45`, adjusted basic matches it, rider premium rises from `TZS 180,000.00`, adjusted rider matches it, savings remain `TZS 82,372.32`, commission declines over time, and net premium is displayed in the last column. A generated timestamp appears below the table.

## Print preview modal

The Print Quote action opens a centered modal over a dimmed detail page. The title is `Quote Printout Preview - Q2026020006-v1 (Zachary Musa Otieno)`, with a close X at the top-right. The modal body contains a vertically scrollable document preview. A bottom note says `This is a preview. Click download to get the formatted PDF document.` and a bottom-right `Download` button with a download icon.

The preview is an A4-like white document with a thin grey border and internal scroll bar. It must not render as an unstyled iframe or generic browser document.

## PDF page one content and layout

The first preview page has a company header with the ZIC logo on the left and right-aligned company information:

`Zanzibar Insurance Corporation`, `Bima House, No. 1 Mpirani Street, Mlandege Road, Zanzibar City`, `Tel: +255 659 072 500`, `Email: info@zic.co.tz`, and `Date: 12/02/2026`.

A centered uppercase title reads `ORDINARY LIFE QUOTATION` with a heavy horizontal rule below it.

The next area is a two-column information layout with headings `Personal Details` and `Quote Summary`.

Personal details include Name, ID Type, ID Number, Date of Birth, Age, Gender, Address, and Location. Quote summary includes Quote Number, Quote Date, Currency, Risk Sum Assured, Basic Premium, Rider Premium, and Gross Premium.

Next is `Quote Configurations`, a table with columns `Plan`, `Sub Product`, `Payment Frequency`, `Policy Term`, `Payment Period`, `Sum Assured (TZS)`, `Basic Premium (TZS)`, `Rider Premium (TZS)`, and `Gross Premium (TZS)`. A totals row follows.

Next is `Additional Benefits`, with a table headed `Rider`, `Plan`, `Sub Product`, `Rider Benefit (TZS)`, and `Benefit Ratio (%)`. The example rows are Accidental Benefit and Critical Illness.

The lower part begins `Member Coverage Details`, which continues on the second preview view.

## PDF page two content and layout

The continuation begins with `Member Coverage Details`, the plan heading, and a table with `Member Name`, `Age`, `Gender`, `Coverage %`, `Sum Assured (TZS)`, `Basic Premium (TZS)`, `Rider Premium (TZS)`, and `Total Premium (TZS)`.

Next is `Installment Payouts`, with plan heading and metadata. The table columns are `#`, `Description`, `Installment Rate`, `Installment Payout (TZS)`, and `Paid Up Rate`.

Next is `Terms and Conditions`, rendered as a numbered list. The visible terms state that the quotation is valid for 30 days from the generation date and expires on a specific date, premiums are based on the provided information and subject to underwriting acceptance, coverage becomes effective only after policy issuance/payment/satisfaction of underwriting requirements, all benefits are subject to applicable terms and exclusions, and the quotation is not a contract of insurance.

The footer signature panel shows `Prepared By: Irvine Sunday`, a `Signature & Date` line, `for and on behalf of Zanzibar Insurance Corporation`, a circular company stamp/seal on the right, and `Zanzibar Insurance Corporation` with `Official Stamp`.

## Printout requirements

The frontend preview and backend-generated PDF must share one data-driven visual contract. The PDF must use the real company header, preserve quote/version/source-template metadata, format TZS amounts with two decimals, render all configured plan/rider/member/installment rows, include projections where applicable, and retain the terms/signature section. Missing sections should be omitted gracefully rather than displaying raw UUIDs or blank placeholder tables.

The screenshot-facing list/detail labels and fields are presentation requirements; backend data remains authoritative and all values must continue to come from quotation APIs and configured OL parameters.

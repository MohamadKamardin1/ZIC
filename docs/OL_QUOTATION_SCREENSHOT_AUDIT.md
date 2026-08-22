# OL Quotation Creation Screenshot Audit

## Scope

This audit is the visual contract for the supplied Ordinary Life quotation creation screenshots only. It covers the ten unique creation-screen states shown in the provided images; the repeated attachment of the first image is treated as the same state. The surrounding ZIC shell, left navigation, top account-period bar, breadcrumb, footer status bar, and the quotation creation workspace are all in scope. The quotation register/list page and unrelated OL parameter screens are out of scope.

## Global shell visible in every screenshot

The desktop shell is a white ZIC application frame with a fixed left navigation rail, a thin top header, a breadcrumb row, and a bottom status strip. The ZIC logo is large and blue in the upper-left. The Ordinary Life navigation group is expanded and shows Ordinary Life Quotations as the selected item, followed by Ordinary Life Commitments, Proposals, Policies, Loans, Withdrawals, Claims, Maturity Installments, and Ordinary Life Parameters. The remaining global navigation includes Dashboard, Partner On-boarding, Group Life, Group Credit, Front Office, Reports, System Parameters, User Management, and Help & Support.

The top bar shows a sidebar control, a calendar icon, `Account Period Feb 2026`, and a smaller timestamp line. On the right it shows search, language/globe, a notification bell with a red count badge, a theme/sun control, the signed-in user `Irvine Sunday`, group `Aims Group`, and a circular avatar. The breadcrumb reads `Home > Quotations > Create Quote`.

The bottom status strip shows a Task pill, a green exchange-rate value in the form `128.45 TZS/USD`, a green-dot `Connection Stable` status, an `AI` pill, and right-aligned `Powered by Aimsoft Limited Solutions`. The main content is a light grey page background with a blue quotation workspace header and white cards.

## Image 1 — Personal Details, no products selected

The workspace header is a saturated blue horizontal gradient with a rounded rectangular shape. A pale document icon sits inside a light circular tile, followed by the title `Create New Quote`. The right side displays `No products selected`; the details control is part of the header stack in the selected-plan states.

The plan panel is a fixed-width white card on the left. Its blue title bar reads `Plan Selection`. Below it is a search field with a magnifying-glass icon and placeholder `Search plans and sub-products...`. The plan list is vertically scrollable and displays compact cards with a numeric/code chip, product or plan name, a short description, and colored plan-type badges such as `With Profit` and `Joint Life`. No plan is selected in this first state.

The main card has a horizontal wizard tab row with icons and these exact labels: `Personal Details`, `Plan & Sub-Products`, `Member Coverage`, `Installments`, `Investment Funds`, `Riders & Benefits`, and a wrapped second-row `Financial Details`. Personal Details is active. The form is a three-column desktop grid with the following visible fields and labels: `Quote Name *`, `Quote Date *`, `Identity Type *`, `Identity Number *`, `Date of Birth *`, `Age`, `Gender *`, `Smoker *`, `Location *`, `Agent *`, and a wide `Address *` textarea. The Age input is greyed and read-only with `Computed`. Placeholders include `Enter quote name`, a date value or date picker, `Select identity type`, `Enter identity number`, `dd/mm/yyyy`, `Select gender`, `Select smoker status`, `Search for a location...`, `Select agent`, and `Enter full address`.

The bottom of the card has an outlined red-accent `Cancel` button on the left and a disabled-looking `Next` button with a right arrow on the right.

## Image 2 — Plan & Sub-Products, one plan selected

The blue workspace header now shows `1 Plan` in the right summary area and a separate `Details` dropdown row below it. The selected plan in the left panel has a blue/purple outline, a checkmark at the upper-right, and its code chip highlighted. Other plan cards remain unselected.

The active wizard tab is `Plan & Sub-Products`. The main area begins with a wide blue gradient section header showing the selected plan name in uppercase, a small `Section 1` badge at the right, and the subtitle `Plan-only configuration` below the plan title.

The form is a three-column grid. The first row shows `Policy Term (Years) *`, `Payment Period (Years) *`, and `Payment Frequency *`. The second row shows `Quote Basis *`, `Estimated Maturity Value *`, and `Premium Factor`. The third row shows `Joint Life *`, `Mortgage *`, and `Personal Accident (PA) *`. The fourth row shows `Premium Waiver (WP) *` and `Estimated Bonus Rate (per mille)`. The boolean controls are compact select fields with `No` visible by default. The premium-factor control shows `None` with a clear icon and dropdown arrow. The primary fields use the same white, lightly bordered, rounded input style as Personal Details.

The bottom controls remain `Cancel`, `Previous`, and `Next` with consistent heights and right/left arrow icons.

## Image 3 — Member Coverage, no additional configuration required

The active tab is `Member Coverage`. The main white card starts with a grey/light section header titled `Principal Member (Policy Holder)` and a person icon. A single horizontal information row shows `Name: Zachary Musa Otieno`, `Date of Birth: 1996-01-01`, and `Gender: male`.

Below it is a full-width light-blue information banner with the exact message: `Selected plans do not require additional member coverage configuration. Principal member is configured automatically.` There is no add-member table in this state. The bottom-right `Next` button is visually active, while `Previous` remains outlined and `Cancel` remains on the left.

## Image 4 — Installments list

The active tab is `Installments`. The main card starts with a light section header containing an amber/orange installment icon, title `Installment Configurations`, and subtitle `Configure installment payouts for whole life plans`.

A table is visible with these headers: `Plan/Sub-Product`, `Policy Term (Years)`, `Payment Mode`, `No. of Installments`, `Status`, and `Actions`. One row shows the selected plan in bold uppercase across two lines, policy term `10`, `Not Set` for payment mode, `Not Set` for number of installments, a dark grey rounded status badge `Ready to Configure`, and a purple `Configure` button with a gear/settings icon. The table is enclosed in a lightly bordered white card.

## Image 5 — Configure Installments modal

The background is dimmed by a translucent dark overlay. A centered white modal has the title `Configure Installments` and a close `X` in the upper-right. The first line reads `Plan/Sub-Product: DUAL PROTECTION AND SAVINGS ENDOWMENT PLAN`, with the plan value in blue/purple emphasis.

A full-width blue information banner states: `No templates available. You can still configure installments manually by filling in the fields below.`

The first form row shows `Annuity Period (years) *` with value `1`. The next row contains `Payment Mode *` with `Annually` selected, a greyed read-only `Policy Term *` with value `10`, and a greyed read-only `Total Number of Installments *` with value `1`. A helper message below Policy Term says it is inherited from the plan configuration.

Two side-by-side toggles are shown: `After Maturity Benefits` with helper text `Member will get benefits after policy maturity`, and `Before Maturity Benefits` with helper text `Member will get benefits before policy maturity`. Both are off in the screenshot.

Below is a table titled `Installment Rate Details` with columns `Installment #`, `Description *`, `Rate (%) *`, and `Paid Up Rate *`. The first row has greyed sequence `1`, description `Installment 1`, rate `100`, and an empty paid-up-rate placeholder `Paid up rate`. The modal footer contains an outlined `Cancel` button and a purple `Save` button with a save icon.

## Image 6 — Investment Funds, not applicable

The active tab is `Investment Funds`. The main content is mostly empty except for a full-width blue information banner reading: `No unit-linked plans selected. Investment fund configuration is only required for unit-linked plans.` This state must not show an empty allocation table or misleading required fields.

## Image 7 — Riders & Benefits, empty state

The active tab is `Riders & Benefits`. The main card has a list icon and title `Selected Riders` on the left and a purple `Configure Riders` button with a settings icon on the right.

A full-width blue information banner says: `No riders configured yet. Click "Configure Riders" to add riders to this quote.` The rest of the card is intentionally empty. The footer controls remain visible.

## Image 8 — Configure Riders modal

The background is dimmed. A centered white modal is titled `Configure Riders` with a close `X`. Inside, a subheading `Rider Configurations` appears on the left and a purple `Add Rider` button with a plus icon on the right.

A bordered section is labeled with a blue `Section 1` badge and has a red-outlined `Delete` button on the right. Its first row contains two select controls: `Product *` with the visible value `017 - DUAL PROTECTION AND SAVINGS EN...`, and `Rider *` with visible value `ACCIDENTAL_BENEFIT - Accidental Benefit`; both show clear/dropdown affordances.

The second row contains `Premium Factor *` with `None` selected and a clear/dropdown affordance, a greyed `Premium Factor Rate (%)` input with placeholder `Enter rate`, and a greyed `Fixed Rate` field showing `Yes` and a small note `(Rate from config)`. The third row shows greyed/read-only `Base` with `1000.00`, greyed/read-only `Rate (per mille)` with `5.0000`, and `Fixed Benefit *` with placeholder `Select fixed benefit`.

The modal footer has `Cancel` and a purple `Save Configuration` button with a save icon.

## Image 9 — Riders & Benefits, selected riders table

The main card title changes to `Selected Riders (2)` and the right-side action becomes an outlined `Edit Configuration` button with an edit icon.

The table headers are: `Product/Sub-Product`, `Rider`, `Loading/Discount`, `Rate`, `Rider Benefit`, and `Actions`. Two rows show the same product, riders `Critical illness` and `Accidental Benefit`, `None` loading/discount, `From table` for the first rate, `5.0000%` for the second rate, benefits `100%(Ratio)` and `50%(Ratio)`, and red `Remove` buttons in the Actions column.

## Image 10 — Financial Details

The active tab is `Financial Details`. The visible form contains `Currency *` with `Select currency`, a greyed `Currency Code` field with `Auto-populated`, and `Currency Rate *` with placeholder `Exchange rate`. Below is `Quote Validity (days) *` with value `30`.

Unlike the other screenshots, this view does not yet show premium breakdown cards or projection tables; the visible contract is the financial input form and its bottom controls. The bottom-left control is `Cancel`, and the bottom-right primary action is `Save`.

## Cross-screen interaction and visual rules

The selected plan count in the blue header is driven by actual selected cards and must never claim a plan is selected when none is selected. Section numbering follows selection order. The left plan list remains visible while the active wizard content changes. The wizard tabs use small icons, an active white-tab/blue-accent treatment, and wrap Financial Details onto a second line at the supplied desktop width.

Every field label uses a required asterisk only where shown. Computed or inherited values are visibly greyed and read-only. Table row actions remain in the outer action column and must not be clipped or overlapped. Buttons use consistent heights, rounded corners, icon-plus-label alignment, and responsive wrapping without creating two visual lines accidentally. Blue banners are reserved for instructional/not-applicable states. Purple/indigo buttons are used for primary actions, while Cancel is a red-accent outline action.

All data values, plans, options, rider names, rates, currency, and user-specific values remain API-driven. No raw UUID may be shown anywhere in the visible quotation screens.

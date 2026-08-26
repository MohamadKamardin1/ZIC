import type { Page } from "@playwright/test"

export const superuser = {
  id: "e2e-superuser",
  email: "superadmin@zic.test",
  firstName: "ZIC",
  lastName: "Superadmin",
  userType: "SUPER_ADMIN",
  user_type: "SUPER_ADMIN",
  isSuperuser: true,
  is_superuser: true,
  permissions: [],
  groups: ["SUPER_ADMIN"],
}

export const quotation = {
  id: "quote-1",
  quote_number: "Q-E2E-0001",
  quote_name: "E2E Family Protection",
  status: "DRAFT",
  currency: "TZS",
  quote_date: "2026-08-19",
  expiry_date: "2026-09-18",
  current_version_number: 1,
  partner_verified: false,
  approval_required: false,
  total_premium: "12000.00",
  total_sum_assured: "100000.00",
  identity_type: "NIN",
  identity_number: "NIN-E2E-001",
  date_of_birth: "1990-01-01",
  age_at_quote: 36,
  gender: "MALE",
  smoker_status: "NON_SMOKER",
  location: "Dar es Salaam",
  address: "Kinondoni",
  created_at: "2026-08-19T10:00:00Z",
  wizard_step_completion: { personal: true, plans: true, members: true, installments: true, funds: true, riders: true, financial: true },
  plan_configurations: [{ id: "config-1", plan_code: "TERM-20", plan_name: "Twenty Year Term", term_years: 20, payment_period_years: 20, premium_frequency: "ANNUAL", quote_basis: "SUM_ASSURED", estimated_maturity_value: "250000" }],
  members: [{ id: "member-1", full_name: "E2E Applicant", relation: "POLICY_HOLDER", date_of_birth: "1990-01-01", age_at_quote: 36, gender: "MALE", is_principal: true }],
  installment_configurations: [{ id: "installment-1", plan_name: "Twenty Year Term", policy_term_years: 20, payment_mode: "ANNUAL", total_number_of_installments: 1, status: "CONFIGURED", after_maturity_benefits: true }],
  fund_allocations: [],
  rider_selections: [],
  benefits: [],
  payment_detail: { id: "payment-1", payment_method: "BANK_TRANSFER", account_reference: "", payment_reference: "", amount: "12000.00", currency: "TZS" },
  underwriting_detail: { id: "underwriting-1", medical_required: false, financial_underwriting_required: false, risk_class: "STANDARD", health_answers: { summary: "No known medical condition." }, medical_requirements: [], declarations: { confirmed: true }, notes: "" },
}

export const financial = {
  quotation_id: "quote-1",
  recalculation_required: false,
  summary: { base_premium: "10000", total_premium: "12000", total_loadings: "500", total_discounts: "0", total_taxes: "0", estimated_maturity_value: "250000", frequency_label: "Annual" },
  projections: [{ policy_year: 1, premiums_paid: "12000", estimated_bonus: "500", surrender_value: "2000", paid_up_value: "4000", estimated_maturity_value: "250000" }],
  installment_payouts: [{ sequence: 1, payout_date: "2046-08-19", description: "Maturity payout", rate_percent: "100", payout_amount: "250000" }],
}

export async function seedSuperuserSession(page: Page) {
  await page.addInitScript((user) => {
    sessionStorage.setItem("aims_access_token", "e2e-access-token")
    sessionStorage.setItem("aims_refresh_token", "e2e-refresh-token")
    sessionStorage.setItem("aims_user", JSON.stringify(user))
  }, superuser)
}

export async function mockAccessApi(page: Page, visibleModules = ["ol_quotations", "ol_parameters", "ol_proposals", "ordinary_life"], permissions: Array<{ module: string; action: string }> = [{ module: "system_parameters", action: "manage" }, { module: "ol_parameters", action: "create" }, { module: "partners", action: "create" }]) {
  await page.route("**/api/v1/iam/me/access/**", async (route) => {
    await route.fulfill({ json: { data: { visibleModules, permissions, groups: ["SUPER_ADMIN"], isSuperuser: true } } })
  })
  await page.route("**/api/v1/auth/me/**", async (route) => {
    await route.fulfill({ json: { data: superuser } })
  })
}

export async function mockQuotationApi(page: Page, overrides: Partial<typeof quotation> = {}) {
  let currentQuotation = { ...quotation, ...overrides }
  const versions = [{ id: "version-1", version_number: 1, status: "CURRENT", created_by: "E2E Superadmin", created_at: "2026-08-19T10:00:00Z", change_reason: "Initial quotation" }]
  const documents = [{ id: "document-1", source_version_number: 1, template_code: "OL_QUOTATION", template_version: "3", document_type: "Quotation PDF", status: "GENERATED", generated_at: "2026-08-19T10:05:00Z", pdf_url: "/media/quotation.pdf" }]

  await page.route("**/api/v1/ol*/quotations/**", async (route) => {
    const url = new URL(route.request().url())
    const path = url.pathname
    const method = route.request().method()
    let response: unknown = {}

    if (path.endsWith("/versions/")) response = { versions }
    else if (path.endsWith("/wizard-summary/")) response = { steps: { "1_product_plan": true, "2_members": true, "3_installments": true, "4_funds": true, "5_riders": true, "6_payment": Boolean(currentQuotation.payment_detail), "7_underwriting": Boolean(currentQuotation.underwriting_detail) } }
    else if (path.endsWith("/documents/")) response = documents
    else if (path.endsWith("/partner-verification/")) response = { partner_exists: false, compliant: currentQuotation.partner_verified === true, missing_fields: ["first_name", "surname"] }
    else if (path.endsWith("/financial-details/")) response = financial
    else if (path.endsWith("/calculate/") && method === "POST") response = financial
    else if (path.endsWith("/finalize/") && method === "POST") { currentQuotation = { ...currentQuotation, status: "FINALIZED" }; response = currentQuotation }
    else if (path.endsWith("/revise/") && method === "POST") { currentQuotation = { ...currentQuotation, status: "DRAFT", current_version_number: Number(currentQuotation.current_version_number ?? 1) + 1 }; response = currentQuotation }
    else if (path.endsWith("/print/") && method === "POST") response = documents[0]
    else if (path.endsWith("/partner-completion/") && method === "POST") { currentQuotation = { ...currentQuotation, partner_verified: true }; response = { partner_verified: true, partner_id: "partner-1" } }
    else if (path.endsWith("/convert-to-proposal/") && method === "POST") { currentQuotation = { ...currentQuotation, status: "CONVERTED" }; response = { quotation: currentQuotation, proposal_id: "proposal-1" } }
    else if (path.match(/\/as-of-version\/\d+\/$/)) response = { ...currentQuotation, version_number: 1, snapshot: currentQuotation }
    else if (path.endsWith("/quotations/") && method === "GET") response = { count: 1, results: [currentQuotation], next: null, previous: null }
    else if (path.endsWith("/quote-1/") && method === "GET") response = currentQuotation
    else if (method === "POST" && path.endsWith("/quotations/")) response = currentQuotation
    else if (path.endsWith("/personal-details-options/")) response = { identity_types: [{ value: "NIN", label: "National Identification Number" }], genders: [{ value: "MALE", label: "Male" }, { value: "FEMALE", label: "Female" }], smoker_statuses: [{ value: "NON_SMOKER", label: "Non-smoker" }], locations: [{ value: "location-1", label: "Dar es Salaam" }], agents: [{ value: "agent-1", label: "E2E Agent" }] }
    else if (path.includes("/personal-details/") && method === "POST") response = currentQuotation
    else if (path.includes("/plans/search/")) response = { count: 1, plans: [{ id: "plan-1", code: "TERM-20", name: "Twenty Year Term", description: "Protection plan for twenty years.", badges: ["WITH_PROFIT"], with_profit: true, joint_life: false, payment_frequencies: ["ANNUAL"], min_entry_age: 18, max_entry_age: 65, min_term_years: 5, max_term_years: 20 }] }
    else if (path.includes("/plan-options/")) response = { payment_frequencies: [{ value: "ANNUAL", label: "Annual" }], quote_bases: [{ value: "SUM_ASSURED", label: "Sum Assured" }], premium_factors: [{ value: "NONE", label: "None" }], plan_features: {} }
    else if (path.endsWith("/members/")) response = { principal_member: { id: "member-1", full_name: "E2E Applicant", relation: "POLICY_HOLDER", date_of_birth: "1990-01-01", age_at_quote: 36, gender: "MALE", is_principal: true }, members: [], additional_members: [], requires_additional_coverage: false, info_banner: "Selected plans do not require additional member coverage configuration. Principal member is configured automatically.", wizard_step_complete: true }
    else if (path.endsWith("/installments/") && method === "GET") response = { rows: [{ plan_configuration_id: "config-1", plan_code: "TERM-20", plan_name: "Twenty Year Term", policy_term_years: 20, payment_mode: "ANNUAL", total_number_of_installments: 1, status: "READY_TO_CONFIGURE", can_configure: true }], requires_configuration: true, wizard_complete: false }
    else if (path.includes("/installments/") && path.includes("/template/")) response = { plan_configuration_id: "config-1", has_template: false, banner: "No templates available. You can still configure installments manually.", policy_term_years: 20, payment_mode: "ANNUAL", available_payment_modes: ["ANNUAL"], rate_rows: [] }
    else if (path.endsWith("/investment-funds/") && method === "GET") response = { plan_rows: [{ plan_configuration_id: "config-1", plan_code: "TERM-20", plan_name: "Twenty Year Term", investment_linked: false, status: "NOT_APPLICABLE", allocations: [] }], not_applicable: true, wizard_complete: true }
    else if (path.includes("/investment-funds/options/")) response = { not_applicable: true, quotation_currency: "TZS", funds: [] }
    else if (path.endsWith("/riders/") && method === "GET") response = { state: { plan_rows: [], available_benefit_types: [], requires_configuration: false, wizard_complete: true } }
    else if (path.includes("/riders/options/")) response = { riders: [], benefit_types: [] }

    await route.fulfill({ json: { data: response } })
  })

  await page.route("**/api/v1/ol/plans/search/**", async (route) => {
    await route.fulfill({ json: { data: { count: 1, plans: [{ id: "plan-1", code: "TERM-20", name: "Twenty Year Term", description: "Protection plan for twenty years.", badges: ["WITH_PROFIT"], with_profit: true, joint_life: false, payment_frequencies: ["ANNUAL"], min_entry_age: 18, max_entry_age: 65, min_term_years: 5, max_term_years: 20 }] } } })
  })
}

export async function mockDropdownQuickCreateApi(page: Page) {
  let productCreated = false
  let memberCreated = false
  let installmentConfigured = false
  let fundCreated = false
  let riderCreated = false
  let benefitCreated = false
  let currentQuotation = { ...quotation, plan_configurations: [], wizard_step_completion: {} }
  const auditEntries: Array<Record<string, unknown>> = []
  const createdOptions: Record<string, { value: string; label: string; meta?: Record<string, unknown> }> = {}

  const optionDefinitions: Record<string, { value: string; label: string }> = {
    "identity-types": { value: "identity-e2e", label: "Passport (E2E)" },
    locations: { value: "location-e2e", label: "Zanzibar City" },
    "plan-types": { value: "plan-type-e2e", label: "Individual Life" },
    products: { value: "product-e2e", label: "E2E Dropdown Product" },
    "member-relations": { value: "relation-e2e", label: "Spouse (E2E)" },
    "payment-modes": { value: "payment-mode-e2e", label: "Electronic Transfer (E2E)" },
    "investment-fund-types": { value: "fund-type-e2e", label: "Balanced (E2E)" },
    "investment-funds": { value: "fund-e2e", label: "ZIC Balanced Fund (E2E)" },
    riders: { value: "rider-e2e", label: "Family Protection Rider (E2E)" },
    "benefit-types": { value: "benefit-e2e", label: "Death Benefit (E2E)" },
  }

  const schemas: Record<string, unknown> = {
    "identity-types": { fields: [{ name: "code", type: "string", required: true }, { name: "name", type: "string", required: true }] },
    locations: { fields: [{ name: "code", type: "string", required: true }, { name: "name", type: "string", required: true }, { name: "branch", type: "select", required: true, choices: [{ value: "branch-e2e", label: "Zanzibar Main Branch" }] }] },
    "plan-types": { fields: [{ name: "code", type: "string", required: true }, { name: "name", type: "string", required: true }, { name: "plan_category", type: "select", required: false, default: "INDIVIDUAL", choices: [{ value: "INDIVIDUAL", label: "Individual" }] }] },
    products: { fields: [{ name: "code", type: "string", required: true }, { name: "name", type: "string", required: true }, { name: "plan_type", type: "select", required: true, nested_entity: "plan-types" }, { name: "insurance_class", type: "select", required: false, default: "INDIVIDUAL", choices: [{ value: "INDIVIDUAL", label: "Individual" }] }, { name: "allow_riders", type: "boolean", required: false, default: true }, { name: "allow_surrender", type: "boolean", required: false, default: true }] },
    "member-relations": { fields: [{ name: "code", type: "string", required: true }, { name: "name", type: "string", required: true }] },
    "payment-modes": { fields: [{ name: "code", type: "string", required: true }, { name: "name", type: "string", required: true }] },
    "investment-fund-types": { fields: [{ name: "code", type: "string", required: true }, { name: "name", type: "string", required: true }, { name: "risk_profile", type: "select", required: false, default: "MODERATE", choices: [{ value: "MODERATE", label: "Moderate" }] }] },
    "investment-funds": { fields: [{ name: "code", type: "string", required: true }, { name: "name", type: "string", required: true }, { name: "fund_type", type: "select", required: true, nested_entity: "investment-fund-types" }, { name: "currency", type: "select", required: false, default: "TZS", choices: [{ value: "TZS", label: "TZS — Tanzanian Shilling" }] }, { name: "valuation_frequency", type: "select", required: false, default: "DAILY", choices: [{ value: "DAILY", label: "Daily" }] }] },
    riders: { fields: [{ name: "code", type: "string", required: true }, { name: "name", type: "string", required: true }, { name: "rider_category", type: "select", required: true, choices: [{ value: "PROTECTION", label: "Protection" }] }, { name: "benefit_type", type: "select", required: true, choices: [{ value: "DEATH", label: "Death" }] }, { name: "calculation_basis", type: "select", required: false, default: "SUM_ASSURED", choices: [{ value: "SUM_ASSURED", label: "Sum Assured" }] }] },
    "benefit-types": { fields: [{ name: "code", type: "string", required: true }, { name: "name", type: "string", required: true }] },
  }

  const audit = (entity: string, option: { value: string; label: string }) => {
    auditEntries.push({ id: `audit-${auditEntries.length + 1}`, action: "CREATE", source_channel: "QUICK_CREATE", reason: "Created from OL quotation wizard", actor: "e2e-superuser", actor_display: "ZIC Superadmin", entity, object_id: option.value })
  }

  await page.route("**/api/v1/ol/options/**", async (route) => {
    const url = new URL(route.request().url())
    const segments = url.pathname.split("/").filter(Boolean)
    const entity = segments[segments.indexOf("options") + 1]
    const method = route.request().method()
    if (!entity) return route.fallback()
    if (segments.includes("quick-create-schema")) {
      await route.fulfill({ json: { data: schemas[entity] ?? { fields: [] } } })
      return
    }
    if (segments.includes("quick-create") && method === "POST") {
      const definition = optionDefinitions[entity]
      if (!definition) { await route.fulfill({ status: 400, json: { detail: "Unknown entity" } }); return }
      const option = { ...definition, meta: { code: definition.value, name: definition.label } }
      createdOptions[entity] = option
      if (entity === "products") productCreated = true
      if (entity === "member-relations") memberCreated = true
      if (entity === "investment-fund-types") createdOptions[entity] = option
      if (entity === "investment-funds") fundCreated = true
      if (entity === "riders") riderCreated = true
      if (entity === "benefit-types") benefitCreated = true
      audit(entity, option)
      await route.fulfill({ status: 201, json: { data: option } })
      return
    }
    const baseline: Record<string, { value: string; label: string }[]> = {
      "payment-frequencies": [{ value: "ANNUAL", label: "Annual" }],
      "quote-bases": [{ value: "SUM_ASSURED", label: "Sum Assured" }],
      "premium-factors": [{ value: "NONE", label: "None" }],
      currencies: [{ value: "TZS", label: "TZS — Tanzanian Shilling" }],
      agents: [{ value: "agent-1", label: "E2E Agent" }],
      "benefit-types": [],
      riders: [],
    }
    const option = createdOptions[entity]
    const results = option ? [option] : (baseline[entity] ?? [])
    await route.fulfill({ json: { data: { count: results.length, results, next: null, previous: null } } })
  })

  await page.route("**/api/v1/onboarding/locations/**", async (route) => {
    await route.fulfill({ json: { data: [] } })
  })

  await page.route("**/api/v1/governance/audit-logs/**", async (route) => {
    await route.fulfill({ json: { data: { count: auditEntries.length, results: auditEntries, next: null, previous: null } } })
  })

  await page.route("**/api/v1/ol*/quotations/**", async (route) => {
    const url = new URL(route.request().url())
    const path = url.pathname
    const method = route.request().method()
    let response: unknown
    if (path.endsWith("/personal-details-options/")) response = { identity_types: [], genders: [{ value: "MALE", label: "Male" }, { value: "FEMALE", label: "Female" }], smoker_statuses: [{ value: "NON_SMOKER", label: "Non-smoker" }], locations: [], agents: [{ value: "agent-1", label: "E2E Agent" }] }
    else if (path.includes("/plans/search/")) response = { count: productCreated ? 1 : 0, plans: productCreated ? [{ id: "product-e2e", plan_id: "product-e2e", product_version_id: "product-e2e-version", code: "E2E-DROPDOWN", name: "E2E Dropdown Product", description: "Created from the quotation wizard.", badges: ["WITH_PROFIT"], with_profit: true, joint_life: false, payment_frequencies: ["ANNUAL"], min_entry_age: 18, max_entry_age: 65, min_term_years: 5, max_term_years: 20 }] : [] }
    else if (path.endsWith("/plan-options/") || path.includes("/plan-options?")) response = { payment_frequencies: [{ value: "ANNUAL", label: "Annual" }], quote_bases: [{ value: "SUM_ASSURED", label: "Sum Assured" }], premium_factors: [{ value: "NONE", label: "None" }], plan_features: {} }
    else if (path.endsWith("/personal-details/") && method === "POST") response = currentQuotation
    else if (path.endsWith("/plans/") && method === "POST") { currentQuotation = { ...currentQuotation, plan_configurations: [{ id: "config-e2e", plan_id: "product-e2e", product_version_id: "product-e2e-version", plan_code: "E2E-DROPDOWN", plan_name: "E2E Dropdown Product", term_years: 20, payment_period_years: 20, premium_frequency: "ANNUAL", quote_basis: "SUM_ASSURED", estimated_maturity_value: "250000", premium_factor: "NONE", is_selected: true }] }; response = { configurations: currentQuotation.plan_configurations, quotation: currentQuotation }
    }
    else if (path.endsWith("/members/") && method === "GET") response = { principal_member: { id: "member-principal", full_name: "E2E Applicant", relation: "POLICY_HOLDER", date_of_birth: "1990-01-01", age_at_quote: 36, gender: "MALE", is_principal: true }, members: memberCreated ? [{ id: "member-e2e", full_name: "E2E Spouse", relation: "relation-e2e", date_of_birth: "1992-01-01", age_at_quote: 34, gender: "FEMALE", is_principal: false }] : [], additional_members: memberCreated ? [{ id: "member-e2e", full_name: "E2E Spouse", relation: "relation-e2e", date_of_birth: "1992-01-01", age_at_quote: 34, gender: "FEMALE", is_principal: false }] : [], requires_additional_coverage: true, wizard_step_complete: memberCreated }
    else if (path.endsWith("/members/") && method === "POST") { memberCreated = true; response = { id: "member-e2e" } }
    else if (path.endsWith("/installments/") && method === "GET") response = { rows: [{ plan_configuration_id: "config-e2e", plan_code: "E2E-DROPDOWN", plan_name: "E2E Dropdown Product", policy_term_years: 20, payment_mode: "payment-mode-e2e", total_number_of_installments: 1, status: installmentConfigured ? "CONFIGURED" : "READY_TO_CONFIGURE", can_configure: true }], requires_configuration: true, wizard_complete: installmentConfigured }
    else if (path.includes("/installments/") && path.includes("/template/")) response = { plan_configuration_id: "config-e2e", has_template: false, banner: "No templates available. You can still configure installments manually.", policy_term_years: 20, payment_mode: "payment-mode-e2e", available_payment_modes: [], rate_rows: [] }
    else if (path.includes("/installments/") && path.includes("/configure/") && method === "POST") { installmentConfigured = true; response = { status: "CONFIGURED" } }
    else if (path.endsWith("/investment-funds/") && method === "GET") response = { plan_rows: [{ plan_configuration_id: "config-e2e", plan_code: "E2E-DROPDOWN", plan_name: "E2E Dropdown Product", investment_linked: true, status: fundCreated ? "CONFIGURED" : "READY_TO_CONFIGURE", allocations: fundCreated ? [{ id: "allocation-e2e", fund_id: "fund-e2e", fund_display: "ZIC Balanced Fund (E2E)", allocation_percent: "100", amount: "250000" }] : [] }], not_applicable: false, wizard_complete: fundCreated }
    else if (path.includes("/investment-funds/options/")) response = { not_applicable: false, quotation_currency: "TZS", funds: fundCreated ? [{ value: "fund-e2e", label: "ZIC Balanced Fund (E2E)" }] : [] }
    else if (path.endsWith("/investment-funds/") && method === "POST") { fundCreated = true; response = { status: "CONFIGURED" } }
    else if (path.endsWith("/riders/") && method === "GET") response = { state: { plan_rows: [{ plan_configuration_id: "config-e2e", plan_code: "E2E-DROPDOWN", plan_name: "E2E Dropdown Product", riders: riderCreated ? [{ rider_id: "rider-e2e", rider_display: "Family Protection Rider (E2E)", rider_sum_assured: "100000", rider_term_years: 20, benefit_basis: "FIXED", benefit_value: "100000", benefits: benefitCreated ? [{ beneficial_type_id: "benefit-e2e", benefit_type_display: "Death Benefit (E2E)", benefit_basis: "FIXED", benefit_value: "100000" }] : [] }] : [] }], available_benefit_types: benefitCreated ? [{ value: "benefit-e2e", label: "Death Benefit (E2E)" }] : [], requires_configuration: true, wizard_complete: riderCreated && benefitCreated } }
    else if (path.includes("/riders/options/")) response = { riders: riderCreated ? [{ value: "rider-e2e", label: "Family Protection Rider (E2E)" }] : [], benefit_types: benefitCreated ? [{ value: "benefit-e2e", label: "Death Benefit (E2E)" }] : [] }
    else if (path.endsWith("/riders/") && method === "POST") { riderCreated = true; benefitCreated = true; response = { status: "CONFIGURED" } }
    else if (path.endsWith("/wizard-summary/")) response = { steps: { "1_product_plan": productCreated, "2_members": memberCreated, "3_installments": installmentConfigured, "4_funds": fundCreated, "5_riders": riderCreated && benefitCreated, "6_payment": Boolean(currentQuotation.payment_detail), "7_underwriting": Boolean(currentQuotation.underwriting_detail) } }
    else if (path.endsWith("/financial-details/") || path.endsWith("/calculate/")) response = financial
    else if (path.endsWith("/finalize/") && method === "POST") { currentQuotation = { ...currentQuotation, status: "FINALIZED" }; response = currentQuotation }
    else response = currentQuotation
    await route.fulfill({ json: { data: response } })
  })

  await page.route("**/api/v1/ol-quotations/quotations/", async (route) => {
    if (route.request().method() === "POST") await route.fulfill({ json: { data: { ...currentQuotation, id: "quote-1" } } })
    else await route.fallback()
  })

  await page.route("**/api/v1/ol/plans/search/**", async (route) => {
    const plans = productCreated ? [{ id: "product-e2e", plan_id: "product-e2e", product_version_id: "product-e2e-version", code: "E2E-DROPDOWN", name: "E2E Dropdown Product", description: "Created from the quotation wizard.", badges: ["WITH_PROFIT"], with_profit: true, joint_life: false, payment_frequencies: ["ANNUAL"], min_entry_age: 18, max_entry_age: 65, min_term_years: 5, max_term_years: 20 }] : []
    await route.fulfill({ json: { data: { count: plans.length, plans } } })
  })
}

export async function mockCommitmentPrintApi(page: Page) {
  const detail = {
    id: "c-1",
    commitmentNumber: "OLC-2026-00001",
    sourceType: "POLICY",
    sourceReference: "POL-2026-0001",
    partnerName: "Zanzibar Trading Co.",
    productName: "Family Protection",
    planName: "Standard",
    currency: "TZS",
    premiumFrequency: "MONTHLY",
    installmentNumber: 7,
    installmentCount: 120,
    dueDate: "2026-08-29",
    premiumAmount: "100000.00",
    amountPaid: "40000.00",
    balance: "60000.00",
    status: "PARTIALLY_PAID",
    graceDate: "2026-09-28",
    lapseDate: "2026-10-18",
    graceDays: 30,
    statusHistory: [],
    allocations: [],
    notificationLogs: [],
  }
  await page.route("**/api/v1/ol-commitments/**", async (route) => {
    const url = new URL(route.request().url())
    const path = url.pathname
    if (path.includes("/c-1/")) {
      await route.fulfill({ json: { data: detail } })
      return
    }
    if (path.endsWith("/commitments/")) {
      await route.fulfill({ json: { data: { count: 1, results: [detail], next: null, previous: null } } })
      return
    }
    await route.fulfill({ json: { data: { count: 0, results: [] } } })
  })
}

export async function mockUnifiedDocumentApi(page: Page, options: { expireFirstDownload?: boolean } = {}) {
  let firstDownloadExpired = false
  let refreshCalls = 0
  const records = {
    OL_QUOTATION: { id: "document-quote-1", document_type: "OL_QUOTATION", template_name: "Ordinary Life Quotation", template_version: 1, generated_by_display: "ZIC Superadmin", generated_at: "2026-08-19T10:05:00Z", page_count: 2, signed_download_url: "/api/v1/documents/instances/document-quote-1/download/?ticket=quote-ticket" },
    PROPOSAL_SUMMARY: { id: "document-proposal-1", document_type: "PROPOSAL_SUMMARY", template_name: "Proposal Summary", template_version: 1, generated_by_display: "ZIC Superadmin", generated_at: "2026-08-19T10:06:00Z", page_count: 1, signed_download_url: "/api/v1/documents/instances/document-proposal-1/download/?ticket=proposal-ticket" },
    COMMITMENT_STATEMENT: { id: "document-commitment-1", document_type: "COMMITMENT_STATEMENT", template_name: "Commitment Statement", template_version: 1, generated_by_display: "ZIC Superadmin", generated_at: "2026-08-19T10:07:00Z", page_count: 1, signed_download_url: "/api/v1/documents/instances/document-commitment-1/download/?ticket=commitment-ticket" },
  }

  await page.route("**/api/v1/auth/refresh/**", async (route) => {
    refreshCalls += 1
    await route.fulfill({ json: { data: { access: "e2e-refreshed-access-token", refresh: "e2e-refreshed-refresh-token" } } })
  })

  await page.route("**/api/v1/documents/**", async (route) => {
    const url = new URL(route.request().url())
    const path = url.pathname
    if (path.endsWith("/download/")) {
      if (options.expireFirstDownload && !firstDownloadExpired) {
        firstDownloadExpired = true
        await route.fulfill({ status: 401, json: { detail: "Authentication credentials were not provided" } })
        return
      }
      await route.fulfill({ status: 200, contentType: "application/pdf", headers: { "Content-Disposition": "inline; filename=document.pdf" }, body: "%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF" })
      return
    }
    if (path.endsWith("/instances/")) {
      const sourceType = url.searchParams.get("source_type") ?? ""
      const documentType = sourceType.includes("proposal") ? "PROPOSAL_SUMMARY" : sourceType.includes("commitment") ? "COMMITMENT_STATEMENT" : "OL_QUOTATION"
      await route.fulfill({ json: { data: { count: 1, page: 1, page_size: 50, results: [records[documentType]] } } })
      return
    }
    if (path.includes("/render/") && route.request().method() === "POST") {
      const documentType = path.split("/").filter(Boolean).at(-2) as keyof typeof records
      await route.fulfill({ status: 201, json: { data: records[documentType] ?? records.OL_QUOTATION } })
      return
    }
    await route.fulfill({ json: { data: {} } })
  })

  const proposal = { id: "proposal-1", proposal_number: "OLP-E2E-0001", quotation_number: "Q-E2E-0001", underwriting_status: "READY", status: "ACTIVE", created_at: "2026-08-19T10:00:00Z" }
  const proposalListResponse = { data: { count: 1, results: [proposal] } }
  const proposalDetailResponse = { data: proposal }
  const proposalHandler = async (route: import("@playwright/test").Route) => {
    const path = new URL(route.request().url()).pathname
    await route.fulfill({ json: path.endsWith("/proposals/") ? proposalListResponse : proposalDetailResponse })
  }
  await page.route("**/api/v1/ordinary-life/core/proposals/**", proposalHandler)
  await page.route("**/api/v1/ol-proposals/proposals/**", proposalHandler)

  return { getRefreshCalls: () => refreshCalls }
}

export async function mockParameterApi(page: Page) {
  await page.route("**/api/v1/ol-parameters/**", async (route) => {
    const method = route.request().method()
    const url = new URL(route.request().url())
    if (method === "POST") {
      await route.fulfill({ status: 201, json: { data: { id: "parameter-e2e", key: "E2E_PARAMETER", value: "10", status: "ACTIVE" } } })
      return
    }
    if (method === "PATCH") {
      await route.fulfill({ json: { data: { id: "parameter-e2e", key: "E2E_PARAMETER", value: "20", status: "ACTIVE" } } })
      return
    }
    if (url.pathname.endsWith("/default-system-parameters/")) {
      await route.fulfill({ json: { data: { count: 1, results: [{ id: "parameter-e2e", category: "E2E", key: "E2E_PARAMETER", value_type: "DECIMAL", value: "10", status: "ACTIVE", effective_from: "2026-01-01" }] } } })
      return
    }
    await route.fulfill({ json: { data: { count: 0, results: [] } } })
  })
}

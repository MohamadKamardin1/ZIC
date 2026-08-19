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

export async function mockAccessApi(page: Page, visibleModules = ["ol_quotations", "ol_parameters", "ol_proposals", "ordinary_life"]) {
  await page.route("**/api/v1/iam/me/access/**", async (route) => {
    await route.fulfill({ json: { data: { visibleModules, permissions: [], groups: ["SUPER_ADMIN"], isSuperuser: true } } })
  })
  await page.route("**/api/v1/auth/me/**", async (route) => {
    await route.fulfill({ json: { data: superuser } })
  })
}

export async function mockQuotationApi(page: Page, overrides: Partial<typeof quotation> = {}) {
  let currentQuotation = { ...quotation, ...overrides }
  const versions = [{ id: "version-1", version_number: 1, status: "CURRENT", created_by: "E2E Superadmin", created_at: "2026-08-19T10:00:00Z", change_reason: "Initial quotation" }]
  const documents = [{ id: "document-1", source_version_number: 1, template_code: "OL_QUOTATION", template_version: "3", document_type: "Quotation PDF", status: "GENERATED", generated_at: "2026-08-19T10:05:00Z", pdf_url: "/media/quotation.pdf" }]

  await page.route("**/api/v1/ol-quotations/quotations/**", async (route) => {
    const url = new URL(route.request().url())
    const path = url.pathname
    const method = route.request().method()
    let response: unknown = {}

    if (path.endsWith("/versions/")) response = { versions }
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
    else if (path.endsWith("/personal-details-options/")) response = { identity_types: [{ value: "NIN", label: "National Identification Number" }], genders: [{ value: "MALE", label: "Male" }], smoker_statuses: [{ value: "NON_SMOKER", label: "Non-smoker" }], locations: [{ value: "location-1", label: "Dar es Salaam" }], agents: [{ value: "agent-1", label: "E2E Agent" }] }
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

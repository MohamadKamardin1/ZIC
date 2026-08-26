import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { beforeEach, describe, expect, it, vi } from "vitest"
import OLQuotationWizard from "./OLQuotationWizard"

const { requestMock, navigateMock, toastMock, MockApiClientError } = vi.hoisted(() => {
  class HoistedApiClientError extends Error {
    fieldErrors: Record<string, string[]>
    status = 400
    code = "VALIDATION_ERROR"
    constructor(message: string, fieldErrors: Record<string, string[]> = {}) {
      super(message)
      this.fieldErrors = fieldErrors
    }
  }
  return { requestMock: vi.fn(), navigateMock: vi.fn(), toastMock: vi.fn(), MockApiClientError: HoistedApiClientError }
})

vi.mock("../../lib/apiClient", () => ({
  request: requestMock,
  ApiClientError: MockApiClientError,
}))

vi.mock("../../lib/access", () => ({
  useAccess: () => ({
    access: { visibleModules: [], permissions: [
      { module: "system_parameters", action: "manage" },
      { module: "ol_parameters", action: "create" },
      { module: "partners", action: "create" },
    ], groups: [] },
    isLoading: false,
    isError: false,
    isSuperAdmin: true,
    canAccess: () => true,
    hasPermission: () => true,
  }),
}))

vi.mock("react-router-dom", () => ({
  useNavigate: () => navigateMock,
  useParams: () => ({}),
}))

vi.mock("../../components/ui/Toast", () => ({
  useToast: () => ({ toast: toastMock, dismiss: vi.fn() }),
}))

const quotation = {
  id: "quote-1",
  quote_number: "Q-0001",
  status: "DRAFT",
  currency: "TZS",
  expiry_date: "2026-09-18",
  wizard_step_completion: {},
  plan_configurations: [],
  payment_detail: { id: "payment-1", payment_method: "BANK_TRANSFER", account_reference: "", payment_reference: "", amount: "12500.00", currency: "TZS" },
  underwriting_detail: { id: "underwriting-1", medical_required: false, financial_underwriting_required: false, risk_class: "STANDARD", health_answers: { summary: "No known medical condition." }, medical_requirements: [], declarations: { confirmed: true }, notes: "" },
}

const plans = [
  {
    id: "plan-1",
    plan_id: "plan-1",
    product_version_id: "version-1",
    product_code: "OL001",
    product_name: "Family Protection",
    code: "TERM-20",
    name: "Twenty Year Term",
    description: "Protection plan for twenty years.",
    badges: ["WITH_PROFIT", "JOINT_LIFE"],
    with_profit: true,
    joint_life: true,
    mortgage: false,
    personal_accident: false,
    premium_waiver: false,
    payment_frequencies: ["ANNUALLY", "MONTHLY"],
    min_entry_age: 18,
    max_entry_age: 65,
    min_term_years: 5,
    max_term_years: 20,
    minimum_sum_assured: "1000.00",
    maximum_sum_assured: "10000000.00",
  },
  {
    id: "plan-2",
    plan_id: "plan-2",
    product_version_id: "version-1",
    product_code: "OL001",
    product_name: "Family Protection",
    code: "TERM-10",
    name: "Ten Year Term",
    description: "Short-term protection plan.",
    badges: [],
    with_profit: false,
    joint_life: false,
    mortgage: false,
    personal_accident: false,
    premium_waiver: false,
    payment_frequencies: ["ANNUALLY"],
    min_entry_age: 18,
    max_entry_age: 65,
    min_term_years: 5,
    max_term_years: 10,
    minimum_sum_assured: "1000.00",
    maximum_sum_assured: "10000000.00",
  },
]

let templateRows: Array<{ sequence: number; description: string; rate_percent: string; paid_up_rate: string | null }> = []
let productCreatedScenario = false
let memberCoverageScenario = false
let investmentFundScenario = false
let riderScenario = false
let financialScenario = false
let finalizeBlocked = false
let finalizedScenario = false
let planSelectionError = false
let latestFundPayload: Record<string, unknown> | null = null
let latestRiderPayload: Record<string, unknown> | null = null
const benefitTypeUuid = "11111111-1111-4111-8111-111111111111"

const configuration = {
  id: "config-1",
  plan: "plan-1",
  product_version: "version-1",
  section_number: 1,
  term_years: 20,
  payment_period_years: 20,
  premium_frequency: "ANNUALLY",
  quote_basis: "SUM_ASSURED",
  estimated_maturity_value: "100000.00",
  base_sum_assured: "1000.00",
  premium_factor: "NONE",
  joint_life: false,
  mortgage: false,
  personal_accident: false,
  premium_waiver: false,
  estimated_bonus_rate: "2.500000",
  is_selected: true,
}

beforeEach(() => {
  localStorage.clear()
  sessionStorage.clear()
  window.history.replaceState({}, "", "/")
  requestMock.mockReset()
  navigateMock.mockReset()
  toastMock.mockReset()
  templateRows = []
  productCreatedScenario = false
  memberCoverageScenario = false
  investmentFundScenario = false
  riderScenario = false
  financialScenario = false
  finalizeBlocked = false
  finalizedScenario = false
  planSelectionError = false
  latestFundPayload = null
  latestRiderPayload = null
  requestMock.mockImplementation(async (path: string, options?: RequestInit) => {
    const draftResponse = finalizedScenario ? { ...quotation, status: "FINALIZED", wizard_step_completion: { "1_personal_details": true, "2_plan_and_sub_products": true, "3_member_coverage": true, "4_installments": true, "5_investment_funds": true, "6_riders_and_benefits": true, "7_financial_details": true } } : financialScenario && finalizeBlocked ? { ...quotation, wizard_step_completion: { "1_personal_details": true, "2_plan_and_sub_products": true, "3_member_coverage": true, "4_installments": true, "5_investment_funds": true, "6_riders_and_benefits": true, "7_financial_details": true } } : quotation
    if (path === "/api/v1/ol-quotations/quotations/" && options?.method === "POST") return draftResponse
    if (path === "/api/v1/ol-quotations/quotations/quote-1/") return draftResponse
    if (path.includes("/personal-details-options/")) return {
      identity_types: [{ value: "NIN", label: "National Identification Number" }],
      genders: [{ value: "MALE", label: "Male" }],
      smoker_statuses: [{ value: "NON_SMOKER", label: "Non-smoker" }],
      locations: [{ value: "location-1", label: "Dar es Salaam" }],
      agents: [{ value: "agent-1", label: "Asha Agent" }],
    }
    if (path.includes("/api/v1/ol/options/products/quick-create-schema/")) return {
      permission: "ol_parameters.create",
      fields: [
        { name: "code", type: "string", required: true },
        { name: "name", type: "string", required: true },
      ],
    }
    if (path.includes("/api/v1/ol/options/member-relations/quick-create-schema/")) return { permission: "system_parameters.manage", fields: [{ name: "code", type: "string", required: true }, { name: "name", type: "string", required: true }] }
    if (path.includes("/api/v1/ol/options/cover-types/quick-create-schema/")) return { permission: "system_parameters.manage", fields: [{ name: "code", type: "string", required: true }, { name: "name", type: "string", required: true }] }
    if (path.includes("/api/v1/ol/options/payment-modes/quick-create-schema/")) return { permission: "system_parameters.manage", fields: [{ name: "code", type: "string", required: true }, { name: "name", type: "string", required: true }] }
    if (path.includes("/api/v1/ol/options/benefit-types/quick-create-schema/")) return { permission: "system_parameters.manage", fields: [{ name: "code", type: "string", required: true }, { name: "name", type: "string", required: true }] }
    if (path.includes("/api/v1/ol/options/riders/quick-create-schema/")) return { permission: "ol_parameters.create", fields: [{ name: "code", type: "string", required: true }, { name: "name", type: "string", required: true }, { name: "rider_category", type: "string", required: true }] }
    if (path.includes("/api/v1/ol/options/investment-funds/quick-create-schema/")) return { permission: "ol_parameters.create", fields: [{ name: "code", type: "string", required: true }, { name: "name", type: "string", required: true }, { name: "fund_type", type: "select", required: true, choices: [{ value: "BALANCED", label: "Balanced" }], nested_entity: "investment-fund-types" }] }
    if (path.includes("/api/v1/ol/options/investment-fund-types/quick-create-schema/")) return { permission: "ol_parameters.create", fields: [{ name: "code", type: "string", required: true }, { name: "name", type: "string", required: true }]
    }
    if (path.includes("/api/v1/ol/options/products/quick-create/") && options?.method === "POST") {
      productCreatedScenario = true
      return { value: "plan-created", label: "New Product", meta: { product_code: "OLNEW", product_name: "New Product" } }
    }
    if (path.includes("/api/v1/ol/options/member-relations/quick-create/") && options?.method === "POST") return { value: "SIBLING", label: "Sibling" }
    if (path.includes("/api/v1/ol/options/cover-types/quick-create/") && options?.method === "POST") return { value: "DEPENDENT", label: "Dependent Cover" }
    if (path.includes("/api/v1/ol/options/payment-modes/quick-create/") && options?.method === "POST") return { value: "MOBILE_MONEY", label: "Mobile money" }
    if (path.includes("/api/v1/ol/options/benefit-types/quick-create/") && options?.method === "POST") return { value: benefitTypeUuid, label: "Accidental Benefit", meta: { code: "ACCIDENTAL", name: "Accidental Benefit" } }
    if (path.includes("/api/v1/ol/options/riders/quick-create/") && options?.method === "POST") return { value: "rider-created", label: "Travel Protection", meta: { code: "TRAVEL-01", name: "Travel Protection", rider_category: "TRAVEL" } }
    if (path.includes("/api/v1/ol/options/investment-fund-types/quick-create/") && options?.method === "POST") return { value: "BALANCED", label: "Balanced" }
    if (path.includes("/api/v1/ol/options/investment-funds/quick-create/") && options?.method === "POST") return { value: "fund-created", label: "New Fund", meta: { code: "FUND-NEW", name: "New Fund" } }
    if (path.startsWith("/api/v1/ol/options/")) {
      const entity = path.split("/api/v1/ol/options/")[1]?.split("/")[0]
      const optionsByEntity: Record<string, Array<{ value: string; label: string }>> = {
        "identity-types": [{ value: "NIN", label: "National Identification Number" }],
        locations: [{ value: "location-1", label: "Dar es Salaam" }],
        agents: [{ value: "agent-1", label: "Asha Agent" }],
        "payment-frequencies": [{ value: "ANNUAL", label: "Annual" }, { value: "MONTHLY", label: "Monthly" }],
        "quote-bases": [{ value: "SUM_ASSURED", label: "Sum Assured" }],
        "premium-factors": [{ value: "NONE", label: "None" }],
        "member-relations": [{ value: "CHILD", label: "Child" }, { value: "SPOUSE", label: "Spouse" }],
        "cover-types": [{ value: "DEPENDENT", label: "Dependent Cover" }],
        "payment-modes": [{ value: "BANK_TRANSFER", label: "Bank transfer" }, { value: "ANNUAL", label: "Annual" }, { value: "MONTHLY", label: "Monthly" }],
        "benefit-types": [{ value: benefitTypeUuid, label: "Death Benefit" }],
        "investment-funds": [{ value: "fund-1", label: "FUND-1 — Balanced Growth" }],
        "investment-fund-types": [{ value: "BALANCED", label: "Balanced" }],
        products: plans.map((plan) => ({ value: plan.plan_id, label: plan.name })),
      }
      return { items: optionsByEntity[entity ?? ""] ?? [] }
    }
    if (path.startsWith("/api/v1/ol/plans/search/")) {
      const refreshedPlan = { ...plans[0], id: "plan-created", plan_id: "plan-created", product_version_id: "version-created", product_code: "OLNEW", product_name: "New Product", code: "OLNEW", name: "New Product", description: "A newly created product." }
      const availablePlans = productCreatedScenario ? [...plans, refreshedPlan] : plans
      return { plans: availablePlans, count: availablePlans.length }
    }
    if (path.includes("/plan-options/")) return {
      payment_frequencies: [{ value: "ANNUALLY", label: "Annually" }, { value: "MONTHLY", label: "Monthly" }],
      quote_bases: [{ value: "SUM_ASSURED", label: "Sum Assured" }],
      premium_factors: [{ value: "NONE", label: "None" }],
      constraints: {
        plan_code: "TERM-20",
        plan_name: "Twenty Year Term",
        currency: "TZS",
        min_entry_age: 18,
        max_entry_age: 65,
        min_term_years: 5,
        max_term_years: 20,
        minimum_sum_assured: "1000.00",
        maximum_sum_assured: "10000000.00",
        allowed_payment_frequencies: [{ value: "ANNUALLY", label: "Annually" }, { value: "MONTHLY", label: "Monthly" }],
        default_term_years: 5,
        default_payment_period_years: 5,
        default_payment_frequency: "ANNUALLY",
        default_quote_basis: "SUM_ASSURED",
        default_premium_factor: "NONE",
        default_base_sum_assured: "1000.00",
        default_estimated_maturity_value: "1000.00",
        default_estimated_bonus_rate: "0",
        feature_availability: { joint_life: true, mortgage: false, personal_accident: false, premium_waiver: false },
      },
      plan_features: { joint_life: true, mortgage: false, personal_accident: false, premium_waiver: false },
    }
    if (path.endsWith("/members/")) return memberCoverageScenario ? {
      principal_member: { id: "member-principal", full_name: "Asha Applicant", relation: "POLICY_HOLDER", date_of_birth: "1990-01-01", age_at_quote: 36, gender: "MALE", sum_assured: null, is_principal: true },
      members: [],
      additional_members: [],
      requires_additional_coverage: true,
      info_banner: null,
      allowed_configurations: [{ relation: "CHILD", cover_type: "DEPENDENT", min_age: 1, max_age: 17, waiting_period_days: 30, benefit_limit: "5000.00", coverage_basis: "SUM_ASSURED" }],
      wizard_step_complete: false,
    } : {
      principal_member: { id: "member-principal", full_name: "Asha Applicant", relation: "POLICY_HOLDER", date_of_birth: "1990-01-01", age_at_quote: 36, gender: "MALE", sum_assured: null, is_principal: true },
      members: [],
      additional_members: [],
      requires_additional_coverage: false,
      info_banner: "Selected plans do not require additional member coverage configuration. Principal member is configured automatically.",
      allowed_configurations: [],
      wizard_step_complete: true,
    }
    if (path.endsWith("/installments/") && !path.includes("/template") && !path.includes("/configure")) return {
      rows: [{ plan_configuration_id: "config-1", plan_code: "TERM-20", plan_name: "Twenty Year Term", policy_term_years: 20, payment_mode: "ANNUAL", total_number_of_installments: 1, status: "READY_TO_CONFIGURE", can_configure: true }],
      requires_configuration: true,
      wizard_complete: false,
    }
    if (path.includes("/installments/config-1/template/")) return {
      plan_configuration_id: "config-1",
      has_template: templateRows.length > 0,
      banner: templateRows.length ? "Template rows loaded." : "No templates available. You can still configure installments manually.",
      policy_term_years: 20,
      payment_mode: "BANK_TRANSFER",
      available_payment_modes: ["BANK_TRANSFER", "MOBILE_MONEY", "CASH"],
      rate_rows: templateRows,
    }
    if (path.endsWith("/investment-funds/") && options?.method === "POST") {
      latestFundPayload = JSON.parse(String(options.body ?? "{}")) as Record<string, unknown>
      return { quotation_id: "quote-1", wizard_step_complete: true }
    }
    if (path.endsWith("/investment-funds/") && !options?.method) return investmentFundScenario ? {
      plan_rows: [{ plan_configuration_id: "config-1", plan_code: "TERM-20", plan_name: "Investment-linked Plan", investment_linked: true, status: "READY_TO_CONFIGURE", allocation_total: "60.0000", allocations: [{ plan_configuration_id: "config-1", fund_id: "fund-1", allocation_percent: "60.0000", allocated_amount: null, fund_name: "Balanced Growth", fund_code: "FUND-1" }], can_configure: true }],
      requires_allocation: true,
      not_applicable: false,
      wizard_complete: false,
    } : {
      plan_rows: [{ plan_configuration_id: "config-1", plan_code: "TERM-20", plan_name: "Twenty Year Term", investment_linked: false, status: "NOT_APPLICABLE", allocation_total: "0.0000", allocations: [], can_configure: false }],
      requires_allocation: false,
      not_applicable: true,
      wizard_complete: true,
    }
    if (path.includes("/investment-funds/options/")) return investmentFundScenario ? { plan_configuration_id: "config-1", not_applicable: false, quotation_currency: "TZS", funds: [{ id: "fund-1", code: "FUND-1", name: "Balanced Growth", fund_type_name: "Balanced", risk_profile: "Moderate", currency: "TZS", valuation_frequency: "DAILY", currency_compatible: true, currency_conversion_allowed: false, selectable: true }] } : { plan_configuration_id: "config-1", not_applicable: true, quotation_currency: "TZS", funds: [] }
    if (path.includes("/riders/options/")) return riderScenario ? { plan_configuration_id: "config-1", quotation_age: 36, quotation_currency: "TZS", riders: [{ id: "rider-1", code: "PA-01", name: "Personal Accident", rider_category: "ACCIDENT", benefit_type: "LUMP_SUM", calculation_basis: "FIXED", min_age: 18, max_age: 65, min_term: 1, max_term: 20, min_sum_assured: "1000", max_sum_assured: "1000000", waiting_period_days: 30, allows_standalone: true, requires_underwriting: false, product_id: "product-1", plan_id: "plan-1", selectable: true, synchronized_option: "PA" }], benefit_types: [{ value: benefitTypeUuid, label: "Death Benefit", meta: { code: "DEATH", name: "Death Benefit" } }] } : { plan_configuration_id: "config-1", quotation_age: 36, quotation_currency: "TZS", riders: [], benefit_types: [] }
    if (path.endsWith("/riders/") && !options?.method) return riderScenario ? { state: { plan_rows: [{ plan_configuration_id: "config-1", plan_code: "TERM-20", plan_name: "Twenty Year Term", personal_accident: true, premium_waiver: false, riders: [], benefits: [], can_configure: true }], available_benefit_types: [{ value: benefitTypeUuid, label: "Death Benefit", meta: { code: "DEATH", name: "Death Benefit" } }], requires_configuration: true, wizard_complete: false } } : { state: { plan_rows: [], available_benefit_types: [], requires_configuration: false, wizard_complete: true } }
    if (path.endsWith("/riders/") && options?.method === "POST") { latestRiderPayload = JSON.parse(String(options.body ?? "{}")) as Record<string, unknown>; return { quotation_id: "quote-1", state: { plan_rows: [{ plan_configuration_id: "config-1", plan_code: "TERM-20", plan_name: "Twenty Year Term", personal_accident: true, premium_waiver: false, riders: [{ rider_id: "rider-1", rider_code: "PA-01", rider_name: "Personal Accident", rider_sum_assured: "100000", rider_term_years: 20, waiting_period_days: 30, benefit_basis: "FIXED", benefit_value: "100000", benefits: [] }] }], available_benefit_types: [], requires_configuration: true, wizard_complete: true }, wizard_step_complete: true }
    }
    if (path.includes("/wizard-summary/")) return { steps: { "1_product_plan": true, "2_members": true, "3_installments": true, "4_funds": true, "5_riders": true, "6_payment": true, "7_underwriting": true } }
    if (path.includes("/payment-details/") && options?.method === "PATCH") return { ...quotation.payment_detail, ...JSON.parse(String(options.body ?? "{}")) }
    if (path.includes("/underwriting/") && options?.method === "PATCH") return { ...quotation.underwriting_detail, ...JSON.parse(String(options.body ?? "{}")) }
    if (path.includes("/financial-details/")) return financialScenario ? { quotation_id: "quote-1", recalculation_required: false, summary: { quotation_id: "quote-1", total_sum_assured: "100000", total_premium: "12000", total_rider_premium: "1500", total_benefit_premium: "0", base_premium: "10000", total_loading: "500", total_discount: "0", total_tax: "0", installment_charge: "0", estimated_maturity_value: "250000", currency: "TZS", calculated_at: "2026-08-19T10:00:00Z", projections: [{ policy_year: 1, premiums_paid: "12000", estimated_bonus: "500", surrender_value: "2000", paid_up_value: "4000", estimated_maturity_value: "250000" }], installment_payouts: [{ sequence: 1, payout_date: "2046-08-19", description: "Maturity payout", rate_percent: "100", payout_amount: "250000" }] } } : { quotation_id: "quote-1", recalculation_required: true, summary: null }
    if (path.endsWith("/calculate/") && options?.method === "POST") return { quotation_id: "quote-1", total_sum_assured: "100000", total_premium: riderScenario ? "13500" : "12000", total_rider_premium: riderScenario ? "3000" : "1500", total_benefit_premium: "0", base_premium: "10000", total_loading: "500", total_discount: "0", total_tax: "0", installment_charge: "0", estimated_maturity_value: "250000", currency: "TZS", calculated_at: "2026-08-19T10:00:00Z", recalculation_required: false, projections: [{ policy_year: 1, premiums_paid: "13500", estimated_bonus: "500", surrender_value: "2000", paid_up_value: "4000", estimated_maturity_value: "250000" }], installment_payouts: [{ sequence: 1, payout_date: "2046-08-19", description: "Maturity payout", rate_percent: "100", payout_amount: "250000" }] }
    if (path.endsWith("/revise/") && options?.method === "POST") { finalizedScenario = false; return { ...quotation, status: "DRAFT", wizard_step_completion: {} } }
    if (path.endsWith("/finalize/") && options?.method === "POST") { if (finalizeBlocked) throw new MockApiClientError("Complete all required steps before finalizing.", { riders: ["Riders & Benefits is incomplete."], financial_details: ["Calculate financial details before finalizing."] }); return { quotation: { ...quotation, status: "FINALIZED" }, status: "FINALIZED" } }
    if (path.includes("/personal-details/") && options?.method === "POST") return { ...quotation, quote_name: "Asha quote" }
    if (path.endsWith("/plans/") && options?.method === "POST") {
      if (planSelectionError) throw new MockApiClientError("Plan selection needs attention.", { term_years: ["Choose a policy term from 5 to 20 years for TERM-20 — Twenty Year Term. You entered 3 years. Enter a value within this range."] })
      return { quotation, configurations: [configuration], selected_plan_count: 1, wizard_step_complete: true }
    }
    if (path.includes("/plans/config-1/") && options?.method === "PATCH") throw new MockApiClientError("Term is outside the configured range.", { term_years: ["Policy term must be between 5 and 20 years."] })
    return {}
  })
})

function renderWizard() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={queryClient}><OLQuotationWizard /></QueryClientProvider>)
}

describe("OL quotation wizard", () => {
  it("shows finalized quotations as read-only and enables editing through Revise", async () => {
    finalizedScenario = true
    renderWizard()
    expect(await screen.findByText("This quotation is read-only. Create a revision to change any wizard step.")).toBeInTheDocument()
    const reviseButton = screen.getByRole("button", { name: "Revise to edit" })
    expect(reviseButton).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /Next/ })).toBeDisabled()

    fireEvent.click(reviseButton)
    const dialog = await screen.findByRole("dialog")
    fireEvent.click(within(dialog).getByRole("button", { name: "Revise and edit" }))

    await waitFor(() => expect(requestMock.mock.calls.some(([path, options]) => String(path).endsWith("/revise/") && options?.method === "POST")).toBe(true))
    await waitFor(() => expect(screen.queryByText("This quotation is read-only. Create a revision to change any wizard step.")).not.toBeInTheDocument())
    expect(screen.getByRole("button", { name: /Next/ })).not.toBeDisabled()
  })

  it("shows authorized Manage links for personal-detail foreign keys with draft context", async () => {
    window.history.replaceState({}, "", "/ordinary-life/quotations/new?step=personal")
    renderWizard()
    await screen.findByRole("button", { name: /^Identity Type/ })
    const manageLinks = screen.getAllByRole("link", { name: "Manage…" })
    const hrefs = manageLinks.map((link) => link.getAttribute("href") ?? "")
    expect(hrefs.some((href) => href.startsWith("/ordinary-life/parameters/dropdown-configuration?entity=identity-types"))).toBe(true)
    expect(hrefs.some((href) => href.startsWith("/system-parameters/partner/locations"))).toBe(true)
    expect(hrefs.some((href) => href.startsWith("/partners"))).toBe(true)
    hrefs.forEach((href) => {
      const target = new URL(href, window.location.origin)
      expect(target.searchParams.get("return_to")).toBe("/ordinary-life/quotations/new?step=personal")
      expect(target.searchParams.get("draft_id")).toBe("quote-1")
    })
  })

  it("blocks navigation when Personal Details is invalid", async () => {
    renderWizard()
    expect(await screen.findByRole("heading", { name: "Personal Details" })).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: /Next/ }))

    expect(await screen.findAllByText("This field is required.")).toHaveLength(9)
    expect(screen.getByRole("button", { name: "Personal Details" })).toHaveAttribute("aria-current", "step")
    expect(requestMock.mock.calls.some(([path]) => String(path).includes("/personal-details/"))).toBe(false)
  })

  it("computes age from Date of Birth and Quote Date", async () => {
    renderWizard()
    await screen.findByLabelText(/Date of Birth/)

    fireEvent.change(screen.getByLabelText(/Quote Date/), { target: { value: "2026-08-19" } })
    fireEvent.change(screen.getByLabelText(/Date of Birth/), { target: { value: "1990-08-20" } })

    expect(screen.getByText("35 years")).toBeInTheDocument()
  })

  it("selects only the clicked plan and updates the header count", async () => {
    renderWizard()
    const selectedCard = await screen.findByRole("button", { name: /TERM-20/ })
    const otherCard = await screen.findByRole("button", { name: /TERM-10/ })

    fireEvent.click(selectedCard)

    expect(screen.getByText("1 Plan", { selector: "span" })).toBeInTheDocument()
    expect(selectedCard).toHaveAttribute("aria-pressed", "true")
    expect(otherCard).toHaveAttribute("aria-pressed", "false")
  })

  it("renders the selected plan configuration immediately in Step 2", async () => {
    renderWizard()
    await screen.findByLabelText(/Quote Name/)
    fireEvent.change(screen.getByLabelText(/Quote Name/), { target: { value: "Asha quote" } })
    fireEvent.click(screen.getByRole("button", { name: /^Identity Type/ }))
    fireEvent.click(await screen.findByRole("option", { name: "National Identification Number" }))
    fireEvent.change(screen.getByLabelText(/Identity Number/), { target: { value: "NIN-001" } })
    fireEvent.change(screen.getByLabelText(/Gender/), { target: { value: "MALE" } })
    fireEvent.change(screen.getByLabelText(/Smoker/), { target: { value: "NON_SMOKER" } })
    fireEvent.change(screen.getByLabelText(/Address/), { target: { value: "Dar es Salaam" } })
    fireEvent.change(screen.getByLabelText(/Date of Birth/), { target: { value: "1990-01-01" } })
    fireEvent.click(screen.getByRole("button", { name: /^Location/ }))
    fireEvent.click(await screen.findByRole("option", { name: "Dar es Salaam" }))
    fireEvent.click(screen.getByRole("button", { name: /^Agent/ }))
    fireEvent.click(await screen.findByRole("option", { name: "Asha Agent" }))
    fireEvent.click(screen.getByRole("button", { name: /Next/ }))
    await waitFor(() => expect(screen.getByRole("button", { name: "Plan & Sub-Products" })).toHaveAttribute("aria-current", "step"))

    const personalCall = requestMock.mock.calls.find(([path, options]) => String(path).includes("/personal-details/") && options?.method === "POST")
    expect(personalCall).toBeTruthy()
    expect(JSON.parse(String(personalCall?.[1]?.body))).toEqual(expect.objectContaining({ identity_type: "NIN", location_id: "location-1", agent_id: "agent-1" }))

    fireEvent.click(await screen.findByRole("button", { name: /TERM-20/ }))

    expect(await screen.findByText("Section 1")).toBeInTheDocument()
    expect(screen.getAllByText("Twenty Year Term").length).toBeGreaterThanOrEqual(2)
    expect(screen.getByLabelText(/Policy Term/)).toBeInTheDocument()
  })

  it("shows plan constraints, includes Base Sum Assured, and submits complete defaults", async () => {
    renderWizard()
    await screen.findByLabelText(/Quote Name/)
    fireEvent.change(screen.getByLabelText(/Quote Name/), { target: { value: "Asha quote" } })
    fireEvent.click(screen.getByRole("button", { name: /^Identity Type/ }))
    fireEvent.click(await screen.findByRole("option", { name: "National Identification Number" }))
    fireEvent.change(screen.getByLabelText(/Identity Number/), { target: { value: "NIN-001" } })
    fireEvent.change(screen.getByLabelText(/Gender/), { target: { value: "MALE" } })
    fireEvent.change(screen.getByLabelText(/Smoker/), { target: { value: "NON_SMOKER" } })
    fireEvent.change(screen.getByLabelText(/Address/), { target: { value: "Dar es Salaam" } })
    fireEvent.change(screen.getByLabelText(/Date of Birth/), { target: { value: "1990-01-01" } })
    fireEvent.click(screen.getByRole("button", { name: /^Location/ }))
    fireEvent.click(await screen.findByRole("option", { name: "Dar es Salaam" }))
    fireEvent.click(screen.getByRole("button", { name: /^Agent/ }))
    fireEvent.click(await screen.findByRole("option", { name: "Asha Agent" }))
    fireEvent.click(screen.getByRole("button", { name: /Next/ }))
    await waitFor(() => expect(screen.getByRole("button", { name: "Plan & Sub-Products" })).toHaveAttribute("aria-current", "step"))
    fireEvent.click(await screen.findByRole("button", { name: /TERM-20/ }))

    expect(await screen.findByLabelText(/Base Sum Assured/)).toHaveValue(1000)
    expect(screen.getByText(/Policy term: 5–20 years/)).toBeInTheDocument()
    expect(screen.getByText(/Base sum assured: TZS 1,000\.00 to TZS 10,000,000\.00/)).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: /Next/ }))
    await waitFor(() => expect(screen.getByRole("button", { name: "Member Coverage" })).toHaveAttribute("aria-current", "step"))
    const planCall = requestMock.mock.calls.find(([path, options]) => String(path).endsWith("/plans/") && options?.method === "POST")
    expect(planCall).toBeTruthy()
    const submitted = JSON.parse(String(planCall?.[1]?.body)).plans[0]
    expect(submitted).toEqual(expect.objectContaining({ term_years: 5, payment_period_years: 5, premium_frequency: "ANNUALLY", quote_basis: "SUM_ASSURED", premium_factor: "NONE" }))
    expect(requestMock.mock.calls.some(([path]) => String(path).includes("/api/v1/ol/options/payment-frequencies/"))).toBe(false)
    expect(Number(submitted.base_sum_assured)).toBe(1000)
    expect(Number(submitted.estimated_maturity_value)).toBe(1000)
  })

  it("routes POST selection errors to the selected plan fields and complete banner", async () => {
    renderWizard()
    await screen.findByLabelText(/Quote Name/)
    fireEvent.change(screen.getByLabelText(/Quote Name/), { target: { value: "Asha quote" } })
    fireEvent.click(screen.getByRole("button", { name: /^Identity Type/ }))
    fireEvent.click(await screen.findByRole("option", { name: "National Identification Number" }))
    fireEvent.change(screen.getByLabelText(/Identity Number/), { target: { value: "NIN-001" } })
    fireEvent.change(screen.getByLabelText(/Gender/), { target: { value: "MALE" } })
    fireEvent.change(screen.getByLabelText(/Smoker/), { target: { value: "NON_SMOKER" } })
    fireEvent.change(screen.getByLabelText(/Address/), { target: { value: "Dar es Salaam" } })
    fireEvent.change(screen.getByLabelText(/Date of Birth/), { target: { value: "1990-01-01" } })
    fireEvent.click(screen.getByRole("button", { name: /^Location/ }))
    fireEvent.click(await screen.findByRole("option", { name: "Dar es Salaam" }))
    fireEvent.click(screen.getByRole("button", { name: /^Agent/ }))
    fireEvent.click(await screen.findByRole("option", { name: "Asha Agent" }))
    fireEvent.click(screen.getByRole("button", { name: /Next/ }))
    await waitFor(() => expect(screen.getByRole("button", { name: "Plan & Sub-Products" })).toHaveAttribute("aria-current", "step"))
    fireEvent.click(await screen.findByRole("button", { name: /TERM-20/ }))
    const term = await screen.findByLabelText(/Policy Term \(Years\)/)
    fireEvent.change(term, { target: { value: "3" } })
    planSelectionError = true
    fireEvent.click(screen.getByRole("button", { name: /Next/ }))

    expect((await screen.findAllByText(/Choose a policy term from 5 to 20 years/)).length).toBeGreaterThanOrEqual(2)
    expect(screen.getAllByRole("alert").some((alert) => /Policy term — Choose a policy term from 5 to 20 years/.test(alert.textContent ?? ""))).toBe(true)
    expect(screen.getAllByText(/You entered 3 years/).length).toBeGreaterThanOrEqual(2)
  })

  it("creates a product inline, refreshes plans, and auto-selects the new plan", async () => {
    renderWizard()
    await screen.findByRole("button", { name: /TERM-20/ })

    fireEvent.click(screen.getByRole("button", { name: "Add product" }))
    const dialog = await screen.findByRole("dialog")
    expect(within(dialog).getByRole("heading", { name: "Add Product" })).toBeInTheDocument()
    const quickCreateFields = await within(dialog).findAllByRole("textbox")
    fireEvent.change(quickCreateFields[0], { target: { value: "OLNEW" } })
    fireEvent.change(quickCreateFields[1], { target: { value: "New Product" } })
    fireEvent.click(within(dialog).getByRole("button", { name: "Create option" }))

    const newPlan = await screen.findByRole("button", { name: /OLNEW.*New Product/ })
    await waitFor(() => expect(newPlan).toHaveAttribute("aria-pressed", "true"))
    expect(screen.getByText("1 Plan", { selector: "span" })).toBeInTheDocument()
  })

  it("keeps fixed enum fields free of quick-create controls", async () => {
    renderWizard()
    await screen.findByLabelText(/Gender/)
    expect(screen.queryByRole("button", { name: "Add new Gender" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Add new Smoker" })).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Add new Identity Type" })).toBeInTheDocument()
  })

  async function reachMemberCoverageStep() {
    renderWizard()
    await screen.findByLabelText(/Quote Name/)
    fireEvent.change(screen.getByLabelText(/Quote Name/), { target: { value: "Asha quote" } })
    fireEvent.click(screen.getByRole("button", { name: /^Identity Type/ }))
    fireEvent.click(await screen.findByRole("option", { name: "National Identification Number" }))
    fireEvent.change(screen.getByLabelText(/Identity Number/), { target: { value: "NIN-001" } })
    fireEvent.change(screen.getByLabelText(/Gender/), { target: { value: "MALE" } })
    fireEvent.change(screen.getByLabelText(/Smoker/), { target: { value: "NON_SMOKER" } })
    fireEvent.change(screen.getByLabelText(/Address/), { target: { value: "Dar es Salaam" } })
    fireEvent.change(screen.getByLabelText(/Date of Birth/), { target: { value: "1990-01-01" } })
    fireEvent.click(screen.getByRole("button", { name: /^Location/ }))
    fireEvent.click(await screen.findByRole("option", { name: "Dar es Salaam" }))
    fireEvent.click(screen.getByRole("button", { name: /^Agent/ }))
    fireEvent.click(await screen.findByRole("option", { name: "Asha Agent" }))
    fireEvent.click(screen.getByRole("button", { name: /Next/ }))
    await waitFor(() => expect(screen.getByRole("button", { name: "Plan & Sub-Products" })).toHaveAttribute("aria-current", "step"))
    const planCard = await screen.findByRole("button", { name: /TERM-20/ })
    fireEvent.click(planCard)
    await waitFor(() => expect(screen.getByText("1 Plan", { selector: "span" })).toBeInTheDocument())
    fireEvent.click(screen.getByRole("button", { name: /Next/ }))
    await waitFor(() => expect(screen.getByRole("button", { name: "Member Coverage" })).toHaveAttribute("aria-current", "step"))
  }

  it("shows the no-additional-coverage banner and principal member card", async () => {
    await reachMemberCoverageStep()
    expect(await screen.findByText("Selected plans do not require additional member coverage configuration. Principal member is configured automatically.")).toBeInTheDocument()
    expect(screen.getByText("Principal Member (Policy Holder)")).toBeInTheDocument()
    expect(screen.getByText("Asha Applicant")).toBeInTheDocument()
  })

  it("quick-creates and auto-selects a member relation and cover type", async () => {
    memberCoverageScenario = true
    await reachMemberCoverageStep()
    expect(requestMock.mock.calls.map(([path]) => path)).toContain("/api/v1/ol-quotations/quotations/quote-1/members/")
    fireEvent.click(await screen.findByRole("button", { name: "Add member" }))
    const memberDialog = await screen.findByRole("dialog")
    expect(within(memberDialog).getByRole("button", { name: "Add new Member Relation" })).toBeInTheDocument()

    fireEvent.click(within(memberDialog).getByRole("button", { name: "Add new Member Relation" }))
    const relationDialog = (await screen.findAllByRole("dialog")).at(-1)
    expect(relationDialog).toBeTruthy()
    const relationFields = await within(relationDialog!).findAllByRole("textbox")
    fireEvent.change(relationFields[0], { target: { value: "SIBLING" } })
    fireEvent.change(relationFields[1], { target: { value: "Sibling" } })
    fireEvent.click(within(relationDialog!).getByRole("button", { name: "Create option" }))
    await waitFor(() => expect(requestMock.mock.calls.some(([path, options]) => String(path).includes("member-relations/quick-create/") && options?.method === "POST")).toBe(true))

    await waitFor(() => expect(document.getElementById("member_relation")).toHaveTextContent("Sibling"))
    expect(document.getElementById("member_cover_type")).toHaveTextContent("Dependent Cover")
  })

  it("quick-creates and auto-selects a payment mode inside Configure Installments", async () => {
    await reachMemberCoverageStep()
    fireEvent.click(screen.getByRole("button", { name: "Installments" }))
    fireEvent.click(await screen.findByRole("button", { name: "Configure" }))
    const dialog = await screen.findByRole("dialog")
    fireEvent.click(within(dialog).getByRole("button", { name: "Add new Payment Mode" }))
    const quickCreateDialog = (await screen.findAllByRole("dialog")).at(-1)
    expect(quickCreateDialog).toBeTruthy()
    const fields = await within(quickCreateDialog!).findAllByRole("textbox")
    fireEvent.change(fields[0], { target: { value: "MOBILE_MONEY" } })
    fireEvent.change(fields[1], { target: { value: "Mobile money" } })
    fireEvent.click(within(quickCreateDialog!).getByRole("button", { name: "Create option" }))
    await waitFor(() => expect(requestMock.mock.calls.some(([path, options]) => String(path).includes("payment-modes/quick-create/") && options?.method === "POST")).toBe(true))

    await waitFor(() => expect(document.getElementById("installment_payment_mode")).toHaveTextContent("Mobile money"))
  })

  it("quick-creates an investment fund with nested fund type and auto-selects it", async () => {
    investmentFundScenario = true
    await reachMemberCoverageStep()
    fireEvent.click(screen.getByRole("button", { name: "Investment Funds" }))
    expect(await screen.findByText("Investment-linked Plan")).toBeInTheDocument()
    const fundSelect = document.getElementById("fund_config-1_0")
    expect(fundSelect).toBeTruthy()
    fireEvent.click(fundSelect!)
    expect(await screen.findByRole("option", { name: /Balanced Growth/ })).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Add new investment fund" }))

    const fundDialog = (await screen.findAllByRole("dialog")).at(-1)
    expect(fundDialog).toBeTruthy()
    await waitFor(() => expect(requestMock.mock.calls.map(([path]) => path)).toContain("/api/v1/ol/options/investment-funds/quick-create-schema/"))
    fireEvent.click(await screen.findByRole("button", { name: "Add new Investment Fund Types" }))
    const typeDialog = (await screen.findAllByRole("dialog")).at(-1)
    expect(typeDialog).toBeTruthy()
    const typeFields = await within(typeDialog!).findAllByRole("textbox")
    fireEvent.change(typeFields[0], { target: { value: "BALANCED" } })
    fireEvent.change(typeFields[1], { target: { value: "Balanced" } })
    fireEvent.click(within(typeDialog!).getByRole("button", { name: "Create option" }))
    await waitFor(() => expect(screen.getAllByRole("dialog")).toHaveLength(1))

    const refreshedFundDialog = (await screen.findAllByRole("dialog")).at(-1)
    expect(refreshedFundDialog).toBeTruthy()
    const fundFields = await within(refreshedFundDialog!).findAllByRole("textbox")
    fireEvent.change(fundFields[0], { target: { value: "FUND-NEW" } })
    fireEvent.change(fundFields[1], { target: { value: "New Fund" } })
    fireEvent.click(within(refreshedFundDialog!).getByRole("button", { name: "Create option" }))

    await waitFor(() => expect(document.getElementById("fund_config-1_0")).toHaveTextContent("New Fund"))
  })

  it("opens Configure Installments with inherited computed fields and validates rate totals", async () => {
    await reachMemberCoverageStep()
    fireEvent.click(screen.getByRole("button", { name: "Installments" }))
    expect(await screen.findByRole("heading", { name: "Installments" })).toBeInTheDocument()
    fireEvent.click(await screen.findByRole("button", { name: "Configure" }))
    const dialog = await screen.findByRole("dialog")
    expect(within(dialog).getByText("No templates available. You can still configure installments manually.")).toBeInTheDocument()
    expect(within(dialog).getByText("20 years")).toBeInTheDocument()
    const rateInput = await within(dialog).findByLabelText("Installment 1 rate")
    expect(within(dialog).getByText("Total Number of Installments").parentElement?.parentElement).toHaveTextContent("1")
    fireEvent.change(rateInput, { target: { value: "60" } })
    fireEvent.click(within(dialog).getByRole("button", { name: "Save configuration" }))
    expect(await within(dialog).findByText("Installment rates must sum exactly to 100.")).toBeInTheDocument()
  })

  it("prefills installment rate rows from a backend template", async () => {
    templateRows = [{ sequence: 1, description: "Maturity Payout", rate_percent: "100.0000", paid_up_rate: "80.0000" }]
    await reachMemberCoverageStep()
    fireEvent.click(screen.getByRole("button", { name: "Installments" }))
    fireEvent.click(await screen.findByRole("button", { name: "Configure" }))
    const dialog = await screen.findByRole("dialog")
    expect(await within(dialog).findByLabelText("Installment 1 description")).toHaveValue("Maturity Payout")
    expect(within(dialog).getByLabelText("Installment 1 rate")).toHaveValue(100)
  })

  it("normalizes existing backend allocation rows before saving the required plan configuration", async () => {
    investmentFundScenario = true
    await reachMemberCoverageStep()
    fireEvent.click(screen.getByRole("button", { name: "Investment Funds" }))
    expect(await screen.findByText("Investment-linked Plan")).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText("Allocation percentage 1"), { target: { value: "100" } })
    fireEvent.click(screen.getByRole("button", { name: /Next/ }))

    await waitFor(() => expect(latestFundPayload).not.toBeNull())
    const submitted = (latestFundPayload?.allocations as Array<Record<string, unknown>>)[0]
    expect(submitted).toEqual(expect.objectContaining({
      plan_config_id: "config-1",
      fund_id: "fund-1",
      allocation_percent: "100",
    }))
    expect(submitted).not.toHaveProperty("plan_configuration_id")
  })

  it("shows the Investment Funds allocation error when a plan total is not 100%", async () => {
    investmentFundScenario = true
    await reachMemberCoverageStep()
    fireEvent.click(screen.getByRole("button", { name: "Investment Funds" }))
    expect(await screen.findByText("Investment-linked Plan")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: /Next/ }))
    expect(await screen.findByText("Each investment-linked plan must have fund allocations totaling exactly 100%."))
  })

  it("quick-creates and auto-selects a benefit type in the rider editor", async () => {
    riderScenario = true
    await reachMemberCoverageStep()
    fireEvent.click(screen.getByRole("button", { name: "Riders & Benefits" }))
    fireEvent.click(await screen.findByRole("button", { name: /PA-01/ }))
    const picker = document.getElementById("benefit_type_0")
    expect(picker).toBeTruthy()
    const benefitControl = picker!.parentElement?.parentElement
    expect(benefitControl).toBeTruthy()
    fireEvent.click(within(benefitControl!).getByRole("button", { name: "Add new Benefit Type" }))
    const dialog = (await screen.findAllByRole("dialog")).at(-1)
    expect(dialog).toBeTruthy()
    const fields = await within(dialog!).findAllByRole("textbox")
    fireEvent.change(fields[0], { target: { value: "ACCIDENTAL" } })
    fireEvent.change(fields[1], { target: { value: "Accidental Benefit" } })
    fireEvent.click(within(dialog!).getByRole("button", { name: "Create option" }))
    await waitFor(() => expect(requestMock.mock.calls.some(([path, options]) => String(path).includes("benefit-types/quick-create/") && options?.method === "POST")).toBe(true))
    await waitFor(() => expect(picker).toHaveTextContent("Accidental Benefit"))
  })

  it("quick-creates and auto-selects a rider in the rider editor", async () => {
    riderScenario = true
    await reachMemberCoverageStep()
    fireEvent.click(screen.getByRole("button", { name: "Riders & Benefits" }))
    expect(await screen.findByText("Applicable Riders")).toBeInTheDocument()
    const riderPicker = document.getElementById("rider_picker_config-1")
    expect(riderPicker).toBeTruthy()
    const riderControl = riderPicker!.parentElement?.parentElement
    expect(riderControl).toBeTruthy()
    fireEvent.click(within(riderControl!).getByRole("button", { name: "Add new rider" }))
    const dialog = (await screen.findAllByRole("dialog")).at(-1)
    expect(dialog).toBeTruthy()
    const fields = await within(dialog!).findAllByRole("textbox")
    fireEvent.change(fields[0], { target: { value: "TRAVEL-01" } })
    fireEvent.change(fields[1], { target: { value: "Travel Protection" } })
    fireEvent.change(fields[2], { target: { value: "TRAVEL" } })
    fireEvent.click(within(dialog!).getByRole("button", { name: "Create option" }))
    await waitFor(() => expect(requestMock.mock.calls.some(([path, options]) => String(path).includes("riders/quick-create/") && options?.method === "POST")).toBe(true))
    expect(await screen.findByText("Travel Protection")).toBeInTheDocument()
  })

  it("attaches a rider and displays the updated backend premium after recalculation", async () => {
    riderScenario = true
    financialScenario = true
    await reachMemberCoverageStep()
    fireEvent.click(screen.getByRole("button", { name: "Riders & Benefits" }))
    expect(await screen.findByText("Applicable Riders")).toBeInTheDocument()
    fireEvent.click(await screen.findByRole("button", { name: /PA-01/ }))
    fireEvent.change(screen.getByLabelText(/Rider Sum Assured \/ Amount/), { target: { value: "100000" } })
    const benefitPicker = document.getElementById("benefit_type_0")
    expect(benefitPicker).toBeTruthy()
    const benefitControl = benefitPicker!.parentElement?.parentElement
    expect(benefitControl).toBeTruthy()
    fireEvent.click(within(benefitControl!).getByRole("button", { name: /^Benefit Type/ }))
    fireEvent.click(await screen.findByRole("option", { name: "Death Benefit" }))
    fireEvent.click(screen.getByRole("button", { name: "Save rider configuration" }))
    await waitFor(() => expect(toastMock).toHaveBeenCalledWith(expect.objectContaining({ title: "Rider configuration saved" })))
    const savedSelection = (latestRiderPayload?.selections as Array<Record<string, unknown>> | undefined)?.[0]
    expect(savedSelection?.beneficial_type_id).toBe(benefitTypeUuid)
    expect((savedSelection?.benefits as Array<Record<string, unknown>> | undefined)?.[0]?.beneficial_type_id).toBe(benefitTypeUuid)
    fireEvent.click(screen.getByRole("button", { name: "Financial Details" }))
    expect((await screen.findAllByText("TZS 12,000.00")).length).toBeGreaterThan(0)
    fireEvent.click(screen.getByRole("button", { name: "Recalculate" }))
    await waitFor(() => expect(screen.getAllByText("TZS 13,500.00").length).toBeGreaterThan(0))
    expect(requestMock.mock.calls.some(([path, options]) => String(path).endsWith("/calculate/") && options?.method === "POST")).toBe(true)
  })

  it("renders backend financial projections and installment payout tables", async () => {
    financialScenario = true
    await reachMemberCoverageStep()
    fireEvent.click(screen.getByRole("button", { name: "Financial Details" }))
    expect(await screen.findByText("Policy-Year Projections")).toBeInTheDocument()
    expect(screen.getByText("Maturity payout")).toBeInTheDocument()
    expect(screen.getByText("Estimated Maturity Value")).toBeInTheDocument()
    expect(screen.getAllByText("TZS 250,000.00").length).toBeGreaterThan(0)
  })

  it("blocks finalize when steps are incomplete and exposes jump links", async () => {
    finalizeBlocked = true
    await reachMemberCoverageStep()
    fireEvent.click(screen.getByRole("button", { name: "Financial Details" }))
    expect(await screen.findByRole("heading", { name: "Review & Finalize" })).toBeInTheDocument()
    const finalizeButton = screen.getByRole("button", { name: "Finalize quotation" })
    expect(finalizeButton).toBeDisabled()
    fireEvent.click(screen.getByRole("button", { name: /Review & Finalize/ }))
    expect(await screen.findByText("Go to Financial Details")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Go to Financial Details" }))
    expect(screen.getAllByRole("button", { name: "Financial Details" }).some((button) => button.getAttribute("aria-current") === "step")).toBe(true)
  })

  it("saves payment details and underwriting answers from Financial Details", async () => {
    financialScenario = true
    await reachMemberCoverageStep()
    fireEvent.click(screen.getByRole("button", { name: "Financial Details" }))
    expect(await screen.findByRole("heading", { name: "Payment Details" })).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "Underwriting Answers" })).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText(/Underwriting Answers/), { target: { value: "health declaration: no known condition" } })
    fireEvent.click(screen.getByRole("button", { name: "Update payment details" }))
    await waitFor(() => expect(requestMock.mock.calls.some(([path, options]) => String(path).includes("payment-details/") && options?.method === "PATCH")).toBe(true))
    fireEvent.click(screen.getByRole("button", { name: "Update underwriting answers" }))
    await waitFor(() => expect(requestMock.mock.calls.some(([path, options]) => String(path).includes("underwriting/") && options?.method === "PATCH")).toBe(true))
    const underwritingRequest = requestMock.mock.calls.find(([path, options]) => String(path).includes("underwriting/") && options?.method === "PATCH")
    expect(String(underwritingRequest?.[1]?.body)).toContain('"health_answers":{"summary":"health declaration: no known condition"}')
    expect(String(underwritingRequest?.[1]?.body)).toContain('"declarations":{"confirmed":true}')
  })

  it("shows backend finalize errors with jump-to-step links", async () => {
    finalizeBlocked = true
    financialScenario = true
    await reachMemberCoverageStep()
    fireEvent.click(screen.getByRole("button", { name: "Financial Details" }))
    await screen.findByRole("heading", { name: "Review & Finalize" })
    fireEvent.click(screen.getByRole("button", { name: /Calculate|Recalculate/ }))
    await waitFor(() => expect(screen.getByRole("button", { name: "Finalize quotation" })).not.toBeDisabled())
    fireEvent.click(screen.getByRole("button", { name: "Finalize quotation" }))
    fireEvent.click(await screen.findByRole("button", { name: "Confirm finalize" }))
    expect(await screen.findByText("Riders & Benefits is incomplete.")).toBeInTheDocument()
    expect(screen.getAllByRole("button", { name: "Review" }).length).toBeGreaterThan(0)
  })

  it("clears a stale Riders & Benefits finalize warning after rider setup is saved", async () => {
    finalizeBlocked = true
    financialScenario = true
    riderScenario = true
    await reachMemberCoverageStep()
    fireEvent.click(screen.getByRole("button", { name: "Financial Details" }))
    await screen.findByRole("heading", { name: "Review & Finalize" })
    fireEvent.click(screen.getByRole("button", { name: /Calculate|Recalculate/ }))
    await waitFor(() => expect(screen.getByRole("button", { name: "Finalize quotation" })).not.toBeDisabled())
    fireEvent.click(screen.getByRole("button", { name: "Finalize quotation" }))
    fireEvent.click(await screen.findByRole("button", { name: "Confirm finalize" }))
    expect(await screen.findByText("Go to Riders & Benefits")).toBeInTheDocument()

    fireEvent.click(screen.getAllByRole("button", { name: "Riders & Benefits" })[0])
    expect(await screen.findByText("Applicable Riders")).toBeInTheDocument()
    fireEvent.click(await screen.findByRole("button", { name: /PA-01/ }))
    fireEvent.change(screen.getByLabelText(/Rider Sum Assured \/ Amount/), { target: { value: "100000" } })
    fireEvent.click(screen.getByRole("button", { name: "Save rider configuration" }))

    await waitFor(() => expect(toastMock).toHaveBeenCalledWith(expect.objectContaining({ title: "Rider configuration saved" })))
    await waitFor(() => expect(screen.queryByText("Go to Riders & Benefits")).not.toBeInTheDocument())
  })

  it("shows backend plan configuration errors inline", async () => {
    renderWizard()
    await screen.findByLabelText(/Quote Name/)

    fireEvent.change(screen.getByLabelText(/Quote Name/), { target: { value: "Asha quote" } })
    fireEvent.click(screen.getByRole("button", { name: /^Identity Type/ }))
    fireEvent.click(await screen.findByRole("option", { name: "National Identification Number" }))
    fireEvent.change(screen.getByLabelText(/Identity Number/), { target: { value: "NIN-001" } })
    fireEvent.change(screen.getByLabelText(/Gender/), { target: { value: "MALE" } })
    fireEvent.change(screen.getByLabelText(/Smoker/), { target: { value: "NON_SMOKER" } })
    fireEvent.change(screen.getByLabelText(/Address/), { target: { value: "Dar es Salaam" } })
    fireEvent.change(screen.getByLabelText(/Date of Birth/), { target: { value: "1990-01-01" } })

    fireEvent.click(screen.getByRole("button", { name: /^Location/ }))
    fireEvent.click(await screen.findByRole("option", { name: "Dar es Salaam" }))
    fireEvent.click(screen.getByRole("button", { name: /^Agent/ }))
    fireEvent.click(await screen.findByRole("option", { name: "Asha Agent" }))

    fireEvent.click(screen.getByRole("button", { name: /Next/ }))
    await waitFor(() => expect(screen.getByRole("button", { name: "Plan & Sub-Products" })).toHaveAttribute("aria-current", "step"))
    const planCard = await screen.findByRole("button", { name: /TERM-20/ })
    fireEvent.click(planCard)
    await waitFor(() => expect(screen.getByText("1 Plan", { selector: "span" })).toBeInTheDocument())
    fireEvent.click(screen.getByRole("button", { name: /Next/ }))
    await waitFor(() => expect(screen.getByRole("button", { name: "Member Coverage" })).toHaveAttribute("aria-current", "step"))
    fireEvent.click(screen.getByRole("button", { name: "Plan & Sub-Products" }))

    const term = await screen.findByLabelText(/Policy Term \(Years\)/)
    fireEvent.change(term, { target: { value: "3" } })

    await waitFor(() => expect(screen.getByText("Policy term must be between 5 and 20 years.")).toBeInTheDocument())
  })
})

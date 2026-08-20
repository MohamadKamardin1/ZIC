import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
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
    payment_frequencies: ["ANNUAL", "MONTHLY"],
    min_entry_age: 18,
    max_entry_age: 65,
    min_term_years: 5,
    max_term_years: 20,
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
    payment_frequencies: ["ANNUAL"],
    min_entry_age: 18,
    max_entry_age: 65,
    min_term_years: 5,
    max_term_years: 10,
  },
]

let templateRows: Array<{ sequence: number; description: string; rate_percent: string; paid_up_rate: string | null }> = []
let investmentFundScenario = false
let riderScenario = false
let financialScenario = false
let finalizeBlocked = false

const configuration = {
  id: "config-1",
  plan: "plan-1",
  product_version: "version-1",
  section_number: 1,
  term_years: 20,
  payment_period_years: 20,
  premium_frequency: "ANNUAL",
  quote_basis: "SUM_ASSURED",
  estimated_maturity_value: "100000.00",
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
  requestMock.mockReset()
  navigateMock.mockReset()
  toastMock.mockReset()
  templateRows = []
  investmentFundScenario = false
  riderScenario = false
  financialScenario = false
  finalizeBlocked = false
  requestMock.mockImplementation(async (path: string, options?: RequestInit) => {
    const draftResponse = financialScenario && finalizeBlocked ? { ...quotation, wizard_step_completion: { "1_personal_details": true, "2_plan_and_sub_products": true, "3_member_coverage": true, "4_installments": true, "5_investment_funds": true, "6_riders_and_benefits": true, "7_financial_details": true } } : quotation
    if (path === "/api/v1/ol-quotations/quotations/" && options?.method === "POST") return draftResponse
    if (path === "/api/v1/ol-quotations/quotations/quote-1/") return draftResponse
    if (path.includes("/personal-details-options/")) return {
      identity_types: [{ value: "NIN", label: "National Identification Number" }],
      genders: [{ value: "MALE", label: "Male" }],
      smoker_statuses: [{ value: "NON_SMOKER", label: "Non-smoker" }],
      locations: [{ value: "location-1", label: "Dar es Salaam" }],
      agents: [{ value: "agent-1", label: "Asha Agent" }],
    }
    if (path.startsWith("/api/v1/ol/plans/search/")) return { plans, count: plans.length }
    if (path.includes("/plan-options/")) return {
      payment_frequencies: [{ value: "ANNUAL", label: "Annual" }, { value: "MONTHLY", label: "Monthly" }],
      quote_bases: [{ value: "SUM_ASSURED", label: "Sum Assured" }],
      premium_factors: [{ value: "NONE", label: "None" }],
      plan_features: { joint_life: true, mortgage: false, personal_accident: false, premium_waiver: false },
    }
    if (path.endsWith("/members/")) return {
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
      payment_mode: "ANNUAL",
      available_payment_modes: ["ANNUAL", "MONTHLY"],
      rate_rows: templateRows,
    }
    if (path.endsWith("/investment-funds/") && !options?.method) return investmentFundScenario ? {
      plan_rows: [{ plan_configuration_id: "config-1", plan_code: "TERM-20", plan_name: "Investment-linked Plan", investment_linked: true, status: "READY_TO_CONFIGURE", allocation_total: "60.0000", allocations: [{ plan_config_id: "config-1", fund_id: "fund-1", allocation_percent: "60.0000", allocated_amount: null, fund_name: "Balanced Growth", fund_code: "FUND-1" }], can_configure: true }],
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
    if (path.includes("/riders/options/")) return riderScenario ? { plan_configuration_id: "config-1", quotation_age: 36, quotation_currency: "TZS", riders: [{ id: "rider-1", code: "PA-01", name: "Personal Accident", rider_category: "ACCIDENT", benefit_type: "LUMP_SUM", calculation_basis: "FIXED", min_age: 18, max_age: 65, min_term: 1, max_term: 20, min_sum_assured: "1000", max_sum_assured: "1000000", waiting_period_days: 30, allows_standalone: true, requires_underwriting: false, product_id: "product-1", plan_id: "plan-1", selectable: true, synchronized_option: "PA" }], benefit_types: [{ value: "DEATH", label: "Death Benefit" }] } : { plan_configuration_id: "config-1", quotation_age: 36, quotation_currency: "TZS", riders: [], benefit_types: [] }
    if (path.endsWith("/riders/") && !options?.method) return riderScenario ? { state: { plan_rows: [{ plan_configuration_id: "config-1", plan_code: "TERM-20", plan_name: "Twenty Year Term", personal_accident: true, premium_waiver: false, riders: [], benefits: [], can_configure: true }], available_benefit_types: [{ value: "DEATH", label: "Death Benefit" }], requires_configuration: true, wizard_complete: false } } : { state: { plan_rows: [], available_benefit_types: [], requires_configuration: false, wizard_complete: true } }
    if (path.endsWith("/riders/") && options?.method === "POST") return { quotation_id: "quote-1", state: { plan_rows: [{ plan_configuration_id: "config-1", plan_code: "TERM-20", plan_name: "Twenty Year Term", personal_accident: true, premium_waiver: false, riders: [{ rider_id: "rider-1", rider_code: "PA-01", rider_name: "Personal Accident", rider_sum_assured: "100000", rider_term_years: 20, waiting_period_days: 30, benefit_basis: "FIXED", benefit_value: "100000", benefits: [] }] }], available_benefit_types: [], requires_configuration: true, wizard_complete: true }, wizard_step_complete: true }
    if (path.includes("/financial-details/")) return financialScenario ? { quotation_id: "quote-1", recalculation_required: false, summary: { quotation_id: "quote-1", total_sum_assured: "100000", total_premium: "12000", total_rider_premium: "1500", total_benefit_premium: "0", base_premium: "10000", total_loading: "500", total_discount: "0", total_tax: "0", installment_charge: "0", estimated_maturity_value: "250000", currency: "TZS", calculated_at: "2026-08-19T10:00:00Z", projections: [{ policy_year: 1, premiums_paid: "12000", estimated_bonus: "500", surrender_value: "2000", paid_up_value: "4000", estimated_maturity_value: "250000" }], installment_payouts: [{ sequence: 1, payout_date: "2046-08-19", description: "Maturity payout", rate_percent: "100", payout_amount: "250000" }] } } : { quotation_id: "quote-1", recalculation_required: true, summary: null }
    if (path.endsWith("/calculate/") && options?.method === "POST") return { quotation_id: "quote-1", total_sum_assured: "100000", total_premium: riderScenario ? "13500" : "12000", total_rider_premium: riderScenario ? "3000" : "1500", total_benefit_premium: "0", base_premium: "10000", total_loading: "500", total_discount: "0", total_tax: "0", installment_charge: "0", estimated_maturity_value: "250000", currency: "TZS", calculated_at: "2026-08-19T10:00:00Z", recalculation_required: false, projections: [{ policy_year: 1, premiums_paid: "13500", estimated_bonus: "500", surrender_value: "2000", paid_up_value: "4000", estimated_maturity_value: "250000" }], installment_payouts: [{ sequence: 1, payout_date: "2046-08-19", description: "Maturity payout", rate_percent: "100", payout_amount: "250000" }] }
    if (path.endsWith("/finalize/") && options?.method === "POST") { if (finalizeBlocked) throw new MockApiClientError("Complete all required steps before finalizing.", { riders: ["Riders & Benefits is incomplete."], financial_details: ["Calculate financial details before finalizing."] }); return { quotation: { ...quotation, status: "FINALIZED" }, status: "FINALIZED" } }
    if (path.includes("/personal-details/") && options?.method === "POST") return { ...quotation, quote_name: "Asha quote" }
    if (path.endsWith("/plans/") && options?.method === "POST") return { quotation, configurations: [configuration], selected_plan_count: 1, wizard_step_complete: true }
    if (path.includes("/plans/config-1/") && options?.method === "PATCH") throw new MockApiClientError("Term is outside the configured range.", { term_years: ["Policy term must be between 5 and 20 years."] })
    return {}
  })
})

describe("OL quotation wizard", () => {
  it("blocks navigation when Personal Details is invalid", async () => {
    render(<OLQuotationWizard />)
    expect(await screen.findByRole("heading", { name: "Personal Details" })).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: /Next/ }))

    expect(await screen.findAllByText("This field is required.")).toHaveLength(9)
    expect(screen.getByRole("button", { name: "Personal Details" })).toHaveAttribute("aria-current", "step")
    expect(requestMock.mock.calls.some(([path]) => String(path).includes("/personal-details/"))).toBe(false)
  })

  it("computes age from Date of Birth and Quote Date", async () => {
    render(<OLQuotationWizard />)
    await screen.findByLabelText(/Date of Birth/)

    fireEvent.change(screen.getByLabelText(/Quote Date/), { target: { value: "2026-08-19" } })
    fireEvent.change(screen.getByLabelText(/Date of Birth/), { target: { value: "1990-08-20" } })

    expect(screen.getByText("35 years")).toBeInTheDocument()
  })

  it("selects only the clicked plan and updates the header count", async () => {
    render(<OLQuotationWizard />)
    const selectedCard = await screen.findByRole("button", { name: /TERM-20/ })
    const otherCard = await screen.findByRole("button", { name: /TERM-10/ })

    fireEvent.click(selectedCard)

    expect(screen.getByText("1 Plan", { selector: "span" })).toBeInTheDocument()
    expect(selectedCard).toHaveAttribute("aria-pressed", "true")
    expect(otherCard).toHaveAttribute("aria-pressed", "false")
  })

  it("renders the selected plan configuration immediately in Step 2", async () => {
    render(<OLQuotationWizard />)
    await screen.findByLabelText(/Quote Name/)
    fireEvent.change(screen.getByLabelText(/Quote Name/), { target: { value: "Asha quote" } })
    fireEvent.change(screen.getByLabelText(/Identity Type/), { target: { value: "NIN" } })
    fireEvent.change(screen.getByLabelText(/Identity Number/), { target: { value: "NIN-001" } })
    fireEvent.change(screen.getByLabelText(/Gender/), { target: { value: "MALE" } })
    fireEvent.change(screen.getByLabelText(/Smoker/), { target: { value: "NON_SMOKER" } })
    fireEvent.change(screen.getByLabelText(/Address/), { target: { value: "Dar es Salaam" } })
    fireEvent.change(screen.getByLabelText(/Date of Birth/), { target: { value: "1990-01-01" } })
    fireEvent.click(screen.getByRole("button", { name: /Location/ }))
    fireEvent.click(await screen.findByRole("option", { name: "Dar es Salaam" }))
    fireEvent.click(screen.getByRole("button", { name: /Agent/ }))
    fireEvent.click(await screen.findByRole("option", { name: "Asha Agent" }))
    fireEvent.click(screen.getByRole("button", { name: /Next/ }))
    await waitFor(() => expect(screen.getByRole("button", { name: "Plan & Sub-Products" })).toHaveAttribute("aria-current", "step"))

    fireEvent.click(await screen.findByRole("button", { name: /TERM-20/ }))

    expect(await screen.findByText("Section 1")).toBeInTheDocument()
    expect(screen.getAllByText("Twenty Year Term").length).toBeGreaterThanOrEqual(2)
    expect(screen.getByLabelText(/Policy Term/)).toBeInTheDocument()
  })

  async function reachMemberCoverageStep() {
    render(<OLQuotationWizard />)
    await screen.findByLabelText(/Quote Name/)
    fireEvent.change(screen.getByLabelText(/Quote Name/), { target: { value: "Asha quote" } })
    fireEvent.change(screen.getByLabelText(/Identity Type/), { target: { value: "NIN" } })
    fireEvent.change(screen.getByLabelText(/Identity Number/), { target: { value: "NIN-001" } })
    fireEvent.change(screen.getByLabelText(/Gender/), { target: { value: "MALE" } })
    fireEvent.change(screen.getByLabelText(/Smoker/), { target: { value: "NON_SMOKER" } })
    fireEvent.change(screen.getByLabelText(/Address/), { target: { value: "Dar es Salaam" } })
    fireEvent.change(screen.getByLabelText(/Date of Birth/), { target: { value: "1990-01-01" } })
    fireEvent.click(screen.getByRole("button", { name: /Location/ }))
    fireEvent.click(await screen.findByRole("option", { name: "Dar es Salaam" }))
    fireEvent.click(screen.getByRole("button", { name: /Agent/ }))
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

  it("shows the Investment Funds allocation error when a plan total is not 100%", async () => {
    investmentFundScenario = true
    await reachMemberCoverageStep()
    fireEvent.click(screen.getByRole("button", { name: "Investment Funds" }))
    expect(await screen.findByText("Investment-linked Plan")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: /Next/ }))
    expect(await screen.findByText("Each investment-linked plan must have fund allocations totaling exactly 100%."))
  })

  it("attaches a rider and displays the updated backend premium after recalculation", async () => {
    riderScenario = true
    financialScenario = true
    await reachMemberCoverageStep()
    fireEvent.click(screen.getByRole("button", { name: "Riders & Benefits" }))
    expect(await screen.findByText("Applicable Riders")).toBeInTheDocument()
    fireEvent.click(await screen.findByRole("button", { name: /PA-01/ }))
    fireEvent.change(screen.getByLabelText(/Rider Sum Assured \/ Amount/), { target: { value: "100000" } })
    fireEvent.click(screen.getByRole("button", { name: "Save rider configuration" }))
    await waitFor(() => expect(toastMock).toHaveBeenCalledWith(expect.objectContaining({ title: "Rider configuration saved" })))
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

  it("shows backend plan configuration errors inline", async () => {
    render(<OLQuotationWizard />)
    await screen.findByLabelText(/Quote Name/)

    fireEvent.change(screen.getByLabelText(/Quote Name/), { target: { value: "Asha quote" } })
    fireEvent.change(screen.getByLabelText(/Identity Type/), { target: { value: "NIN" } })
    fireEvent.change(screen.getByLabelText(/Identity Number/), { target: { value: "NIN-001" } })
    fireEvent.change(screen.getByLabelText(/Gender/), { target: { value: "MALE" } })
    fireEvent.change(screen.getByLabelText(/Smoker/), { target: { value: "NON_SMOKER" } })
    fireEvent.change(screen.getByLabelText(/Address/), { target: { value: "Dar es Salaam" } })
    fireEvent.change(screen.getByLabelText(/Date of Birth/), { target: { value: "1990-01-01" } })

    fireEvent.click(screen.getByRole("button", { name: /Location/ }))
    fireEvent.click(await screen.findByRole("option", { name: "Dar es Salaam" }))
    fireEvent.click(screen.getByRole("button", { name: /Agent/ }))
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

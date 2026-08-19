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
]

let templateRows: Array<{ sequence: number; description: string; rate_percent: string; paid_up_rate: string | null }> = []
let investmentFundScenario = false

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
  requestMock.mockImplementation(async (path: string, options?: RequestInit) => {
    if (path === "/api/v1/ol-quotations/quotations/" && options?.method === "POST") return quotation
    if (path === "/api/v1/ol-quotations/quotations/quote-1/") return quotation
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

  it("updates the header count when plans are multi-selected", async () => {
    render(<OLQuotationWizard />)
    const planCard = await screen.findByRole("button", { name: /TERM-20/ })

    fireEvent.click(planCard)

    expect(screen.getByText("1 Plan", { selector: "span" })).toBeInTheDocument()
    expect(planCard).toHaveAttribute("aria-pressed", "true")
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

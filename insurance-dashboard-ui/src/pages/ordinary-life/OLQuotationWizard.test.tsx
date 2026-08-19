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

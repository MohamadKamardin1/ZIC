import { beforeEach, describe, expect, it, vi } from "vitest"
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { request } from "../../lib/apiClient"
import { useAccess } from "../../lib/access"
import { useToast } from "../../components/ui/Toast"
import OLRiderSetup from "./OLRiderSetup"
import OLAgentManagement from "./OLAgentManagement"
import OLLoanSetup from "./OLLoanSetup"

vi.mock("../../lib/apiClient", async () => {
  const actual = await vi.importActual<typeof import("../../lib/apiClient")>("../../lib/apiClient")
  return { ...actual, request: vi.fn() }
})
vi.mock("../../lib/access", () => ({ useAccess: vi.fn() }))
vi.mock("../../components/ui/Toast", () => ({ useToast: vi.fn() }))

const requestMock = vi.mocked(request)
const accessMock = vi.mocked(useAccess)
const toastMock = vi.fn()
const permissions = [
  { module: "ol_parameters", action: "view" },
  { module: "ol_parameters", action: "create" },
  { module: "ol_parameters", action: "update" },
  { module: "ol_parameters", action: "deactivate" },
]

const choiceMap: Record<string, Array<{ value: string; display_name: string }>> = {
  rider_category: [{ value: "HEALTH", display_name: "Health" }],
  benefit_type: [{ value: "FIXED", display_name: "Fixed" }],
  calculation_basis: [{ value: "SUM_ASSURED", display_name: "Sum assured" }],
  rating_basis: [{ value: "PREMIUM", display_name: "Premium" }],
  gender: [{ value: "M", display_name: "Male" }],
  smoker_status: [{ value: "NON_SMOKER", display_name: "Non-smoker" }],
  frequency: [{ value: "ANNUAL", display_name: "Annual" }],
  rate_unit: [{ value: "PER_MILLE", display_name: "Per mille" }],
  intermediary_type: [{ value: "AGENT", display_name: "Agent" }],
  distribution_channel: [{ value: "DIRECT", display_name: "Direct" }],
  commission_type: [{ value: "NEW_BUSINESS", display_name: "New business" }],
  rate_type: [{ value: "PERCENTAGE", display_name: "Percentage" }],
  loan_basis: [{ value: "CASH_VALUE", display_name: "Cash value" }],
  effect_on_claim: [{ value: "DEDUCT", display_name: "Deduct" }],
  effect_on_surrender: [{ value: "DEDUCT", display_name: "Deduct" }],
  effect_on_maturity: [{ value: "DEDUCT", display_name: "Deduct" }],
  compounding_frequency: [{ value: "ANNUAL", display_name: "Annual" }],
  interest_calculation_basis: [{ value: "OUTSTANDING_BALANCE", display_name: "Outstanding balance" }],
}

const rider = { id: "rider-1", code: "PA", name: "Personal Accident", is_active: true, rider_category: "HEALTH", benefit_type: "FIXED", calculation_basis: "SUM_ASSURED", min_age: 18, max_age: 65, min_term: 1, max_term: 30, waiting_period_days: 30, allows_standalone: true, requires_underwriting: false, effective_from: "2026-01-01", effective_to: null }
const commission = { id: "commission-1", code: "COMM-1", name: "Agent commission", is_active: true, intermediary_type: "AGENT", distribution_channel: "DIRECT", commission_type: "NEW_BUSINESS", rate_type: "PERCENTAGE", rate_value: "5.0000", priority: 100, effective_from: "2026-01-01", effective_to: null }
const loanSystem = { id: "loan-1", code: "LOAN-1", name: "Cash value loans", is_active: true, loan_basis: "CASH_VALUE", max_loan_percentage_of_cash_value: "80.0000", min_loan_amount: "1000.00", max_loan_amount: "100000.00", allow_policy_loans: true, require_approval: false, effective_from: "2026-01-01", effective_to: null }
const loanInterest = { id: "interest-1", code: "INT-1", name: "Annual loan interest", is_active: true, interest_rate: "8.0000", compounding_frequency: "ANNUAL", interest_calculation_basis: "OUTSTANDING_BALANCE", grace_period_days: 30, penalty_interest_rate: "2.0000", capitalize_interest: true, effective_from: "2026-01-01", effective_to: null }

function accessValue() {
  return { access: { visibleModules: ["ol_parameters"], permissions, groups: [] }, isLoading: false, isError: false, canAccess: vi.fn(() => true) }
}

function optionsPayload() {
  return { actions: { POST: Object.fromEntries(Object.entries(choiceMap).map(([key, choices]) => [key, { choices }])) } }
}

function mockApi() {
  requestMock.mockImplementation(async (path, options) => {
    const url = String(path)
    if (options?.method === "OPTIONS") return optionsPayload() as never
    if (options?.method === "POST" && url.includes("agent-commission-setups")) throw new Error("Overlapping commission rule for this scope and effective period")
    if (options?.method === "POST" || options?.method === "PATCH") return {} as never
    if (url.includes("rider-rate-tables")) return { results: [{ id: "table-1", table_code: "PA-2026", name: "PA rates", rider: "rider-1", rating_basis: "PREMIUM", version: "1.0", is_active: true, effective_from: "2026-01-01" }], count: 1, page: 1, page_size: 20 } as never
    if (url.includes("rider-rate-rows")) return { results: [{ id: "row-1", code: "PA-ROW-1", name: "PA row", table: "table-1", gender: "M", smoker_status: "NON_SMOKER", age_from: 18, age_to: 65, term_from: 1, term_to: 30, frequency: "ANNUAL", rate: "1.20", rate_unit: "PER_MILLE", is_active: true, effective_from: "2026-01-01" }], count: 1, page: 1, page_size: 20 } as never
    if (url.includes("rider-setups")) return { results: [rider], count: 1, page: 1, page_size: 20 } as never
    if (url.includes("agent-commission-setups")) return { results: [commission], count: 1, page: 1, page_size: 20 } as never
    if (url.includes("loan-interest-controls")) return { results: [loanInterest], count: 1, page: 1, page_size: 20 } as never
    if (url.includes("loan-system-setups")) return { results: [loanSystem], count: 1, page: 1, page_size: 20 } as never
    return { results: [], count: 0, page: 1, page_size: 20 } as never
  })
}

describe("OL rider, agent, and loan setup", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    accessMock.mockReturnValue(accessValue())
    vi.mocked(useToast).mockReturnValue({ toast: toastMock, dismiss: vi.fn() })
    mockApi()
  })

  it("blocks an invalid rider save with required-field validation", async () => {
    render(<OLRiderSetup />)
    expect(await screen.findByRole("columnheader", { name: "Category" })).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "New setup" }))
    fireEvent.click(screen.getByRole("button", { name: "Save setup" }))
    expect(await screen.findByText("Category is required.")).toBeInTheDocument()
    expect(requestMock.mock.calls.some(([, options]) => options?.method === "POST" && String(options.body).includes('"code"'))).toBe(false)
  })

  it("shows the backend overlap warning in the commission modal", async () => {
    render(<OLAgentManagement />)
    expect(await screen.findByRole("columnheader", { name: "Commission type" })).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "New commission setup" }))
    const dialog = within(await screen.findByRole("dialog"))
    fireEvent.change(dialog.getByRole("textbox", { name: /Code/ }), { target: { value: "COMM-NEW" } })
    fireEvent.change(dialog.getByRole("textbox", { name: /Name/ }), { target: { value: "Overlapping commission" } })
    for (const [label, value] of [["Intermediary type", "AGENT"], ["Distribution channel", "DIRECT"], ["Commission type", "NEW_BUSINESS"], ["Rate type", "PERCENTAGE"]] as const) fireEvent.change(dialog.getByRole("combobox", { name: new RegExp(label) }), { target: { value } })
    fireEvent.change(dialog.getByRole("spinbutton", { name: /Rate value/ }), { target: { value: "5" } })
    fireEvent.click(dialog.getByRole("button", { name: "Save commission setup" }))
    expect(await screen.findByText(/Overlapping commission rule/)).toBeInTheDocument()
  })

  it("validates loan percentages and exposes the loan setup toggles", async () => {
    render(<OLLoanSetup />)
    expect(await screen.findByRole("columnheader", { name: "Loan basis" })).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "New setup" }))
    expect(screen.getByRole("switch", { name: "Allow policy loans" })).toBeInTheDocument()
    expect(screen.getByRole("switch", { name: "Require approval" })).toBeInTheDocument()
    fireEvent.change(screen.getByRole("spinbutton", { name: /Maximum % of cash value/ }), { target: { value: "120" } })
    fireEvent.click(screen.getByRole("button", { name: "Save setup" }))
    expect(await screen.findByText("Maximum loan percentage must be between 0 and 100.")).toBeInTheDocument()
    expect(requestMock.mock.calls.some(([, options]) => options?.method === "POST" && String(options.body).includes("120"))).toBe(false)
    fireEvent.click(screen.getByRole("switch", { name: "Require approval" }))
    expect(screen.getByRole("switch", { name: "Require approval" })).toHaveAttribute("aria-checked", "true")
  })
})

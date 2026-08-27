import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import type { PolicyListItem } from "../../lib/policies"

const { listPoliciesMock, createLoanRequestMock, usePolicyLoanEligibilityMock, useLoanOptionsMock } = vi.hoisted(() => ({
  listPoliciesMock: vi.fn(),
  createLoanRequestMock: vi.fn(),
  usePolicyLoanEligibilityMock: vi.fn(),
  useLoanOptionsMock: vi.fn(),
}))

vi.mock("../../lib/policies", async () => {
  const actual = await vi.importActual<typeof import("../../lib/policies")>("../../lib/policies")
  return { ...actual, listPolicies: listPoliciesMock }
})

vi.mock("../../lib/loans", async () => {
  const actual = await vi.importActual<typeof import("../../lib/loans")>("../../lib/loans")
  return { ...actual, createLoanRequest: createLoanRequestMock }
})

vi.mock("../../lib/loansHooks", async () => {
  const actual = await vi.importActual<typeof import("../../lib/loansHooks")>("../../lib/loansHooks")
  return { ...actual, usePolicyLoanEligibility: usePolicyLoanEligibilityMock, useLoanOptions: useLoanOptionsMock }
})

vi.mock("../../components/ui/Toast", () => ({ useToast: () => ({ toast: vi.fn() }) }))

vi.mock("../../lib/access", () => ({
  useAccess: () => ({ access: { permissions: [], visibleModules: [], groups: [] }, hasPermission: () => false, isSuperAdmin: false, canAccess: () => false, isLoading: false, isError: false }),
}))

import { LoanRequestModal } from "./OLLoans"

const activePolicy = { id: "policy-active-1", policyNumber: "ZIC-OL-2026-000001", policyholderDisplay: "P-000001 — Amani Salum", policyholderName: "Amani Salum", productPlanDisplay: "OL_EDU_GROWTH — Elimu Bora Growth Plan", currency: "TZS", status: "ACTIVE", statusDisplay: "Active" } as PolicyListItem
const lapsedPolicy = { ...activePolicy, id: "policy-lapsed-1", policyNumber: "ZIC-OL-2025-000099", status: "LAPSED", statusDisplay: "Lapsed" } as PolicyListItem
const eligible = { policyId: activePolicy.id, policyNumber: activePolicy.policyNumber, currency: "TZS", policyStatus: "ACTIVE", eligible: true, cashValue: "2500000.00", maxLoanPercentage: "50.00", availableLoanLimit: "1250000.00", minimumLoanAmount: "100000.00", maximumLoanAmount: "1250000.00", repaymentModes: ["MONTHLY", "DEDUCTION_FROM_MATURITY"], approvalRequired: true }
const lapsedEligibility = { ...eligible, policyId: lapsedPolicy.id, policyNumber: lapsedPolicy.policyNumber, policyStatus: "LAPSED", eligible: false, availableLoanLimit: "0.00", maximumLoanAmount: "0.00", errorCode: "LOAN_INELIGIBLE", message: "Policy is not eligible for loans.", resolutionSteps: ["Select an Active or Paid-up policy with loans enabled."] }

function renderModal(onCreated = vi.fn()) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return { onCreated, ...render(<QueryClientProvider client={client}><MemoryRouter><LoanRequestModal open onClose={vi.fn()} onCreated={onCreated} /></MemoryRouter></QueryClientProvider>) }
}

describe("OL Loans Prompt 6 request modal", () => {
  beforeEach(() => {
    listPoliciesMock.mockReset().mockResolvedValue({ results: [activePolicy], count: 1, next: null, previous: null })
    createLoanRequestMock.mockReset().mockResolvedValue({ loan: { id: "loan-requested-1" } })
    useLoanOptionsMock.mockReturnValue({ data: { results: [{ value: "MONTHLY", label: "Monthly repayment" }] }, isLoading: false, error: null })
    usePolicyLoanEligibilityMock.mockImplementation((policyId?: string) => ({ data: policyId === lapsedPolicy.id ? lapsedEligibility : policyId ? eligible : undefined, isLoading: false, error: null }))
  })

  it("forwards policy search and displays labeled eligible policies", async () => {
    const user = userEvent.setup()
    renderModal()
    expect(await screen.findByText(activePolicy.policyNumber)).toBeInTheDocument()
    const search = screen.getByPlaceholderText("Policy number, policyholder, or product")
    await user.clear(search)
    await user.type(search, "Amani")
    await waitFor(() => expect(listPoliciesMock.mock.calls.some(([params]) => params.search === "Amani")).toBe(true))
    expect(screen.getByText(/Amani Salum/)).toBeInTheDocument()
    expect(screen.queryByText(activePolicy.id)).not.toBeInTheDocument()
  })

  it("blocks an amount above the backend available limit with ErrorCoach guidance", async () => {
    const user = userEvent.setup()
    renderModal()
    await user.click(await screen.findByRole("button", { name: /ZIC-OL-2026-000001/ }))
    expect(await screen.findByText("Available Loan Limit")).toBeInTheDocument()
    await user.type(screen.getByPlaceholderText("Up to 1250000.00"), "1300000")
    await user.click(screen.getByRole("button", { name: "Next" }))
    expect(screen.getByRole("alert")).toHaveTextContent("Loan amount exceeds available cash value limit.")
    expect(screen.queryByRole("heading", { name: "Summary & Submit" })).not.toBeInTheDocument()
  })

  it("blocks lapsed policies with a teachable eligibility error", async () => {
    const user = userEvent.setup()
    listPoliciesMock.mockResolvedValue({ results: [lapsedPolicy], count: 1, next: null, previous: null })
    renderModal()
    await user.click(await screen.findByRole("button", { name: /ZIC-OL-2025-000099/ }))
    await user.type(screen.getByPlaceholderText("Up to 0.00"), "100000")
    await user.click(screen.getByRole("button", { name: "Next" }))
    expect(screen.getByRole("alert")).toHaveTextContent("Policy is not eligible for loans.")
  })

  it("completes the three-step flow and submits the canonical payload", async () => {
    const user = userEvent.setup()
    const onCreated = vi.fn()
    renderModal(onCreated)
    await user.click(await screen.findByRole("button", { name: /ZIC-OL-2026-000001/ }))
    await user.type(screen.getByPlaceholderText("Up to 1250000.00"), "500000")
    await user.type(screen.getByPlaceholderText("Explain why the policyholder is requesting this loan."), "Education expenses")
    await user.click(screen.getByRole("button", { name: "Next" }))
    expect(await screen.findByRole("heading", { name: "Summary & Submit" })).toBeInTheDocument()
    expect(screen.getByText(/Estimated Monthly Payment/)).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Submit Request" }))
    await waitFor(() => expect(createLoanRequestMock).toHaveBeenCalledWith(activePolicy.id, { requestedAmount: "500000", termMonths: 12, repaymentMode: "MONTHLY", reason: "Education expenses" }, expect.stringContaining(`ol-loan-request:${activePolicy.id}:`)))
    expect(onCreated).toHaveBeenCalledWith("loan-requested-1")
  })
})

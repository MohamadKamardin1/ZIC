import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import type { WithdrawalOption } from "../../lib/withdrawals"

const { useWithdrawalOptionsMock, useWithdrawalEligibilityMock, useEstimateWithdrawalMutationMock, useRequestWithdrawalMutationMock, toastMock } = vi.hoisted(() => ({
  useWithdrawalOptionsMock: vi.fn(),
  useWithdrawalEligibilityMock: vi.fn(),
  useEstimateWithdrawalMutationMock: vi.fn(),
  useRequestWithdrawalMutationMock: vi.fn(),
  toastMock: vi.fn(),
}))

const estimateMutationState = {
  data: { policyId: "policy-aman-1", currency: "TZS", requestedAmount: "500000.00", estimatedFee: "25000.00", estimatedNetPayout: "475000.00", feeRate: "5.0000", feeBasis: "5% fixed" },
  error: null,
  mutate: vi.fn(),
  reset: vi.fn(),
}

const requestMutationState = {
  isPending: false,
  mutateAsync: vi.fn().mockResolvedValue({ withdrawal: { id: "withdrawal-new-1" } }),
}

vi.mock("../../lib/withdrawalsHooks", () => ({
  useWithdrawalOptions: useWithdrawalOptionsMock,
  useWithdrawalEligibility: useWithdrawalEligibilityMock,
  useEstimateWithdrawalMutation: useEstimateWithdrawalMutationMock,
  useRequestWithdrawalMutation: useRequestWithdrawalMutationMock,
}))

vi.mock("../../components/ui/Toast", () => ({ useToast: () => ({ toast: toastMock }) }))

import OLWithdrawalRequest from "./OLWithdrawalRequest"

const policy: WithdrawalOption = {
  value: "policy-aman-1",
  label: "ZIC-OL-2026-000001 — Amani Salum",
  meta: { status: "ACTIVE", currency: "TZS", cash_value: "2500000.00", loan_balance: "150000.00" },
}

function renderWizard() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={["/ordinary-life/withdrawals/new?policy_id=policy-aman-1"]}><OLWithdrawalRequest /></MemoryRouter></QueryClientProvider>)
}

describe("OL Withdrawal request wizard", () => {
  beforeEach(() => {
    useWithdrawalOptionsMock.mockReset().mockReturnValue({ data: { results: [policy] }, isLoading: false, error: null })
    useWithdrawalEligibilityMock.mockReset().mockReturnValue({ data: { policyId: "policy-aman-1", policyNumber: "ZIC-OL-2026-000001", policyholderDisplay: policy.label, currency: "TZS", policyStatus: "ACTIVE", eligible: true, cashValue: "2500000.00", loanBalance: "150000.00", availableLimit: "2350000.00", feeRate: "5.0000", feeBasis: "5% fixed" }, isLoading: false, error: null })
    estimateMutationState.data = { policyId: "policy-aman-1", currency: "TZS", requestedAmount: "500000.00", estimatedFee: "25000.00", estimatedNetPayout: "475000.00", feeRate: "5.0000", feeBasis: "5% fixed" }
    estimateMutationState.error = null
    estimateMutationState.mutate.mockReset()
    estimateMutationState.reset.mockReset()
    useEstimateWithdrawalMutationMock.mockReset().mockReturnValue(estimateMutationState)
    requestMutationState.isPending = false
    requestMutationState.mutateAsync.mockReset().mockResolvedValue({ withdrawal: { id: "withdrawal-new-1" } })
    useRequestWithdrawalMutationMock.mockReset().mockReturnValue(requestMutationState)
    toastMock.mockReset()
  })

  it("filters the policy search through the backend options hook", async () => {
    const user = userEvent.setup()
    renderWizard()
    await screen.findByText("Available Limit")
    const search = screen.getByRole("textbox", { name: "Search active policies" })
    await user.type(search, "Amani")
    await waitFor(() => expect(useWithdrawalOptionsMock.mock.calls.some(([kind, params]) => kind === "policies" && params.q === "Amani")).toBe(true))
  })

  it("displays Available Limit and warns when an active loan reduces it", async () => {
    renderWizard()
    expect(await screen.findByText(/TZS\s+2,350,000\.00/)).toBeInTheDocument()
    expect(screen.getByText("Active loan reduces available withdrawal limit.")).toBeInTheDocument()
    expect(screen.getByText(/Cash Value.*less Loan Balance/)).toBeInTheDocument()
  })

  it("shows the backend fee estimate and net payout on Amount & Fees", async () => {
    const user = userEvent.setup()
    renderWizard()
    await screen.findByText("Available Limit")
    await user.click(screen.getByRole("button", { name: /Continue/ }))
    expect(await screen.findByRole("heading", { name: "Amount & Fees" })).toBeInTheDocument()
    expect(screen.getByText(/TZS\s+25,000\.00/)).toBeInTheDocument()
    expect(screen.getByText(/TZS\s+475,000\.00/)).toBeInTheDocument()
  })

  it("shows ErrorCoach when Requested Amount exceeds Available Limit", async () => {
    const user = userEvent.setup()
    renderWizard()
    await screen.findByText("Available Limit")
    await user.click(screen.getByRole("button", { name: /Continue/ }))
    const amount = screen.getByRole("textbox", { name: /Requested Amount/ })
    await user.type(amount, "3000000")
    await user.click(screen.getByRole("button", { name: /Continue/ }))
    expect(await screen.findByRole("alert")).toHaveTextContent("Amount exceeds available cash value limit.")
  })

  it("submits a complete request with the backend payload and success toast", async () => {
    const user = userEvent.setup()
    renderWizard()
    await screen.findByText("Available Limit")
    await user.click(screen.getByRole("button", { name: /Continue/ }))
    await user.type(screen.getByRole("textbox", { name: /Requested Amount/ }), "500000")
    await user.type(screen.getByRole("textbox", { name: /Reason/ }), "Education expenses")
    await user.click(screen.getByRole("button", { name: /Continue/ }))
    expect(await screen.findByRole("heading", { name: "Summary & Impact" })).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: /Submit Request/ }))
    await waitFor(() => expect(requestMutationState.mutateAsync).toHaveBeenCalledWith(expect.objectContaining({ policyId: "policy-aman-1", payload: { amount: "500000", reason: "Education expenses" } })))
    expect(toastMock).toHaveBeenCalledWith(expect.objectContaining({ title: "Withdrawal Request Submitted", message: "Status: Pending Approval." }))
  })
})

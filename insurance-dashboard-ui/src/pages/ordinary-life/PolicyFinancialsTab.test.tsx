import { fireEvent, render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import PolicyFinancialsTab from "./PolicyFinancialsTab"
import type { PolicyDetail } from "../../lib/policies"

const { loanMutationMock, withdrawalMutationMock, toastMock, setLoanOpenMock, setWithdrawalOpenMock } = vi.hoisted(() => ({
  loanMutationMock: vi.fn(),
  withdrawalMutationMock: vi.fn(),
  toastMock: vi.fn(),
  setLoanOpenMock: vi.fn(),
  setWithdrawalOpenMock: vi.fn(),
}))

vi.mock("react-router-dom", () => ({ useNavigate: () => vi.fn() }))
vi.mock("../../lib/policiesHooks", () => ({
  useRequestPolicyLoanMutation: loanMutationMock,
  useRequestPolicyWithdrawalMutation: withdrawalMutationMock,
}))
vi.mock("../../components/ui/Toast", () => ({ useToast: () => ({ toast: toastMock }) }))

const activePolicy = {
  id: "policy-1",
  policyNumber: "ZIC-OL-2026-000001",
  policyholderDisplay: "P-000018 — Amani Salum",
  policyholderName: "Amani Salum",
  productPlanDisplay: "OL_EDU_GROWTH — Elimu Bora Growth Plan",
  agentDisplay: "AG-0004 — Faraja Intermediaries",
  currency: "TZS",
  sumAssured: "25000000.00",
  premiumAmount: "120000.00",
  premiumFrequency: "MONTHLY",
  status: "ACTIVE",
  statusDisplay: "Active",
  allowedActions: ["loan", "withdraw"],
  contractSnapshot: { cash_value: "10000.00", max_loan_percentage_of_cash_value: "50", withdrawals_total: "1000.00", allow_withdrawals: true },
  members: [], riders: [], benefits: [], endorsements: [], auditLogs: [],
} as PolicyDetail

const baseProps = { loans: [{ id: "loan-1", loan_number: "LOAN-2026-000001", principal_amount: "2000.00", outstanding_principal: "1000.00", outstanding_interest: "100.00", interest_rate: "8.00", status: "DISBURSED" }], withdrawals: [{ id: "withdrawal-1", request_number: "WDR-2026-000001", request_date: "2026-07-01", amount: "500.00", net_amount: "490.00", status: "PAID" }], canRequestLoan: true, canRequestWithdrawal: true, loanModalOpen: false, withdrawalModalOpen: false, onLoanModalChange: setLoanOpenMock, onWithdrawalModalChange: setWithdrawalOpenMock }

beforeEach(() => {
  loanMutationMock.mockReturnValue({ mutate: vi.fn(), isPending: false, error: null })
  withdrawalMutationMock.mockReturnValue({ mutate: vi.fn(), isPending: false, error: null })
  toastMock.mockReset(); setLoanOpenMock.mockReset(); setWithdrawalOpenMock.mockReset()
})

describe("PolicyFinancialsTab", () => {
  it("renders loan history and validates a request against the configured available limit", () => {
    render(<PolicyFinancialsTab policy={activePolicy} {...baseProps} />)
    expect(screen.getByRole("heading", { name: "Policy loans" })).toBeInTheDocument()
    expect(screen.getByText("LOAN-2026-000001")).toBeInTheDocument()
    expect(screen.getByText(/Available limit:/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Request Loan" }))
    expect(setLoanOpenMock).toHaveBeenCalledWith(true)
  })

  it("shows withdrawal warning and blocks an amount above available cash value", () => {
    render(<PolicyFinancialsTab policy={activePolicy} {...baseProps} />)
    fireEvent.click(screen.getByRole("button", { name: "Withdrawals" }))
    expect(screen.getByRole("heading", { name: "Withdrawals" })).toBeInTheDocument()
    expect(screen.getByText("Withdrawals may reduce your Sum Assured.")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Request Withdrawal" }))
    expect(setWithdrawalOpenMock).toHaveBeenCalledWith(true)

    const { unmount } = render(<PolicyFinancialsTab policy={activePolicy} {...baseProps} withdrawalModalOpen />)
    fireEvent.change(screen.getByRole("spinbutton", { name: /Withdrawal amount/ }), { target: { value: "9000" } })
    fireEvent.click(screen.getByRole("button", { name: "Request withdrawal" }))
    expect(screen.getByText(/exceeds available cash value/)).toBeInTheDocument()
    unmount()
  })

  it("blocks a loan amount above the configured maximum loan limit", () => {
    render(<PolicyFinancialsTab policy={activePolicy} {...baseProps} loanModalOpen />)
    fireEvent.change(screen.getByRole("spinbutton", { name: /Loan amount/ }), { target: { value: "5000" } })
    fireEvent.click(screen.getByRole("button", { name: "Request loan" }))
    expect(screen.getByText(/exceeds the available loan limit/)).toBeInTheDocument()
  })

  it("blocks loan requests for a lapsed policy with ErrorCoach guidance", () => {
    render(<PolicyFinancialsTab policy={{ ...activePolicy, status: "LAPSED", statusDisplay: "Lapsed" }} {...baseProps} />)
    expect(screen.getByText("Loan request blocked")).toBeInTheDocument()
    expect(screen.getByText(/cannot request a loan until it is reinstated/)).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Request Loan" })).not.toBeInTheDocument()
  })
})

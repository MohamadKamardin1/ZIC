import { fireEvent, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { PartnerLoanDetail, PartnerLoans } from "./PartnerLoans"

const { navigateMock, useParamsMock, usePortalLoansMock, usePortalLoanMock, usePortalLoanRequestMutationMock, toastMock, mutateMock } = vi.hoisted(() => ({
  navigateMock: vi.fn(),
  useParamsMock: vi.fn(),
  usePortalLoansMock: vi.fn(),
  usePortalLoanMock: vi.fn(),
  usePortalLoanRequestMutationMock: vi.fn(),
  toastMock: vi.fn(),
  mutateMock: vi.fn(),
}))

vi.mock("react-router-dom", () => ({
  Link: ({ children, to, ...props }: { children: React.ReactNode; to: string; [key: string]: unknown }) => <a href={to} {...props}>{children}</a>,
  useNavigate: () => navigateMock,
  useParams: useParamsMock,
}))

vi.mock("../../lib/loanPortalHooks", () => ({
  usePortalLoans: usePortalLoansMock,
  usePortalLoan: usePortalLoanMock,
  usePortalLoanRequestMutation: usePortalLoanRequestMutationMock,
}))

vi.mock("../../components/ui/Toast", () => ({ useToast: () => ({ toast: toastMock }) }))

afterEach(() => vi.clearAllMocks())

const loan = {
  loanNumber: "LOAN-PORTAL-001",
  policyNumber: "POL-PORTAL-001",
  policyholder: "Asha Mussa",
  status: "Active",
  currency: "TZS",
  principalAmount: "1000000.00",
  disbursedAmount: "1000000.00",
  outstandingBalance: "650000.00",
  interestRate: "12.00",
  termMonths: 12,
  repaymentMode: "Monthly deduction",
  disbursementDate: "2026-01-15",
  maturityDate: "2027-01-15",
  product: "Elimu Bora Growth Plan",
  requestAllowed: true,
  totalRepaid: "350000.00",
  compoundingFrequency: "Monthly",
  schedule: [{ installmentNumber: 1, dueDate: "2026-02-15", principalDue: "80000.00", interestDue: "10000.00", penaltyDue: "0.00", amountPaid: "90000.00", balance: "650000.00", status: "Paid" }],
}

beforeEach(() => {
  usePortalLoansMock.mockReturnValue({ data: { count: 1, results: [loan] }, isLoading: false, isError: false })
  usePortalLoanMock.mockReturnValue({ data: loan, isLoading: false, isError: false })
  useParamsMock.mockReturnValue({ loanNumber: loan.loanNumber })
  usePortalLoanRequestMutationMock.mockReturnValue({ mutate: mutateMock, isPending: false, error: null })
})

describe("Partner portal loans", () => {
  it("renders partner-scoped loan data and exposes only View plus eligible Request Loan", () => {
    render(<PartnerLoans />)
    expect(screen.getByRole("heading", { name: "My Loans" })).toBeInTheDocument()
    expect(screen.getByText("For changes to loan terms, contact ZIC Finance.")).toBeInTheDocument()
    expect(screen.getByText("LOAN-PORTAL-001")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "View" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Request Loan" })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /Disburse|Repay|Offset|Reverse/ })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "View" }))
    expect(navigateMock).toHaveBeenCalledWith("/portal/loans/LOAN-PORTAL-001")
  })

  it("submits a partner request with human-readable policy context", async () => {
    const user = userEvent.setup()
    mutateMock.mockImplementation((_variables: unknown, options: { onSuccess: () => void }) => options.onSuccess())
    render(<PartnerLoans />)
    await user.click(screen.getByRole("button", { name: "Request Loan" }))
    fireEvent.change(screen.getByPlaceholderText("Enter amount"), { target: { value: "250000" } })
    fireEvent.change(screen.getByPlaceholderText("Configured mode"), { target: { value: "Monthly deduction" } })
    fireEvent.change(screen.getByPlaceholderText("Explain the request"), { target: { value: "Education expenses" } })
    await user.click(screen.getByRole("button", { name: "Submit Request" }))
    expect(mutateMock).toHaveBeenCalledWith({ payload: { policyNumber: "POL-PORTAL-001", requestedAmount: "250000.00", termMonths: 12, repaymentMode: "Monthly deduction", reason: "Education expenses" }, idempotencyKey: expect.stringContaining("portal-loan-request-POL-PORTAL-001") }, expect.any(Object))
    expect(toastMock).toHaveBeenCalledWith(expect.objectContaining({ title: "Loan request submitted" }))
    expect(screen.queryByRole("heading", { name: "Request Loan" })).not.toBeInTheDocument()
  })

  it("renders read-only detail, repayment schedule, and restriction messaging", () => {
    render(<PartnerLoanDetail />)
    expect(screen.getByTestId("portal-loan-overview")).toHaveTextContent("Asha Mussa")
    expect(screen.getByTestId("portal-loan-schedule")).toHaveTextContent("2026")
    expect(screen.getByTestId("portal-loan-schedule")).toHaveTextContent("Paid")
    expect(screen.getByText(/Disburse, repay, offset, reverse/)).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /Disburse|Repay|Offset|Reverse/ })).not.toBeInTheDocument()
  })
})

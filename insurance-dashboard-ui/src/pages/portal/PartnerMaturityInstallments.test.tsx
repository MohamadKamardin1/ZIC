import { fireEvent, render, screen, within } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { PartnerMaturityInstallmentDetail, PartnerMaturityInstallments } from "./PartnerMaturityInstallments"

const { navigateMock, useParamsMock, useMIPortalPlanListMock, useMIPortalPlanDetailMock } = vi.hoisted(() => ({
  navigateMock: vi.fn(),
  useParamsMock: vi.fn(),
  useMIPortalPlanListMock: vi.fn(),
  useMIPortalPlanDetailMock: vi.fn(),
}))

vi.mock("react-router-dom", () => ({
  Link: ({ children, to, ...props }: { children: React.ReactNode; to: string; [key: string]: unknown }) => <a href={to} {...props}>{children}</a>,
  useNavigate: () => navigateMock,
  useParams: useParamsMock,
}))

vi.mock("../../lib/maturityInstallmentsHooks", () => ({
  useMIPortalPlanList: useMIPortalPlanListMock,
  useMIPortalPlanDetail: useMIPortalPlanDetailMock,
}))

afterEach(() => vi.clearAllMocks())

const portalPlanA = {
  id: "0f5c3a18-2b6d-4e7a-9c21-a11f4b3d2e05",
  planNumber: "MI-PORTAL-001",
  policyNumber: "POL-PORTAL-001",
  status: "ACTIVE",
  statusDisplay: "Active",
  currency: "TZS",
  frequency: "MONTHLY",
  installmentCount: 12,
  paidInstallments: 4,
  totalAmount: "12000000.00",
  paidAmount: "4000000.00",
  startDate: "2026-01-01",
  endDate: "2026-12-31",
  items: [
    { id: "b7e2f1a4-9c30-4d8e-aa12-7f3c9d1e2b40", installmentNumber: 1, dueDate: "2026-02-01", amount: "1000000.00", status: "PAID", statusDisplay: "Paid" },
    { id: "c8f3a2b5-1d40-4e9f-bb23-8g4d0e2f3c51", installmentNumber: 2, dueDate: "2026-03-01", amount: "1000000.00", status: "PAID", statusDisplay: "Paid" },
    { id: "d9g4b3c6-2e51-4f0a-cc34-9h5e1f3g4d62", installmentNumber: 3, dueDate: "2026-04-01", amount: "1000000.00", status: "SCHEDULED", statusDisplay: "Scheduled" },
  ],
}

const portalPlanB = {
  id: "e0h5c4d7-3f62-4a1b-dd45-0i6f2g4h5e73",
  planNumber: "MI-PORTAL-002",
  policyNumber: "POL-PORTAL-002",
  status: "COMPLETED",
  statusDisplay: "Completed",
  currency: "TZS",
  frequency: "SINGLE",
  installmentCount: 1,
  paidInstallments: 1,
  totalAmount: "5000000.00",
  paidAmount: "5000000.00",
  startDate: "2025-06-01",
  endDate: "2025-06-01",
  items: [
    { id: "f1i6d5e8-4g73-4b1c-ee56-1j7g3h5i6f84", installmentNumber: 1, dueDate: "2025-06-01", amount: "5000000.00", status: "PAID", statusDisplay: "Paid" },
  ],
}

beforeEach(() => {
  useMIPortalPlanListMock.mockReturnValue({ data: [portalPlanA, portalPlanB], isLoading: false, isError: false, error: null })
  useMIPortalPlanDetailMock.mockReturnValue({ data: portalPlanA, isLoading: false, isError: false, error: null })
  useParamsMock.mockReturnValue({ planId: portalPlanA.planNumber })
})

describe("Partner portal maturity installments", () => {
  it("shows the partner only their own linked policy plans", () => {
    render(<PartnerMaturityInstallments />)
    expect(screen.getByRole("heading", { name: "My Installments" })).toBeInTheDocument()
    expect(screen.getByText("Payout schedule")).toBeInTheDocument()
    expect(screen.getByText("Payments are processed by ZIC Finance.")).toBeInTheDocument()
    expect(screen.getByText("MI-PORTAL-001")).toBeInTheDocument()
    expect(screen.getByText("MI-PORTAL-002")).toBeInTheDocument()
    expect(screen.getByText("POL-PORTAL-001")).toBeInTheDocument()
    expect(screen.getAllByRole("button", { name: "View" })).toHaveLength(2)
    expect(screen.queryByText("MI-PORTAL-099")).not.toBeInTheDocument()
  })

  it("hides restricted actions and exposes View instead of Manage", () => {
    render(<PartnerMaturityInstallments />)
    const table = screen.getByTestId("portal-mi-table")
    expect(within(table).getAllByRole("button", { name: "View" })).toHaveLength(2)
    expect(within(table).queryByRole("button", { name: /Manage|Process Payment|Reverse|Cancel|Print/ })).not.toBeInTheDocument()
    expect(screen.queryByText("Process Payment")).not.toBeInTheDocument()
    expect(screen.queryByText("Reverse")).not.toBeInTheDocument()
  })

  it("sanitizes internal audit data and never leaks internal ids", () => {
    render(<PartnerMaturityInstallments />)
    render(<PartnerMaturityInstallmentDetail />)
    expect(screen.queryByText(/Audit trail/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Bank accounts/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Parameter snapshot/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Status history/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Requisition/i)).not.toBeInTheDocument()
    expect(screen.queryByText(portalPlanA.id)).not.toBeInTheDocument()
    expect(screen.queryByText(portalPlanA.items[0].id)).not.toBeInTheDocument()
  })

  it("is strictly read-only: View navigates to the schedule detail with no actions", () => {
    render(<PartnerMaturityInstallments />)
    fireEvent.click(within(screen.getByTestId("portal-mi-row-MI-PORTAL-001")).getByRole("button", { name: "View" }))
    expect(navigateMock).toHaveBeenCalledWith("/portal/maturity-installments/MI-PORTAL-001")

    render(<PartnerMaturityInstallmentDetail />)
    expect(screen.getByTestId("portal-mi-detail")).toBeInTheDocument()
    expect(within(screen.getByTestId("portal-mi-detail")).getByText("MI-PORTAL-001")).toBeInTheDocument()
    expect(screen.getByText("Read-only partner view")).toBeInTheDocument()
    const schedule = screen.getByTestId("portal-mi-schedule")
    expect(within(schedule).getByText("1")).toBeInTheDocument()
    expect(within(schedule).getByText("3")).toBeInTheDocument()
    expect(within(schedule).getAllByText("Paid")).toHaveLength(2)
    expect(within(schedule).getByText("Scheduled")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /Process Payment|Reverse|Manage|Cancel|Print|Terminate/ })).not.toBeInTheDocument()
    expect(screen.getByText(/Process payment, reverse, and other servicing actions are not available here/)).toBeInTheDocument()
  })
})

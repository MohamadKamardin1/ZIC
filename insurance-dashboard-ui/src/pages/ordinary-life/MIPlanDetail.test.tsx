import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter, Route, Routes, useParams } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import type { MIPlanDetail as MIPlanDetailType } from "../../lib/maturityInstallments"

const { useMIPlanDetailMock, processMIPaymentMock, cancelMIPlanMock, printMIScheduleMock, printMIAdviceMock, toastMock } = vi.hoisted(() => ({
  useMIPlanDetailMock: vi.fn(),
  processMIPaymentMock: vi.fn(),
  cancelMIPlanMock: vi.fn(),
  printMIScheduleMock: vi.fn(),
  printMIAdviceMock: vi.fn(),
  toastMock: vi.fn(),
}))

vi.mock("../../lib/maturityInstallmentsHooks", async () => {
  const actual = await vi.importActual<typeof import("../../lib/maturityInstallmentsHooks")>("../../lib/maturityInstallmentsHooks")
  return { ...actual, useMIPlanDetail: useMIPlanDetailMock }
})

vi.mock("../../lib/maturityInstallments", async () => {
  const actual = await vi.importActual<typeof import("../../lib/maturityInstallments")>("../../lib/maturityInstallments")
  return { ...actual, processMIPayment: processMIPaymentMock, cancelMIPlan: cancelMIPlanMock, printMISchedule: printMIScheduleMock, printMIAdvice: printMIAdviceMock }
})

vi.mock("../../components/ui/Toast", () => ({ useToast: () => ({ toast: toastMock }) }))

let mockPermissions: string[]

vi.mock("../../lib/access", () => ({
  useAccess: () => ({
    access: {
      permissions: mockPermissions.map((code) => { const [module, action] = code.split("."); return { module, action } }),
      visibleModules: ["ol_maturity_installments"],
      groups: [],
    },
    hasPermission: (permission: string) => mockPermissions.includes(permission),
    isSuperAdmin: false,
    canAccess: () => true,
    isLoading: false,
    isError: false,
  }),
}))

import MIPlanDetail from "./MIPlanDetail"

const baseDetail = (overrides: Partial<MIPlanDetailType> = {}): MIPlanDetailType => ({
  id: "plan-active-1",
  planNumber: "MIP-20260901-9DD41C66AF",
  policyId: "policy-aman-1",
  policyNumber: "ZIC-OL-2026-000001",
  policyholderName: "Amani Salum",
  policyholderDisplay: "P-000001 — Amani Salum",
  claimNumber: null,
  currency: "TZS",
  frequency: "ANNUAL",
  status: "ACTIVE",
  statusDisplay: "Active",
  totalAmount: "62500000.00",
  paidAmount: "15625000.00",
  balance: "46875000.00",
  maturityValue: "62500000.00",
  installmentCount: 4,
  startDate: "2026-03-01",
  endDate: "2029-03-01",
  productCode: "OL_ENDOWMENT_STANDARD",
  productDisplay: "OL Endowment Standard",
  completedAt: null,
  terminationReason: null,
  terminatedAt: null,
  allowedActions: ["view", "create", "process_payment", "cancel", "print"],
  createdAt: "2026-09-01T08:00:00Z",
  updatedAt: "2026-09-01T08:00:00Z",
  maturityClaimId: null,
  totalPayableAmount: "62500000.00",
  totalPaidAmount: "15625000.00",
  sourceChannel: "API",
  sourceChannelDisplay: "Maturity Installments Console",
  calculationSource: "RATE_TABLE",
  calculationSourceDisplay: "Rate Table",
  parameterSnapshot: {},
  items: [
    { id: "plan-active-1-item-1", planId: "plan-active-1", installmentNumber: 1, dueDate: "2026-03-01", amount: "15625000.00", status: "PAID", statusDisplay: "Paid", requisitionNumber: "FO-MIP-2026-000001", paidDate: "2026-03-01", paidByDisplay: "Finance Officer — Rehema S.", payerDisplay: "Amani Salum", paymentReference: "FO-PAY-2026-000101", narration: "" },
    { id: "plan-active-1-item-2", planId: "plan-active-1", installmentNumber: 2, dueDate: "2026-08-01", amount: "15625000.00", status: "MISSED", statusDisplay: "Missed", requisitionNumber: null, paidDate: null, paidByDisplay: null, payerDisplay: null, paymentReference: null, narration: "" },
    { id: "plan-active-1-item-3", planId: "plan-active-1", installmentNumber: 3, dueDate: "2028-03-01", amount: "15625000.00", status: "SCHEDULED", statusDisplay: "Scheduled", requisitionNumber: null, paidDate: null, paidByDisplay: null, payerDisplay: null, paymentReference: null, narration: "" },
  ],
  paymentHistory: [
    { installmentNumber: 1, dueDate: "2026-03-01", amount: "15625000.00", status: "PAID", paidDate: "2026-03-01", requisitionNumber: "FO-MIP-2026-000001", paymentReference: "FO-PAY-2026-000101", payerDisplay: "Amani Salum" },
  ],
  reconciliation: { status: "FAIL", maturityValue: "62500000.00", totalPayableAmount: "62500000.00", paidAmount: "15625000.00", missingAmount: "46875000.00", paidItems: 1, totalItems: 3, discrepancies: [{ code: "MISSING_PAYMENTS", message: "Paid 15625000.00 is below the total payable 62500000.00." }] },
  statusHistory: [
    { status: "CREATED", statusDisplay: "Created", timestamp: "2026-09-01T08:00:00Z", note: "Plan created against the policy maturity value." },
    { status: "ACTIVE", statusDisplay: "Active", timestamp: "2026-09-01T08:00:00Z", note: "Activated on the first confirmed payment." },
  ],
  auditHistory: [
    { id: "plan-active-1-audit-created", action: "INSTALLMENT_PLAN_CREATED", actionDisplay: "Plan created", actorDisplay: "Sultan Admin", timestamp: "2026-09-01T08:00:00Z", channel: "API", details: "Plan created." },
  ],
  documents: [
    { id: "doc-plan-active-1-schedule", documentType: "OL_MATURITY_SCHEDULE", templateName: "OL Maturity Schedule", templateVersion: 1, pageCount: 2, generatedByDisplay: "Sultan Admin", generatedAt: "2026-09-01T08:00:00Z", previewUrl: "/api/v1/documents/instances/doc-plan-active-1-schedule/preview/", signedDownloadUrl: "/api/v1/documents/instances/doc-plan-active-1-schedule/download/?ticket=mock-schedule-plan-active-1" },
  ],
  ...overrides,
})

function renderDetail(detail = baseDetail(), withPolicyRoute = false) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const PolicyMarker = () => { const params = useParams<{ policyId: string }>(); return <div data-testid="policy-marker">{params.policyId}</div> }
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/ordinary-life/maturity-installments/plan-active-1"]}>
        <Routes>
          <Route path="ordinary-life/maturity-installments/:planId" element={<MIPlanDetail />} />
          {withPolicyRoute && <Route path="ordinary-life/policies/:policyId" element={<PolicyMarker />} />}
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe("OL Maturity Installments detail (Prompt 3 master-detail)", () => {
  beforeEach(() => {
    mockPermissions = ["ol_maturity_installments.view", "ol_maturity_installments.process_payment", "ol_maturity_installments.print", "ol_maturity_installments.cancel"]
    useMIPlanDetailMock.mockReset()
    processMIPaymentMock.mockReset()
    cancelMIPlanMock.mockReset()
    printMIScheduleMock.mockReset()
    printMIAdviceMock.mockReset()
    toastMock.mockReset()
    vi.spyOn(window, "open").mockImplementation(() => null)
  })

  it("renders the header financial fields, product policy link, and dates without leaking record ids", async () => {
    useMIPlanDetailMock.mockReturnValue({ data: baseDetail(), isLoading: false, error: null })
    renderDetail()
    expect(await screen.findByText("MIP-20260901-9DD41C66AF")).toBeInTheDocument()
    expect(screen.getAllByText("ZIC-OL-2026-000001").length).toBeGreaterThan(0)
    expect(screen.getAllByText("OL Endowment Standard").length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Amani Salum/).length).toBeGreaterThan(0)
    expect(screen.getAllByText("Active").length).toBeGreaterThan(0)
    expect(screen.getByText("Total maturity value")).toBeInTheDocument()
    expect(screen.getByText("Amount paid")).toBeInTheDocument()
    expect(screen.getByText("Balance remaining")).toBeInTheDocument()
    expect(screen.getAllByText(/62,500,000\.00/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/15,625,000\.00/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/46,875,000\.00/).length).toBeGreaterThan(0)
    expect(screen.getByText(/Start 1 Mar 2026/)).toBeInTheDocument()
    expect(screen.getByText(/End 1 Mar 2029/)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Process Payment" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Print schedule" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Cancel plan" })).toBeInTheDocument()
    expect(screen.queryByText("plan-active-1")).not.toBeInTheDocument()
    expect(screen.queryByText("plan-active-1-item-1")).not.toBeInTheDocument()
  })

  it("hides Process Payment and Cancel for completed plans, keeping print only", async () => {
    const completed = baseDetail({ id: "plan-completed-1", planNumber: "MIP-20260815-9E1168C4EF", status: "COMPLETED", statusDisplay: "Completed", allowedActions: ["view", "print"], completedAt: "2026-08-15T09:30:00Z", paidAmount: "50000000.00", balance: "0.00", installmentCount: 10, startDate: "2016-01-15", endDate: "2025-01-15", totalPayableAmount: "50000000.00", totalPaidAmount: "50000000.00", statusHistory: [{ status: "COMPLETED", statusDisplay: "Completed", timestamp: "2026-08-15T09:30:00Z", note: "All installments paid and reconciled." }] })
    useMIPlanDetailMock.mockReturnValue({ data: completed, isLoading: false, error: null })
    renderDetail(completed)
    await screen.findByText("MIP-20260815-9E1168C4EF")
    expect(screen.queryByRole("button", { name: "Process Payment" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Cancel plan" })).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Print schedule" })).toBeInTheDocument()
  })

  it("shows a red terminated banner with the recorded reason and a green completed banner", async () => {
    const terminated = baseDetail({ id: "plan-terminated-1", planNumber: "MIP-20260710-77C0F1A4B2", status: "TERMINATED", statusDisplay: "Terminated", allowedActions: ["view", "print"], terminationReason: "Policy terminated by the policyholder’s surrender on 2026-07-10; the remaining maturity schedule was waived.", terminatedAt: "2026-07-10T11:00:00Z", statusHistory: [{ status: "TERMINATED", statusDisplay: "Terminated", timestamp: "2026-07-10T11:00:00Z", note: "Plan terminated." }] })
    useMIPlanDetailMock.mockReturnValue({ data: terminated, isLoading: false, error: null })
    const { unmount } = renderDetail(terminated)
    expect(await screen.findByRole("alert")).toBeInTheDocument()
    expect(screen.getByText("Plan terminated")).toBeInTheDocument()
    expect(screen.getByText(/Policy terminated by the policyholder/)).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Process Payment" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Cancel plan" })).not.toBeInTheDocument()
    unmount()

    const completed = baseDetail({ id: "plan-completed-1", planNumber: "MIP-20260815-9E1168C4EF", status: "COMPLETED", statusDisplay: "Completed", allowedActions: ["view", "print"], completedAt: "2026-08-15T09:30:00Z", installmentCount: 10 })
    useMIPlanDetailMock.mockReturnValue({ data: completed, isLoading: false, error: null })
    renderDetail(completed)
    expect(await screen.findByText("Plan completed")).toBeInTheDocument()
    expect(screen.getByText(/All 10 installments have been paid and reconciled/)).toBeInTheDocument()
    expect(screen.getByText(/Completed on 15 Aug 2026/)).toBeInTheDocument()
  })

  it("navigates to the linked policy when the header policy link is clicked", async () => {
    useMIPlanDetailMock.mockReturnValue({ data: baseDetail(), isLoading: false, error: null })
    const user = userEvent.setup()
    renderDetail(baseDetail(), true)
    await screen.findAllByText("ZIC-OL-2026-000001")
    const links = screen.getAllByRole("button", { name: /ZIC-OL-2026-000001/ })
    await user.click(links[0])
    expect(await screen.findByTestId("policy-marker")).toHaveTextContent("policy-aman-1")
  })

  it("switches between Overview, Schedule, Payments, Audit, and Documents tabs", async () => {
    useMIPlanDetailMock.mockReturnValue({ data: baseDetail(), isLoading: false, error: null })
    const user = userEvent.setup()
    renderDetail()
    await screen.findByText("MIP-20260901-9DD41C66AF")
    expect(screen.getByText("Plan context")).toBeInTheDocument()
    expect(screen.getByText("Number of installments")).toBeInTheDocument()
    expect(screen.getByText("Calculation source")).toBeInTheDocument()
    expect(screen.getByText("Rate Table")).toBeInTheDocument()
    expect(screen.getByText("Policy details")).toBeInTheDocument()
    expect(screen.getByText("Status timeline")).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Schedule" }))
    expect(screen.getByText("Installment schedule")).toBeInTheDocument()
    expect(screen.getByText("Installment #")).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Payments" }))
    expect(screen.getByText("Payment history")).toBeInTheDocument()
    expect(screen.getByText("Reconciliation report")).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Audit" }))
    expect(screen.getByText("Audit trail")).toBeInTheDocument()
    expect(screen.getByText("Plan created")).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Documents" }))
    expect(await screen.findByText("Maturity Schedule")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Print Schedule" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Print Advice" })).toBeInTheDocument()
  })

  it("processes the next due installment through the confirm modal", async () => {
    processMIPaymentMock.mockResolvedValue({ item: { id: "plan-active-1-item-2" }, created: true })
    useMIPlanDetailMock.mockReturnValue({ data: baseDetail(), isLoading: false, error: null })
    const user = userEvent.setup()
    renderDetail()
    await screen.findByText("MIP-20260901-9DD41C66AF")
    await user.click(screen.getByRole("button", { name: "Process Payment" }))
    const dialog = await screen.findByRole("dialog")
    expect(within(dialog).getByText(/Installment 2 of/)).toBeInTheDocument()
    await user.click(within(dialog).getByRole("button", { name: "Process payment" }))
    await waitFor(() => expect(processMIPaymentMock).toHaveBeenCalledWith("plan-active-1-item-2"))
    expect(toastMock).toHaveBeenCalledWith(expect.objectContaining({ tone: "success", title: "Payment processed" }))
  })

  it("withholds action buttons and document prints the user lacks permission for", async () => {
    mockPermissions = ["ol_maturity_installments.view"]
    useMIPlanDetailMock.mockReturnValue({ data: baseDetail(), isLoading: false, error: null })
    const user = userEvent.setup()
    renderDetail()
    await screen.findByText("MIP-20260901-9DD41C66AF")
    expect(screen.queryByRole("button", { name: "Process Payment" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Cancel plan" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Print schedule" })).not.toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Documents" }))
    expect(screen.getByText("Maturity Schedule")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Print Schedule" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Print Advice" })).not.toBeInTheDocument()
  })
})

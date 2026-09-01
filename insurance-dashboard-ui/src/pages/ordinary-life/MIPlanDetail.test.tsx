import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter, Route, Routes, useParams } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import type { MIBankAccount, MIPlanDetail as MIPlanDetailType, MIPlanItem, MIPlanItemPage } from "../../lib/maturityInstallments"

const { useMIPlanDetailMock, useMIPlanItemsMock, processMIPaymentMock, reverseMIPaymentMock, cancelMIPlanMock, printMIScheduleMock, printMIAdviceMock, toastMock } = vi.hoisted(() => ({
  useMIPlanDetailMock: vi.fn(),
  useMIPlanItemsMock: vi.fn(),
  processMIPaymentMock: vi.fn(),
  reverseMIPaymentMock: vi.fn(),
  cancelMIPlanMock: vi.fn(),
  printMIScheduleMock: vi.fn(),
  printMIAdviceMock: vi.fn(),
  toastMock: vi.fn(),
}))

vi.mock("../../lib/maturityInstallmentsHooks", async () => {
  const actual = await vi.importActual<typeof import("../../lib/maturityInstallmentsHooks")>("../../lib/maturityInstallmentsHooks")
  return { ...actual, useMIPlanDetail: useMIPlanDetailMock, useMIPlanItems: useMIPlanItemsMock }
})

vi.mock("../../lib/maturityInstallments", async () => {
  const actual = await vi.importActual<typeof import("../../lib/maturityInstallments")>("../../lib/maturityInstallments")
  return { ...actual, processMIPayment: processMIPaymentMock, reverseMIPayment: reverseMIPaymentMock, cancelMIPlan: cancelMIPlanMock, printMISchedule: printMIScheduleMock, printMIAdvice: printMIAdviceMock }
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
  bankAccounts: [
    { id: "ba-plan-active-1-1", accountName: "Amani Salum — Maturity", accountNumber: "0151234567891", bankName: "NMB Bank", branch: "Dar es Salaam", isDefault: true, availableBalance: "75000000.00" },
    { id: "ba-plan-active-1-2", accountName: "Amani Salum", accountNumber: "0169876543210", bankName: "CRDB Bank", branch: "Dar es Salaam", isDefault: false, availableBalance: "0.00" },
  ],
  ...overrides,
})

const scheduleRow = (overrides: Partial<MIPlanItem> = {}): MIPlanItem => ({
  id: `plan-long-term-1-item-${overrides.installmentNumber ?? 1}`,
  planId: "plan-long-term-1",
  installmentNumber: 1,
  dueDate: "2026-03-15",
  amount: "5000000.00",
  status: "SCHEDULED",
  statusDisplay: "Scheduled",
  requisitionNumber: null,
  paidDate: null,
  paidByDisplay: null,
  payerDisplay: null,
  paymentReference: null,
  narration: "",
  ...overrides,
})

const schedulePageOneRows: MIPlanItem[] = [
  scheduleRow({ installmentNumber: 1, dueDate: "2026-03-15", status: "PAID", statusDisplay: "Paid", requisitionNumber: "FO-MIP-2026-000501", paidDate: "2026-03-15", paymentReference: "FO-PAY-2026-000501" }),
  scheduleRow({ installmentNumber: 2, dueDate: "2027-03-15", status: "PAID", statusDisplay: "Paid", requisitionNumber: "FO-MIP-2026-000502", paidDate: "2027-03-15", paymentReference: "FO-PAY-2026-000502" }),
  scheduleRow({ installmentNumber: 3, dueDate: "2028-03-15", status: "MISSED", statusDisplay: "Missed", narration: "Payment was not received by the due date." }),
  ...Array.from({ length: 7 }, (_, index) => scheduleRow({ installmentNumber: index + 4, dueDate: `20${29 + index}-03-15`, status: "SCHEDULED", statusDisplay: "Scheduled" })),
]

const schedulePageTwoRows: MIPlanItem[] = Array.from({ length: 10 }, (_, index) => scheduleRow({ installmentNumber: index + 11, dueDate: `20${36 + index}-03-15`, status: "SCHEDULED", statusDisplay: "Scheduled" }))

const schedulePageData = (overrides: Partial<MIPlanItemPage> = {}): MIPlanItemPage => ({
  results: schedulePageOneRows,
  count: 20,
  page: 1,
  pageSize: 10,
  next: true,
  previous: false,
  totalAmount: "100000000.00",
  totalPaid: "10000000.00",
  totalRemaining: "90000000.00",
  ...overrides,
})

const longTermDetail = baseDetail({ id: "plan-long-term-1", planNumber: "MIP-20260101-5A1B2C3D4E" })

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

async function selectSmartOption(dialog: HTMLElement, fieldName: RegExp, optionName: RegExp) {
  fireEvent.click(within(dialog).getByRole("button", { name: fieldName }))
  fireEvent.click(await screen.findByRole("option", { name: optionName }))
}

async function completeCashFlow(dialog: HTMLElement, submitName: string) {
  await selectSmartOption(dialog, /Payment method/, /^Cash$/)
  fireEvent.click(within(dialog).getByRole("button", { name: "Next" }))
  await screen.findByText(/This will create a payment requisition in the Front Office/)
  fireEvent.click(within(dialog).getByRole("button", { name: submitName }))
}

describe("OL Maturity Installments detail (Prompt 3 master-detail)", () => {
  beforeEach(() => {
    mockPermissions = ["ol_maturity_installments.view", "ol_maturity_installments.process_payment", "ol_maturity_installments.reverse", "ol_maturity_installments.print", "ol_maturity_installments.cancel"]
    useMIPlanDetailMock.mockReset()
    useMIPlanItemsMock.mockReset()
    useMIPlanItemsMock.mockImplementation(() => ({ data: schedulePageData(), isLoading: false, error: null }))
    processMIPaymentMock.mockReset()
    reverseMIPaymentMock.mockReset()
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

  it("processes the next due installment through the payment modal", async () => {
    processMIPaymentMock.mockResolvedValue({ item: { id: "plan-active-1-item-2" }, created: true })
    useMIPlanDetailMock.mockReturnValue({ data: baseDetail(), isLoading: false, error: null })
    const user = userEvent.setup()
    renderDetail()
    await screen.findByText("MIP-20260901-9DD41C66AF")
    await user.click(screen.getByRole("button", { name: "Process Payment" }))
    const dialog = await screen.findByRole("dialog")
    expect(within(dialog).getByText(/Installment 2 — due/)).toBeInTheDocument()
    await completeCashFlow(dialog, "Process payment")
    await waitFor(() => expect(processMIPaymentMock).toHaveBeenCalledWith("plan-active-1-item-2", expect.objectContaining({ paymentMethod: "CASH" })))
    expect(within(dialog).getByText("Payment Requisition Created")).toBeInTheDocument()
    expect(toastMock).toHaveBeenCalledWith(expect.objectContaining({ tone: "success", title: "Payment Requisition Created" }))
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

  it("renders the schedule table with server-side pagination across pages", async () => {
    const pageTwo = schedulePageData({ results: schedulePageTwoRows, page: 2, next: false, previous: true })
    useMIPlanItemsMock.mockImplementation((_planId, page) => (page === 2 ? { data: pageTwo, isLoading: false, error: null } : { data: schedulePageData(), isLoading: false, error: null }))
    useMIPlanDetailMock.mockReturnValue({ data: longTermDetail, isLoading: false, error: null })
    const user = userEvent.setup()
    renderDetail()
    await user.click(screen.getByRole("button", { name: "Schedule" }))
    expect(await screen.findByText("Installment schedule")).toBeInTheDocument()
    expect(screen.getAllByRole("row")).toHaveLength(11)
    expect(screen.getByText("Page 1 of 2")).toBeInTheDocument()
    expect(screen.getByText("20 installments · 10 per page")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Next" })).toBeEnabled()
    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled()
    expect(screen.getAllByRole("row")[1]).toHaveTextContent("1")
    expect(screen.getAllByRole("row")[10]).toHaveTextContent("10")

    await user.click(screen.getByRole("button", { name: "Next" }))
    expect(await screen.findByText("Page 2 of 2")).toBeInTheDocument()
    expect(screen.getAllByRole("row")[1]).toHaveTextContent("11")
    expect(screen.getAllByRole("row")[10]).toHaveTextContent("20")
    expect(screen.getByRole("button", { name: "Previous" })).toBeEnabled()
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled()
  })

  it("highlights missed rows in red, paid rows in green, and keeps scheduled rows neutral", async () => {
    useMIPlanDetailMock.mockReturnValue({ data: longTermDetail, isLoading: false, error: null })
    const user = userEvent.setup()
    renderDetail()
    await user.click(screen.getByRole("button", { name: "Schedule" }))
    await screen.findByText("Installment schedule")
    const dataRows = screen.getAllByRole("row").slice(1)
    const missed = dataRows.find((row) => row.getAttribute("data-status") === "MISSED")
    const paid = dataRows.find((row) => row.getAttribute("data-status") === "PAID")
    const scheduled = dataRows.find((row) => row.getAttribute("data-status") === "SCHEDULED")
    expect(missed).toBeTruthy()
    expect(missed!.className).toContain("bg-[var(--destructive)]")
    expect(paid).toBeTruthy()
    expect(paid!.className).toContain("bg-[var(--success)]")
    expect(scheduled).toBeTruthy()
    expect(scheduled!.className).not.toContain("bg-[var(--destructive)]")
    expect(scheduled!.className).not.toContain("bg-[var(--success)]")
  })

  it("summarises the whole-schedule totals in the schedule footer", async () => {
    useMIPlanDetailMock.mockReturnValue({ data: longTermDetail, isLoading: false, error: null })
    const user = userEvent.setup()
    renderDetail()
    await user.click(screen.getByRole("button", { name: "Schedule" }))
    await screen.findByText("Installment schedule")
    expect(screen.getByText("Total amount")).toBeInTheDocument()
    expect(screen.getByText("Total paid")).toBeInTheDocument()
    expect(screen.getByText("Total remaining")).toBeInTheDocument()
    expect(screen.getAllByText(/100,000,000\.00/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/10,000,000\.00/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/90,000,000\.00/).length).toBeGreaterThan(0)
  })

  it("completes the payment modal flow for a scheduled installment with bank transfer details", async () => {
    processMIPaymentMock.mockResolvedValue({ item: { id: "plan-long-term-1-item-4" }, created: true })
    useMIPlanDetailMock.mockReturnValue({ data: longTermDetail, isLoading: false, error: null })
    const user = userEvent.setup()
    renderDetail()
    await user.click(screen.getByRole("button", { name: "Schedule" }))
    await screen.findByText("Installment schedule")
    await user.click(screen.getByRole("button", { name: "Process payment for installment 4" }))
    const dialog = await screen.findByRole("dialog")
    expect(within(dialog).getByText(/Installment 4 — due 15 Mar 2029/)).toBeInTheDocument()
    expect(within(dialog).getAllByText(/5,000,000\.00/).length).toBeGreaterThan(0)

    await selectSmartOption(dialog, /Payment method/, /^Bank Transfer$/)
    await selectSmartOption(dialog, /Bank account/, /NMB Bank 0151234567891/)
    fireEvent.change(within(dialog).getByLabelText(/Reference number/), { target: { value: "REF-2026-001" } })
    fireEvent.click(within(dialog).getByRole("button", { name: "Next" }))
    await screen.findByText(/This will create a payment requisition in the Front Office/)
    expect(within(dialog).getAllByText("Bank Transfer").length).toBeGreaterThan(0)
    expect(within(dialog).getAllByText(/NMB Bank 0151234567891/).length).toBeGreaterThan(0)
    fireEvent.click(within(dialog).getByRole("button", { name: "Process payment" }))

    await waitFor(() => expect(processMIPaymentMock).toHaveBeenCalledWith("plan-long-term-1-item-4", expect.objectContaining({ paymentMethod: "BANK_TRANSFER", referenceNumber: "REF-2026-001", bankAccountId: "ba-plan-active-1-1" })))
    expect(within(dialog).getByText("Payment Requisition Created")).toBeInTheDocument()
    expect(toastMock).toHaveBeenCalledWith(expect.objectContaining({ tone: "success", title: "Payment Requisition Created" }))
  })

  it("reverses a paid installment from its row action after capturing a reason", async () => {
    reverseMIPaymentMock.mockResolvedValue({ item: { id: "plan-long-term-1-item-1" }, plan: longTermDetail })
    useMIPlanDetailMock.mockReturnValue({ data: longTermDetail, isLoading: false, error: null })
    const user = userEvent.setup()
    renderDetail()
    await user.click(screen.getByRole("button", { name: "Schedule" }))
    await screen.findByText("Installment schedule")
    await user.click(screen.getByRole("button", { name: "Reverse payment for installment 1" }))
    const dialog = await screen.findByRole("dialog")
    fireEvent.change(within(dialog).getByPlaceholderText(/why this payment is being reversed/), { target: { value: "Duplicate disbursement" } })
    await user.click(within(dialog).getByRole("button", { name: "Reverse payment" }))
    await waitFor(() => expect(reverseMIPaymentMock).toHaveBeenCalledWith("plan-long-term-1-item-1", { reason: "Duplicate disbursement" }))
    expect(toastMock).toHaveBeenCalledWith(expect.objectContaining({ tone: "success", title: "Payment reversed" }))
  })

  it("processes selected installments in bulk through the payment modal", async () => {
    processMIPaymentMock.mockResolvedValue({ item: { id: "plan-long-term-1-item-4" }, created: true })
    useMIPlanDetailMock.mockReturnValue({ data: longTermDetail, isLoading: false, error: null })
    const user = userEvent.setup()
    renderDetail()
    await user.click(screen.getByRole("button", { name: "Schedule" }))
    await screen.findByText("Installment schedule")
    await user.click(screen.getByRole("checkbox", { name: "Select installment 4" }))
    await user.click(screen.getByRole("checkbox", { name: "Select installment 5" }))
    await user.click(screen.getByRole("button", { name: /Process Selected/ }))
    const dialog = await screen.findByRole("dialog")
    expect(within(dialog).getByText("Process 2 installment payments")).toBeInTheDocument()
    expect(within(dialog).getByText(/Installment 4 — due/)).toBeInTheDocument()
    expect(within(dialog).getByText(/Installment 5 — due/)).toBeInTheDocument()
    await completeCashFlow(dialog, "Process 2 payments")
    await waitFor(() => expect(processMIPaymentMock).toHaveBeenCalledWith("plan-long-term-1-item-4", expect.objectContaining({ paymentMethod: "CASH" })))
    await waitFor(() => expect(processMIPaymentMock).toHaveBeenCalledWith("plan-long-term-1-item-5", expect.objectContaining({ paymentMethod: "CASH" })))
    expect(within(dialog).getByText("Payment Requisition Created")).toBeInTheDocument()
    expect(toastMock).toHaveBeenCalledWith(expect.objectContaining({ tone: "success", title: "Payment Requisition Created" }))
  })

  it("requires a partner bank account and reference for bank transfer payments", async () => {
    useMIPlanDetailMock.mockReturnValue({ data: longTermDetail, isLoading: false, error: null })
    const user = userEvent.setup()
    renderDetail()
    await user.click(screen.getByRole("button", { name: "Schedule" }))
    await screen.findByText("Installment schedule")
    await user.click(screen.getByRole("button", { name: "Process payment for installment 4" }))
    const dialog = await screen.findByRole("dialog")
    await selectSmartOption(dialog, /Payment method/, /^Bank Transfer$/)
    fireEvent.click(within(dialog).getByRole("button", { name: "Next" }))
    expect(within(dialog).getByText("Select the partner bank account that will fund this disbursement.")).toBeInTheDocument()
    expect(within(dialog).getByText("A bank transfer or cheque reference is required for this payment method.")).toBeInTheDocument()
    expect(within(dialog).queryByText(/This will create a payment requisition in the Front Office/)).not.toBeInTheDocument()
    expect(processMIPaymentMock).not.toHaveBeenCalled()
  })

  it("shows the success state for a processed installment", async () => {
    processMIPaymentMock.mockResolvedValue({ item: { id: "plan-long-term-1-item-4", status: "PAYMENT_PENDING" }, created: true })
    useMIPlanDetailMock.mockReturnValue({ data: longTermDetail, isLoading: false, error: null })
    const user = userEvent.setup()
    renderDetail()
    await user.click(screen.getByRole("button", { name: "Schedule" }))
    await screen.findByText("Installment schedule")
    await user.click(screen.getByRole("button", { name: "Process payment for installment 4" }))
    const dialog = await screen.findByRole("dialog")
    await completeCashFlow(dialog, "Process payment")
    await waitFor(() => expect(processMIPaymentMock).toHaveBeenCalledWith("plan-long-term-1-item-4", expect.objectContaining({ paymentMethod: "CASH" })))
    expect(within(dialog).getByText("Payment Requisition Created")).toBeInTheDocument()
    expect(within(dialog).getByText(/Installment 4 on MIP-20260101-5A1B2C3D4E are now payment pending/)).toBeInTheDocument()
    expect(toastMock).toHaveBeenCalledWith(expect.objectContaining({ tone: "success", title: "Payment Requisition Created" }))
  })

  it("surfaces an error coach when the partner bank has insufficient funds", async () => {
    processMIPaymentMock.mockRejectedValue(new Error("Insufficient funds in partner bank for this disbursement."))
    useMIPlanDetailMock.mockReturnValue({ data: longTermDetail, isLoading: false, error: null })
    const user = userEvent.setup()
    renderDetail()
    await user.click(screen.getByRole("button", { name: "Schedule" }))
    await screen.findByText("Installment schedule")
    await user.click(screen.getByRole("button", { name: "Process payment for installment 4" }))
    const dialog = await screen.findByRole("dialog")
    await completeCashFlow(dialog, "Process payment")
    expect(await screen.findByText("Insufficient funds in partner bank for this disbursement.")).toBeInTheDocument()
    expect(within(dialog).getByText("Payment requisition not created")).toBeInTheDocument()
  })
})

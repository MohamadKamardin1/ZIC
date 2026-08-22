import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import CommitmentDetailPage from "./CommitmentDetail"

const { requestMock, navigateMock, paramsMock } = vi.hoisted(() => ({ requestMock: vi.fn(), navigateMock: vi.fn(), paramsMock: { id: "uuid-1" } }))

vi.mock("../../lib/apiClient", () => ({ request: requestMock }))
vi.mock("react-router-dom", () => ({
  useParams: () => paramsMock,
  useNavigate: () => navigateMock,
}))
vi.mock("../../components/ui/Toast", () => ({ useToast: () => ({ toast: vi.fn(), dismiss: vi.fn() }) }))

const DETAIL = {
  id: "uuid-1",
  commitmentNumber: "OLC-2026-00010",
  sourceType: "POLICY",
  sourceReference: "POL-2026-0001",
  partnerName: "Zanzibar Trading Co.",
  productName: "Family Protection",
  planName: "Standard",
  currency: "TZS",
  premiumFrequency: "MONTHLY",
  installmentNumber: 7,
  installmentCount: 120,
  dueDate: "2026-09-01",
  premiumAmount: "100000.00",
  amountPaid: "40000.00",
  amountWaived: "0.00",
  balance: "60000.00",
  status: "PARTIALLY_PAID",
  graceDate: "2026-10-01",
  lapseDate: "2026-10-16",
  allowedActions: ["record_payment", "reschedule"],
  graceDays: 30,
  reasonCode: "",
  reasonText: "",
  allocations: [
    { id: "a1", receiptReference: "RCT-2026-001", amount: "40000.00", paymentMode: "CASH", currency: "TZS", exchangeRate: "1.000000", reversalOf: null, allocatedAt: "2026-08-20T10:00:00Z" },
    { id: "a2", receiptReference: "RCT-2026-001-R1", amount: "40000.00", paymentMode: "CASH", currency: "TZS", exchangeRate: "1.000000", reversalOf: "a1", allocatedAt: "2026-08-21T10:00:00Z" },
  ],
  notificationLogs: [
    { id: "n1", eventType: "GRACE_START", dispatchOn: "2026-10-02", notificationChannel: "SMS", recipientType: "POLICYHOLDER", recipientIdentifier: "+255700000000", status: "DISPATCHED" },
  ],
  statusHistory: [
    { fromStatus: "PENDING", toStatus: "PARTIALLY_PAID", actorName: "Amina Hassan", createdAt: "2026-08-20T10:05:00Z", reason: "Cash allocation posted", sourceChannel: "API" },
  ],
}

function renderDetail() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <CommitmentDetailPage />
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  requestMock.mockReset()
  navigateMock.mockReset()
  requestMock.mockImplementation(async (path: string) => {
    if (path.includes("/options/")) return { statuses: [{ code: "PARTIALLY_PAID", name: "Partially Paid", tone: "warning" }], currencies: ["TZS", "USD"], paymentModes: [] }
    if (path.includes("/commitments/")) return DETAIL
    return {}
  })
})

describe("CommitmentDetailPage", () => {
  it("renders the header with names, status, balance highlight, and never UUIDs", async () => {
    renderDetail()

    expect(await screen.findByText("OLC-2026-00010")).toBeInTheDocument()
    expect(screen.getByText(/Zanzibar Trading Co\./)).toBeInTheDocument()
    expect(screen.getByText(/Family Protection \/ Standard/)).toBeInTheDocument()
    expect(await screen.findByText("Partially Paid")).toBeInTheDocument()
    expect(screen.getByText(/balance TZS 60,000\.00/i)).toBeInTheDocument()
    expect(screen.queryByText("uuid-1")).not.toBeInTheDocument()
  })

  it("renders the payment progress bar with correct math (40%)", async () => {
    renderDetail()
    await screen.findByText("OLC-2026-00010")

    const progress = screen.getByTestId("payment-progress")
    expect(progress).toHaveAttribute("aria-valuenow", "40")
    expect(screen.getByText(/40%/)).toBeInTheDocument()
  })

  it("renders action buttons only from the allowed-actions payload", async () => {
    renderDetail()
    await screen.findByText("OLC-2026-00010")

    expect(screen.getByRole("button", { name: "Record Payment" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Reschedule" })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Reverse" })).not.toBeInTheDocument()
  })

  it("renders the overview tab with source, amounts, and applied parameters", async () => {
    renderDetail()
    await screen.findByText("OLC-2026-00010")

    expect(screen.getByText("MONTHLY")).toBeInTheDocument()
    expect(screen.getByText("30")).toBeInTheDocument()
    expect(screen.getByText("7 of 120")).toBeInTheDocument()
    expect(screen.getAllByText("TZS 100,000.00").length).toBeGreaterThan(0)
  })

  it("renders the allocations tab with receipts and reversal links", async () => {
    renderDetail()
    await screen.findByText("OLC-2026-00010")

    fireEvent.click(screen.getByRole("button", { name: "Allocations" }))
    expect(await screen.findByText("RCT-2026-001")).toBeInTheDocument()
    expect(screen.getAllByText("CASH").length).toBeGreaterThan(0)
    expect(screen.getAllByText("1.000000").length).toBeGreaterThan(0)
    expect(screen.getByText(/Reversal of a1/i)).toBeInTheDocument()
    expect(screen.queryByText("a1", { exact: true })).not.toBeInTheDocument()
  })

  it("renders the history tab with actors and reasons", async () => {
    renderDetail()
    await screen.findByText("OLC-2026-00010")

    fireEvent.click(screen.getByRole("button", { name: "History" }))
    expect(await screen.findByText(/PARTIALLY_PAID/)).toBeInTheDocument()
    expect(screen.getByText(/Amina Hassan/)).toBeInTheDocument()
    expect(screen.getByText("Cash allocation posted")).toBeInTheDocument()
    expect(screen.getByText("API")).toBeInTheDocument()
  })

  it("renders the notifications tab with channel and recipient badges", async () => {
    renderDetail()
    await screen.findByText("OLC-2026-00010")

    fireEvent.click(screen.getByRole("button", { name: "Notifications" }))
    expect(await screen.findByText("GRACE_START")).toBeInTheDocument()
    expect(screen.getByText("SMS")).toBeInTheDocument()
    expect(screen.getByText("POLICYHOLDER")).toBeInTheDocument()
    expect(screen.getByText("+255700000000")).toBeInTheDocument()
  })

  it("renders the ErrorCoach when the detail fetch fails", async () => {
    requestMock.mockImplementation(async (path: string) => {
      if (path.includes("/options/")) return { statuses: [], currencies: [], paymentModes: [] }
      throw { error_code: "COMMITMENT_NOT_FOUND", message: "This commitment no longer exists." }
    })
    renderDetail()
    expect(await screen.findByText("Commitment detail could not be loaded")).toBeInTheDocument()
    expect(screen.getByTestId("error-coach-code")).toHaveTextContent("COMMITMENT_NOT_FOUND")
    expect(screen.queryByTestId("error-coach-retry")).not.toBeInTheDocument()
  })
})
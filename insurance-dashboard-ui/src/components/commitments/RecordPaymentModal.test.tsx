import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import type { ComponentProps } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { RecordPaymentModal } from "./RecordPaymentModal"
import type { CommitmentDetail } from "../../lib/commitments"

const { requestMock, toastMock } = vi.hoisted(() => ({ requestMock: vi.fn(), toastMock: vi.fn() }))

vi.mock("../../lib/apiClient", () => ({ request: requestMock }))
vi.mock("react-router-dom", () => ({ useNavigate: () => vi.fn() }))
vi.mock("../../lib/access", () => ({
  useAccess: () => ({ access: { visibleModules: [], permissions: [{ module: "system_parameters", action: "manage" }], groups: [] }, canAccess: () => true }),
}))
vi.mock("../../components/ui/Toast", () => ({ useToast: () => ({ toast: toastMock, dismiss: vi.fn() }) }))

const COMMITMENT: CommitmentDetail = {
  id: "c-1",
  commitmentNumber: "OLC-2026-00010",
  sourceType: "POLICY",
  sourceReference: "POL-2026-0001",
  partnerName: "Zanzibar Trading Co.",
  productName: "Family Protection",
  planName: "Standard",
  currency: "TZS",
  premiumFrequency: "MONTHLY",
  installmentNumber: 1,
  installmentCount: 12,
  dueDate: "2026-09-01",
  premiumAmount: "100000.00",
  amountPaid: "40000.00",
  balance: "60000.00",
  status: "PARTIALLY_PAID",
  graceDate: "2026-10-01",
  lapseDate: "2026-10-16",
  allowedActions: ["record_payment"],
  allocations: [],
  notificationLogs: [],
}

function renderModal(props: Partial<ComponentProps<typeof RecordPaymentModal>> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <RecordPaymentModal open onClose={vi.fn()} commitment={COMMITMENT} onSuccess={vi.fn()} {...props} />
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  requestMock.mockReset()
  toastMock.mockReset()
  requestMock.mockImplementation(async (path: string) => {
    if (path.includes("/ol/options/payment-modes/")) return { items: [{ id: "CASH", label: "Cash" }, { id: "M-PESA", label: "M-PESA" }] }
    if (path.includes("/ol/options/currencies/")) return { items: [{ id: "TZS", label: "TZS" }, { id: "USD", label: "USD" }] }
    return {}
  })
})

async function selectPaymentMode() {
  fireEvent.click(screen.getByLabelText(/Payment mode/))
  fireEvent.click(await screen.findByRole("option", { name: "Cash" }))
}

async function selectCurrency(value: string) {
  fireEvent.click(screen.getByLabelText(/Currency/))
  fireEvent.click(await screen.findByRole("option", { name: value }))
}

describe("RecordPaymentModal", () => {
  it("previews the remaining balance live (60,000 − 25,000 = 35,000)", async () => {
    renderModal()
    fireEvent.change(screen.getByLabelText(/Amount/), { target: { value: "25000" } })
    expect(screen.getByTestId("balance-preview")).toHaveTextContent("Within balance")
    expect(screen.getByText(/TZS 35,000\.00/)).toBeInTheDocument()
  })

  it("flags an amount above the balance as exceeds-balance", async () => {
    renderModal()
    fireEvent.change(screen.getByLabelText(/Amount/), { target: { value: "999999" } })
    expect(screen.getByTestId("balance-preview")).toHaveTextContent("Exceeds balance")
    expect(screen.getByText(/939,999\.00/)).toBeInTheDocument()
  })

  it("requires an exchange rate for a cross-currency payment", async () => {
    renderModal()
    await selectCurrency("USD")
    expect(screen.getByTestId("exchange-rate-field")).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText(/Amount/), { target: { value: "10000" } })
    fireEvent.change(screen.getByLabelText(/Receipt reference/), { target: { value: "RCT-2026-999" } })
    await selectPaymentMode()
    fireEvent.click(screen.getByTestId("record-payment-submit"))

    expect(screen.getByText(/exchange rate greater than zero/)).toBeInTheDocument()
    expect(requestMock.mock.calls.some((call) => String(call[0]).includes("/record_payment/"))).toBe(false)
  })

  it("renders the COMMITMENT_OVERPAYMENT ErrorCoach with resolution steps", async () => {
    requestMock.mockImplementation(async (path: string) => {
      if (path.includes("/ol/options/payment-modes/")) return { items: [{ id: "CASH", label: "Cash" }] }
      if (path.includes("/ol/options/currencies/")) return { items: [{ id: "TZS", label: "TZS" }, { id: "USD", label: "USD" }] }
      throw {
        error_code: "COMMITMENT_OVERPAYMENT",
        message: "The payment amount exceeds the outstanding balance.",
        resolution_steps: ["Adjust the amount so it is equal to or below the outstanding balance.", "If you collected more, record the surplus as a credit."],
      }
    })
    renderModal()
    fireEvent.change(screen.getByLabelText(/Amount/), { target: { value: "999999" } })
    fireEvent.change(screen.getByLabelText(/Receipt reference/), { target: { value: "RCT-2026-999" } })
    await selectPaymentMode()

    fireEvent.click(screen.getByTestId("record-payment-submit"))
    expect(await screen.findByTestId("error-coach-code")).toHaveTextContent("COMMITMENT_OVERPAYMENT")
    expect(screen.getByText(/Adjust the amount so it is equal to or below the outstanding balance/)).toBeInTheDocument()
  })

  it("records a same-currency payment and reports success", async () => {
    renderModal()
    fireEvent.change(screen.getByLabelText(/Amount/), { target: { value: "40000" } })
    fireEvent.change(screen.getByLabelText(/Receipt reference/), { target: { value: "RCT-2026-777" } })
    await selectPaymentMode()

    fireEvent.click(screen.getByTestId("record-payment-submit"))
    await waitFor(() => expect(requestMock).toHaveBeenCalledWith(expect.stringContaining("/record_payment/"), expect.anything()), { timeout: 5000 })
    expect(toastMock).toHaveBeenCalledWith(expect.objectContaining({ tone: "success", title: "Payment recorded" }))
  })
})
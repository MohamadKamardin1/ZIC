import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import type { ComponentProps } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { ManualCommitmentModal } from "./ManualCommitmentModal"

const { requestMock, toastMock } = vi.hoisted(() => ({ requestMock: vi.fn(), toastMock: vi.fn() }))

vi.mock("../../lib/apiClient", () => ({ request: requestMock }))

vi.mock("../../lib/access", () => ({
  useAccess: () => ({
    access: { visibleModules: ["ol_commitments"], permissions: [{ module: "ol_commitments", action: "record_payment" }], groups: [] },
    isLoading: false,
    isSuperAdmin: false,
    canAccess: () => true,
    hasPermission: (code: string) => ["ol_commitments.record_payment"].includes(code.toLowerCase()),
  }),
}))

vi.mock("../../components/ui/Toast", () => ({ useToast: () => ({ toast: toastMock, dismiss: vi.fn() }) }))

const REFERENCES = {
  partners: [{ id: "partner-1", label: "Zanzibar Trading Co." }],
  products: [{ id: "product-1", label: "Family Protection" }],
  plans: [{ id: "plan-1", label: "Standard" }],
}

let createdPayload: Record<string, unknown> | null = null

function renderModal(props: Partial<ComponentProps<typeof ManualCommitmentModal>> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <ManualCommitmentModal open onClose={vi.fn()} onCreated={onCreatedSpy} {...props} />
    </QueryClientProvider>,
  )
}

const onCreatedSpy = vi.fn()

beforeEach(() => {
  requestMock.mockReset()
  toastMock.mockReset()
  onCreatedSpy.mockReset()
  createdPayload = null
  requestMock.mockImplementation(async (path: string, init?: RequestInit) => {
    if (path.includes("/options/references/")) return REFERENCES
    if (path.includes("/options/")) return { currencies: ["TZS", "USD"], paymentModes: ["CASH", "M-PESA"], statuses: [] }
    if (path.includes("/ol/options/payment-modes/")) return { items: [{ id: "CASH", label: "Cash" }, { id: "M-PESA", label: "M-PESA" }] }
    if (path.includes("/commitments/manual/")) {
      createdPayload = init?.body ? (JSON.parse(String(init.body)) as Record<string, unknown>) : {}
      return { id: "new-1", commitmentNumber: "OLC-2026-00050", sourceType: "MANUAL", status: "PENDING", currency: "TZS" }
    }
    return {}
  })
})

describe("ManualCommitmentModal", () => {
  it("shows inline validation errors before anything is filled", async () => {
    renderModal()
    fireEvent.click(screen.getByTestId("manual-submit"))

    expect(screen.getByText("Select a partner.")).toBeInTheDocument()
    expect(screen.getByText("Select a product.")).toBeInTheDocument()
    expect(screen.getByText("Choose a due date.")).toBeInTheDocument()
    expect(screen.getByText("Amount must be greater than zero.")).toBeInTheDocument()
    expect(screen.getByText("A reason is required.")).toBeInTheDocument()
    expect(requestMock).not.toHaveBeenCalledWith(expect.stringContaining("/commitments/manual/"))
  })

  it("creates a manual commitment and reports success with a next-step hint", async () => {
    renderModal()

    fireEvent.click(screen.getByLabelText(/Partner/))
    fireEvent.click(await screen.findByRole("option", { name: /Zanzibar Trading Co/ }))

    fireEvent.click(screen.getByLabelText(/Product/))
    fireEvent.click(await screen.findByRole("option", { name: /Family Protection/ }))

    fireEvent.change(screen.getByLabelText(/Due date/), { target: { value: "2026-09-15" } })
    fireEvent.change(screen.getByLabelText(/Amount/), { target: { value: "75000.00" } })
    fireEvent.change(screen.getByLabelText(/Reason/), { target: { value: "Arrears catch-up premium for the client" } })

    fireEvent.click(screen.getByTestId("manual-submit"))

    await waitFor(
      () => {
        const madeManualRequest = requestMock.mock.calls.some((call) => String(call[0]).includes("/commitments/manual/"))
        expect(madeManualRequest).toBe(true)
      },
      { timeout: 5000 },
    )
    expect(createdPayload).toMatchObject({
      partner: "partner-1",
      product: "product-1",
      currency: "TZS",
      dueDate: "2026-09-15",
      premiumAmount: "75000.00",
    })
    expect(toastMock).toHaveBeenCalledWith(expect.objectContaining({ tone: "success" }))
    await waitFor(() => expect(onCreatedSpy).toHaveBeenCalledWith(expect.objectContaining({ commitmentNumber: "OLC-2026-00050", id: "new-1" })), { timeout: 5000 })
  })
})
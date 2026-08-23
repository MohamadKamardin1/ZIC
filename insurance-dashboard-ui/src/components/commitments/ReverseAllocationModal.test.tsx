import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import type { ComponentProps } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { ReverseAllocationModal } from "./ReverseAllocationModal"
import type { CommitmentAllocation } from "../../lib/commitments"

const { requestMock, toastMock } = vi.hoisted(() => ({ requestMock: vi.fn(), toastMock: vi.fn() }))

vi.mock("../../lib/apiClient", () => ({ request: requestMock }))
vi.mock("react-router-dom", () => ({ useNavigate: () => vi.fn() }))
vi.mock("../../components/ui/Toast", () => ({ useToast: () => ({ toast: toastMock, dismiss: vi.fn() }) }))

const ALLOCATION: CommitmentAllocation = {
  id: "a-1",
  receiptReference: "RCT-2026-001",
  amount: "40000.00",
  paymentMode: "CASH",
  currency: "TZS",
  exchangeRate: "1.000000",
  allocatedAt: "2026-08-20T10:00:00Z",
}

function renderModal(props: Partial<ComponentProps<typeof ReverseAllocationModal>> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <ReverseAllocationModal open onClose={vi.fn()} commitmentId="c-1" allocation={ALLOCATION} onSuccess={onSuccessSpy} {...props} />
    </QueryClientProvider>,
  )
}

const onSuccessSpy = vi.fn()

beforeEach(() => {
  requestMock.mockReset()
  toastMock.mockReset()
  onSuccessSpy.mockReset()
  requestMock.mockImplementation(async (path: string) => {
    if (path.includes("/reverse_allocation/")) return { id: "c-1", status: "PENDING", allocations: [] }
    return {}
  })
})

describe("ReverseAllocationModal", () => {
  it("summarises the allocation being reversed", async () => {
    renderModal()
    expect(screen.getByText("RCT-2026-001")).toBeInTheDocument()
    expect(screen.getByText("TZS 40,000.00")).toBeInTheDocument()
    expect(screen.getByText("CASH")).toBeInTheDocument()
  })

  it("requires a reason before reversing", async () => {
    renderModal()
    fireEvent.click(screen.getByTestId("reverse-allocation-submit"))
    expect(screen.getByText("A reason is required.")).toBeInTheDocument()
    expect(requestMock.mock.calls.some((call) => String(call[0]).includes("/reverse_allocation/"))).toBe(false)
  })

  it("reverses with a supplied reason, toasts, and completes", async () => {
    renderModal()
    fireEvent.change(screen.getByLabelText(/Reason/), { target: { value: "Duplicate cash receipt collected in error" } })
    fireEvent.click(screen.getByTestId("reverse-allocation-submit"))

    await waitFor(
      () => {
        expect(requestMock.mock.calls.some((call) => String(call[0]).includes("/reverse_allocation/"))).toBe(true)
      },
      { timeout: 5000 },
    )
    expect(toastMock).toHaveBeenCalledWith(expect.objectContaining({ tone: "success", message: expect.stringContaining("Balance restored.") }))
    await waitFor(() => expect(onSuccessSpy).toHaveBeenCalled(), { timeout: 5000 })
  })
})
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import type { ComponentProps } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { LifecycleActionModal, LIFECYCLE_ACTIONS } from "./LifecycleActionModal"
import type { LifecycleAction } from "./LifecycleActionModal"
import type { CommitmentDetail } from "../../lib/commitments"

const { requestMock, toastMock } = vi.hoisted(() => ({ requestMock: vi.fn(), toastMock: vi.fn() }))

vi.mock("../../lib/apiClient", () => ({ request: requestMock }))
vi.mock("react-router-dom", () => ({ useNavigate: () => vi.fn() }))
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
  amountPaid: "0.00",
  balance: "100000.00",
  status: "PENDING",
  graceDate: "2026-10-01",
  lapseDate: "2026-10-16",
  graceDays: 30,
  allowedActions: LIFECYCLE_ACTIONS,
  allocations: [],
  notificationLogs: [],
}

function renderModal(action: LifecycleAction, overrides: Partial<ComponentProps<typeof LifecycleActionModal>> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <LifecycleActionModal open onClose={vi.fn()} commitmentId="c-1" action={action} commitment={COMMITMENT} onSuccess={onSuccessSpy} {...overrides} />
    </QueryClientProvider>,
  )
}

const onSuccessSpy = vi.fn()

function calledWithAction(action: string): boolean {
  return requestMock.mock.calls.some((call) => String(call[0]).includes(`/${action}/`))
}

beforeEach(() => {
  requestMock.mockReset()
  toastMock.mockReset()
  onSuccessSpy.mockReset()
  requestMock.mockImplementation(async (path: string) => {
    if (path.includes("/suspend/")) return { id: "c-1", status: "SUSPENDED" }
    if (path.includes("/reactivate/")) return { id: "c-1", status: "PENDING" }
    if (path.includes("/waive/")) return { id: "c-1", status: "WAIVED", approval_required: true }
    if (path.includes("/cancel/")) return { id: "c-1", status: "CANCELLED" }
    if (path.includes("/reschedule/")) return { id: "c-1", status: "PENDING" }
    return {}
  })
})

describe("LifecycleActionModal — validation per action", () => {
  it.each(LIFECYCLE_ACTIONS)("%s requires a mandatory reason", async (action) => {
    renderModal(action)
    fireEvent.click(screen.getByTestId(`lifecycle-submit-${action}`))
    expect(screen.getByText("A reason is required.")).toBeInTheDocument()
    expect(calledWithAction(action)).toBe(false)
  })

  it.each(["suspend", "cancel"] as LifecycleAction[])("%s sends the reason after filling", async (action) => {
    renderModal(action)
    fireEvent.change(screen.getByLabelText(/Reason/), { target: { value: "Business decision to close this commitment" } })
    fireEvent.click(screen.getByTestId(`lifecycle-submit-${action}`))
    await waitFor(() => expect(calledWithAction(action)).toBe(true), { timeout: 5000 })
    expect(toastMock).toHaveBeenCalledWith(expect.objectContaining({ tone: "success" }))
  })

  it("waive shows the approval-required banner explaining the approval hook", async () => {
    renderModal("waive")
    expect(screen.getByText("Approval required")).toBeInTheDocument()
    expect(screen.getByText(/will route through the approval workflow/i)).toBeInTheDocument()
  })

  it("reschedule requires a new due date and shows the parameter hint", async () => {
    renderModal("reschedule")
    expect(screen.getByTestId("reschedule-hint")).toHaveTextContent(/OL Grace Period/)
    expect(screen.getByTestId("reschedule-hint")).toHaveTextContent("30")
    fireEvent.click(screen.getByTestId(`lifecycle-submit-reschedule`))
    expect(screen.getByText("Choose a new due date on or after today.")).toBeInTheDocument()
    expect(calledWithAction("reschedule")).toBe(false)

    fireEvent.change(screen.getByLabelText(/New due date/), { target: { value: "2026-10-01" } })
    fireEvent.change(screen.getByLabelText(/Reason/), { target: { value: "Customer requested a later collection date" } })
    fireEvent.click(screen.getByTestId(`lifecycle-submit-reschedule`))
    await waitFor(() => expect(calledWithAction("reschedule")).toBe(true), { timeout: 5000 })
  })

  it("renders allowed transitions in the ErrorCoach for an invalid transition", async () => {
    requestMock.mockImplementation(async () => {
      throw {
        error_code: "COMMITMENT_INVALID_TRANSITION",
        message: "This commitment cannot be cancelled from its current state.",
        resolution_steps: ["Allowed transitions: record payment from PENDING.", "Allowed transitions: suspend from PENDING.", "Allowed transitions: waive from PENDING."],
      }
    })
    renderModal("cancel")
    fireEvent.change(screen.getByLabelText(/Reason/), { target: { value: "Attempting an invalid cancellation" } })
    fireEvent.click(screen.getByTestId(`lifecycle-submit-cancel`))

    expect(await screen.findByTestId("error-coach-code")).toHaveTextContent("COMMITMENT_INVALID_TRANSITION")
    const steps = [...screen.queryAllByTestId("error-coach-steps")[0]?.querySelectorAll("li") ?? []].map((node) => node.textContent)
    expect(steps.some((step) => (step ?? "").toLowerCase().includes("allowed transitions"))).toBe(true)
    expect(screen.getByText(/Allowed transitions: suspend from PENDING/)).toBeInTheDocument()
  })
})
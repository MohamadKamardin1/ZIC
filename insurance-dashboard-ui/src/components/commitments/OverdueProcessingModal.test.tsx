import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import type { ComponentProps } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { OverdueProcessingModal, OVERDUE_STAGES } from "./OverdueProcessingModal"

const { requestMock, navigateMock, toastMock } = vi.hoisted(() => ({ requestMock: vi.fn(), navigateMock: vi.fn(), toastMock: vi.fn() }))

vi.mock("../../lib/apiClient", () => ({ request: requestMock }))
vi.mock("react-router-dom", () => ({ useNavigate: () => navigateMock }))
vi.mock("../../components/ui/Toast", () => ({ useToast: () => ({ toast: toastMock, dismiss: vi.fn() }) }))

function renderModal(props: Partial<ComponentProps<typeof OverdueProcessingModal>> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <OverdueProcessingModal open onClose={vi.fn()} onComplete={vi.fn()} {...props} />
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  requestMock.mockReset()
  navigateMock.mockReset()
  toastMock.mockReset()
})

describe("OverdueProcessingModal", () => {
  it("renders all four staged progress labels", () => {
    renderModal()
    OVERDUE_STAGES.forEach((stage) => {
      expect(screen.getByTestId(`overdue-stage-${stage}`)).toBeInTheDocument()
    })
    expect(screen.getByText("Validate due commitments")).toBeInTheDocument()
    expect(screen.getByText("Update statuses to overdue")).toBeInTheDocument()
    expect(screen.getByText("Create grace notifications")).toBeInTheDocument()
    expect(screen.getByText("Summarize results")).toBeInTheDocument()
  })

  it("runs processing and shows summary counts with working links", async () => {
    requestMock.mockImplementation(async (path: string) => {
      if (path.includes("/process-overdue/")) return { processed: 7, overdue: 3, notified: 5, lapse_reviews: 2 }
      return {}
    })
    renderModal()

    fireEvent.click(screen.getByTestId("run-overdue"))

    const summary = await screen.findByTestId("overdue-summary", undefined, { timeout: 5000 })
    expect(within(summary).getByText("7")).toBeInTheDocument()
    expect(within(summary).getByText("3")).toBeInTheDocument()
    expect(within(summary).getByText("5")).toBeInTheDocument()
    expect(within(summary).getByText("2")).toBeInTheDocument()

    fireEvent.click(screen.getByTestId("overdue-link"))
    expect(navigateMock).toHaveBeenCalledWith("/ordinary-life/commitments?overdue_only=true")

    fireEvent.click(screen.getByTestId("lapse-link"))
    expect(navigateMock).toHaveBeenCalledWith("/ordinary-life/commitments")
  })

  it("renders the ErrorCoach when the batch fails", async () => {
    requestMock.mockImplementation(async (path: string) => {
      if (path.includes("/process-overdue/")) throw { error_code: "COMMITMENT_NOT_FOUND", message: "Batch job aborted." }
      return {}
    })
    renderModal()
    fireEvent.click(screen.getByTestId("run-overdue"))
    expect(await screen.findByTestId("error-coach-code", undefined, { timeout: 5000 })).toHaveTextContent("COMMITMENT_NOT_FOUND")
  })
})
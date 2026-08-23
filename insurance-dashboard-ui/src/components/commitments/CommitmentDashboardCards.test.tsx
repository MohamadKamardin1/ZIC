import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter, useLocation } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { CommitmentDashboardCards } from "./CommitmentDashboardCards"

const { requestMock, accessMock } = vi.hoisted(() => ({ requestMock: vi.fn(), accessMock: vi.fn() }))

vi.mock("../../lib/apiClient", () => ({ request: requestMock }))
vi.mock("../../lib/access", () => ({ useAccess: () => accessMock() }))

const KPI_PAYLOAD = {
  totalDue: "1000000.00",
  totalOutstanding: "650000.00",
  overdueCount: 3,
  collectedInPeriod: "350000.00",
  approvalsPending: 2,
}

function LocationProbe() {
  const location = useLocation()
  return <div data-testid="location">{location.pathname}{location.search}</div>
}

function renderCards() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <CommitmentDashboardCards />
        <LocationProbe />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  requestMock.mockReset()
  accessMock.mockReset()
  requestMock.mockImplementation(async (path: string) => {
    if (path.includes("/kpis/")) return KPI_PAYLOAD
    return {}
  })
})

describe("CommitmentDashboardCards", () => {
  it("is hidden for users without ol_commitments.view", () => {
    accessMock.mockReturnValue({ hasPermission: () => false, isSuperAdmin: false })
    const { container } = renderCards()
    expect(container.firstChild).not.toBeNull()
    expect(screen.queryByText("Overdue Commitments")).not.toBeInTheDocument()
  })

  it("shows counts and each deep link applies its filter", async () => {
    accessMock.mockReturnValue({ hasPermission: (code: string) => code === "ol_commitments.view", isSuperAdmin: false })
    renderCards()

    expect(await screen.findByText("TZS 650,000.00")).toBeInTheDocument()
    expect(screen.getByTestId("card-value-overdue")).toHaveTextContent("3")
    expect(screen.getByTestId("card-value-approvals")).toHaveTextContent("2")

    fireEvent.click(screen.getByTestId("card-link-overdue"))
    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("/ordinary-life/commitments?overdue_only=true"))

    fireEvent.click(screen.getByTestId("card-link-outstanding"))
    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("/ordinary-life/commitments?balance_only=true"))

    fireEvent.click(screen.getByTestId("card-link-approvals"))
    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("/ordinary-life/commitments?approval_required=true"))
  })
})
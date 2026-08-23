import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import type { ReactElement } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import {
  commitmentListKey,
  useCommitmentKPIs,
  useCommitmentList,
  useCommitmentOptions,
} from "./commitmentsHooks"

const { listCommitmentsMock, getKPIsMock, getOptionsMock } = vi.hoisted(() => ({
  listCommitmentsMock: vi.fn(),
  getKPIsMock: vi.fn(),
  getOptionsMock: vi.fn(),
}))

vi.mock("./commitments", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./commitments")>()
  return {
    ...actual,
    listCommitments: listCommitmentsMock,
    getCommitmentKPIs: getKPIsMock,
    getCommitmentOptions: getOptionsMock,
  }
})

function ListHarness({ filters }: { filters?: Parameters<typeof useCommitmentList>[0] }) {
  const list = useCommitmentList(filters)
  return (
    <div>
      <span data-testid="list-count">{list.data?.count ?? (list.isLoading ? "loading" : "none")}</span>
      <span data-testid="list-status">{list.status}</span>
    </div>
  )
}

function KPIsHarness() {
  const kpis = useCommitmentKPIs()
  return <span data-testid="kpis-overdue">{kpis.data?.overdueCount ?? (kpis.isLoading ? "loading" : "none")}</span>
}

function OptionsHarness() {
  const options = useCommitmentOptions()
  return <span data-testid="options-currencies">{(options.data?.currencies ?? []).join(",") || "loading"}</span>
}

function renderWithProviders(element: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={queryClient}>{element}</QueryClientProvider>)
}

describe("commitment query hooks", () => {
  beforeEach(() => {
    listCommitmentsMock.mockReset()
    getKPIsMock.mockReset()
    getOptionsMock.mockReset()
  })

  it("queries the list with the given filters and renders the count", async () => {
    listCommitmentsMock.mockResolvedValue({
      results: [{ id: "c1", commitment_number: "OLC-2026-00001", status: "PENDING" }],
      count: 1,
    })
    renderWithProviders(<ListHarness filters={{ status: "PENDING", pageSize: 50 }} />)
    await waitFor(() => expect(screen.getByTestId("list-count")).toHaveTextContent("1"))
    expect(listCommitmentsMock).toHaveBeenCalledWith({ status: "PENDING", pageSize: 50 })
  })

  it("keeps distinct cache keys per filter set", () => {
    expect(commitmentListKey({ status: "PENDING" })).not.toEqual(commitmentListKey({ status: "OVERDUE" }))
    expect(commitmentListKey({ status: "PENDING" })).toEqual(["commitments", "list", { status: "PENDING" }])
  })

  it("fetches KPI totals", async () => {
    getKPIsMock.mockResolvedValue({
      totalDue: "250000.00",
      totalOutstanding: "150000.00",
      overdueCount: 3,
      collectedInPeriod: "100000.00",
    })
    renderWithProviders(<KPIsHarness />)
    await waitFor(() => expect(screen.getByTestId("kpis-overdue")).toHaveTextContent("3"))
    expect(getKPIsMock).toHaveBeenCalledOnce()
  })

  it("fetches option catalogs for payment modes and currencies", async () => {
    getOptionsMock.mockResolvedValue({
      paymentModes: ["CASH", "M-PESA"],
      currencies: ["TZS", "USD"],
      statuses: [{ code: "PENDING", name: "Pending" }],
    })
    renderWithProviders(<OptionsHarness />)
    await waitFor(() => expect(screen.getByTestId("options-currencies")).toHaveTextContent("TZS,USD"))
    expect(getOptionsMock).toHaveBeenCalledOnce()
  })
})
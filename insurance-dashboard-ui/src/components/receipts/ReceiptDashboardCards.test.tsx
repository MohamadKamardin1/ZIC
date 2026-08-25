import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { ReceiptDashboardCards } from "./ReceiptDashboardCards"

const apiMocks = vi.hoisted(() => ({ kpis: vi.fn() }))
const navigateMock = vi.hoisted(() => vi.fn())
const accessMock = vi.hoisted(() => vi.fn())

vi.mock("../../lib/receipts-api", () => ({ receiptsApi: { kpis: apiMocks.kpis } }))
vi.mock("../../lib/access", () => ({ useAccess: accessMock }))
vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>()
  return { ...actual, useNavigate: () => navigateMock }
})

function renderCards() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}><MemoryRouter><ReceiptDashboardCards /></MemoryRouter></QueryClientProvider>)
}

beforeEach(() => {
  vi.clearAllMocks()
  accessMock.mockReturnValue({ isSuperAdmin: false, hasPermission: (code: string) => code === "front_office.receipts.view" })
  apiMocks.kpis.mockResolvedValue({ received_today: "150000.00", allocated_in_period: "50000.00", unallocated_amount: "100000.00", receipt_count: 7, receipts_today: 3, unallocated_receipt_count: 2, reversed_amount: "25000.00", currency: "TZS" })
})

describe("ReceiptDashboardCards Prompt 9", () => {
  it("renders server-driven receipt KPI cards and their deep links", async () => {
    renderCards()
    expect(await screen.findByText("Receipts Today")).toBeInTheDocument()
    await waitFor(() => expect(screen.getByTestId("receipt-card-value-today")).toHaveTextContent("3"))
    expect(screen.getByTestId("receipt-card-value-received")).toHaveTextContent("TZS 150,000.00")
    expect(screen.getByTestId("receipt-card-value-unallocated")).toHaveTextContent("2")
    expect(screen.getByTestId("receipt-card-value-reversed")).toHaveTextContent("TZS 25,000.00")
    fireEvent.click(screen.getByTestId("receipt-card-link-unallocated"))
    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith("/front-office/receipts?unallocated_only=true"))
    fireEvent.click(screen.getByTestId("receipt-card-link-reversed"))
    expect(navigateMock).toHaveBeenCalledWith("/front-office/receipts?reversed_only=true")
  })

  it("is hidden when the staff member lacks receipt view permission", () => {
    accessMock.mockReturnValue({ isSuperAdmin: false, hasPermission: () => false })
    const { container } = renderCards()
    expect(container.querySelector("[aria-label='Receipts oversight']")).not.toBeInTheDocument()
    expect(apiMocks.kpis).not.toHaveBeenCalled()
  })
})

import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { PartnerCommitmentDetail, PartnerCommitments, PORTAL_HELP_MESSAGE, sanitizePortalError } from "./PartnerCommitments"

const { requestMock } = vi.hoisted(() => ({ requestMock: vi.fn() }))

vi.mock("../../lib/apiClient", () => ({ request: requestMock }))

const OWN_ROWS = {
  results: [
    { id: "c-1", commitmentNumber: "OLC-2026-00001", sourceType: "POLICY", sourceReference: "POL-2026-0001", partnerName: "Zanzibar Trading Co.", productName: "Family Protection", planName: "Standard", currency: "TZS", installmentNumber: 1, installmentCount: 12, dueDate: "2026-09-01", premiumAmount: "120000.00", amountPaid: "40000.00", balance: "80000.00", status: "PARTIALLY_PAID", graceDate: "2026-10-01", lapseDate: "2026-10-16" },
  ],
  count: 1,
}

const DETAIL = {
  ...OWN_ROWS.results[0],
  allowed_actions: ["record_payment", "cancel"],
  allocations: [
    { id: "a-1", receipt_reference: "RCT-2026-001", amount: "40000.00", payment_mode: "CASH", currency: "TZS", exchange_rate: "1.000000", reversal_of: null, allocated_at: "2026-08-20T10:00:00Z" },
  ],
  notificationLogs: [],
}

function renderList() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <PartnerCommitments />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

function renderDetail() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/portal/commitments/c-1"]}>
        <Routes>
          <Route path="/portal/commitments/:id" element={<PartnerCommitmentDetail />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  requestMock.mockReset()
})

describe("PartnerCommitments (read-only list)", () => {
  it("shows only the partner-scoped commitments and the help banner, no action buttons", async () => {
    requestMock.mockImplementation(async (path: string) => {
      if (path.includes("/portal/commitments/")) return OWN_ROWS
      return {}
    })
    renderList()

    expect(await screen.findByText("OLC-2026-00001")).toBeInTheDocument()
    expect(screen.getByText(PORTAL_HELP_MESSAGE)).toBeInTheDocument()
    expect(screen.getByTestId("raise-ticket")).toHaveAttribute("href", "/tickets")
    expect(screen.queryByRole("button", { name: "Record Payment" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument()
  })

  it("sanitizes fetch errors for the portal", async () => {
    requestMock.mockImplementation(async () => {
      throw new Error("sqlite3 error near table ol_commitment_foreign_key")
    })
    renderList()

    expect(await screen.findByText(/The request could not be completed/)).toBeInTheDocument()
    expect(screen.queryByText(/sqlite3 error near table/)).not.toBeInTheDocument()
  })

  it("sanitizePortalError never leaks internal detail", () => {
    const sanitized = sanitizePortalError({ message: "SELECT * FROM ol_commitment" })
    expect(sanitized.message).toContain("contact your ZIC representative")
    expect(JSON.stringify(sanitized)).not.toContain("SELECT")
  })
})

describe("PartnerCommitmentDetail (read-only)", () => {
  it("renders overview and allocations without any action buttons", async () => {
    requestMock.mockImplementation(async (path: string) => {
      if (path.includes("/portal/commitments/c-1")) return DETAIL
      if (path.includes("/portal/commitments/")) return OWN_ROWS
      return {}
    })
    renderDetail()

    expect((await screen.findAllByText("OLC-2026-00001")).length).toBeGreaterThan(0)
    expect(screen.getByText("RCT-2026-001")).toBeInTheDocument()
    expect(screen.getByText(PORTAL_HELP_MESSAGE)).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /Record Payment/ })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /Cancel/ })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /Waive/ })).not.toBeInTheDocument()
  })
})
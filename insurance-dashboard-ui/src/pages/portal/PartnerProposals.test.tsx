import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { PartnerProposalDetail, PartnerProposals, PROPOSAL_PORTAL_HELP_MESSAGE, PortalBanner } from "./PartnerProposals"

const { requestMock, navigateMock } = vi.hoisted(() => ({ requestMock: vi.fn(), navigateMock: vi.fn() }))

vi.mock("../../lib/apiClient", () => ({
  request: requestMock,
  buildTableQuery: () => "",
}))

vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>()
  return { ...actual, useNavigate: () => navigateMock }
})

const OWN_ROWS = {
  results: [
    {
      id: "prop-uuid-0001",
      proposal_number: "OLP-2026-000042",
      policyholder: "Zanzibar Ports Ltd",
      product: "OL001 - Family Protection",
      plan: "Plan A",
      total_premium: "1250.50",
      currency: "TZS",
      status_badge: { code: "AWAITING_FIRST_PREMIUM", name: "Awaiting first premium" },
      expiry_date: "2026-09-30",
      created_at: "2026-08-01T09:00:00Z",
    },
    {
      id: "prop-other-partner",
      proposal_number: "OLP-2026-000099",
      policyholder: "Someone Else",
      product: "OL002 - Education",
      plan: "Plan B",
      total_premium: "900.00",
      currency: "TZS",
      status_badge: { code: "ENRICHMENT", name: "Enrichment" },
      expiry_date: "2026-10-30",
      created_at: "2026-08-02T09:00:00Z",
    },
  ],
  count: 1,
}

const DETAIL = {
  ...OWN_ROWS.results[0],
  quotation_number: "QT-2026-000101",
  beneficiaries: [
    { id: "ben-1", person_name: "Asha Said", share_percent: "100.0", is_primary: true },
  ],
  documents: [
    { id: "doc-1", document_type: "NATIONAL_ID", file_reference: "DMS-77", mandatory: true, status: "APPROVED", uploaded_at: "2026-08-03T08:00:00Z" },
    { id: "doc-2", document_type: "SIGNATURE_SPECIMEN", file_reference: "", mandatory: false, status: "PENDING", uploaded_at: null },
  ],
  first_premium: {
    linked: true,
    commitment_number: "CMT-2026-0044",
    status: "PARTIAL",
    amount_due: "1250.50",
    amount_paid: "500.00",
    balance: "750.50",
    first_premium_posted: false,
  },
}

function renderList() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <PartnerProposals />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

function renderDetail() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/portal/proposals/prop-uuid-0001"]}>
        <Routes>
          <Route path="/portal/proposals/:id" element={<PartnerProposalDetail />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  requestMock.mockReset()
  navigateMock.mockReset()
})

describe("PartnerProposals (read-only list)", () => {
  it("shows the partner-scoped proposals with premium and expiry and no action buttons", async () => {
    requestMock.mockImplementation(async (path: string) => {
      expect(path).toContain("/ol-proposals/proposals/portal/")
      return OWN_ROWS
    })
    renderList()

    expect(await screen.findByText("OLP-2026-000042")).toBeInTheDocument()
    expect(screen.getByTestId("portal-proposals-table")).toHaveTextContent("Family Protection")
    expect(screen.getByTestId("portal-proposals-table")).toHaveTextContent("1,250.50")
    expect(screen.getByTestId("portal-proposals-table")).toHaveTextContent("30 Sept 2026")

    // Read-only: none of the staff money/lifecycle actions may appear.
    expect(screen.queryByRole("button", { name: /Mark Payment Ready/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /Convert/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /Cancel/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /Print/i })).not.toBeInTheDocument()

    expect(screen.getByText(PROPOSAL_PORTAL_HELP_MESSAGE)).toBeInTheDocument()
    expect(screen.getByTestId("raise-ticket")).toHaveAttribute("href", "/tickets")
  })

  it("sanitizes fetch errors for the portal", async () => {
    requestMock.mockImplementation(async () => {
      throw new Error("sqlite3 error near table ol_proposal: PROPOSAL_NOT_FOUND")
    })
    renderList()

    expect(await screen.findByText(/The request could not be completed/)).toBeInTheDocument()
    expect(screen.queryByText(/sqlite3 error near table/)).not.toBeInTheDocument()
    expect(screen.queryByText(/PROPOSAL_NOT_FOUND/)).not.toBeInTheDocument()
  })

  it("renders the read-only help banner with raise-ticket shortcut", () => {
    render(
      <MemoryRouter>
        <PortalBanner />
      </MemoryRouter>,
    )
    expect(screen.getByText("For changes, contact your ZIC representative or raise a ticket.")).toBeInTheDocument()
    expect(screen.getByTestId("raise-ticket")).toHaveTextContent("Raise Ticket")
  })
})

describe("PartnerProposalDetail (read-only)", () => {
  it("renders overview, first premium status, and documents without any action buttons", async () => {
    requestMock.mockImplementation(async (path: string) => {
      if (path.includes("/proposals/portal/prop-uuid-0001")) return DETAIL
      throw new Error(`unexpected path ${path}`)
    })
    renderDetail()

    await waitFor(() => expect(screen.getByTestId("portal-proposal-detail")).toBeInTheDocument())

    // Overview section
    expect(screen.getByTestId("portal-overview")).toHaveTextContent("Zanzibar Ports Ltd")
    expect(screen.getByTestId("portal-overview")).toHaveTextContent("QT-2026-000101")

    // First premium status
    expect(screen.getByTestId("portal-first-premium")).toHaveTextContent("CMT-2026-0044")
    expect(screen.getByTestId("portal-first-premium")).toHaveTextContent("750.50")
    expect(screen.getByTestId("portal-first-premium-posted")).toHaveTextContent("Not yet")

    // Documents view
    expect(screen.getByTestId("portal-documents")).toHaveTextContent("NATIONAL_ID")
    expect(screen.getByTestId("portal-document-row-doc-2")).toHaveTextContent("SIGNATURE_SPECIMEN")
    expect(screen.getByTestId("portal-document-row-doc-2")).toHaveTextContent("Optional")

    // No actions anywhere on the page.
    expect(screen.queryByRole("button", { name: /Mark Payment Ready/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /Convert to Policy/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /Cancel Proposal/i })).not.toBeInTheDocument()
    expect(screen.queryByText(PROPOSAL_PORTAL_HELP_MESSAGE)).toBeInTheDocument()
  })

  it("shows an unlinked first premium state without commitment details", async () => {
    requestMock.mockResolvedValue({
      ...DETAIL,
      first_premium: { linked: false, first_premium_posted: false },
    })
    renderDetail()

    await waitFor(() => expect(screen.getByTestId("portal-proposal-detail")).toBeInTheDocument())
    expect(screen.getByTestId("portal-first-premium")).toHaveTextContent(
      "No first premium commitment has been raised for this proposal yet.",
    )
    expect(screen.queryByText("CMT-2026-0044")).not.toBeInTheDocument()
  })

  it("sanitizes detail errors for the portal", async () => {
    requestMock.mockImplementation(async () => {
      throw new Error("internal evaluation error: relation does not exist")
    })
    renderDetail()

    expect(await screen.findByText(/The request could not be completed/)).toBeInTheDocument()
    expect(screen.queryByText(/relation does not exist/)).not.toBeInTheDocument()
  })
})

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { ApiClientError } from "../../lib/apiClient"
import OLProposalDetail from "./OLProposalDetail"

const {
  navigateMock,
  getProposalMock,
  getHistoryMock,
  getSnapshotMock,
  markReadyMock,
  convertMock,
} = vi.hoisted(() => ({
  navigateMock: vi.fn(),
  getProposalMock: vi.fn(),
  getHistoryMock: vi.fn(),
  getSnapshotMock: vi.fn(),
  markReadyMock: vi.fn(),
  convertMock: vi.fn(),
}))

vi.mock("../../lib/proposals", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../lib/proposals")>()
  return {
    ...actual,
    getProposal: getProposalMock,
    getProposalHistory: getHistoryMock,
    getQuotationVersionSnapshot: getSnapshotMock,
    markPaymentReady: markReadyMock,
    convertToPolicy: convertMock,
  }
})

vi.mock("react-router-dom", () => ({
  useParams: () => ({ id: "prop-uuid-0001" }),
  useNavigate: () => navigateMock,
  Link: ({ children, to }: { children: React.ReactNode; to?: string }) => <a data-href={to}>{children}</a>,
}))

let grantedPermissions: string[]

vi.mock("../../lib/access", () => ({
  useAccess: () => ({
    access: {
      permissions: grantedPermissions.map((code) => {
        const [module, action] = code.split(".")
        return { module, action }
      }),
    },
    isSuperAdmin: false,
    canAccess: (module: string) => module === "ol_proposals",
  }),
}))

vi.mock("../../components/ui/Toast", () => ({
  useToast: () => ({ toast: vi.fn(), dismiss: vi.fn() }),
}))

function detailFixture(overrides: Record<string, unknown> = {}) {
  return {
    id: "prop-uuid-0001",
    proposal_number: "OLP-2026-000042",
    quotation: "quote-uuid-0009",
    quotation_number: "QT-2026-000101",
    quotation_version: 3,
    status: "ENRICHMENT",
    status_badge: { code: "ENRICHMENT", name: "Enrichment" },
    partner_name_snapshot: "Asha Said",
    agent_name_snapshot: "Juma Agent",
    employer_name_snapshot: "Zanzibar Ports Ltd",
    currency: "TZS",
    expiry_date: "2026-09-30",
    payment_ready: false,
    underwriting_status: "PENDING",
    medical_required: false,
    source_channel: "WEB",
    employment_reference: "ZPL-2231",
    payroll_deduction: true,
    intermediary_channel: "BANCASSURANCE",
    declaration_pep_flag: true,
    declaration_aml_flag: false,
    existing_policies_count: 2,
    occupation_risk_note: "Office administration role.",
    created_at: "2026-08-01T09:00:00Z",
    checklist: {
      passed: false,
      items: [
        { key: "partner_verified", passed: true },
        { key: "enrichment_complete", passed: true },
        { key: "beneficiaries_valid", passed: true },
        {
          key: "mandatory_documents_complete",
          passed: false,
          message: "Mandatory documents are missing.",
          error_code: "PROPOSAL_DOCUMENTS_INCOMPLETE",
          resolution_steps: ["Upload the missing mandatory documents."],
          deep_link: "/proposals/{id}/documents",
        },
        { key: "underwriting_cleared_or_not_required", passed: true },
        { key: "not_expired", passed: true },
        { key: "quotation_version_current", passed: true },
      ],
    },
    completeness: { missing: ["documents"], required_missing: ["documents"], complete: false },
    quotation_versions: [
      { version_number: 3, status: "FINALIZED", change_reason: "Premium recalculated after rider change.", created_at: "2026-07-28T10:00:00Z" },
      { version_number: 2, status: "DRAFT", change_reason: "Added spouse member.", created_at: "2026-07-20T08:00:00Z" },
      { version_number: 1, status: "DRAFT", change_reason: "Initial capture.", created_at: "2026-07-10T07:00:00Z" },
    ],
    plan_configs: [
      {
        id: "plan-row-uuid-1",
        plan_name_snapshot: "Twenty Year Endowment",
        base_sum_assured: "5000000.00",
        term_years: 20,
        premium_amount: "1250.50",
        is_selected: true,
      },
    ],
    members: [
      {
        id: "member-uuid-1",
        member_type: "PRINCIPAL",
        full_name_snapshot: "Asha Said",
        date_of_birth: "1985-04-12",
        age_at_quote: 41,
        gender: "FEMALE",
        smoker_status: "NON_SMOKER",
        relationship: "SELF",
        coverage_basis: "FIXED",
      },
    ],
    installment_configs: [
      {
        id: "inst-uuid-1",
        frequency: "MONTHLY",
        number_of_installments: 240,
        installment_amount: "1250.50",
        first_due_date: "2026-09-01",
        currency: "TZS",
        is_selected: true,
      },
    ],
    fund_allocations: [
      { id: "fund-uuid-1", fund_name_snapshot: "ZIC Balanced Fund", allocation_percentage: "60.00", is_selected: true },
      { id: "fund-uuid-2", fund_name_snapshot: "ZIC Growth Fund", allocation_percentage: "40.00", is_selected: true },
    ],
    riders: [
      { id: "rider-uuid-1", rider_name_snapshot: "Family Protection Benefit", premium_amount: "85.00", benefit_basis: "FIXED", benefit_value: "50000.00", is_selected: true },
    ],
    benefits: [
      { id: "benefit-uuid-1", code: "MAT", name: "Maturity Benefit", benefit_type: "MATURITY", sum_assured: "5200000.00", is_selected: true },
    ],
    beneficiaries: [
      { id: "ben-uuid-1", person_name: "Neema Said", share_percent: "100.00", is_primary: true, is_minor: false },
    ],
    documents: [
      { id: "doc-uuid-1", document_type: "NATIONAL_ID", document_type_display: "National ID", status: "APPROVED", file_reference: "docs/nid.pdf" },
    ],
    first_premium: { linked: false, first_premium_posted: false, next_actions: [] },
    allowed_actions: ["view", "enrich", "upload_documents", "mark_payment_ready", "convert", "cancel", "print"],
  }
}

function historyFixture() {
  return [
    {
      id: "evt-uuid-1",
      eventType: "ProposalCreated",
      eventTypeLabel: "Proposal Created",
      occurredAt: "2026-08-01T09:00:00Z",
      actor: "Asha Underwriter",
      fromStatus: "",
      toStatus: "Enrichment",
      reason: "Created from quotation QT-2026-000101",
      sourceChannel: "WEB",
    },
    {
      id: "evt-uuid-2",
      eventType: "ProposalEnriched",
      eventTypeLabel: "Proposal Enriched",
      occurredAt: "2026-08-05T14:30:00Z",
      actor: "Juma Agent",
      fromStatus: "Enrichment",
      toStatus: "Pending Underwriting",
      reason: "Bank details captured",
      sourceChannel: "API",
    },
  ]
}

function snapshotFixture(versionNumber: number) {
  return {
    quotationId: "quote-uuid-0009",
    quoteNumber: "QT-2026-000101",
    versionNumber,
    status: "DRAFT",
    changeReason: "Added spouse member.",
    createdAt: "2026-07-20T08:00:00Z",
    snapshot: {
      quote_number: "QT-2026-000101",
      total_sum_assured: "4800000.00",
      financial_summary: { total_premium: "1335.50", currency: "TZS", installment_frequency: "MONTHLY" },
      members: [{}, {}],
    },
  }
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <OLProposalDetail />
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  navigateMock.mockReset()
  getProposalMock.mockReset()
  getHistoryMock.mockReset()
  getSnapshotMock.mockReset()
  markReadyMock.mockReset()
  convertMock.mockReset()

  grantedPermissions = [
    "ol_proposals.view",
    "ol_proposals.enrich",
    "ol_proposals.upload_documents",
    "ol_proposals.mark_payment_ready",
    "ol_proposals.convert",
    "ol_proposals.cancel",
    "ol_proposals.print",
  ]

  getProposalMock.mockResolvedValue(detailFixture())
  getHistoryMock.mockResolvedValue(historyFixture())
  getSnapshotMock.mockImplementation(async (_quotationId: string, versionNumber: number) => snapshotFixture(versionNumber))
})

describe("OL Proposal detail page", () => {
  it("renders header and tabs from the detail payload without leaking UUIDs", async () => {
    const { container } = renderPage()

    expect(await screen.findByTestId("proposal-detail-header")).toHaveTextContent("OLP-2026-000042")
    expect(screen.getByTestId("proposal-detail-header")).toHaveTextContent("Asha Said")
    expect(screen.getByTestId("proposal-detail-header")).toHaveTextContent("Twenty Year Endowment")

    for (const tab of ["Overview", "Quotation Source", "History"]) {
      expect(screen.getByRole("button", { name: tab })).toBeInTheDocument()
    }

    expect(screen.getByTestId("tick-payment-ready-off")).toBeTruthy()
    expect(screen.getByTestId("tick-first-premium-off")).toBeTruthy()
    expect(screen.getByText("Employer: Zanzibar Ports Ltd")).toBeInTheDocument()
    expect(screen.getByTestId("declarations-summary")).toHaveTextContent("PEP declarationYes")

    // Names everywhere — no raw UUIDs anywhere in the rendered tree.
    expect(container.textContent).not.toMatch(/[0-9a-f]{8}-[0-9a-f]{4}/i)
    expect(container.textContent).not.toContain("prop-uuid-0001")

    // History tab renders the timeline with actors and state transitions.
    fireEvent.click(screen.getByRole("button", { name: "History" }))
    const timeline = await screen.findByTestId("history-timeline")
    expect(within(timeline).getByText("Proposal Created")).toBeInTheDocument()
    expect(within(timeline).getAllByText(/Asha Underwriter|Juma Agent/).length).toBeGreaterThan(0)
    expect(within(timeline).getByText(/Enrichment → Pending Underwriting/i)).toBeInTheDocument()
    expect(within(timeline).getByText(/via WEB/)).toBeInTheDocument()
  })

  it("renders the readiness panel matching backend checklist state", async () => {
    renderPage()

    await screen.findByTestId("proposal-detail-header")

    const verdict = screen.getByTestId("readiness-verdict")
    expect(verdict).toHaveTextContent("1 to resolve")
    expect(screen.getByTestId("completeness-line")).toHaveTextContent("Missing sections: documents")

    const items = document.querySelectorAll("[data-checklist-item]")
    expect(items.length).toBe(7)

    const failedItem = Array.from(items).find((item) => item.getAttribute("data-checklist-item") === "mandatory_documents_complete") as HTMLElement
    expect(failedItem.getAttribute("data-checklist-passed")).toBe("false")
    expect(failedItem).toHaveTextContent("Mandatory documents are missing.")
    expect(failedItem.querySelector('[data-testid="checklist-link-mandatory_documents_complete"]')).toBeTruthy()

    const passedItem = Array.from(items).find((item) => item.getAttribute("data-checklist-item") === "partner_verified") as HTMLElement
    expect(passedItem.getAttribute("data-checklist-passed")).toBe("true")
    expect(passedItem.querySelector("button")).toBeNull()

    expect(screen.getByTestId("panel-mark-payment-ready")).toBeInTheDocument()
  })

  it("switches to a prior quotation version and renders its read-only snapshot", async () => {
    renderPage()
    await screen.findByTestId("proposal-detail-header")

    expect(screen.getByTestId("carried-version-note")).toHaveTextContent("carries version 3")

    fireEvent.change(screen.getByTestId("snapshot-version-select"), { target: { value: "2" } })

    const panel = await screen.findByTestId("quotation-snapshot-panel")
    await waitFor(() =>
      expect(getSnapshotMock).toHaveBeenCalledWith("quote-uuid-0009", 2),
    )
    expect(screen.getByTestId("snapshot-change-reason")).toHaveTextContent("Added spouse member.")
    expect(panel).toHaveTextContent("total premium")
    expect(panel).toHaveTextContent("1335.50")
    expect(panel).toHaveTextContent("members: 2")
    expect(screen.getByText(/this proposal continues to carry version 3/i)).toBeInTheDocument()
  })

  it("marks the proposal payment ready from the readiness panel", async () => {
    markReadyMock.mockResolvedValue({ ok: true })

    renderPage()
    await screen.findByTestId("proposal-detail-header")

    fireEvent.click(screen.getByTestId("panel-mark-payment-ready"))
    await waitFor(() => expect(markReadyMock).toHaveBeenCalledWith("prop-uuid-0001"))
  })

  it("renders an ErrorCoach when the proposal fetch fails", async () => {
    getProposalMock.mockRejectedValue(
      new ApiClientError({
        status: 404,
        code: "PROPOSAL_NOT_FOUND",
        message: "The proposal could not be found.",
        fieldErrors: {},
        details: { resolution_steps: ["Verify the proposal number.", "Check the proposal register filters."] },
      }),
    )

    renderPage()

    expect(await screen.findByTestId("error-coach-code")).toHaveTextContent("PROPOSAL_NOT_FOUND")
    expect(screen.getByTestId("error-coach-steps")).toHaveTextContent("Verify the proposal number.")
  })
})

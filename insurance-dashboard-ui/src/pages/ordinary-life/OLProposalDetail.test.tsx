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
  cancelProposalMock,
  enrichMock,
  documentsListMock,
  uploadDocMock,
  addBeneficiaryMock,
  updateBeneficiaryMock,
  deleteBeneficiaryMock,
  getFirstPremiumMock,
  generatePrintMock,
  listGeneratedDocsMock,
  requestMock,
} = vi.hoisted(() => ({
  navigateMock: vi.fn(),
  getProposalMock: vi.fn(),
  getHistoryMock: vi.fn(),
  getSnapshotMock: vi.fn(),
  markReadyMock: vi.fn(),
  convertMock: vi.fn(),
  cancelProposalMock: vi.fn(),
  enrichMock: vi.fn(),
  documentsListMock: vi.fn(),
  uploadDocMock: vi.fn(),
  addBeneficiaryMock: vi.fn(),
  updateBeneficiaryMock: vi.fn(),
  deleteBeneficiaryMock: vi.fn(),
  getFirstPremiumMock: vi.fn(),
  generatePrintMock: vi.fn(),
  listGeneratedDocsMock: vi.fn(),
  requestMock: vi.fn(),
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
    cancelProposal: cancelProposalMock,
    enrichProposalSection: enrichMock,
    listProposalDocuments: documentsListMock,
    uploadProposalDocument: uploadDocMock,
    addBeneficiary: addBeneficiaryMock,
    updateBeneficiary: updateBeneficiaryMock,
    deleteBeneficiary: deleteBeneficiaryMock,
    getFirstPremiumStatus: getFirstPremiumMock,
    generateProposalPrint: generatePrintMock,
    listGeneratedDocuments: listGeneratedDocsMock,
  }
})

vi.mock("../../lib/apiClient", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../lib/apiClient")>()
  return { ...actual, request: requestMock }
})

const routerState: { params: Record<string, string | undefined>; search: string } = {
  params: { id: "prop-uuid-0001" },
  search: "",
}

vi.mock("react-router-dom", () => ({
  useParams: () => routerState.params,
  useNavigate: () => navigateMock,
  useSearchParams: () => [
    new URLSearchParams(routerState.search),
    (next: URLSearchParams) => {
      routerState.search = next.toString()
    },
  ],
  Link: ({ children, ...rest }: { children: React.ReactNode; to?: string }) => <a {...rest}>{children}</a>,
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
    bank_name: "CRDB Bank PLC",
    bank_account_name: "Asha Said",
    bank_account_number: "******8842",
    declarations_free_text: {"smoker": false},
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
      {
        id: "ben-uuid-1",
        person_name: "Neema Said",
        identity_type: "NIN",
        identity_number: "NIN-8842",
        beneficial_type_name_snapshot: "Education Benefit",
        share_percent: "60.00",
        is_primary: true,
        is_minor: false,
      },
      {
        id: "ben-uuid-2",
        person_name: "Baraka Juma",
        identity_type: "BIRTH_CERTIFICATE",
        identity_number: "BC-5531",
        beneficial_type_name_snapshot: "Survivor Benefit",
        share_percent: "20.00",
        is_primary: false,
        is_minor: true,
        guardian_name: "Halima Juma",
        guardian_relationship: "Mother",
      },
    ],
    documents: [
      { id: "doc-uuid-1", document_type: "NATIONAL_ID", document_type_display: "National ID", status: "APPROVED", file_reference: "docs/nid.pdf" },
    ],
    first_premium: { linked: false, first_premium_posted: false, next_actions: [] },
    allowed_actions: ["view", "enrich", "upload_documents", "mark_payment_ready", "convert", "cancel", "print"],
    ...overrides,
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

function routeBaseRequests(path: string) {
  if (path.includes("/ol-proposals/options/employers/")) {
    return { data: { kind: "employers", results: [{ id: "employer-partner-7", label: "Zanzibar Ports Ltd" }], count: 1 } }
  }
  if (path.includes("/ol-proposals/options/intermediaries/")) {
    return { data: { kind: "intermediaries", results: [{ id: "agent-partner-3", label: "Juma Intermediaries" }], count: 1 } }
  }
  if (path.includes("/ol-proposals/options/banks/")) {
    return { data: { kind: "banks", results: [{ id: "crdb", value: "CRDB Bank PLC", label: "CRDB Bank PLC" }, { id: "nmb", value: "NMB Bank PLC", label: "NMB Bank PLC" }], count: 2 } }
  }
  if (path.includes("/ol-proposals/options/document-types/")) {
    return {
      data: {
        kind: "document-types",
        results: [
          { id: "NATIONAL_ID", value: "NATIONAL_ID", label: "National ID" },
          { id: "SIGNATURE", value: "SIGNATURE", label: "Signature specimen" },
        ],
        count: 2,
      },
    }
  }
  if (path.includes("/api/v1/ol/options/identity-types")) {
    return { items: [{ value: "NIN", label: "National Identification Number" }, { value: "BIRTH_CERTIFICATE", label: "Birth Certificate" }] }
  }
  if (path.includes("/api/v1/ol/options/benefit-types")) {
    return { items: [{ value: "benefit-edu", label: "Education Benefit" }, { value: "benefit-survivor", label: "Survivor Benefit" }] }
  }
  if (path.includes("/health-questions/")) {
    return healthQuestionsFixture()
  }
  if (path.includes("/health-answers/")) {
    return { health_result: { triggered: false, medical_required: false, status: "ENRICHMENT", answered: 1 } }
  }
  if (path.includes("/underwriting-decision/")) {
    return { ok: true }
  }
  throw new Error(`Unhandled request in test: ${path}`)
}

function healthQuestionsFixture() {
  return {
    questionnaire: "OL-HQ-2026",
    results: [
      {
        id: "hq-uuid-1",
        sequence: 1,
        mandatory: true,
        trigger_medical_requirement: false,
        question_id: "hq-cat-1",
        question_code: "HOSPITALISED_5Y",
        question_text: "Have you been hospitalised in the last five years?",
        answer_type: "BOOLEAN",
        category: "Medical history",
        underwriting_impact: "NONE",
      },
      {
        id: "hq-uuid-2",
        sequence: 2,
        mandatory: false,
        trigger_medical_requirement: true,
        question_id: "hq-cat-2",
        question_code: "HEART_CONDITION",
        question_text: "Have you ever been diagnosed with a heart condition?",
        answer_type: "BOOLEAN",
        category: "Cardiovascular",
        underwriting_impact: "HIGH",
      },
    ],
  }
}

beforeEach(() => {
  navigateMock.mockReset()
  routerState.params = { id: "prop-uuid-0001" }
  routerState.search = ""
  getProposalMock.mockReset()
  getHistoryMock.mockReset()
  getSnapshotMock.mockReset()
  markReadyMock.mockReset()
  convertMock.mockReset()
  enrichMock.mockReset()
  documentsListMock.mockReset()
  uploadDocMock.mockReset()
  addBeneficiaryMock.mockReset()
  updateBeneficiaryMock.mockReset()
  deleteBeneficiaryMock.mockReset()
  getFirstPremiumMock.mockReset()
  generatePrintMock.mockReset()
  listGeneratedDocsMock.mockReset()
  requestMock.mockReset()

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
  enrichMock.mockResolvedValue({ data: {} })
  documentsListMock.mockResolvedValue({
    results: [
      { id: "doc-uuid-1", document_type: "NATIONAL_ID", document_type_display: "National ID", status: "UPLOADED", file_reference: "docs/nid.pdf", mandatory: true },
    ],
    count: 1,
    requirements: [
      { code: "PROPOSAL_DOC_ID", name: "National ID", document_type: "NATIONAL_ID", mandatory: true },
      { code: "PROPOSAL_DOC_SIG", name: "Signature specimen", document_type: "SIGNATURE", mandatory: true },
      { code: "PROPOSAL_DOC_BANK", name: "Bank statement", document_type: "BANK_STATEMENT", mandatory: false },
    ],
  })
  uploadDocMock.mockResolvedValue({ document_type: "NATIONAL_ID", status: "UPLOADED" })
  addBeneficiaryMock.mockResolvedValue({ data: {} })
  updateBeneficiaryMock.mockResolvedValue({ data: {} })
  deleteBeneficiaryMock.mockResolvedValue({ data: { deleted: true } })
  getFirstPremiumMock.mockResolvedValue({ linked: false, first_premium_posted: false, next_actions: [] })
  generatePrintMock.mockResolvedValue({
    documentType: "PROPOSAL_PRINT",
    status: "GENERATED",
    templateCode: "OL_PROPOSAL_PRINT",
    templateVersion: 1,
    sourceVersion: 3,
    generatedByName: "Asha Underwriter",
    generatedAt: "2026-08-20T10:00:00Z",
    pdfUrl: "/media/ol_proposals/OLP-2026-000042/print.pdf",
    htmlUrl: null,
  })
  listGeneratedDocsMock.mockResolvedValue([
    {
      id: "print-doc-uuid-1",
      documentType: "PROPOSAL_PRINT",
      status: "GENERATED",
      templateCode: "OL_PROPOSAL_PRINT",
      templateVersion: 1,
      sourceVersion: 3,
      generatedByName: "Asha Underwriter",
      generatedAt: "2026-08-20T10:00:00Z",
      pdfUrl: "/media/ol_proposals/OLP-2026-000042/print.pdf",
      htmlUrl: null,
    },
  ])

  requestMock.mockImplementation(routeBaseRequests)
})

function installRoutes(extra?: (path: string) => unknown) {
  requestMock.mockImplementation((path: string) => {
    const overridden = extra?.(path)
    if (overridden !== undefined) return overridden
    return routeBaseRequests(path)
  })
}

describe("OL Proposal detail page", () => {
  it("renders header and tabs from the detail payload without leaking UUIDs", async () => {
    const { container } = renderPage()

    expect(await screen.findByTestId("proposal-detail-header")).toHaveTextContent("OLP-2026-000042")
    expect(screen.getByTestId("proposal-detail-header")).toHaveTextContent("Asha Said")
    expect(screen.getByTestId("proposal-detail-header")).toHaveTextContent("Twenty Year Endowment")

    const tabsNav = within(screen.getByTestId("proposal-tabs"))
    for (const tab of ["Overview", "Beneficiaries", "Health & Underwriting", "Documents", "Generated Documents", "Quotation Source", "History"]) {
      expect(tabsNav.getByRole("button", { name: tab })).toBeInTheDocument()
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

  it("flips failed checklist items red with resolution steps and deep links on a 409 refusal", async () => {
    markReadyMock.mockRejectedValueOnce(
      new ApiClientError({
        status: 409,
        code: "PROPOSAL_NOT_PAYMENT_READY",
        message: "This proposal is not payment-ready; resolve each failed checklist item.",
        fieldErrors: {},
        details: {
          checklist: [
            {
              key: "mandatory_documents_complete",
              passed: false,
              error_code: "PROPOSAL_MANDATORY_DOCUMENTS_MISSING",
              message: "Signature specimen has not been uploaded.",
              resolution_steps: ["Open Documents and upload Signature specimen.", "Re-run Mark Payment Ready."],
              deep_link: "/proposals/{id}/documents",
            },
          ],
        },
      }),
    )

    renderPage()
    await screen.findByTestId("proposal-detail-header")

    fireEvent.click(screen.getByTestId("panel-mark-payment-ready"))

    // Teachable conflict note replaces the generic error coach.
    expect(await screen.findByTestId("conflict-note")).toHaveTextContent(/refused/i)

    const failedItem = document.querySelector('[data-checklist-item="mandatory_documents_complete"]') as HTMLElement
    await waitFor(() => expect(failedItem.getAttribute("data-checklist-passed")).toBe("false"))
    expect(failedItem).toHaveTextContent("Signature specimen has not been uploaded.")
    expect(failedItem).toHaveTextContent("Open Documents and upload Signature specimen.")
    expect(failedItem).toHaveTextContent("Re-run Mark Payment Ready.")

    // The deep link routes to the screen where the failure is fixed.
    fireEvent.click(within(failedItem).getByTestId("checklist-link-mandatory_documents_complete"))
    expect(navigateMock).toHaveBeenCalledWith("/ordinary-life/proposals/prop-uuid-0001/documents")
  })

  it("activates the tab carried by the :tab path segment", async () => {
    routerState.params = { id: "prop-uuid-0001", tab: "documents" }
    renderPage()

    await screen.findByTestId("proposal-detail-header")
    expect(screen.getByTestId("tab-documents")).toBeInTheDocument()
    expect(screen.queryByTestId("tab-overview")).not.toBeInTheDocument()
  })

  it("fires the row-action deep link once and strips ?action= afterwards", async () => {
    routerState.search = "?action=convert"
    renderPage()

    await screen.findByTestId("proposal-detail-header")
    expect(await screen.findByTestId("br03-summary")).toBeInTheDocument()

    const next = new URLSearchParams(routerState.search)
    expect(next.get("action")).toBeNull()
  })

  it("shows the first premium commitment with due, paid, balance and receipt hint while partially paid", async () => {
    getProposalMock.mockResolvedValue(
      detailFixture({
        status: "AWAITING_FIRST_PREMIUM",
        first_premium: {
          linked: true,
          first_premium_posted: false,
          next_actions: ["Record receipt in Front Office.", "Allocate the receipt against commitment CMT-2026-0044."],
          commitment: {
            commitment_number: "CMT-2026-0044",
            commitment_id: "cmt-uuid-1",
            status: "PARTIAL",
            amount_due: "1250.50",
            amount_paid: "500.00",
            balance: "750.50",
            currency: "TZS",
            allocations: [
              { receipt_reference: "RCP-88", amount: "500.00", payment_mode: "CASH", currency: "TZS", allocated_at: "2026-08-18T09:15:00Z" },
            ],
          },
        },
      }),
    )

    renderPage()
    await screen.findByTestId("proposal-detail-header")

    const card = document.querySelector('[data-first-premium-card="linked"]') as HTMLElement
    await waitFor(() => expect(card.getAttribute("data-posted")).toBe("false"))
    expect(card).toHaveTextContent("CMT-2026-0044")
    expect(card).toHaveTextContent("1,250.50")
    expect(card).toHaveTextContent("500.00")
    expect(card).toHaveTextContent("750.50")
    expect(within(card).getByTestId("first-premium-allocations")).toHaveTextContent("RCP-88")
    const hint = within(card).getByTestId("record-receipt-hint")
    expect(hint).toHaveTextContent("Record receipt in Front Office")
  })

  it("hides the receipt hint once the first premium is fully posted (BR-03 satisfied)", async () => {
    getProposalMock.mockResolvedValue(
      detailFixture({
        status: "AWAITING_FIRST_PREMIUM",
        payment_ready: true,
        first_premium: {
          linked: true,
          first_premium_posted: true,
          next_actions: ["Proceed to policy conversion (first premium is fully allocated)."],
          commitment: {
            commitment_number: "CMT-2026-0044",
            commitment_id: "cmt-uuid-1",
            status: "SETTLED",
            amount_due: "1250.50",
            amount_paid: "1250.50",
            balance: "0.00",
            currency: "TZS",
            allocations: [],
          },
        },
      }),
    )

    renderPage()
    await screen.findByTestId("proposal-detail-header")

    const card = document.querySelector('[data-first-premium-card="linked"]') as HTMLElement
    await waitFor(() => expect(card.getAttribute("data-posted")).toBe("true"))
    expect(screen.queryByTestId("record-receipt-hint")).not.toBeInTheDocument()
  })

  it("blocks conversion behind BR-03 with PROPOSAL_FIRST_PREMIUM_NOT_POSTED before the premium posts", async () => {
    getFirstPremiumMock.mockResolvedValue({
      linked: true,
      first_premium_posted: false,
      next_actions: ["Record receipt in Front Office."],
      commitment: {
        commitment_number: "CMT-2026-0044",
        commitment_id: "cmt-uuid-1",
        status: "PARTIAL",
        amount_due: "1250.50",
        amount_paid: "500.00",
        balance: "750.50",
        currency: "TZS",
        allocations: [],
      },
    })

    renderPage()
    await screen.findByTestId("proposal-detail-header")

    fireEvent.click(screen.getByTestId("open-convert"))

    expect(await screen.findByTestId("br03-summary")).toHaveTextContent("Not posted")
    const coach = screen.getByTestId("br03-blocked-coach")
    expect(coach).toHaveTextContent("PROPOSAL_FIRST_PREMIUM_NOT_POSTED")
    expect(coach).toHaveTextContent(/Front Office/i)
    expect(screen.getByTestId("confirm-convert")).toBeDisabled()
    expect(convertMock).not.toHaveBeenCalled()
  })

  it("issues the policy after BR-03 passes and links the issued policy number", async () => {
    getFirstPremiumMock.mockResolvedValue({
      linked: true,
      first_premium_posted: true,
      next_actions: ["Proceed to policy conversion (first premium is fully allocated)."],
      commitment: {
        commitment_number: "CMT-2026-0044",
        commitment_id: "cmt-uuid-1",
        status: "SETTLED",
        amount_due: "1250.50",
        amount_paid: "1250.50",
        balance: "0.00",
        currency: "TZS",
        allocations: [],
      },
    })
    convertMock.mockResolvedValue({ proposal_number: "OLP-2026-000042", status: "CONVERTED", policy_number: "OLP-POL-2026-0077", converted_policy: "pol-uuid-77", created: true })
    getProposalMock.mockResolvedValueOnce(detailFixture()).mockResolvedValue(
      detailFixture({ status: "CONVERTED", reason_code: "CONVERTED", reason_text: "Converted to policy OLP-POL-2026-0077.", allowed_actions: ["view", "print"] }),
    )

    renderPage()
    await screen.findByTestId("proposal-detail-header")

    fireEvent.click(screen.getByTestId("open-convert"))
    await waitFor(() => expect(screen.getByTestId("br03-summary")).toHaveTextContent("Posted"))

    fireEvent.click(screen.getByTestId("confirm-convert"))
    await waitFor(() => expect(convertMock).toHaveBeenCalledWith("prop-uuid-0001"))

    const policyLink = await screen.findByTestId("policy-number-link")
    expect(policyLink).toHaveTextContent("OLP-POL-2026-0077")

    // Lifecycle banner confirms conversion after the detail refresh.
    expect(await screen.findByTestId("converted-banner")).toHaveTextContent("Converted to policy OLP-POL-2026-0077")
  })

  it("cancels through the reason + danger confirm flow and shows the cancellation banner", async () => {
    cancelProposalMock.mockResolvedValue({ data: {} })
    getProposalMock.mockResolvedValueOnce(detailFixture()).mockResolvedValue(
      detailFixture({ status: "CANCELLED", reason_code: "CUSTOMER_REQUEST", reason_text: "Customer withdrew the application.", allowed_actions: ["view"] }),
    )

    renderPage()
    await screen.findByTestId("proposal-detail-header")

    fireEvent.click(screen.getByTestId("open-cancel"))

    const continueButton = screen.getByTestId("cancel-continue") as HTMLButtonElement
    expect(continueButton).toBeDisabled()

    fireEvent.change(screen.getByLabelText(/Cancellation reason/), { target: { value: "Customer withdrew the application." } })
    fireEvent.click(continueButton)

    // Danger confirm restates the reason before anything is sent.
    expect(screen.getByText(/Cancel this proposal\?/)).toBeInTheDocument()
    expect(screen.getByText(/Customer withdrew the application\./)).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Yes — cancel proposal" }))

    await waitFor(() => expect(cancelProposalMock).toHaveBeenCalledWith("prop-uuid-0001", "Customer withdrew the application."))
    expect(await screen.findByTestId("cancelled-banner")).toHaveTextContent("Customer withdrew the application.")
  })

  it("previews the printout with a PDF download and lists generated documents with template metadata", async () => {
    renderPage()
    await screen.findByTestId("proposal-detail-header")

    fireEvent.click(screen.getByTestId("open-print"))

    const metadata = await screen.findByTestId("print-metadata")
    expect(metadata).toHaveTextContent("PROPOSAL_PRINT")
    expect(metadata).toHaveTextContent("OL_PROPOSAL_PRINT")
    expect(metadata).toHaveTextContent("v1")
    const download = screen.getByTestId("print-download-pdf") as HTMLAnchorElement
    expect(download.getAttribute("download")).toBe("proposal-prop-uuid-0001.pdf")

    fireEvent.click(within(screen.getByTestId("proposal-tabs")).getByRole("button", { name: "Generated Documents" }))
    const panel = await screen.findByTestId("tab-generated")
    expect(await within(panel).findByTestId("generated-counts")).toHaveTextContent("1 printout")
    const row = await within(panel).findByTestId("generated-row-print-doc-uuid-1")
    expect(row).toHaveTextContent("v1")
    expect(row).toHaveTextContent("Asha Underwriter")
    expect(row).toHaveTextContent("v3")
    expect(row).toHaveTextContent("PDF")
    expect(generatePrintMock).toHaveBeenCalledWith("prop-uuid-0001")
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

  it("saves the employer enrichment section with the selected corporate partner", async () => {
    renderPage()
    await screen.findByTestId("proposal-detail-header")

    fireEvent.click(screen.getByTestId("open-enrichment"))
    const section = await screen.findByTestId("enrich-section-employer")

    const referenceInput = within(section).getByLabelText(/Employment reference/) as HTMLInputElement
    expect(referenceInput.value).toBe("ZPL-2231")
    fireEvent.change(referenceInput, { target: { value: "ZPL-9988" } })

    fireEvent.click(document.getElementById("enrich_employer_partner") as HTMLElement)
    fireEvent.click(await screen.findByRole("option", { name: "Zanzibar Ports Ltd" }))

    fireEvent.click(screen.getByTestId("enrich-save-employer"))

    await waitFor(() =>
      expect(enrichMock).toHaveBeenCalledWith("prop-uuid-0001", "employer", {
        employer_partner: "employer-partner-7",
        employment_reference: "ZPL-9988",
        payroll_deduction: true,
      }),
    )
  })

  it("only sends the bank account number when a replacement value is typed", async () => {
    renderPage()
    await screen.findByTestId("proposal-detail-header")

    fireEvent.click(screen.getByTestId("open-enrichment"))
    await screen.findByTestId("enrich-section-bank")

    // Save without touching the masked number — it must not be overwritten.
    fireEvent.click(screen.getByTestId("enrich-save-bank_details"))
    await waitFor(() => expect(enrichMock).toHaveBeenCalledTimes(1))
    const [, , firstPayload] = enrichMock.mock.calls[0]
    expect(firstPayload.bank_name).toBe("CRDB Bank PLC")
    expect(firstPayload.bank_account_name).toBe("Asha Said")
    expect(firstPayload).not.toHaveProperty("bank_account_number")

    fireEvent.change(document.getElementById("enrich_bank_account_number") as HTMLInputElement, {
      target: { value: "9988776655" },
    })
    fireEvent.click(screen.getByTestId("enrich-save-bank_details"))
    await waitFor(() => expect(enrichMock).toHaveBeenCalledTimes(2))
    const [, , secondPayload] = enrichMock.mock.calls[1]
    expect(secondPayload.bank_account_number).toBe("9988776655")
  })

  it("blocks saving declarations with invalid JSON and shows a validation message", async () => {
    renderPage()
    await screen.findByTestId("proposal-detail-header")

    fireEvent.click(screen.getByTestId("open-enrichment"))
    await screen.findByTestId("enrich-section-declarations")

    fireEvent.change(screen.getByLabelText(/Declarations note/), { target: { value: "{not json" } })
    fireEvent.click(screen.getByTestId("enrich-save-declarations"))

    expect(await screen.findByTestId("enrich-validation-error")).toHaveTextContent(/valid JSON/i)
    expect(enrichMock).not.toHaveBeenCalled()
  })

  it("flags missing mandatory documents and uploads through the preview modal", async () => {
    renderPage()
    await screen.findByTestId("proposal-detail-header")

    fireEvent.click(within(screen.getByTestId("proposal-tabs")).getByRole("button", { name: "Documents" }))
    const panel = await screen.findByTestId("tab-documents")

    // Checklist resolves requirement names, badges, and statuses — never raw codes.
    const nationalRow = await within(panel).findByTestId("requirement-row-NATIONAL_ID")
    expect(nationalRow).toHaveTextContent("National ID")
    expect(nationalRow).toHaveTextContent("Mandatory")
    expect(nationalRow).toHaveTextContent("UPLOADED")
    await within(panel).findByTestId("requirement-row-SIGNATURE")
    await within(panel).findByTestId("requirement-row-BANK_STATEMENT")
    expect(within(panel).getByTestId("requirement-row-SIGNATURE")).toHaveTextContent("Not uploaded")
    expect(within(panel).getByTestId("requirement-row-BANK_STATEMENT")).toHaveTextContent("Optional")
    expect(within(panel).getByText("2/3 satisfied")).toBeInTheDocument()

    // Blocking banner lists each missing mandatory item but skips optional ones.
    const banner = await within(panel).findByTestId("mandatory-documents-banner")
    expect(banner).toHaveTextContent(/payment readiness is blocked/i)
    expect(banner).toHaveTextContent("Signature specimen")
    expect(banner).not.toHaveTextContent("Bank statement")

    // The banner chip opens the upload modal with that type preselected.
    fireEvent.click(within(banner).getByTestId("missing-document-SIGNATURE"))
    const typeTrigger = document.getElementById("upload_document_type") as HTMLElement
    await waitFor(() => expect(typeTrigger).toHaveTextContent("Signature specimen"))

    // Attach a file: preview card shows name and size before saving.
    const file = new File([new Uint8Array(2048)], "signature-scan.pdf", { type: "application/pdf" })
    fireEvent.change(screen.getByTestId("document-file-input"), { target: { files: [file] } })
    const preview = screen.getByTestId("document-preview")
    expect(preview).toHaveTextContent("signature-scan.pdf")
    expect(preview).toHaveTextContent("2.0 KB")
    expect(screen.getByLabelText(/File reference/)).toHaveValue("signature-scan.pdf")

    fireEvent.click(screen.getByTestId("upload-document"))

    await waitFor(() =>
      expect(uploadDocMock).toHaveBeenCalledWith("prop-uuid-0001", {
        document_type: "SIGNATURE",
        file_reference: "signature-scan.pdf",
      }),
    )
  })

  it("renders the health questionnaire, saves answers, and surfaces the medical trigger", async () => {
    installRoutes((path) => {
      if (path.includes("/health-answers/")) {
        return { health_result: { triggered: true, medical_required: true, status: "PENDING_UNDERWRITING", answered: 1 } }
      }
      return undefined
    })
    const pendingDetail = detailFixture({ status: "PENDING_UNDERWRITING", underwriting_status: "PENDING", medical_required: true })
    getProposalMock.mockResolvedValueOnce(detailFixture()).mockResolvedValue(pendingDetail)

    renderPage()
    await screen.findByTestId("proposal-detail-header")

    // No decision entry point while enriching — even with ol_proposals.enrich granted.
    fireEvent.click(within(screen.getByTestId("proposal-tabs")).getByRole("button", { name: "Health & Underwriting" }))
    const panel = await screen.findByTestId("tab-health")
    expect(screen.queryByTestId("open-underwriting-decision")).not.toBeInTheDocument()

    // Questionnaire renders by question text with impact context — never raw codes only.
    const heartQuestion = await within(panel).findByTestId("health-question-hq-cat-2")
    expect(heartQuestion).toHaveTextContent("Have you ever been diagnosed with a heart condition?")
    expect(heartQuestion).toHaveTextContent("Triggers medical")
    expect(heartQuestion).toHaveTextContent("High impact")

    fireEvent.change(document.getElementById("health-answer-hq-cat-2") as HTMLSelectElement, { target: { value: "Yes" } })
    fireEvent.click(screen.getByTestId("save-health-answers"))

    await waitFor(() =>
      expect(requestMock).toHaveBeenCalledWith(
        expect.stringContaining("/health-answers/"),
        expect.objectContaining({ method: "POST" }),
      )
    )
    const call = requestMock.mock.calls.find(([path]) => String(path).includes("/health-answers/"))
    const body = JSON.parse(String(call?.[1]?.body ?? "{}"))
    expect(body.answers).toEqual([{ health_question: "hq-cat-2", answer: "Yes" }])

    // Status moved to pending underwriting after invalidation: banners appear.
    expect(await screen.findByTestId("underwriting-pending-banner")).toBeInTheDocument()
    expect(await screen.findByTestId("medical-requirement-card")).toBeInTheDocument()
    expect(screen.getByTestId("open-underwriting-decision")).toBeInTheDocument()
  })

  it("requires notes for a load decision and records the loading percentage", async () => {
    getProposalMock
      .mockResolvedValueOnce(detailFixture({ status: "PENDING_UNDERWRITING", underwriting_status: "PENDING", medical_required: true }))
      .mockResolvedValue(detailFixture({ status: "PENDING_UNDERWRITING", underwriting_status: "PENDING", medical_required: true }))

    renderPage()
    await screen.findByTestId("proposal-detail-header")

    fireEvent.click(within(screen.getByTestId("proposal-tabs")).getByRole("button", { name: "Health & Underwriting" }))
    fireEvent.click(await screen.findByTestId("open-underwriting-decision"))

    const decisionSelect = document.getElementById("underwriting_decision") as HTMLSelectElement
    fireEvent.change(decisionSelect, { target: { value: "load" } })
    expect(screen.getByTestId("loading-percent-input")).toBeInTheDocument()

    // Submitting without notes is blocked inline — nothing reaches the API.
    fireEvent.click(screen.getByTestId("submit-underwriting-decision"))
    expect(await screen.findByText(/Notes are mandatory/i)).toBeInTheDocument()

    fireEvent.change(screen.getByTestId("loading-percent-input"), { target: { value: "25" } })
    fireEvent.change(screen.getByTestId("decision-notes"), { target: { value: "Elevated blood pressure readings" } })
    fireEvent.click(screen.getByTestId("submit-underwriting-decision"))

    await waitFor(() => {
      const call = requestMock.mock.calls.find(([path]) => String(path).includes("/underwriting-decision/"))
      expect(call).toBeTruthy()
      expect(JSON.parse(String(call?.[1]?.body ?? "{}"))).toEqual({
        decision: "load",
        reason: "Elevated blood pressure readings — +25% premium loading",
      })
    })
  })

  it("declines with mandatory notes and shows the terminal rejection banner", async () => {
    getProposalMock
      .mockResolvedValueOnce(detailFixture({ status: "PENDING_UNDERWRITING", underwriting_status: "PENDING", medical_required: true }))
      .mockResolvedValue(
        detailFixture({
          status: "CANCELLED",
          underwriting_status: "DECLINED",
          reason_code: "UNDERWRITING_DECLINED",
          reason_text: "BMI above acceptance threshold",
        }),
      )

    renderPage()
    await screen.findByTestId("proposal-detail-header")

    fireEvent.click(within(screen.getByTestId("proposal-tabs")).getByRole("button", { name: "Health & Underwriting" }))
    fireEvent.click(await screen.findByTestId("open-underwriting-decision"))

    const decisionSelect = document.getElementById("underwriting_decision") as HTMLSelectElement
    fireEvent.change(decisionSelect, { target: { value: "decline" } })
    expect(screen.queryByTestId("loading-percent-input")).not.toBeInTheDocument()

    fireEvent.change(screen.getByTestId("decision-notes"), { target: { value: "Declined on medical evidence." } })
    fireEvent.click(screen.getByTestId("submit-underwriting-decision"))

    await waitFor(() => {
      const call = requestMock.mock.calls.find(([path]) => String(path).includes("/underwriting-decision/"))
      expect(JSON.parse(String(call?.[1]?.body ?? "{}"))).toEqual({
        decision: "decline",
        reason: "Declined on medical evidence.",
      })
    })

    // Terminal state banner explains the decline in plain language.
    expect(await screen.findByTestId("underwriting-declined-banner")).toHaveTextContent("BMI above acceptance threshold")
    expect(screen.queryByTestId("open-underwriting-decision")).not.toBeInTheDocument()
  })

  it("keeps the share total visible and live while editing a beneficiary", async () => {
    renderPage()
    await screen.findByTestId("proposal-detail-header")

    fireEvent.click(within(screen.getByTestId("proposal-tabs")).getByRole("button", { name: "Beneficiaries" }))
    const panel = await screen.findByTestId("tab-beneficiaries")
    const headerIndicator = within(panel).getByRole("status")
    expect(headerIndicator).toHaveAttribute("data-share-total", "under")
    expect(headerIndicator).toHaveTextContent("allocate 20.00% more")

    fireEvent.click(screen.getByRole("button", { name: "Edit Neema Said" }))
    await screen.findByTestId("beneficiary-form")
    const indicator = within(screen.getByTestId("beneficiary-form")).getByRole("status")

    // Existing rows hold 20% — dropping Neema to 10% leaves the set under.
    fireEvent.change(screen.getByLabelText(/Share percent/), { target: { value: "10" } })
    expect(indicator).toHaveAttribute("data-share-total", "under")
    expect(indicator).toHaveTextContent("allocate 70.00% more")

    fireEvent.change(screen.getByLabelText(/Share percent/), { target: { value: "90" } })
    expect(indicator).toHaveAttribute("data-share-total", "over")
    expect(indicator).toHaveTextContent("reduce 10.00%")

    fireEvent.change(screen.getByLabelText(/Share percent/), { target: { value: "80" } })
    expect(indicator).toHaveAttribute("data-share-total", "valid")
    expect(indicator).toHaveTextContent("ready to save")
  })

  it("blocks an invalid share set with teachable steps, then saves at exactly 100%", async () => {
    renderPage()
    await screen.findByTestId("proposal-detail-header")

    fireEvent.click(within(screen.getByTestId("proposal-tabs")).getByRole("button", { name: "Beneficiaries" }))
    await screen.findByTestId("tab-beneficiaries")
    fireEvent.click(screen.getByTestId("add-beneficiary"))
    await screen.findByTestId("beneficiary-form")

    fireEvent.change(screen.getByLabelText(/Full name/), { target: { value: "Neema Backup" } })
    fireEvent.click(document.getElementById("beneficiary_identity_type") as HTMLElement)
    fireEvent.click(await screen.findByRole("option", { name: "National Identification Number" }))
    fireEvent.change(document.getElementById("beneficiary_identity_number") as HTMLInputElement, { target: { value: "NIN-0009" } })
    fireEvent.change(screen.getByLabelText(/Share percent/), { target: { value: "50" } })

    fireEvent.click(screen.getByTestId("save-beneficiary"))

    expect(await screen.findByTestId("error-coach-code")).toHaveTextContent("PROPOSAL_BENEFICIARY_SHARES_INVALID")
    expect(screen.getByTestId("error-coach-steps")).toHaveTextContent("total is exactly 100%")
    expect(addBeneficiaryMock).not.toHaveBeenCalled()

    fireEvent.change(screen.getByLabelText(/Share percent/), { target: { value: "20" } })
    fireEvent.click(screen.getByTestId("save-beneficiary"))

    await waitFor(() => expect(addBeneficiaryMock).toHaveBeenCalledTimes(1))
    const [, payload] = addBeneficiaryMock.mock.calls[0]
    expect(payload.person_name).toBe("Neema Backup")
    expect(payload.share_percent).toBe("20")
    expect(payload.is_minor).toBe(false)
  })

  it("requires a guardian when a beneficiary is marked minor", async () => {
    renderPage()
    await screen.findByTestId("proposal-detail-header")

    fireEvent.click(within(screen.getByTestId("proposal-tabs")).getByRole("button", { name: "Beneficiaries" }))
    await screen.findByTestId("tab-beneficiaries")
    fireEvent.click(screen.getByTestId("add-beneficiary"))
    await screen.findByTestId("beneficiary-form")

    fireEvent.change(screen.getByLabelText(/Full name/), { target: { value: "Baby Zuri" } })
    fireEvent.click(document.getElementById("beneficiary_identity_type") as HTMLElement)
    fireEvent.click(await screen.findByRole("option", { name: "Birth Certificate" }))
    fireEvent.change(document.getElementById("beneficiary_identity_number") as HTMLInputElement, { target: { value: "BC-7788" } })
    fireEvent.change(screen.getByLabelText(/Share percent/), { target: { value: "20" } })
    fireEvent.click(screen.getByRole("switch", { name: /Minor/ }))

    expect(screen.getByTestId("guardian-fields")).toBeInTheDocument()
    fireEvent.click(screen.getByTestId("save-beneficiary"))

    expect(await screen.findByText(/A guardian is required for a minor beneficiary/i)).toBeInTheDocument()
    expect(addBeneficiaryMock).not.toHaveBeenCalled()

    fireEvent.change(screen.getByLabelText(/Guardian full name/), { target: { value: "Halima Juma" } })
    fireEvent.click(screen.getByTestId("save-beneficiary"))

    await waitFor(() => expect(addBeneficiaryMock).toHaveBeenCalledTimes(1))
    const [, payload] = addBeneficiaryMock.mock.calls[0]
    expect(payload.guardian_name).toBe("Halima Juma")
    expect(payload.is_minor).toBe(true)
  })

  it("enforces at least one primary beneficiary with a teachable error", async () => {
    renderPage()
    await screen.findByTestId("proposal-detail-header")

    fireEvent.click(within(screen.getByTestId("proposal-tabs")).getByRole("button", { name: "Beneficiaries" }))
    await screen.findByTestId("tab-beneficiaries")

    // Neema is the only primary — unchecking her must be blocked.
    fireEvent.click(screen.getByRole("button", { name: "Edit Neema Said" }))
    await screen.findByTestId("beneficiary-form")
    fireEvent.click(screen.getByRole("switch", { name: /Primary beneficiary/ }))
    fireEvent.change(screen.getByLabelText(/Share percent/), { target: { value: "80" } })
    fireEvent.click(screen.getByTestId("save-beneficiary"))

    expect(await screen.findByTestId("error-coach-code")).toHaveTextContent("PROPOSAL_BENEFICIARY_SHARES_INVALID")
    expect(screen.getByTestId("error-coach-steps")).toHaveTextContent("Mark one beneficiary as primary.")
    expect(updateBeneficiaryMock).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole("switch", { name: /Primary beneficiary/ }))
    fireEvent.click(screen.getByTestId("save-beneficiary"))
    await waitFor(() => expect(updateBeneficiaryMock).toHaveBeenCalledTimes(1))
  })

  it("flags a duplicate identity inline before submitting", async () => {
    renderPage()
    await screen.findByTestId("proposal-detail-header")

    fireEvent.click(within(screen.getByTestId("proposal-tabs")).getByRole("button", { name: "Beneficiaries" }))
    await screen.findByTestId("tab-beneficiaries")
    fireEvent.click(screen.getByTestId("add-beneficiary"))
    await screen.findByTestId("beneficiary-form")

    fireEvent.change(screen.getByLabelText(/Full name/), { target: { value: "Duplicate Dan" } })
    fireEvent.click(document.getElementById("beneficiary_identity_type") as HTMLElement)
    fireEvent.click(await screen.findByRole("option", { name: "National Identification Number" }))
    fireEvent.change(document.getElementById("beneficiary_identity_number") as HTMLInputElement, { target: { value: "nin-8842" } })
    fireEvent.change(screen.getByLabelText(/Share percent/), { target: { value: "20" } })
    fireEvent.click(screen.getByTestId("save-beneficiary"))

    expect(await screen.findByText(/already exists on this proposal/i)).toBeInTheDocument()
    expect(addBeneficiaryMock).not.toHaveBeenCalled()
  })

  it("removes a beneficiary through the confirm dialog", async () => {
    renderPage()
    await screen.findByTestId("proposal-detail-header")

    fireEvent.click(within(screen.getByTestId("proposal-tabs")).getByRole("button", { name: "Beneficiaries" }))
    await screen.findByTestId("tab-beneficiaries")

    fireEvent.click(screen.getByRole("button", { name: "Remove Baraka Juma" }))
    expect(await screen.findByText(/The remaining shares must still total 100%/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Remove" }))

    await waitFor(() => expect(deleteBeneficiaryMock).toHaveBeenCalledWith("prop-uuid-0001", "ben-uuid-2"))
  })
})

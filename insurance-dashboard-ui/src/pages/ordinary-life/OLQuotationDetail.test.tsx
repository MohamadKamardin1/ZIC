import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import OLQuotationDetail from "./OLQuotationDetail"

const { requestMock, navigateMock, toastMock, fetchDocumentMock, openDocumentMock, revokeDocumentMock } = vi.hoisted(() => ({
  requestMock: vi.fn(),
  navigateMock: vi.fn(),
  toastMock: vi.fn(),
  fetchDocumentMock: vi.fn(),
  openDocumentMock: vi.fn(),
  revokeDocumentMock: vi.fn(),
}))

vi.mock("../../lib/apiClient", () => ({
  request: requestMock,
  ApiClientError: class ApiClientError extends Error {
    fieldErrors: Record<string, string[]> = {}
  },
}))

vi.mock("../../lib/documentClient", () => ({
  AuthenticatedDocumentError: class AuthenticatedDocumentError extends Error {
    requiresLogin = false
    loginUrl = "/login"
  },
  fetchAuthenticatedDocument: fetchDocumentMock,
  openAuthenticatedDocument: openDocumentMock,
  revokeAuthenticatedDocument: revokeDocumentMock,
}))

vi.mock("react-router-dom", () => ({
  useNavigate: () => navigateMock,
  useParams: () => ({ id: "quote-1" }),
}))

vi.mock("../../lib/access", () => ({
  useAccess: () => ({
    access: { permissions: [] },
    isLoading: false,
    isError: false,
    isSuperAdmin: true,
    canAccess: () => true,
  }),
}))

vi.mock("../../components/ui/Toast", () => ({
  useToast: () => ({ toast: toastMock, dismiss: vi.fn() }),
}))

const quotation = {
  id: "quote-1",
  quote_number: "Q-0001",
  quote_name: "Asha Family Protection",
  status: "DRAFT",
  currency: "TZS",
  quote_date: "2026-08-19",
  expiry_date: "2026-09-18",
  current_version_number: 1,
  partner_verified: false,
  approval_required: true,
  approval_reason: "Sum assured exceeds the configured approval threshold.",
  total_premium: "12000.00",
  total_sum_assured: "100000.00",
  identity_type: "NIN",
  identity_number: "NIN-001",
  date_of_birth: "1990-01-01",
  age_at_quote: 36,
  gender: "MALE",
  smoker_status: "NON_SMOKER",
  location: "Dar es Salaam",
  address: "Kinondoni",
  created_at: "2026-08-19T10:00:00Z",
  wizard_step_completion: {
    personal: true,
    plans: true,
    financial: false,
  },
  plan_configurations: [{ id: "config-1", plan_code: "TERM-20", plan_name: "Twenty Year Term", term_years: 20, payment_period_years: 20, premium_frequency: "ANNUAL", quote_basis: "SUM_ASSURED", estimated_maturity_value: "250000" }],
  members: [{ id: "member-1", full_name: "Asha Applicant", relation: "POLICY_HOLDER", date_of_birth: "1990-01-01", age_at_quote: 36, gender: "MALE", is_principal: true }],
  installment_configurations: [{ id: "installment-1", plan_name: "Twenty Year Term", policy_term_years: 20, payment_mode: "ANNUAL", total_number_of_installments: 1, status: "CONFIGURED", after_maturity_benefits: true }],
  fund_allocations: [],
  rider_selections: [],
  benefits: [],
}

const financial = {
  quotation_id: "quote-1",
  recalculation_required: false,
  summary: {
    base_premium: "10000",
    total_premium: "12000",
    total_loadings: "500",
    total_discounts: "0",
    total_taxes: "0",
    estimated_maturity_value: "250000",
    frequency_label: "Annual",
  },
  projections: [{ policy_year: 1, premiums_paid: "12000", estimated_bonus: "500", surrender_value: "2000", paid_up_value: "4000", estimated_maturity_value: "250000" }],
  installment_payouts: [{ sequence: 1, payout_date: "2046-08-19", description: "Maturity payout", rate_percent: "100", payout_amount: "250000" }],
}

const versions = { versions: [{ id: "version-1", version_number: 1, status: "CURRENT", created_by: "Superuser", created_at: "2026-08-19T10:00:00Z", change_reason: "Initial quotation" }] }
const unifiedDocuments = { count: 1, page: 1, page_size: 50, results: [{ id: "document-1", document_type: "OL_QUOTATION", template_name: "Ordinary Life Quotation", template_version: 1, generated_by_display: "Superuser", generated_at: "2026-08-19T10:05:00Z", page_count: 2, signed_download_url: "/api/v1/documents/instances/document-1/download/?ticket=signed-ticket" }] }

function setupRequestMock(status = "DRAFT") {
  requestMock.mockImplementation(async (path: string, options?: RequestInit) => {
    if (path === "/api/v1/ol-quotations/quotations/quote-1/" && options?.method === undefined) return { ...quotation, status }
    if (path.endsWith("/versions/")) return versions
    if (path.startsWith("/api/v1/documents/instances/?")) return unifiedDocuments
    if (path.startsWith("/api/v1/documents/render/") && options?.method === "POST") return unifiedDocuments.results[0]
    if (path.endsWith("/partner-verification/")) return { partner_exists: false, compliant: false, missing_fields: ["first_name", "surname"] }
    if (path.endsWith("/financial-details/")) return financial
    if (path.endsWith("/finalize/") && options?.method === "POST") return { ...quotation, status: "FINALIZED" }
    if (path.endsWith("/convert-to-proposal/") && options?.method === "POST") return { quotation: { ...quotation, status: "CONVERTED" }, proposal_id: "proposal-1" }
    return {}
  })
}

beforeEach(() => {
  requestMock.mockReset()
  navigateMock.mockReset()
  toastMock.mockReset()
  fetchDocumentMock.mockReset()
  openDocumentMock.mockReset()
  revokeDocumentMock.mockReset()
  fetchDocumentMock.mockResolvedValue({ objectUrl: "blob:quotation-preview", blob: new Blob(["preview"], { type: "text/html" }), contentType: "text/html" })
  setupRequestMock()
})

describe("OL quotation detail lifecycle", () => {
  it("renders the summary header and all lifecycle tabs", async () => {
    render(<OLQuotationDetail />)

    expect(await screen.findByText("Q-0001")).toBeInTheDocument()
    expect(screen.getAllByText("Asha Family Protection").length).toBeGreaterThanOrEqual(1)
    for (const label of ["Plans & Sub-Products", "Member Coverage", "Riders", "Projections", "Installment Payouts", "Quote Versions", "Documents"]) {
      expect(screen.getByRole("button", { name: label })).toBeInTheDocument()
    }
  })

  it("shows approval-required and partner verification banners", async () => {
    render(<OLQuotationDetail />)

    expect(await screen.findByRole("alert", { name: "" })).toBeInTheDocument()
    expect(screen.getByText("Approval required")).toBeInTheDocument()
    expect(screen.getByText("Partner verification pending")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Complete partner" })).toBeInTheDocument()
  })

  it("finalize action calls the finalize endpoint", async () => {
    render(<OLQuotationDetail />)
    await screen.findByText("Q-0001")

    fireEvent.click(screen.getByRole("button", { name: "Finalize quotation" }))
    expect(screen.getByRole("heading", { name: "Finalize quotation" })).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Finalize" }))

    await waitFor(() => expect(requestMock).toHaveBeenCalledWith("/api/v1/ol-quotations/quotations/quote-1/finalize/", { method: "POST" }))
  })

  it("blocks conversion and lists eligibility errors when partner verification is incomplete", async () => {
    setupRequestMock("FINALIZED")
    render(<OLQuotationDetail />)
    await screen.findByText("Q-0001")

    fireEvent.click(screen.getAllByRole("button", { name: "Convert to Proposal" })[0])

    expect(await screen.findByText("Conversion is blocked")).toBeInTheDocument()
    expect(screen.getByText(/Partner verification must be completed and compliant/)).toBeInTheDocument()
    expect(requestMock.mock.calls.some(([path, options]) => String(path).endsWith("/convert-to-proposal/") && options?.method === "POST")).toBe(false)
  })

  it("renders the versions tab and version list", async () => {
    render(<OLQuotationDetail />
    )
    await screen.findByText("Q-0001")
    fireEvent.click(screen.getByRole("button", { name: "Quote Versions" })
)

    expect(await screen.findByText("Historical quotation snapshots are preserved.")).toBeInTheDocument()
    expect(screen.getByText("Initial quotation")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "View" })).toBeInTheDocument()
  })

  it("renders generated printouts in the documents tab", async () => {
    render(<OLQuotationDetail />)
    await screen.findByText("Q-0001")
    fireEvent.click(screen.getByRole("button", { name: "Documents" }))

    expect(await screen.findByText("Ordinary Life Quotation")).toBeInTheDocument()
    expect(screen.getByText("Superuser")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Preview" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Open in new tab" })).toBeInTheDocument()
  })

  it("matches the screenshot-facing detail tabs and table headings", async () => {
    render(<OLQuotationDetail />)
    await screen.findByText("Q-0001")

    fireEvent.click(screen.getByRole("button", { name: "Plans & Sub-Products" }))
    expect(screen.getByText("Sub-Product")).toBeInTheDocument()
    expect(screen.getByRole("columnheader", { name: "Total Premium" })).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "Member Coverage" }))
    expect(screen.getByText("Coverage %")).toBeInTheDocument()
    expect(screen.getByText("Basic Premium")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "Riders" }))
    expect(screen.getByText("Rider Benefit")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "Projections" }))
    expect(screen.getByText("Adjusted Basic")).toBeInTheDocument()
    expect(screen.getByText("Net Premium")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "Installment Payouts" }))
    expect(screen.getByText("Installment Rate")).toBeInTheDocument()
    expect(screen.getByText("Paid Up Rate")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "Quote Versions" }))
    expect(screen.getByText("Gross Premium")).toBeInTheDocument()
    expect(screen.getByText("Current View")).toBeInTheDocument()
  })

  it("routes the quote print action to the authenticated documents tab", async () => {
    setupRequestMock("FINALIZED")
    render(<OLQuotationDetail />)
    await screen.findByText("Q-0001")
    fireEvent.click(screen.getByRole("button", { name: "Print Quote" }))

    expect(await screen.findByRole("heading", { name: "Quotation documents" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Generate quotation PDF" })).toBeInTheDocument()
    expect(fetchDocumentMock).not.toHaveBeenCalled()
  })
})

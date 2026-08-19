import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import OLQuotationDetail from "./OLQuotationDetail"

const { requestMock, navigateMock, toastMock } = vi.hoisted(() => ({
  requestMock: vi.fn(),
  navigateMock: vi.fn(),
  toastMock: vi.fn(),
}))

vi.mock("../../lib/apiClient", () => ({
  request: requestMock,
  ApiClientError: class ApiClientError extends Error {
    fieldErrors: Record<string, string[]> = {}
  },
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
const documents = [{ id: "document-1", source_version_number: 1, template_code: "OL_QUOTATION", template_version: "3", document_type: "Quotation PDF", status: "GENERATED", generated_at: "2026-08-19T10:05:00Z", pdf_url: "/media/quotation.pdf" }]

function setupRequestMock(status = "DRAFT") {
  requestMock.mockImplementation(async (path: string, options?: RequestInit) => {
    if (path === "/api/v1/ol-quotations/quotations/quote-1/" && options?.method === undefined) return { ...quotation, status }
    if (path.endsWith("/versions/")) return versions
    if (path.endsWith("/documents/")) return documents
    if (path.endsWith("/partner-verification/")) return { partner_exists: false, compliant: false, missing_fields: ["first_name", "surname"] }
    if (path.endsWith("/financial-details/")) return financial
    if (path.endsWith("/finalize/") && options?.method === "POST") return { ...quotation, status: "FINALIZED" }
    if (path.endsWith("/print/") && options?.method === "POST") return documents[0]
    if (path.endsWith("/convert-to-proposal/") && options?.method === "POST") return { quotation: { ...quotation, status: "CONVERTED" }, proposal_id: "proposal-1" }
    return {}
  })
}

beforeEach(() => {
  requestMock.mockReset()
  navigateMock.mockReset()
  toastMock.mockReset()
  setupRequestMock()
})

describe("OL quotation detail lifecycle", () => {
  it("renders the summary header and all lifecycle tabs", async () => {
    render(<OLQuotationDetail />)

    expect(await screen.findByText("Q-0001")).toBeInTheDocument()
    expect(screen.getByText("Asha Family Protection")).toBeInTheDocument()
    for (const label of ["Overview", "Plans", "Members", "Installments", "Funds", "Riders & Benefits", "Financials", "Versions", "Documents"]) {
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
    fireEvent.click(screen.getByRole("button", { name: "Versions" }))

    expect(await screen.findByText("Historical snapshots are retained under BR-02.")).toBeInTheDocument()
    expect(screen.getByText("Initial quotation")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "View" })).toBeInTheDocument()
  })

  it("renders generated printouts in the documents tab", async () => {
    render(<OLQuotationDetail />)
    await screen.findByText("Q-0001")
    fireEvent.click(screen.getByRole("button", { name: "Documents" }))

    expect(await screen.findByText("OL_QUOTATION")).toBeInTheDocument()
    expect(screen.getByText("Quotation PDF")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Preview" })).toBeInTheDocument()
  })
})

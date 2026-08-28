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
  fund_allocations: [{ id: "fund-1", fund_name: "ZIC Balanced Fund", fund_type: "Balanced", risk_profile: "MEDIUM", currency: "TZS", allocation_percent: "100", allocated_amount: "12000" }],
  rider_selections: [{ id: "rider-1", rider_name: "Family Income Rider", plan_name: "Twenty Year Term", sub_product_name: "Family protection", rider_benefit: "50000", benefit_basis: "FIXED" }],
  benefits: [{ id: "benefit-1", benefit_type: "Death benefit", basis: "FIXED", value: "50000" }],
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
    if (path.endsWith("/plan-details/")) return { configurations: quotation.plan_configurations, selected_plan_count: 1, wizard_step_complete: true }
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
    for (const label of ["Plans & Sub-Products", "Member Coverage", "Investment Funds", "Riders", "Projections", "Installment Payouts", "Quote Versions", "Documents"]) {
      expect(screen.getByRole("button", { name: label })).toBeInTheDocument()
    }
  })

  it("hydrates the quotation header and every populated detail tab", async () => {
    render(<OLQuotationDetail />)
    expect((await screen.findAllByText("Asha Family Protection")).length).toBeGreaterThanOrEqual(2)
    expect(screen.getByText("NIN-001")).toBeInTheDocument()
    expect(screen.getByText("Dar es Salaam")).toBeInTheDocument()
    expect(screen.getAllByText("TZS 12,000.00").length).toBeGreaterThanOrEqual(1)

    fireEvent.click(screen.getByRole("button", { name: "Plans & Sub-Products" }))
    expect(screen.getByText("Twenty Year Term")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Member Coverage" }))
    expect(screen.getByText("Asha Applicant")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Installment Payouts" }))
    expect(screen.getByText("Maturity payout")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Projections" }))
    expect(screen.getByText(/250,000\.00/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Quote Versions" }))
    expect(screen.getByText("Q-0001")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Documents" }))
    expect(await screen.findByText("Ordinary Life Quotation")).toBeInTheDocument()
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

    fireEvent.click(screen.getByRole("button", { name: "Investment Funds" }))
    expect(screen.getByText("ZIC Balanced Fund")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "Riders" }))
    expect(screen.getByText("Rider Benefit")).toBeInTheDocument()
    expect(screen.getByText("Family Income Rider")).toBeInTheDocument()

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

  it("populates the Sum Assured KPI from plan configuration when no financial data exists", async () => {
    const bareDraft = {
      ...quotation,
      status: "DRAFT",
      total_premium: null,
      total_sum_assured: null,
      financial_summary: null,
      plan_configurations: [{ ...(quotation.plan_configurations[0] ?? {}), base_sum_assured: "100000.00", premium_amount: null }],
    }
    requestMock.mockImplementation(async (path: string, options?: RequestInit) => {
      if (path === "/api/v1/ol-quotations/quotations/quote-1/" && options?.method === undefined) return bareDraft
      if (path.endsWith("/financial-details/")) return { quotation_id: "quote-1", recalculation_required: true, summary: null }
      if (path.endsWith("/plan-details/")) return { configurations: bareDraft.plan_configurations, selected_plan_count: 1 }
      if (path.endsWith("/versions/")) return versions
      if (path.startsWith("/api/v1/documents/instances/?")) return unifiedDocuments
      return {}
    })
    render(<OLQuotationDetail />)
    expect((await screen.findAllByText("Q-0001")).length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("TZS 100,000.00").length).toBeGreaterThanOrEqual(1)
  })

  it("renders a camelCase backend payload in the summary card instead of empty fields and a raw plan UUID", async () => {
    const camelCasePayload = {
      id: "quote-1",
      quoteNumber: "OLQ-2026-000002",
      quoteName: "ZIC Complete OL Quotation Seed",
      quoteDate: "2026-08-27",
      status: "FINALIZED",
      currency: "TZS",
      gender: "MALE",
      location: "Jambiani, Unguja South, Zanzibar",
      address: "Mizingani Road, Stone Town, Zanzibar",
      identityType: "NIN",
      identityNumber: "NIN-1985-0615-001",
      dateOfBirth: "1995-06-15",
      ageAtQuote: 31,
      smokerStatus: "NON_SMOKER",
      currentVersionNumber: 3,
      expiryDate: "2026-09-26",
      totalPremium: "8501.50",
      totalSumAssured: "5000000.00",
      wizardStepCompletion: { "1PersonalDetails": true, "2PlanAndSubProducts": true, "3MemberCoverage": true, "4Installments": true, "5InvestmentFunds": true, "6RidersAndBenefits": true, "7FinancialDetails": true },
      planConfigurations: [{
        id: "config-1",
        plan: "0dc4b733-406f-4805-8279-579e3b6d4362",
        planDisplay: "OL_EDU_GROWTH — Elimu Bora Growth Plan",
        subProductCode: "BASE",
        baseSumAssured: "5000000.00",
        termYears: 20,
        paymentPeriodYears: 5,
        premiumFrequency: "MONTHLY",
        premiumAmount: "6001.50",
      }],
      members: [{ id: "member-1", memberType: "LIFE_ASSURED", firstName: "Asha", lastName: "Applicant", relationship: "POLICY_HOLDER", ageAtQuote: 36, gender: "MALE" }],
      beneficiaries: [
        { id: "b1", firstName: "CoderX", lastName: "Sultan", percentage: "60" },
        { id: "b2", firstName: "Furaha", lastName: "Joseph", percentage: "40" },
      ],
    }
    requestMock.mockImplementation(async (path: string, options?: RequestInit) => {
      if (path === "/api/v1/ol-quotations/quotations/quote-1/" && options?.method === undefined) return camelCasePayload
      if (path.endsWith("/financial-details/")) return { quotationId: "quote-1", recalculationRequired: false, summary: { totalPremium: "8501.50", totalSumAssured: "5000000.00", basePremium: "6001.50", estimatedMaturityValue: "5000000.00" } }
      if (path.endsWith("/plan-details/")) return { configurations: camelCasePayload.planConfigurations, selectedPlanCount: 1 }
      if (path.endsWith("/versions/")) return { versions: [{ id: "v-1", versionNumber: 3, status: "CURRENT", changeReason: "Initial quotation", createdAt: "2026-08-27T10:00:00Z" }] }
      return {}
    })
    render(<OLQuotationDetail />)

    expect((await screen.findAllByText("ZIC Complete OL Quotation Seed")).length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText("OLQ-2026-000002")).toBeInTheDocument()
    expect(screen.getByText("NIN-1985-0615-001")).toBeInTheDocument()
    expect(screen.getByText("OL_EDU_GROWTH — Elimu Bora Growth Plan")).toBeInTheDocument()
    expect(screen.queryByText("0dc4b733-406f-4805-8279-579e3b6d4362")).not.toBeInTheDocument()
    expect(screen.getByText("20 years")).toBeInTheDocument()
    expect(screen.getByText("MONTHLY")).toBeInTheDocument()
  })

  it("shows KPI cards from each quotation's own financial details, not a shared default", async () => {
    const draftPayload = {
      id: "quote-1",
      quote_number: "OLQ-2026-000001",
      quote_name: "my new quote",
      status: "DRAFT",
      currency: "TZS",
      financial_summary: { total_sum_assured: "5000000.00", base_premium: "6000.00", total_rider_premium: "1000.00", total_premium: "7001.50" },
      plan_configurations: [{ id: "config-1", plan_name: "Elimu Bora Growth Plan", base_sum_assured: "5000000.00", premium_amount: "6001.50", term_years: 20 }],
      members: [{ id: "member-1", full_name: "Asha Applicant", is_principal: true }],
    }
    requestMock.mockImplementation(async (path: string, options?: RequestInit) => {
      if (path === "/api/v1/ol-quotations/quotations/quote-1/" && options?.method === undefined) return draftPayload
      if (path.endsWith("/financial-details/")) return { quotation_id: "quote-1", recalculation_required: true, total_sum_assured: "5000000.00", base_premium: "6000.00", total_rider_premium: "1000.00", total_premium: "7001.50" }
      if (path.endsWith("/plan-details/")) return { configurations: draftPayload.plan_configurations, selected_plan_count: 1 }
      if (path.endsWith("/versions/")) return versions
      if (path.startsWith("/api/v1/documents/instances/?")) return unifiedDocuments
      return {}
    })
    render(<OLQuotationDetail />)
    expect(await screen.findByText("OLQ-2026-000001")).toBeInTheDocument()
    expect(screen.getAllByText("TZS 7,001.50").length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText("TZS 1,000.00")).toBeInTheDocument()
    expect(screen.queryByText("TZS 8,501.50")).not.toBeInTheDocument()
  })

  it("shows a short summary card and reveals the full summary in a modal", async () => {
    render(<OLQuotationDetail />)
    await screen.findByText("Q-0001")

    expect(screen.getByText("Twenty Year Term")).toBeInTheDocument()
    expect(screen.getByText("20 years")).toBeInTheDocument()
    expect(screen.getByText("1 (0 life assured)")).toBeInTheDocument()
    expect(screen.queryByText("Kinondoni")).not.toBeInTheDocument()
    expect(screen.queryByText("Fund Allocations")).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: /Show full summary/ }))

    expect(screen.getByRole("heading", { name: "Full quotation summary" })).toBeInTheDocument()
    expect(screen.getByText("Kinondoni")).toBeInTheDocument()
    expect(screen.getByText("Fund Allocations")).toBeInTheDocument()
    expect(screen.getByText("1 allocation: 100%")).toBeInTheDocument()
  })
})

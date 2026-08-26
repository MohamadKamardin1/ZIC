import { fireEvent, render, screen } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { PortalPolicies, PortalPolicyDetail } from "./PortalPolicies"

const { navigateMock, usePortalPoliciesMock, usePortalPolicyMock, usePortalPolicyDocumentsMock } = vi.hoisted(() => ({
  navigateMock: vi.fn(),
  usePortalPoliciesMock: vi.fn(),
  usePortalPolicyMock: vi.fn(),
  usePortalPolicyDocumentsMock: vi.fn(),
}))

vi.mock("react-router-dom", () => ({
  Link: ({ children, to, ...props }: { children: React.ReactNode; to: string; [key: string]: unknown }) => <a href={to} {...props}>{children}</a>,
  useNavigate: () => navigateMock,
  useParams: () => ({ id: "policy-1" }),
}))
vi.mock("../../lib/policyPortalHooks", () => ({
  usePortalPolicies: usePortalPoliciesMock,
  usePortalPolicy: usePortalPolicyMock,
  usePortalPolicyDocuments: usePortalPolicyDocumentsMock,
}))

afterEach(() => vi.clearAllMocks())

const policy = { id: "policy-1", policyNumber: "ZIC-OL-2026-000001", status: "ACTIVE", productPlanDisplay: "OL_EDU_GROWTH — Elimu Bora Growth Plan", riskCommencementDate: "2026-01-15", maturityDate: "2041-01-15", currency: "TZS", sumAssured: "25000000.00", premiumAmount: "120000.00", premiumFrequency: "MONTHLY" }

beforeEach(() => {
  usePortalPoliciesMock.mockReturnValue({ data: { count: 1, results: [policy] }, isLoading: false, isError: false })
  usePortalPolicyMock.mockReturnValue({ data: policy, isLoading: false, isError: false })
  usePortalPolicyDocumentsMock.mockReturnValue({ data: [{ id: "document-1", documentType: "POLICY_CONTRACT", templateName: "Policy Contract", templateVersion: "2", generatedByDisplay: "ZIC Admin", generatedAt: "2026-08-26T10:00:00Z", pageCount: 2 }], isLoading: false, isError: false })
})

describe("Partner policy portal", () => {
  it("renders a partner-scoped list and opens read-only detail", () => {
    render(<PortalPolicies />)
    expect(screen.getByRole("heading", { name: "My Policies" })).toBeInTheDocument()
    expect(screen.getByText("Contact agent for changes.")).toBeInTheDocument()
    expect(screen.getByText("ZIC-OL-2026-000001")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /Endorse|Loan|Surrender|Cancel/ })).not.toBeInTheDocument()
    fireEvent.click(screen.getByTestId("portal-policy-row-policy-1"))
    expect(navigateMock).toHaveBeenCalledWith("/portal/policies/policy-1")
  })

  it("renders overview, members, and document metadata without staff actions", () => {
    render(<PortalPolicyDetail />)
    expect(screen.getByTestId("portal-policy-overview")).toHaveTextContent("OL_EDU_GROWTH — Elimu Bora Growth Plan")
    expect(screen.getByTestId("portal-policy-members")).toHaveTextContent("Members")
    expect(screen.getByTestId("portal-policy-documents")).toHaveTextContent("Policy Contract")
    expect(screen.getByText("Contact agent for changes.")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /Endorse|Loan|Surrender|Cancel/ })).not.toBeInTheDocument()
  })
})

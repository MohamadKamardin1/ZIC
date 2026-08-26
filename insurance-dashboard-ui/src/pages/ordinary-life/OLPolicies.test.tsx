import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import OLPolicies from "./OLPolicies"
import { UUID_RE } from "../../lib/display"

const { listPoliciesMock, usePolicyKpisMock, usePolicyOptionsMock, navigateMock } = vi.hoisted(() => ({
  listPoliciesMock: vi.fn(),
  usePolicyKpisMock: vi.fn(),
  usePolicyOptionsMock: vi.fn(),
  navigateMock: vi.fn(),
}))

vi.mock("react-router-dom", () => ({ useNavigate: () => navigateMock }))
vi.mock("../../lib/access", () => ({
  useAccess: () => ({
    access: { permissions: [
      { module: "ol_policies", action: "view" },
      { module: "ol_policies", action: "endorse" },
      { module: "ol_policies", action: "print" },
    ] },
    hasPermission: (code: string) => code !== "ol_policies.cancel",
    isSuperAdmin: false,
  }),
}))
vi.mock("../../lib/policiesHooks", () => ({
  usePolicyKpis: usePolicyKpisMock,
  usePolicyOptions: usePolicyOptionsMock,
}))
vi.mock("../../lib/policies", async () => {
  const actual = await vi.importActual<typeof import("../../lib/policies")>("../../lib/policies")
  return { ...actual, listPolicies: listPoliciesMock }
})

const activeRow = {
  id: "policy-active-1",
  policyNumber: "ZIC-OL-2026-000001",
  policyholderDisplay: "P-000018 — Amani Salum",
  policyholderName: "Amani Salum",
  productPlanDisplay: "OL_EDU_GROWTH — Elimu Bora Growth Plan",
  agentDisplay: "AG-0004 — Faraja Intermediaries",
  currency: "TZS",
  sumAssured: "25000000.00",
  premiumAmount: "120000.00",
  premiumFrequency: "MONTHLY",
  riskCommencementDate: "2026-01-15",
  maturityDate: "2041-01-15",
  status: "ACTIVE",
  statusDisplay: "Active",
  allowedActions: ["view", "endorse", "print", "cancel"],
  version: 1,
}

const cancelledRow = {
  ...activeRow,
  id: "policy-cancelled-1",
  policyNumber: "ZIC-OL-2026-000003",
  policyholderDisplay: "P-000020 — Fatma Ali",
  policyholderName: "Fatma Ali",
  status: "CANCELLED",
  statusDisplay: "Cancelled",
  allowedActions: ["view", "print"],
}

beforeEach(() => {
  listPoliciesMock.mockReset().mockResolvedValue({ results: [activeRow, cancelledRow], count: 2, page: 1, pageSize: 20 })
  navigateMock.mockReset()
  usePolicyKpisMock.mockReset().mockReturnValue({ data: { totalActivePolicies: 2, totalSumAssured: "65000000.00", newPoliciesThisMonth: 3, lapsedPoliciesCount: 1, lapsedPoliciesValue: "40000000.00", maturingSoonCount: 1, currency: "TZS", sumAssuredByCurrency: { TZS: "65000000.00" } }, isPending: false, isError: false, error: null, refetch: vi.fn() })
  usePolicyOptionsMock.mockImplementation((entity: string) => ({ data: {
    statuses: [{ value: "ACTIVE", label: "Active" }, { value: "CANCELLED", label: "Cancelled" }],
    products: [{ value: "product-edu", label: "OL_EDU_GROWTH — Elimu Bora Growth Plan" }],
    agents: [{ value: "agent-4", label: "AG-0004 — Faraja Intermediaries" }],
    branches: [{ value: "branch-zanzibar", label: "Zanzibar Main Branch" }],
  }[entity] ?? [], isPending: false, isError: false }))
})

describe("OL Policies register", () => {
  it("renders all five KPI cards and table rows with human-readable fields", async () => {
    const { container } = render(<OLPolicies />)
    expect(await screen.findByText("ZIC-OL-2026-000001")).toBeInTheDocument()
    expect(screen.getByText("Total active policies")).toBeInTheDocument()
    expect(screen.getAllByText("Sum assured").length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText("New policies")).toBeInTheDocument()
    expect(screen.getByText("Lapsed policies")).toBeInTheDocument()
    expect(screen.getByText("Maturing soon")).toBeInTheDocument()
    expect(screen.getByText("P-000018 — Amani Salum")).toBeInTheDocument()
    expect(screen.getAllByText("OL_EDU_GROWTH — Elimu Bora Growth Plan").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("AG-0004 — Faraja Intermediaries").length).toBeGreaterThanOrEqual(1)
    expect(UUID_RE.test(container.textContent ?? "")).toBe(false)
  })

  it("gates row actions by backend allowed_actions and operator permissions", async () => {
    render(<OLPolicies />)
    await screen.findByText("ZIC-OL-2026-000001")
    const rows = screen.getAllByRole("row")
    fireEvent.click(within(rows[1]).getByRole("button", { name: "Actions for row 1" }))
    expect(screen.getByRole("button", { name: "View" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Endorse" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Print" })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument()
    fireEvent.click(within(rows[2]).getByRole("button", { name: "Actions for row 2" }))
    expect(screen.getByRole("button", { name: "Print" })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Endorse" })).not.toBeInTheDocument()
  })

  it("forwards search and filter changes to the list and KPI queries", async () => {
    render(<OLPolicies />)
    await screen.findByText("ZIC-OL-2026-000001")
    fireEvent.change(screen.getByLabelText("Search"), { target: { value: "Amani" } })
    fireEvent.change(screen.getByLabelText("Status"), { target: { value: "ACTIVE" } })

    await waitFor(() => {
      expect(listPoliciesMock.mock.calls.some(([params]) => params.search === "Amani" && params.status === "ACTIVE")).toBe(true)
      expect(usePolicyKpisMock.mock.calls.some(([params]) => params.status === "ACTIVE")).toBe(true)
    })
  })

  it("navigates to issuance and policy detail from the register", async () => {
    render(<OLPolicies />)
    await screen.findByText("ZIC-OL-2026-000001")
    fireEvent.click(screen.getByRole("button", { name: "New policy" }))
    expect(navigateMock).toHaveBeenCalledWith("/ordinary-life/policies/new")
    fireEvent.click(screen.getByRole("button", { name: "Actions for row 1" }))
    fireEvent.click(screen.getByRole("button", { name: "View" }))
    expect(navigateMock).toHaveBeenCalledWith("/ordinary-life/policies/policy-active-1")
  })
})

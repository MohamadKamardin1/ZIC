import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import OLPolicySetup from "./OLPolicySetup"
import { request } from "../../lib/apiClient"
import { useAccess } from "../../lib/access"
import { useToast } from "../../components/ui/Toast"

vi.mock("../../lib/apiClient", async () => {
  const actual = await vi.importActual<typeof import("../../lib/apiClient")>("../../lib/apiClient")
  return { ...actual, request: vi.fn() }
})
vi.mock("../../lib/access", () => ({ useAccess: vi.fn() }))
vi.mock("../../components/ui/Toast", () => ({ useToast: vi.fn() }))

const requestMock = vi.mocked(request)
const useAccessMock = vi.mocked(useAccess)
const toastMock = vi.fn()

const activePermissions = [
  { module: "ol_parameters", action: "view" },
  { module: "ol_parameters", action: "create" },
  { module: "ol_parameters", action: "update" },
  { module: "ol_parameters", action: "deactivate" },
]

const accessWith = (permissions: Array<{ module: string; action: string }>) => ({
  access: { visibleModules: ["ol_parameters"], permissions, groups: [] },
  isLoading: false,
  isError: false,
  canAccess: vi.fn(() => true),
})

const rows = [{
  id: "policy-1",
  code: "POLICY_ACTIVE",
  name: "Active policy setup",
  is_active: true,
  effective_from: "2026-01-01",
  effective_to: null,
  product: "product-1",
  plan: "plan-1",
  frequency: "ANNUAL",
  rate_factor: "1.05000000",
  installment_type: "ANTICIPATED_ENDOWMENT",
  badge_type: "POSITIVE",
  display_order: 1,
  is_terminal: false,
  allowed_transitions: ["POLICY_LAPSED"],
  renewal_action: "PENDING",
  category: "BENEFICIARY",
  calculation_basis: "PERCENTAGE",
  default_ratio: "100.0000",
  cover_type: "DEPENDENT",
  member_relation: "SPOUSE",
  min_age: 18,
  max_age: 65,
  waiting_period_days: 30,
  benefit_limit: "1000000.00",
}]

function mockApi() {
  requestMock.mockImplementation(async (path, options) => {
    if (options?.method === "POST" || options?.method === "PATCH") return {} as never
    if (String(path).includes("policy-statuses")) {
      return { results: [{ ...rows[0], code: "POLICY_LAPSED", name: "Lapsed" }], count: 1, page: 1, page_size: 20 } as never
    }
    return { results: rows, count: rows.length, page: 1, page_size: 20 } as never
  })
}

describe("OLPolicySetup", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAccessMock.mockReturnValue(accessWith(activePermissions))
    vi.mocked(useToast).mockReturnValue({ toast: toastMock, dismiss: vi.fn() })
    mockApi()
  })

  it("renders each Policy Setup screen from its backend API", async () => {
    render(<OLPolicySetup />)
    expect(await screen.findByRole("columnheader", { name: "Rate factor" })).toBeInTheDocument()

    const tabs = [
      ["OL Grace Period", "/api/v1/ol-parameters/grace-periods/", "Grace days"],
      ["OL Policy Status", "/api/v1/ol-parameters/policy-statuses/", "Configured badge"],
      ["OL Policy Renewal Status", "/api/v1/ol-parameters/policy-renewal-statuses/", "Renewal action"],
      ["OL Beneficial Type", "/api/v1/ol-parameters/beneficial-types/", "Default ratio"],
      ["OL Member Cover Configuration", "/api/v1/ol-parameters/member-cover-configurations/", "Waiting days"],
    ] as const

    for (const [label, endpoint, column] of tabs) {
      fireEvent.click(screen.getByRole("button", { name: label }))
      expect(await screen.findByRole("columnheader", { name: column })).toBeInTheDocument()
      await waitFor(() => expect(requestMock).toHaveBeenCalledWith(expect.stringContaining(endpoint)))
    }
  })

  it("shows inline validation and blocks an invalid rate-row save", async () => {
    render(<OLPolicySetup />)
    fireEvent.click(await screen.findByRole("button", { name: "New setup" }))

    expect(screen.getByText("Rate factor is required.")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Create setup" }))

    expect(toastMock).toHaveBeenCalledWith(expect.objectContaining({ title: "Check the form" }))
    expect(requestMock.mock.calls.some(([, options]) => options?.method === "POST")).toBe(false)
  })

  it("saves policy status transitions selected from the active status catalog", async () => {
    render(<OLPolicySetup />)
    fireEvent.click(await screen.findByRole("button", { name: "OL Policy Status" }))
    fireEvent.click(await screen.findByRole("button", { name: "New setup" }))

    fireEvent.change(screen.getByRole("textbox", { name: /Code/ }), { target: { value: "POLICY_NEW" } })
    fireEvent.change(screen.getByRole("textbox", { name: /Name/ }), { target: { value: "New policy status" } })
    fireEvent.change(screen.getByRole("textbox", { name: /Configured badge type/ }), { target: { value: "NEUTRAL" } })
    const transition = await screen.findByRole("checkbox")
    fireEvent.click(transition)
    fireEvent.click(screen.getByRole("button", { name: "Create setup" }))

    await waitFor(() => expect(requestMock).toHaveBeenCalledWith(
      "/api/v1/ol-parameters/policy-statuses/",
      expect.objectContaining({ method: "POST", body: expect.stringContaining('"allowed_transitions":["POLICY_LAPSED"]') }),
    ))
  })

  it("hides create and row mutation actions for view-only users", async () => {
    useAccessMock.mockReturnValue(accessWith([{ module: "ol_parameters", action: "view" }]))
    render(<OLPolicySetup />)

    expect(await screen.findByText("POLICY_ACTIVE")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "New setup" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Actions for row 1" })).not.toBeInTheDocument()
  })
})

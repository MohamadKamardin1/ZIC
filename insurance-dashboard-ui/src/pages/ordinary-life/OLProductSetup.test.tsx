import { beforeEach, describe, expect, it, vi } from "vitest"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import OLProductSetup from "./OLProductSetup"
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

const permissions = [
  { module: "ol_parameters", action: "view" },
  { module: "ol_parameters", action: "create" },
  { module: "ol_parameters", action: "update" },
  { module: "ol_parameters", action: "deactivate" },
]

const baseRow = {
  id: "row-1",
  code: "BASIC",
  name: "Basic",
  is_active: true,
  effective_from: "2026-01-01",
  effective_to: null,
  plan_category: "TRADITIONAL",
  plan_type: "TYPE-1",
  insurance_class: "ORDINARY_LIFE",
  currency: "TZS",
  min_entry_age: 18,
  max_entry_age: 65,
  min_term: 1,
  max_term: 30,
  premium_frequencies: ["ANNUAL"],
  allow_riders: true,
  allow_loans: false,
  allow_withdrawals: false,
  allow_surrender: true,
  allow_paidup: true,
  allow_bonus: true,
  investment_linked: false,
  product: "PRODUCT-1",
  plan: "PLAN-1",
  tax_type: "STAMP_DUTY",
  tax_basis: "PREMIUM",
  rate_type: "PERCENTAGE",
  rate_value: "2.5000",
  apply_on: "TOTAL_PREMIUM",
  sequence: 1,
  target_market_type: "RETAIL",
  min_age: 18,
  max_age: 65,
  occupation_categories: ["OFFICE"],
  residency_requirement: "ZANZIBAR",
  underwriting_class: "STANDARD",
  loading_basis: "PREMIUM",
  occupation_risk_category: "LOW",
  max_sum_assured: "100000000.00",
  loading_rate: "5.0000",
  exclusion_flag: false,
  risk_profile: "BALANCED",
  fund_type: "FUND-TYPE-1",
  valuation_frequency: "DAILY",
  unit_price: "1.0000",
}

function accessWith(currentPermissions = permissions, isSuperAdmin = false) {
  return { access: { visibleModules: ["ol_parameters"], permissions: currentPermissions, groups: [] }, isLoading: false, isError: false, isSuperAdmin, canAccess: vi.fn(() => true) }
}

function mockApi() {
  requestMock.mockImplementation(async (path, options) => {
    if (options?.method === "POST" || options?.method === "PATCH" || options?.method === "DELETE") return {} as never
    if (String(path).includes("plan-types")) return { results: [{ ...baseRow, id: "TYPE-1", code: "TYPE-1", name: "Traditional" }], count: 1, page: 1, page_size: 20 } as never
    if (String(path).includes("products")) return { results: [{ ...baseRow, id: "PRODUCT-1", code: "PRODUCT-1", name: "Basic Product" }], count: 1, page: 1, page_size: 20 } as never
    if (String(path).includes("investment-fund-types")) return { results: [{ ...baseRow, id: "FUND-TYPE-1", code: "FUND-TYPE-1", name: "Balanced Fund" }], count: 1, page: 1, page_size: 20 } as never
    return { results: [baseRow], count: 1, page: 1, page_size: 20 } as never
  })
}

describe("OLProductSetup", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAccessMock.mockReturnValue(accessWith())
    vi.mocked(useToast).mockReturnValue({ toast: toastMock, dismiss: vi.fn() })
    mockApi()
  })

  it("renders all eight Product Setup screens from their APIs", async () => {
    render(<OLProductSetup />)
    expect(await screen.findByRole("columnheader", { name: "Plan category" })).toBeInTheDocument()
    const tabs = [
      ["OL Product", "Insurance class"],
      ["Plan Tax Configurations", "Tax type"],
      ["Plan Target Market", "Market type"],
      ["Plan Risk Categories", "Underwriting class"],
      ["Plan Occupation Risk Limit", "Occupation risk"],
      ["Investment Fund Type", "Risk profile"],
      ["Investment Fund", "Fund type"],
    ] as const
    for (const [label, column] of tabs) {
      fireEvent.click(screen.getByRole("button", { name: label }))
      expect(await screen.findByRole("columnheader", { name: column })).toBeInTheDocument()
    }
    await waitFor(() => expect(requestMock.mock.calls.some(([path]) => String(path).includes("/api/v1/ol-parameters/investment-funds/"))).toBe(true))
  })

  it("grants unrestricted Product Setup access to a superuser without IAM permission entries", async () => {
    useAccessMock.mockReturnValue(accessWith([], true))
    render(<OLProductSetup />)

    expect(await screen.findByText("Traditional")).toBeInTheDocument()
    expect(screen.queryByText("Read access required")).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "New setup" })).not.toBeDisabled()
    fireEvent.click(screen.getByRole("button", { name: "Actions for row 1" }))
    expect(await screen.findByRole("button", { name: "Edit" })).toBeInTheDocument()
  })

  it("saves a product with capability toggles", async () => {
    render(<OLProductSetup />)
    await screen.findByText("Traditional")
    await waitFor(() => expect(requestMock.mock.calls.filter(([path]) => String(path).includes("page_size=200")).length).toBeGreaterThanOrEqual(3))
    fireEvent.click(await screen.findByRole("button", { name: "OL Product" }))
    fireEvent.click(screen.getByRole("button", { name: "New setup" }))
    fireEvent.change(screen.getByRole("textbox", { name: /Code/ }), { target: { value: "PROD-NEW" } })
    fireEvent.change(screen.getByRole("textbox", { name: /Name/ }), { target: { value: "New Product" } })
    fireEvent.change(screen.getByRole("textbox", { name: /Insurance class/ }), { target: { value: "ORDINARY_LIFE" } })
    fireEvent.change(screen.getByRole("textbox", { name: /Currency/ }), { target: { value: "TZS" } })
    fireEvent.click(screen.getByRole("button", { name: /^Plan typerequired$/ }))
    fireEvent.click(await screen.findByRole("option", { name: /TYPE-1/ }))
    fireEvent.change(screen.getByRole("spinbutton", { name: /Minimum entry age/ }), { target: { value: "18" } })
    fireEvent.change(screen.getByRole("spinbutton", { name: /Maximum entry age/ }), { target: { value: "65" } })
    fireEvent.change(screen.getByRole("spinbutton", { name: /Minimum term/ }), { target: { value: "1" } })
    fireEvent.change(screen.getByRole("spinbutton", { name: /Maximum term/ }), { target: { value: "30" } })
    fireEvent.change(screen.getByPlaceholderText("Add or type a frequency"), { target: { value: "ANNUAL" } })
    fireEvent.click(screen.getByRole("button", { name: "Add" }))
    fireEvent.click(screen.getByRole("switch", { name: "Riders" }))
    fireEvent.click(screen.getByRole("switch", { name: "Loans" }))
    fireEvent.click(screen.getByRole("button", { name: "Create setup" }))

    await waitFor(() => expect(requestMock).toHaveBeenCalledWith("/api/v1/ol-parameters/products/", expect.objectContaining({ method: "POST", body: expect.stringContaining('"allow_riders":true') })))
    expect(requestMock.mock.calls.some(([, options]) => options?.method === "POST" && String(options.body).includes('"allow_loans":true'))).toBe(true)
  })

  it("shows inline range validation and blocks an invalid product save", async () => {
    render(<OLProductSetup />)
    await screen.findByText("Traditional")
    await waitFor(() => expect(requestMock.mock.calls.filter(([path]) => String(path).includes("page_size=200")).length).toBeGreaterThanOrEqual(3))
    fireEvent.click(await screen.findByRole("button", { name: "OL Product" }))
    fireEvent.click(screen.getByRole("button", { name: "New setup" }))
    fireEvent.change(screen.getByRole("textbox", { name: /Code/ }), { target: { value: "PROD-BAD" } })
    fireEvent.change(screen.getByRole("textbox", { name: /Name/ }), { target: { value: "Invalid Product" } })
    fireEvent.change(screen.getByRole("textbox", { name: /Insurance class/ }), { target: { value: "ORDINARY_LIFE" } })
    fireEvent.change(screen.getByRole("textbox", { name: /Currency/ }), { target: { value: "TZS" } })
    fireEvent.click(screen.getByRole("button", { name: /^Plan typerequired$/ }))
    fireEvent.click(await screen.findByRole("option", { name: /TYPE-1/ }))
    fireEvent.change(screen.getByRole("spinbutton", { name: /Minimum entry age/ }), { target: { value: "70" } })
    fireEvent.change(screen.getByRole("spinbutton", { name: /Maximum entry age/ }), { target: { value: "60" } })
    fireEvent.click(screen.getByRole("button", { name: "Create setup" }))

    expect(await screen.findByText("Maximum entry age cannot be less than minimum entry age.")).toBeInTheDocument()
    expect(requestMock.mock.calls.some(([, options]) => options?.method === "POST")).toBe(false)
  })
})

import { beforeEach, describe, expect, it, vi } from "vitest"
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import OLProductRating from "./OLProductRating"
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

const premiumTable = {
  id: "premium-table-1",
  table_code: "PREM-2026",
  name: "Ordinary Life Premium 2026",
  description: "Premium basis",
  rating_basis: "SUM_ASSURED",
  currency: "TZS",
  version: "1.0",
  effective_from: "2026-01-01",
  effective_to: null,
  is_active: true,
}

const mortalityTable = {
  id: "mortality-table-1",
  table_code: "MORT-2026",
  name: "Ordinary Life Mortality 2026",
  description: "Mortality basis",
  version: "1.0",
  effective_from: "2026-01-01",
  effective_to: null,
  is_active: true,
}

const jointSetup = {
  id: "joint-1",
  code: "JOINT-FIRST",
  name: "First death setup",
  joint_life_type: "FIRST_DEATH",
  age_basis: "YOUNGER_LIFE",
  survivor_benefit_rule: "Pay on first death",
  premium_adjustment_factor: "1.10000000",
  underwriting_rule: "Joint underwriting",
  product: "product-1",
  plan: null,
  effective_from: "2026-01-01",
  effective_to: null,
  is_active: true,
}

const premiumRow = {
  id: "premium-row-1",
  code: "PREM-ROW-1",
  name: "Male non-smoker",
  gender: "MALE",
  smoker_status: "NON_SMOKER",
  age_from: 18,
  age_to: 65,
  term_from: 1,
  term_to: 30,
  frequency: "ANNUAL",
  sum_assured_band_from: null,
  sum_assured_band_to: null,
  rate: "2.50000000",
  rate_unit: "PER_THOUSAND_SUM_ASSURED",
}

const mortalityRow = {
  id: "mortality-row-1",
  code: "MORT-ROW-1",
  name: "Age 18",
  age: 18,
  gender: "MALE",
  smoker_status: "NON_SMOKER",
  policy_year: 1,
  mortality_rate: "0.00100000",
}

const reinstatementRate = { id: "rein-1", code: "REIN-2026", product: "product-1", plan: null, calculation_basis: "OUTSTANDING_PREMIUM", rate: "5.00000000", effective_from: "2026-01-01", effective_to: null, is_active: true }
const bonusRate = { id: "bonus-1", code: "BONUS-2026", product: "product-1", plan: null, bonus_type: "REVERSIONARY", valuation_year: 1, rate: "2.25000000", effective_from: "2026-01-01", effective_to: null, is_active: true }
const mortgageFactor = { id: "mortgage-1", code: "MORTGAGE-2026", product: "product-1", plan: null, calculation_basis: "LOAN_BALANCE", factor: "1.09000000", effective_from: "2026-01-01", effective_to: null, is_active: true }
const installmentCharge = { id: "installment-1", code: "INSTALLMENT-2026", product: "product-1", plan: null, frequency: "MONTHLY", charge_type: "PERCENTAGE", apply_on: "PREMIUM", rate_value: "3.00000000", effective_from: "2026-01-01", effective_to: null, is_active: true }
const cashSurrenderValue = { id: "csv-1", code: "CSV-2026", product: "product-1", plan: null, policy_year_from: 1, policy_year_to: 30, age_from: 18, age_to: 65, term_from: 5, term_to: 30, gender: "M", smoker_status: "NS", surrender_value_factor: "0.55000000", rate: null, effective_from: "2026-01-01", effective_to: null, is_active: true }
const reserveLoading = { id: "reserve-1", code: "RESERVE-2026", product: "product-1", plan: null, loading_type: "EXPENSE", loading_basis: "RESERVE", rate_value: "2.50000000", effective_from: "2026-01-01", effective_to: null, is_active: true }

function accessWith(currentPermissions = permissions) {
  return { access: { visibleModules: ["ol_parameters"], permissions: currentPermissions, groups: [] }, isLoading: false, isError: false, canAccess: vi.fn(() => true), isSuperAdmin: false }
}

function mockApi() {
  requestMock.mockImplementation(async (path, options) => {
    const url = String(path)
    if (options?.method === "POST" || options?.method === "PATCH" || options?.method === "DELETE") return {} as never
    if (url.includes("premium-rate-tables")) return { results: [premiumTable], count: 1, page: 1, page_size: 20 } as never
    if (url.includes("mortality-rate-tables")) return { results: [mortalityTable], count: 1, page: 1, page_size: 20 } as never
    if (url.includes("joint-life-setups")) return { results: [jointSetup], count: 1, page: 1, page_size: 20 } as never
    if (url.includes("reinstatement-interest-rates")) return { results: [reinstatementRate], count: 1, page: 1, page_size: 20 } as never
    if (url.includes("bonus-rates")) return { results: [bonusRate], count: 1, page: 1, page_size: 20 } as never
    if (url.includes("mortgage-interest-factors")) return { results: [mortgageFactor], count: 1, page: 1, page_size: 20 } as never
    if (url.includes("installment-charge-rates")) return { results: [installmentCharge], count: 1, page: 1, page_size: 20 } as never
    if (url.includes("cash-surrender-values")) return { results: [cashSurrenderValue], count: 1, page: 1, page_size: 20 } as never
    if (url.includes("reserve-loadings")) return { results: [reserveLoading], count: 1, page: 1, page_size: 20 } as never
    if (url.includes("premium-rate-rows")) return { results: [premiumRow], count: 1, page: 1, page_size: 500 } as never
    if (url.includes("mortality-rate-rows")) return { results: [mortalityRow], count: 1, page: 1, page_size: 500 } as never
    return { results: [], count: 0, page: 1, page_size: 20 } as never
  })
}

describe("OLProductRating", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAccessMock.mockReturnValue(accessWith())
    vi.mocked(useToast).mockReturnValue({ toast: toastMock, dismiss: vi.fn() })
    mockApi()
  })

  it("renders premium, mortality, and joint-life screens from APIs", async () => {
    render(<OLProductRating />)
    expect(await screen.findByRole("columnheader", { name: "Table" })).toBeInTheDocument()
    expect(screen.getByText("PREM-2026")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "OL Mortality Rate" }))
    expect(await screen.findByText("MORT-2026")).toBeInTheDocument()
    expect(screen.getByRole("columnheader", { name: "Effective from" })).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "OL Joint Life Setup" }))
    expect(await screen.findByRole("columnheader", { name: "Survivor rule" })).toBeInTheDocument()
    expect(screen.getByText("JOINT-FIRST")).toBeInTheDocument()
  })

  it("supports premium row add, edit, remove, and persistence", async () => {
    render(<OLProductRating />)
    await screen.findByText("PREM-2026")
    fireEvent.click(screen.getByRole("button", { name: "Actions for row 1" }))
    fireEvent.click(screen.getByRole("button", { name: "Open rate rows" }))
    expect(await screen.findByText("Rate row editor")).toBeInTheDocument()
    const rateInputs = () => Array.from(document.querySelectorAll<HTMLInputElement>('input[name="rate"]'))
    expect(rateInputs()).toHaveLength(1)

    fireEvent.click(screen.getByRole("button", { name: "Add row" }))
    expect(rateInputs()).toHaveLength(2)
    fireEvent.change(rateInputs()[1], { target: { value: "3.25000000" } })
    fireEvent.click(screen.getByRole("button", { name: "Remove row 2" }))
    expect(rateInputs()).toHaveLength(1)

    fireEvent.click(screen.getByRole("button", { name: "Add row" }))
    fireEvent.change(rateInputs()[1], { target: { value: "3.25000000" } })
    fireEvent.click(screen.getByRole("button", { name: "Save rows" }))
    await waitFor(() => expect(requestMock.mock.calls.some(([, options]) => options?.method === "POST" && String(options.body).includes("premium-table-1"))).toBe(true))
  })

  it("renders row-level mortality CSV import errors", async () => {
    render(<OLProductRating />)
    fireEvent.click(await screen.findByRole("button", { name: "OL Mortality Rate" }))
    await screen.findByText("MORT-2026")
    fireEvent.click(screen.getByRole("button", { name: "Actions for row 1" }))
    fireEvent.click(screen.getByRole("button", { name: "Open rate rows" }))
    await screen.findByText("Rate row editor")

    const csv = new File(["code,age,mortality_rate\nBAD-ROW,200,-1"], "mortality.csv", { type: "text/csv" })
    fireEvent.change(screen.getByLabelText("Import rate rows CSV"), { target: { files: [csv] } })
    expect(await screen.findByText(/Row 2: age or mortality rate is invalid/)).toBeInTheDocument()
    expect(requestMock.mock.calls.some(([, options]) => options?.method === "POST" && String(options.body).includes("mortality-rate-rows/bulk-import"))).toBe(false)
  })

  it("creates a new premium version from an existing table", async () => {
    render(<OLProductRating />)
    await screen.findByText("PREM-2026")
    fireEvent.click(screen.getByRole("button", { name: "Actions for row 1" }))
    fireEvent.click(screen.getByRole("button", { name: "Create new version" }))
    await waitFor(() => expect(requestMock.mock.calls.some(([, options]) => options?.method === "POST" && String(options.body).includes('"version":"2.0"'))).toBe(true))
  })

  it("blocks an invalid joint-life setup with inline validation", async () => {
    render(<OLProductRating />)
    fireEvent.click(await screen.findByRole("button", { name: "OL Joint Life Setup" }))
    await screen.findByText("JOINT-FIRST")
    fireEvent.click(screen.getByRole("button", { name: "Add setup" }))
    fireEvent.click(screen.getByRole("button", { name: "Save setup" }))
    expect(await screen.findByText(/Code is required/)).toBeInTheDocument()
    expect(requestMock.mock.calls.some(([, options]) => options?.method === "POST")).toBe(false)
  })

  it("renders all six Part 2 screens from their backend collections", async () => {
    render(<OLProductRating />)
    const screens = [
      ["Reinstatement Interest Rate", "Basis", "REIN-2026"],
      ["OL Bonus Rate", "Bonus type", "BONUS-2026"],
      ["OL Mortgage Interest Factor", "Factor", "MORTGAGE-2026"],
      ["Installment Charge Rate", "Frequency", "INSTALLMENT-2026"],
      ["OL Cash Surrender Value", "Policy year", "CSV-2026"],
      ["OL Reserve Loadings", "Loading type", "RESERVE-2026"],
    ] as const

    for (const [tab, column, code] of screens) {
      fireEvent.click(screen.getByRole("button", { name: tab }))
      expect(await screen.findByRole("columnheader", { name: column })).toBeInTheDocument()
      expect(screen.getByText(code)).toBeInTheDocument()
    }
  })

  it("saves a reinstatement interest rate with its backend scope and enum values", async () => {
    render(<OLProductRating />)
    fireEvent.click(await screen.findByRole("button", { name: "Reinstatement Interest Rate" }))
    await screen.findByText("REIN-2026")
    fireEvent.click(screen.getByRole("button", { name: "Actions for row 1" }))
    fireEvent.click(await screen.findByRole("button", { name: "Edit" }))
    await screen.findByLabelText(/^Code/)
    fireEvent.change(screen.getByLabelText(/^Code/), { target: { value: "REIN-UPDATED" } })
    fireEvent.click(screen.getByRole("button", { name: "Save setup" }))

    await waitFor(() => expect(requestMock.mock.calls.some(([path, options]) => String(path) === "/api/v1/ol-parameters/reinstatement-interest-rates/rein-1/" && options?.method === "PATCH" && String(options.body).includes('"code":"REIN-UPDATED"'))).toBe(true))
  })

  it("blocks a bonus setup when the required code and scope are missing", async () => {
    render(<OLProductRating />)
    fireEvent.click(await screen.findByRole("button", { name: "OL Bonus Rate" }))
    await screen.findByText("BONUS-2026")
    fireEvent.click(screen.getByRole("button", { name: "Actions for row 1" }))
    fireEvent.click(await screen.findByRole("button", { name: "Edit" }))
    await screen.findByLabelText(/^Code/)
    fireEvent.change(screen.getByLabelText(/^Code/), { target: { value: "" } })
    fireEvent.change(screen.getByLabelText("Product ID"), { target: { value: "" } })
    fireEvent.click(screen.getByRole("button", { name: "Save setup" }))

    expect(await screen.findByText(/Code is required/)).toBeInTheDocument()
    expect(requestMock.mock.calls.some(([, options]) => options?.method === "POST")).toBe(false)
  })

  it("rejects an out-of-range cash-surrender factor during CSV import", async () => {
    render(<OLProductRating />)
    fireEvent.click(await screen.findByRole("button", { name: "OL Cash Surrender Value" }))
    await screen.findByText("CSV-2026")
    const csv = new File(["code,product,policy_year_from,policy_year_to,age_from,age_to,term_from,term_to,gender,smoker_status,surrender_value_factor,rate\nCSV-BAD,product-1,1,30,18,65,5,30,M,NS,1.1,"], "cash-surrender.csv", { type: "text/csv" })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    fireEvent.change(input, { target: { files: [csv] } })

    expect(await screen.findByText(/Row 2: surrender value factor must be between 0 and 1/)).toBeInTheDocument()
    expect(requestMock.mock.calls.some(([path, options]) => String(path).includes("cash-surrender-values") && options?.method === "POST")).toBe(false)
  })

  it("deactivates a Part 2 record only after confirmation", async () => {
    render(<OLProductRating />)
    fireEvent.click(await screen.findByRole("button", { name: "Reinstatement Interest Rate" }))
    await screen.findByText("REIN-2026")
    fireEvent.click(screen.getByRole("button", { name: "Actions for row 1" }))
    fireEvent.click(await screen.findByRole("button", { name: "Deactivate" }))
    const dialog = await screen.findByRole("dialog")
    expect(dialog).toBeInTheDocument()
    fireEvent.click(within(dialog).getByRole("button", { name: "Confirm" }))

    await waitFor(() => expect(requestMock.mock.calls.some(([path, options]) => String(path) === "/api/v1/ol-parameters/reinstatement-interest-rates/rein-1/deactivate/" && options?.method === "POST")).toBe(true))
  })
})

export {}

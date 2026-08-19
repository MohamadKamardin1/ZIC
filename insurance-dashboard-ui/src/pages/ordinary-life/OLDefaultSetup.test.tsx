import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import OLDefaultSetup from "./OLDefaultSetup"
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

const activeRow = {
  id: "default-1",
  code: "DEFAULT_QUOTE_EXPIRY_DAYS",
  name: "Default quotation expiry",
  description: "Expiry used for new quotations.",
  is_active: true,
  effective_from: "2026-01-01",
  effective_to: null,
  parameter_category: "QUOTATION",
  parameter_key: "DEFAULT_QUOTE_EXPIRY_DAYS",
  value_type: "INTEGER",
  value: 30,
}

const accessWith = (permissions: Array<{ module: string; action: string }>) => ({
  access: { visibleModules: ["ol_parameters"], permissions, groups: [] },
  isLoading: false,
  isError: false,
  canAccess: vi.fn(() => true),
  isSuperAdmin: false,
})

function mockList(rows = [activeRow]) {
  requestMock.mockImplementation(async (path, options) => {
    if (String(path).includes("/deactivate/") || options?.method === "POST" || options?.method === "PATCH") return {} as never
    return { results: rows, count: rows.length, page: 1, page_size: 20 } as never
  })
}

describe("OLDefaultSetup", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAccessMock.mockReturnValue(accessWith([
      { module: "ol_parameters", action: "view" },
      { module: "ol_parameters", action: "create" },
      { module: "ol_parameters", action: "update" },
      { module: "ol_parameters", action: "deactivate" },
    ]))
    vi.mocked(useToast).mockReturnValue({ toast: toastMock, dismiss: vi.fn() })
    mockList()
  })

  it("renders the default setup table from the API", async () => {
    render(<OLDefaultSetup />)

    expect((await screen.findAllByText("DEFAULT_QUOTE_EXPIRY_DAYS")).length).toBeGreaterThan(0)
    expect(screen.getByRole("columnheader", { name: "Code" })).toBeInTheDocument()
    expect(screen.getByRole("columnheader", { name: "Category" })).toBeInTheDocument()
    expect(screen.getByRole("columnheader", { name: "Typed value" })).toBeInTheDocument()
    expect(requestMock).toHaveBeenCalledWith(expect.stringContaining("/api/v1/ol-parameters/default-system-parameters/"))
  })

  it("blocks an empty create modal and reports required-field validation", async () => {
    mockList([])
    render(<OLDefaultSetup />)

    fireEvent.click(await screen.findByRole("button", { name: "New setup" }))
    expect(screen.getByRole("dialog")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Create setup" }))

    expect(screen.getAllByText("This field is required.").length).toBeGreaterThan(0)
    expect(toastMock).toHaveBeenCalledWith(expect.objectContaining({ title: "Check required fields" }))
    expect(requestMock.mock.calls.some(([, options]) => options?.method === "POST")).toBe(false)
  })

  it("calls the deactivate API only after confirmation", async () => {
    render(<OLDefaultSetup />)

    expect((await screen.findAllByText("DEFAULT_QUOTE_EXPIRY_DAYS")).length).toBeGreaterThan(0)
    fireEvent.click(screen.getByRole("button", { name: "Actions for row 1" }))
    fireEvent.click(screen.getByRole("button", { name: "Deactivate" }))
    expect(screen.getByRole("dialog")).toHaveTextContent(/Deactivate/)

    fireEvent.click(screen.getByRole("button", { name: /^Deactivate$/ }))
    await waitFor(() => expect(requestMock).toHaveBeenCalledWith(
      "/api/v1/ol-parameters/default-system-parameters/default-1/deactivate/",
      { method: "POST" },
    ))
    expect(toastMock).toHaveBeenCalledWith(expect.objectContaining({ title: "Parameter deactivated" }))
  })

  it("hides mutation actions when the user has view-only permission", async () => {
    useAccessMock.mockReturnValue(accessWith([{ module: "ol_parameters", action: "view" }]))
    mockList()
    render(<OLDefaultSetup />)

    expect((await screen.findAllByText("DEFAULT_QUOTE_EXPIRY_DAYS")).length).toBeGreaterThan(0)
    expect(screen.queryByRole("button", { name: "New setup" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Actions for row 1" })).not.toBeInTheDocument()
    expect(screen.queryByText("Edit")).not.toBeInTheDocument()
    expect(screen.queryByText("Deactivate")).not.toBeInTheDocument()
  })
})

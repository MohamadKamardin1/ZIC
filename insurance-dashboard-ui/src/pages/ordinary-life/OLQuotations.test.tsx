import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import OLQuotations from "./OLQuotations"

const { requestMock, navigateMock, openDocumentMock } = vi.hoisted(() => ({ requestMock: vi.fn(), navigateMock: vi.fn(), openDocumentMock: vi.fn() }))

vi.mock("../../lib/documentClient", () => ({
  AuthenticatedDocumentError: class AuthenticatedDocumentError extends Error {
    requiresLogin = false
    loginUrl = "/login"
  },
  openAuthenticatedDocument: openDocumentMock,
}))

vi.mock("../../lib/apiClient", () => ({
  request: requestMock,
  buildTableQuery: (query: { page?: number; pageSize?: number; search?: string; ordering?: string; filters?: Record<string, unknown> } = {}) => {
    const params = new URLSearchParams()
    if (query.page) params.set("page", String(query.page))
    if (query.pageSize) params.set("page_size", String(query.pageSize))
    if (query.search) params.set("search", query.search)
    if (query.ordering) params.set("ordering", query.ordering)
    Object.entries(query.filters ?? {}).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") params.set(key, String(value))
    })
    const result = params.toString()
    return result ? `?${result}` : ""
  },
}))

vi.mock("react-router-dom", () => ({
  useNavigate: () => navigateMock,
}))

vi.mock("../../lib/access", () => ({
  useAccess: () => ({
    access: {
      permissions: [
        { module: "ol_quotations", action: "view" },
        { module: "ol_quotations", action: "update" },
        { module: "ol_quotations", action: "finalize" },
        { module: "ol_quotations", action: "print" },
        { module: "ol_quotations", action: "convert" },
        { module: "ol_quotations", action: "destroy" },
      ],
    },
    canAccess: () => true,
  }),
}))

vi.mock("../../components/ui/Toast", () => ({
  useToast: () => ({ toast: vi.fn(), dismiss: vi.fn() }),
}))

const draftRow = {
  id: "draft-1",
  quote_number: "Q-0001",
  quote_name: "Draft family cover",
  prospect_name: "Asha Said",
  plans_summary: "OL001 - Family Protection",
  plan_count: 1,
  total_premium: "125.50",
  currency: "TZS",
  status: "DRAFT",
  status_badge: { code: "DRAFT", label: "Draft", tone: "neutral" },
  version: 1,
  quote_date: "2026-08-18",
  agent: { name: "Juma Agent" },
  created_by: { name: "Admin User" },
  row_actions: {
    view: { key: "view", visible: true, enabled: true },
    edit: { key: "edit", visible: true, enabled: true },
    finalize: { key: "finalize", visible: true, enabled: true },
    delete: { key: "delete", visible: true, enabled: true },
    revise: { key: "revise", visible: false, enabled: false },
    print: { key: "print", visible: false, enabled: false },
    convert_to_proposal: { key: "convert_to_proposal", visible: false, enabled: false },
  },
}

const finalizedRow = {
  id: "finalized-1",
  quote_number: "Q-0002",
  quote_name: "Finalized business cover",
  prospect_name: "Hassan Ali",
  plans_summary: "OL002 - Business Life",
  plan_count: 2,
  total_premium: "560.00",
  currency: "USD",
  status: "FINALIZED",
  status_badge: { code: "FINALIZED", label: "Finalized", tone: "success" },
  version: 3,
  quote_date: "2026-08-17",
  agent: { name: "Mariam Agent" },
  created_by: { name: "Underwriting User" },
  row_actions: {
    view: { key: "view", visible: true, enabled: true },
    edit: { key: "edit", visible: false, enabled: false },
    finalize: { key: "finalize", visible: false, enabled: false },
    delete: { key: "delete", visible: false, enabled: false },
    revise: { key: "revise", visible: true, enabled: true },
    print: { key: "print", visible: true, enabled: true },
    convert_to_proposal: { key: "convert_to_proposal", visible: true, enabled: true, state_allowed: true },
  },
}

beforeEach(() => {
  requestMock.mockReset()
  navigateMock.mockReset()
  openDocumentMock.mockReset()
  openDocumentMock.mockResolvedValue({ objectUrl: "blob:quotation" })
  requestMock.mockImplementation(async (path: string) => {
    if (path.includes("/print/")) return { pdf_url: "/api/v1/ol-quotations/documents/document-1/download/" }
    if (path.includes("/summary/")) return { total: 4, drafts: 1, finalized: 1, converted: 1, expired: 1 }
    if (path.startsWith("/api/v1/ol/quotations/quotations/")) return { results: [draftRow, finalizedRow], count: 25, page: 1, page_size: 20 }
    return {}
  })
})

describe("OL Quotations list", () => {
  it("renders KPI counts, quotation rows, status badges, and pagination", async () => {
    render(<OLQuotations />)

    expect(await screen.findByText("Drafts")).toBeInTheDocument()
    expect(within(screen.getByText("Drafts").closest("article") as HTMLElement).getByText("1", { selector: "p" })).toBeInTheDocument()
    expect(screen.getByText("Q-0001")).toBeInTheDocument()
    expect(screen.getByText("Q-0002")).toBeInTheDocument()
    expect(screen.getByText("Draft")).toBeInTheDocument()
    expect(within(screen.getAllByRole("row")[2]).getByText("Finalized")).toBeInTheDocument()
    expect(screen.getByText("Page 1 of 2")).toBeInTheDocument()
    expect(screen.getByText("2", { selector: "span" })).toBeInTheDocument()
  })

  it("shows row actions according to quotation state and backend action metadata", async () => {
    render(<OLQuotations />)
    await screen.findByText("Q-0001")

    const rows = screen.getAllByRole("row")
    const draftActions = within(rows[1]).getByRole("button", { name: "Actions for row 1" })
    fireEvent.click(draftActions)
    expect(screen.getByRole("button", { name: "Edit" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Finalize" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Delete" })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Revise" })).not.toBeInTheDocument()
    fireEvent.click(draftActions)

    const finalizedActions = within(rows[2]).getByRole("button", { name: "Actions for row 2" })
    fireEvent.click(finalizedActions)
    expect(screen.getByRole("button", { name: "Revise" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Print" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Convert to Proposal" })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Delete" })).not.toBeInTheDocument()
  })

  it("passes search, filters, and date ranges to the quotations API", async () => {
    render(<OLQuotations />)
    await screen.findByText("Q-0001")
    fireEvent.change(screen.getByLabelText("Search"), { target: { value: "Q-0001" } })
    fireEvent.change(screen.getByLabelText("Status"), { target: { value: "DRAFT" } })
    fireEvent.change(screen.getByLabelText("Quote date from"), { target: { value: "2026-08-01" } })
    fireEvent.change(screen.getByLabelText("Quote date to"), { target: { value: "2026-08-31" } })

    await waitFor(() => {
      const listCalls = requestMock.mock.calls.filter(([path]) => String(path).startsWith("/api/v1/ol/quotations/quotations/") && !String(path).includes("/summary/"))
      const latestPath = String(listCalls.at(-1)?.[0] ?? "")
      expect(latestPath).toContain("search=Q-0001")
      expect(latestPath).toContain("status=DRAFT")
      expect(latestPath).toContain("quote_date_from=2026-08-01")
      expect(latestPath).toContain("quote_date_to=2026-08-31")
    })
  })

  it("opens print documents through authenticated retrieval from the work queue", async () => {
    const openSpy = vi.spyOn(window, "open").mockImplementation(() => null)
    render(<OLQuotations />)
    await screen.findByText("Q-0001")

    const rows = screen.getAllByRole("row")
    fireEvent.click(within(rows[2]).getByRole("button", { name: "Actions for row 2" }))
    fireEvent.click(screen.getByRole("button", { name: "Print" }))

    await waitFor(() => expect(openDocumentMock).toHaveBeenCalledWith("/api/v1/ol-quotations/documents/document-1/download/", {
      kind: "pdf",
      mode: "preview",
      filename: "Q-0002.pdf",
    }))
    expect(openSpy).not.toHaveBeenCalledWith(expect.stringContaining("/api/"), expect.anything(), expect.anything())
  })

  it("navigates to create and view routes", async () => {
    render(<OLQuotations />)
    await screen.findByText("Q-0001")
    fireEvent.click(screen.getByRole("button", { name: "Create New Quote" }))
    expect(navigateMock).toHaveBeenCalledWith("/ordinary-life/quotations/new")

    const rows = screen.getAllByRole("row")
    fireEvent.click(within(rows[1]).getByRole("button", { name: "Actions for row 1" }))
    fireEvent.click(screen.getByRole("button", { name: "View" }))
    expect(navigateMock).toHaveBeenCalledWith("/ordinary-life/quotations/draft-1")
  })
})

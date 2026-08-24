import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { cleanup, render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it, vi, beforeEach } from "vitest"
import { Sidebar } from "./Sidebar"
import { AccessProvider } from "../../lib/access"
import { fetchAccessMetadata } from "../../lib/apiClient"
import { useAuth } from "../../lib/auth"

vi.mock("../../lib/apiClient", () => ({
  fetchAccessMetadata: vi.fn(),
}))

vi.mock("../../lib/auth", () => ({
  useAuth: vi.fn(),
}))

vi.mock("../../lib/language", () => ({
  useLanguage: () => ({ t: (key: string) => key }),
}))

const mockedFetchAccessMetadata = vi.mocked(fetchAccessMetadata)
const mockedUseAuth = vi.mocked(useAuth)

function renderSidebar() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/ordinary-life/quotations"]}>
        <AccessProvider><Sidebar open /></AccessProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe("Sidebar access rendering", () => {
  beforeEach(() => {
    mockedFetchAccessMetadata.mockReset()
    mockedUseAuth.mockReturnValue({ user: { fullName: "Test User", username: "tester", userType: "USER", groups: [], permissions: [] } } as unknown as ReturnType<typeof useAuth>)
  })

  it("renders only module branches returned by IAM access metadata", async () => {
    mockedFetchAccessMetadata.mockResolvedValue({
      visibleModules: ["ol_quotations"],
      permissions: [],
      groups: ["Underwriting"],
    })

    renderSidebar()

    await waitFor(() => expect(screen.getByText("Quotations")).toBeInTheDocument())
    expect(screen.queryByText("Partner On-boarding")).not.toBeInTheDocument()
    expect(screen.queryByText("Group Life")).not.toBeInTheDocument()
  })

  it("gates Front Office Receipts by the exact view permission", async () => {
    mockedFetchAccessMetadata.mockResolvedValue({ visibleModules: ["front_office"], permissions: [], groups: [] })
    renderSidebar()
    await waitFor(() => expect(screen.getByText("Front Office")).toBeInTheDocument())
    expect(screen.queryByText("Receipts")).not.toBeInTheDocument()

    cleanup()
    mockedFetchAccessMetadata.mockResolvedValue({ visibleModules: ["front_office"], permissions: [{ module: "front_office.receipts", action: "view" }], groups: [] })
    renderSidebar()
    await waitFor(() => expect(screen.getByText("Receipts")).toBeInTheDocument())
  })

  it("shows Ordinary Life for a SUPER_ADMIN when access metadata is unavailable", async () => {
    mockedFetchAccessMetadata.mockResolvedValue(null)
    mockedUseAuth.mockReturnValue({ user: { fullName: "Super Admin", username: "admin", userType: "SUPER_ADMIN", groups: [], permissions: [] } } as unknown as ReturnType<typeof useAuth>)

    renderSidebar()

    await waitFor(() => expect(screen.getByText("Ordinary Life")).toBeInTheDocument())
    expect(screen.getAllByText("Quotations").length).toBeGreaterThan(0)
  })
})

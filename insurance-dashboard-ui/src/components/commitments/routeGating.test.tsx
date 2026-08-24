import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { RequirePermission } from "../../lib/access"
import { Sidebar } from "../layout/Sidebar"
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

const USER = {
  fullName: "Test User",
  username: "tester",
  userType: "USER",
  groups: [],
  permissions: [],
}

function renderSidebar(initialEntries = ["/ordinary-life/quotations"]) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        <AccessProvider>
          <Sidebar open />
        </AccessProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

function renderGate(permission = "ol_commitments.view", label = "Commitments panel") {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AccessProvider>
          <RequirePermission permission={permission}>
            <div>{label}</div>
          </RequirePermission>
        </AccessProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe("RequirePermission (route gating)", () => {
  beforeEach(() => {
    mockedUseAuth.mockReturnValue({ user: USER } as unknown as ReturnType<typeof useAuth>)
  })

  it("renders children when the exact permission is present", async () => {
    mockedFetchAccessMetadata.mockResolvedValue({
      visibleModules: [], permissions: [{ module: "ol_commitments", action: "view" }], groups: [],
    })
    renderGate()
    expect(await screen.findByText("Commitments panel")).toBeInTheDocument()
  })

  it("gates Front Office Receipts by the exact view permission", async () => {
    mockedFetchAccessMetadata.mockResolvedValue({ visibleModules: ["front_office"], permissions: [], groups: [] })
    renderGate("front_office.receipts.view", "Receipts panel")
    expect(await screen.findByText("Access restricted")).toBeInTheDocument()
    expect(screen.queryByText("Receipts panel")).not.toBeInTheDocument()
  })

  it("shows AccessDenied without the permission", async () => {
    mockedFetchAccessMetadata.mockResolvedValue({ visibleModules: ["ol_commitments"], permissions: [], groups: [] })
    renderGate()
    expect(await screen.findByText("Access restricted")).toBeInTheDocument()
    expect(screen.queryByText("Commitments panel")).not.toBeInTheDocument()
  })

  it("lets super admins through regardless of permission list", async () => {
    mockedFetchAccessMetadata.mockResolvedValue({
      isSuperuser: true, visibleModules: [], permissions: [], groups: [],
    })
    renderGate()
    expect(await screen.findByText("Commitments panel")).toBeInTheDocument()
  })
})

describe("Sidebar hides Commitments without ol_commitments.view", () => {
  beforeEach(() => {
    mockedUseAuth.mockReturnValue({ user: USER } as unknown as ReturnType<typeof useAuth>)
  })

  it("hides the Commitments item even when Ordinary Life is visible", async () => {
    mockedFetchAccessMetadata.mockResolvedValue({ visibleModules: ["ordinary_life"], permissions: [], groups: [] })

    renderSidebar()

    await waitFor(() => expect(screen.getByText("Quotations")).toBeInTheDocument())
    expect(screen.getByText("Ordinary Life")).toBeInTheDocument()
    expect(screen.queryByText("Commitments")).not.toBeInTheDocument()
  })

  it("shows Commitments when the ol_commitments.view permission exists", async () => {
    mockedFetchAccessMetadata.mockResolvedValue({
      visibleModules: ["ordinary_life"],
      permissions: [{ module: "ol_commitments", action: "view" }],
      groups: [],
    })

    renderSidebar()

    await waitFor(() => expect(screen.getByText("Commitments")).toBeInTheDocument())
  })
})
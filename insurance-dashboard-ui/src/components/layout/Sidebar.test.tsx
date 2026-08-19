import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"
import { Sidebar } from "./Sidebar"
import { AccessProvider } from "../../lib/access"

vi.mock("../../lib/apiClient", () => ({
  fetchAccessMetadata: vi.fn().mockResolvedValue({
    visibleModules: ["ol_quotations"],
    permissions: [],
    groups: ["Underwriting"],
  }),
}))

vi.mock("../../lib/auth", () => ({
  useAuth: () => ({ user: { fullName: "Test User", username: "tester" } }),
}))

vi.mock("../../lib/language", () => ({
  useLanguage: () => ({ t: (key: string) => key }),
}))

describe("Sidebar access rendering", () => {
  it("renders only module branches returned by IAM access metadata", async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/ordinary-life/quotations"]}>
          <AccessProvider><Sidebar open /></AccessProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    )

    await waitFor(() => expect(screen.getByText("Quotations")).toBeInTheDocument())
    expect(screen.queryByText("Partner On-boarding")).not.toBeInTheDocument()
    expect(screen.queryByText("Group Life")).not.toBeInTheDocument()
  })
})

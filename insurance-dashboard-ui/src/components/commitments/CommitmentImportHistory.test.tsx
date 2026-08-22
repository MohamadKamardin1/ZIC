import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { CommitmentImportHistory } from "./CommitmentImportHistory"

const { requestMock } = vi.hoisted(() => ({ requestMock: vi.fn() }))

vi.mock("../../lib/apiClient", () => ({ request: requestMock }))
vi.mock("react-router-dom", () => ({ useNavigate: () => vi.fn() }))

const IMPORT_RECORDS = {
  results: [
    { id: "import-1", file_name: "commitments_may.csv", uploaded_by_name: "Amina Hassan", created_at: "2026-08-20T10:00:00Z", ok_count: 12, error_count: 3, created_count: 12, status: "COMPLETED" },
    { id: "import-2", file_name: "commitments_april.csv", uploaded_by_name: "Juma Ali", created_at: "2026-07-15T09:30:00Z", ok_count: 5, error_count: 1, created_count: 4, status: "PARTIAL" },
  ],
}

function renderHistory() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <CommitmentImportHistory />
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  requestMock.mockReset()
  requestMock.mockImplementation(async (path: string) => {
    if (path.includes("/imports/import-1")) return { errors: [{ row: 2, field_errors: { currency: ["Must be a three-letter code."] } }], ok_count: 12, error_count: 3 }
    if (path.includes("/imports/")) return IMPORT_RECORDS
    return {}
  })
})

describe("CommitmentImportHistory", () => {
  it("lists import runs with file name, counts, and status badges", async () => {
    renderHistory()

    expect(await screen.findByText("commitments_may.csv")).toBeInTheDocument()
    expect(screen.getByText("commitments_april.csv")).toBeInTheDocument()
    expect(screen.getByText("Amina Hassan")).toBeInTheDocument()
    const statuses = screen.getAllByRole("status").map((node) => node.textContent)
    expect(statuses).toContain("COMPLETED")
    expect(statuses).toContain("PARTIAL")
    expect(screen.getAllByText("12").length).toBeGreaterThan(0)
    expect(screen.getByText("3")).toBeInTheDocument()
    expect(screen.getByText("4")).toBeInTheDocument()
  })

  it("expands to reveal row-level errors for an import", async () => {
    renderHistory()
    await screen.findByText("commitments_may.csv")

    fireEvent.click(screen.getByTestId("import-errors-import-1"))
    expect(await screen.findByText(/currency/)).toBeInTheDocument()
    expect(await screen.findByText(/Must be a three-letter code/)).toBeInTheDocument()
    expect(screen.getByText(/Row 2/)).toBeInTheDocument()
  })
})
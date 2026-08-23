import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import type { ComponentProps } from "react"
import { beforeEach, afterEach, describe, expect, it, vi } from "vitest"
import { ImportCommitmentsModal } from "./ImportCommitmentsModal"

const { requestMock, toastMock } = vi.hoisted(() => ({ requestMock: vi.fn(), toastMock: vi.fn() }))

vi.mock("../../lib/apiClient", () => ({ request: requestMock }))
vi.mock("react-router-dom", () => ({ useNavigate: () => vi.fn() }))
vi.mock("../../components/ui/Toast", () => ({ useToast: () => ({ toast: toastMock, dismiss: vi.fn() }) }))

const originalCreateObjectURL = URL.createObjectURL
const originalRevokeObjectURL = URL.revokeObjectURL

const CSV = [
  "source_type,currency,due_date,premium_amount,reason",
  "POLICY,TZS,2026-09-01,50000.00,Row one",
  "PROPOSAL,TZS,2026-09-15,75000.00,Row two",
].join("\n")

function renderModal(props: Partial<ComponentProps<typeof ImportCommitmentsModal>> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <ImportCommitmentsModal open onClose={vi.fn()} onComplete={vi.fn()} {...props} />
    </QueryClientProvider>,
  )
}

async function uploadAndDryRun() {
  const input = screen.getByTestId("import-file-input")
  const file = new File([CSV], "commitments.csv", { type: "text/csv" })
  fireEvent.change(input, { target: { files: [file] } })
  await waitFor(() => expect(screen.getByText("2 data row(s)")).toBeInTheDocument())
  fireEvent.click(screen.getByTestId("dry-run"))
}

beforeEach(() => {
  requestMock.mockReset()
  toastMock.mockReset()
  Object.assign(URL, { createObjectURL: vi.fn(() => "blob:csv"), revokeObjectURL: vi.fn() })
  requestMock.mockImplementation(async (path: string) => {
    if (path.startsWith("/api/v1/ol-commitments/commitments/import/")) {
      return { dry_run: true, imported: 2, created: 0, errors: [{ row: 2, field_errors: { currency: ["Must be a three-letter code."] }, message: "invalid" }] }
    }
    return {}
  })
})

afterEach(() => {
  Object.assign(URL, { createObjectURL: originalCreateObjectURL, revokeObjectURL: originalRevokeObjectURL })
})

describe("ImportCommitmentsModal", () => {
  it("downloads the CSV template", () => {
    const createObjectURL = vi.fn(() => "blob:csv")
    Object.assign(URL, { createObjectURL, revokeObjectURL: vi.fn() })
    renderModal()
    const link = screen.getByTestId("import-template")
    expect(link).toHaveTextContent("Download CSV template")
    fireEvent.click(link)
    expect(createObjectURL).toHaveBeenCalled()
  })

  it("renders the dry-run error table with field-level resolution hints", async () => {
    renderModal()
    await uploadAndDryRun()

    expect(await screen.findByText("Dry-run results · 3 rows")).toBeInTheDocument()
    expect(screen.getByText("ERROR")).toBeInTheDocument()
    expect(screen.getByText("currency")).toBeInTheDocument()
    expect(screen.getByText("Must be a three-letter code.")).toBeInTheDocument()
    expect(screen.getByText(/fix this field and re-run/i)).toBeInTheDocument()
    expect(screen.getByText("Fix and reprocess before creating")).toBeInTheDocument()
  })

  it("leaves the commit button disabled while blocking errors exist", async () => {
    renderModal()
    await uploadAndDryRun()
    await screen.findByText("Fix and reprocess before creating")
    expect(screen.getByTestId("commit-import")).toBeDisabled()
  })

  it("enables the commit button after a clean dry run", async () => {
    requestMock.mockImplementation(async (path: string) => {
      if (path.startsWith("/api/v1/ol-commitments/commitments/import/")) {
        return { dry_run: true, imported: 2, created: 0, errors: [] }
      }
      return {}
    })
    renderModal()
    await uploadAndDryRun()

    expect(await screen.findByText("Dry run passed")).toBeInTheDocument()
    await waitFor(() => expect(screen.getByTestId("commit-import")).toBeEnabled())
  })
})
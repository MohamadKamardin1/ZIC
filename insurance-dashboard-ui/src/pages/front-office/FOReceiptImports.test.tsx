import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { ToastProvider } from "../../components/ui/Toast"
import type { ReceiptImportBatch, ReceiptImportResult } from "../../lib/receipts-api"
import FOReceiptImports from "./FOReceiptImports"

const apiMocks = vi.hoisted(() => ({
  importDryRun: vi.fn(),
  importCommit: vi.fn(),
  imports: vi.fn(),
  importDetail: vi.fn(),
  importReprocess: vi.fn(),
  downloadCsvTemplate: vi.fn(),
}))

vi.mock("../../lib/access", () => ({
  useAccess: () => ({
    access: { permissions: [{ module: "front_office.receipts", action: "import" }] },
    isSuperAdmin: false,
    hasPermission: (code: string) => code === "front_office.receipts.import",
  }),
}))

vi.mock("../../lib/receipts-api", () => ({ receiptsApi: apiMocks }))

const historyBatch: ReceiptImportBatch = {
  id: "import-batch-1",
  file_name: "receipts-2026-08-24.csv",
  uploaded_by_display: "Sultan Admin",
  uploaded_at: "2026-08-24T10:00:00Z",
  total_rows: 2,
  ok_count: 1,
  error_count: 1,
  status: "PARTIAL_FAILURE",
}

const dryRunError: ReceiptImportResult = {
  dry_run: true,
  imported: 2,
  created: 0,
  total_rows: 2,
  ok_count: 1,
  error_count: 1,
  rows: [
    { row: 2, status: "OK", field_errors: {}, resolution_steps: [] },
    { row: 3, status: "ERROR", field_errors: { receipt_amount: ["Enter a positive decimal amount."] }, resolution_steps: ["Correct receipt_amount to a positive number."] },
  ],
  errors: [{ row: 3, status: "ERROR", field_errors: { receipt_amount: ["Enter a positive decimal amount."] }, resolution_steps: ["Correct receipt_amount to a positive number."] }],
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}><MemoryRouter><ToastProvider><FOReceiptImports /></ToastProvider></MemoryRouter></QueryClientProvider>)
}

beforeEach(() => {
  vi.clearAllMocks()
  apiMocks.imports.mockResolvedValue({ count: 1, next: null, previous: null, results: [historyBatch] })
  apiMocks.importDetail.mockResolvedValue({ ...historyBatch, errors: dryRunError.errors })
  apiMocks.importDryRun.mockResolvedValue(dryRunError)
  apiMocks.importCommit.mockResolvedValue({ ...dryRunError, dry_run: false, created: 1 })
  apiMocks.importReprocess.mockResolvedValue({ ...dryRunError, dry_run: false, created: 2, errors: [] })
  apiMocks.downloadCsvTemplate.mockResolvedValue(new Blob(["receipt_date,receipt_amount\n"]))
})

describe("FOReceiptImports Prompt 7", () => {
  it("downloads the CSV template through the authenticated receipt contract", async () => {
    renderPage()
    fireEvent.click(screen.getByRole("button", { name: "Download CSV template" }))
    await waitFor(() => expect(apiMocks.downloadCsvTemplate).toHaveBeenCalledOnce())
  })

  it("shows dry-run row errors and blocks commit until corrected or explicitly partially confirmed", async () => {
    renderPage()
    fireEvent.change(screen.getByLabelText("Receipt CSV file"), { target: { files: [new File(["csv"], "receipts-errors.csv", { type: "text/csv" })] } })
    fireEvent.click(screen.getByRole("button", { name: "Run dry-run" }))
    expect(await screen.findByText("Enter a positive decimal amount.")).toBeInTheDocument()
    expect(screen.getByText(/Commit is disabled until all blocking rows are corrected/)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Commit import" })).toBeDisabled()
    fireEvent.click(screen.getByRole("checkbox", { name: /Allow partial import/ }))
    expect(screen.getByRole("button", { name: "Commit import" })).toBeEnabled()
  })

  it("commits a clean file using the selected post-and-allocate mode", async () => {
    const cleanResult: ReceiptImportResult = { dry_run: true, imported: 2, created: 0, total_rows: 2, ok_count: 2, error_count: 0, rows: [{ row: 2, status: "OK", field_errors: {} }, { row: 3, status: "OK", field_errors: {} }], errors: [] }
    apiMocks.importDryRun.mockResolvedValueOnce(cleanResult)
    renderPage()
    fireEvent.change(screen.getByLabelText("Receipt CSV file"), { target: { files: [new File(["csv"], "receipts-clean.csv", { type: "text/csv" })] } })
    fireEvent.click(screen.getByRole("button", { name: "Run dry-run" }))
    await screen.findByText("All rows passed the dry-run.")
    fireEvent.change(screen.getByRole("combobox", { name: "Import mode" }), { target: { value: "POST_AND_ALLOCATE" } })
    fireEvent.click(screen.getByRole("button", { name: "Commit import" }))
    await waitFor(() => expect(apiMocks.importCommit).toHaveBeenCalledWith(expect.any(File), "POST_AND_ALLOCATE"))
  })

  it("drills into history row errors and reprocesses the selected batch", async () => {
    renderPage()
    fireEvent.click(await screen.findByRole("button", { name: "View rows" }))
    expect(await screen.findByText("Batch row detail")).toBeInTheDocument()
    expect(await screen.findByText("Enter a positive decimal amount.")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Reprocess batch" }))
    await waitFor(() => expect(apiMocks.importReprocess).toHaveBeenCalledWith(historyBatch.id))
  })
})

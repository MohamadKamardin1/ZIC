import { beforeEach, describe, expect, it, vi } from "vitest"
import { request } from "./apiClient"
import { receiptsApi } from "./receipts-api"

vi.mock("./apiClient", async () => {
  const actual = await vi.importActual<typeof import("./apiClient")>("./apiClient")
  return { ...actual, request: vi.fn() }
})

const mockedRequest = vi.mocked(request)

beforeEach(() => {
  mockedRequest.mockReset()
  mockedRequest.mockResolvedValue({} as never)
})

describe("receiptsApi contract surface", () => {
  it("maps list filters, pagination, and search to the receipts endpoint", async () => {
    await receiptsApi.list({ page: 2, page_size: 10, search: "Amani", status: "POSTED", unallocated_only: true })
    expect(mockedRequest.mock.calls[0]?.[0]).toBe("/api/v1/front-office/receipts/?page=2&page_size=10&search=Amani&status=POSTED&unallocated_only=true")
  })

  it("covers create, draft patch, post, and idempotency headers", async () => {
    const payload = { receipt_date: "2026-08-24", branch: "branch-1", payer: "partner-1", currency: "TZS", payment_mode: "CASH", receipt_amount: "100.00" }
    await receiptsApi.create(payload, "idempotency-1")
    expect(mockedRequest).toHaveBeenCalledWith("/api/v1/front-office/receipts/", expect.objectContaining({ method: "POST", body: JSON.stringify(payload), headers: { "X-Idempotency-Key": "idempotency-1" } }))
    await receiptsApi.patchDraft("receipt-1", { narration: "Updated" })
    expect(mockedRequest).toHaveBeenCalledWith("/api/v1/front-office/receipts/receipt-1/", expect.objectContaining({ method: "PATCH" }))
    await receiptsApi.post("receipt-1", "post-key")
    expect(mockedRequest).toHaveBeenCalledWith("/api/v1/front-office/receipts/receipt-1/post/", expect.objectContaining({ method: "POST", headers: { "X-Idempotency-Key": "post-key" } }))
  })

  it("covers allocation, lifecycle, print, and document endpoints", async () => {
    await receiptsApi.allocationOptions("receipt-1", { search: "OLC" })
    await receiptsApi.allocate("receipt-1", { allocations: [{ commitment: "commitment-1", amount: "50.00", exchange_rate: "1" }] })
    await receiptsApi.autoAllocate("receipt-1")
    await receiptsApi.reverse("receipt-1", { reason: "Duplicate payment" })
    await receiptsApi.reverseAllocation("receipt-1", "allocation-1", { reason: "Correction" })
    await receiptsApi.cancel("receipt-1", { reason: "Draft error" })
    await receiptsApi.print("receipt-1")
    await receiptsApi.documents("receipt-1")
    const calls = mockedRequest.mock.calls.map(([path]) => path)
    expect(calls).toEqual(expect.arrayContaining([
      "/api/v1/front-office/receipts/receipt-1/allocation-options/?search=OLC",
      "/api/v1/front-office/receipts/receipt-1/allocate/",
      "/api/v1/front-office/receipts/receipt-1/auto-allocate/",
      "/api/v1/front-office/receipts/receipt-1/reverse/",
      "/api/v1/front-office/receipts/receipt-1/allocations/allocation-1/reverse/",
      "/api/v1/front-office/receipts/receipt-1/cancel/",
      "/api/v1/front-office/receipts/receipt-1/print/",
      "/api/v1/front-office/receipts/receipt-1/documents/",
    ]))
  })

  it("uses multipart forms for imports and covers KPIs, options, and portal", async () => {
    const file = new Blob(["receipt_number\nRCT-1\n"], { type: "text/csv" })
    await receiptsApi.importDryRun(file)
    expect(mockedRequest).toHaveBeenCalledWith("/api/v1/front-office/receipts/import/dry-run/", expect.objectContaining({ method: "POST", body: expect.any(FormData) }))
    await receiptsApi.importCommit(file, "POST_AND_ALLOCATE")
    await receiptsApi.imports({ page: 2, page_size: 25 })
    await receiptsApi.importDetail("import-1")
    await receiptsApi.kpis({ date_from: "2026-08-01", date_to: "2026-08-24" })
    await receiptsApi.exchangeRate("USD", "2026-08-24")
    await receiptsApi.options.branches("Zan")
    await receiptsApi.options.currencies()
    await receiptsApi.options.paymentModes()
    await receiptsApi.options.bankAccounts()
    await receiptsApi.options.statuses()
    await receiptsApi.portal.list()
    await receiptsApi.portal.get("receipt-1")
    const calls = mockedRequest.mock.calls.map(([path]) => path)
    expect(calls).toContain("/api/v1/front-office/receipts/import/commit/")
    expect(calls).toContain("/api/v1/front-office/receipts/imports/?page=2&page_size=25")
    expect(calls).toContain("/api/v1/front-office/receipts/kpis/?date_from=2026-08-01&date_to=2026-08-24")
    expect(calls).toContain("/api/v1/front-office/options/branches/?q=Zan")
    expect(calls).toContain("/api/v1/portal/receipts/")
    expect(calls).toContain("/api/v1/portal/receipts/receipt-1/")
  })
})

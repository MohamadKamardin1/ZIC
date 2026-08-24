import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest"
import { server } from "./server"

beforeAll(() => server.listen({ onUnhandledRequest: "error" }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe("receipts MSW contract", () => {
  it("returns paginated receipts with human-readable display fields", async () => {
    const response = await fetch("http://localhost/api/v1/front-office/receipts/?page=1&page_size=10&search=Amani")
    expect(response.status).toBe(200)
    const body = await response.json()
    expect(body.data.results[0]).toMatchObject({ receipt_number: "RCT-2026-000001", payer_display: "Amani Assurance Partner", branch_display: "Zanzibar Main Branch", currency_display: "TZS — Tanzanian Shilling" })
  })

  it("returns labeled option payloads and payment-mode metadata", async () => {
    const response = await fetch("http://localhost/api/v1/front-office/options/payment-modes/?q=mobile")
    expect(response.status).toBe(200)
    const body = await response.json()
    expect(body.data.results).toEqual([expect.objectContaining({ value: "MOBILE_MONEY", label: "Mobile Money", meta: { requires_reference: true, requires_bank_account: false } })])
  })

  it("returns the structured teachable over-allocation error", async () => {
    const response = await fetch("http://localhost/api/v1/front-office/receipts/receipt-demo-1/allocate/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ allocations: [{ commitment: "commitment-1", amount: "999999.00" }] }) })
    expect(response.status).toBe(422)
    const body = await response.json()
    expect(body).toMatchObject({ errorCode: "RECEIPT_OVERALLOCATION", message: expect.stringContaining("unallocated"), resolutionSteps: expect.arrayContaining([expect.stringContaining("Reduce")]) })
  })
})

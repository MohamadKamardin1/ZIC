import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from "vitest"
import { resetWithdrawalMockState } from "./withdrawalsHandlers"
import { server } from "./server"

beforeAll(() => server.listen({ onUnhandledRequest: "error" }))
afterEach(() => {
  server.resetHandlers()
  resetWithdrawalMockState()
})
afterAll(() => server.close())
beforeEach(() => resetWithdrawalMockState())

describe("OL Withdrawals MSW contract", () => {
  it("returns a paginated register with human-readable policy and financial fields", async () => {
    const response = await fetch("http://localhost/api/v1/ol/withdrawals/?page=1&page_size=10&q=Amani")
    expect(response.status).toBe(200)
    const body = await response.json()
    expect(body.data.results[0]).toMatchObject({
      withdrawal_number: "OL-WDR-2026-000001",
      policy_display: "ZIC-OL-2026-000001 — Amani Salum",
      policyholder_name: "Amani Salum",
      product_display: "OL_EDU_GROWTH — Elimu Bora Growth Plan",
      gross_amount: "250000.00",
      fee_amount: "12500.00",
      net_payout: "237500.00",
      status_display: "Requested",
    })
  })

  it("returns searchable option catalogs and a structured unknown-catalog error", async () => {
    const optionResponse = await fetch("http://localhost/api/v1/ol/withdrawals/options/policies/?q=Amani")
    expect(optionResponse.status).toBe(200)
    const optionBody = await optionResponse.json()
    expect(optionBody.data.results).toEqual([expect.objectContaining({ value: "policy-aman-1", label: "ZIC-OL-2026-000001 — Amani Salum" })])
    expect(optionBody.data.results[0].meta).toMatchObject({ available_limit: "2350000.00", status: "ACTIVE" })

    const unknownResponse = await fetch("http://localhost/api/v1/ol/withdrawals/options/not-registered/")
    expect(unknownResponse.status).toBe(404)
    const unknownBody = await unknownResponse.json()
    expect(unknownBody).toMatchObject({ errorCode: "OPTIONS_ENTITY_NOT_FOUND", error: { code: "OPTIONS_ENTITY_NOT_FOUND" } })
  })

  it("returns nested breakdown, payment, and audit resources plus secure print data", async () => {
    const [detailResponse, breakdownResponse, paymentsResponse, auditResponse, printResponse] = await Promise.all([
      fetch("http://localhost/api/v1/ol/withdrawals/withdrawal-paid-1/"),
      fetch("http://localhost/api/v1/ol/withdrawals/withdrawal-paid-1/breakdown/"),
      fetch("http://localhost/api/v1/ol/withdrawals/withdrawal-paid-1/payments/"),
      fetch("http://localhost/api/v1/ol/withdrawals/withdrawal-paid-1/audit/"),
      fetch("http://localhost/api/v1/ol/withdrawals/withdrawal-paid-1/print-statement/", { method: "POST" }),
    ])
    expect(detailResponse.status).toBe(200)
    expect(breakdownResponse.status).toBe(200)
    expect(paymentsResponse.status).toBe(200)
    expect(auditResponse.status).toBe(200)
    expect(printResponse.status).toBe(201)

    const detail = await detailResponse.json()
    const breakdown = await breakdownResponse.json()
    const payments = await paymentsResponse.json()
    const audit = await auditResponse.json()
    const print = await printResponse.json()
    expect(detail.data).toMatchObject({ status_display: "Paid", policyholder_display: "P-000021 — Fatma Ali" })
    expect(detail.data.breakdown).toMatchObject({ fee_basis: "5% fixed", adjustment_ratio: "10.0000" })
    expect(breakdown.data).toMatchObject({ cash_value_after: "1100000.00", net_payout: "95000.00" })
    expect(payments.data.results[0]).toMatchObject({ payment_mode_display: "Bank transfer", receipt_reference: "RCT-2026-000001" })
    expect(audit.data.results[0]).toMatchObject({ actor_display: "Sultan Admin", source_channel: "API" })
    expect(print.data).toMatchObject({ instance: { document_type: "OL_WITHDRAWAL_STATEMENT", template_version: 1 }, signed_download_url: expect.stringContaining("ticket=mock-withdrawal-withdrawal-paid-1") })
  })

  it("returns only linked partner withdrawals and sanitizes sensitive fields by default", async () => {
    const listingResponse = await fetch("http://localhost/api/v1/portal/withdrawals/?page=1&page_size=10")
    expect(listingResponse.status).toBe(200)
    const listingBody = await listingResponse.json()
    expect(listingBody.data.count).toBe(1)
    expect(listingBody.data.results[0]).toMatchObject({ request_number: "OL-WDR-2026-000001", policy_number: "ZIC-OL-2026-000001", status_display: "Requested", request_allowed: true })
    expect(listingBody.data.results[0]).not.toHaveProperty("fee_amount")
    expect(listingBody.data.results[0]).not.toHaveProperty("cash_value_before")

    const detailResponse = await fetch("http://localhost/api/v1/portal/withdrawals/withdrawal-requested-1/")
    expect(detailResponse.status).toBe(200)
    const detailBody = await detailResponse.json()
    expect(detailBody.data).toMatchObject({ request_number: "OL-WDR-2026-000001", policyholder_display: "P-000001 — Amani Salum" })
    expect(detailBody.data).not.toHaveProperty("loan_balance_before")

    const requestResponse = await fetch("http://localhost/api/v1/portal/withdrawals/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ policy_id: "policy-aman-1", amount: "125000.00", reason: "Education fees" }) })
    expect(requestResponse.status).toBe(201)
    const requestBody = await requestResponse.json()
    expect(requestBody.data.withdrawal).toMatchObject({ policy_id: "policy-aman-1", status: "REQUESTED", reason: "Education fees" })
  })

  it("returns teachable lifecycle validation and changes a requested withdrawal to approved", async () => {
    const invalidResponse = await fetch("http://localhost/api/v1/ol/withdrawals/withdrawal-requested-1/reject/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) })
    expect(invalidResponse.status).toBe(400)
    const invalidBody = await invalidResponse.json()
    expect(invalidBody).toMatchObject({ errorCode: "REASON_REQUIRED", fieldErrors: { reason: ["Enter a reason."] } })

    const approveResponse = await fetch("http://localhost/api/v1/ol/withdrawals/withdrawal-requested-1/approve/", { method: "POST" })
    expect(approveResponse.status).toBe(200)
    const approveBody = await approveResponse.json()
    expect(approveBody.data.withdrawal).toMatchObject({ status: "APPROVED", status_display: "Approved", approved_at: "2026-08-27T09:00:00Z" })
  })
})

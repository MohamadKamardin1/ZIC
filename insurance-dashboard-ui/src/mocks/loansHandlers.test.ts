import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest"
import { resetLoanMockState } from "./loansHandlers"
import { server } from "./server"

beforeAll(() => server.listen({ onUnhandledRequest: "error" }))
afterEach(() => {
  server.resetHandlers()
  resetLoanMockState()
})
afterAll(() => server.close())

describe("OL Loans MSW contract", () => {
  it("returns a paginated labeled loan register and nested detail data", async () => {
    const listResponse = await fetch("http://localhost/api/v1/ol/loans/?page=1&page_size=10&q=Amani")
    expect(listResponse.status).toBe(200)
    const listBody = await listResponse.json()
    expect(listBody.data.results[0]).toMatchObject({ loan_number: "OL-LOAN-2026-000001", policyholder_name: "Amani Salum", product_display: "OL_EDU_GROWTH — Elimu Bora Growth Plan", branch_display: "ZNZ-MAIN — Zanzibar Main Branch" })

    const detailResponse = await fetch("http://localhost/api/v1/ol/loans/loan-active-1/")
    expect(detailResponse.status).toBe(200)
    const detailBody = await detailResponse.json()
    expect(detailBody.data.schedules).toHaveLength(2)
    expect(detailBody.data.repayments[0]).toMatchObject({ receipt_number: "RCT-2026-000013" })
    expect(detailBody.data.header).toMatchObject({ loan_number: "OL-LOAN-2026-000001", policyholder_name: "Amani Salum" })
  })

  it("returns searchable options and a structured unknown-catalog error", async () => {
    const optionResponse = await fetch("http://localhost/api/v1/ol/loans/options/repayment-terms/?q=maturity")
    expect(optionResponse.status).toBe(200)
    const optionBody = await optionResponse.json()
    expect(optionBody.data.results).toEqual([expect.objectContaining({ value: "DEDUCTION_FROM_MATURITY", label: "Deduction from maturity" })])

    const unknownResponse = await fetch("http://localhost/api/v1/ol/loans/options/not-registered/")
    expect(unknownResponse.status).toBe(404)
    const unknownBody = await unknownResponse.json()
    expect(unknownBody).toMatchObject({ errorCode: "OPTIONS_ENTITY_NOT_FOUND", error: { code: "OPTIONS_ENTITY_NOT_FOUND" } })
  })

  it("returns a paginated schedule and full-schedule aggregates", async () => {
    const response = await fetch("http://localhost/api/v1/ol/loans/loan-active-1/schedule/?page=1&page_size=1")
    expect(response.status).toBe(200)
    const body = await response.json()
    expect(body.data.results).toHaveLength(1)
    expect(body.data.results[0]).toMatchObject({ installment_number: 1, status: "PAID" })
    expect(body.data).toMatchObject({ count: 2, next: true, aggregates: { total_scheduled: "173333.34", total_paid: "86666.67", remaining_balance: "86666.67" } })
  })

  it("returns KPI and secure print contracts", async () => {
    const [kpiResponse, printResponse] = await Promise.all([
      fetch("http://localhost/api/v1/ol/loans/kpis/"),
      fetch("http://localhost/api/v1/ol/loans/loan-active-1/print-agreement/", { method: "POST" }),
    ])
    expect(kpiResponse.status).toBe(200)
    expect(printResponse.status).toBe(201)
    const kpis = await kpiResponse.json()
    const print = await printResponse.json()
    expect(kpis.data).toMatchObject({ active_count: 1, defaulted_count: 1, currency: "TZS" })
    expect(print.data).toMatchObject({ instance: { document_type: "OL_LOAN_AGREEMENT", template_version: 1 }, signed_download_url: expect.stringContaining("ticket=mock-agreement-loan-active-1") })
  })
})

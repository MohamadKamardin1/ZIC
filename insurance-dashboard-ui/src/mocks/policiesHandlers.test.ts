import { beforeAll, afterAll, afterEach, describe, expect, it } from "vitest"
import { server } from "./server"

beforeAll(() => server.listen({ onUnhandledRequest: "error" }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe("OL Policies MSW contract", () => {
  it("returns a paginated labeled policy register", async () => {
    const response = await fetch("http://localhost/api/v1/ol/policies/?page=1&page_size=10&search=Amani")
    expect(response.status).toBe(200)
    const body = await response.json()
    expect(body.data.results[0]).toMatchObject({ policy_number: "ZIC-OL-2026-000001", policyholder_display: "P-000018 — Amani Salum", product_plan_display: "OL_EDU_GROWTH — Elimu Bora Growth Plan", agent_display: "AG-0004 — Faraja Intermediaries" })
  })

  it("returns detail children and KPI data", async () => {
    const [detailResponse, kpiResponse] = await Promise.all([
      fetch("http://localhost/api/v1/ol/policies/policy-active-1/"),
      fetch("http://localhost/api/v1/ol/policies/kpis/?currency=TZS"),
    ])
    expect(detailResponse.status).toBe(200)
    expect(kpiResponse.status).toBe(200)
    const detail = await detailResponse.json()
    const kpis = await kpiResponse.json()
    expect(detail.data.members[0]).toMatchObject({ name: "Amani Salum", member_relation: "Principal member" })
    expect(detail.data.linked_proposal).toMatchObject({ status: "CONVERTED" })
    expect(kpis.data).toMatchObject({ total_active_policies: 2, currency: "TZS" })
  })

  it("returns a secure policy contract print result", async () => {
    const response = await fetch("http://localhost/api/v1/ol/policies/policy-active-1/print-contract/", { method: "POST", body: JSON.stringify({}), headers: { "Content-Type": "application/json" } })
    expect(response.status).toBe(201)
    const body = await response.json()
    expect(body.data).toMatchObject({ instance: { document_type: "POLICY_CONTRACT", template_version: 1 }, signed_download_url: expect.stringContaining("ticket=mock-policy-active-1-policy_contract") })
  })

  it("enforces terminal-flow eligibility and returns realistic response envelopes", async () => {
    const surrenderResponse = await fetch("http://localhost/api/v1/ol/policies/policy-active-1/surrender/", { method: "POST", body: JSON.stringify({ reason: "Customer request" }), headers: { "Content-Type": "application/json" } })
    expect(surrenderResponse.status).toBe(201)
    const surrender = await surrenderResponse.json()
    expect(surrender.data).toMatchObject({ created: true, surrender_request: { status: "SURRENDER_PENDING", net_surrender_value: "8750000.00" }, policy: { status: "SURRENDER_PENDING", status_display: "Surrender pending" } })

    const paidUpResponse = await fetch("http://localhost/api/v1/ol/policies/policy-lapsed-1/paid-up/", { method: "POST", body: JSON.stringify({}), headers: { "Content-Type": "application/json" } })
    expect(paidUpResponse.status).toBe(200)
    const paidUp = await paidUpResponse.json()
    expect(paidUp.data).toMatchObject({ status: "PAID_UP", status_display: "Paid-up", allowed_actions: ["view", "print"] })

    const missingReasonResponse = await fetch("http://localhost/api/v1/ol/policies/policy-active-1/cancel/", { method: "POST", body: JSON.stringify({}), headers: { "Content-Type": "application/json" } })
    expect(missingReasonResponse.status).toBe(400)
    const missingReason = await missingReasonResponse.json()
    expect(missingReason).toMatchObject({ errorCode: "POLICY_CANCELLATION_REASON_REQUIRED", fieldErrors: { reason: [expect.any(String)] } })

    const cancelResponse = await fetch("http://localhost/api/v1/ol/policies/policy-active-1/cancel/", { method: "POST", body: JSON.stringify({ reason: "Free-look cancellation" }), headers: { "Content-Type": "application/json" } })
    expect(cancelResponse.status).toBe(200)
    const cancelled = await cancelResponse.json()
    expect(cancelled.data).toMatchObject({ policy: { status: "CANCELLED" }, refund: { amount: "120000.00", requisition_number: "REF-2026-000001" } })
  })

  it("returns searchable standard policy options and a structured unknown-entity error", async () => {
    const optionResponse = await fetch("http://localhost/api/v1/ol/options/statuses/?q=lapsed")
    expect(optionResponse.status).toBe(200)
    const optionBody = await optionResponse.json()
    expect(optionBody.data.results).toEqual([expect.objectContaining({ value: "LAPSED", label: "Lapsed", meta: { badge_type: "WARNING" } })])

    const unknownResponse = await fetch("http://localhost/api/v1/ol/options/not-registered/")
    expect(unknownResponse.status).toBe(404)
    const unknownBody = await unknownResponse.json()
    expect(unknownBody).toMatchObject({ errorCode: "OPTIONS_ENTITY_NOT_FOUND", error: { code: "OPTIONS_ENTITY_NOT_FOUND" } })
  })
})

describe("OL Policies MSW contract — matured-policy search for the plan wizard", () => {
  it("returns only matured policies with a maturity value when filtered by status", async () => {
    const response = await fetch("http://localhost/api/v1/ol/policies/?page=1&page_size=10&status=MATURED")
    expect(response.status).toBe(200)
    const body = await response.json()
    expect(body.data.results.length).toBeGreaterThan(0)
    for (const row of body.data.results) {
      expect(row.status).toBe("MATURED")
      expect(row.status_display).toBe("Matured")
      expect(row.maturity_value).toBeTruthy()
    }
    expect(body.data.results).toEqual(expect.arrayContaining([
      expect.objectContaining({ policy_number: "ZIC-OL-2025-000101", maturity_value: "60000000.00" }),
    ]))
  })

  it("excludes immature policies from the matured search by policy number", async () => {
    const response = await fetch("http://localhost/api/v1/ol/policies/?page=1&page_size=10&status=MATURED&search=ZIC-OL-2026-000001")
    expect(response.status).toBe(200)
    const body = await response.json()
    expect(body.data.count).toBe(0)
    expect(body.data.results).toEqual([])
  })

  it("still returns the immature policy when the status filter is absent", async () => {
    const response = await fetch("http://localhost/api/v1/ol/policies/?page=1&page_size=10&search=ZIC-OL-2026-000001")
    expect(response.status).toBe(200)
    const body = await response.json()
    expect(body.data.results[0]).toMatchObject({ policy_number: "ZIC-OL-2026-000001", status: "ACTIVE" })
  })
})

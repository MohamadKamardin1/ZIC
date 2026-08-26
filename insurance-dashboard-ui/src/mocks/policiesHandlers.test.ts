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

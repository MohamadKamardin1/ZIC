import { beforeEach, describe, expect, it, vi } from "vitest"

const { requestMock } = vi.hoisted(() => ({ requestMock: vi.fn() }))

vi.mock("./apiClient", () => ({ request: requestMock }))

import { getPortalPolicy, listPortalPolicies, listPortalPolicyDocuments } from "./policyPortal"

beforeEach(() => requestMock.mockReset())

describe("partner policy portal API contract", () => {
  it("normalizes the partner-scoped list without requiring staff-only fields", async () => {
    requestMock.mockResolvedValue({ count: 1, results: [{ policy_number: "ZIC-OL-2026-000001", status: "ACTIVE", product_plan: "OL_EDU_GROWTH — Elimu Bora Growth Plan", risk_commencement_date: "2026-01-15", maturity_date: "2041-01-15", currency: "TZS" }] })

    const result = await listPortalPolicies()

    expect(requestMock).toHaveBeenCalledWith("/api/v1/ol/policies/portal/")
    expect(result).toEqual({ count: 1, results: [expect.objectContaining({ policyNumber: "ZIC-OL-2026-000001", productPlanDisplay: "OL_EDU_GROWTH — Elimu Bora Growth Plan", status: "ACTIVE", currency: "TZS" })] })
  })

  it("loads one partner policy detail through the scoped route", async () => {
    requestMock.mockResolvedValue({ policy_number: "ZIC-OL-2026-000001", status: "ACTIVE", product_plan: "OL_EDU_GROWTH — Elimu Bora Growth Plan", currency: "TZS", sum_assured: "25000000.00", premium_amount: "120000.00", premium_frequency: "MONTHLY" })

    const result = await getPortalPolicy("policy-1")

    expect(requestMock).toHaveBeenCalledWith("/api/v1/ol/policies/portal/policy-1/")
    expect(result).toMatchObject({ policyNumber: "ZIC-OL-2026-000001", productPlanDisplay: "OL_EDU_GROWTH — Elimu Bora Growth Plan", sumAssured: "25000000.00", premiumAmount: "120000.00", premiumFrequency: "MONTHLY" })
  })

  it("requests read-only document metadata without exposing secure download URLs", async () => {
    requestMock.mockResolvedValue({ count: 1, results: [{ id: "document-1", document_type: "POLICY_CONTRACT", template_name: "Policy Contract", template_version: 2, generated_by_display: "Sultan Admin", generated_at: "2026-08-26T10:00:00Z", page_count: 2, signed_download_url: "/api/v1/documents/instances/document-1/download/?ticket=secret" }] })

    const result = await listPortalPolicyDocuments("policy-1")

    expect(requestMock).toHaveBeenCalledWith(expect.stringContaining("/api/v1/documents/instances/?"))
    expect(requestMock.mock.calls[0][0]).toContain("source_type=ol_policies.policy")
    expect(requestMock.mock.calls[0][0]).toContain("object_id=policy-1")
    expect(result).toEqual([expect.objectContaining({ id: "document-1", documentType: "POLICY_CONTRACT", templateName: "Policy Contract", templateVersion: "2", generatedByDisplay: "Sultan Admin", pageCount: 2 })])
    expect(result[0]).not.toHaveProperty("signed_download_url")
  })
})

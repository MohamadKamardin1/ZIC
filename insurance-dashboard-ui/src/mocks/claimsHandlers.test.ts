import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from "vitest"
import { resetClaimMockState } from "./claimsHandlers"
import { server } from "./server"

beforeAll(() => server.listen({ onUnhandledRequest: "error" }))
afterEach(() => {
  server.resetHandlers()
  resetClaimMockState()
})
afterAll(() => server.close())
beforeEach(() => resetClaimMockState())

describe("OL Claims MSW contract", () => {
  it("returns a paginated register with human-readable policy and lifecycle fields", async () => {
    const response = await fetch("http://localhost/api/v1/ol/claims/?page=1&page_size=10&q=Amani")
    expect(response.status).toBe(200)
    const body = await response.json()
    expect(body.data.results[0]).toMatchObject({
      claim_number: "OL-CLM-2026-000001",
      policy_number: "ZIC-OL-2026-000001",
      policyholder_name: "Amani Salum",
      product_display: "OL_EDU_GROWTH — Elimu Bora Growth Plan",
      status_display: "Registered",
      allowed_actions: ["view", "assess", "cancel", "print"],
    })
    expect(body.data.results[0].id).not.toContain("uuid")
  })

  it("returns claim KPIs with outstanding, settled, and pending-assessment aggregates", async () => {
    const response = await fetch("http://localhost/api/v1/ol/claims/kpis/")
    expect(response.status).toBe(200)
    const body = await response.json()
    expect(body.data).toMatchObject({
      total_claims: 8,
      pending_assessment_count: 2,
      currency: "TZS",
    })
    expect(body.data.outstanding_amount).toMatch(/^\d+\.\d{2}$/)
    expect(body.data.currency_totals.TZS).toMatchObject({ outstanding_amount: expect.any(String), settled_amount: expect.any(String) })
  })

  it("returns searchable option catalogs and enforces policy-scoped benefit and member lookups", async () => {
    const typeResponse = await fetch("http://localhost/api/v1/ol/claims/options/types/?q=Maternity")
    expect(typeResponse.status).toBe(200)
    const typeBody = await typeResponse.json()
    expect(typeBody.data.results).toEqual([expect.objectContaining({ value: "MATERNITY", label: "Maternity Benefit" })])

    const benefitResponse = await fetch("http://localhost/api/v1/ol/claims/options/benefits/?policy_id=policy-fatma-1")
    expect(benefitResponse.status).toBe(200)
    const benefitBody = await benefitResponse.json()
    expect(benefitBody.data.results[0]).toMatchObject({ value: "CI_BENEFIT", meta: { sum_assured: "1500000.00" } })

    const noPolicyResponse = await fetch("http://localhost/api/v1/ol/claims/options/benefits/")
    expect(noPolicyResponse.status).toBe(400)
    const noPolicyBody = await noPolicyResponse.json()
    expect(noPolicyBody).toMatchObject({ errorCode: "CLAIM_POLICY_REQUIRED" })

    const memberResponse = await fetch("http://localhost/api/v1/ol/claims/options/members/?policy_id=policy-aman-1")
    expect(memberResponse.status).toBe(200)
    const memberBody = await memberResponse.json()
    expect(memberBody.data.results[0]).toMatchObject({ value: "claimant-aman-1", label: "Amani Salum — Policyholder" })
  })

  it("returns a nested detail workspace with documents, notes, financials, and audit history", async () => {
    const [detailResponse, documentsResponse, notesResponse, financialResponse] = await Promise.all([
      fetch("http://localhost/api/v1/ol/claims/claim-approved-1/"),
      fetch("http://localhost/api/v1/ol/claims/claim-approved-1/documents/"),
      fetch("http://localhost/api/v1/ol/claims/claim-approved-1/notes/"),
      fetch("http://localhost/api/v1/ol/claims/claim-approved-1/financial-summary/"),
    ])
    expect(detailResponse.status).toBe(200)
    expect(documentsResponse.status).toBe(200)
    expect(notesResponse.status).toBe(200)
    expect(financialResponse.status).toBe(200)

    const detail = await detailResponse.json()
    const documents = await documentsResponse.json()
    const notes = await notesResponse.json()
    const financial = await financialResponse.json()
    expect(detail.data).toMatchObject({ status_display: "Approved", policyholder_display: "P-000078 — Mariam Juma", medical_result: "LOADING", medical_loading_factor: "1.25" })
    expect(detail.data.items[0]).toMatchObject({ benefit_type: "CI_BENEFIT", approved_amount: "4000000.00" })
    expect(detail.data.claimant).toMatchObject({ name: "Mariam Juma", claimant_type: "POLICYHOLDER" })
    expect(detail.data.audit_timeline.map((entry: { action: string }) => entry.action)).toEqual(expect.arrayContaining(["REGISTERED", "MEDICAL_REVIEW_COMPLETED", "ASSESSED", "APPROVED"]))
    expect(documents.data.all_mandatory_uploaded).toBe(false)
    expect(documents.data.missing_document_types).toContain("IDENTITY_DOCUMENT")
    expect(notes.data[0]).toMatchObject({ author_display: "Finance Manager — Yusuf A." })
    expect(financial.data).toMatchObject({ net_payout: "4000000.00", loan_offset_applied: false })
  })

  it("registers a claim with an idempotency key and rejects requests without one", async () => {
    const missingKeyResponse = await fetch("http://localhost/api/v1/ol/policies/policy-aman-1/claims/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ claim_type: "MATERNITY", claim_date: "2026-08-20" }) })
    expect(missingKeyResponse.status).toBe(400)
    const missingKeyBody = await missingKeyResponse.json()
    expect(missingKeyBody).toMatchObject({ errorCode: "CLAIM_IDEMPOTENCY_REQUIRED" })

    const registeredResponse = await fetch("http://localhost/api/v1/ol/policies/policy-aman-1/claims/", { method: "POST", headers: { "Content-Type": "application/json", "X-Idempotency-Key": "test-key-1" }, body: JSON.stringify({ claim_type: "MATERNITY", claim_date: "2026-08-20", benefit_type: "MATERNITY_BENEFIT", cause_of_claim: "Maternity hospitalisation", member_id: "claimant-aman-1" }) })
    expect(registeredResponse.status).toBe(201)
    const registeredBody = await registeredResponse.json()
    expect(registeredBody.data.claim).toMatchObject({ policy_number: "ZIC-OL-2026-000001", status: "REGISTERED", claim_type: "MATERNITY", policyholder_display: "P-000001 — Amani Salum" })

    const lapsedResponse = await fetch("http://localhost/api/v1/ol/policies/policy-lapsed-1/claims/", { method: "POST", headers: { "Content-Type": "application/json", "X-Idempotency-Key": "test-key-2" }, body: JSON.stringify({ claim_type: "HOSPITAL_CASH", claim_date: "2026-08-20", member_id: "claimant-lapsed-1" }) })
    expect(lapsedResponse.status).toBe(422)
    const lapsedBody = await lapsedResponse.json()
    expect(lapsedBody).toMatchObject({ errorCode: "CLAIM_POLICY_INACTIVE" })
  })

  it("walks the lifecycle: assessment, requisition, and settlement with progression guards", async () => {
    const assessMissingMedical = await fetch("http://localhost/api/v1/ol/claims/claim-registered-1/assess/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ assessed_amount: "250000.00", assessment_notes: "Approved." }) })
    expect(assessMissingMedical.status).toBe(422)
    expect((await assessMissingMedical.json())).toMatchObject({ errorCode: "CLAIM_MEDICAL_REVIEW_REQUIRED" })

    const requireMedical = await fetch("http://localhost/api/v1/ol/claims/claim-registered-1/medical/require/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ reason: "Specialist confirmation required." }) })
    expect(requireMedical.status).toBe(201)
    expect((await requireMedical.json()).data.medical_status).toBe("REQUESTED")

    const medicalResult = await fetch("http://localhost/api/v1/ol/claims/claim-registered-1/medical/result/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ result: "CLEARED", reason: "Specialist report confirms diagnosis." }) })
    expect(medicalResult.status).toBe(201)
    expect((await medicalResult.json()).data.medical_result).toBe("CLEARED")

    const assessMissingDoc = await fetch("http://localhost/api/v1/ol/claims/claim-registered-1/assess/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ assessed_amount: "250000.00", assessment_notes: "Approved." }) })
    expect(assessMissingDoc.status).toBe(422)
    expect((await assessMissingDoc.json())).toMatchObject({ errorCode: "CLAIM_MANDATORY_DOC_MISSING" })

    const uploadDocument = (documentType: string) => {
      const boundary = `----vitestBoundary${documentType}`
      const body = [
        `--${boundary}`,
        `Content-Disposition: form-data; name="document_type"`,
        ``,
        documentType,
        `--${boundary}`,
        `Content-Disposition: form-data; name="file"; filename="${documentType}.pdf"`,
        `Content-Type: application/pdf`,
        ``,
        `mock-pdf-content`,
        `--${boundary}--`,
        ``,
      ].join("\r\n")
      return fetch("http://localhost/api/v1/ol/claims/claim-registered-1/documents/", { method: "POST", headers: { "Content-Type": `multipart/form-data; boundary=${boundary}` }, body })
    }
    for (const documentType of ["MEDICAL_REPORT", "HOSPITAL_DISCHARGE", "IDENTITY_DOCUMENT"]) {
      const uploadResponse = await uploadDocument(documentType)
      expect(uploadResponse.status).toBe(201)
    }

    const assess = await fetch("http://localhost/api/v1/ol/claims/claim-registered-1/assess/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ assessed_amount: "250000.00", assessment_notes: "Approved." }) })
    expect(assess.status).toBe(201)
    expect((await assess.json()).data.status).toBe("ASSESSED")

    const requisitionNoBank = await fetch("http://localhost/api/v1/ol/claims/claim-registered-1/raise-requisition/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) })
    expect(requisitionNoBank.status).toBe(400)
    expect((await requisitionNoBank.json())).toMatchObject({ errorCode: "CLAIM_REQUISITION_BANK_DETAILS_REQUIRED" })

    const requisition = await fetch("http://localhost/api/v1/ol/claims/claim-registered-1/raise-requisition/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ bank_details: { account_holder: "Amani Salum", account_number: "0150-0999-8877", bank_name: "CRDB Bank" }, narration: "Claim settlement payment" }) })
    expect(requisition.status).toBe(201)
    expect((await requisition.json()).data.requisition).toMatchObject({ status_display: "Pending", approval_required: true })

    const settleNoReference = await fetch("http://localhost/api/v1/ol/claims/claim-registered-1/settle/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) })
    expect(settleNoReference.status).toBe(400)
    expect((await settleNoReference.json())).toMatchObject({ errorCode: "CLAIM_SETTLEMENT_PAYMENT_REFERENCE_REQUIRED" })

    const settle = await fetch("http://localhost/api/v1/ol/claims/claim-registered-1/settle/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ payment_reference: "FO-PAY-2026-000099" }) })
    expect(settle.status).toBe(201)
    const settleBody = await settle.json()
    expect(settleBody.data.claim.status).toBe("SETTLED")
    expect(settleBody.data.claim.allowed_actions).toEqual(["view", "print"])
  })

  it("returns a printable discharge voucher for settled claims and a teachable not-found error", async () => {
    const printResponse = await fetch("http://localhost/api/v1/ol/claims/claim-settled-1/print-discharge-voucher/", { method: "POST" })
    expect(printResponse.status).toBe(201)
    const printBody = await printResponse.json()
    expect(printBody.data).toMatchObject({ instance: { document_type: "OL_CLAIM_DISCHARGE_VOUCHER", template_version: 1 }, signed_download_url: expect.stringContaining("ticket=mock-voucher-claim-settled-1") })

    const notFoundResponse = await fetch("http://localhost/api/v1/ol/claims/does-not-exist/")
    expect(notFoundResponse.status).toBe(404)
    const notFoundBody = await notFoundResponse.json()
    expect(notFoundBody).toMatchObject({ errorCode: "CLAIM_NOT_FOUND", resolutionSteps: expect.any(Array) })
  })
})

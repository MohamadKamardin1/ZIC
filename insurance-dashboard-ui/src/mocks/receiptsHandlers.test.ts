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

  it("returns payer, proposal, and source-module options for receipt creation", async () => {
    const [payerResponse, proposalResponse, sourceResponse] = await Promise.all([
      fetch("http://localhost/api/v1/front-office/options/payers/?q=Amani"),
      fetch("http://localhost/api/v1/front-office/options/proposals/?q=OLP"),
      fetch("http://localhost/api/v1/front-office/options/source-modules/"),
    ])
    expect(payerResponse.status).toBe(200)
    expect(proposalResponse.status).toBe(200)
    expect(sourceResponse.status).toBe(200)
    const payerBody = await payerResponse.json()
    const proposalBody = await proposalResponse.json()
    const sourceBody = await sourceResponse.json()
    expect(payerBody.data.results[0]).toMatchObject({ value: "partner-amani", label: "Amani Assurance Partner" })
    expect(proposalBody.data.results[0]).toMatchObject({ label: expect.stringContaining("OLP-2026-000001"), meta: { status_hint: "First premium due" } })
    expect(sourceBody.data.results).toEqual(expect.arrayContaining([expect.objectContaining({ value: "OL_PROPOSAL", label: "Ordinary Life proposal" })]))
  })

  it("persists an idempotent draft update and post transition", async () => {
    const createResponse = await fetch("http://localhost/api/v1/front-office/receipts/", { method: "POST", headers: { "Content-Type": "application/json", "X-Idempotency-Key": "msw-prompt3-create" }, body: JSON.stringify({ receipt_date: "2026-08-24", branch: "branch-zanzibar", payer: "partner-amani", currency: "TZS", payment_mode: "CASH", receipt_amount: "25000.00" }) })
    expect(createResponse.status).toBe(201)
    const created = (await createResponse.json()).data
    const patchResponse = await fetch(`http://localhost/api/v1/front-office/receipts/${created.id}/`, { method: "PATCH", headers: { "Content-Type": "application/json", "X-Idempotency-Key": "msw-prompt3-patch" }, body: JSON.stringify({ narration: "Verified cash receipt" }) })
    expect(patchResponse.status).toBe(200)
    expect((await patchResponse.json()).data.narration).toBe("Verified cash receipt")
    const postResponse = await fetch(`http://localhost/api/v1/front-office/receipts/${created.id}/post/`, { method: "POST", headers: { "X-Idempotency-Key": "msw-prompt3-post" } })
    expect(postResponse.status).toBe(200)
    expect((await postResponse.json()).data).toMatchObject({ id: created.id, status: "POSTED" })
  })

  it("persists cancellation and reversal lifecycle outcomes", async () => {
    const draftResponse = await fetch("http://localhost/api/v1/front-office/receipts/", { method: "POST", headers: { "Content-Type": "application/json", "X-Idempotency-Key": "msw-prompt6-draft" }, body: JSON.stringify({ receipt_date: "2026-08-24", branch: "branch-zanzibar", payer: "partner-amani", currency: "TZS", payment_mode: "CASH", receipt_amount: "12000.00" }) })
    const draft = (await draftResponse.json()).data
    const cancelResponse = await fetch(`http://localhost/api/v1/front-office/receipts/${draft.id}/cancel/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ reason: "Duplicate draft" }) })
    expect(cancelResponse.status).toBe(200)
    expect((await cancelResponse.json()).data).toMatchObject({ id: draft.id, status: "CANCELLED", cancelled_reason: "Duplicate draft" })
    const cancelledDetail = await fetch(`http://localhost/api/v1/front-office/receipts/${draft.id}/`)
    expect((await cancelledDetail.json()).data).toMatchObject({ status: "CANCELLED", cancelled_reason: "Duplicate draft" })

    const postedDraftResponse = await fetch("http://localhost/api/v1/front-office/receipts/", { method: "POST", headers: { "Content-Type": "application/json", "X-Idempotency-Key": "msw-prompt6-posted" }, body: JSON.stringify({ receipt_date: "2026-08-24", branch: "branch-zanzibar", payer: "partner-amani", currency: "TZS", payment_mode: "CASH", receipt_amount: "18000.00" }) })
    const postedDraft = (await postedDraftResponse.json()).data
    await fetch(`http://localhost/api/v1/front-office/receipts/${postedDraft.id}/post/`, { method: "POST", headers: { "X-Idempotency-Key": "msw-prompt6-post" } })
    const reverseResponse = await fetch(`http://localhost/api/v1/front-office/receipts/${postedDraft.id}/reverse/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ reason: "Duplicate payment" }) })
    expect(reverseResponse.status).toBe(200)
    expect((await reverseResponse.json()).data).toMatchObject({ id: postedDraft.id, status: "REVERSED", reversed_reason: "Duplicate payment" })
  })

  it("returns an oldest-first auto-allocation summary with first-premium metadata", async () => {
    const response = await fetch("http://localhost/api/v1/front-office/receipts/receipt-demo-1/auto-allocate/", { method: "POST" })
    expect(response.status).toBe(200)
    const body = await response.json()
    expect(body.data).toMatchObject({ remaining_unallocated_amount: "0.00", first_premium_completed: true, first_premium_proposal_number: "OLP-2026-000001", receipt: { status: "ALLOCATED" } })
    expect(body.data.allocations[0]).toMatchObject({ is_first_premium: true, proposal_number: "OLP-2026-000001" })
  })

  it("returns the structured teachable over-allocation error", async () => {
    const response = await fetch("http://localhost/api/v1/front-office/receipts/receipt-demo-1/allocate/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ allocations: [{ commitment: "commitment-1", amount: "999999.00" }] }) })
    expect(response.status).toBe(422)
    const body = await response.json()
    expect(body).toMatchObject({ errorCode: "RECEIPT_OVERALLOCATION", message: expect.stringContaining("unallocated"), resolutionSteps: expect.arrayContaining([expect.stringContaining("Reduce")]) })
  })
})

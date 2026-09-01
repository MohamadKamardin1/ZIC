import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from "vitest"
import { resetMIPlanMockState } from "./maturityInstallmentsHandlers"
import { server } from "./server"

const BASE = "http://localhost/api/v1/ol/maturity-installments"

beforeAll(() => server.listen({ onUnhandledRequest: "error" }))
afterEach(() => {
  server.resetHandlers()
  resetMIPlanMockState()
})
afterAll(() => server.close())
beforeEach(() => resetMIPlanMockState())

describe("OL Maturity Installments MSW contract", () => {
  it("returns a paginated register with human-readable plan fields", async () => {
    const response = await fetch(`${BASE}/?page=1&page_size=10&q=Amani`)
    expect(response.status).toBe(200)
    const body = await response.json()
    expect(body.data.results[0]).toMatchObject({
      plan_number: "MIP-20260901-9DD41C66AF",
      policy_number: "ZIC-OL-2026-000001",
      policyholder_name: "Amani Salum",
      status: "ACTIVE",
      status_display: "Active",
      currency: "TZS",
      frequency: "ANNUAL",
    })
    expect(body.data.results[0].paid_amount).toMatch(/^\d+\.\d{2}$/)
    expect(body.data.results[0].id).not.toContain("uuid")
  })

  it("returns live KPIs with filter-aware lifecycle and value aggregates", async () => {
    const all = await fetch(`${BASE}/kpis/`)
    expect(all.status).toBe(200)
    const allBody = await all.json()
    expect(allBody.data).toMatchObject({
      total_plans_active: 5,
      total_active_plans_value: "222750000.00",
      missed_payments_count: 6,
      completed_plans_count: 1,
    })
    expect(typeof allBody.data.total_upcoming_payouts).toBe("number")
    expect(typeof allBody.data.upcoming_next_30_days).toBe("number")

    const filtered = await fetch(`${BASE}/kpis/?status=ACTIVE`)
    const filteredBody = await filtered.json()
    expect(filteredBody.data).toMatchObject({ total_plans_active: 5, total_active_plans_value: "222750000.00", completed_plans_count: 0 })

    const dateFiltered = await fetch(`${BASE}/kpis/?date_from=2026-03-01&date_to=2026-03-31`)
    const dateFilteredBody = await dateFiltered.json()
    expect(dateFilteredBody.data).toMatchObject({ total_plans_active: 3, total_active_plans_value: "162750000.00", completed_plans_count: 0 })
  })

  it("returns searchable frequency and term option catalogs", async () => {
    const frequencyResponse = await fetch(`${BASE}/options/frequencies/?q=Quarterly`)
    expect(frequencyResponse.status).toBe(200)
    const frequencyBody = await frequencyResponse.json()
    expect(frequencyBody.data.results[0]).toMatchObject({ value: "QUARTERLY", label: "Quarterly", meta: { months_between: 3, payout_per_year: 4 } })

    const rateTableResponse = await fetch(`${BASE}/options/terms/?product=OL_ENDOWMENT_STANDARD`)
    expect(rateTableResponse.status).toBe(200)
    const rateTableBody = await rateTableResponse.json()
    expect(rateTableBody.data.results).toEqual(expect.arrayContaining([expect.objectContaining({ value: "10", meta: expect.objectContaining({ source: "RATE_TABLE" }) })]))

    const defaultResponse = await fetch(`${BASE}/options/terms/`)
    const defaultBody = await defaultResponse.json()
    expect(defaultBody.data.results[0]).toMatchObject({ value: "1", meta: { source: "DEFAULT" } })
  })

  it("returns a nested detail workspace with schedule items, payment history, and reconciliation", async () => {
    const response = await fetch(`${BASE}/plan-active-1/`)
    expect(response.status).toBe(200)
    const body = await response.json()
    expect(body.data).toMatchObject({
      plan_number: "MIP-20260901-9DD41C66AF",
      status_display: "Active",
      total_payable_amount: "62500000.00",
      paid_amount: "15625000.00",
      balance: "46875000.00",
    })
    expect(body.data.items).toHaveLength(4)
    expect(body.data.items[0]).toMatchObject({ installment_number: 1, status: "PAID", requisition_number: "FO-MIP-2026-000001" })
    expect(body.data.items[1]).toMatchObject({ installment_number: 2, status: "MISSED" })
    expect(body.data.payment_history).toHaveLength(1)
    expect(body.data.reconciliation).toMatchObject({ status: "FAIL", missing_amount: "46875000.00" })
    expect(body.data.bank_accounts).toHaveLength(2)
    expect(body.data.bank_accounts[0]).toMatchObject({ bank_name: "NMB Bank", account_number: "0151234567891", is_default: true })
  })

  it("serves installment items with server-side pagination and whole-schedule totals", async () => {
    const pageOne = await fetch(`${BASE}/plan-long-term-1/items/?page=1&page_size=10`)
    expect(pageOne.status).toBe(200)
    const bodyOne = await pageOne.json()
    expect(bodyOne.data.results).toHaveLength(10)
    expect(bodyOne.data.count).toBe(20)
    expect(bodyOne.data.page).toBe(1)
    expect(bodyOne.data.next).toBe(true)
    expect(bodyOne.data.previous).toBe(false)
    expect(bodyOne.data.total_amount).toBe("100000000.00")
    expect(bodyOne.data.total_paid).toBe("10000000.00")
    expect(bodyOne.data.total_remaining).toBe("90000000.00")
    expect(bodyOne.data.results[0]).toMatchObject({ installment_number: 1, status: "PAID", paid_date: "2026-03-15" })
    expect(bodyOne.data.results[2]).toMatchObject({ installment_number: 3, status: "MISSED" })
    expect(bodyOne.data.results[9]).toMatchObject({ installment_number: 10, status: "SCHEDULED" })

    const pageTwo = await fetch(`${BASE}/plan-long-term-1/items/?page=2&page_size=10`)
    const bodyTwo = await pageTwo.json()
    expect(bodyTwo.data.results).toHaveLength(10)
    expect(bodyTwo.data.page).toBe(2)
    expect(bodyTwo.data.next).toBe(false)
    expect(bodyTwo.data.previous).toBe(true)
    expect(bodyTwo.data.total_paid).toBe("10000000.00")
    expect(bodyTwo.data.results[0]).toMatchObject({ installment_number: 11 })

    const missing = await fetch(`${BASE}/plan-unknown-1/items/`)
    expect(missing.status).toBe(404)
  })

  it("strictly validates payment processing and stores the disbursement method", async () => {
    const url = `${BASE}/items/plan-reversed-1-item-1/process-payment/`
    const json = { "Content-Type": "application/json" }

    const missingMethod = await fetch(url, { method: "POST", headers: json, body: JSON.stringify({}) })
    expect(missingMethod.status).toBe(400)
    expect(await missingMethod.json()).toMatchObject({ errorCode: "INSTALLMENT_PAYMENT_METHOD_REQUIRED" })

    const missingBank = await fetch(url, { method: "POST", headers: json, body: JSON.stringify({ payment_method: "BANK_TRANSFER" }) })
    expect(missingBank.status).toBe(422)
    expect(await missingBank.json()).toMatchObject({ errorCode: "INSTALLMENT_BANK_ACCOUNT_REQUIRED" })

    const missingReference = await fetch(url, { method: "POST", headers: json, body: JSON.stringify({ payment_method: "BANK_TRANSFER", bank_account_id: "ba-plan-reversed-1-1" }) })
    expect(missingReference.status).toBe(422)
    expect(await missingReference.json()).toMatchObject({ errorCode: "INSTALLMENT_PAYMENT_REFERENCE_REQUIRED" })

    const insufficient = await fetch(url, { method: "POST", headers: json, body: JSON.stringify({ payment_method: "BANK_TRANSFER", bank_account_id: "ba-plan-reversed-1-2", reference_number: "REF-2026-090" }) })
    expect(insufficient.status).toBe(422)
    expect(await insufficient.json()).toMatchObject({ errorCode: "INSTALLMENT_PARTNER_BANK_INSUFFICIENT_FUNDS" })

    const success = await fetch(url, { method: "POST", headers: json, body: JSON.stringify({ payment_method: "BANK_TRANSFER", bank_account_id: "ba-plan-reversed-1-1", reference_number: "REF-2026-091" }) })
    expect(success.status).toBe(201)
    const successBody = await success.json()
    expect(successBody.data.item).toMatchObject({ status: "PAYMENT_PENDING", payment_method: "BANK_TRANSFER", payment_reference: "REF-2026-091", bank_account_display: "NMB Bank 0151234567891" })
    expect(successBody.data.requisition).toMatchObject({ status: "PENDING", department: "MATURITY_INSTALLMENTS" })

    const cash = await fetch(`${BASE}/items/plan-reversed-1-item-2/process-payment/`, { method: "POST", headers: json, body: JSON.stringify({ payment_method: "CASH" }) })
    expect(cash.status).toBe(201)
    expect((await cash.json()).data.item).toMatchObject({ status: "PAYMENT_PENDING", payment_method: "CASH" })
  })

  it("exports the register as a CSV without spreadsheet formula injection", async () => {
    const response = await fetch(`${BASE}/export/`)
    expect(response.status).toBe(200)
    expect(response.headers.get("Content-Type")).toContain("text/csv")
    expect(response.headers.get("X-Content-Type-Options")).toBe("nosniff")
    const text = await response.text()
    expect(text).toContain("Plan Number,Policy Number,Policyholder Name")
    expect(text).toContain("MIP-20260901-9DD41C66AF")
  })

  it("creates a plan idempotently and rejects a reused key with a different payload", async () => {
    const createUrl = `${BASE}/create/`
    const payload = JSON.stringify({ policy_id: "policy-new-1", frequency: "ANNUAL", term_years: 10 })

    const missingKeyResponse = await fetch(createUrl, { method: "POST", headers: { "Content-Type": "application/json" }, body: payload })
    expect(missingKeyResponse.status).toBe(400)
    expect(await missingKeyResponse.json()).toMatchObject({ errorCode: "INSTALLMENT_IDEMPOTENCY_REQUIRED" })

    const createdResponse = await fetch(createUrl, { method: "POST", headers: { "Content-Type": "application/json", "X-Idempotency-Key": "create-key-1" }, body: payload })
    expect(createdResponse.status).toBe(201)
    const createdBody = await createdResponse.json()
    expect(createdBody.data.created).toBe(true)
    expect(createdBody.data.plan).toMatchObject({ status: "CREATED", frequency: "ANNUAL" })
    expect(createdBody.data.plan.items).toHaveLength(10)
    expect(createdBody.data.plan.plan_number).toBeTruthy()

    const replayResponse = await fetch(createUrl, { method: "POST", headers: { "Content-Type": "application/json", "X-Idempotency-Key": "create-key-1" }, body: payload })
    expect(replayResponse.status).toBe(200)
    const replayBody = await replayResponse.json()
    expect(replayBody.data.created).toBe(false)
    expect(replayBody.data.plan.plan_number).toBe(createdBody.data.plan.plan_number)

    const conflictResponse = await fetch(createUrl, { method: "POST", headers: { "Content-Type": "application/json", "X-Idempotency-Key": "create-key-1" }, body: JSON.stringify({ policy_id: "policy-new-1", frequency: "QUARTERLY", term_years: 5 }) })
    expect(conflictResponse.status).toBe(409)
    expect(await conflictResponse.json()).toMatchObject({ errorCode: "INSTALLMENT_IDEMPOTENCY_CONFLICT" })
  })

  it("blocks plan creation against an immature policy", async () => {
    const response = await fetch(`${BASE}/create/`, { method: "POST", headers: { "Content-Type": "application/json", "X-Idempotency-Key": "immature-key" }, body: JSON.stringify({ policy_id: "policy-immature-1", frequency: "ANNUAL", term_years: 10 }) })
    expect(response.status).toBe(422)
    expect(await response.json()).toMatchObject({ errorCode: "INSTALLMENT_POLICY_NOT_MATURED" })
  })

  it("walks the payment lifecycle on a fresh plan: not due, process, confirm, activate, reverse", async () => {
    const createResponse = await fetch(`${BASE}/create/`, { method: "POST", headers: { "Content-Type": "application/json", "X-Idempotency-Key": "lifecycle-key" }, body: JSON.stringify({ policy_id: "policy-new-1", frequency: "ANNUAL", term_years: 10 }) })
    const planId = (await createResponse.json()).data.plan.id

    const notDueResponse = await fetch(`${BASE}/items/${planId}-item-2/process-payment/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ payment_method: "CASH" }) })
    expect(notDueResponse.status).toBe(422)
    expect(await notDueResponse.json()).toMatchObject({ errorCode: "INSTALLMENT_PAYMENT_NOT_DUE" })

    const processResponse = await fetch(`${BASE}/items/${planId}-item-1/process-payment/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ payment_method: "CASH" }) })
    expect(processResponse.status).toBe(201)
    const processBody = await processResponse.json()
    expect(processBody.data.item).toMatchObject({ status: "PAYMENT_PENDING" })
    expect(processBody.data.created).toBe(true)
    const requisition = processBody.data.requisition.requisition_number
    expect(requisition).toMatch(/^FO-MIP-/)

    const replayResponse = await fetch(`${BASE}/items/${planId}-item-1/process-payment/`, { method: "POST" })
    expect(replayResponse.status).toBe(200)
    expect((await replayResponse.json()).data.created).toBe(false)

    const confirmResponse = await fetch(`${BASE}/items/${planId}-item-1/confirm-payment/`, { method: "POST" })
    expect(confirmResponse.status).toBe(200)
    const confirmBody = await confirmResponse.json()
    expect(confirmBody.data.item).toMatchObject({ status: "PAID" })
    expect(confirmBody.data.plan.status).toBe("ACTIVE")
    expect(confirmBody.data.plan_completed).toBe(false)

    const reconfirmResponse = await fetch(`${BASE}/items/${planId}-item-1/confirm-payment/`, { method: "POST" })
    expect((await reconfirmResponse.json()).data.confirmed).toBe(false)

    const noReasonResponse = await fetch(`${BASE}/items/${planId}-item-1/reverse-payment/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) })
    expect(noReasonResponse.status).toBe(400)
    expect(await noReasonResponse.json()).toMatchObject({ errorCode: "INSTALLMENT_REVERSAL_REASON_REQUIRED" })

    const reverseResponse = await fetch(`${BASE}/items/${planId}-item-1/reverse-payment/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ reason: "Front Office disbursement errored." }) })
    expect(reverseResponse.status).toBe(200)
    const reverseBody = await reverseResponse.json()
    expect(reverseBody.data.item.status).toBe("SCHEDULED")
    expect(reverseBody.data.plan.paid_amount).toBe("0.00")

    const reverseAgainResponse = await fetch(`${BASE}/items/${planId}-item-1/reverse-payment/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ reason: "Duplicate reversal." }) })
    expect(reverseAgainResponse.status).toBe(422)
    expect(await reverseAgainResponse.json()).toMatchObject({ errorCode: "INSTALLMENT_REVERSAL_NOT_ALLOWED" })
  })

  it("blocks reversal outside the 7-day window and requires a reason", async () => {
    const noReasonResponse = await fetch(`${BASE}/items/plan-usd-1-item-1/reverse-payment/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) })
    expect(noReasonResponse.status).toBe(400)
    expect(await noReasonResponse.json()).toMatchObject({ errorCode: "INSTALLMENT_REVERSAL_REASON_REQUIRED" })

    const expiredResponse = await fetch(`${BASE}/items/plan-usd-1-item-1/reverse-payment/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ reason: "Bank rejected the credit." }) })
    expect(expiredResponse.status).toBe(422)
    expect(await expiredResponse.json()).toMatchObject({ errorCode: "INSTALLMENT_REVERSAL_WINDOW_EXPIRED" })
  })

  it("confirms the final installment and completes the plan with a passing reconciliation", async () => {
    expect((await fetch(`${BASE}/items/plan-reversed-1-item-1/process-payment/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ payment_method: "CASH" }) })).status).toBe(201)
    await fetch(`${BASE}/items/plan-reversed-1-item-1/confirm-payment/`, { method: "POST" })
    expect((await fetch(`${BASE}/items/plan-reversed-1-item-2/process-payment/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ payment_method: "CASH" }) })).status).toBe(201)
    const confirmResponse = await fetch(`${BASE}/items/plan-reversed-1-item-2/confirm-payment/`, { method: "POST" })
    const confirmBody = await confirmResponse.json()
    expect(confirmBody.data.plan_completed).toBe(true)
    expect(confirmBody.data.plan.status).toBe("COMPLETED")

    const reconciliationResponse = await fetch(`${BASE}/plan-reversed-1/reconciliation/`)
    const reconciliationBody = await reconciliationResponse.json()
    expect(reconciliationBody.data.status).toBe("PASS")
    expect(reconciliationBody.data.missing_amount).toBe("0.00")
  })

  it("cancels an active plan with a reason and waives the remaining installments", async () => {
    const noReasonResponse = await fetch(`${BASE}/plans/plan-active-1/cancel/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) })
    expect(noReasonResponse.status).toBe(400)
    expect(await noReasonResponse.json()).toMatchObject({ errorCode: "INSTALLMENT_CANCELLATION_REASON_REQUIRED" })

    const cancelResponse = await fetch(`${BASE}/plans/plan-active-1/cancel/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ reason: "Policyholder surrendered the contract." }) })
    expect(cancelResponse.status).toBe(200)
    const cancelBody = await cancelResponse.json()
    expect(cancelBody.data.status).toBe("CANCELLED")
    expect(cancelBody.data.items[1]).toMatchObject({ status: "WAIVED" })

    const blockedResponse = await fetch(`${BASE}/plans/plan-completed-1/cancel/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ reason: "Test cancellation." }) })
    expect(blockedResponse.status).toBe(422)
    expect(await blockedResponse.json()).toMatchObject({ errorCode: "INSTALLMENT_PLAN_CANNOT_CANCEL" })
  })

  it("returns a passing reconciliation for a completed plan", async () => {
    const response = await fetch(`${BASE}/plan-completed-1/reconciliation/`)
    expect(response.status).toBe(200)
    const body = await response.json()
    expect(body.data).toMatchObject({ status: "PASS", missing_amount: "0.00", paid_items: 10, total_items: 10 })
  })

  it("prints a schedule and a payment advice through the documents engine", async () => {
    const scheduleResponse = await fetch(`${BASE}/plan-active-1/print-schedule/`, { method: "POST" })
    expect(scheduleResponse.status).toBe(201)
    const scheduleBody = await scheduleResponse.json()
    expect(scheduleBody.data.instance.document_type).toBe("OL_MATURITY_SCHEDULE")
    expect(scheduleBody.data.signed_download_url).toContain("/download/")

    const adviceResponse = await fetch(`${BASE}/plan-active-1/print-advice/`, { method: "POST" })
    expect(adviceResponse.status).toBe(201)
    const adviceBody = await adviceResponse.json()
    expect(adviceBody.data.instance.document_type).toBe("OL_MATURITY_PAYMENT_ADVICE")
  })

  it("exposes a read-only partner portal scoped to available plans", async () => {
    const listResponse = await fetch(`${BASE}/portal/`)
    expect(listResponse.status).toBe(200)
    const listBody = await listResponse.json()
    expect(listBody.data.results).toHaveLength(9)
    expect(listBody.data.results[0]).toMatchObject({ plan_number: "MIP-20260901-9DD41C66AF", status_display: "Active" })

    const detailResponse = await fetch(`${BASE}/portal/plan-active-1/`)
    expect(detailResponse.status).toBe(200)
    const detailBody = await detailResponse.json()
    expect(detailBody.data).toMatchObject({ plan_number: "MIP-20260901-9DD41C66AF" })
    expect(detailBody.data.items).toHaveLength(4)

    const byNumberResponse = await fetch(`${BASE}/portal/MIP-20260901-9DD41C66AF/`)
    expect((await byNumberResponse.json()).data.id).toBe("plan-active-1")

    const missingResponse = await fetch(`${BASE}/portal/unknown-plan-1/`)
    expect(missingResponse.status).toBe(404)
    expect(await missingResponse.json()).toMatchObject({ errorCode: "PORTAL_RESOURCE_NOT_FOUND" })
  })
})

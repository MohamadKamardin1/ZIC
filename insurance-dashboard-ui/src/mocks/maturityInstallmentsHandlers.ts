import { http, HttpResponse } from "msw"

const BASE = "/api/v1/ol/maturity-installments"

export type MIPlanMockItem = {
  id: string
  plan_id: string
  installment_number: number
  due_date: string | null
  amount: string
  status: string
  status_display: string
  requisition_number: string | null
  paid_date: string | null
  paid_by_display: string | null
  payer_display: string | null
  payment_reference: string | null
  narration: string
}

export type MIPlanMockRow = {
  id: string
  plan_number: string
  policy_id: string
  policy_number: string
  policyholder_name: string
  policyholder_display: string
  claim_number: string | null
  currency: string
  frequency: string
  status: string
  status_display: string
  maturity_value: string
  total_payable_amount: string
  total_amount: string
  paid_amount: string
  balance: string
  installment_count: number
  start_date: string | null
  end_date: string | null
  allowed_actions: string[]
  idempotency_key: string | null
  idempotency_fingerprint: string | null
  source_channel: string
  source_channel_display: string
  parameter_snapshot: Record<string, unknown>
  items: MIPlanMockItem[]
  created_at: string
  updated_at: string
}

const PLAN_STATUS_LABELS: Record<string, string> = {
  CREATED: "Created",
  ACTIVE: "Active",
  COMPLETED: "Completed",
  CANCELLED: "Cancelled",
  TERMINATED: "Terminated",
}

const ITEM_STATUS_LABELS: Record<string, string> = {
  SCHEDULED: "Scheduled",
  PAYMENT_PENDING: "Payment pending",
  PAID: "Paid",
  MISSED: "Missed",
  WAIVED: "Waived",
}

function planStatusLabel(status: string): string {
  return PLAN_STATUS_LABELS[status] ?? status.charAt(0) + status.slice(1).toLowerCase()
}

function itemStatusLabel(status: string): string {
  return ITEM_STATUS_LABELS[status] ?? status.toLowerCase().replace(/_/g, " ")
}

function planAllowedActions(status: string): string[] {
  switch (status) {
    case "COMPLETED":
    case "CANCELLED":
    case "TERMINATED":
      return ["view", "print"]
    default:
      return ["view", "create", "process_payment", "cancel", "print"]
  }
}

function item(planId: string, number: number, dueDate: string, amount: string, status = "SCHEDULED"): MIPlanMockItem {
  return {
    id: `${planId}-item-${number}`,
    plan_id: planId,
    installment_number: number,
    due_date: dueDate,
    amount,
    status,
    status_display: itemStatusLabel(status),
    requisition_number: null,
    paid_date: null,
    paid_by_display: null,
    payer_display: null,
    payment_reference: null,
    narration: "",
  }
}

function plan(
  partial: Pick<MIPlanMockRow, "id" | "plan_number" | "policy_id" | "policy_number" | "policyholder_name" | "policyholder_display" | "currency" | "frequency" | "status" | "maturity_value">,
  items: MIPlanMockItem[],
  extra: Partial<MIPlanMockRow> = {},
): MIPlanMockRow {
  const total = partial.maturity_value
  const paid = items.filter((i) => i.status === "PAID").reduce((sum, i) => sum + Number(i.amount), 0).toFixed(2)
  const balance = (Number(total) - Number(paid)).toFixed(2)
  const firstDue = items.map((i) => i.due_date).filter(Boolean).sort()[0] ?? null
  return {
    id: partial.id,
    plan_number: partial.plan_number,
    policy_id: partial.policy_id,
    policy_number: partial.policy_number,
    policyholder_name: partial.policyholder_name,
    policyholder_display: partial.policyholder_display,
    claim_number: null,
    currency: partial.currency,
    frequency: partial.frequency,
    status: partial.status,
    status_display: planStatusLabel(partial.status),
    maturity_value: partial.maturity_value,
    total_payable_amount: total,
    total_amount: total,
    paid_amount: paid,
    balance,
    installment_count: items.length,
    start_date: firstDue,
    end_date: items[items.length - 1]?.due_date ?? null,
    allowed_actions: planAllowedActions(partial.status),
    idempotency_key: null,
    idempotency_fingerprint: null,
    source_channel: "API",
    source_channel_display: "Maturity Installments Console",
    parameter_snapshot: {
      frequency: partial.frequency,
      term_years: 1,
      rate_factor: 10.0,
      rate_key: "R-PROBE3",
    },
    items,
    created_at: "2026-09-01T08:00:00Z",
    updated_at: "2026-09-01T08:00:00Z",
    ...extra,
  }
}

const initialPlans: MIPlanMockRow[] = [
  plan(
    { id: "plan-active-1", plan_number: "MIP-20260901-9DD41C66AF", policy_id: "policy-aman-1", policy_number: "ZIC-OL-2026-000001", policyholder_name: "Amani Salum", policyholder_display: "P-000001 — Amani Salum", currency: "TZS", frequency: "ANNUAL", status: "ACTIVE", maturity_value: "62500000.00" },
    [
      { ...item("plan-active-1", 1, "2026-03-01", "15625000.00", "PAID"), requisition_number: "FO-MIP-2026-000001", paid_date: "2026-03-01", paid_by_display: "Finance Officer — Rehema S.", payer_display: "Amani Salum", payment_reference: "FO-PAY-2026-000101" },
      { ...item("plan-active-1", 2, "2027-03-01", "15625000.00", "MISSED") },
      { ...item("plan-active-1", 3, "2028-03-01", "15625000.00") },
      { ...item("plan-active-1", 4, "2029-03-01", "15625000.00") },
    ],
  ),
  plan(
    { id: "plan-completed-1", plan_number: "MIP-20260815-9E1168C4EF", policy_id: "policy-fatma-1", policy_number: "ZIC-OL-2025-000021", policyholder_name: "Fatma Ali", policyholder_display: "P-000021 — Fatma Ali", currency: "TZS", frequency: "ANNUAL", status: "COMPLETED", maturity_value: "50000000.00" },
    Array.from({ length: 10 }, (_, index) => {
      const number = index + 1
      const due = `20${16 + index}-01-15`
      return {
        ...item("plan-completed-1", number, due, "5000000.00", "PAID"),
        requisition_number: `FO-MIP-2026-0000${String(number).padStart(2, "0")}`,
        paid_date: due,
        paid_by_display: "Finance Officer — Rehema S.",
        payer_display: "Fatma Ali",
        payment_reference: `FO-PAY-2026-0002${String(number).padStart(2, "0")}`,
      }
    }),
    { claim_number: null },
  ),
  plan(
    { id: "plan-created-1", plan_number: "MIP-20260901-EE02332018", policy_id: "policy-juma-1", policy_number: "ZIC-OL-2026-000003", policyholder_name: "Juma Hassan", policyholder_display: "P-000003 — Juma Hassan", currency: "TZS", frequency: "ANNUAL", status: "CREATED", maturity_value: "100000000.00" },
    Array.from({ length: 10 }, (_, index) => item("plan-created-1", index + 1, `20${27 + index}-06-30`, "10000000.00")),
  ),
  plan(
    { id: "plan-cancelled-1", plan_number: "MIP-20260720-9024C42F9B", policy_id: "policy-rehema-1", policy_number: "ZIC-OL-2024-000005", policyholder_name: "Rehema Mwinyi", policyholder_display: "P-000005 — Rehema Mwinyi", currency: "TZS", frequency: "QUARTERLY", status: "CANCELLED", maturity_value: "20000000.00" },
    Array.from({ length: 4 }, (_, index) => item("plan-cancelled-1", index + 1, `20${24 + Math.floor(index / 4)}-0${(index % 4) + 1}-15`, "5000000.00", "WAIVED")),
  ),
  plan(
    { id: "plan-usd-1", plan_number: "MIP-20260901-BFD254340F", policy_id: "policy-baraka-1", policy_number: "ZIC-OL-2026-000008", policyholder_name: "Baraka Mushi", policyholder_display: "P-000008 — Baraka Mushi", currency: "USD", frequency: "QUARTERLY", status: "ACTIVE", maturity_value: "250000.00" },
    [
      { ...item("plan-usd-1", 1, "2026-03-31", "62500.00", "PAID"), requisition_number: "FO-MIP-2026-000021", paid_date: "2026-03-31", paid_by_display: "Finance Officer — Rehema S.", payer_display: "Baraka Mushi", payment_reference: "FO-PAY-2026-000301" },
      { ...item("plan-usd-1", 2, "2026-06-30", "62500.00") },
      { ...item("plan-usd-1", 3, "2026-09-30", "62500.00") },
      { ...item("plan-usd-1", 4, "2026-12-31", "62500.00") },
    ],
    { currency: "USD" },
  ),
  plan(
    { id: "plan-claim-linked-1", plan_number: "MIP-20260901-6208658FAC", policy_id: "policy-neema-1", policy_number: "ZIC-OL-2025-000012", policyholder_name: "Neema Said", policyholder_display: "P-000012 — Neema Said", currency: "TZS", frequency: "ANNUAL", status: "ACTIVE", maturity_value: "40000000.00" },
    [
      { ...item("plan-claim-linked-1", 1, "2026-02-28", "10000000.00", "PAID"), requisition_number: "FO-MIP-2026-000030", paid_date: "2026-02-28", paid_by_display: "Finance Officer — Rehema S.", payer_display: "Neema Said", payment_reference: "FO-PAY-2026-000310" },
      { ...item("plan-claim-linked-1", 2, "2027-02-28", "10000000.00") },
      { ...item("plan-claim-linked-1", 3, "2028-02-28", "10000000.00") },
      { ...item("plan-claim-linked-1", 4, "2029-02-28", "10000000.00") },
    ],
    { claim_number: "OL-CLM-2026-000010" },
  ),
  plan(
    { id: "plan-missed-1", plan_number: "MIP-20260501-EE8E0C1FE8", policy_id: "policy-salim-1", policy_number: "ZIC-OL-2024-000007", policyholder_name: "Salim Omar", policyholder_display: "P-000007 — Salim Omar", currency: "TZS", frequency: "QUARTERLY", status: "CREATED", maturity_value: "12000000.00" },
    Array.from({ length: 4 }, (_, index) => item("plan-missed-1", index + 1, `2026-0${(index % 4) + 1}-15`, "3000000.00", "MISSED")),
  ),
  plan(
    { id: "plan-reversed-1", plan_number: "MIP-20260801-A46A281E7C", policy_id: "policy-hamisi-1", policy_number: "ZIC-OL-2026-000011", policyholder_name: "Hamisi Juma", policyholder_display: "P-000011 — Hamisi Juma", currency: "TZS", frequency: "HALF_YEARLY", status: "ACTIVE", maturity_value: "20000000.00" },
    [
      item("plan-reversed-1", 1, "2026-02-01", "10000000.00"),
      item("plan-reversed-1", 2, "2026-08-01", "10000000.00"),
    ],
  ),
]

const frequencyOptions: Array<{ value: string; label: string; meta: { months_between: number; payout_per_year: number } }> = [
  { value: "SINGLE", label: "Single lump sum", meta: { months_between: 12, payout_per_year: 1 } },
  { value: "MONTHLY", label: "Monthly", meta: { months_between: 1, payout_per_year: 12 } },
  { value: "QUARTERLY", label: "Quarterly", meta: { months_between: 3, payout_per_year: 4 } },
  { value: "HALF_YEARLY", label: "Half-yearly", meta: { months_between: 6, payout_per_year: 2 } },
  { value: "ANNUAL", label: "Annual", meta: { months_between: 12, payout_per_year: 1 } },
]

const KNOWN_PRODUCT = "OL_ENDOWMENT_STANDARD"

let plans: MIPlanMockRow[] = []

function clonePlans(rows: MIPlanMockRow[]): MIPlanMockRow[] {
  return rows.map((row) => ({
    ...row,
    allowed_actions: [...row.allowed_actions],
    parameter_snapshot: { ...row.parameter_snapshot },
    items: row.items.map((itemRow) => ({ ...itemRow })),
  }))
}

export function resetMIPlanMockState() {
  plans = clonePlans(initialPlans)
}

function data<T>(payload: T, status = 200) {
  return HttpResponse.json({ data: payload }, { status })
}

function error(status: number, code: string, message: string, resolutionSteps: string[], details: Record<string, unknown> = {}, fieldErrors: Record<string, string[]> = {}) {
  return HttpResponse.json({ success: false, errorCode: code, message, resolutionSteps, details, fieldErrors, error: { code, message, details, resolutionSteps } }, { status })
}

function page<T>(rows: T[], url: URL) {
  const pageSize = Math.max(1, Number(url.searchParams.get("page_size") ?? 20))
  const pageNumber = Math.max(1, Number(url.searchParams.get("page") ?? 1))
  const start = (pageNumber - 1) * pageSize
  return { results: rows.slice(start, start + pageSize), count: rows.length, page: pageNumber, page_size: pageSize, next: start + pageSize < rows.length, previous: pageNumber > 1 }
}

function findPlan(id: string) {
  return plans.find((row) => row.id === id)
}

function findItem(itemId: string) {
  for (const row of plans) {
    const match = row.items.find((it) => it.id === itemId)
    if (match) return { plan: row, item: match }
  }
  return undefined
}

function todayIso() {
  return new Date().toISOString().slice(0, 10)
}

function plusDays(isoToday: string, days: number): string {
  const [year, month, day] = isoToday.split("-").map(Number)
  const result = new Date(Date.UTC(year, month - 1, day + days))
  return result.toISOString().slice(0, 10)
}

function recomputePlanTotals(row: MIPlanMockRow) {
  const paid = row.items.filter((it) => it.status === "PAID").reduce((sum, it) => sum + Number(it.amount), 0).toFixed(2)
  row.paid_amount = paid
  row.balance = (Number(row.total_payable_amount) - Number(paid)).toFixed(2)
  if (row.status !== "COMPLETED" && row.items.every((it) => it.status === "PAID")) {
    row.status = "COMPLETED"
    row.status_display = planStatusLabel("COMPLETED")
    row.allowed_actions = planAllowedActions("COMPLETED")
  }
  row.updated_at = new Date().toISOString()
}

function planListRow(row: MIPlanMockRow) {
  return {
    id: row.id,
    plan_number: row.plan_number,
    policy_id: row.policy_id,
    policy_number: row.policy_number,
    policyholder_name: row.policyholder_name,
    policyholder_display: row.policyholder_display,
    claim_number: row.claim_number,
    currency: row.currency,
    frequency: row.frequency,
    status: row.status,
    status_display: row.status_display,
    total_amount: row.total_amount,
    paid_amount: row.paid_amount,
    balance: row.balance,
    maturity_value: row.maturity_value,
    installment_count: row.installment_count,
    start_date: row.start_date,
    end_date: row.end_date,
    allowed_actions: row.allowed_actions,
    created_at: row.created_at,
    updated_at: row.updated_at,
  }
}

function planDetailFor(row: MIPlanMockRow) {
  return {
    ...planListRow(row),
    maturity_claim_id: row.claim_number ? "claim-" + row.claim_number.toLowerCase().replace(/-/g, "") : null,
    total_payable_amount: row.total_payable_amount,
    total_paid_amount: row.paid_amount,
    source_channel: row.source_channel,
    source_channel_display: row.source_channel_display,
    parameter_snapshot: row.parameter_snapshot,
    items: row.items.map((it) => ({ ...it })),
    payment_history: row.items.filter((it) => it.status === "PAID").map((it) => ({
      installment_number: it.installment_number,
      due_date: it.due_date,
      amount: it.amount,
      status: it.status,
      paid_date: it.paid_date,
      requisition_number: it.requisition_number,
      payment_reference: it.payment_reference,
      payer_display: it.payer_display,
    })),
    reconciliation: reconciliationFor(row),
  }
}

function reconciliationFor(row: MIPlanMockRow) {
  const paid = row.items.filter((it) => it.status === "PAID").reduce((sum, it) => sum + Number(it.amount), 0).toFixed(2)
  const total = Number(row.total_payable_amount)
  const missing = Math.max(0, total - Number(paid)).toFixed(2)
  const discrepancies: Array<{ code: string; message: string }> = []
  if (Math.abs(Number(paid) - total) > 0.01) {
    discrepancies.push({ code: "MISSING_PAYMENTS", message: `Paid ${paid} is below the total payable ${row.total_payable_amount}.` })
  }
  return {
    status: discrepancies.length === 0 ? "PASS" : "FAIL",
    maturity_value: row.maturity_value,
    total_payable_amount: row.total_payable_amount,
    paid_amount: paid,
    missing_amount: missing,
    paid_items: row.items.filter((it) => it.status === "PAID").length,
    total_items: row.items.length,
    discrepancies,
  }
}

function filteredPlans(url: URL) {
  const q = (url.searchParams.get("q") ?? url.searchParams.get("search") ?? "").toLowerCase()
  const status = url.searchParams.get("status")
  const frequency = url.searchParams.get("frequency")
  const policyNumber = url.searchParams.get("policy_number")
  const product = url.searchParams.get("product")
  const branch = url.searchParams.get("branch")
  const missedOnly = url.searchParams.get("missed_only") === "true"
  const dateFrom = url.searchParams.get("date_from")
  const dateTo = url.searchParams.get("date_to")
  return plans.filter((row) => {
    if (q && !`${row.plan_number} ${row.policy_number} ${row.policyholder_display} ${row.claim_number ?? ""}`.toLowerCase().includes(q)) return false
    if (status && row.status !== status) return false
    if (frequency && row.frequency !== frequency) return false
    if (policyNumber && row.policy_number !== policyNumber) return false
    if (product && !row.parameter_snapshot.product_code?.toString().toLowerCase().includes(product.toLowerCase())) return false
    if (branch && !row.policyholder_display.toLowerCase().includes(branch.toLowerCase())) return false
    if (missedOnly && !row.items.some((it) => it.status === "MISSED")) return false
    if (dateFrom && row.start_date && row.start_date < dateFrom) return false
    if (dateTo && row.start_date && row.start_date > dateTo) return false
    return true
  })
}

function payoutsPerYear(frequency: string): number {
  switch (frequency) {
    case "MONTHLY": return 12
    case "QUARTERLY": return 4
    case "HALF_YEARLY": return 2
    default: return 1
  }
}

function monthOffset(date: string, months: number): string {
  const parsed = new Date(`${date}T00:00:00`)
  const result = new Date(parsed.getFullYear(), parsed.getMonth() + months, parsed.getDate())
  return result.toISOString().slice(0, 10)
}

let createdCounter = 100

function buildCreatedPlan(policyId: string, frequency: string, termYears: number, idempotencyKey: string, maturityClaimId: string | null): MIPlanMockRow {
  createdCounter += 1
  const id = `plan-created-${createdCounter}`
  const today = todayIso()
  const frequencyLabel = frequency.toLowerCase().replace(/_/g, " ")
  const planNumber = `MIP-${today.replace(/-/g, "")}-${(Math.random().toString(16).slice(2, 10)).toUpperCase()}`
  const count = Math.max(1, termYears * payoutsPerYear(frequency))
  const base = (Number("50000000.00") / count).toFixed(2)
  const rows = Array.from({ length: count }, (_, index) => {
    const number = index + 1
    const months = Math.round((index / count) * termYears * 12)
    const amount = number === count ? "50000000.00" : base
    return item(id, number, monthOffset(today, months), amount)
  })
  return plan(
    { id, plan_number: planNumber, policy_id: policyId, policy_number: "ZIC-OL-2026-000099", policyholder_name: "New Policyholder", policyholder_display: "P-000099 — New Policyholder", currency: "TZS", frequency, status: "CREATED", maturity_value: "50000000.00" },
    rows,
    {
      idempotency_key: idempotencyKey,
      source_channel: "WEB",
      source_channel_display: "Maturity Installments Console",
      parameter_snapshot: { frequency, term_years: termYears, product_code: "OL_ENDOWMENT_STANDARD", rate_factor: 10.0 },
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  )
}

export const maturityInstallmentsHandlers = [
  http.get(`*${BASE}/kpis/`, ({ request }) => {
    const url = new URL(request.url)
    const rows = filteredPlans(url)
    const active = rows.filter((row) => row.status === "ACTIVE")
    const completed = rows.filter((row) => row.status === "COMPLETED")
    const missed = rows.flatMap((row) => row.items.filter((it) => it.status === "MISSED"))
    const today = todayIso()
    const horizon = plusDays(today, 30)
    const upcoming = rows.flatMap((row) => row.items.filter((it) => (it.status === "SCHEDULED" || it.status === "PAYMENT_PENDING") && Boolean(it.due_date) && it.due_date! >= today))
    const upcomingNext30Days = rows.flatMap((row) => row.items.filter((it) => (it.status === "SCHEDULED" || it.status === "PAYMENT_PENDING") && Boolean(it.due_date) && it.due_date! >= today && it.due_date! <= horizon))
    const totalActivePlansValue = active.reduce((sum, row) => sum + Number(row.total_amount), 0).toFixed(2)
    return data({
      total_plans_active: active.length,
      total_active_plans_value: totalActivePlansValue,
      total_upcoming_payouts: upcoming.length,
      upcoming_next_30_days: upcomingNext30Days.length,
      missed_payments_count: missed.length,
      completed_plans_count: completed.length,
      filters_applied: { q: url.searchParams.get("q") ?? undefined, status: url.searchParams.get("status") ?? undefined },
      timestamp: new Date().toISOString(),
    })
  }),
  http.get(`*${BASE}/options/frequencies/`, ({ request }) => {
    const url = new URL(request.url)
    const q = (url.searchParams.get("q") ?? "").toLowerCase()
    return data(page(frequencyOptions.filter((option) => !q || `${option.value} ${option.label}`.toLowerCase().includes(q)), url))
  }),
  http.get(`*${BASE}/options/terms/`, ({ request }) => {
    const url = new URL(request.url)
    const q = (url.searchParams.get("q") ?? "").toLowerCase()
    const product = url.searchParams.get("product") ?? url.searchParams.get("product_code")
    const terms = product === KNOWN_PRODUCT
      ? [1, 2, 3, 5, 10, 15, 20]
      : Array.from({ length: 30 }, (_, index) => index + 1)
    const rows = terms.map((term) => ({ value: String(term), label: `${term} year${term === 1 ? "" : "s"}`, meta: { source: product === KNOWN_PRODUCT ? "RATE_TABLE" : "DEFAULT", term_years: term } }))
    return data(page(rows.filter((option) => !q || `${option.value} ${option.label}`.toLowerCase().includes(q)), url))
  }),
  http.get(`*${BASE}/export/`, () => new HttpResponse("Plan Number,Policy Number,Policyholder Name,Total Amount,Paid Amount,Balance,Status,Start Date,End Date\nMIP-20260901-9DD41C66AF,ZIC-OL-2026-000001,Amani Salum,62500000.00,15625000.00,46875000.00,Active,2026-03-01,2029-03-01\n", { status: 200, headers: { "Content-Type": "text/csv", "X-Content-Type-Options": "nosniff" } })),
  http.get(`*${BASE}/portal/`, () => {
    const rows = plans.filter((row) => row.status !== "CANCELLED").map((row) => ({
      id: row.id,
      plan_number: row.plan_number,
      policy_number: row.policy_number,
      status: row.status,
      status_display: row.status_display,
      currency: row.currency,
      frequency: row.frequency,
      installment_count: row.installment_count,
      paid_installments: row.items.filter((it) => it.status === "PAID").length,
      total_amount: row.total_amount,
      paid_amount: row.paid_amount,
      start_date: row.start_date,
      end_date: row.end_date,
    }))
    return data({ count: rows.length, results: rows })
  }),
  http.get(`*${BASE}/portal/:planId/`, ({ params }) => {
    const key = String(params.planId)
    const row = findPlan(key) ?? plans.find((candidate) => candidate.plan_number === key)
    if (!row) return error(404, "PORTAL_RESOURCE_NOT_FOUND", "The requested installment plan could not be found.", ["Check the plan number and try again.", "Ask policy administration to confirm the plan exists for your partner profile."])
    return data({
      id: row.id,
      plan_number: row.plan_number,
      policy_number: row.policy_number,
      status: row.status,
      status_display: row.status_display,
      currency: row.currency,
      frequency: row.frequency,
      installment_count: row.installment_count,
      paid_installments: row.items.filter((it) => it.status === "PAID").length,
      total_amount: row.total_amount,
      paid_amount: row.paid_amount,
      start_date: row.start_date,
      end_date: row.end_date,
      items: row.items.map((it) => ({ id: it.id, installment_number: it.installment_number, due_date: it.due_date, amount: it.amount, status: it.status, status_display: it.status_display })),
    })
  }),
  http.post(`*${BASE}/create/`, async ({ request }) => {
    const idempotencyKey = request.headers.get("X-Idempotency-Key") ?? ""
    if (!idempotencyKey) return error(400, "INSTALLMENT_IDEMPOTENCY_REQUIRED", "Plan creation requires an idempotency key.", ["Retry the request with a unique X-Idempotency-Key header.", "Reuse the same key when retrying the same submission so the original plan is returned."])
    const body = await request.json().catch(() => null) as Record<string, unknown> | null
    const policyId = String(body?.policy_id ?? "")
    const frequency = String(body?.frequency ?? "").toUpperCase()
    const termYears = Number(body?.term_years ?? 0)
    const maturityClaimId = body?.maturity_claim_id ? String(body.maturity_claim_id) : null
    const fingerprint = `${policyId}|${frequency}|${termYears}|${maturityClaimId ?? ""}`
    const existing = plans.find((row) => row.idempotency_key === idempotencyKey)
    if (existing) {
      if (existing.idempotency_fingerprint === fingerprint) return data({ plan: planDetailFor(existing), created: false }, 200)
      return error(409, "INSTALLMENT_IDEMPOTENCY_CONFLICT", "The idempotency key was already used with a different plan payload.", ["Use the existing plan returned for the original key, or generate a new key for a new submission.", "Do not reuse a key after changing policy, claim, frequency, or term."])
    }
    if (policyId === "policy-immature-1") return error(422, "INSTALLMENT_POLICY_NOT_MATURED", "An installment plan can only be created against a matured policy.", ["Confirm the policy status is Matured or Matured pending payment before creating an installment plan.", "Ask Policy Administration to process the maturity event if the policy has not been matured yet."], { policyNumber: "ZIC-OL-2026-000099", policyStatus: "ACTIVE" })
    if (!frequency || !["SINGLE", "MONTHLY", "QUARTERLY", "HALF_YEARLY", "ANNUAL"].includes(frequency)) return error(400, "INSTALLMENT_INVALID_FREQUENCY", "The requested payout frequency is not supported.", ["Choose a frequency from the options catalog.", "Retry creation with a supported frequency and term."])
    const created = buildCreatedPlan(policyId, frequency, termYears, idempotencyKey, maturityClaimId)
    created.idempotency_fingerprint = fingerprint
    if (maturityClaimId) created.claim_number = "OL-CLM-2026-000099"
    plans.push(created)
    return data({ plan: planDetailFor(created), created: true }, 201)
  }),
  http.post(`*${BASE}/items/:itemId/process-payment/`, ({ params }) => {
    const found = findItem(String(params.itemId))
    if (!found) return error(404, "INSTALLMENT_ITEM_NOT_FOUND", "The requested installment item could not be found.", ["Return to the plan schedule and choose an available installment."])
    const { item: it } = found
    if (it.status === "PAID") return error(422, "INSTALLMENT_ITEM_INVALID_STATUS", "A disbursement is only possible for an installment that is not already paid.", ["Review the installment status in the plan schedule.", "Open the payment history to confirm the earlier disbursement."], { currentStatus: "PAID" })
    if (it.status === "PAYMENT_PENDING" && it.requisition_number) {
      return data({ item: { ...it }, requisition: { requisition_number: it.requisition_number, status: "PENDING", status_display: "Pending", amount: it.amount, department: "MATURITY_INSTALLMENTS" }, created: false }, 200)
    }
    if (it.due_date && it.due_date > todayIso()) {
      return error(422, "INSTALLMENT_PAYMENT_NOT_DUE", "This installment is not due for disbursement yet.", ["Check the installment due date in the plan schedule.", "Process the payment once the due date arrives."], { dueDate: it.due_date, today: todayIso() })
    }
    if (it.status === "MISSED" || it.status === "SCHEDULED" || it.status === "PAYMENT_PENDING") {
      it.status = "PAYMENT_PENDING"
      it.status_display = itemStatusLabel("PAYMENT_PENDING")
      it.requisition_number = `FO-MIP-2026-0000${String(400 + found.plan.items.indexOf(it)).padStart(2, "0")}`
      found.plan.updated_at = new Date().toISOString()
      return data({ item: { ...it }, requisition: { requisition_number: it.requisition_number, status: "PENDING", status_display: "Pending", amount: it.amount, department: "MATURITY_INSTALLMENTS" }, created: true }, 201)
    }
    return error(422, "INSTALLMENT_ITEM_INVALID_STATUS", "A disbursement is not possible in the installment's current state.", ["Review the installment status in the plan schedule."], { currentStatus: it.status })
  }),
  http.post(`*${BASE}/items/:itemId/confirm-payment/`, ({ params }) => {
    const found = findItem(String(params.itemId))
    if (!found) return error(404, "INSTALLMENT_ITEM_NOT_FOUND", "The requested installment item could not be found.", ["Return to the plan schedule and choose an available installment."])
    const { plan: row, item: it } = found
    if (it.status === "PAID") return data({ item: { ...it }, confirmed: false }, 200)
    if (it.status !== "PAYMENT_PENDING") return error(422, "INSTALLMENT_ITEM_INVALID_STATUS", "Only a disbursed installment can be confirmed as paid.", ["Process the payment first so the installment is pending disbursement.", "Then confirm the payment once Front Office has disbursed it."], { currentStatus: it.status })
    it.status = "PAID"
    it.status_display = itemStatusLabel("PAID")
    it.paid_date = todayIso()
    it.paid_by_display = "Finance Officer — Rehema S."
    it.payer_display = row.policyholder_display.split(" — ")[0] ?? row.policyholder_name
    it.payment_reference = `FO-PAY-2026-0004${String(row.items.indexOf(it) + 1).padStart(2, "0")}`
    if (row.status === "CREATED") {
      row.status = "ACTIVE"
      row.status_display = planStatusLabel("ACTIVE")
      row.allowed_actions = planAllowedActions("ACTIVE")
    }
    const wasCompleted = row.status === "COMPLETED"
    recomputePlanTotals(row)
    const planCompleted = row.status === "COMPLETED" && !wasCompleted
    return data({ item: { ...it }, plan: planDetailFor(row), plan_completed: planCompleted, confirmed: true }, 200)
  }),
  http.post(`*${BASE}/items/:itemId/reverse-payment/`, async ({ params, request }) => {
    const body = await request.json().catch(() => null) as Record<string, unknown> | null
    const reason = String(body?.reason ?? "").trim()
    if (!reason) return error(400, "INSTALLMENT_REVERSAL_REASON_REQUIRED", "A reason is required to reverse an installment payment.", ["Describe why the payment is being reversed.", "Do not include sensitive credentials in the reason."])
    const found = findItem(String(params.itemId))
    if (!found) return error(404, "INSTALLMENT_ITEM_NOT_FOUND", "The requested installment item could not be found.", ["Return to the plan schedule and choose an available installment."])
    const { item: it } = found
    if (it.status !== "PAID") return error(422, "INSTALLMENT_REVERSAL_NOT_ALLOWED", "Only a paid installment can be reversed.", ["Review the installment status in the plan schedule."], { currentStatus: it.status })
    const daysSincePaid = it.paid_date ? Math.floor((Date.now() - new Date(`${it.paid_date}T00:00:00`).getTime()) / 86400000) : 0
    if (daysSincePaid > 7) return error(422, "INSTALLMENT_REVERSAL_WINDOW_EXPIRED", "The payment is older than the reversal window.", ["The reversal window is 7 days from payment.", "Raise a finance review instead of reversing this installment."], { daysSincePaid, windowDays: 7 })
    it.status = "SCHEDULED"
    it.status_display = itemStatusLabel("SCHEDULED")
    it.requisition_number = null
    it.paid_date = null
    it.paid_by_display = null
    it.payer_display = null
    it.payment_reference = null
    it.narration = reason
    recomputePlanTotals(found.plan)
    return data({ item: { ...it }, plan: planDetailFor(found.plan) }, 200)
  }),
  http.post(`*${BASE}/plans/:planId/cancel/`, async ({ params, request }) => {
    const body = await request.json().catch(() => null) as Record<string, unknown> | null
    const reason = String(body?.reason ?? "").trim()
    if (!reason) return error(400, "INSTALLMENT_CANCELLATION_REASON_REQUIRED", "A reason is required to cancel an installment plan.", ["Describe why the plan is being cancelled.", "Do not include sensitive credentials in the reason."])
    const row = findPlan(String(params.planId))
    if (!row) return error(404, "INSTALLMENT_PLAN_NOT_FOUND", "The requested installment plan could not be found.", ["Return to the plan register and choose an available plan."])
    if (["COMPLETED", "CANCELLED", "TERMINATED"].includes(row.status) || row.items.every((it) => it.status === "PAID")) {
      return error(422, "INSTALLMENT_PLAN_CANNOT_CANCEL", "A terminal or fully paid plan cannot be cancelled.", ["Open the plan to review its lifecycle status.", "Choose a plan that is still active and not fully paid."], { planStatus: row.status })
    }
    row.status = "CANCELLED"
    row.status_display = planStatusLabel("CANCELLED")
    row.allowed_actions = planAllowedActions("CANCELLED")
    row.items.forEach((it) => {
      if (it.status === "SCHEDULED" || it.status === "PAYMENT_PENDING" || it.status === "MISSED") {
        it.status = "WAIVED"
        it.status_display = itemStatusLabel("WAIVED")
        it.requisition_number = null
      }
    })
    recomputePlanTotals(row)
    return data(planDetailFor(row), 200)
  }),
  http.get(`*${BASE}/:planId/reconciliation/`, ({ params }) => {
    const row = findPlan(String(params.planId))
    if (!row) return error(404, "INSTALLMENT_PLAN_NOT_FOUND", "The requested installment plan could not be found.", ["Return to the plan register and choose an available plan."])
    return data(reconciliationFor(row))
  }),
  http.post(`*${BASE}/:planId/print-schedule/`, ({ params }) => {
    const row = findPlan(String(params.planId))
    if (!row) return error(404, "INSTALLMENT_PLAN_NOT_FOUND", "The requested installment plan could not be found.", ["Return to the plan register and choose an available plan."])
    return data({ instance: { id: `doc-${row.id}-schedule`, document_type: "OL_MATURITY_SCHEDULE", template_name: "OL Maturity Schedule", template_version: 1, page_count: 2, generated_by_display: "Sultan Admin", generated_at: new Date().toISOString() }, signed_download_url: `/api/v1/documents/instances/doc-${row.id}-schedule/download/?ticket=mock-schedule-${row.id}`, preview_url: `/api/v1/documents/instances/doc-${row.id}-schedule/preview/` }, 201)
  }),
  http.post(`*${BASE}/:planId/print-advice/`, ({ params }) => {
    const row = findPlan(String(params.planId))
    if (!row) return error(404, "INSTALLMENT_PLAN_NOT_FOUND", "The requested installment plan could not be found.", ["Return to the plan register and choose an available plan."])
    return data({ instance: { id: `doc-${row.id}-advice`, document_type: "OL_MATURITY_PAYMENT_ADVICE", template_name: "OL Maturity Payment Advice", template_version: 1, page_count: 1, generated_by_display: "Sultan Admin", generated_at: new Date().toISOString() }, signed_download_url: `/api/v1/documents/instances/doc-${row.id}-advice/download/?ticket=mock-advice-${row.id}`, preview_url: `/api/v1/documents/instances/doc-${row.id}-advice/preview/` }, 201)
  }),
  http.get(`*${BASE}/:planId/`, ({ params }) => {
    const row = findPlan(String(params.planId))
    return row ? data(planDetailFor(row)) : error(404, "INSTALLMENT_PLAN_NOT_FOUND", "The requested installment plan could not be found.", ["Return to the plan register and choose an available plan."])
  }),
  http.get(`*${BASE}/`, ({ request }) => {
    const url = new URL(request.url)
    return data(page(filteredPlans(url).map(planListRow), url))
  }),
]

import { http, HttpResponse } from "msw"
import { RECEIPTS_BASE, RECEIPTS_OPTIONS_BASE, PORTAL_RECEIPTS_BASE, type ReceiptRecord } from "../lib/receipts-api"

const ids = {
  receipt: "receipt-demo-1",
  branch: "branch-zanzibar",
  payer: "partner-amani",
  document: "receipt-document-1",
}

let receipts: ReceiptRecord[] = [
  {
    id: ids.receipt,
    receipt_number: "RCT-2026-000001",
    receipt_date: "2026-08-24",
    payer_display: "Amani Assurance Partner",
    payer_id: ids.payer,
    branch_display: "Zanzibar Main Branch",
    branch_id: ids.branch,
    payment_mode_display: "Mobile Money",
    payment_mode: "MOBILE_MONEY",
    currency_display: "TZS — Tanzanian Shilling",
    currency: "TZS",
    receipt_amount: "150000.00",
    allocated_amount: "50000.00",
    unallocated_amount: "100000.00",
    source_module: "OL_PROPOSAL",
    payment_reference: "MPESA-20260824-001",
    narration: "First premium collection",
    status: "PARTIALLY_ALLOCATED",
    created_by_display: "Sultan Admin",
    posted_by_display: "Sultan Admin",
    posted_at: "2026-08-24T08:30:00Z",
    bank_account_display: "**** 0042",
    allowed_actions: ["view", "allocate", "auto_allocate", "reverse", "print"],
    amount_in_words: "One hundred fifty thousand Tanzanian shillings only",
  },
]

const options = {
  branches: [{ value: ids.branch, label: "Zanzibar Main Branch", meta: { code: "ZNZ-MAIN" } }, { value: "branch-pemba", label: "Pemba Branch", meta: { code: "PEMBA" } }],
  payers: [{ value: ids.payer, label: "Amani Assurance Partner", meta: { partner_type: "AGENT" } }, { value: "partner-zic", label: "ZIC Individual Policyholder", meta: { partner_type: "INDIVIDUAL" } }],
  proposals: [{ value: "proposal-1", label: "OLP-2026-000001 — Amani Assurance Partner", meta: { status: "FIRST_PREMIUM_DUE", status_hint: "First premium due" } }, { value: "proposal-2", label: "OLP-2026-000002 — ZIC Individual Policyholder", meta: { status: "FIRST_PREMIUM_PAID", status_hint: "First premium already paid" } }],
  sourceModules: [{ value: "DIRECT", label: "Direct payment" }, { value: "OL_PROPOSAL", label: "Ordinary Life proposal" }, { value: "POLICY", label: "Policy" }, { value: "COMMITMENT", label: "Commitment" }],
  currencies: [{ value: "TZS", label: "TZS — Tanzanian Shilling", meta: { symbol: "TSh" } }, { value: "USD", label: "USD — United States Dollar", meta: { symbol: "$" } }],
  paymentModes: [{ value: "CASH", label: "Cash", meta: { requires_reference: false, requires_bank_account: false } }, { value: "MOBILE_MONEY", label: "Mobile Money", meta: { requires_reference: true, requires_bank_account: false } }, { value: "BANK_TRANSFER", label: "Bank Transfer", meta: { requires_reference: true, requires_bank_account: true } }],
  bankAccounts: [{ value: "bank-1", label: "CRDB — Zanzibar Operations — **** 0042", meta: { account_name: "ZIC Zanzibar Operations", masked: true } }],
  statuses: [{ value: "DRAFT", label: "Draft" }, { value: "POSTED", label: "Posted" }, { value: "PARTIALLY_ALLOCATED", label: "Partially Allocated" }, { value: "ALLOCATED", label: "Allocated" }, { value: "REVERSED", label: "Reversed" }, { value: "CANCELLED", label: "Cancelled" }],
}

function data<T>(payload: T, status = 200) {
  return HttpResponse.json({ data: payload }, { status })
}

function error(status: number, errorCode: string, message: string, resolutionSteps: string[], deepLink?: string, fieldErrors: Record<string, string[]> = {}) {
  return HttpResponse.json({
    success: false,
    errorCode,
    message,
    resolutionSteps,
    ...(deepLink ? { deepLink } : {}),
    fieldErrors,
    error: { code: errorCode, message, details: { resolutionSteps, deepLink, fieldErrors } },
  }, { status })
}

function page<T>(results: T[], url: URL) {
  const pageSize = Number(url.searchParams.get("page_size") ?? 25)
  const pageNumber = Number(url.searchParams.get("page") ?? 1)
  const start = (pageNumber - 1) * pageSize
  return { count: results.length, next: null, previous: null, page: pageNumber, page_size: pageSize, results: results.slice(start, start + pageSize) }
}

function findReceipt(id: string) {
  return receipts.find((receipt) => receipt.id === id)
}

function documentFor(receipt: ReceiptRecord) {
  return {
    id: ids.document,
    document_type: "RECEIPT",
    template_name: "Official Receipt",
    template_version: 1,
    generated_by_display: receipt.created_by_display,
    generated_at: "2026-08-24T08:35:00Z",
    page_count: 1,
    preview_url: `/api/v1/front-office/receipts/${receipt.id}/documents/${ids.document}/preview/`,
    signed_download_url: `/api/v1/front-office/receipts/${receipt.id}/documents/${ids.document}/download/?ticket=mock-receipt-ticket`,
  }
}

export const receiptsHandlers = [
  http.get(`*${RECEIPTS_BASE}/import/template/`, () => new HttpResponse("receipt_number,receipt_date,branch,payer,currency,payment_mode,receipt_amount,payment_reference,bank_account,narration\n", { status: 200, headers: { "Content-Type": "text/csv", "Content-Disposition": "attachment; filename=receipt-import-template.csv" } })),
  http.get(`*${RECEIPTS_OPTIONS_BASE}/branches/quick-create-schema/`, () => data({ entity: "branches", permission: "front_office.receipts.create", fields: [{ name: "code", type: "text", required: true }, { name: "name", type: "text", required: true }] })),
  http.post(`*${RECEIPTS_OPTIONS_BASE}/branches/quick-create/`, async ({ request }) => {
    const body = await request.json() as { code?: string; name?: string }
    if (!body.code || !body.name) return error(400, "OPTION_INVALID", "Branch code and name are required.", ["Enter both the branch code and the branch name."], undefined, { code: ["Branch code is required."], name: ["Branch name is required."] })
    const option = { value: `branch-${body.code.toLowerCase()}`, label: `${body.code} — ${body.name}`, meta: { code: body.code } }
    options.branches.unshift(option)
    return data({ option }, 201)
  }),
  http.get(`*${RECEIPTS_OPTIONS_BASE}/payers/quick-create-schema/`, () => data({ entity: "payers", permission: "partners.create", fields: [{ name: "legal_name", type: "text", required: true }, { name: "national_id", type: "text", required: true }, { name: "phone", type: "text", required: true }] })),
  http.post(`*${RECEIPTS_OPTIONS_BASE}/payers/quick-create/`, async ({ request }) => {
    const body = await request.json() as { legal_name?: string; national_id?: string; phone?: string }
    if (!body.legal_name || !body.national_id || !body.phone) return error(400, "OPTION_INVALID", "Payer details are incomplete.", ["Provide the legal name, national ID, and phone number."], undefined, { legal_name: ["Legal name is required."], national_id: ["National ID is required."], phone: ["Phone is required."] })
    const option = { value: `payer-${Date.now()}`, label: body.legal_name, meta: { partner_type: "INDIVIDUAL", national_id: body.national_id, phone: body.phone } }
    options.payers.unshift(option)
    return data({ option }, 201)
  }),
  http.get(`*${RECEIPTS_BASE}/kpis/`, () => data({ received_today: "150000.00", allocated_in_period: "50000.00", unallocated_amount: "100000.00", receipt_count: receipts.length, reversed_amount: "0.00" })),
  http.get(`*${RECEIPTS_BASE}/exchange-rate/`, ({ request }) => {
    const url = new URL(request.url)
    if (url.searchParams.get("currency") === "BAD") return error(422, "RECEIPT_CURRENCY_MISMATCH", "No exchange rate is configured for this currency.", ["Choose a supported currency.", "Configure the exchange rate before retrying."], "/front-office/parameters/exchange-rates")
    return data({ from_currency: url.searchParams.get("currency") ?? "TZS", to_currency: "TZS", rate: "1.000000", effective_date: "2026-08-24" })
  }),
  http.get(`*${RECEIPTS_BASE}/imports/`, ({ request }) => data(page([{ id: "import-1", file_name: "receipts.csv", uploaded_by_display: "Sultan Admin", uploaded_at: "2026-08-24T08:00:00Z", total_rows: 2, ok_count: 2, error_count: 0, status: "COMPLETED" }], new URL(request.url)))),
  http.get(`*${RECEIPTS_BASE}/imports/:id/`, ({ params }) => data({ id: String(params.id), file_name: "receipts.csv", uploaded_by_display: "Sultan Admin", uploaded_at: "2026-08-24T08:00:00Z", total_rows: 2, ok_count: 1, error_count: 1, status: "COMPLETED", errors: [{ row: 2, field_errors: { currency: ["Choose a three-letter ISO currency code, for example TZS."] }, resolution_steps: ["Correct the currency code and re-upload the row."] }] })),
  http.post(`*${RECEIPTS_BASE}/import/dry-run/`, async ({ request }) => {
    const form = await request.formData()
    const file = form.get("file")
    if (!file) return error(400, "RECEIPT_IMPORT_ROW_INVALID", "Attach a CSV file before running a dry-run.", ["Choose the receipt CSV template and upload a file."], undefined, { file: ["This file is required."] })
    return data({ dry_run: true, imported: 2, created: 0, errors: [] })
  }),
  http.post(`*${RECEIPTS_BASE}/import/commit/`, async ({ request }) => {
    const form = await request.formData()
    if (!form.get("file")) return error(400, "RECEIPT_IMPORT_ROW_INVALID", "Attach a CSV file before committing an import.", ["Upload the completed receipt CSV template."], undefined, { file: ["This file is required."] })
    return data({ dry_run: false, imported: 2, created: 2, errors: [] }, 201)
  }),
  http.get(`*${RECEIPTS_BASE}/:id/audit-timeline/`, ({ params }) => {
    const receipt = findReceipt(String(params.id))
    if (!receipt) return error(404, "RECEIPT_NOT_FOUND", "The receipt could not be found.", ["Check the receipt number and try again."])
    return data(page([
      { id: "audit-create-1", action: "create", actor_display: receipt.created_by_display, occurred_at: "2026-08-24T08:00:00Z", before_summary: null, after_summary: "Draft receipt created", reason: "Payment captured at front office", source_channel: "UI" },
      { id: "audit-post-1", action: "post", actor_display: receipt.posted_by_display ?? "Sultan Admin", occurred_at: "2026-08-24T08:30:00Z", before_summary: "DRAFT", after_summary: "POSTED", reason: "Payment verified", source_channel: "UI" },
      { id: "audit-allocate-1", action: "allocate", actor_display: "Sultan Admin", occurred_at: "2026-08-24T08:45:00Z", before_summary: "TZS 150,000 unallocated", after_summary: "TZS 50,000 allocated", reason: "First premium commitment selected", source_channel: "UI" },
      { id: "audit-reverse-1", action: "reverse", actor_display: "Sultan Admin", occurred_at: "2026-08-24T09:00:00Z", before_summary: "POSTED", after_summary: "REVERSED", reason: "Correction requested", source_channel: "UI" },
      { id: "audit-cancel-1", action: "cancel", actor_display: "Sultan Admin", occurred_at: "2026-08-24T09:15:00Z", before_summary: "DRAFT", after_summary: "CANCELLED", reason: "Duplicate draft", source_channel: "UI" },
      { id: "audit-print-1", action: "print", actor_display: "Sultan Admin", occurred_at: "2026-08-24T09:30:00Z", before_summary: "No document", after_summary: "Official Receipt v1 generated", reason: "Receipt print requested", source_channel: "UI" },
    ], new URL("http://mock.local/?page=1&page_size=25")))
  }),
  http.get(`*${RECEIPTS_BASE}/:id/reversals/`, ({ params, request }) => {
    const receipt = findReceipt(String(params.id))
    if (!receipt) return error(404, "RECEIPT_NOT_FOUND", "The receipt could not be found.", ["Check the receipt number and try again."])
    const reversals = receipt.status === "REVERSED" ? [{ id: "reversal-1", reversal_number: "REV-2026-000001", reason: receipt.reversed_reason ?? "Correction requested", created_by_display: "Sultan Admin", created_at: "2026-08-24T09:00:00Z", source_channel: "UI" }] : []
    return data(page(reversals, new URL(request.url)))
  }),
  http.get(`*${RECEIPTS_BASE}/:id/allocations/`, ({ params, request }) => {
    const receipt = findReceipt(String(params.id))
    if (!receipt) return error(404, "RECEIPT_NOT_FOUND", "The receipt could not be found.", ["Check the receipt number and try again."])
    return data(page([{ id: "allocation-1", target_display: "OLC-2026-000001 — OL Proposal OLP-2026-000001", commitment_number: "OLC-2026-000001", source_display: "OL Proposal OLP-2026-000001", amount: "50000.00", currency: receipt.currency, exchange_rate: null, status: "ACTIVE", reversed_at: null }], new URL(request.url)))
  }),
  http.get(`*${RECEIPTS_BASE}/:id/bank-account/`, ({ params }) => {
    const receipt = findReceipt(String(params.id))
    return receipt ? data({ bank_account_display: "CRDB Zanzibar Operations · Account ending 0042" }) : error(404, "RECEIPT_NOT_FOUND", "The receipt could not be found.", ["Check the receipt number and try again."])
  }),
  http.get(`*${RECEIPTS_BASE}/:id/documents/`, ({ params }) => {
    const receipt = findReceipt(String(params.id))
    return receipt ? data(page([documentFor(receipt)], new URL("http://mock.local/?page=1&page_size=25"))) : error(404, "RECEIPT_NOT_FOUND", "The receipt could not be found.", ["Check the receipt number and try again."])
  }),
  http.post(`*${RECEIPTS_BASE}/:id/print/`, ({ params }) => {
    const receipt = findReceipt(String(params.id))
    return receipt ? data({ receipt, document: documentFor(receipt) }, 201) : error(404, "RECEIPT_NOT_FOUND", "The receipt could not be found.", ["Check the receipt number and try again."])
  }),
  http.get(`*${RECEIPTS_BASE}/:id/allocation-options/`, ({ params, request }) => {
    const receipt = findReceipt(String(params.id))
    if (!receipt) return error(404, "RECEIPT_NOT_FOUND", "The receipt could not be found.", ["Check the receipt number and try again."])
    return data(page([{ id: "commitment-1", commitment_number: "OLC-2026-000001", source_display: "OL Proposal OLP-2026-000001", product_display: "Elimu Bora", plan_display: "Growth Plan", due_date: "2026-08-24", balance: "50000.00", currency: receipt.currency, status: "PENDING", is_first_premium: true, proposal_number: "OLP-2026-000001" }], new URL(request.url)))
  }),
  http.post(`*${RECEIPTS_BASE}/:id/allocate/`, async ({ params, request }) => {
    const receipt = findReceipt(String(params.id))
    const body = await request.json() as { allocations?: Array<{ amount?: string; exchange_rate?: string }> }
    const total = (body.allocations ?? []).reduce((sum, row) => sum + Number(row.amount ?? 0), 0)
    if (!receipt) return error(404, "RECEIPT_NOT_FOUND", "The receipt could not be found.", ["Check the receipt number and try again."])
    if (total > Number(receipt.unallocated_amount)) return error(422, "RECEIPT_OVERALLOCATION", "The allocation total exceeds the unallocated receipt balance.", ["Reduce the allocation total.", "Confirm each commitment balance before saving."])
    return data({ receipt: { ...receipt, allocated_amount: String(Number(receipt.allocated_amount) + total), unallocated_amount: String(Number(receipt.unallocated_amount) - total) }, allocations: body.allocations ?? [] })
  }),
  http.post(`*${RECEIPTS_BASE}/:id/auto-allocate/`, ({ params }) => {
    const receipt = findReceipt(String(params.id))
    return receipt ? data({ receipt: { ...receipt, allocated_amount: receipt.receipt_amount, unallocated_amount: "0.00", status: "ALLOCATED" }, allocations: [{ id: "allocation-1", target_display: "OLC-2026-000001 — OL Proposal OLP-2026-000001", amount: receipt.unallocated_amount, currency: receipt.currency, status: "ACTIVE" }], remaining_unallocated_amount: "0.00" }) : error(404, "RECEIPT_NOT_FOUND", "The receipt could not be found.", ["Check the receipt number and try again."])
  }),
  http.post(`*${RECEIPTS_BASE}/:id/post/`, ({ params }) => {
    const receipt = findReceipt(String(params.id))
    if (!receipt) return error(404, "RECEIPT_NOT_FOUND", "The receipt could not be found.", ["Check the receipt number and try again."])
    const posted = { ...receipt, status: "POSTED", posted_by_display: "Sultan Admin", posted_at: "2026-08-24T09:00:00Z" }
    receipts = receipts.map((item) => item.id === receipt.id ? posted : item)
    return data(posted)
  }),
  http.post(`*${RECEIPTS_BASE}/:id/reverse/`, ({ params, request }) => {
    const receipt = findReceipt(String(params.id))
    if (!receipt) return error(404, "RECEIPT_NOT_FOUND", "The receipt could not be found.", ["Check the receipt number and try again."])
    return data({ ...receipt, status: "REVERSED", reversed_reason: typeof request === "object" ? "Reversal requested by operator" : null })
  }),
  http.post(`*${RECEIPTS_BASE}/:id/allocations/:allocationId/reverse/`, ({ params }) => data({ id: String(params.allocationId), target_display: "OLC-2026-000001 — OL Proposal OLP-2026-000001", amount: "50000.00", currency: "TZS", status: "REVERSED", reversed_at: "2026-08-24T09:10:00Z" })),
  http.post(`*${RECEIPTS_BASE}/:id/cancel/`, ({ params }) => {
    const receipt = findReceipt(String(params.id))
    return receipt ? data({ ...receipt, status: "CANCELLED", cancelled_reason: "Cancelled by operator" }) : error(404, "RECEIPT_NOT_FOUND", "The receipt could not be found.", ["Check the receipt number and try again."])
  }),
  http.get(`*${RECEIPTS_BASE}/:id/`, ({ params }) => {
    const receipt = findReceipt(String(params.id))
    return receipt ? data(receipt) : error(404, "RECEIPT_NOT_FOUND", "The receipt could not be found.", ["Check the receipt number and try again."])
  }),
  http.patch(`*${RECEIPTS_BASE}/:id/`, async ({ params, request }) => {
    const receipt = findReceipt(String(params.id))
    if (!receipt) return error(404, "RECEIPT_NOT_FOUND", "The receipt could not be found.", ["Check the receipt number and try again."])
    const updated = { ...receipt, ...(await request.json() as Record<string, unknown>) } as ReceiptRecord
    receipts = receipts.map((item) => item.id === receipt.id ? updated : item)
    return data(updated)
  }),
  http.post(`*${RECEIPTS_BASE}/`, async ({ request }) => {
    if (request.headers.get("X-Idempotency-Key") === "duplicate-demo") return error(409, "RECEIPT_DUPLICATE", "This submission was already received.", ["Open the existing receipt and continue from there."], "/front-office/receipts/receipt-demo-1")
    const body = await request.json() as Record<string, unknown>
    const receipt: ReceiptRecord = { ...receipts[0], ...body, id: `receipt-${Date.now()}`, receipt_number: `RCT-2026-${String(receipts.length + 1).padStart(6, "0")}`, status: "DRAFT", allocated_amount: "0.00", unallocated_amount: String(body.receipt_amount ?? "0.00"), created_by_display: "Sultan Admin", payer_display: String(body.payer ?? "Selected payer"), branch_display: String(body.branch ?? "Selected branch"), payment_mode_display: String(body.payment_mode ?? "Selected payment mode"), currency_display: String(body.currency ?? "TZS") } as ReceiptRecord
    receipts = [receipt, ...receipts]
    return data(receipt, 201)
  }),
  http.get(`*${RECEIPTS_BASE}/`, ({ request }) => {
    const url = new URL(request.url)
    const search = (url.searchParams.get("search") ?? "").toLowerCase()
    const status = url.searchParams.get("status")
    const branch = url.searchParams.get("branch")
    const currency = url.searchParams.get("currency")
    const paymentMode = url.searchParams.get("payment_mode")
    const payer = (url.searchParams.get("payer") ?? "").toLowerCase()
    const sourceModule = (url.searchParams.get("source_module") ?? "").toLowerCase()
    const dateFrom = url.searchParams.get("date_from")
    const dateTo = url.searchParams.get("date_to")
    const unallocatedOnly = url.searchParams.get("unallocated_only") === "true"
    const reversedOnly = url.searchParams.get("reversed_only") === "true"
    const todayOnly = url.searchParams.get("today") === "true"
    const filtered = receipts.filter((receipt) => {
      const searchValues = [receipt.receipt_number, receipt.payer_display, receipt.payment_reference, receipt.source_module]
      return (!status || receipt.status === status)
        && (!branch || receipt.branch_id === branch)
        && (!currency || receipt.currency === currency)
        && (!paymentMode || receipt.payment_mode === paymentMode)
        && (!payer || receipt.payer_display.toLowerCase().includes(payer))
        && (!sourceModule || String(receipt.source_module ?? "").toLowerCase().includes(sourceModule))
        && (!dateFrom || receipt.receipt_date >= dateFrom)
        && (!dateTo || receipt.receipt_date <= dateTo)
        && (!unallocatedOnly || Number(receipt.unallocated_amount) > 0)
        && (!reversedOnly || receipt.status === "REVERSED")
        && (!todayOnly || receipt.receipt_date === "2026-08-24")
        && (!search || searchValues.some((value) => String(value ?? "").toLowerCase().includes(search)))
    })
    return data(page(filtered, url))
  }),
  ...Object.entries(options).map(([entity, values]) => {
    const entityPath = entity.replace(/[A-Z]/g, (letter) => `-${letter.toLowerCase()}`)
    return http.get(`*${RECEIPTS_OPTIONS_BASE}/${entityPath}/`, ({ request }) => {
    const url = new URL(request.url)
    const query = (url.searchParams.get("q") ?? "").toLowerCase()
      return data(page(values.filter((value) => !query || value.label.toLowerCase().includes(query)), url))
    })
  }),
  http.get(`*${PORTAL_RECEIPTS_BASE}/:id/`, ({ params }) => {
    const receipt = findReceipt(String(params.id))
    return receipt ? data({ ...receipt, allowed_actions: [], bank_account_display: null }) : error(404, "RECEIPT_NOT_FOUND", "The receipt could not be found.", ["Check the receipt number and try again."])
  }),
  http.get(`*${PORTAL_RECEIPTS_BASE}/`, ({ request }) => data(page(receipts.map((receipt) => ({ ...receipt, allowed_actions: [], bank_account_display: null })), new URL(request.url)))),
]

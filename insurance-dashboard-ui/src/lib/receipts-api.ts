import { buildQueryString, request, type QueryParams } from "./apiClient"
import { apiFetchAuth } from "./api"

export const RECEIPTS_BASE = "/api/v1/front-office/receipts"
export const RECEIPTS_OPTIONS_BASE = "/api/v1/front-office/options"
export const PORTAL_RECEIPTS_BASE = "/api/v1/portal/receipts"

export type ReceiptStatus = "DRAFT" | "POSTED" | "PARTIALLY_ALLOCATED" | "ALLOCATED" | "REVERSED" | "CANCELLED" | string
export type PaymentMode = "CASH" | "BANK_TRANSFER" | "MOBILE_MONEY" | "CARD" | "CHEQUE" | string

export interface DisplayOption {
  value: string
  label: string
  meta?: Record<string, unknown>
}

export interface ReceiptRecord {
  id: string
  receipt_number: string
  receipt_date: string
  payer_display: string
  payer_id?: string | null
  branch_display: string
  branch_id?: string | null
  payment_mode_display: string
  payment_mode: PaymentMode
  currency_display: string
  currency: string
  receipt_amount: string
  allocated_amount: string
  unallocated_amount: string
  source_module?: string | null
  payment_reference?: string | null
  narration?: string | null
  status: ReceiptStatus
  created_by_display: string
  posted_by_display?: string | null
  posted_at?: string | null
  bank_account_display?: string | null
  allowed_actions?: string[]
  amount_in_words?: string
  reversed_reason?: string | null
  cancelled_reason?: string | null
  [key: string]: unknown
}

export interface ReceiptKpis {
  received_today: string
  allocated_in_period: string
  unallocated_amount: string
  receipt_count: number
  reversed_amount: string
}

export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
  page?: number
  page_size?: number
}

export interface ReceiptDocument {
  id: string
  document_type: string
  template_name: string
  template_version: number
  generated_by_display: string
  generated_at: string
  page_count: number
  preview_url?: string | null
  download_url?: string | null
  signed_download_url?: string | null
}

export interface ReceiptAllocationOption {
  id: string
  commitment_number: string
  source_display: string
  product_display: string
  plan_display: string
  due_date: string
  balance: string
  currency: string
  status: string
  is_first_premium: boolean
  proposal_number?: string | null
}

export interface ReceiptAllocation {
  id: string
  target_display: string
  commitment_number?: string
  source_display?: string
  amount: string
  currency: string
  exchange_rate?: string | null
  status: string
  reversed_at?: string | null
}

export interface ReceiptImportBatch {
  id: string
  file_name: string
  uploaded_by_display: string
  uploaded_at: string
  total_rows: number
  ok_count: number
  error_count: number
  status: string
}

export interface ReceiptImportResult {
  dry_run: boolean
  imported: number
  created: number
  errors: Array<{ row: number; status?: string; field_errors: Record<string, string[]>; resolution_steps?: string[] }>
}

export interface ReceiptListQuery {
  page?: number
  page_size?: number
  search?: string
  ordering?: string
  status?: string
  branch?: string
  currency?: string
  payment_mode?: string
  payer?: string
  source_module?: string
  date_from?: string
  date_to?: string
  unallocated_only?: boolean
  reversed_only?: boolean
  today?: boolean
}

export interface ReceiptWritePayload {
  receipt_date: string
  branch: string
  payer: string
  source_module?: string
  source_reference?: string
  currency: string
  payment_mode: string
  payment_reference?: string
  bank_account?: string
  receipt_amount: string
  narration?: string
}

export interface AllocationPayload {
  allocations: Array<{ commitment: string; amount: string; exchange_rate?: string }>
}

export interface ActionPayload {
  reason?: string
}

async function readJsonRequest<T>(path: string, options?: Parameters<typeof request<T>>[1]): Promise<T> {
  return request<T>(path, options)
}

function jsonOptions(method: "POST" | "PATCH", body?: unknown, headers?: HeadersInit): Parameters<typeof request>[1] {
  return {
    method,
    body: body === undefined ? undefined : JSON.stringify(body),
    headers,
  }
}

function toQuery(query: object): string {
  const params: QueryParams = Object.fromEntries(Object.entries(query).filter(([, value]) => value !== undefined && value !== "")) as QueryParams
  return buildQueryString(params)
}

export const receiptsApi = {
  list: (query: ReceiptListQuery = {}) => readJsonRequest<Paginated<ReceiptRecord>>(`${RECEIPTS_BASE}/${toQuery(query)}`),
  get: (id: string) => readJsonRequest<ReceiptRecord>(`${RECEIPTS_BASE}/${encodeURIComponent(id)}/`),
  create: (payload: ReceiptWritePayload, idempotencyKey: string = crypto.randomUUID()) => readJsonRequest<ReceiptRecord>(`${RECEIPTS_BASE}/`, jsonOptions("POST", payload, { "X-Idempotency-Key": idempotencyKey })),
  patchDraft: (id: string, payload: Partial<ReceiptWritePayload>, idempotencyKey: string = crypto.randomUUID()) => readJsonRequest<ReceiptRecord>(`${RECEIPTS_BASE}/${encodeURIComponent(id)}/`, jsonOptions("PATCH", payload, { "X-Idempotency-Key": idempotencyKey })),
  post: (id: string, idempotencyKey: string = crypto.randomUUID()) => readJsonRequest<ReceiptRecord>(`${RECEIPTS_BASE}/${encodeURIComponent(id)}/post/`, jsonOptions("POST", undefined, { "X-Idempotency-Key": idempotencyKey })),
  allocationOptions: (id: string, query: { search?: string } = {}) => readJsonRequest<Paginated<ReceiptAllocationOption>>(`${RECEIPTS_BASE}/${encodeURIComponent(id)}/allocation-options/${toQuery(query)}`),
  allocate: (id: string, payload: AllocationPayload) => readJsonRequest<{ receipt: ReceiptRecord; allocations: ReceiptAllocation[] }>(`${RECEIPTS_BASE}/${encodeURIComponent(id)}/allocate/`, jsonOptions("POST", payload)),
  autoAllocate: (id: string) => readJsonRequest<{ receipt: ReceiptRecord; allocations: ReceiptAllocation[]; remaining_unallocated_amount: string }>(`${RECEIPTS_BASE}/${encodeURIComponent(id)}/auto-allocate/`, jsonOptions("POST")),
  reverse: (id: string, payload: ActionPayload) => readJsonRequest<ReceiptRecord>(`${RECEIPTS_BASE}/${encodeURIComponent(id)}/reverse/`, jsonOptions("POST", payload)),
  reverseAllocation: (id: string, allocationId: string, payload: ActionPayload) => readJsonRequest<ReceiptAllocation>(`${RECEIPTS_BASE}/${encodeURIComponent(id)}/allocations/${encodeURIComponent(allocationId)}/reverse/`, jsonOptions("POST", payload)),
  cancel: (id: string, payload: ActionPayload) => readJsonRequest<ReceiptRecord>(`${RECEIPTS_BASE}/${encodeURIComponent(id)}/cancel/`, jsonOptions("POST", payload)),
  print: (id: string) => readJsonRequest<{ receipt: ReceiptRecord; document: ReceiptDocument }>(`${RECEIPTS_BASE}/${encodeURIComponent(id)}/print/`, jsonOptions("POST")),
  documents: (id: string) => readJsonRequest<Paginated<ReceiptDocument>>(`${RECEIPTS_BASE}/${encodeURIComponent(id)}/documents/`),
  importDryRun: (file: File | Blob) => {
    const form = new FormData()
    form.append("file", file, file instanceof File ? file.name : "receipts.csv")
    return readJsonRequest<ReceiptImportResult>(`${RECEIPTS_BASE}/import/dry-run/`, { method: "POST", body: form })
  },
  importCommit: (file: File | Blob, mode: "CREATE_DRAFTS" | "POST" | "POST_AND_ALLOCATE" = "CREATE_DRAFTS") => {
    const form = new FormData()
    form.append("file", file, file instanceof File ? file.name : "receipts.csv")
    form.append("mode", mode)
    return readJsonRequest<ReceiptImportResult>(`${RECEIPTS_BASE}/import/commit/`, { method: "POST", body: form })
  },
  imports: (query: { page?: number; page_size?: number } = {}) => readJsonRequest<Paginated<ReceiptImportBatch>>(`${RECEIPTS_BASE}/imports/${toQuery(query)}`),
  importDetail: (id: string) => readJsonRequest<ReceiptImportBatch & { errors: ReceiptImportResult["errors"] }>(`${RECEIPTS_BASE}/imports/${encodeURIComponent(id)}/`),
  kpis: (query: { date_from?: string; date_to?: string } = {}) => readJsonRequest<ReceiptKpis>(`${RECEIPTS_BASE}/kpis/${toQuery(query)}`),
  exchangeRate: (currency: string, date?: string) => readJsonRequest<{ from_currency: string; to_currency: string; rate: string; effective_date: string }>(`${RECEIPTS_BASE}/exchange-rate/${toQuery({ currency, date })}`),
  downloadCsvTemplate: async () => {
    const response = await apiFetchAuth(`${RECEIPTS_BASE}/import/template/`, { headers: { Accept: "text/csv" } })
    if (!response.ok) throw new Error(`Unable to download the receipt CSV template (${response.status}).`)
    return response.blob()
  },
  options: {
    branches: (query = "") => readJsonRequest<Paginated<DisplayOption>>(`${RECEIPTS_OPTIONS_BASE}/branches/${toQuery({ q: query })}`),
    payers: (query = "") => readJsonRequest<Paginated<DisplayOption>>(`${RECEIPTS_OPTIONS_BASE}/payers/${toQuery({ q: query })}`),
    proposals: (query = "") => readJsonRequest<Paginated<DisplayOption>>(`${RECEIPTS_OPTIONS_BASE}/proposals/${toQuery({ q: query })}`),
    sourceModules: (query = "") => readJsonRequest<Paginated<DisplayOption>>(`${RECEIPTS_OPTIONS_BASE}/source-modules/${toQuery({ q: query })}`),
    currencies: (query = "") => readJsonRequest<Paginated<DisplayOption>>(`${RECEIPTS_OPTIONS_BASE}/currencies/${toQuery({ q: query })}`),
    paymentModes: (query = "") => readJsonRequest<Paginated<DisplayOption>>(`${RECEIPTS_OPTIONS_BASE}/payment-modes/${toQuery({ q: query })}`),
    bankAccounts: (query = "") => readJsonRequest<Paginated<DisplayOption>>(`${RECEIPTS_OPTIONS_BASE}/bank-accounts/${toQuery({ q: query })}`),
    statuses: (query = "") => readJsonRequest<Paginated<DisplayOption>>(`${RECEIPTS_OPTIONS_BASE}/statuses/${toQuery({ q: query })}`),
  },
  portal: {
    list: (query: ReceiptListQuery = {}) => readJsonRequest<Paginated<ReceiptRecord>>(`${PORTAL_RECEIPTS_BASE}/${toQuery(query)}`),
    get: (id: string) => readJsonRequest<ReceiptRecord>(`${PORTAL_RECEIPTS_BASE}/${encodeURIComponent(id)}/`),
  },
}

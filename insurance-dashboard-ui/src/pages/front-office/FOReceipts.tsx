import { useCallback, useMemo, useRef, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { Banknote, CalendarDays, FilePlus2, Receipt, RotateCcw, Upload, WalletCards } from "lucide-react"
import { ErrorCoach } from "../../components/ErrorCoach"
import { AllocationProgressBar, AmountCell, PaymentModeBadge, ReceiptStatusBadge } from "../../components/receipts/ReceiptPrimitives"
import { DataTable, type TableFetcher } from "../../components/ui/DataTable"
import { FilterBar, type FilterValues } from "../../components/ui/FilterBar"
import { InfoBanner } from "../../components/ui/Overlays"
import { MasterDetailPage } from "../../components/ui/Patterns"
import type { RowAction, TableColumn } from "../../components/ui/types"
import { useAccess } from "../../lib/access"
import { ApiClientError, type TableQuery } from "../../lib/apiClient"
import { receiptsApi, type DisplayOption, type ReceiptKpis, type ReceiptListQuery, type ReceiptRecord } from "../../lib/receipts-api"

const ACTION_PERMISSIONS: Record<string, string> = {
  view: "front_office.receipts.view",
  edit: "front_office.receipts.edit",
  post: "front_office.receipts.post",
  allocate: "front_office.receipts.allocate",
  auto_allocate: "front_office.receipts.allocate",
  reverse: "front_office.receipts.reverse",
  cancel: "front_office.receipts.cancel",
  print: "front_office.receipts.print",
}

const ACTION_META: Array<{ key: string; label: string; tone?: "danger" }> = [
  { key: "view", label: "View" },
  { key: "edit", label: "Edit draft" },
  { key: "post", label: "Post" },
  { key: "allocate", label: "Allocate" },
  { key: "reverse", label: "Reverse", tone: "danger" },
  { key: "cancel", label: "Cancel", tone: "danger" },
  { key: "print", label: "Print" },
]

const CHIP_FILTERS = {
  unallocated: { unallocated_only: "true" },
  reversed: { reversed_only: "true" },
  today: { today: "true" },
} as const

type ReceiptChip = keyof typeof CHIP_FILTERS | null
type ReceiptListRow = ReceiptRecord & Record<string, unknown>

function asString(value: unknown): string | undefined {
  if (typeof value === "string" && value) return value
  if (typeof value === "number") return String(value)
  if (Array.isArray(value) && value.length > 0) return String(value[0])
  return undefined
}

function dateRange(value: unknown): { from?: string; to?: string } {
  if (typeof value === "string") {
    const [from, to] = value.split(",")
    return { from: from || undefined, to: to || undefined }
  }
  if (value && typeof value === "object" && !Array.isArray(value)) return value as { from?: string; to?: string }
  return {}
}

export function mapReceiptFilters(filters: Record<string, unknown>): ReceiptListQuery {
  const range = dateRange(filters.receipt_date)
  return {
    status: asString(filters.status),
    branch: asString(filters.branch),
    currency: asString(filters.currency),
    payment_mode: asString(filters.payment_mode),
    payer: asString(filters.payer),
    source_module: asString(filters.source_module),
    date_from: range.from,
    date_to: range.to,
    unallocated_only: asString(filters.unallocated_only) === "true" ? true : undefined,
    reversed_only: asString(filters.reversed_only) === "true" ? true : undefined,
    today: asString(filters.today) === "true" ? true : undefined,
  }
}

export function receiptRowActionEnabled(key: string, row: ReceiptListRow, isSuperAdmin: boolean, hasPermission: (code: string) => boolean): boolean {
  const allowedActions = Array.isArray(row.allowed_actions) ? row.allowed_actions.map((value) => String(value).toLowerCase()) : []
  const backendDecides = allowedActions.length > 0
  const permission = ACTION_PERMISSIONS[key]
  const permitted = isSuperAdmin || (permission ? hasPermission(permission) : false)
  if (!permitted) return false
  if (key === "view") return true
  if (!backendDecides) return key === "edit" ? String(row.status).toUpperCase() === "DRAFT" : false
  return allowedActions.includes(key.toLowerCase())
}

function optionToFilter(option: DisplayOption) {
  return { label: option.label, value: option.value }
}

function errorCoachProps(error: unknown) {
  if (error instanceof ApiClientError) return { message: error.message, resolutionSteps: error.resolutionSteps, loginUrl: error.deepLink, actionLabel: error.deepLink ? "Open resolution page" : undefined }
  return { message: error instanceof Error ? error.message : "The receipts service could not be reached. Refresh and try again." }
}

function defaultKpis(): ReceiptKpis {
  return { received_today: "0.00", allocated_in_period: "0.00", unallocated_amount: "0.00", receipt_count: 0, reversed_amount: "0.00" }
}

export default function FOReceipts() {
  const navigate = useNavigate()
  const { access, isSuperAdmin, hasPermission: accessHasPermission } = useAccess()
  const [filters, setFilters] = useState<FilterValues>({})
  const [chip, setChip] = useState<ReceiptChip>(null)
  const [refreshKey, setRefreshKey] = useState(0)
  const [listError, setListError] = useState<unknown>(null)
  const [listCount, setListCount] = useState<number | null>(null)
  const [importError, setImportError] = useState<unknown>(null)
  const [importMessage, setImportMessage] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const hasPermission = useCallback((permission: string) => isSuperAdmin || Boolean(accessHasPermission?.(permission)), [accessHasPermission, isSuperAdmin])
  const permissionKeys = useMemo(() => access.permissions.map((permission) => `${permission.module}.${permission.action}`.toLowerCase()), [access.permissions])

  const kpisQuery = useQuery({ queryKey: ["receipts", "kpis"], queryFn: () => receiptsApi.kpis(), staleTime: 30_000 })
  const branchesQuery = useQuery({ queryKey: ["receipts", "options", "branches"], queryFn: () => receiptsApi.options.branches(), staleTime: 5 * 60_000 })
  const currenciesQuery = useQuery({ queryKey: ["receipts", "options", "currencies"], queryFn: () => receiptsApi.options.currencies(), staleTime: 5 * 60_000 })
  const paymentModesQuery = useQuery({ queryKey: ["receipts", "options", "payment-modes"], queryFn: () => receiptsApi.options.paymentModes(), staleTime: 5 * 60_000 })
  const statusesQuery = useQuery({ queryKey: ["receipts", "options", "statuses"], queryFn: () => receiptsApi.options.statuses(), staleTime: 5 * 60_000 })

  const fetcher: TableFetcher<ReceiptListRow> = useCallback(async (query: TableQuery) => {
    try {
      const payload = await receiptsApi.list({ ...mapReceiptFilters(query.filters ?? {}), page: query.page, page_size: query.pageSize, search: typeof query.search === "string" ? query.search : undefined, ordering: query.ordering })
      setListError(null)
      setListCount(payload.count)
      return payload
    } catch (error) {
      setListError(error)
      setListCount(0)
      return { results: [], count: 0, page: query.page, page_size: query.pageSize }
    }
  }, [])

  const applyChip = (nextChip: Exclude<ReceiptChip, null>) => {
    setChip((current) => {
      const next = current === nextChip ? null : nextChip
      setFilters((currentFilters) => {
        const nextFilters = { ...currentFilters }
        Object.values(CHIP_FILTERS).forEach((chipFilters) => Object.keys(chipFilters).forEach((key) => delete nextFilters[key]))
        return next ? { ...nextFilters, ...CHIP_FILTERS[next] } : nextFilters
      })
      return next
    })
  }

  const handleImport = async (file: File) => {
    setImportError(null)
    setImportMessage(null)
    try {
      const result = await receiptsApi.importDryRun(file)
      setImportMessage(`Dry-run complete: ${result.imported} rows checked, ${result.errors.length} blocking errors.`)
      if (result.errors.length > 0) setImportError(new Error("The CSV contains rows that need correction before import."))
    } catch (error) {
      setImportError(error)
    }
  }

  const actions: RowAction<ReceiptListRow>[] = useMemo(() => ACTION_META.map((action) => ({
    key: action.key,
    label: action.label,
    tone: action.tone,
    onSelect: (row) => {
      if (action.key === "view") navigate(`/front-office/receipts/${row.id}`)
      else navigate(`/front-office/receipts/${row.id}?action=${encodeURIComponent(action.key)}`)
    },
  })), [navigate])

  const canAction = useCallback((action: RowAction<ReceiptListRow>, row: ReceiptListRow) => receiptRowActionEnabled(action.key, row, isSuperAdmin, hasPermission), [hasPermission, isSuperAdmin])

  const columns: TableColumn<ReceiptListRow>[] = useMemo(() => [
    { key: "receipt_number", label: "Receipt number", field: "receipt_number", sortable: true, render: (_value, row) => <button type="button" className="font-semibold text-[var(--primary)] underline-offset-2 hover:underline" onClick={() => navigate(`/front-office/receipts/${row.id}`)}>{row.receipt_number}</button> },
    { key: "receipt_date", label: "Date", field: "receipt_date", sortable: true },
    { key: "payer_display", label: "Payer", field: "payer_display" },
    { key: "branch_display", label: "Branch", field: "branch_display" },
    { key: "payment_mode_display", label: "Payment mode", render: (_value, row) => <PaymentModeBadge mode={row.payment_mode} label={row.payment_mode_display} /> },
    { key: "currency_display", label: "Currency", field: "currency_display", align: "center" },
    { key: "receipt_amount", label: "Receipt amount", field: "receipt_amount", align: "right", sortable: true, render: (_value, row) => <AmountCell amount={row.receipt_amount} currency={row.currency} amountInWords={row.amount_in_words} /> },
    { key: "allocation", label: "Allocation", render: (_value, row) => <AllocationProgressBar allocated={row.allocated_amount} total={row.receipt_amount} currency={row.currency} /> },
    { key: "state", label: "Status", field: "status", sortable: true, render: (_value, row) => <ReceiptStatusBadge status={row.status} /> },
    { key: "source_module", label: "Source", field: "source_module" },
    { key: "created_by_display", label: "Created by", field: "created_by_display" },
    { key: "posted_by_display", label: "Posted by", field: "posted_by_display" },
  ], [navigate])

  const optionList = (optionsQuery: { data?: { results: DisplayOption[] } }) => (optionsQuery.data?.results ?? []).map(optionToFilter)
  const filterDefinitions = useMemo(() => [
    { key: "status", label: "Status", type: "select" as const, options: optionList(statusesQuery), placeholder: "Any status" },
    { key: "branch", label: "Branch", type: "select" as const, options: optionList(branchesQuery), placeholder: "Any branch" },
    { key: "currency", label: "Currency", type: "select" as const, options: optionList(currenciesQuery), placeholder: "Any currency" },
    { key: "payment_mode", label: "Payment mode", type: "select" as const, options: optionList(paymentModesQuery), placeholder: "Any mode" },
    { key: "payer", label: "Payer", type: "text" as const, placeholder: "Payer name" },
    { key: "source_module", label: "Source module", type: "text" as const, placeholder: "OL_PROPOSAL, POLICY…" },
    { key: "receipt_date", label: "Receipt date", type: "date-range" as const },
  ], [branchesQuery, currenciesQuery, paymentModesQuery, statusesQuery])

  const kpis = kpisQuery.data ?? defaultKpis()
  const stats = [
    { label: "Received Today", value: <AmountCell amount={kpis.received_today} currency="TZS" />, helper: "All posted receipts today" },
    { label: "Allocated in Period", value: <AmountCell amount={kpis.allocated_in_period} currency="TZS" />, helper: "Applied to commitments" },
    { label: "Unallocated Amount", value: <AmountCell amount={kpis.unallocated_amount} currency="TZS" />, helper: "Needs allocation", },
    { label: "Receipt Count", value: kpis.receipt_count.toLocaleString(), helper: "Receipts in the register" },
    { label: "Reversed Amount", value: <AmountCell amount={kpis.reversed_amount} currency="TZS" />, helper: "Reversed in period" },
  ]

  return (
    <div className="space-y-5 p-4 md:p-6">
      <MasterDetailPage
        eyebrow="Front Office"
        title="Receipts Work Queue"
        description="Register incoming payments, monitor unallocated balances, and follow the next permitted action for each receipt."
        stats={stats}
        actions={
          <>
            <button type="button" className="button-secondary" onClick={() => fileRef.current?.click()} disabled={!hasPermission("front_office.receipts.import")}><Upload size={16} aria-hidden="true" />Import CSV</button>
            <input ref={fileRef} type="file" accept=".csv,text/csv" className="hidden" onChange={(event) => { const file = event.target.files?.[0]; if (file) void handleImport(file); event.target.value = "" }} />
            <button type="button" className="button-primary" onClick={() => navigate("/front-office/receipts/new")} disabled={!hasPermission("front_office.receipts.create")}><FilePlus2 size={16} aria-hidden="true" />New Receipt</button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Receipt quick filters">
            <span className="mr-1 inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.12em] text-[var(--muted-foreground)]"><Receipt size={14} aria-hidden="true" />Quick views</span>
            {(Object.keys(CHIP_FILTERS) as Array<Exclude<ReceiptChip, null>>).map((key) => {
              const labels = { unallocated: "Unallocated Only", reversed: "Reversed Only", today: "Today" }
              return <button key={key} type="button" aria-pressed={chip === key} onClick={() => applyChip(key)} className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${chip === key ? "border-[var(--primary)] bg-[var(--primary)]/10 text-[var(--primary)]" : "border-[var(--border)] text-[var(--muted-foreground)] hover:text-[var(--foreground)]"}`}>{labels[key]}</button>
            })}
            {chip && <button type="button" className="inline-flex items-center gap-1 text-xs underline-offset-2 hover:underline" onClick={() => applyChip(chip)}><RotateCcw size={13} aria-hidden="true" />Clear quick view</button>}
          </div>

          <FilterBar definitions={filterDefinitions} value={filters} onChange={(key, value) => setFilters((current) => ({ ...current, [key]: value }))} onReset={() => { setFilters({}); setChip(null) }} />

          {(listError || kpisQuery.error || branchesQuery.error || currenciesQuery.error || paymentModesQuery.error || statusesQuery.error) && <ErrorCoach title="Receipts need attention" {...errorCoachProps(listError ?? kpisQuery.error ?? branchesQuery.error ?? currenciesQuery.error ?? paymentModesQuery.error ?? statusesQuery.error)} />}
          {importMessage && <InfoBanner title="Receipt CSV dry-run"><p>{importMessage}</p></InfoBanner>}
          {importError !== null && <ErrorCoach title="Receipt import needs correction" {...errorCoachProps(importError)} />}
          {!listError && listCount === 0 && <InfoBanner title="No receipts match the current view"><p>Try clearing filters, changing the date range, or create a new receipt when a payment is received.</p></InfoBanner>}

          <DataTable<ReceiptListRow>
            metadata={{ columns, defaultOrdering: "-receipt_date", pageSize: 20, totalLabel: "Receipts" }}
            fetcher={fetcher}
            filters={filters}
            refreshKey={refreshKey}
            actions={actions}
            permissions={permissionKeys}
            canAction={canAction}
            exportFileName="front-office-receipts.csv"
            caption="Front Office receipts register"
            hideSearch
          />
          <div className="sr-only" aria-live="polite">{listCount === null ? "Loading receipts" : `${listCount} receipts found`}</div>
        </div>
      </MasterDetailPage>
      <div className="sr-only"><CalendarDays aria-hidden="true" /><Banknote aria-hidden="true" /><WalletCards aria-hidden="true" /></div>
    </div>
  )
}

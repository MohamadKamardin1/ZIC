import { useCallback, useEffect, useMemo, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { FilePlus2 } from "lucide-react"
import { buildTableQuery, request, type TableQuery } from "../../lib/apiClient"
import { DocumentInstancesPanel } from "../../components/documents/DocumentInstancesPanel"
import { useAccess } from "../../lib/access"
import { DataTable, normalizeTableResponse } from "../../components/ui/DataTable"
import { FilterBar, type FilterValues } from "../../components/ui/FilterBar"
import { ConfirmModal, InfoBanner } from "../../components/ui/Overlays"
import { MasterDetailPage } from "../../components/ui/Patterns"
import OLQuotationDetailPage from "./OLQuotationDetail"
import { StatusBadge, type StatusTone } from "../../components/ui/StatusBadge"
import { useToast } from "../../components/ui/Toast"
import { renderFk, scrubUuids } from "../../lib/display"
import type { RowAction, TableColumn, TableMetadata } from "../../components/ui/types"

type ActionKey = "view" | "edit" | "revise" | "finalize" | "print" | "convert_to_proposal" | "delete"

type ActionMetadata = {
  key: ActionKey
  visible?: boolean
  enabled?: boolean
  url?: string
  method?: string
  permission?: string
  state_allowed?: boolean
  reason?: string | null
}

type QuotationRecord = {
  id: string
  quote_number: string
  quote_name: string
  prospect_name: string
  plans_summary: string
  plan_count: number
  total_premium?: string | number | null
  currency?: string | null
  currency_display?: string | null
  status: string
  status_badge?: { code?: string; label?: string; tone?: string }
  version: number
  quote_date: string
  agent?: { id?: string; name?: string; username?: string } | null
  agent_display?: string | null
  created_by?: { id?: string; name?: string; username?: string } | null
  created_by_display?: string | null
  partner_display?: string | null
  branch_display?: string | null
  product_display?: string | null
  row_actions?: Partial<Record<ActionKey, ActionMetadata>>
}

export type QuotationKpis = {
  total_drafts: number
  total_finalized: number
  total_converted: number
  total_expired: number
  total_premium_sum: string | number | null
  avg_days_to_finalize: string | number | null
  currency: string | null
  premium_by_currency?: Record<string, string | number>
  timestamp?: string
}

type ConfirmState = { kind: "delete" | "finalize" | "revise" | "convert"; row: QuotationRecord } | null

const API_PREFIX = "/api/v1/ol/quotations/quotations/"
export const KPI_ENDPOINT = "/api/v1/ol/quotations/kpis/"

export const emptyKpis: QuotationKpis = {
  total_drafts: 0,
  total_finalized: 0,
  total_converted: 0,
  total_expired: 0,
  total_premium_sum: null,
  avg_days_to_finalize: null,
  currency: null,
}

type FilterInput = Record<string, unknown>

function serverQuotationFilters(filters: FilterInput): Record<string, string> {
  const result: Record<string, string> = {}
  Object.entries(filters).forEach(([key, value]) => {
    if (value === null || value === undefined || value === "") return
    if (key === "quote_date") {
      if (typeof value === "object" && !Array.isArray(value)) {
        const range = value as { from?: string; to?: string }
        if (range.from) result.quote_date_from = range.from
        if (range.to) result.quote_date_to = range.to
        return
      }
      const [from, to] = String(value).split(",")
      if (from) result.quote_date_from = from
      if (to) result.quote_date_to = to
      return
    }
    result[key] = Array.isArray(value) ? value.join(",") : String(value)
  })
  return result
}

export function buildQuotationKpiQuery(filters: FilterInput = {}): string {
  return buildTableQuery({ filters: serverQuotationFilters(filters) })
}

function numericValue(value: unknown, fallback = 0): number {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : fallback
}

function normalizeQuotationKpis(value: unknown): QuotationKpis {
  const record = value && typeof value === "object" ? value as Record<string, unknown> : {}
  const nullableValue = (key: string, fallbackKey: string): string | number | null => {
    const raw = record[key] ?? record[fallbackKey]
    return raw === null || raw === undefined || raw === "" ? null : raw as string | number
  }
  return {
    total_drafts: numericValue(record.total_drafts ?? record.totalDrafts),
    total_finalized: numericValue(record.total_finalized ?? record.totalFinalized),
    total_converted: numericValue(record.total_converted ?? record.totalConverted),
    total_expired: numericValue(record.total_expired ?? record.totalExpired),
    total_premium_sum: nullableValue("total_premium_sum", "totalPremiumSum"),
    avg_days_to_finalize: nullableValue("avg_days_to_finalize", "avgDaysToFinalize"),
    currency: typeof (record.currency ?? record.reportingCurrency) === "string" ? String(record.currency ?? record.reportingCurrency) : null,
    premium_by_currency: record.premium_by_currency && typeof record.premium_by_currency === "object" ? record.premium_by_currency as Record<string, string | number> : undefined,
    timestamp: typeof (record.timestamp) === "string" ? record.timestamp : undefined,
  }
}

export function formatCurrency(value: string | number | null | undefined, currency?: string | null, locale?: string): string {
  if (value === null || value === undefined || value === "") return "—"
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return "—"
  if (!currency) return new Intl.NumberFormat(locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(numeric)
  try {
    return new Intl.NumberFormat(locale, { style: "currency", currency, minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(numeric)
  } catch {
    return `${currency} ${new Intl.NumberFormat(locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(numeric)}`
  }
}

export function formatNumber(value: string | number | null | undefined, maximumFractionDigits = 0, locale?: string): string {
  if (value === null || value === undefined || value === "") return "—"
  const numeric = Number(value)
  return Number.isFinite(numeric) ? new Intl.NumberFormat(locale, { maximumFractionDigits }).format(numeric) : "—"
}

export function useQuotationKpis(filters: FilterInput, refreshKey: number) {
  const query = useMemo(() => buildQuotationKpiQuery(filters), [filters])
  const [state, setState] = useState<{ data: QuotationKpis | null; loading: boolean; error: Error | null }>({ data: null, loading: true, error: null })

  useEffect(() => {
    let active = true
    setState((current) => ({ data: current.data, loading: true, error: null }))
    request<unknown>(`${KPI_ENDPOINT}${query}`).then((payload) => {
      if (active) setState({ data: normalizeQuotationKpis(payload), loading: false, error: null })
    }).catch((reason: unknown) => {
      if (active) setState((current) => ({ data: current.data, loading: false, error: reason instanceof Error ? reason : new Error("Unable to load quotation KPIs.") }))
    })
    return () => { active = false }
  }, [query, refreshKey])

  return state
}

const filterDefinitions = [
  { key: "quote_date", label: "Quote date", type: "date-range" as const },
]

function textValue(value: unknown): string {
  return value === null || value === undefined || value === "" ? "—" : scrubUuids(value)
}

function statusTone(status: string): StatusTone {
  switch (status.toUpperCase()) {
    case "DRAFT": return "neutral"
    case "FINALIZED": return "success"
    case "CONVERTED": return "info"
    case "EXPIRED": return "danger"
    default: return "neutral"
  }
}

function amountLabel(value: string | number | null | undefined, currency?: string | null): string {
  return formatCurrency(value, currency)
}

function dateLabel(value?: string | null): string {
  if (!value) return "—"
  const parsed = new Date(`${value.slice(0, 10)}T00:00:00`)
  return Number.isNaN(parsed.getTime()) ? value : new Intl.DateTimeFormat("en-GB", { dateStyle: "medium" }).format(parsed)
}

function normalizeActionMetadata(value: unknown): Partial<Record<ActionKey, ActionMetadata>> | undefined {
  if (!value || typeof value !== "object") return undefined
  const source = value as Record<string, unknown>
  const normalized: Partial<Record<ActionKey, ActionMetadata>> = {}
  ;(["view", "edit", "revise", "finalize", "print", "convert_to_proposal", "delete"] as ActionKey[]).forEach((key) => {
    const candidate = source[key] ?? source[key.replace(/_([a-z])/g, (_match, letter: string) => letter.toUpperCase())]
    if (candidate && typeof candidate === "object") normalized[key] = candidate as ActionMetadata
  })
  return Object.keys(normalized).length ? normalized : undefined
}

function normalizeQuotationRecord(value: QuotationRecord & { rowActions?: unknown }): QuotationRecord {
  const record = value as unknown as Record<string, unknown>
  return {
    ...value,
    id: String(record.id ?? ""),
    quote_number: String(record.quote_number ?? record.quoteNumber ?? ""),
    quote_name: String(record.quote_name ?? record.quoteName ?? ""),
    prospect_name: String(record.prospect_name ?? record.prospectName ?? ""),
    plans_summary: String(record.plans_summary ?? record.plansSummary ?? ""),
    plan_count: Number(record.plan_count ?? record.planCount ?? 0),
    total_premium: (record.total_premium ?? record.totalPremium) as string | number | null | undefined,
    currency: record.currency as string | null | undefined,
    currency_display: (record.currency_display ?? record.currencyDisplay) as string | null | undefined,
    status: String(record.status ?? "").toUpperCase(),
    status_badge: (record.status_badge ?? record.statusBadge) as QuotationRecord["status_badge"],
    version: Number(record.version ?? 1),
    quote_date: String(record.quote_date ?? record.quoteDate ?? ""),
    agent: record.agent as QuotationRecord["agent"],
    agent_display: (record.agent_display ?? record.agentDisplay) as string | null | undefined,
    created_by: (record.created_by ?? record.createdBy) as QuotationRecord["created_by"],
    created_by_display: (record.created_by_display ?? record.createdByDisplay) as string | null | undefined,
    partner_display: (record.partner_display ?? record.partnerDisplay) as string | null | undefined,
    branch_display: (record.branch_display ?? record.branchDisplay) as string | null | undefined,
    product_display: (record.product_display ?? record.productDisplay) as string | null | undefined,
    row_actions: normalizeActionMetadata(record.row_actions ?? record.rowActions),
  }
}

function actionPath(row: QuotationRecord, key: ActionKey, fallback: string): string {
  return row.row_actions?.[key]?.url ?? `${API_PREFIX}${row.id}${fallback}`
}

function buildQuotationColumns(navigate: (path: string) => void): TableColumn<QuotationRecord>[] {
  return [
  { key: "quote_number", label: "Quote number", field: "quote_number", sortable: true, render: (_value, row) => <button type="button" className="font-semibold text-[var(--primary)] underline decoration-[var(--primary)]/35 underline-offset-2 hover:decoration-[var(--primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]" onClick={() => navigate(`/ordinary-life/quotations/${row.id}`)} aria-label={`Open quotation ${row.quote_number}`}>{row.quote_number}</button> },
  { key: "quote_name", label: "Quote name", field: "quote_name", sortable: true },
  { key: "prospect_name", label: "Prospect", field: "prospect_name", sortable: true },
  { key: "plans", label: "Plans", render: (_value, row) => <div><span className="font-semibold">{row.plan_count}</span><span className="ml-2 text-xs text-[var(--muted-foreground)]">{textValue(row.plans_summary)}</span></div> },
  { key: "total_premium", label: "Total premium", field: "total_premium", sortable: true, align: "right", render: (_value, row) => amountLabel(row.total_premium, row.currency) },
  { key: "currency", label: "Currency", field: "currency", sortable: true, align: "center", render: (_value, row) => renderFk(row.currency, row.currency_display) },
  { key: "state", label: "Status", field: "status", sortable: true, render: (_value, row) => <StatusBadge value={row.status_badge?.label ?? row.status} tone={statusTone(row.status)} /> },
  { key: "version", label: "Version", field: "version", sortable: true, align: "center" },
  { key: "quote_date", label: "Quote date", field: "quote_date", sortable: true, render: (value) => dateLabel(value as string | null) },
  { key: "agent_name", label: "Agent", render: (_value, row) => renderFk(row.agent, row.agent_display) },
  { key: "created_by_name", label: "Created by", render: (_value, row) => renderFk(row.created_by, row.created_by_display) },
  ]
}

export default function OLQuotations() {
  const navigate = useNavigate()
  const { access, canAccess, isSuperAdmin } = useAccess()
  const columns = useMemo(() => buildQuotationColumns(navigate), [navigate])
  const { toast } = useToast()
  const [filters, setFilters] = useState<FilterValues>({})
  const [refreshKey, setRefreshKey] = useState(0)
  const kpiState = useQuotationKpis(filters, refreshKey)
  const [confirm, setConfirm] = useState<ConfirmState>(null)
  const [busy, setBusy] = useState(false)
  const [documentTarget, setDocumentTarget] = useState<QuotationRecord | null>(null)

  const permissionKeys = useMemo(() => access.permissions.map((permission) => `${permission.module}.${permission.action}`.toLowerCase()), [access.permissions])
  const hasPermission = useCallback((permission: string) => {
    if (!access.permissions.length) return canAccess("ol_quotations")
    return permissionKeys.includes(permission.toLowerCase())
  }, [access.permissions.length, canAccess, permissionKeys])

  const fetcher = useCallback(async (query: TableQuery) => {
    const table = normalizeTableResponse<QuotationRecord & { rowActions?: unknown }>(await request<unknown>(`${API_PREFIX}${buildTableQuery({ ...query, filters: serverQuotationFilters(query.filters ?? {}) })}`))
    return { ...table, results: table.results.map(normalizeQuotationRecord) }
  }, [])

  const runAction = useCallback(async (row: QuotationRecord, key: "revise" | "finalize" | "convert_to_proposal") => {
    const fallback = key === "revise" ? "/revise/" : key === "finalize" ? "/finalize/" : "/convert/"
    const url = actionPath(row, key, fallback)
    setBusy(true)
    try {
      await request(url, { method: "POST" })
      const labels = { revise: "Quotation revision created", finalize: "Quotation finalized", convert_to_proposal: "Quotation converted to proposal" }
      toast({ tone: "success", title: labels[key] })
      setRefreshKey((value) => value + 1)
      setConfirm(null)
    } catch (error) {
      toast({ tone: "danger", title: "Quotation action failed", message: error instanceof Error ? error.message : "The quotation action was rejected." })
    } finally { setBusy(false) }
  }, [toast])

  const deleteQuotation = useCallback(async () => {
    if (!confirm || confirm.kind !== "delete") return
    setBusy(true)
    try {
      await request(actionPath(confirm.row, "delete", "/"), { method: "DELETE" })
      toast({ tone: "success", title: "Quotation deleted" })
      setConfirm(null)
      setRefreshKey((value) => value + 1)
    } catch (error) {
      toast({ tone: "danger", title: "Unable to delete quotation", message: error instanceof Error ? error.message : "The quotation could not be deleted." })
    } finally { setBusy(false) }
  }, [confirm, toast])

  const printQuotation = useCallback((row: QuotationRecord) => {
    setDocumentTarget(row)
  }, [])

  const actions: RowAction<QuotationRecord>[] = useMemo(() => [
    { key: "view", label: "View", onSelect: (row) => navigate(`/ordinary-life/quotations/${row.id}`) },
    { key: "edit", label: "Edit", onSelect: (row) => navigate(`/ordinary-life/quotations/${row.id}/edit`) },
    { key: "revise", label: "Revise", onSelect: (row) => setConfirm({ kind: "revise", row }) },
    { key: "finalize", label: "Finalize", onSelect: (row) => setConfirm({ kind: "finalize", row }) },
    { key: "print", label: "Print", onSelect: (row) => { void printQuotation(row) } },
    { key: "convert_to_proposal", label: "Convert to Proposal", onSelect: (row) => setConfirm({ kind: "convert", row }) },
    { key: "delete", label: "Delete", tone: "danger", onSelect: (row) => setConfirm({ kind: "delete", row }) },
  ], [navigate, printQuotation])

  const canAction = useCallback((action: RowAction<QuotationRecord>, row: QuotationRecord) => {
    const key = action.key as ActionKey
    const backendAction = row.row_actions?.[key]
    if (backendAction) return Boolean(backendAction.visible && backendAction.enabled)
    if (key === "view") return isSuperAdmin || hasPermission("ol_quotations.view")
    if (key === "edit") return row.status === "DRAFT" && (isSuperAdmin || hasPermission("ol_quotations.update"))
    if (key === "revise") return row.status === "FINALIZED" && (isSuperAdmin || hasPermission("ol_quotations.update"))
    if (key === "finalize") return row.status === "DRAFT" && (isSuperAdmin || hasPermission("ol_quotations.finalize"))
    if (key === "print") return ["FINALIZED", "CONVERTED"].includes(row.status) && (isSuperAdmin || hasPermission("ol_quotations.print"))
    if (key === "convert_to_proposal") return row.status === "FINALIZED" && (isSuperAdmin || hasPermission("ol_quotations.convert"))
    if (key === "delete") return row.status === "DRAFT" && (isSuperAdmin || hasPermission("ol_quotations.delete"))
    return false
  }, [hasPermission, isSuperAdmin])

  const kpis = kpiState.data ?? emptyKpis
  const stats = [
    { label: "Drafts", value: kpiState.loading ? "…" : formatNumber(kpis.total_drafts), helper: kpiState.data && kpis.total_drafts === 0 ? "No quotations match these filters" : "Editable quotations" },
    { label: "Finalized", value: kpiState.loading ? "…" : formatNumber(kpis.total_finalized), helper: kpiState.data && kpis.total_finalized === 0 ? "No quotations match these filters" : "Ready for downstream actions" },
    { label: "Converted", value: kpiState.loading ? "…" : formatNumber(kpis.total_converted), helper: kpiState.data && kpis.total_converted === 0 ? "No quotations match these filters" : "Handed off to proposals" },
    { label: "Expired", value: kpiState.loading ? "…" : formatNumber(kpis.total_expired), helper: kpiState.data && kpis.total_expired === 0 ? "No quotations match these filters" : "Outside validity period" },
    { label: "Premium total", value: kpiState.loading ? "…" : formatCurrency(kpis.total_premium_sum, kpis.currency), helper: kpis.currency ? `Reporting currency: ${kpis.currency}` : "Select one currency to total premiums" },
    { label: "Avg. days to finalize", value: kpiState.loading ? "…" : kpis.avg_days_to_finalize === null ? "—" : `${formatNumber(kpis.avg_days_to_finalize, 2)} days`, helper: "Finalized and converted quotations" },
  ]

  const onConfirm = () => {
    if (!confirm) return
    if (confirm.kind === "delete") return void deleteQuotation()
    if (confirm.kind === "finalize") return void runAction(confirm.row, "finalize")
    if (confirm.kind === "revise") return void runAction(confirm.row, "revise")
    if (confirm.kind === "convert") return void runAction(confirm.row, "convert_to_proposal")
  }

  return <div className="space-y-5 p-4 md:p-6">
    {documentTarget && <DocumentInstancesPanel sourceType="ol_quotations.olquotation" objectId={documentTarget.id} documentType="OL_QUOTATION" title={`Quotation documents · ${documentTarget.quote_number}`} renderLabel="Generate quotation PDF" />}
    <MasterDetailPage
      eyebrow="Ordinary Life"
      title="Quotations"
      description="Review, manage, and progress Ordinary Life quotations through the work queue. Search and filters are applied server-side."
      stats={stats}
      actions={<button type="button" className="button-primary" onClick={() => navigate("/ordinary-life/quotations/new")} disabled={!canAccess("ol_quotations")}><FilePlus2 size={16} aria-hidden="true" />Create New Quote</button>}
    >
      {kpiState.error && <InfoBanner title="Quotation KPIs unavailable" className="border-red-200 bg-red-50 text-red-900 dark:border-red-900/60 dark:bg-red-950/30 dark:text-red-100">{kpiState.error.message}. The quotation table remains available; try changing the filters or refresh the page.</InfoBanner>}
      <div className="space-y-3">
        <div className="surface-card flex flex-wrap items-end gap-3 p-4" role="group" aria-label="Quotation filters">
          {([ ["status", "Status", "DRAFT or FINALIZED"], ["plan", "Plan", "Plan code or name"], ["agent", "Agent", "Agent name or username"], ["location", "Location", "Location"], ["branch", "Branch", "Branch code or name"], ["currency", "Currency", "ISO currency code"] ] as const).map(([key, label, placeholder]) => <div key={key} className="min-w-44 flex-1"><label className="mb-1.5 block text-xs font-bold uppercase tracking-[0.12em] text-[var(--muted-foreground)]" htmlFor={`quotation-filter-${key}`}>{label}</label><input id={`quotation-filter-${key}`} value={typeof filters[key] === "string" ? filters[key] as string : ""} onChange={(event) => setFilters((current) => ({ ...current, [key]: event.target.value }))} placeholder={placeholder} className="h-10 w-full rounded-[10px] border bg-[var(--card)] px-3 text-sm outline-none focus:border-[var(--ring)]" /></div>)}
        </div>
        <FilterBar definitions={filterDefinitions} value={filters} onChange={(key, value) => setFilters((current) => ({ ...current, [key]: value }))} onReset={() => setFilters({})} />
      </div>
            <DataTable<QuotationRecord>

        metadata={{ columns, defaultOrdering: "-quote_date", pageSize: 20, totalLabel: "Quotations" } satisfies TableMetadata<QuotationRecord>}
        fetcher={fetcher}
        filters={filters}
        refreshKey={refreshKey}
        actions={actions}
        permissions={[]}
        canAction={canAction}
        exportFileName="ol-quotations.csv"
        caption="Ordinary Life quotations work queue"
      />
    </MasterDetailPage>
    <ConfirmModal open={Boolean(confirm)} title={confirm?.kind === "delete" ? "Delete quotation" : confirm?.kind === "finalize" ? "Finalize quotation" : confirm?.kind === "convert" ? "Convert quotation to proposal" : "Revise quotation"} description={confirm?.kind === "delete" ? `Delete ${confirm?.row.quote_number ?? "this quotation"}? Draft deletion cannot be undone.` : confirm?.kind === "finalize" ? `Finalize ${confirm?.row.quote_number ?? "this quotation"}? It will become read-only until revised.` : confirm?.kind === "convert" ? `Convert ${confirm?.row.quote_number ?? "this quotation"} to a proposal?` : `Create a new editable version from ${confirm?.row.quote_number ?? "this quotation"}?`} confirmLabel={confirm?.kind === "delete" ? "Delete" : confirm?.kind === "finalize" ? "Finalize" : confirm?.kind === "convert" ? "Convert" : "Revise"} onClose={() => { if (!busy) setConfirm(null) }} onConfirm={onConfirm} />
  </div>
}

export function OLQuotationDetail() {
  return <OLQuotationDetailPage />
}

export { default as OLQuotationWizard } from "./OLQuotationWizard"

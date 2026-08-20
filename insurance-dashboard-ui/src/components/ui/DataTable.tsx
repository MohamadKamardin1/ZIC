import { ChevronDown, ChevronUp, Download, FileUp, MoreHorizontal, RefreshCw } from "lucide-react"
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react"
import { createPortal } from "react-dom"
import { buildTableQuery, request, type TableQuery } from "../../lib/apiClient"
import type { FilterValues } from "./FilterBar"
import type { RowAction, TableMetadata, TableResponse } from "./types"
export type { TableResponse } from "./types"
import { StatusBadge } from "./StatusBadge"
import { renderFk } from "../../lib/display"

const FK_FIELD_KEYS = new Set(["agent", "branch", "benefit_type", "beneficial_type", "created_by", "currency", "facility", "fund", "location", "medical_facility", "partner", "payment_mode", "plan", "product", "rider", "linked_partner"])

function isForeignKeyField(field: string) {
  if (field.endsWith("_id")) return true
  const normalized = field.endsWith("_id") ? field.slice(0, -3) : field
  return FK_FIELD_KEYS.has(normalized) || normalized.endsWith("_type") || normalized.endsWith("_relation")
}

export type TableFetcher<T> = (query: TableQuery) => Promise<TableResponse<T>>

export function normalizeTableResponse<T>(payload: unknown): TableResponse<T> {
  const data = payload && typeof payload === "object" && "data" in payload ? (payload as { data: unknown }).data : payload
  if (Array.isArray(data)) return { results: data as T[], count: data.length, page: 1, page_size: data.length }
  if (data && typeof data === "object") {
    const record = data as Record<string, unknown>
    const results = Array.isArray(record.results) ? record.results as T[] : Array.isArray(record.items) ? record.items as T[] : []
    return { results, count: Number(record.count ?? record.total ?? results.length), next: record.next as string | null | undefined, previous: record.previous as string | null | undefined, page: Number(record.page ?? 1), page_size: Number(record.page_size ?? record.pageSize ?? results.length) }
  }
  return { results: [], count: 0, page: 1, page_size: 0 }
}

export async function fetchTable<T>(endpoint: string, query: TableQuery) {
  return normalizeTableResponse<T>(await request<unknown>(`${endpoint}${buildTableQuery(query)}`))
}

type DataTableProps<T> = {
  metadata: TableMetadata<T>
  fetcher: TableFetcher<T>
  filters?: FilterValues
  refreshKey?: string | number
  actions?: RowAction<T>[]
  permissions?: string[]
  canAction?: (action: RowAction<T>, row: T) => boolean
  onImportCsv?: (file: File) => void | Promise<void>
  exportFileName?: string
  caption?: string
  className?: string
}

export function DataTable<T extends Record<string, unknown>>({ metadata, fetcher, filters = {}, refreshKey, actions = [], permissions = [], canAction, onImportCsv, exportFileName = "zic-export.csv", caption, className = "" }: DataTableProps<T>) {
  const [rows, setRows] = useState<T[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(metadata.pageSize ?? 10)
  const [search, setSearch] = useState("")
  const [ordering, setOrdering] = useState(metadata.defaultOrdering ?? "")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [openAction, setOpenAction] = useState<string | null>(null)
  const [actionPosition, setActionPosition] = useState<{ top: number; left: number } | null>(null)
  const [refreshTick, setRefreshTick] = useState(0)
  const fileRef = useRef<HTMLInputElement>(null)
  const actionTriggerRef = useRef<HTMLButtonElement | null>(null)
  const actionMenuRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!openAction) return
    const updatePosition = () => {
      const trigger = actionTriggerRef.current
      if (!trigger) return
      const rect = trigger.getBoundingClientRect()
      const menuWidth = 176
      const left = Math.max(8, Math.min(rect.right - menuWidth, window.innerWidth - menuWidth - 8))
      const top = rect.bottom + 6
      setActionPosition({ top, left })
    }
    const closeIfOutside = (event: MouseEvent) => {
      const target = event.target as Node
      if (!actionTriggerRef.current?.contains(target) && !actionMenuRef.current?.contains(target)) {
        setOpenAction(null)
        setActionPosition(null)
      }
    }
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") { setOpenAction(null); setActionPosition(null) }
    }
    updatePosition()
    document.addEventListener("mousedown", closeIfOutside)
    document.addEventListener("keydown", closeOnEscape)
    window.addEventListener("resize", updatePosition)
    window.addEventListener("scroll", updatePosition, true)
    return () => {
      document.removeEventListener("mousedown", closeIfOutside)
      document.removeEventListener("keydown", closeOnEscape)
      window.removeEventListener("resize", updatePosition)
      window.removeEventListener("scroll", updatePosition, true)
    }
  }, [openAction])

  const query = useMemo(() => ({ page, pageSize, search, ordering, filters: Object.fromEntries(Object.entries(filters).map(([key, value]) => [key, Array.isArray(value) ? value.join(",") : typeof value === "object" ? `${value.from ?? ""},${value.to ?? ""}` : value])) }), [filters, ordering, page, pageSize, search])

  useEffect(() => {
    let active = true
    setLoading(true)
    setError(null)
    fetcher(query).then((result) => { if (!active) return; setRows(result.results); setTotal(result.count) }).catch((reason: unknown) => { if (!active) return; setError(reason instanceof Error ? reason.message : "Unable to load records.") }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [fetcher, query, refreshKey, refreshTick])

  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const availableActions = (row: T) => actions.filter((action) => (!action.permission || permissions.includes(action.permission)) && (action.isVisible ? action.isVisible(row) : true) && (canAction ? canAction(action, row) : true))
  const renderValue = (column: TableMetadata<T>["columns"][number], row: T, index: number): ReactNode => {
    const fieldKey = String(column.field ?? column.key)
    const rawValue = column.field ? row[column.field] : row[column.key]
    const displayValue = row[`${fieldKey}_display`] ?? row[`${column.key}_display`]
    const safeValue: unknown = isForeignKeyField(fieldKey) ? renderFk(rawValue, displayValue) : rawValue
    if (column.render) return column.render(safeValue, row, index)
    if (isForeignKeyField(fieldKey)) return String(safeValue)
    if (rawValue === null || rawValue === undefined || rawValue === "") return "—"
    if (typeof rawValue === "string" || typeof rawValue === "number") return rawValue
    if (typeof rawValue === "boolean") return rawValue ? "Yes" : "No"
    return renderFk(rawValue, displayValue)
  }

  function toggleOrdering(column: TableMetadata<T>["columns"][number]) {
    if (!column.sortable) return
    const key = String(column.field ?? column.key)
    setPage(1)
    setOrdering(ordering === key ? `-${key}` : ordering === `-${key}` ? "" : key)
  }

  function exportCsv() {
    const columns = metadata.columns
    const csvRows = [columns.map((column) => column.label), ...rows.map((row, index) => columns.map((column) => { const fieldKey = String(column.field ?? column.key); const value = isForeignKeyField(fieldKey) ? renderFk(column.field ? row[column.field] : row[column.key], row[`${fieldKey}_display`] ?? row[`${column.key}_display`], "") : column.field ? row[column.field] : row[column.key]; return String(value ?? "").split('"').join('""') }))]
    const csv = csvRows.map((line) => line.map((value) => `"${value}"`).join(",")).join("\n")
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }))
    const link = document.createElement("a"); link.href = url; link.download = exportFileName; link.click(); URL.revokeObjectURL(url)
  }

  return <section className={`surface-card overflow-hidden ${className}`} aria-label={caption ?? "Data table"}><div className="flex flex-wrap items-center justify-between gap-3 border-b bg-[var(--muted)]/35 px-4 py-3"><div><p className="text-sm font-bold">{caption ?? metadata.totalLabel ?? "Records"}</p><p className="text-xs text-[var(--muted-foreground)]">{total.toLocaleString()} total records</p></div><div className="flex flex-wrap items-center justify-end gap-2"><label className="sr-only" htmlFor="data-table-search">Search records</label><input id="data-table-search" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} className="h-9 w-52 rounded-md border bg-[var(--card)] px-3 text-sm" placeholder="Search records" /><button type="button" className="button-secondary !min-h-9 !px-3" onClick={() => setRefreshTick((current) => current + 1)} aria-label="Refresh table"><RefreshCw size={15} aria-hidden="true" />Refresh</button><button type="button" className="button-secondary !min-h-9 !px-3" onClick={exportCsv} disabled={!rows.length}><Download size={15} aria-hidden="true" />Export CSV</button>{onImportCsv && <><input ref={fileRef} type="file" accept=".csv,text/csv" className="hidden" onChange={(event) => { const file = event.target.files?.[0]; if (file) void onImportCsv(file); event.target.value = "" }} /><button type="button" className="button-secondary !min-h-9 !px-3" onClick={() => fileRef.current?.click()}><FileUp size={15} aria-hidden="true" />Import CSV</button></>}</div></div><div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><caption className="sr-only">{caption ?? "Data table"}</caption><thead className="bg-[var(--muted)]/45 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><tr>{metadata.columns.map((column) => <th key={column.key} scope="col" style={{ width: column.width }} className={`px-4 py-3 font-bold ${column.align === "right" ? "text-right" : column.align === "center" ? "text-center" : ""}`}><button type="button" disabled={!column.sortable} onClick={() => toggleOrdering(column)} className={`inline-flex items-center gap-1 ${column.sortable ? "cursor-pointer hover:text-[var(--foreground)]" : "cursor-default"}`}>{column.label}{ordering === String(column.field ?? column.key) && <ChevronUp size={14} aria-hidden="true" />}{ordering === `-${String(column.field ?? column.key)}` && <ChevronDown size={14} aria-hidden="true" />}</button></th>)}{actions.length > 0 && <th scope="col" className="px-4 py-3 text-right font-bold">Actions</th>}</tr></thead><tbody className="divide-y divide-[var(--border)]">{loading && <tr><td colSpan={metadata.columns.length + (actions.length ? 1 : 0)} className="px-4 py-16 text-center text-[var(--muted-foreground)]"><RefreshCw className="mx-auto mb-2 animate-spin" size={22} aria-hidden="true" />Loading records…</td></tr>}{!loading && error && <tr><td colSpan={metadata.columns.length + (actions.length ? 1 : 0)} className="px-4 py-16 text-center"><p className="font-semibold text-[var(--destructive)]">{error}</p><button type="button" className="button-secondary mt-3" onClick={() => setRefreshTick((current) => current + 1)}>Try again</button></td></tr>}{!loading && !error && rows.length === 0 && <tr><td colSpan={metadata.columns.length + (actions.length ? 1 : 0)} className="px-4 py-16 text-center text-[var(--muted-foreground)]">No records match the current filters.</td></tr>}{!loading && !error && rows.map((row, index) => <tr key={String(row.id ?? row.uuid ?? index)} className="transition hover:bg-[var(--muted)]/25">{metadata.columns.map((column) => <td key={column.key} className={`px-4 py-3 ${column.align === "right" ? "text-right" : column.align === "center" ? "text-center" : ""}`}>{column.key.toLowerCase().includes("status") ? <StatusBadge value={String(column.field ? row[column.field] ?? "—" : row[column.key] ?? "—")} /> : renderValue(column, row, index)}</td>)}{actions.length > 0 && <td className="px-4 py-3 text-right"><button type="button" data-action-trigger="true" className="inline-flex min-h-9 min-w-9 items-center justify-center rounded-md p-2 transition hover:bg-[var(--secondary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]" aria-label={`Actions for row ${index + 1}`} aria-expanded={openAction === String(row.id ?? index)} onClick={(event) => { const key = String(row.id ?? index); if (openAction === key) { setOpenAction(null); setActionPosition(null); return } actionTriggerRef.current = event.currentTarget; const rect = event.currentTarget.getBoundingClientRect(); setActionPosition({ top: rect.bottom + 6, left: Math.max(8, Math.min(rect.right - 176, window.innerWidth - 184)) }); setOpenAction(key) }}><MoreHorizontal size={17} aria-hidden="true" /></button>{openAction === String(row.id ?? index) && actionPosition && createPortal(<div ref={actionMenuRef} data-datatable-action-menu="true" style={{ position: "fixed", top: actionPosition.top, left: actionPosition.left, zIndex: 1000 }} className="min-w-44 rounded-[10px] border border-[var(--border)] bg-[var(--popover)] p-1 text-left shadow-xl">{availableActions(row).map((action) => <button key={action.key} type="button" className={`flex w-full items-center rounded-md px-3 py-2 text-sm transition hover:bg-[var(--secondary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] ${action.tone === "danger" ? "text-[var(--destructive)]" : ""}`} onClick={() => { action.onSelect(row); setOpenAction(null); setActionPosition(null) }}>{action.label}</button>)}{availableActions(row).length === 0 && <span className="block px-3 py-2 text-xs text-[var(--muted-foreground)]">No actions available</span>}</div>, document.body)}</td>}</tr>)}</tbody></table></div><div className="flex flex-wrap items-center justify-between gap-3 border-t px-4 py-3"><div className="flex items-center gap-2 text-xs text-[var(--muted-foreground)]"><span>Rows per page</span><select value={pageSize} onChange={(event) => { setPageSize(Number(event.target.value)); setPage(1) }} className="h-8 rounded-md border bg-[var(--card)] px-2 text-xs"><option value={10}>10</option><option value={25}>25</option><option value={50}>50</option></select><span>Page {page} of {totalPages}</span></div><div className="flex gap-2"><button type="button" className="button-secondary !min-h-8 !px-3" disabled={page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>Previous</button><button type="button" className="button-secondary !min-h-8 !px-3" disabled={page >= totalPages} onClick={() => setPage((current) => Math.min(totalPages, current + 1))}>Next</button></div></div></section>
}

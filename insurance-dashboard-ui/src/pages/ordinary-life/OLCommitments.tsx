import { useCallback, useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import { useQueryClient } from "@tanstack/react-query"
import { FilePlus2, Workflow } from "lucide-react"
import { useAccess } from "../../lib/access"
import type { TableQuery } from "../../lib/apiClient"
import { DataTable, normalizeTableResponse, type TableFetcher } from "../../components/ui/DataTable"
import { FilterBar, type FilterValues } from "../../components/ui/FilterBar"
import { MasterDetailPage } from "../../components/ui/Patterns"
import { InfoBanner } from "../../components/ui/Overlays"
import { useToast } from "../../components/ui/Toast"
import { ErrorCoach } from "../../components/commitments/ErrorCoach"
import { CommitmentStatusBadge, commitmentStatusLabel } from "../../components/commitments/CommitmentStatusBadge"
import { DueDateWarning } from "../../components/commitments/DueDateWarning"
import { notifyCommitmentSuccess, notifyCommitmentFailure } from "../../lib/commitmentsNotify"
import { useCommitmentKPIs, useCommitmentOptions } from "../../lib/commitmentsHooks"
import {
  importCommitmentRows,
  listCommitments,
  normalizeCommitment,
  type CommitmentListFilters,
  type CommitmentRecord,
} from "../../lib/commitments"
import type { RowAction, TableColumn } from "../../components/ui/types"

type CommitmentListRow = CommitmentRecord & Record<string, unknown>
type ChipKey = "overdue" | "in_grace" | "outstanding" | null

const DEFAULT_STATUSES = ["PENDING", "PARTIALLY_PAID", "OVERDUE", "SUSPENDED", "WAIVED", "COMPLETED", "CANCELLED"]
const DEFAULT_CURRENCIES = ["TZS", "USD"]

const CHIP_FILTERS: Record<Exclude<ChipKey, null>, FilterValues> = {
  overdue: { overdue_only: "true" },
  in_grace: { status: "IN_GRACE" },
  outstanding: { balance_only: "true" },
}

const CHIPS: Array<{ key: Exclude<ChipKey, null>; label: string }> = [
  { key: "overdue", label: "Overdue" },
  { key: "in_grace", label: "In Grace" },
  { key: "outstanding", label: "Outstanding" },
]

export function formatMoney(value: string | number | null | undefined, currency = "TZS"): string {
  if (value === null || value === undefined || value === "") return "—"
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return String(value)
  try {
    return new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 2 }).format(numeric)
  } catch {
    return `${currency} ${numeric.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  }
}

export function dateLabel(value?: string | null): string {
  if (!value) return "—"
  const parsed = new Date(`${String(value).slice(0, 10)}T00:00:00`)
  return Number.isNaN(parsed.getTime()) ? String(value) : new Intl.DateTimeFormat("en-GB", { dateStyle: "medium" }).format(parsed)
}

export function sourceLabel(sourceType?: string): string {
  switch (String(sourceType ?? "").toUpperCase()) {
    case "PROPOSAL": return "Proposal"
    case "POLICY": return "Policy"
    case "MANUAL": return "Manual"
    default: return String(sourceType ?? "—")
  }
}

export function isTerminalCommitmentStatus(status: string): boolean {
  return ["COMPLETED", "CANCELLED"].includes(String(status ?? "").toUpperCase())
}

export function rowActionEnabled(
  key: string,
  row: CommitmentListRow,
  isSuperAdmin: boolean,
  hasPermission: (code: string) => boolean,
): boolean {
  const allowed = (row.allowedActions ?? []).map((action) => action.toLowerCase())
  const backendDecides = allowed.length > 0
  const backendAllows = backendDecides && allowed.includes(key.toLowerCase())
  const terminal = isTerminalCommitmentStatus(row.status)
  const has = (code: string) => isSuperAdmin || hasPermission(code)

  switch (key) {
    case "view":
      return has("ol_commitments.view")
    case "record_payment":
      return backendDecides ? backendAllows : !terminal && has("ol_commitments.record_payment")
    case "reverse":
      return backendDecides ? backendAllows : !terminal && has("ol_commitments.reverse")
    case "suspend":
      return backendDecides ? backendAllows : !terminal && String(row.status).toUpperCase() !== "SUSPENDED" && has("ol_commitments.suspend")
    case "waive":
      return backendDecides ? backendAllows : !terminal && has("ol_commitments.waive")
    case "cancel":
      return backendDecides ? backendAllows : !terminal && has("ol_commitments.cancel")
    case "reschedule":
      return backendDecides ? backendAllows : !terminal && has("ol_commitments.reschedule")
    default:
      return false
  }
}

function asString(value: unknown): string | undefined {
  if (typeof value === "string") return value
  if (Array.isArray(value) && value.length > 0) return String(value[0])
  return undefined
}

function dueRange(value: unknown): { from?: string; to?: string } {
  if (typeof value === "string") {
    const [from, to] = value.split(",")
    return { from: from || undefined, to: to || undefined }
  }
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as { from?: string; to?: string }
  }
  return {}
}

function mapFilters(filters: Record<string, unknown>): CommitmentListFilters {
  return {
    status: asString(filters.status),
    product: asString(filters.product),
    sourceType: asString(filters.source_type) as CommitmentListFilters["sourceType"],
    currency: asString(filters.currency),
    dueDateFrom: dueRange(filters.due_date).from,
    dueDateTo: dueRange(filters.due_date).to,
    overdueOnly: asString(filters.overdue_only) === "true",
    balanceOnly: asString(filters.balance_only) === "true",
  }
}

const ORDERING_MAP: Record<string, string> = {
  commitmentNumber: "commitment_number",
  dueDate: "due_date",
  premiumAmount: "premium_amount",
  amountPaid: "amount_paid",
  balance: "balance",
}

function toBackendOrdering(value?: string): string | undefined {
  if (!value) return undefined
  const negative = value.startsWith("-") ? "-" : ""
  const key = value.replace(/^-/, "")
  return `${negative}${ORDERING_MAP[key] ?? key}`
}

const ACTION_META: Array<{ key: string; label: string; tone?: "danger" }> = [
  { key: "record_payment", label: "Record Payment" },
  { key: "reverse", label: "Reverse", tone: "danger" },
  { key: "suspend", label: "Suspend" },
  { key: "waive", label: "Waive" },
  { key: "cancel", label: "Cancel", tone: "danger" },
  { key: "reschedule", label: "Reschedule" },
]

export default function OLCommitments() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { access, isSuperAdmin, canAccess } = useAccess()
  const [filters, setFilters] = useState<FilterValues>({})
  const [chip, setChip] = useState<ChipKey>(null)
  const [refreshKey, setRefreshKey] = useState(0)
  const [listError, setListError] = useState<unknown>(null)
  const [importErrors, setImportErrors] = useState<Array<{ row: number; message: string }>>([])
  const [importing, setImporting] = useState(false)

  const kpisQuery = useCommitmentKPIs()
  const optionsQuery = useCommitmentOptions()

  const permissionKeys = useMemo(
    () => access.permissions.map((permission) => `${permission.module}.${permission.action}`.toLowerCase()),
    [access.permissions],
  )
  const hasPermission = useCallback(
    (code: string) => {
      if (isSuperAdmin) return true
      if (access.permissions.length === 0) return code.endsWith(".view") ? canAccess("ol_commitments") : false
      return permissionKeys.includes(code.toLowerCase())
    },
    [access.permissions.length, canAccess, isSuperAdmin, permissionKeys],
  )

  const optionStatuses = useMemo(
    () =>
      (optionsQuery.data?.statuses ?? []).length > 0
        ? optionsQuery.data!.statuses.map((status) => ({ label: status.name || status.code, value: status.code }))
        : DEFAULT_STATUSES.map((code) => ({ label: commitmentStatusLabel(code), value: code })),
    [optionsQuery.data],
  )
  const optionCurrencies = useMemo(
    () =>
      (optionsQuery.data?.currencies ?? []).map((currency) => ({ label: currency, value: currency })),
    [optionsQuery.data],
  )

  const filterDefinitions = useMemo(
    () => [
      { key: "status", label: "Status", type: "select" as const, options: optionStatuses, placeholder: "Any status" },
      { key: "product", label: "Product", type: "text" as const, placeholder: "Product name or code" },
      {
        key: "source_type",
        label: "Source",
        type: "select" as const,
        options: [
          { label: "Proposal", value: "PROPOSAL" },
          { label: "Policy", value: "POLICY" },
          { label: "Manual", value: "MANUAL" },
        ],
      },
      {
        key: "currency",
        label: "Currency",
        type: "select" as const,
        options: optionCurrencies.length ? optionCurrencies : DEFAULT_CURRENCIES.map((currency) => ({ label: currency, value: currency })),
      },
      { key: "due_date", label: "Due date", type: "date-range" as const },
    ],
    [optionCurrencies, optionStatuses],
  )

  const fetcher: TableFetcher<CommitmentListRow> = useCallback(async (query: TableQuery) => {
    try {
      const commitmentFilters: CommitmentListFilters = {
        ...mapFilters(query.filters ?? {}),
        page: query.page,
        pageSize: query.pageSize,
        search: typeof query.search === "string" && query.search ? query.search : asString(query.filters?.search),
        ordering: toBackendOrdering(query.ordering),
      }
      const payload = await listCommitments(commitmentFilters)
      setListError(null)
      return { ...normalizeTableResponse<CommitmentListRow>(payload), results: payload.results.map(normalizeCommitment) }
    } catch (error) {
      setListError(error)
      return { results: [], count: 0, page: 1, page_size: 0 }
    }
  }, [])

  const applyChip = (key: Exclude<ChipKey, null>) => {
    setChip((current) => {
      const next = current === key ? null : key
      setFilters((previous) => {
        if (!next) return previous
        const merged: FilterValues = { ...previous }
        for (const other of Object.keys(CHIP_FILTERS) as Array<Exclude<ChipKey, null>>) {
          for (const filterKey of Object.keys(CHIP_FILTERS[other])) {
            if (filterKey in merged) delete merged[filterKey]
          }
        }
        return { ...merged, ...CHIP_FILTERS[next] }
      })
      return next
    })
  }

  const onImportCsv = useCallback(
    async (file: File) => {
      setImporting(true)
      setImportErrors([])
      try {
        const records = parseCsv(await file.text())
        if (records.length === 0) {
          setImportErrors([{ row: 1, message: "The CSV must contain a header row and at least one data row." }])
          return
        }
        const result = await importCommitmentRows({ rows: records })
        if (result.imported > 0) {
          notifyCommitmentSuccess(toast, "Commitments imported", `${result.imported} commitment row(s) created. Refresh the register to review.`)
          setRefreshKey((value) => value + 1)
          void queryClient.invalidateQueries({ queryKey: ["commitments", "kpis"] })
        }
        if (result.errors?.length) {
          setImportErrors(result.errors.map((error) => ({ row: error.row, message: error.field_errors ? Object.values(error.field_errors).flat().join(" ") : error.message ?? "Row rejected." })))
        }
      } catch (error) {
        setImportErrors([{ row: 1, message: error instanceof Error ? error.message : "The CSV could not be read." }])
        notifyCommitmentFailure(toast, error, "Import failed")
      } finally {
        setImporting(false)
      }
    },
    [queryClient, toast],
  )

  const actions: RowAction<CommitmentListRow>[] = useMemo(
    () => [
      { key: "view", label: "View", onSelect: (row) => navigate(`/ordinary-life/commitments/${row.id}`) },
      ...ACTION_META.map((meta) => ({
        key: meta.key,
        label: meta.label,
        tone: meta.tone,
        onSelect: (row: CommitmentListRow) => navigate(`/ordinary-life/commitments/${row.id}?action=${encodeURIComponent(meta.key)}`),
      })),
    ],
    [navigate],
  )

  const canAction = useCallback(
    (action: RowAction<CommitmentListRow>, row: CommitmentListRow) => rowActionEnabled(action.key, row, isSuperAdmin, hasPermission),
    [hasPermission, isSuperAdmin],
  )

  const columns: TableColumn<CommitmentListRow>[] = useMemo(
    () => [
      {
        key: "commitment_number",
        label: "Commitment",
        field: "commitmentNumber",
        sortable: true,
        render: (_value, row) => (
          <button type="button" className="font-semibold text-[var(--foreground)] underline-offset-2 hover:underline" onClick={() => navigate(`/ordinary-life/commitments/${row.id}`)}>
            {row.commitmentNumber || "—"}
          </button>
        ),
      },
      {
        key: "source_display",
        label: "Source",
        render: (_value, row) => (
          <div className="flex flex-col">
            <span className="font-semibold">{sourceLabel(row.sourceType)}</span>
            {row.sourceReference && <span className="text-xs text-[var(--muted-foreground)]">{row.sourceReference}</span>}
          </div>
        ),
      },
      { key: "partner_name", label: "Policyholder / Partner", render: (_value, row) => row.partnerName || "—" },
      {
        key: "product_plan",
        label: "Product / Plan",
        render: (_value, row) => {
          if (row.productName && row.planName) return `${row.productName} / ${row.planName}`
          return row.productName || row.planName || "—"
        },
      },
      {
        key: "installment",
        label: "Installment",
        align: "center",
        render: (_value, row) => (
          <span className="tabular-nums">
            {row.installmentNumber} of {row.installmentCount}
          </span>
        ),
      },
      { key: "due_date", label: "Due date", field: "dueDate", sortable: true, render: (value) => dateLabel(value as string | null) },
      { key: "premium_amount", label: "Amount due", field: "premiumAmount", align: "right", render: (_value, row) => formatMoney(row.premiumAmount, row.currency) },
      { key: "amount_paid", label: "Paid", field: "amountPaid", align: "right", render: (_value, row) => formatMoney(row.amountPaid, row.currency) },
      {
        key: "balance",
        label: "Balance",
        field: "balance",
        align: "right",
        render: (_value, row) => (
          <span className={Number(row.balance) > 0 ? "font-semibold text-[var(--destructive)]" : ""}>{formatMoney(row.balance, row.currency)}</span>
        ),
      },
      { key: "currency", label: "Currency", field: "currency", align: "center" },
      { key: "state", label: "Status", field: "status", sortable: true, render: (_value, row) => <CommitmentStatusBadge value={row.status} config={optionsQuery.data?.statuses} /> },
      { key: "grace_date", label: "Grace / lapse", render: (_value, row) => <DueDateWarning dueDate={row.dueDate} graceDate={row.graceDate} lapseDate={row.lapseDate} /> },
    ],
    [navigate, optionsQuery.data?.statuses],
  )

  const stats = useMemo(
    () => [
      { label: "Total Due", value: kpisQuery.data ? formatMoney(kpisQuery.data.totalDue) : "—", helper: "Sum of scheduled premium" },
      { label: "Outstanding", value: kpisQuery.data ? formatMoney(kpisQuery.data.totalOutstanding) : "—", helper: "Unpaid balance across commitments" },
      { label: "Overdue Count", value: kpisQuery.data ? kpisQuery.data.overdueCount.toLocaleString() : "—", helper: "Past the grace date" },
      { label: "Collected in Period", value: kpisQuery.data ? formatMoney(kpisQuery.data.collectedInPeriod) : "—", helper: "Allocated in the current period" },
    ],
    [kpisQuery.data],
  )

  const empty = !listError && !importErrors.length && Boolean(kpisQuery.data) && Number(kpisQuery.data?.totalDue ?? 0) === 0 && Number(kpisQuery.data?.totalOutstanding ?? 0) === 0

  return (
    <div className="space-y-5 p-4 md:p-6">
      <MasterDetailPage
        eyebrow="Ordinary Life"
        title="Ordinary Life Commitments"
        description="Track proposal first premiums and policy renewal schedules. Row actions follow allowed-actions from the service and your permissions."
        stats={stats}
        actions={
          <>
            <button type="button" className="button-secondary" disabled={importing} onClick={() => navigate("/ordinary-life/commitments/generate")} title="Run parameter-driven commitment generation">
              <Workflow size={16} aria-hidden="true" />
              Generate Commitments
            </button>
            <button type="button" className="button-primary" disabled={!hasPermission("ol_commitments.create")} onClick={() => navigate("/ordinary-life/commitments/new")}>
              <FilePlus2 size={16} aria-hidden="true" />
              Create New Commitment
            </button>
          </>
        }
      >
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Commitment quick filters">
            {CHIPS.map((chipItem) => (
              <button
                key={chipItem.key}
                type="button"
                onClick={() => applyChip(chipItem.key)}
                aria-pressed={chip === chipItem.key}
                className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${chip === chipItem.key ? "border-[var(--primary)] bg-[var(--primary)]/10 text-[var(--primary)]" : "border-[var(--border)] text-[var(--muted-foreground)] hover:text-[var(--foreground)]"}`}
              >
                {chipItem.label}
              </button>
            ))}
            {chip && (
              <button type="button" className="text-xs underline-offset-2 hover:underline" onClick={() => applyChip(chip)}>
                Clear chip
              </button>
            )}
          </div>
          <FilterBar
            definitions={filterDefinitions}
            value={filters}
            onChange={(key, value) => setFilters((current) => ({ ...current, [key]: value }))}
            onReset={() => {
              setFilters({})
              setChip(null)
            }}
          />
          {listError ? <ErrorCoach error={listError} onRetry={() => setRefreshKey((value) => value + 1)} title="Commitments could not be loaded" /> : null}
          {importErrors.length > 0 && (
            <InfoBanner title={`${importErrors.length} CSV row(s) rejected`}>
              <ul className="mt-1 list-disc pl-5 text-xs">
                {importErrors.map((item) => (
                  <li key={`${item.row}-${item.message}`}>
                    Row {item.row}: {item.message}
                  </li>
                ))}
              </ul>
            </InfoBanner>
          )}
          {empty && (
            <InfoBanner title="No commitments yet">
              <p className="text-sm">
                Commitments appear here when a proposal reaches payment-ready or a policy issues its first premium. Adjust the filters or create one manually.
              </p>
            </InfoBanner>
          )}
          <DataTable<CommitmentListRow>
            metadata={{ columns, defaultOrdering: "-dueDate", pageSize: 20, totalLabel: "Commitments" }}
            fetcher={fetcher}
            filters={filters}
            refreshKey={refreshKey}
            actions={actions}
            permissions={[]}
            canAction={canAction}
            onImportCsv={onImportCsv}
            exportFileName="ol-commitments.csv"
            caption="Ordinary Life commitments register"
          />
        </div>
      </MasterDetailPage>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Minimal CSV parser (RFC-4180-lite) shared by the import flow
// ---------------------------------------------------------------------------

function parseCsvLine(line: string): string[] {
  const result: string[] = []
  let current = ""
  let quoted = false
  for (let index = 0; index < line.length; index += 1) {
    const character = line[index]
    if (character === '"' && line[index + 1] === '"' && quoted) {
      current += '"'
      index += 1
    } else if (character === '"') {
      quoted = !quoted
    } else if (character === "," && !quoted) {
      result.push(current.trim())
      current = ""
    } else {
      current += character
    }
  }
  result.push(current.trim())
  return result
}

export function parseCsv(text: string): Array<Record<string, string>> {
  const lines = text.split(/\r?\n/).filter((line) => line.trim())
  if (lines.length < 2) return []
  const headers = parseCsvLine(lines[0]).map((header) => header.toLowerCase())
  return lines.slice(1).map((line) => Object.fromEntries(parseCsvLine(line).map((value, index) => [headers[index], value])))
}
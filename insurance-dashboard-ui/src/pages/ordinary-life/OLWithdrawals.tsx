import { useCallback, useMemo, useState } from "react"
import { FilePlus2, Search } from "lucide-react"
import { ErrorCoach } from "../../components/ErrorCoach"
import Modal from "../../components/shared/Modal"
import { DataTable } from "../../components/ui/DataTable"
import { FilterBar, type FilterValues } from "../../components/ui/FilterBar"
import { MasterDetailPage } from "../../components/ui/Patterns"
import { useNavigate } from "react-router-dom"
import type { RowAction, TableColumn, TableMetadata } from "../../components/ui/types"
import { useAccess } from "../../lib/access"
import { formatMoney } from "../../lib/commitmentsDisplay"
import {
  useWithdrawalKpis,
  useWithdrawalOptions,
} from "../../lib/withdrawalsHooks"
import { listWithdrawals, type WithdrawalAction, type WithdrawalListFilters, type WithdrawalOption, type WithdrawalRecord } from "../../lib/withdrawals"
import { MoneyCell, WithdrawalStatusBadge } from "../../components/withdrawals/WithdrawalPrimitives"
import { useToast } from "../../components/ui/Toast"

const STATUS_OPTIONS = [
  { value: "REQUESTED", label: "Requested" },
  { value: "APPROVED", label: "Approved" },
  { value: "PROCESSING", label: "Processing" },
  { value: "PAID", label: "Paid" },
  { value: "REVERSED", label: "Reversed" },
  { value: "DECLINED", label: "Declined" },
  { value: "CANCELLED", label: "Cancelled" },
]

const FILTER_DEFINITIONS = [
  { key: "status", label: "Status", type: "select" as const, options: STATUS_OPTIONS, placeholder: "All statuses" },
  { key: "product", label: "Product", type: "select" as const, placeholder: "All products" },
  { key: "branch", label: "Branch", type: "select" as const, placeholder: "All branches" },
  { key: "agent", label: "Agent", type: "select" as const, placeholder: "All agents" },
  { key: "date_range", label: "Requested date", type: "date-range" as const },
  { key: "pending_approval_only", label: "Pending approval only", type: "select" as const, options: [{ value: "true", label: "Pending only" }], placeholder: "All withdrawals" },
]

type ListQuery = { page?: number; pageSize?: number; search?: string; ordering?: string; filters?: Record<string, unknown> }
type ActionKey = "view" | "approve" | "reject" | "print"
type ActionTarget = { action: ActionKey; row: WithdrawalRecord } | null

function textValue(value: unknown): string {
  return value === null || value === undefined ? "" : String(value)
}

function dateLabel(value?: string | null): string {
  if (!value) return "—"
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? value : new Intl.DateTimeFormat("en-GB", { dateStyle: "medium" }).format(parsed)
}

function numberLabel(value: number | undefined): string {
  return value === undefined ? "…" : new Intl.NumberFormat("en-US").format(value)
}

function queryValue(value: unknown): string {
  if (typeof value === "string") return value
  if (Array.isArray(value)) return value.join(",")
  return value === undefined || value === null ? "" : String(value)
}

function optionValues(options: WithdrawalOption[]): { value: string; label: string }[] {
  return options.map((option) => ({ value: option.value, label: option.label }))
}

function tableFilters(query: ListQuery): WithdrawalListFilters {
  const filters = query.filters ?? {}
  const range = queryValue(filters.date_range).split(",")
  return {
    page: query.page,
    pageSize: query.pageSize,
    search: query.search,
    ordering: query.ordering,
    status: queryValue(filters.status) || undefined,
    product: queryValue(filters.product) || undefined,
    branch: queryValue(filters.branch) || undefined,
    agent: queryValue(filters.agent) || undefined,
    dateFrom: range[0] || undefined,
    dateTo: range[1] || undefined,
    pendingApprovalOnly: queryValue(filters.pending_approval_only).toLowerCase() === "true" || undefined,
  }
}

function humanActionLabel(action: string): string {
  return action.replace(/[_-]+/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function readActionError(error: unknown): string {
  return error instanceof Error ? error.message : "The withdrawal request could not be submitted."
}

function kpiMoney(value: string | undefined, currency: string | undefined) {
  return value === undefined ? "…" : <MoneyCell value={value} currency={currency || "TZS"} />
}

function WithdrawalPolicySearchModal({ open, onClose, onSelected }: { open: boolean; onClose: () => void; onSelected: (option: WithdrawalOption) => void }) {
  const [search, setSearch] = useState("")
  const params = useMemo(() => ({ q: search, page: 1, pageSize: 10 }), [search])
  const policyQuery = useWithdrawalOptions("policies", params, open)
  const options = policyQuery.data?.results ?? []
  return (
    <Modal open={open} title="Request Withdrawal" onClose={onClose}>
      <div className="space-y-4">
        <div><h3 className="text-base font-bold">Select an eligible policy</h3><p className="mt-1 text-sm leading-6 text-[var(--muted-foreground)]">Search active policies to review the available cash value before starting the withdrawal request.</p></div>
        <label className="block space-y-1.5"><span className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Search policies</span><span className="relative block"><Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)]" aria-hidden="true" /><input autoFocus value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Policy number or policyholder" className="h-10 w-full rounded-[10px] border bg-[var(--card)] pl-9 pr-3 text-sm outline-none focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)]" /></span></label>
        {policyQuery.error && <ErrorCoach title="Policies could not be loaded" message={policyQuery.error.message} resolutionSteps={["Confirm that the policy service is available.", "Search again or ask servicing support to verify withdrawal eligibility."]} />}
        <div className="max-h-72 space-y-2 overflow-y-auto" aria-live="polite">
          {policyQuery.isLoading && <div className="rounded-lg border border-dashed px-4 py-8 text-center text-sm text-[var(--muted-foreground)]">Loading eligible policies…</div>}
          {!policyQuery.isLoading && !policyQuery.error && options.length === 0 && <div className="rounded-lg border border-dashed px-4 py-8 text-center text-sm text-[var(--muted-foreground)]">No eligible policies match this search.</div>}
          {options.map((option) => <button key={option.value} type="button" onClick={() => onSelected(option)} className="flex w-full items-start justify-between gap-3 rounded-lg border bg-[var(--card)] px-3 py-3 text-left transition hover:border-[var(--primary)] hover:bg-[var(--secondary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"><span className="min-w-0"><span className="block truncate text-sm font-bold">{option.label}</span><span className="mt-1 block text-xs text-[var(--muted-foreground)]">Available limit: <MoneyCell value={option.meta?.available_limit as string | number | undefined} currency={String(option.meta?.currency ?? "TZS")} /></span></span><span className="shrink-0 rounded-full bg-emerald-100 px-2 py-1 text-[11px] font-bold text-emerald-700">{String(option.meta?.status ?? "Eligible")}</span></button>)}
        </div>
        <div className="flex justify-end border-t pt-4"><button type="button" className="button-secondary" onClick={onClose}>Cancel</button></div>
      </div>
    </Modal>
  )
}

export default function OLWithdrawals() {
  const { access, canAccess, hasPermission, isSuperAdmin } = useAccess()
  const navigate = useNavigate()
  const { toast } = useToast()
  const [filters, setFilters] = useState<FilterValues>({})
  const [refreshKey, setRefreshKey] = useState(0)
  const [requestOpen, setRequestOpen] = useState(false)
  const [actionTarget, setActionTarget] = useState<ActionTarget>(null)
  const productQuery = useWithdrawalOptions("products")
  const branchQuery = useWithdrawalOptions("branches")
  const agentQuery = useWithdrawalOptions("agents")

  const can = useCallback((permission: string) => {
    if (isSuperAdmin) return true
    const normalized = permission.toLowerCase()
    const permissionKeys = access.permissions.map((item) => `${item.module}.${item.action}`.toLowerCase())
    return Boolean(hasPermission?.(permission) || permissionKeys.includes(normalized) || (permission.endsWith(".view") && canAccess("ol_withdrawals")))
  }, [access.permissions, canAccess, hasPermission, isSuperAdmin])

  const kpiFilters = useMemo<WithdrawalListFilters>(() => {
    const range = filters.date_range && typeof filters.date_range === "object" && !Array.isArray(filters.date_range) ? filters.date_range : {}
    return {
      status: textValue(filters.status) || undefined,
      product: textValue(filters.product) || undefined,
      branch: textValue(filters.branch) || undefined,
      agent: textValue(filters.agent) || undefined,
      dateFrom: range.from,
      dateTo: range.to,
      pendingApprovalOnly: textValue(filters.pending_approval_only).toLowerCase() === "true" || undefined,
    }
  }, [filters])
  const kpiQuery = useWithdrawalKpis(kpiFilters, can("ol_withdrawals.view"))

  const fetcher = useCallback(async (query: ListQuery) => {
    const result = await listWithdrawals(tableFilters(query))
    return { results: result.results, count: result.count, next: typeof result.next === "string" ? result.next : null, previous: typeof result.previous === "string" ? result.previous : null, page: result.page, page_size: result.pageSize }
  }, [])

  const actions: RowAction<WithdrawalRecord>[] = useMemo(() => [
    { key: "view", label: "View", onSelect: (row) => setActionTarget({ action: "view", row }) },
    { key: "approve", label: "Approve", isVisible: (row) => row.status.toUpperCase() === "REQUESTED", onSelect: (row) => setActionTarget({ action: "approve", row }) },
    { key: "reject", label: "Reject", tone: "danger", isVisible: (row) => row.status.toUpperCase() === "REQUESTED", onSelect: (row) => setActionTarget({ action: "reject", row }) },
    { key: "print", label: "Print", onSelect: (row) => setActionTarget({ action: "print", row }) },
  ], [])

  const canAction = useCallback((action: RowAction<WithdrawalRecord>, row: WithdrawalRecord) => {
    const actionKey = action.key as ActionKey
    const allowed = new Set((row.allowedActions ?? []).map((item) => item.toLowerCase().replace(/-/g, "_")))
    if (actionKey !== "view" && !allowed.has(actionKey)) return false
    const permissions: Record<ActionKey, string> = { view: "ol_withdrawals.view", approve: "ol_withdrawals.approve", reject: "ol_withdrawals.approve", print: "ol_withdrawals.print" }
    return can(permissions[actionKey])
  }, [can])

  const columns: TableColumn<WithdrawalRecord>[] = useMemo(() => [
    { key: "withdrawal_number", label: "Withdrawal number", field: "withdrawalNumber", sortable: true, render: (_value, row) => <span className="font-bold">{row.withdrawalNumber || "—"}</span> },
    { key: "policy_number", label: "Policy number", field: "policyNumber", sortable: true, render: (_value, row) => <button type="button" className="font-semibold text-[var(--primary)] underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]" onClick={() => setActionTarget({ action: "view", row })}>{row.policyNumber || row.policyDisplay || "—"}</button> },
    { key: "policyholder_name", label: "Policyholder", field: "policyholderName", sortable: true, render: (_value, row) => <div><span className="font-semibold">{row.policyholderName || "—"}</span><span className="mt-1 block text-xs text-[var(--muted-foreground)]">{row.policyholderDisplay && row.policyholderDisplay !== row.policyholderName ? row.policyholderDisplay : ""}</span></div> },
    { key: "product", label: "Product", field: "productDisplay", sortable: true, render: (_value, row) => row.productDisplay || "—" },
    { key: "gross_amount", label: "Gross amount", field: "grossAmount", sortable: true, align: "right", render: (_value, row) => <MoneyCell value={row.grossAmount} currency={row.currency} /> },
    { key: "fee_amount", label: "Fee amount", field: "feeAmount", sortable: true, align: "right", render: (_value, row) => <MoneyCell value={row.feeAmount} currency={row.currency} /> },
    { key: "net_payout", label: "Net payout", field: "netPayout", sortable: true, align: "right", render: (_value, row) => <MoneyCell value={row.netPayout} currency={row.currency} /> },
    { key: "state", label: "Status", field: "status", sortable: true, render: (_value, row) => <WithdrawalStatusBadge status={row.status} statusDisplay={row.statusDisplay} /> },
    { key: "requested_at", label: "Requested date", field: "requestedAt", sortable: true, render: (value) => dateLabel(value as string | null) },
    { key: "allowed_actions", label: "Allowed actions", field: "allowedActions", render: (_value, row) => row.allowedActions.length ? <span className="text-xs text-[var(--muted-foreground)]">{row.allowedActions.map(humanActionLabel).join(", ")}</span> : "—" },
  ], [])

  const stats = [
    { label: "Total withdrawn · current month", value: kpiMoney(kpiQuery.data?.totalWithdrawnCurrentMonth, kpiQuery.data?.currency), helper: `Currency: ${kpiQuery.data?.currency || "TZS"}` },
    { label: "Pending approvals", value: numberLabel(kpiQuery.data?.pendingApprovalsCount), helper: kpiQuery.data ? `${formatMoney(kpiQuery.data.pendingApprovalsAmount, kpiQuery.data.currency)} awaiting review` : "Count and amount from backend" },
    { label: "Processing payouts", value: numberLabel(kpiQuery.data?.processingPayoutsCount), helper: "Payouts awaiting completion" },
    { label: "Average fee amount", value: kpiMoney(kpiQuery.data?.averageFeeAmount, kpiQuery.data?.currency), helper: kpiQuery.data?.timestamp ? `Updated ${dateLabel(kpiQuery.data.timestamp)}` : "Backend KPI timestamp" },
  ]

  const productDefinitions = useMemo(() => FILTER_DEFINITIONS.map((definition) => definition.key === "product" ? { ...definition, options: optionValues(productQuery.data?.results ?? []) } : definition.key === "branch" ? { ...definition, options: optionValues(branchQuery.data?.results ?? []) } : definition.key === "agent" ? { ...definition, options: optionValues(agentQuery.data?.results ?? []) } : definition), [agentQuery.data?.results, branchQuery.data?.results, productQuery.data?.results])

  const handlePolicySelected = (option: WithdrawalOption) => {
    setRequestOpen(false)
    toast({ tone: "info", title: "Policy selected", message: `${option.label} is ready for the withdrawal request wizard.` })
    navigate(`/ordinary-life/withdrawals/new?policy_id=${encodeURIComponent(option.value)}`)
  }

  const actionLabel: Record<ActionKey, string> = { view: "View", approve: "Approve", reject: "Reject", print: "Print" }
  const target = actionTarget

  return (
    <div className="space-y-5 p-1 md:p-2">
      <MasterDetailPage eyebrow="Ordinary Life / Servicing" title="Withdrawals" description="Review policy withdrawals, available actions, and payout values. Search and filters are applied server-side; the backend action matrix remains the source of truth." stats={stats} actions={<button type="button" className="button-primary inline-flex items-center gap-2" onClick={() => setRequestOpen(true)} disabled={!can("ol_withdrawals.request")}><FilePlus2 size={16} aria-hidden="true" />Request Withdrawal</button>}>
        {kpiQuery.error && <ErrorCoach title="Withdrawal KPIs need attention" message={kpiQuery.error.message} resolutionSteps={["Confirm the OL Withdrawals API is available.", "Review the selected filters and retry the page."]} />}
        <FilterBar definitions={productDefinitions} value={filters} onChange={(key, value) => setFilters((current) => ({ ...current, [key]: value }))} onApply={() => setRefreshKey((value) => value + 1)} onReset={() => { setFilters({}); setRefreshKey((value) => value + 1) }} />
        <DataTable<WithdrawalRecord> metadata={{ columns, defaultOrdering: "-requested_at", pageSize: 20, totalLabel: "Withdrawals" } satisfies TableMetadata<WithdrawalRecord>} fetcher={fetcher} filters={filters} refreshKey={refreshKey} actions={actions} canAction={canAction} hideSearch errorContent={<ErrorCoach title="Withdrawals could not be loaded" message="The Withdrawals register did not return a response." resolutionSteps={["Confirm the backend is running and your session has ol_withdrawals.view.", "Retry the table. If the problem continues, provide the correlation ID from the failed request to support."]} />} exportFileName="ol-withdrawals.csv" caption="Ordinary Life withdrawals work queue" />
      </MasterDetailPage>
      <WithdrawalPolicySearchModal open={requestOpen} onClose={() => setRequestOpen(false)} onSelected={handlePolicySelected} />
      <Modal open={Boolean(target)} title={`${target ? actionLabel[target.action] : "Withdrawal"} withdrawal`} onClose={() => setActionTarget(null)}>
        {target && <div className="space-y-4"><div className="rounded-lg border bg-[var(--muted)]/35 p-4"><p className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Selected record</p><p className="mt-1 text-sm font-bold">{target.row.withdrawalNumber}</p><p className="mt-1 text-xs text-[var(--muted-foreground)]">{target.row.policyholderName} · {target.row.policyNumber}</p><div className="mt-3 flex flex-wrap items-center gap-3 text-sm"><WithdrawalStatusBadge status={target.row.status} statusDisplay={target.row.statusDisplay} /><MoneyCell value={target.row.netPayout} currency={target.row.currency} label="Net payout" /></div></div><p className="text-sm leading-6 text-[var(--muted-foreground)]">{target.action === "view" ? "Open the withdrawal detail workspace to review breakdown, payments, documents, and audit history." : target.action === "print" ? "Open the detail workspace to generate the authenticated withdrawal statement." : `The ${actionLabel[target.action].toLowerCase()} confirmation form will verify permissions and require the appropriate controlled reason.`}</p><div className="flex justify-end gap-2 border-t pt-4"><button type="button" className="button-secondary" onClick={() => setActionTarget(null)}>Cancel</button><button type="button" className="button-primary" onClick={() => { const id = target.row.id; const action = target.action as WithdrawalAction; setActionTarget(null); navigate(`/ordinary-life/withdrawals/${id}?action=${encodeURIComponent(action)}`) }}>Open detail</button></div></div>}
      </Modal>
    </div>
  )
}

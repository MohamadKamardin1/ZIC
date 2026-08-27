import { useCallback, useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { FilePlus2, Search, ShieldCheck } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { ErrorCoach } from "../../components/ErrorCoach"
import Modal from "../../components/shared/Modal"
import { DataTable } from "../../components/ui/DataTable"
import { FilterBar, type FilterValues } from "../../components/ui/FilterBar"
import { MasterDetailPage } from "../../components/ui/Patterns"
import type { RowAction, TableColumn, TableMetadata } from "../../components/ui/types"
import { LoanStatusBadge, MoneyCell, ProgressCell } from "../../components/loans/LoanPrimitives"
import { useAccess } from "../../lib/access"
import { listPolicies, type PolicyListItem } from "../../lib/policies"
import { buildLoanQuery, listLoans, type LoanListFilters, type LoanRecord } from "../../lib/loans"
import { useLoanKpis } from "../../lib/loansHooks"
import { useToast } from "../../components/ui/Toast"

const STATUS_OPTIONS = [
  { label: "Requested", value: "REQUESTED" },
  { label: "Approved", value: "APPROVED" },
  { label: "Disbursed", value: "DISBURSED" },
  { label: "Active", value: "ACTIVE" },
  { label: "Partially repaid", value: "PARTIALLY_REPAID" },
  { label: "Defaulted", value: "DEFAULTED" },
  { label: "Settled", value: "SETTLED" },
  { label: "Closed", value: "CLOSED" },
  { label: "Rejected", value: "REJECTED" },
]

const FILTER_DEFINITIONS = [
  { key: "status", label: "Status", type: "select" as const, options: STATUS_OPTIONS, placeholder: "All statuses" },
  { key: "date_range", label: "Disbursement date", type: "date-range" as const },
  { key: "defaulted_only", label: "Defaulted only", type: "select" as const, options: [{ value: "true", label: "Defaulted only" }], placeholder: "All loans" },
]

type ActionKey = "view" | "disburse" | "repay" | "offset" | "print"
type ActionTarget = { action: ActionKey; row: LoanRecord } | null

function textValue(value: unknown): string {
  return value === null || value === undefined || value === "" ? "" : String(value)
}

function dateLabel(value?: string | null): string {
  if (!value) return "—"
  const parsed = new Date(`${value.slice(0, 10)}T00:00:00`)
  return Number.isNaN(parsed.getTime()) ? value : new Intl.DateTimeFormat("en-GB", { dateStyle: "medium" }).format(parsed)
}

function numberLabel(value: number | undefined): string {
  return value === undefined ? "…" : new Intl.NumberFormat("en-US").format(value)
}

function kpiMoney(value: string | Record<string, string> | undefined, currency: string | undefined) {
  if (value === undefined) return "…"
  if (typeof value === "string") return <MoneyCell value={value} currency={currency || "TZS"} />
  return <span className="space-y-1">{Object.entries(value).map(([code, amount]) => <span key={code} className="block"><MoneyCell value={amount} currency={code} /></span>)}</span>
}

function queryString(value: unknown): string {
  if (typeof value === "string") return value
  if (Array.isArray(value)) return value.join(",")
  return value === undefined || value === null ? "" : String(value)
}

function tableFilters(query: { page?: number; pageSize?: number; search?: string; ordering?: string; filters?: Record<string, unknown> }): LoanListFilters {
  const filters = query.filters ?? {}
  const range = queryString(filters.date_range).split(",")
  const defaultedOnly = queryString(filters.defaulted_only).toLowerCase() === "true"
  return {
    page: query.page,
    pageSize: query.pageSize,
    search: query.search,
    ordering: query.ordering,
    status: defaultedOnly ? "DEFAULTED" : queryString(filters.status) || undefined,
    product: queryString(filters.product) || undefined,
    branch: queryString(filters.branch) || undefined,
    dateFrom: range[0] || undefined,
    dateTo: range[1] || undefined,
    overdueOnly: defaultedOnly,
  }
}

function PolicySearchModal({ open, onClose, onSelect }: { open: boolean; onClose: () => void; onSelect: (policy: PolicyListItem) => void }) {
  const [search, setSearch] = useState("")
  const policyQuery = useQuery({
    queryKey: ["ol-loans", "request-policy-search", search],
    queryFn: () => listPolicies({ search, status: "ACTIVE", page: 1, pageSize: 10 }),
    enabled: open,
    staleTime: 30_000,
  })
  const policies = policyQuery.data?.results ?? []

  return <Modal open={open} title="Request Loan · Select policy" onClose={onClose}>
    <div className="space-y-4">
      <p className="text-sm leading-6 text-[var(--muted-foreground)]">Search active policies that can be reviewed for an OL Loan request. Final eligibility and available limit are always validated by the backend before submission.</p>
      <label className="block space-y-1.5"><span className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Search active policies</span><span className="relative block"><Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)]" aria-hidden="true" /><input autoFocus value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Policy number, policyholder, or product" className="h-10 w-full rounded-[10px] border border-[var(--border)] bg-[var(--card)] pl-9 pr-3 text-sm outline-none focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)]" /></span></label>
      {policyQuery.error && <ErrorCoach title="Eligible policies could not be loaded" message={policyQuery.error.message} resolutionSteps={["Confirm that the policy service is available.", "Search again or ask a servicing administrator to verify the policy status."]} />}
      <div className="max-h-72 space-y-2 overflow-y-auto" aria-live="polite">{policyQuery.isLoading && <div className="rounded-lg border border-dashed border-[var(--border)] px-4 py-8 text-center text-sm text-[var(--muted-foreground)]">Loading eligible policies…</div>}{!policyQuery.isLoading && !policyQuery.error && policies.length === 0 && <div className="rounded-lg border border-dashed border-[var(--border)] px-4 py-8 text-center text-sm text-[var(--muted-foreground)]">No active eligible policies match this search.</div>}{policies.map((policy) => <button key={policy.id} type="button" onClick={() => onSelect(policy)} className="flex w-full items-start justify-between gap-3 rounded-lg border border-[var(--border)] bg-[var(--card)] px-3 py-3 text-left transition hover:border-[var(--primary)] hover:bg-[var(--secondary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"><span className="min-w-0"><span className="block truncate text-sm font-bold">{policy.policyNumber}</span><span className="mt-1 block truncate text-xs text-[var(--muted-foreground)]">{policy.policyholderDisplay || policy.policyholderName}</span><span className="mt-1 block truncate text-xs text-[var(--muted-foreground)]">{policy.productPlanDisplay}</span></span><span className="shrink-0 rounded-full bg-[var(--success)]/10 px-2 py-1 text-[11px] font-bold text-[var(--success)]">{policy.statusDisplay || "Active"}</span></button>)}</div>
      <div className="flex justify-end border-t border-[var(--border)] pt-4"><button type="button" className="button-secondary" onClick={onClose}>Cancel</button></div>
    </div>
  </Modal>
}

export default function OLLoans() {
  const navigate = useNavigate()
  const { access, hasPermission, isSuperAdmin } = useAccess()
  const { toast } = useToast()
  const [filters, setFilters] = useState<FilterValues>({})
  const [refreshKey, setRefreshKey] = useState(0)
  const [requestOpen, setRequestOpen] = useState(false)
  const [actionTarget, setActionTarget] = useState<ActionTarget>(null)

  const kpiFilters = useMemo<LoanListFilters>(() => {
    const dateRange = filters.date_range && typeof filters.date_range === "object" && !Array.isArray(filters.date_range) ? filters.date_range : {}
    const defaultedOnly = filters.defaulted_only === "true"
    return { status: defaultedOnly ? "DEFAULTED" : textValue(filters.status) || undefined, product: textValue(filters.product) || undefined, branch: textValue(filters.branch) || undefined, dateFrom: dateRange.from, dateTo: dateRange.to, overdueOnly: defaultedOnly }
  }, [filters])
  const kpiQuery = useLoanKpis(kpiFilters)

  const permissionCodes = useMemo(() => access.permissions.map((permission) => `${permission.module}.${permission.action}`.toLowerCase()), [access.permissions])
  const can = useCallback((permission: string) => isSuperAdmin || Boolean(hasPermission?.(permission) || permissionCodes.includes(permission.toLowerCase())), [hasPermission, isSuperAdmin, permissionCodes])

  const fetcher = useCallback(async (query: { page?: number; pageSize?: number; search?: string; ordering?: string; filters?: Record<string, unknown> }) => {
    const result = await listLoans(tableFilters(query))
    return { results: result.results, count: result.count, next: typeof result.next === "string" ? result.next : null, previous: typeof result.previous === "string" ? result.previous : null, page: result.page, page_size: result.pageSize }
  }, [])

  const actions: RowAction<LoanRecord>[] = useMemo(() => [
    { key: "view", label: "View", onSelect: (row) => navigate(`/ordinary-life/loans/${row.id}`) },
    { key: "disburse", label: "Disburse", onSelect: (row) => setActionTarget({ action: "disburse", row }) },
    { key: "repay", label: "Repay", onSelect: (row) => setActionTarget({ action: "repay", row }) },
    { key: "offset", label: "Offset", onSelect: (row) => setActionTarget({ action: "offset", row }) },
    { key: "print", label: "Print", onSelect: (row) => setActionTarget({ action: "print", row }) },
  ], [navigate])

  const canAction = useCallback((action: RowAction<LoanRecord>, row: LoanRecord) => {
    const actionKey = action.key as ActionKey
    const allowed = new Set((row.allowedActions ?? []).map((item) => item.toLowerCase()))
    if (!allowed.has(actionKey)) return false
    const permissions: Record<ActionKey, string> = { view: "ol_loans.view", disburse: "ol_loans.disburse", repay: "ol_loans.repay", offset: "ol_loans.offset", print: "ol_loans.print" }
    return can(permissions[actionKey])
  }, [can])

  const columns: TableColumn<LoanRecord>[] = useMemo(() => [
    { key: "loan_number", label: "Loan number", field: "loanNumber", sortable: true, render: (_value, row) => <span className="font-bold">{row.loanNumber || "—"}</span> },
    { key: "policy_number", label: "Policy number", field: "policyNumber", sortable: true, render: (_value, row) => <button type="button" className="font-semibold text-[var(--primary)] underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]" onClick={() => navigate(`/ordinary-life/policies/${row.policyNumber}`)}>{row.policyNumber || row.policyDisplay || "—"}</button> },
    { key: "policyholder_name", label: "Policyholder", field: "policyholderName", sortable: true, render: (_value, row) => <div><span className="font-semibold">{row.policyholderName || row.partnerDisplay || "—"}</span><span className="mt-1 block text-xs text-[var(--muted-foreground)]">{row.partnerDisplay && row.partnerDisplay !== row.policyholderName ? row.partnerDisplay : ""}</span></div> },
    { key: "product", label: "Product", field: "productDisplay", sortable: true, render: (_value, row) => row.productDisplay || "—" },
    { key: "principal_amount", label: "Principal amount", field: "principalAmount", sortable: true, align: "right", render: (_value, row) => <MoneyCell value={row.principalAmount} currency={row.currency} /> },
    { key: "outstanding_balance", label: "Outstanding balance", field: "outstandingBalance", sortable: true, align: "right", render: (_value, row) => <ProgressCell principal={row.principalAmount} balance={row.outstandingBalance} currency={row.currency} /> },
    { key: "interest_rate", label: "Interest rate", field: "interestRate", sortable: true, align: "right", render: (_value, row) => `${row.interestRate || "0.00"}%` },
    { key: "disbursement_date", label: "Disbursement date", field: "disbursementDate", sortable: true, render: (value) => dateLabel(value as string | null) },
    { key: "state", label: "Status", field: "status", sortable: true, render: (_value, row) => <LoanStatusBadge status={row.status} statusDisplay={row.statusDisplay} /> },
  ], [navigate])

  const onPolicySelect = (policy: PolicyListItem) => {
    setRequestOpen(false)
    toast({ tone: "info", title: "Policy selected", message: `${policy.policyNumber} is ready for the loan request details flow.` })
  }

  const activeAction = actionTarget ? actionTarget.action : "view"
  const actionLabel: Record<ActionKey, string> = { view: "View", disburse: "Disburse", repay: "Repay", offset: "Offset", print: "Print" }

  const stats = [
    { label: "Total loans outstanding", value: kpiMoney(kpiQuery.data?.totalOutstanding, kpiQuery.data?.currency), helper: kpiQuery.data?.currency === "MULTI" ? "Grouped by currency" : `Currency: ${kpiQuery.data?.currency || "TZS"}` },
    { label: "Active loans count", value: numberLabel(kpiQuery.data?.activeCount), helper: "Active or partially repaid" },
    { label: "Defaulted loans count", value: <span className="text-[var(--destructive)]">{numberLabel(kpiQuery.data?.defaultedCount)}</span>, helper: "Requires servicing review" },
    { label: "Loans disbursed this month", value: kpiMoney(kpiQuery.data?.totalDisbursedPeriod, kpiQuery.data?.currency), helper: "Backend KPI period" },
  ]

  return <div className="space-y-5 p-1 md:p-2">
    <MasterDetailPage eyebrow="Ordinary Life / Servicing" title="Policy loans" description="Review loan balances and controlled servicing actions. Search and filters are applied server-side; the backend action matrix remains the source of truth." stats={stats} actions={<button type="button" className="button-primary inline-flex items-center gap-2" onClick={() => setRequestOpen(true)} disabled={!can("ol_loans.request")}><FilePlus2 size={16} aria-hidden="true" />Request Loan</button>}>
      {kpiQuery.error && <ErrorCoach title="Loan KPIs need attention" message={kpiQuery.error.message} resolutionSteps={["Confirm the OL Loans API is available.", "Review the selected filters and retry the page."]} />}
      <div className="space-y-3">
        <div className="surface-card flex flex-wrap items-end gap-3 p-4" role="group" aria-label="Loan table filters">
          <div className="min-w-48 flex-1"><label className="mb-1.5 block text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]" htmlFor="loan-filter-product">Product</label><input id="loan-filter-product" value={textValue(filters.product)} onChange={(event) => setFilters((current) => ({ ...current, product: event.target.value }))} placeholder="Product code or name" className="h-10 w-full rounded-[10px] border bg-[var(--card)] px-3 text-sm outline-none focus:border-[var(--ring)]" /></div>
          <div className="min-w-48 flex-1"><label className="mb-1.5 block text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]" htmlFor="loan-filter-branch">Branch</label><input id="loan-filter-branch" value={textValue(filters.branch)} onChange={(event) => setFilters((current) => ({ ...current, branch: event.target.value }))} placeholder="Branch code or name" className="h-10 w-full rounded-[10px] border bg-[var(--card)] px-3 text-sm outline-none focus:border-[var(--ring)]" /></div>
        </div>
        <FilterBar definitions={FILTER_DEFINITIONS} value={filters} onChange={(key, value) => setFilters((current) => ({ ...current, [key]: value }))} onApply={() => setRefreshKey((value) => value + 1)} onReset={() => { setFilters({}); setRefreshKey((value) => value + 1) }} />
      </div>
      <DataTable<LoanRecord> metadata={{ columns, defaultOrdering: "-created_at", pageSize: 20, totalLabel: "Loans" } satisfies TableMetadata<LoanRecord>} fetcher={fetcher} filters={filters} refreshKey={refreshKey} actions={actions} canAction={canAction} hideSearch errorContent={<ErrorCoach title="Loans could not be loaded" message="The Loans register did not return a response." resolutionSteps={["Confirm the backend is running and your session has `ol_loans.view`.", "Retry the table. If it continues, provide the correlation ID from the failed request to support."]} />} exportFileName="ol-loans.csv" caption="Ordinary Life loans work queue" />
    </MasterDetailPage>
    <PolicySearchModal open={requestOpen} onClose={() => setRequestOpen(false)} onSelect={onPolicySelect} />
    <Modal open={Boolean(actionTarget)} title={`${actionLabel[activeAction]} loan`} onClose={() => setActionTarget(null)}>
      {actionTarget && <div className="space-y-4"><div className="rounded-lg border border-[var(--border)] bg-[var(--muted)]/35 p-4"><p className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Selected record</p><p className="mt-1 text-sm font-bold">{actionTarget.row.loanNumber}</p><p className="mt-1 text-xs text-[var(--muted-foreground)]">{actionTarget.row.policyholderName} · {actionTarget.row.productDisplay}</p><div className="mt-3 flex flex-wrap items-center gap-3 text-sm"><LoanStatusBadge status={actionTarget.row.status} statusDisplay={actionTarget.row.statusDisplay} /><MoneyCell value={actionTarget.row.outstandingBalance} currency={actionTarget.row.currency} label="Outstanding balance" /></div></div><p className="text-sm leading-6 text-[var(--muted-foreground)]">This action is allowed by the current backend status matrix. Open the loan detail workspace to complete the controlled form and confirmation step.</p><div className="flex justify-end gap-2 border-t border-[var(--border)] pt-4"><button type="button" className="button-secondary" onClick={() => setActionTarget(null)}>Cancel</button><button type="button" className="button-primary" onClick={() => { const id = actionTarget.row.id; const action = actionTarget.action; setActionTarget(null); navigate(`/ordinary-life/loans/${id}?action=${action}`) }}>Open loan detail</button></div></div>}
    </Modal>
  </div>
}

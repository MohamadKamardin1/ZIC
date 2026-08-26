import { useCallback, useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import { CalendarDays, FilePlus2, ShieldCheck, TrendingDown, TrendingUp, WalletCards } from "lucide-react"
import { DataTable, type TableFetcher } from "../../components/ui/DataTable"
import { FilterBar, type FilterValues } from "../../components/ui/FilterBar"
import { ErrorCoach } from "../../components/commitments/ErrorCoach"
import { KPIStat } from "../../components/ui/Patterns"
import { PolicyStatusBadge, MoneyCell } from "../../components/policies"
import type { FilterDefinition, RowAction, TableColumn } from "../../components/ui/types"
import { useAccess } from "../../lib/access"
import { formatMoney, dateLabel } from "../../lib/commitmentsDisplay"
import type { TableQuery } from "../../lib/apiClient"
import {
  listPolicies,
  type PolicyListItem,
  type PolicyListParams,
  type PolicyOption,
} from "../../lib/policies"
import { usePolicyKpis, usePolicyOptions } from "../../lib/policiesHooks"

export type PolicyListRow = PolicyListItem & Record<string, unknown>

const ACTION_PERMISSION: Record<string, string> = {
  view: "ol_policies.view",
  endorse: "ol_policies.endorse",
  print: "ol_policies.print",
  cancel: "ol_policies.cancel",
}

function normalizedActions(row: Pick<PolicyListRow, "allowedActions">): string[] {
  return (row.allowedActions ?? []).map((action) => String(action).toLowerCase())
}

/** Actions require both the backend lifecycle allowance and the operator permission. */
export function policyRowActionEnabled(
  key: string,
  row: Pick<PolicyListRow, "allowedActions">,
  isSuperAdmin: boolean,
  hasPermission: (code: string) => boolean,
): boolean {
  const permission = ACTION_PERMISSION[key] ?? "ol_policies.view"
  if (!isSuperAdmin && !hasPermission(permission)) return false
  if (key === "view") return true
  const allowed = normalizedActions(row)
  return allowed.length > 0 && allowed.includes(key.toLowerCase())
}

function optionDefinitions(options: {
  statuses: PolicyOption[]
  products: PolicyOption[]
  agents: PolicyOption[]
  branches: PolicyOption[]
}): FilterDefinition[] {
  return [
    { key: "status", label: "Status", type: "select", placeholder: "All statuses", options: options.statuses.map(({ value, label }) => ({ value, label })) },
    { key: "product", label: "Product / plan", type: "select", placeholder: "All products", options: options.products.map(({ value, label }) => ({ value, label })) },
    { key: "branch", label: "Branch", type: "select", placeholder: "All branches", options: options.branches.map(({ value, label }) => ({ value, label })) },
    { key: "agent", label: "Agent", type: "select", placeholder: "All agents", options: options.agents.map(({ value, label }) => ({ value, label })) },
    { key: "commencement_range", label: "Commencement date", type: "date-range" },
    { key: "maturity_range", label: "Maturity date", type: "date-range" },
  ]
}

function stringFilter(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value : undefined
}

function rangeFilter(value: unknown): { from?: string; to?: string } {
  if (value && typeof value === "object" && !Array.isArray(value)) return value as { from?: string; to?: string }
  return {}
}

function paramsFromTableQuery(query: TableQuery): PolicyListParams {
  const filters = query.filters ?? {}
  const commencement = rangeFilter(filters.commencement_range)
  const maturity = rangeFilter(filters.maturity_range)
  return {
    page: query.page,
    pageSize: query.pageSize,
    search: query.search,
    ordering: query.ordering,
    status: stringFilter(filters.status),
    product: stringFilter(filters.product),
    branch: stringFilter(filters.branch),
    agent: stringFilter(filters.agent),
    commencementFrom: commencement.from,
    commencementTo: commencement.to,
    maturityFrom: maturity.from,
    maturityTo: maturity.to,
  }
}

function kpiParams(filters: FilterValues): Record<string, string> {
  const params: Record<string, string> = {}
  const assign = (key: string, value: unknown) => {
    const string = stringFilter(value)
    if (string) params[key] = string
  }
  assign("status", filters.status)
  assign("product", filters.product)
  assign("branch", filters.branch)
  assign("agent", filters.agent)
  const commencement = rangeFilter(filters.commencement_range)
  const maturity = rangeFilter(filters.maturity_range)
  assign("commencement_from", commencement.from)
  assign("commencement_to", commencement.to)
  assign("maturity_from", maturity.from)
  assign("maturity_to", maturity.to)
  return params
}

function MultiCurrencyMoney({ value, currency, byCurrency }: { value: string; currency: string; byCurrency: Record<string, string> }) {
  if (currency !== "MULTI") return <MoneyCell value={value} currency={currency} />
  return <span className="tabular-nums">{Object.entries(byCurrency).map(([code, amount]) => formatMoney(amount, code)).join(" · ") || "—"}</span>
}

function KpiSkeleton({ label }: { label: string }) {
  return <article className="surface-card animate-pulse p-4" aria-label={`${label} loading`}><div className="h-3 w-28 rounded bg-[var(--muted)]" /><div className="mt-3 h-8 w-24 rounded bg-[var(--muted)]" /><div className="mt-3 h-3 w-36 rounded bg-[var(--muted)]" /></article>
}

export default function OLPolicies() {
  const navigate = useNavigate()
  const { access, hasPermission, isSuperAdmin } = useAccess()
  const [filters, setFilters] = useState<FilterValues>({})
  const [listError, setListError] = useState<unknown>(null)

  const statuses = usePolicyOptions("statuses")
  const products = usePolicyOptions("products")
  const agents = usePolicyOptions("agents")
  const branches = usePolicyOptions("branches")
  const kpis = usePolicyKpis(kpiParams(filters))
  const filterDefinitions = useMemo(() => optionDefinitions({
    statuses: statuses.data ?? [],
    products: products.data ?? [],
    agents: agents.data ?? [],
    branches: branches.data ?? [],
  }), [agents.data, branches.data, products.data, statuses.data])

  const handleFilterChange = useCallback((key: string, value: FilterValues[string]) => {
    setFilters((current) => ({ ...current, [key]: value }))
  }, [])

  const handleReset = useCallback(() => setFilters({}), [])

  const fetcher = useCallback<TableFetcher<PolicyListRow>>(async (query) => {
    setListError(null)
    try {
      const result = await listPolicies(paramsFromTableQuery(query))
      return { results: result.results as PolicyListRow[], count: result.count, page: result.page, page_size: result.pageSize }
    } catch (error) {
      setListError(error)
      throw error
    }
  }, [])

  const permissionCodes = useMemo(() => {
    const codes = access.permissions.map((permission) => `${permission.module}.${permission.action}`)
    return isSuperAdmin ? Object.values(ACTION_PERMISSION) : codes
  }, [access.permissions, isSuperAdmin])

  const actions = useMemo<RowAction<PolicyListRow>[]>(() => [
    { key: "view", label: "View", permission: ACTION_PERMISSION.view, onSelect: (row) => navigate(`/ordinary-life/policies/${row.id}`) },
    { key: "endorse", label: "Endorse", permission: ACTION_PERMISSION.endorse, onSelect: (row) => navigate(`/ordinary-life/policies/${row.id}?tab=endorsements`) },
    { key: "print", label: "Print", permission: ACTION_PERMISSION.print, onSelect: (row) => navigate(`/ordinary-life/policies/${row.id}?action=print`) },
    { key: "cancel", label: "Cancel", permission: ACTION_PERMISSION.cancel, tone: "danger", onSelect: (row) => { if (window.confirm(`Cancel policy ${row.policyNumber}?`)) navigate(`/ordinary-life/policies/${row.id}?action=cancel`) } },
  ], [navigate])

  const columns = useMemo<TableColumn<PolicyListRow>[]>(() => [
    { key: "policy_number", field: "policyNumber", label: "Policy number", sortable: true, render: (value, row) => <button type="button" className="font-bold text-[var(--primary)] hover:underline" onClick={() => navigate(`/ordinary-life/policies/${row.id}`)}>{String(value ?? "—")}</button> },
    { key: "policyholder_name", field: "policyholderDisplay", label: "Policyholder", sortable: true },
    { key: "product_plan", field: "productPlanDisplay", label: "Product / plan", sortable: true },
    { key: "sum_assured", field: "sumAssured", label: "Sum assured", sortable: true, align: "right", render: (value, row) => <MoneyCell value={value as string | number | null} currency={row.currency} /> },
    { key: "premium", field: "premiumAmount", label: "Premium", sortable: true, align: "right", render: (value, row) => <MoneyCell value={value as string | number | null} currency={row.currency} /> },
    { key: "status", field: "status", label: "Status", sortable: true, render: (_value, row) => <PolicyStatusBadge status={row.status} /> },
    { key: "commencement_date", field: "riskCommencementDate", label: "Commencement", sortable: true, render: (value) => dateLabel(value as string | null | undefined) },
    { key: "maturity_date", field: "maturityDate", label: "Maturity", sortable: true, render: (value) => dateLabel(value as string | null | undefined) },
    { key: "agent_name", field: "agentDisplay", label: "Agent", sortable: true },
    { key: "allowed_actions", field: "allowedActions", label: "Lifecycle actions", render: (value) => <span className="text-xs text-[var(--muted-foreground)]">{Array.isArray(value) && value.length ? value.map(String).join(" · ") : "—"}</span> },
  ], [navigate])

  const canAction = useCallback((action: RowAction<PolicyListRow>, row: PolicyListRow) => policyRowActionEnabled(action.key, row, isSuperAdmin, (code) => hasPermission?.(code) ?? false), [hasPermission, isSuperAdmin])
  const hasKpiError = kpis.isError
  const kpiData = kpis.data

  return (
    <div className="space-y-5">
      <header className="section-header p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.15em] text-white/70">Ordinary Life</p>
            <h1 className="mt-2 text-2xl font-extrabold tracking-tight">Policies</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-white/80">Table-first policy servicing register for issued contracts, lifecycle status, and risk exposure.</p>
          </div>
          <button type="button" className="button-primary inline-flex items-center gap-2 bg-white text-[var(--primary)] hover:bg-white/90" onClick={() => navigate("/ordinary-life/policies/new")}><FilePlus2 size={16} aria-hidden="true" />New policy</button>
        </div>
      </header>

      {hasKpiError && <ErrorCoach error={kpis.error} onRetry={() => void kpis.refetch()} title="Policy KPIs could not be loaded" />}
      <section aria-label="Policy KPIs" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        {kpis.isPending && ["Total active policies", "Sum assured", "New policies", "Lapsed policies", "Maturing soon"].map((label) => <KpiSkeleton key={label} label={label} />)}
        {!kpis.isPending && kpiData && <>
          <KPIStat label="Total active policies" value={kpiData.totalActivePolicies.toLocaleString()} helper="Policies currently in force" tone="success" icon={<ShieldCheck size={18} aria-hidden="true" />} />
          <KPIStat label="Sum assured" value={<MultiCurrencyMoney value={kpiData.totalSumAssured} currency={kpiData.currency} byCurrency={kpiData.sumAssuredByCurrency} />} helper="Total risk exposure" icon={<WalletCards size={18} aria-hidden="true" />} />
          <KPIStat label="New policies" value={kpiData.newPoliciesThisMonth.toLocaleString()} helper="Current month" tone="info" icon={<TrendingUp size={18} aria-hidden="true" />} />
          <KPIStat label="Lapsed policies" value={kpiData.lapsedPoliciesCount.toLocaleString()} helper={`${formatMoney(kpiData.lapsedPoliciesValue, kpiData.currency === "MULTI" ? "TZS" : kpiData.currency)} at risk`} tone="danger" icon={<TrendingDown size={18} aria-hidden="true" />} />
          <KPIStat label="Maturing soon" value={kpiData.maturingSoonCount.toLocaleString()} helper="Next 30 days" tone="warning" icon={<CalendarDays size={18} aria-hidden="true" />} />
        </>}
      </section>

      <FilterBar definitions={filterDefinitions} value={filters} onChange={handleFilterChange} onReset={handleReset} />
      {listError ? <ErrorCoach error={listError} onRetry={() => window.location.reload()} title="Policies could not be loaded" compact /> : null}
      <DataTable
        metadata={{ columns, defaultOrdering: "-createdAt", pageSize: 20, totalLabel: "Policies" }}
        fetcher={fetcher}
        filters={filters}
        actions={actions}
        permissions={permissionCodes}
        canAction={canAction}
        exportFileName="ol-policies.csv"
        caption="Ordinary Life policy register"
        hideSearch
      />
    </div>
  )
}

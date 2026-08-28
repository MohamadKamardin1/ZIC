import { useCallback, useMemo, useState } from "react"
import { FilePlus2, Search } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { ErrorCoach } from "../../components/ErrorCoach"
import Modal from "../../components/shared/Modal"
import { DataTable } from "../../components/ui/DataTable"
import { FilterBar, type FilterValues } from "../../components/ui/FilterBar"
import { MasterDetailPage } from "../../components/ui/Patterns"
import { useToast } from "../../components/ui/Toast"
import type { RowAction, TableColumn, TableMetadata } from "../../components/ui/types"
import { useAccess } from "../../lib/access"
import { formatMoney } from "../../lib/commitmentsDisplay"
import {
  useClaimKpis,
  useClaimOptions,
  useRegisterClaimMutation,
} from "../../lib/claimsHooks"
import {
  CLAIM_STATUSES,
  listClaims,
  type ClaimAction,
  type ClaimListFilters,
  type ClaimOption,
  type ClaimRecord,
} from "../../lib/claims"
import { ClaimStatusBadge, claimStatusLabel, MoneyCell } from "../../components/claims/ClaimPrimitives"

const STATUS_OPTIONS = CLAIM_STATUSES.map((status) => ({ value: status, label: claimStatusLabel(status) }))

const FILTER_DEFINITIONS = [
  { key: "status", label: "Status", type: "select" as const, options: STATUS_OPTIONS, placeholder: "All statuses" },
  { key: "claim_type", label: "Claim type", type: "select" as const, placeholder: "All claim types" },
  { key: "fraud_flag", label: "Fraud review", type: "select" as const, options: [{ value: "true", label: "Flagged" }], placeholder: "All claims" },
  { key: "date_range", label: "Claim date", type: "date-range" as const },
]

type ListQuery = { page?: number; pageSize?: number; search?: string; ordering?: string; filters?: Record<string, unknown> }
type ActionKey = "view" | "assess" | "raise-requisition" | "settle" | "print"
type ActionTarget = { action: ActionKey; row: ClaimRecord } | null

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

function optionValues(options: ClaimOption[]): { value: string; label: string }[] {
  return options.map((option) => ({ value: option.value, label: option.label }))
}

function tableFilters(query: ListQuery): ClaimListFilters {
  const filters = query.filters ?? {}
  const range = queryValue(filters.date_range).split(",")
  return {
    page: query.page,
    pageSize: query.pageSize,
    search: query.search,
    ordering: query.ordering,
    status: queryValue(filters.status) || undefined,
    claimType: queryValue(filters.claim_type) || undefined,
    fraudFlag: queryValue(filters.fraud_flag).toLowerCase() === "true" || undefined,
    dateFrom: range[0] || undefined,
    dateTo: range[1] || undefined,
  }
}

function humanActionLabel(action: string): string {
  return action.replace(/[_-]+/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function kpiMoney(value: string | undefined, currency: string | undefined) {
  return value === undefined ? "…" : <MoneyCell value={value} currency={currency || "TZS"} />
}

function RegisterClaimModal({ open, onClose, onRegistered }: { open: boolean; onClose: () => void; onRegistered: (claimNumber: string) => void }) {
  const [policy, setPolicy] = useState<ClaimOption | null>(null)
  const [policySearch, setPolicySearch] = useState("")
  const [claimType, setClaimType] = useState("")
  const [benefitType, setBenefitType] = useState("")
  const [memberId, setMemberId] = useState("")
  const [claimDate, setClaimDate] = useState("")
  const [causeOfClaim, setCauseOfClaim] = useState("")
  const [description, setDescription] = useState("")
  const [searchOpen, setSearchOpen] = useState(false)

  const policyParams = useMemo(() => ({ q: policySearch, page: 1, pageSize: 10 }), [policySearch])
  const policyQuery = useClaimOptions("policies", policyParams, open && searchOpen)
  const typeQuery = useClaimOptions("types", {}, open && Boolean(policy))
  const benefitQuery = useClaimOptions("benefits", { policyId: policy?.value }, open && Boolean(policy))
  const memberQuery = useClaimOptions("members", { policyId: policy?.value }, open && Boolean(policy))

  const registerMutation = useRegisterClaimMutation()

  const policies = policyQuery.data?.results ?? []
  const benefits = benefitQuery.data?.results ?? []
  const members = memberQuery.data?.results ?? []

  const canSubmit = Boolean(policy && claimType && claimDate)

  const submit = () => {
    if (!policy || !canSubmit) return
    const selectedMember = members.find((member) => member.value === memberId)
    const claimantDetails = selectedMember
      ? { member_id: selectedMember.value, claimant_type: selectedMember.meta?.claimant_type ?? "POLICYHOLDER", relationship: selectedMember.meta?.relationship ?? "Self", name: selectedMember.label.split(" — ")[0] }
      : { claimant_type: "POLICYHOLDER", relationship: "Self", name: policy.meta?.policyholder_name ?? String(policy.label.split(" — ")[0]) }
    const idempotencyKey = typeof crypto.randomUUID === "function" ? crypto.randomUUID() : `claim-${Date.now()}`
    registerMutation.mutate(
      { policyId: policy.value, payload: { claimType, benefitType: benefitType || undefined, claimDate, causeOfClaim, description, memberId: selectedMember?.value, claimantDetails }, idempotencyKey },
      {
        onSuccess: (result) => {
          const claimNumber = result.claim?.claimNumber ?? "the claim"
          setPolicy(null); setPolicySearch(""); setClaimType(""); setBenefitType(""); setMemberId(""); setClaimDate(""); setCauseOfClaim(""); setDescription(""); setSearchOpen(false)
          onClose()
          onRegistered(claimNumber)
        },
      },
    )
  }

  return (
    <Modal open={open} title="Register Claim" onClose={onClose}>
      <div className="space-y-4">
        <div>
          <h3 className="text-base font-bold">New claim against a policy</h3>
          <p className="mt-1 text-sm leading-6 text-[var(--muted-foreground)]">Select the policy, claim type, and claimant. The claim registers with a unique idempotency key so a retry never creates a duplicate.</p>
        </div>

        <label className="block space-y-1.5">
          <span className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Policy</span>
          {policy ? (
            <div className="flex items-center justify-between gap-3 rounded-[10px] border bg-[var(--muted)]/35 px-3 py-2.5">
              <span className="min-w-0"><span className="block truncate text-sm font-bold">{policy.label}</span><span className="block text-xs text-[var(--muted-foreground)]">Status: {String(policy.meta?.status ?? "Active")} · {String(policy.meta?.policy_number ?? "")}</span></span>
              <button type="button" className="text-xs font-bold text-[var(--primary)] hover:underline" onClick={() => setPolicy(null)}>Change</button>
            </div>
          ) : (
            <button type="button" onClick={() => setSearchOpen(true)} className="flex h-10 w-full items-center justify-between rounded-[10px] border bg-[var(--card)] px-3 text-sm outline-none focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)]"><span className="text-[var(--muted-foreground)]">Choose a policy…</span><Search size={16} className="text-[var(--muted-foreground)]" aria-hidden="true" /></button>
          )}
        </label>

        {searchOpen && (
          <div className="space-y-2">
            <input autoFocus value={policySearch} onChange={(event) => setPolicySearch(event.target.value)} placeholder="Policy number or policyholder" className="h-10 w-full rounded-[10px] border bg-[var(--card)] px-3 text-sm outline-none focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)]" />
            {policyQuery.error && <ErrorCoach title="Policies could not be loaded" message={policyQuery.error.message} resolutionSteps={["Confirm that the policy service is available.", "Search again or ask servicing support to verify the policy reference."]} />}
            <div className="max-h-56 space-y-2 overflow-y-auto" aria-live="polite">
              {policyQuery.isLoading && <div className="rounded-lg border border-dashed px-4 py-6 text-center text-sm text-[var(--muted-foreground)]">Loading policies…</div>}
              {!policyQuery.isLoading && !policyQuery.error && policies.length === 0 && <div className="rounded-lg border border-dashed px-4 py-6 text-center text-sm text-[var(--muted-foreground)]">No policies match this search.</div>}
              {policies.map((option) => <button key={option.value} type="button" onClick={() => { setPolicy(option); setSearchOpen(false); setPolicySearch("") }} className="flex w-full items-start justify-between gap-3 rounded-lg border bg-[var(--card)] px-3 py-3 text-left transition hover:border-[var(--primary)] hover:bg-[var(--secondary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"><span className="min-w-0"><span className="block truncate text-sm font-bold">{option.label}</span><span className="mt-1 block text-xs text-[var(--muted-foreground)]">{String(option.meta?.policy_number ?? "")}</span></span><span className="shrink-0 rounded-full bg-emerald-100 px-2 py-1 text-[11px] font-bold text-emerald-700">{String(option.meta?.status ?? "Active")}</span></button>)}
            </div>
          </div>
        )}

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block space-y-1.5">
            <span className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Claim type *</span>
            <select value={claimType} onChange={(event) => setClaimType(event.target.value)} className="h-10 w-full rounded-[10px] border bg-[var(--card)] px-3 text-sm outline-none focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)]">
              <option value="">Choose a claim type…</option>
              {(typeQuery.data?.results ?? []).map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </label>
          <label className="block space-y-1.5">
            <span className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Claim date *</span>
            <input type="date" value={claimDate} onChange={(event) => setClaimDate(event.target.value)} className="h-10 w-full rounded-[10px] border bg-[var(--card)] px-3 text-sm outline-none focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)]" />
          </label>
        </div>

        <label className="block space-y-1.5">
          <span className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Covered benefit</span>
          <select value={benefitType} onChange={(event) => setBenefitType(event.target.value)} disabled={!policy} className="h-10 w-full rounded-[10px] border bg-[var(--card)] px-3 text-sm outline-none focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)] disabled:opacity-60">
            <option value="">{policy ? "Choose a covered benefit…" : "Choose a policy first"}</option>
            {benefits.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </label>

        <label className="block space-y-1.5">
          <span className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Claimant</span>
          <select value={memberId} onChange={(event) => setMemberId(event.target.value)} disabled={!policy} className="h-10 w-full rounded-[10px] border bg-[var(--card)] px-3 text-sm outline-none focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)] disabled:opacity-60">
            <option value="">{policy ? "Choose a policy member…" : "Choose a policy first"}</option>
            {members.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </label>

        <label className="block space-y-1.5">
          <span className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Cause of claim</span>
          <input value={causeOfClaim} onChange={(event) => setCauseOfClaim(event.target.value)} placeholder="e.g. Hospitalisation for malaria treatment" className="h-10 w-full rounded-[10px] border bg-[var(--card)] px-3 text-sm outline-none focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)]" />
        </label>

        <label className="block space-y-1.5">
          <span className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Description</span>
          <textarea value={description} onChange={(event) => setDescription(event.target.value)} rows={2} placeholder="Additional context for the claims officer" className="w-full rounded-[10px] border bg-[var(--card)] px-3 py-2 text-sm outline-none focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)]" />
        </label>

        {registerMutation.isError && <ErrorCoach title="The claim could not be registered" message={registerMutation.error.message} resolutionSteps={["Correct the highlighted fields and submit again.", "If the error mentions an idempotency conflict, reopen the existing claim instead of resubmitting."]} />}

        <div className="flex justify-end gap-2 border-t pt-4">
          <button type="button" className="button-secondary" onClick={onClose}>Cancel</button>
          <button type="button" className="button-primary inline-flex items-center gap-2" onClick={submit} disabled={!canSubmit || registerMutation.isPending}><FilePlus2 size={16} aria-hidden="true" />{registerMutation.isPending ? "Registering…" : "Register Claim"}</button>
        </div>
      </div>
    </Modal>
  )
}

export default function OLClaims() {
  const { access, canAccess, hasPermission, isSuperAdmin } = useAccess()
  const navigate = useNavigate()
  const { toast } = useToast()
  const [filters, setFilters] = useState<FilterValues>({})
  const [refreshKey, setRefreshKey] = useState(0)
  const [registerOpen, setRegisterOpen] = useState(false)
  const [actionTarget, setActionTarget] = useState<ActionTarget>(null)
  const claimTypeQuery = useClaimOptions("types")

  const can = useCallback((permission: string) => {
    if (isSuperAdmin) return true
    const normalized = permission.toLowerCase()
    const permissionKeys = access.permissions.map((item) => `${item.module}.${item.action}`.toLowerCase())
    return Boolean(hasPermission?.(permission) || permissionKeys.includes(normalized) || (permission.endsWith(".view") && canAccess("ol_claims")))
  }, [access.permissions, canAccess, hasPermission, isSuperAdmin])

  const kpiFilters = useMemo<ClaimListFilters>(() => {
    const range = filters.date_range && typeof filters.date_range === "object" && !Array.isArray(filters.date_range) ? filters.date_range : {}
    return {
      status: textValue(filters.status) || undefined,
      claimType: textValue(filters.claim_type) || undefined,
      fraudFlag: textValue(filters.fraud_flag).toLowerCase() === "true" || undefined,
      dateFrom: range.from,
      dateTo: range.to,
    }
  }, [filters])
  const kpiQuery = useClaimKpis(kpiFilters, can("ol_claims.view"))

  const fetcher = useCallback(async (query: ListQuery) => {
    const result = await listClaims(tableFilters(query))
    return { results: result.results, count: result.count, next: typeof result.next === "string" ? result.next : null, previous: typeof result.previous === "string" ? result.previous : null, page: result.page, page_size: result.pageSize }
  }, [])

  const actions: RowAction<ClaimRecord>[] = useMemo(() => [
    { key: "view", label: "View", onSelect: (row) => navigate(`/ordinary-life/claims/${encodeURIComponent(row.id)}`) },
    { key: "assess", label: "Assess", isVisible: (row) => ["REGISTERED", "PENDING_MEDICAL"].includes(String(row.status).toUpperCase()), onSelect: (row) => navigate(`/ordinary-life/claims/${encodeURIComponent(row.id)}?action=assess`) },
    { key: "raise-requisition", label: "Raise requisition", isVisible: (row) => String(row.status).toUpperCase() === "ASSESSED", onSelect: (row) => navigate(`/ordinary-life/claims/${encodeURIComponent(row.id)}?action=raise-requisition`) },
    { key: "settle", label: "Settle", isVisible: (row) => ["REQUISITIONED", "APPROVED"].includes(String(row.status).toUpperCase()), onSelect: (row) => navigate(`/ordinary-life/claims/${encodeURIComponent(row.id)}?action=settle`) },
    { key: "print", label: "Print voucher", isVisible: (row) => ["SETTLED", "APPROVED"].includes(String(row.status).toUpperCase()), onSelect: (row) => navigate(`/ordinary-life/claims/${encodeURIComponent(row.id)}?action=print`) },
  ], [navigate])

  const canAction = useCallback((action: RowAction<ClaimRecord>, row: ClaimRecord) => {
    const actionKey = action.key as ActionKey
    const allowed = new Set((row.allowedActions ?? []).map((item) => item.toLowerCase().replace(/-/g, "_")))
    if (actionKey !== "view" && !allowed.has(actionKey)) return false
    const permissions: Record<ActionKey, string> = { view: "ol_claims.view", assess: "ol_claims.assess", "raise-requisition": "ol_claims.requisition", settle: "ol_claims.settle", print: "ol_claims.print" }
    return can(permissions[actionKey])
  }, [can])

  const columns: TableColumn<ClaimRecord>[] = useMemo(() => [
    { key: "claim_number", label: "Claim number", field: "claimNumber", sortable: true, render: (_value, row) => <button type="button" className="font-bold text-[var(--primary)] underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]" onClick={() => navigate(`/ordinary-life/claims/${encodeURIComponent(row.id)}`)}>{row.claimNumber || "—"}</button> },
    { key: "policy_number", label: "Policy number", field: "policyNumber", sortable: true, render: (_value, row) => <span className="font-semibold">{row.policyNumber || "—"}</span> },
    { key: "policyholder_name", label: "Policyholder", field: "policyholderName", sortable: true, render: (_value, row) => <div><span className="font-semibold">{row.policyholderName || "—"}</span><span className="mt-1 block text-xs text-[var(--muted-foreground)]">{row.policyholderDisplay && row.policyholderDisplay !== row.policyholderName ? row.policyholderDisplay : ""}</span></div> },
    { key: "product", label: "Product", field: "productDisplay", sortable: true, render: (_value, row) => row.productDisplay || "—" },
    { key: "claim_type", label: "Claim type", field: "claimType", sortable: true, render: (_value, row) => row.claimType || "—" },
    { key: "claim_date", label: "Claim date", field: "claimDate", sortable: true, render: (value) => dateLabel(value as string | null) },
    { key: "amount", label: "Amount", field: "amount", sortable: true, align: "right", render: (_value, row) => <MoneyCell value={row.amount} currency={row.currency} variant="calculated" label="Claim amount" /> },
    { key: "status", label: "Status", field: "status", sortable: true, render: (_value, row) => <ClaimStatusBadge status={row.status} statusDisplay={row.statusDisplay} /> },
    { key: "fraud_flag", label: "Fraud review", field: "fraudFlag", render: (_value, row) => row.fraudFlag ? <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-bold text-amber-700">Flagged</span> : "—" },
    { key: "allowed_actions", label: "Allowed actions", field: "allowedActions", render: (_value, row) => row.allowedActions.length ? <span className="text-xs text-[var(--muted-foreground)]">{row.allowedActions.map(humanActionLabel).join(", ")}</span> : "—" },
  ], [navigate])

  const stats = [
    { label: "Total claims", value: numberLabel(kpiQuery.data?.totalClaims), helper: kpiQuery.data ? `${formatMoney(kpiQuery.data.outstandingAmount, kpiQuery.data.currency)} outstanding` : "From backend KPIs" },
    { label: "Outstanding amount", value: kpiMoney(kpiQuery.data?.outstandingAmount, kpiQuery.data?.currency), helper: `Currency: ${kpiQuery.data?.currency || "TZS"}` },
    { label: "Settled · period", value: kpiMoney(kpiQuery.data?.settledAmountPeriod, kpiQuery.data?.currency), helper: "Settled claims this period" },
    { label: "Pending assessment", value: numberLabel(kpiQuery.data?.pendingAssessmentCount), helper: kpiQuery.data?.timestamp ? `Updated ${dateLabel(kpiQuery.data.timestamp)}` : "Backend KPI timestamp" },
  ]

  const filterDefinitions = useMemo(() => FILTER_DEFINITIONS.map((definition) => definition.key === "claim_type" ? { ...definition, options: optionValues(claimTypeQuery.data?.results ?? []) } : definition), [claimTypeQuery.data?.results])

  return (
    <div className="space-y-5 p-1 md:p-2">
      <MasterDetailPage eyebrow="Ordinary Life / Servicing" title="Claims" description="Review OL claims, lifecycle status, and available actions. Search and filters are applied server-side; the backend action matrix remains the source of truth." stats={stats} actions={<button type="button" className="button-primary inline-flex items-center gap-2" onClick={() => setRegisterOpen(true)} disabled={!can("ol_claims.create")}><FilePlus2 size={16} aria-hidden="true" />Register Claim</button>}>
        {kpiQuery.error && <ErrorCoach title="Claim KPIs need attention" message={kpiQuery.error.message} resolutionSteps={["Confirm the OL Claims API is available.", "Review the selected filters and retry the page."]} />}
        <FilterBar definitions={filterDefinitions} value={filters} onChange={(key, value) => setFilters((current) => ({ ...current, [key]: value }))} onApply={() => setRefreshKey((value) => value + 1)} onReset={() => { setFilters({}); setRefreshKey((value) => value + 1) }} />
        <DataTable<ClaimRecord> metadata={{ columns, defaultOrdering: "-created_at", pageSize: 20, totalLabel: "Claims" } satisfies TableMetadata<ClaimRecord>} fetcher={fetcher} filters={filters} refreshKey={refreshKey} actions={actions} canAction={canAction} hideSearch errorContent={<ErrorCoach title="Claims could not be loaded" message="The Claims register did not return a response." resolutionSteps={["Confirm the backend is running and your session has ol_claims.view.", "Retry the table. If the problem continues, provide the correlation ID from the failed request to support."]} />} exportFileName="ol-claims.csv" caption="Ordinary Life claims work queue" />
      </MasterDetailPage>
      <RegisterClaimModal open={registerOpen} onClose={() => setRegisterOpen(false)} onRegistered={(claimNumber) => { toast({ tone: "success", title: "Claim registered", message: `${claimNumber} has been registered against the selected policy.` }) }} />
      <Modal open={Boolean(actionTarget)} title={actionTarget ? `Claim ${actionTarget.action.replace("-", " ")}` : "Claim action"} onClose={() => setActionTarget(null)}>
        {actionTarget && <div className="space-y-4"><div className="rounded-lg border bg-[var(--muted)]/35 p-4"><p className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Selected claim</p><p className="mt-1 text-sm font-bold">{actionTarget.row.claimNumber}</p><p className="mt-1 text-xs text-[var(--muted-foreground)]">{actionTarget.row.policyholderName} · {actionTarget.row.policyNumber}</p><div className="mt-3 flex flex-wrap items-center gap-3 text-sm"><ClaimStatusBadge status={actionTarget.row.status} statusDisplay={actionTarget.row.statusDisplay} /><MoneyCell value={actionTarget.row.amount} currency={actionTarget.row.currency} variant="calculated" label="Claim amount" /></div></div><p className="text-sm leading-6 text-[var(--muted-foreground)]">{actionTarget.action === "view" ? "Open the claim detail workspace to review documents, assessment, financials, and audit history." : "Open the claim detail workspace to complete this workflow step. The detail page verifies permissions and enforces the backend progression guards."}</p><div className="flex justify-end gap-2 border-t pt-4"><button type="button" className="button-secondary" onClick={() => setActionTarget(null)}>Cancel</button><button type="button" className="button-primary" onClick={() => { const id = actionTarget.row.id; const action = actionTarget.action as ClaimAction; setActionTarget(null); navigate(`/ordinary-life/claims/${encodeURIComponent(id)}?action=${encodeURIComponent(action)}`) }}>Open detail</button></div></div>}
      </Modal>
    </div>
  )
}

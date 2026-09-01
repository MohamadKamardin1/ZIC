import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { FilePlus2, Search } from "lucide-react"
import { ErrorCoach } from "../../components/ErrorCoach"
import { DataTable } from "../../components/ui/DataTable"
import { FilterBar, type FilterValues } from "../../components/ui/FilterBar"
import { MasterDetailPage } from "../../components/ui/Patterns"
import { Modal } from "../../components/ui/Overlays"
import type { RowAction, TableColumn, TableMetadata } from "../../components/ui/types"
import { MoneyCell, PlanStatusBadge, planStatusLabel } from "../../components/maturityInstallments/MIPrimitives"
import { useToast } from "../../components/ui/Toast"
import { useAccess } from "../../lib/access"
import { listPolicies, type PolicyListItem } from "../../lib/policies"
import {
  cancelMIPlan,
  createMIPlan,
  getMIPlanDetail,
  listMIPlans,
  MI_FREQUENCIES,
  MI_PLAN_STATUSES,
  printMISchedule,
  processMIPayment,
  type MIPlanAction,
  type MIPlanListFilters,
  type MIPlanRecord,
} from "../../lib/maturityInstallments"
import { invalidateMaturityInstallmentQueries, useMIFrequencyOptions, useMIPlanKpis, useMITermOptions } from "../../lib/maturityInstallmentsHooks"
import { toStructuredError, type StructuredError } from "../../lib/structuredError"

const STATUS_OPTIONS = MI_PLAN_STATUSES.map((value) => ({ value, label: planStatusLabel(value) }))

const FREQUENCY_LABELS: Record<string, string> = {
  SINGLE: "Single lump sum",
  MONTHLY: "Monthly",
  QUARTERLY: "Quarterly",
  HALF_YEARLY: "Half-yearly",
  ANNUAL: "Annual",
}

function frequencyLabel(value: string): string {
  return FREQUENCY_LABELS[value.toUpperCase()] ?? value.toLowerCase().replace(/_/g, " ")
}

const FREQUENCY_OPTIONS = MI_FREQUENCIES.map((value) => ({ value, label: frequencyLabel(value) }))

const FILTER_DEFINITIONS = [
  { key: "status", label: "Status", type: "select" as const, options: STATUS_OPTIONS, placeholder: "All statuses" },
  { key: "frequency", label: "Frequency", type: "select" as const, options: FREQUENCY_OPTIONS, placeholder: "All frequencies" },
  { key: "date_range", label: "Start date", type: "date-range" as const },
]

type ActionKey = "view" | "process_payment" | "print" | "cancel"

function textValue(value: unknown): string {
  return value === null || value === undefined || value === "" ? "" : String(value)
}

function dateLabel(value?: string | null): string {
  if (!value) return "—"
  const parsed = new Date(`${value.slice(0, 10)}T00:00:00`)
  return Number.isNaN(parsed.getTime()) ? value : new Intl.DateTimeFormat("en-GB", { dateStyle: "medium" }).format(parsed)
}

function numberLabel(value: number | null | undefined): string {
  if (value === undefined) return "…"
  if (value === null) return "—"
  return new Intl.NumberFormat("en-US").format(value)
}

function kpiMoney(value: string | null | undefined): ReactNode {
  if (value === undefined) return "…"
  if (value === null) return "—"
  return <MoneyCell value={value} currency="TZS" />
}

function todayLocal(): string {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`
}

function queryString(value: unknown): string {
  if (typeof value === "string") return value
  if (Array.isArray(value)) return value.join(",")
  return value === undefined || value === null ? "" : String(value)
}

function tableFilters(query: { page?: number; pageSize?: number; search?: string; ordering?: string; filters?: Record<string, unknown> }): MIPlanListFilters {
  const filters = query.filters ?? {}
  const range = queryString(filters.date_range).split(",")
  return {
    page: query.page,
    pageSize: query.pageSize,
    search: query.search,
    sort: query.ordering,
    status: queryString(filters.status) || undefined,
    frequency: queryString(filters.frequency) || undefined,
    product: queryString(filters.product) || undefined,
    branch: queryString(filters.branch) || undefined,
    dateFrom: range[0] || undefined,
    dateTo: range[1] || undefined,
  }
}

const PAYOUTS_PER_YEAR: Record<string, number> = { SINGLE: 1, MONTHLY: 12, QUARTERLY: 4, HALF_YEARLY: 2, ANNUAL: 1 }

function moneyNumber(value: string | number | null | undefined): number {
  if (value === null || value === undefined || value === "") return Number.NaN
  const number = Number(value)
  return Number.isFinite(number) ? number : Number.NaN
}

function GeneratePlanModal({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: (planId: string) => void }) {
  const [step, setStep] = useState(1)
  const [search, setSearch] = useState("")
  const [policy, setPolicy] = useState<PolicyListItem | null>(null)
  const [frequency, setFrequency] = useState("")
  const [termYears, setTermYears] = useState("")
  const [error, setError] = useState<StructuredError | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const policyQuery = useQuery({
    queryKey: ["ol-maturity-installments", "create-policy-search", search],
    queryFn: () => listPolicies({ search, status: "MATURED", page: 1, pageSize: 10 }),
    enabled: open && step === 1,
    staleTime: 30_000,
  })
  const frequencyQuery = useMIFrequencyOptions({}, open)
  const termQuery = useMITermOptions({}, open && step >= 2)
  const policies = policyQuery.data?.results ?? []
  const frequencyOptions = frequencyQuery.data?.results ?? []
  const termOptions = termQuery.data?.results ?? []

  useEffect(() => {
    if (open) return
    setStep(1); setSearch(""); setPolicy(null); setFrequency(""); setTermYears(""); setError(null); setSubmitting(false)
  }, [open])

  useEffect(() => {
    if (!frequency && frequencyOptions.length > 0) setFrequency(frequencyOptions[0].value)
  }, [frequencyOptions, frequency])

  const maturityValue = moneyNumber(policy?.maturityValue)
  const maturityValueValid = Boolean(policy) && Number.isFinite(maturityValue) && maturityValue > 0
  const selectedFrequency = frequencyOptions.find((option) => option.value === frequency)
  const payoutPerYear = selectedFrequency?.meta?.payoutPerYear ?? (frequency ? PAYOUTS_PER_YEAR[frequency] ?? 0 : 0)
  const termNumber = Number(termYears)
  const installments = Number.isFinite(termNumber) && termNumber > 0 && payoutPerYear > 0 ? termNumber * payoutPerYear : 0
  const amountPerInstallment = maturityValueValid && installments > 0 ? maturityValue / installments : 0
  const canConfigure = maturityValueValid && Boolean(frequency) && Boolean(termYears)
  const installmentsLabel = installments > 0 ? new Intl.NumberFormat("en-US").format(installments) : "—"
  const amountLabel = amountPerInstallment > 0 ? <MoneyCell value={amountPerInstallment.toFixed(2)} currency={policy?.currency ?? "TZS"} /> : "—"

  const selectPolicy = (selected: PolicyListItem) => {
    if (selected.status !== "MATURED") {
      setPolicy(null)
      setError({ code: "POLICY_NOT_MATURED", message: `${selected.policyNumber} is ${selected.statusDisplay.toLowerCase()} and cannot be used to generate an installment plan. Only matured policies are eligible.`, resolutionSteps: ["Search for a policy with Matured status.", "Raise the maturity for this policy in the policy register first, then search again."], fieldErrors: {}, retryable: false, status: 422, raw: null })
      return
    }
    setPolicy(selected)
    setError(null)
    setStep(2)
  }

  const submit = async () => {
    if (!policy) return
    if (!frequency || !termYears) {
      setError({ code: "REQUIRED_FIELDS", message: "Choose a payout frequency and term before generating the plan.", resolutionSteps: ["Select the frequency and term from the options catalogs.", "Submit again once both fields are completed."], fieldErrors: {}, retryable: false, status: 400, raw: null })
      return
    }
    if (!maturityValueValid) {
      setError({ code: "INVALID_MATURITY_VALUE", message: "The policy maturity value must be positive before an installment plan can be generated.", resolutionSteps: ["Confirm the maturity valuation was posted for the selected policy.", "Choose a matured policy with a positive effective maturity value."], fieldErrors: {}, retryable: false, status: 422, raw: null })
      return
    }
    setSubmitting(true); setError(null)
    try {
      const result = await createMIPlan({ policyId: policy.id, frequency, termYears: Number(termYears) }, crypto.randomUUID())
      const createdId = result.plan?.id
      if (!createdId) throw new Error("The backend did not return the created plan identifier.")
      onCreated(createdId)
    } catch (caught) {
      setError(toStructuredError(caught, "The installment plan could not be generated."))
    } finally {
      setSubmitting(false)
    }
  }

  return <Modal open={open} title="Generate installment plan" description="Create a maturity installment schedule against a matured policy. The backend revalidates policy maturity and the configured rate table before creating the plan." onClose={onClose} size="lg">
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2" aria-label="Generate plan steps">
        {["Select Policy", "Configure Terms", "Generate"].map((label, index) => <div key={label} className={`flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-bold ${step === index + 1 ? "bg-[var(--primary)] text-[var(--primary-foreground)]" : step > index + 1 ? "bg-[var(--success)]/12 text-[var(--success)]" : "bg-[var(--muted)] text-[var(--muted-foreground)]"}`}><span>{index + 1}</span>{label}</div>)}
      </div>
      {error && <ErrorCoach title={error.code === "INSTALLMENT_POLICY_NOT_MATURED" || error.code === "POLICY_NOT_MATURED" ? "Policy not matured" : error.code === "INVALID_MATURITY_VALUE" ? "Maturity value must be positive" : "Installment plan needs attention"} message={error.message} resolutionSteps={error.resolutionSteps} />}
      {step === 1 && <div className="space-y-4">
        <div><h3 className="text-base font-bold">Select policy</h3><p className="mt-1 text-sm leading-6 text-[var(--muted-foreground)]">Search for a matured policy. Selecting it auto-fills the effective maturity value the schedule is built from.</p></div>
        <label className="block space-y-1.5"><span className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Search policies</span><span className="relative block"><Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)]" aria-hidden="true" /><input autoFocus value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Policy number, policyholder, or product" className="h-10 w-full rounded-[10px] border border-[var(--border)] bg-[var(--card)] pl-9 pr-3 text-sm outline-none focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)]" /></span></label>
        {policyQuery.error && <ErrorCoach title="Policies could not be loaded" message={policyQuery.error.message} resolutionSteps={["Confirm that the policy service is available.", "Search again or ask servicing support to verify policy access."]} />}
        <div className="max-h-72 space-y-2 overflow-y-auto" aria-live="polite">
          {policyQuery.isLoading && <div className="rounded-lg border border-dashed border-[var(--border)] px-4 py-8 text-center text-sm text-[var(--muted-foreground)]">Loading policies…</div>}
          {!policyQuery.isLoading && !policyQuery.error && policies.length === 0 && <div className="rounded-lg border border-dashed border-[var(--border)] px-4 py-8 text-center text-sm text-[var(--muted-foreground)]">No policies match this search.</div>}
          {policies.map((item) => <button key={item.id} type="button" onClick={() => selectPolicy(item)} className="flex w-full items-start justify-between gap-3 rounded-lg border border-[var(--border)] bg-[var(--card)] px-3 py-3 text-left transition hover:border-[var(--primary)] hover:bg-[var(--secondary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"><span className="min-w-0"><span className="block truncate text-sm font-bold">{item.policyNumber}</span><span className="mt-1 block truncate text-xs text-[var(--muted-foreground)]">{item.policyholderDisplay || item.policyholderName}</span><span className="mt-1 block truncate text-xs text-[var(--muted-foreground)]">{item.productPlanDisplay}</span></span><span className={`shrink-0 rounded-full px-2 py-1 text-[11px] font-bold ${item.status === "MATURED" ? "bg-[var(--success)]/10 text-[var(--success)]" : "bg-[var(--warning)]/12 text-[var(--warning-foreground)]"}`}>{item.statusDisplay || item.status}</span></button>)}
        </div>
      </div>}
      {step === 2 && policy && <div className="space-y-4">
        <div><h3 className="text-base font-bold">Configure terms</h3><p className="mt-1 text-sm leading-6 text-[var(--muted-foreground)]">Choose the payout frequency and term. The installment count and amount are calculated from the policy maturity value.</p></div>
        <div className="rounded-lg border border-[var(--border)] bg-[var(--muted)]/35 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Selected policy</p>
              <p className="mt-1 text-sm font-bold">{policy.policyNumber}</p>
              <p className="mt-1 text-xs text-[var(--muted-foreground)]">{policy.policyholderDisplay || policy.policyholderName} · {policy.productPlanDisplay}</p>
            </div>
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Maturity value</p>
              <p className="mt-1 text-sm font-bold"><MoneyCell value={policy.maturityValue} currency={policy.currency} /></p>
            </div>
          </div>
        </div>
        {!maturityValueValid && <ErrorCoach title="Maturity value must be positive" message={`${policy.policyNumber} does not carry a positive effective maturity value. An installment plan can only be generated against a positive maturity value.`} resolutionSteps={["Confirm the maturity valuation was posted for the selected policy.", "Choose a matured policy with a positive effective maturity value."]} />}
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block space-y-1.5"><span className="text-xs font-bold">Payout frequency</span><select value={frequency} onChange={(event) => setFrequency(event.target.value)} className="h-10 w-full rounded-[10px] border border-[var(--border)] bg-[var(--card)] px-3 text-sm outline-none focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)]"><option value="">Select frequency</option>{frequencyOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
          <label className="block space-y-1.5"><span className="text-xs font-bold">Term (years)</span><select value={termYears} onChange={(event) => setTermYears(event.target.value)} className="h-10 w-full rounded-[10px] border border-[var(--border)] bg-[var(--card)] px-3 text-sm outline-none focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)]"><option value="">Select term</option>{termOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
        </div>
        <div className="rounded-lg border border-[var(--success)]/25 bg-[var(--success)]/8 px-4 py-3" data-testid="installment-preview">
          <p className="text-sm font-bold">Preview</p>
          <dl className="mt-2 grid gap-2 text-sm sm:grid-cols-2">
            <div><dt className="text-xs text-[var(--muted-foreground)]">Number of installments</dt><dd className="mt-1 font-bold" data-testid="preview-installments">{installmentsLabel}</dd></div>
            <div><dt className="text-xs text-[var(--muted-foreground)]">Amount per installment</dt><dd className="mt-1 font-bold" data-testid="preview-amount">{amountLabel}</dd></div>
          </dl>
          <p className="mt-2 text-xs leading-5 text-[var(--muted-foreground)]">Calculated as maturity value ÷ ({installments > 0 ? `${termNumber} year${termNumber === 1 ? "" : "s"} × ${payoutPerYear} payments per year` : "the configured term"}). The backend reconciles against the rate table before activation.</p>
        </div>
      </div>}
      {step === 3 && policy && <div className="space-y-4">
        <div><h3 className="text-base font-bold">Confirm and generate</h3><p className="mt-1 text-sm leading-6 text-[var(--muted-foreground)]">Review the plan configuration before creation. The plan is created in CREATED status with every installment scheduled.</p></div>
        <dl className="rounded-lg border border-[var(--border)] bg-[var(--muted)]/35 p-4 text-sm">
          <div className="grid gap-3 sm:grid-cols-2">
            <div><dt className="text-xs text-[var(--muted-foreground)]">Policy</dt><dd className="mt-1 font-bold">{policy.policyNumber}</dd></div>
            <div><dt className="text-xs text-[var(--muted-foreground)]">Policyholder</dt><dd className="mt-1">{policy.policyholderDisplay || policy.policyholderName}</dd></div>
            <div><dt className="text-xs text-[var(--muted-foreground)]">Maturity value</dt><dd className="mt-1 font-bold"><MoneyCell value={policy.maturityValue} currency={policy.currency} /></dd></div>
            <div><dt className="text-xs text-[var(--muted-foreground)]">Payout frequency</dt><dd className="mt-1 font-bold">{frequencyLabel(frequency)}</dd></div>
            <div><dt className="text-xs text-[var(--muted-foreground)]">Term</dt><dd className="mt-1 font-bold">{termYears} year{Number(termYears) === 1 ? "" : "s"}</dd></div>
            <div><dt className="text-xs text-[var(--muted-foreground)]">Installments</dt><dd className="mt-1 font-bold" data-testid="preview-installments">{installmentsLabel}</dd></div>
            <div><dt className="text-xs text-[var(--muted-foreground)]">Amount per installment</dt><dd className="mt-1 font-bold" data-testid="preview-amount">{amountLabel}</dd></div>
          </div>
        </dl>
      </div>}
      <div className="flex flex-wrap justify-between gap-2 border-t border-[var(--border)] pt-4">
        <button type="button" className="button-secondary" onClick={step === 1 ? onClose : () => setStep((current) => Math.max(1, current - 1))} disabled={submitting}>{step === 1 ? "Cancel" : "Back"}</button>
        {step < 2 && <button type="button" className="button-primary" onClick={() => setStep(2)} disabled={!policy}>Next</button>}
        {step === 2 && <button type="button" className="button-primary" onClick={() => setStep(3)} disabled={!canConfigure}>Review & Generate</button>}
        {step === 3 && <button type="button" className="button-primary" onClick={() => void submit()} disabled={submitting}>{submitting ? "Generating…" : "Generate plan"}</button>}
      </div>
    </div>
  </Modal>
}

export default function OLMaturityInstallments() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { access, hasPermission, isSuperAdmin } = useAccess()
  const { toast } = useToast()
  const [filters, setFilters] = useState<FilterValues>({})
  const [refreshKey, setRefreshKey] = useState(0)
  const [createOpen, setCreateOpen] = useState(false)
  const [processTarget, setProcessTarget] = useState<MIPlanRecord | null>(null)
  const [processBusy, setProcessBusy] = useState(false)
  const [processError, setProcessError] = useState<StructuredError | null>(null)
  const [cancelTarget, setCancelTarget] = useState<MIPlanRecord | null>(null)
  const [cancelBusy, setCancelBusy] = useState(false)
  const [cancelError, setCancelError] = useState<StructuredError | null>(null)
  const [cancelReason, setCancelReason] = useState("")

  const permissionCodes = useMemo(() => access.permissions.map((permission) => `${permission.module}.${permission.action}`.toLowerCase()), [access.permissions])
  const can = useCallback((permission: string) => isSuperAdmin || Boolean(hasPermission?.(permission) || permissionCodes.includes(permission.toLowerCase())), [hasPermission, isSuperAdmin, permissionCodes])

  const kpiFilters = useMemo<MIPlanListFilters>(() => {
    const dateRange = filters.date_range && typeof filters.date_range === "object" && !Array.isArray(filters.date_range) ? filters.date_range : {}
    return {
      status: textValue(filters.status) || undefined,
      frequency: textValue(filters.frequency) || undefined,
      product: textValue(filters.product) || undefined,
      branch: textValue(filters.branch) || undefined,
      dateFrom: dateRange.from,
      dateTo: dateRange.to,
    }
  }, [filters])
  const kpiQuery = useMIPlanKpis(kpiFilters, can("ol_maturity_installments.view"))

  const fetcher = useCallback(async (query: { page?: number; pageSize?: number; search?: string; ordering?: string; filters?: Record<string, unknown> }) => {
    const result = await listMIPlans(tableFilters(query))
    return { results: result.results, count: result.count, next: typeof result.next === "string" ? result.next : null, previous: typeof result.previous === "string" ? result.previous : null, page: result.page, page_size: result.pageSize }
  }, [])

  const handlePrint = useCallback(async (row: MIPlanRecord) => {
    try {
      const result = await printMISchedule(row.id)
      const url = result.signedDownloadUrl ?? result.previewUrl
      if (url) window.open(url, "_blank", "noopener,noreferrer")
      else toast({ tone: "info", title: "Schedule generated", message: "The schedule document has been generated for this plan." })
    } catch (error) {
      toast({ tone: "danger", title: "Schedule could not be printed", message: toStructuredError(error, "The schedule could not be generated.").message })
    }
  }, [toast])

  const actions: RowAction<MIPlanRecord>[] = useMemo(() => [
    { key: "view", label: "View", onSelect: (row) => navigate(`/ordinary-life/maturity-installments/${row.id}`) },
    { key: "process_payment", label: "Process payments", onSelect: (row) => { setProcessError(null); setProcessTarget(row) } },
    { key: "print", label: "Print schedule", onSelect: (row) => void handlePrint(row) },
    { key: "cancel", label: "Cancel plan", tone: "danger", onSelect: (row) => { setCancelError(null); setCancelReason(""); setCancelTarget(row) } },
  ], [navigate, handlePrint])

  const canAction = useCallback((action: RowAction<MIPlanRecord>, row: MIPlanRecord) => {
    const actionKey = action.key as ActionKey
    const allowed = new Set((row.allowedActions ?? []).map((item) => item.toLowerCase()))
    if (!allowed.has(actionKey)) return false
    const permissions: Record<ActionKey, string> = { view: "ol_maturity_installments.view", process_payment: "ol_maturity_installments.process_payment", print: "ol_maturity_installments.print", cancel: "ol_maturity_installments.cancel" }
    return can(permissions[actionKey])
  }, [can])

  const columns: TableColumn<MIPlanRecord>[] = useMemo(() => [
    { key: "plan_number", label: "Plan number", field: "planNumber", sortable: true, render: (_value, row) => <span className="font-bold">{row.planNumber || "—"}</span> },
    { key: "policy_number", label: "Policy number", field: "policyNumber", sortable: true, render: (_value, row) => <button type="button" className="font-semibold text-[var(--primary)] underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]" onClick={() => navigate(`/ordinary-life/policies/${row.policyId ?? row.policyNumber}`)}>{row.policyNumber || "—"}</button> },
    { key: "policyholder_name", label: "Policyholder", field: "policyholderName", sortable: true, render: (_value, row) => <div><span className="font-semibold">{row.policyholderName || "—"}</span><span className="mt-1 block text-xs text-[var(--muted-foreground)]">{row.policyholderDisplay && row.policyholderDisplay !== row.policyholderName ? row.policyholderDisplay : ""}</span></div> },
    { key: "maturity_value", label: "Total maturity value", field: "maturityValue", sortable: true, align: "right", render: (_value, row) => <MoneyCell value={row.maturityValue} currency={row.currency} /> },
    { key: "paid_amount", label: "Total paid", field: "paidAmount", sortable: true, align: "right", render: (_value, row) => <MoneyCell value={row.paidAmount} currency={row.currency} variant="paid" /> },
    { key: "balance", label: "Remaining balance", field: "balance", sortable: true, align: "right", render: (_value, row) => <MoneyCell value={row.balance} currency={row.currency} variant="balance" /> },
    { key: "frequency", label: "Frequency", field: "frequency", sortable: true, render: (_value, row) => <span>{frequencyLabel(row.frequency)}</span> },
    { key: "state", label: "Status", field: "status", sortable: true, render: (_value, row) => <PlanStatusBadge status={row.status} statusDisplay={row.statusDisplay} /> },
    { key: "start_date", label: "Start date", field: "startDate", sortable: true, render: (value) => dateLabel(value as string | null) },
  ], [navigate])

  const onPlanCreated = (planId: string) => {
    invalidateMaturityInstallmentQueries(queryClient, planId)
    setCreateOpen(false)
    setRefreshKey((value) => value + 1)
    toast({ tone: "success", title: "Installment Plan Generated", message: "Status: Created. The schedule is ready for the first due installment." })
    navigate(`/ordinary-life/maturity-installments/${planId}`)
  }

  const runBulkProcess = async () => {
    if (!processTarget) return
    setProcessBusy(true); setProcessError(null)
    try {
      const detail = await getMIPlanDetail(processTarget.id)
      const due = detail.items.filter((item) => (item.status === "SCHEDULED" || item.status === "MISSED") && (!item.dueDate || item.dueDate <= todayLocal()))
      if (due.length === 0) {
        toast({ tone: "info", title: "No due installments", message: `${processTarget.planNumber} has no scheduled or missed installments due for payment yet.` })
        setProcessTarget(null)
        return
      }
      let processed = 0
      for (const item of due) {
        await processMIPayment(item.id)
        processed += 1
      }
      invalidateMaturityInstallmentQueries(queryClient, processTarget.id)
      toast({ tone: "success", title: "Payments processed", message: `${processed} installment${processed === 1 ? "" : "s"} on ${processTarget.planNumber} moved to payment pending.` })
      setProcessTarget(null)
    } catch (error) {
      setProcessError(toStructuredError(error, "The installment payments could not be processed."))
    } finally {
      setProcessBusy(false)
    }
  }

  const confirmCancel = async () => {
    if (!cancelTarget) return
    if (!cancelReason.trim()) {
      setCancelError({ code: "REASON_REQUIRED", message: "A reason is required to cancel an installment plan.", resolutionSteps: ["Describe why the plan is being cancelled.", "Do not include sensitive credentials in the reason."], fieldErrors: {}, retryable: false, status: 400, raw: null })
      return
    }
    setCancelBusy(true); setCancelError(null)
    try {
      await cancelMIPlan(cancelTarget.id, { reason: cancelReason.trim() })
      invalidateMaturityInstallmentQueries(queryClient, cancelTarget.id)
      toast({ tone: "success", title: "Plan cancelled", message: `${cancelTarget.planNumber} has been cancelled and the remaining installments waived.` })
      setCancelTarget(null); setCancelReason("")
    } catch (error) {
      setCancelError(toStructuredError(error, "The plan could not be cancelled."))
    } finally {
      setCancelBusy(false)
    }
  }

  const stats = [
    { label: "Total active plans", value: numberLabel(kpiQuery.data?.totalPlansActive), helper: "Plans currently in the ACTIVE state" },
    { label: "Total value of active plans", value: kpiMoney(kpiQuery.data?.totalActivePlansValue), helper: "Sum of maturity value across active plans" },
    { label: "Upcoming payments (next 30 days)", value: numberLabel(kpiQuery.data?.upcomingNext30Days), helper: "Installments due within the next 30 days" },
    { label: "Missed payments", value: <span className="text-[var(--destructive)]">{numberLabel(kpiQuery.data?.missedPaymentsCount)}</span>, helper: "Installments past due and unpaid" },
  ]

  return <div className="space-y-5 p-1 md:p-2">
    <MasterDetailPage eyebrow="Ordinary Life / Maturity Installments" title="Maturity installment plans" description="Review maturity installment plans and run controlled payment actions. Search and filters are applied server-side; the backend action matrix remains the source of truth." stats={stats} actions={<button type="button" className="button-primary inline-flex items-center gap-2" onClick={() => setCreateOpen(true)} disabled={!can("ol_maturity_installments.create")}><FilePlus2 size={16} aria-hidden="true" />Generate Plan</button>}>
      {kpiQuery.error && <ErrorCoach title="Maturity Installment KPIs need attention" message={kpiQuery.error.message} resolutionSteps={["Confirm the Maturity Installments API is available.", "Review the selected filters and retry the page."]} />}
      <div className="space-y-3">
        <div className="surface-card flex flex-wrap items-end gap-3 p-4" role="group" aria-label="Installment plan filters">
          <div className="min-w-48 flex-1"><label className="mb-1.5 block text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]" htmlFor="mi-filter-product">Product</label><input id="mi-filter-product" value={textValue(filters.product)} onChange={(event) => setFilters((current) => ({ ...current, product: event.target.value }))} placeholder="Product code or name" className="h-10 w-full rounded-[10px] border bg-[var(--card)] px-3 text-sm outline-none focus:border-[var(--ring)]" /></div>
          <div className="min-w-48 flex-1"><label className="mb-1.5 block text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]" htmlFor="mi-filter-branch">Branch</label><input id="mi-filter-branch" value={textValue(filters.branch)} onChange={(event) => setFilters((current) => ({ ...current, branch: event.target.value }))} placeholder="Branch code or name" className="h-10 w-full rounded-[10px] border bg-[var(--card)] px-3 text-sm outline-none focus:border-[var(--ring)]" /></div>
        </div>
        <FilterBar definitions={FILTER_DEFINITIONS} value={filters} onChange={(key, value) => setFilters((current) => ({ ...current, [key]: value }))} onApply={() => setRefreshKey((value) => value + 1)} onReset={() => { setFilters({}); setRefreshKey((value) => value + 1) }} />
      </div>
      <DataTable<MIPlanRecord> metadata={{ columns, defaultOrdering: "-created_at", pageSize: 20, totalLabel: "Installment plans" } satisfies TableMetadata<MIPlanRecord>} fetcher={fetcher} filters={filters} refreshKey={refreshKey} actions={actions} canAction={canAction} hideSearch errorContent={<ErrorCoach title="Installment plans could not be loaded" message="The Maturity Installments register did not return a response." resolutionSteps={["Confirm the backend is running and your session has `ol_maturity_installments.view`.", "Retry the table. If it continues, provide the correlation ID from the failed request to support."]} />} exportFileName="ol-maturity-installments.csv" caption="Maturity installment plans register" />
    </MasterDetailPage>
    <GeneratePlanModal open={createOpen} onClose={() => setCreateOpen(false)} onCreated={onPlanCreated} />
    <Modal open={Boolean(processTarget)} title="Process due payments" onClose={() => { if (!processBusy) { setProcessTarget(null); setProcessError(null) } }} size="md">
      {processTarget && <div className="space-y-4">
        <div className="rounded-lg border border-[var(--border)] bg-[var(--muted)]/35 p-4">
          <p className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Selected plan</p>
          <p className="mt-1 text-sm font-bold">{processTarget.planNumber}</p>
          <p className="mt-1 text-xs text-[var(--muted-foreground)]">{processTarget.policyholderName} · {processTarget.policyNumber}</p>
          <div className="mt-3 flex flex-wrap items-center gap-3 text-sm"><PlanStatusBadge status={processTarget.status} statusDisplay={processTarget.statusDisplay} /><MoneyCell value={processTarget.balance} currency={processTarget.currency} label="Remaining balance" /></div>
        </div>
        <p className="text-sm leading-6 text-[var(--muted-foreground)]">This moves every scheduled or missed installment that is already due for payment into payment-pending and raises a Front Office requisition for each.</p>
        {processError && <ErrorCoach title="Payments could not be processed" message={processError.message} resolutionSteps={processError.resolutionSteps} />}
        <div className="flex flex-wrap justify-end gap-2 border-t border-[var(--border)] pt-4">
          <button type="button" className="button-secondary" onClick={() => { setProcessTarget(null); setProcessError(null) }} disabled={processBusy}>Cancel</button>
          <button type="button" className="button-primary" onClick={() => void runBulkProcess()} disabled={processBusy}>{processBusy ? "Processing…" : "Process due payments"}</button>
        </div>
      </div>}
    </Modal>
    <Modal open={Boolean(cancelTarget)} title="Cancel plan" onClose={() => { if (!cancelBusy) { setCancelTarget(null); setCancelError(null) } }} size="md">
      {cancelTarget && <div className="space-y-4">
        <div className="rounded-lg border border-[var(--border)] bg-[var(--muted)]/35 p-4">
          <p className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Selected plan</p>
          <p className="mt-1 text-sm font-bold">{cancelTarget.planNumber}</p>
          <p className="mt-1 text-xs text-[var(--muted-foreground)]">{cancelTarget.policyholderName} · {cancelTarget.policyNumber}</p>
          <div className="mt-3 flex flex-wrap items-center gap-3 text-sm"><PlanStatusBadge status={cancelTarget.status} statusDisplay={cancelTarget.statusDisplay} /><MoneyCell value={cancelTarget.balance} currency={cancelTarget.currency} label="Remaining balance" /></div>
        </div>
        <label className="block space-y-1.5"><span className="text-xs font-bold">Reason <span className="text-[var(--destructive)]">*</span></span><textarea value={cancelReason} onChange={(event) => { setCancelReason(event.target.value); setCancelError(null) }} rows={3} className="w-full rounded-[10px] border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm outline-none focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)]" placeholder="Explain why the plan is being cancelled. Remaining installments will be waived." /></label>
        {cancelError && <ErrorCoach title="Plan could not be cancelled" message={cancelError.message} resolutionSteps={cancelError.resolutionSteps} />}
        <div className="flex flex-wrap justify-end gap-2 border-t border-[var(--border)] pt-4">
          <button type="button" className="button-secondary" onClick={() => { setCancelTarget(null); setCancelError(null) }} disabled={cancelBusy}>Cancel</button>
          <button type="button" className="inline-flex min-h-10 items-center justify-center rounded-[10px] bg-[var(--destructive)] px-4 text-sm font-bold text-white" onClick={() => void confirmCancel()} disabled={cancelBusy}>{cancelBusy ? "Cancelling…" : "Cancel plan"}</button>
        </div>
      </div>}
    </Modal>
  </div>
}

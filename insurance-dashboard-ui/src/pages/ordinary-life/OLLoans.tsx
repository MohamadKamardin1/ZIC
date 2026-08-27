import { useCallback, useEffect, useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { FilePlus2, Search, ShieldCheck } from "lucide-react"
import { SmartSelect } from "../../components/ui/SmartSelect"
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
import { buildLoanQuery, createLoanRequest, listLoans, type LoanListFilters, type LoanRecord } from "../../lib/loans"
import { useLoanKpis, useLoanOptions, usePolicyLoanEligibility } from "../../lib/loansHooks"
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

const TERM_OPTIONS = [
  { value: "6", label: "6 months" },
  { value: "12", label: "12 months" },
  { value: "24", label: "24 months" },
  { value: "36", label: "36 months" },
  { value: "60", label: "60 months" },
]

type RequestModalError = { message: string; resolutionSteps: string[]; fieldErrors: Record<string, string[]> }

function readRequestError(error: unknown): RequestModalError {
  const record = error && typeof error === "object" ? error as Record<string, unknown> : {}
  const fieldErrors = record.fieldErrors && typeof record.fieldErrors === "object" ? record.fieldErrors as Record<string, string[]> : {}
  const resolutionSteps = Array.isArray(record.resolutionSteps) ? record.resolutionSteps.map(String) : ["Review the highlighted fields and active OL Loan Setup limits.", "Retry the request or ask Loan Operations to review the policy configuration."]
  return { message: error instanceof Error ? error.message : String(record.message || "The loan request could not be submitted."), resolutionSteps, fieldErrors }
}

function estimateMonthlyPayment(amount: string, termMonths: number): string | null {
  const principal = Number(amount)
  if (!Number.isFinite(principal) || principal <= 0 || !termMonths) return null
  return (principal / termMonths).toFixed(2)
}

export function LoanRequestModal({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: (loanId: string) => void }) {
  const [step, setStep] = useState(1)
  const [search, setSearch] = useState("")
  const [policy, setPolicy] = useState<PolicyListItem | null>(null)
  const [amount, setAmount] = useState("")
  const [termMonths, setTermMonths] = useState(12)
  const [repaymentMode, setRepaymentMode] = useState("")
  const [reason, setReason] = useState("")
  const [amountError, setAmountError] = useState("")
  const [submissionError, setSubmissionError] = useState<RequestModalError | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const policyQuery = useQuery({
    queryKey: ["ol-loans", "request-policy-search", search],
    queryFn: () => listPolicies({ search, page: 1, pageSize: 10 }),
    enabled: open && step === 1,
    staleTime: 30_000,
  })
  const eligibilityQuery = usePolicyLoanEligibility(policy?.id, undefined, open && Boolean(policy))
  const modeQuery = useLoanOptions("repayment-terms", {}, open && step === 2)
  const policies = policyQuery.data?.results ?? []
  const backendModes = eligibilityQuery.data?.repaymentModes ?? []
  const modeOptions = useMemo(() => backendModes.length > 0 ? backendModes.map((value) => ({ value, label: value === "DEDUCTION_FROM_MATURITY" ? "Deduction from maturity" : value.split("_").join(" ").toLowerCase().replace(/(^| )\\w/g, (letter: string) => letter.toUpperCase()) })) : modeQuery.data?.results ?? [], [backendModes, modeQuery.data?.results])
  const maxAmount = eligibilityQuery.data?.maximumLoanAmount || eligibilityQuery.data?.availableLoanLimit || "0.00"
  const minAmount = eligibilityQuery.data?.minimumLoanAmount || "0.00"
  const monthlyEstimate = estimateMonthlyPayment(amount, termMonths)

  useEffect(() => {
    if (open) return
    setStep(1); setSearch(""); setPolicy(null); setAmount(""); setTermMonths(12); setRepaymentMode(""); setReason(""); setAmountError(""); setSubmissionError(null); setSubmitting(false)
  }, [open])

  useEffect(() => {
    if (!repaymentMode && modeOptions.length > 0) setRepaymentMode(modeOptions[0].value)
  }, [modeOptions, repaymentMode])

  const selectPolicy = (selected: PolicyListItem) => {
    setPolicy(selected)
    setAmount("")
    setAmountError("")
    setSubmissionError(null)
    setStep(2)
  }

  const validateAmount = () => {
    const value = Number(amount)
    const maximum = Number(maxAmount)
    const minimum = Number(minAmount)
    if (!amount || !Number.isFinite(value) || value <= 0) return "Enter a requested amount greater than zero."
    if (minimum > 0 && value < minimum) return `Enter at least ${minAmount} ${eligibilityQuery.data?.currency || policy?.currency || "TZS"}.`
    if (Number.isFinite(maximum) && value > maximum) return "Loan amount exceeds available cash value limit."
    return ""
  }

  const next = () => {
    setSubmissionError(null)
    if (step === 1 && policy) return setStep(2)
    if (step === 2) {
      if (!eligibilityQuery.data?.eligible) {
        setSubmissionError({ message: eligibilityQuery.data?.message || "Policy is not eligible for loans.", resolutionSteps: eligibilityQuery.data?.resolutionSteps || ["Select an Active or Paid-up policy with loans enabled.", "Review the active OL Loan Setup configuration."], fieldErrors: {} })
        return
      }
      const error = validateAmount()
      if (error) {
        setAmountError(error)
        setSubmissionError({ message: error, resolutionSteps: ["Reduce the requested amount to the available loan limit.", "Review the policy cash value and active OL Loan Setup parameters."], fieldErrors: { requested_amount: [error] } })
        return
      }
      if (!termMonths || !repaymentMode || !reason.trim()) {
        setSubmissionError({ message: "Complete all required loan details before continuing.", resolutionSteps: ["Choose a loan term and repayment mode.", "Enter a clear reason for the request."], fieldErrors: { reason: !reason.trim() ? ["Explain why the policyholder is requesting the loan."] : [] } })
        return
      }
      return setStep(3)
    }
  }

  const submit = async () => {
    if (!policy) return
    const error = validateAmount()
    if (error) { setAmountError(error); setStep(2); return }
    if (!reason.trim()) { setSubmissionError({ message: "A reason is required for every loan request.", resolutionSteps: ["Explain why the policyholder is requesting the loan.", "Return to Loan Details and complete the highlighted field."], fieldErrors: { reason: ["Enter a reason before submitting."] } }); setStep(2); return }
    setSubmitting(true); setSubmissionError(null)
    try {
      const result = await createLoanRequest(policy.id, { requestedAmount: amount, termMonths, repaymentMode, reason: reason.trim() }, `ol-loan-request:${policy.id}:${Date.now()}`)
      const createdId = result.loan?.id || (typeof result.id === "string" ? result.id : "")
      if (!createdId) throw new Error("The backend did not return the created loan identifier.")
      onCreated(createdId)
    } catch (error) {
      const parsed = readRequestError(error)
      setSubmissionError(parsed)
      setAmountError(parsed.fieldErrors.requested_amount?.[0] || parsed.fieldErrors.amount?.[0] || "")
      setStep(2)
    } finally {
      setSubmitting(false)
    }
  }

  const requestErrorCoach = submissionError && <ErrorCoach title={submissionError.message === "Loan amount exceeds available cash value limit." ? submissionError.message : "Loan request needs attention"} message={submissionError.message} resolutionSteps={submissionError.resolutionSteps} />
  return <Modal open={open} title="Request Loan" onClose={onClose}>
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2" aria-label="Loan request steps">{["Select Policy", "Loan Details", "Summary & Submit"].map((label, index) => <div key={label} className={`flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-bold ${step === index + 1 ? "bg-[var(--primary)] text-[var(--primary-foreground)]" : step > index + 1 ? "bg-[var(--success)]/12 text-[var(--success)]" : "bg-[var(--muted)] text-[var(--muted-foreground)]"}`}><span>{index + 1}</span>{label}</div>)}</div>
      {requestErrorCoach}
      {step === 1 && <div className="space-y-4"><div><h3 className="text-base font-bold">Select Policy</h3><p className="mt-1 text-sm leading-6 text-[var(--muted-foreground)]">Search policies to review their current loan eligibility. Policy status and product rules are rechecked by the backend.</p></div><label className="block space-y-1.5"><span className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Search policies</span><span className="relative block"><Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)]" aria-hidden="true" /><input autoFocus value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Policy number, policyholder, or product" className="h-10 w-full rounded-[10px] border border-[var(--border)] bg-[var(--card)] pl-9 pr-3 text-sm outline-none focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)]" /></span></label>{policyQuery.error && <ErrorCoach title="Policies could not be loaded" message={policyQuery.error.message} resolutionSteps={["Confirm that the policy service is available.", "Search again or ask servicing support to verify policy access."]} />}<div className="max-h-72 space-y-2 overflow-y-auto" aria-live="polite">{policyQuery.isLoading && <div className="rounded-lg border border-dashed border-[var(--border)] px-4 py-8 text-center text-sm text-[var(--muted-foreground)]">Loading policies…</div>}{!policyQuery.isLoading && !policyQuery.error && policies.length === 0 && <div className="rounded-lg border border-dashed border-[var(--border)] px-4 py-8 text-center text-sm text-[var(--muted-foreground)]">No policies match this search.</div>}{policies.map((item) => <button key={item.id} type="button" onClick={() => selectPolicy(item)} className="flex w-full items-start justify-between gap-3 rounded-lg border border-[var(--border)] bg-[var(--card)] px-3 py-3 text-left transition hover:border-[var(--primary)] hover:bg-[var(--secondary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"><span className="min-w-0"><span className="block truncate text-sm font-bold">{item.policyNumber}</span><span className="mt-1 block truncate text-xs text-[var(--muted-foreground)]">{item.policyholderDisplay || item.policyholderName}</span><span className="mt-1 block truncate text-xs text-[var(--muted-foreground)]">{item.productPlanDisplay}</span></span><span className={`shrink-0 rounded-full px-2 py-1 text-[11px] font-bold ${item.status === "ACTIVE" || item.status === "PAID_UP" ? "bg-[var(--success)]/10 text-[var(--success)]" : "bg-[var(--warning)]/12 text-[var(--warning-foreground)]"}`}>{item.statusDisplay || item.status}</span></button>)}</div></div>}
      {step === 2 && policy && <div className="space-y-4"><div><h3 className="text-base font-bold">Loan Details</h3><p className="mt-1 text-sm leading-6 text-[var(--muted-foreground)]">{policy.policyNumber} · {policy.policyholderDisplay || policy.policyholderName}</p></div>{eligibilityQuery.isLoading && <div className="rounded-lg border border-dashed border-[var(--border)] px-4 py-4 text-sm text-[var(--muted-foreground)]">Calculating the available loan limit from the effective policy and OL Loan Setup parameters…</div>}{eligibilityQuery.error && <ErrorCoach title="Loan eligibility could not be calculated" message={eligibilityQuery.error.message} resolutionSteps={["Confirm the policy has an active cash-value and loan configuration.", "Retry the eligibility check or ask Loan Operations to review the policy."]} />}{eligibilityQuery.data && <div className={`rounded-lg border px-4 py-3 ${eligibilityQuery.data.eligible ? "border-[var(--success)]/30 bg-[var(--success)]/8" : "border-[var(--destructive)]/30 bg-[var(--destructive)]/8"}`}><p className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Available Loan Limit</p><p className="mt-1 text-lg font-bold"><MoneyCell value={eligibilityQuery.data.availableLoanLimit} currency={eligibilityQuery.data.currency} /></p><p className="mt-1 text-xs text-[var(--muted-foreground)]">Maximum permitted: <MoneyCell value={maxAmount} currency={eligibilityQuery.data.currency} /> · Cash value snapshot: <MoneyCell value={eligibilityQuery.data.cashValue} currency={eligibilityQuery.data.currency} /></p>{!eligibilityQuery.data.eligible && <p className="mt-2 text-sm font-semibold text-[var(--destructive)]">{eligibilityQuery.data.message || "Policy is not eligible for loans."}</p>}</div>}<div className="grid gap-4 sm:grid-cols-2"><label className="block space-y-1.5"><span className="text-xs font-bold">Requested Amount <span className="text-[var(--destructive)]">*</span></span><input inputMode="decimal" value={amount} onChange={(event) => { setAmount(event.target.value); setAmountError("") }} aria-invalid={Boolean(amountError)} className="h-10 w-full rounded-[10px] border border-[var(--border)] bg-[var(--card)] px-3 text-sm outline-none focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)]" placeholder={`Up to ${maxAmount}`} />{amountError && <span className="text-xs font-semibold text-[var(--destructive)]">{amountError}</span>}</label><SmartSelect entity="loan-term" name="term_months" label="Term" required value={String(termMonths)} onChange={(value) => setTermMonths(Number(value))} options={TERM_OPTIONS} allowCreate={false} /></div><SmartSelect entity="repayment-terms" name="repayment_mode" label="Repayment Mode" required value={repaymentMode} onChange={setRepaymentMode} options={modeOptions} allowCreate={false} error={submissionError?.fieldErrors.repayment_mode?.[0]} /><label className="block space-y-1.5"><span className="text-xs font-bold">Reason <span className="text-[var(--destructive)]">*</span></span><textarea value={reason} onChange={(event) => setReason(event.target.value)} rows={3} className="w-full rounded-[10px] border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm outline-none focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)]" placeholder="Explain why the policyholder is requesting this loan." />{submissionError?.fieldErrors.reason?.[0] && <span className="text-xs font-semibold text-[var(--destructive)]">{submissionError.fieldErrors.reason[0]}</span>}</label></div>}
      {step === 3 && policy && <div className="space-y-4"><div><h3 className="text-base font-bold">Summary & Submit</h3><p className="mt-1 text-sm leading-6 text-[var(--muted-foreground)]">Review the request before it is submitted for controlled approval.</p></div><dl className="grid gap-3 rounded-lg border border-[var(--border)] bg-[var(--muted)]/25 p-4 sm:grid-cols-2"><div><dt className="text-xs text-[var(--muted-foreground)]">Policy</dt><dd className="mt-1 text-sm font-bold">{policy.policyNumber}</dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Policyholder</dt><dd className="mt-1 text-sm font-bold">{policy.policyholderDisplay || policy.policyholderName}</dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Requested amount</dt><dd className="mt-1 text-sm font-bold"><MoneyCell value={amount} currency={eligibilityQuery.data?.currency || policy.currency} /></dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Term / repayment</dt><dd className="mt-1 text-sm font-bold">{termMonths} months · {repaymentMode.split("_").join(" ")}</dd></div><div className="sm:col-span-2"><dt className="text-xs text-[var(--muted-foreground)]">Reason</dt><dd className="mt-1 text-sm">{reason}</dd></div></dl><div className="rounded-lg border border-[var(--info)]/25 bg-[var(--info)]/8 px-4 py-3 text-sm"><p className="font-bold">Estimated Monthly Payment</p><p className="mt-1">{monthlyEstimate ? <MoneyCell value={monthlyEstimate} currency={eligibilityQuery.data?.currency || policy.currency} /> : "Not available until the servicing schedule is generated."}</p><p className="mt-1 text-xs text-[var(--muted-foreground)]">This is an indicative principal-only estimate; the approved schedule remains the source of truth.</p></div></div>}
      <div className="flex flex-wrap justify-between gap-2 border-t border-[var(--border)] pt-4"><button type="button" className="button-secondary" onClick={step === 1 ? onClose : () => setStep(step - 1)}>{step === 1 ? "Cancel" : "Back"}</button>{step < 3 ? <button type="button" className="button-primary" onClick={next} disabled={(step === 1 && !policy) || (step === 2 && (eligibilityQuery.isLoading || Boolean(eligibilityQuery.error)))}>Next</button> : <button type="button" className="button-primary" onClick={() => void submit()} disabled={submitting}>{submitting ? "Submitting…" : "Submit Request"}</button>}</div>
    </div>
  </Modal>
}

export default function OLLoans() {
  const navigate = useNavigate()
  const { access, hasPermission, isSuperAdmin } = useAccess()
  const { toast } = useToast()
  const [filters, setFilters] = useState<FilterValues>({})
  const [refreshKey, setRefreshKey] = useState(0)
  const [requestOpen, setRequestOpen] = useState(() => new URLSearchParams(window.location.search).get("request") === "1")
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
    { key: "policy_number", label: "Policy number", field: "policyNumber", sortable: true, render: (_value, row) => <button type="button" className="font-semibold text-[var(--primary)] underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]" onClick={() => navigate(`/ordinary-life/policies/${row.policyId ?? row.policyNumber}`)}>{row.policyNumber || row.policyDisplay || "—"}</button> },
    { key: "policyholder_name", label: "Policyholder", field: "policyholderName", sortable: true, render: (_value, row) => <div><span className="font-semibold">{row.policyholderName || row.partnerDisplay || "—"}</span><span className="mt-1 block text-xs text-[var(--muted-foreground)]">{row.partnerDisplay && row.partnerDisplay !== row.policyholderName ? row.partnerDisplay : ""}</span></div> },
    { key: "product", label: "Product", field: "productDisplay", sortable: true, render: (_value, row) => row.productDisplay || "—" },
    { key: "principal_amount", label: "Principal amount", field: "principalAmount", sortable: true, align: "right", render: (_value, row) => <MoneyCell value={row.principalAmount} currency={row.currency} /> },
    { key: "outstanding_balance", label: "Outstanding balance", field: "outstandingBalance", sortable: true, align: "right", render: (_value, row) => <ProgressCell principal={row.principalAmount} balance={row.outstandingBalance} currency={row.currency} /> },
    { key: "interest_rate", label: "Interest rate", field: "interestRate", sortable: true, align: "right", render: (_value, row) => `${row.interestRate || "0.00"}%` },
    { key: "disbursement_date", label: "Disbursement date", field: "disbursementDate", sortable: true, render: (value) => dateLabel(value as string | null) },
    { key: "state", label: "Status", field: "status", sortable: true, render: (_value, row) => <LoanStatusBadge status={row.status} statusDisplay={row.statusDisplay} /> },
  ], [navigate])

  const onLoanCreated = (loanId: string) => {
    setRequestOpen(false)
    setRefreshKey((value) => value + 1)
    toast({ tone: "success", title: "Loan Request Created", message: "Status: Pending Approval." })
    navigate(`/ordinary-life/loans/${loanId}`)
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
    <LoanRequestModal open={requestOpen} onClose={() => setRequestOpen(false)} onCreated={onLoanCreated} />
    <Modal open={Boolean(actionTarget)} title={`${actionLabel[activeAction]} loan`} onClose={() => setActionTarget(null)}>
      {actionTarget && <div className="space-y-4"><div className="rounded-lg border border-[var(--border)] bg-[var(--muted)]/35 p-4"><p className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Selected record</p><p className="mt-1 text-sm font-bold">{actionTarget.row.loanNumber}</p><p className="mt-1 text-xs text-[var(--muted-foreground)]">{actionTarget.row.policyholderName} · {actionTarget.row.productDisplay}</p><div className="mt-3 flex flex-wrap items-center gap-3 text-sm"><LoanStatusBadge status={actionTarget.row.status} statusDisplay={actionTarget.row.statusDisplay} /><MoneyCell value={actionTarget.row.outstandingBalance} currency={actionTarget.row.currency} label="Outstanding balance" /></div></div><p className="text-sm leading-6 text-[var(--muted-foreground)]">This action is allowed by the current backend status matrix. Open the loan detail workspace to complete the controlled form and confirmation step.</p><div className="flex justify-end gap-2 border-t border-[var(--border)] pt-4"><button type="button" className="button-secondary" onClick={() => setActionTarget(null)}>Cancel</button><button type="button" className="button-primary" onClick={() => { const id = actionTarget.row.id; const action = actionTarget.action; setActionTarget(null); navigate(`/ordinary-life/loans/${id}?action=${action}`) }}>Open loan detail</button></div></div>}
    </Modal>
  </div>
}

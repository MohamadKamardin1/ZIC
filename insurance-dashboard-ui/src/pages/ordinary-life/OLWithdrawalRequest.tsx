import { useEffect, useMemo, useState } from "react"
import { AlertTriangle, ArrowLeft, ArrowRight, CheckCircle2, Search, ShieldCheck } from "lucide-react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { ErrorCoach } from "../../components/ErrorCoach"
import { ImpactAlert, MoneyCell } from "../../components/withdrawals/WithdrawalPrimitives"
import { MasterDetailPage } from "../../components/ui/Patterns"
import { useToast } from "../../components/ui/Toast"
import { formatMoney } from "../../lib/commitmentsDisplay"
import {
  useEstimateWithdrawalMutation,
  useRequestWithdrawalMutation,
  useWithdrawalEligibility,
  useWithdrawalOptions,
} from "../../lib/withdrawalsHooks"
import type { WithdrawalOption } from "../../lib/withdrawals"

type FormError = { message: string; resolutionSteps: string[]; fieldErrors: Record<string, string[]> }

function readError(error: unknown): FormError {
  const record = error && typeof error === "object" ? error as Record<string, unknown> : {}
  const fieldErrors = record.fieldErrors && typeof record.fieldErrors === "object" ? record.fieldErrors as Record<string, string[]> : {}
  const resolutionSteps = Array.isArray(record.resolutionSteps) ? record.resolutionSteps.map(String) : ["Review the highlighted fields and the active OL Withdrawal Setup parameters.", "Retry the request or ask Withdrawal Operations to review the policy configuration."]
  return { message: error instanceof Error ? error.message : String(record.message ?? "The withdrawal request could not be submitted."), resolutionSteps, fieldErrors }
}

function amountNumber(value: string): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

function formatPolicyStatus(value: string): string {
  return value.replace(/[_-]+/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function WizardStep({ number, label, active, completed }: { number: number; label: string; active: boolean; completed: boolean }) {
  return <div className={`flex items-center gap-2 rounded-full px-3 py-2 text-xs font-bold ${active ? "bg-[var(--primary)] text-[var(--primary-foreground)]" : completed ? "bg-emerald-100 text-emerald-800" : "bg-[var(--muted)] text-[var(--muted-foreground)]"}`}><span className="flex h-5 w-5 items-center justify-center rounded-full bg-white/80 text-[var(--foreground)]">{completed ? <CheckCircle2 size={14} aria-label="Completed" /> : number}</span>{label}</div>
}

export default function OLWithdrawalRequest() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const initialPolicyId = searchParams.get("policy_id") ?? ""
  const { toast } = useToast()
  const [step, setStep] = useState(1)
  const [search, setSearch] = useState("")
  const [selectedPolicy, setSelectedPolicy] = useState<WithdrawalOption | null>(null)
  const [amount, setAmount] = useState("")
  const [reason, setReason] = useState("")
  const [amountError, setAmountError] = useState("")
  const [reasonError, setReasonError] = useState("")
  const [submissionError, setSubmissionError] = useState<FormError | null>(null)

  const policyParams = useMemo(() => ({ q: search, page: 1, pageSize: 10 }), [search])
  const policyQuery = useWithdrawalOptions("policies", policyParams)
  const eligibilityQuery = useWithdrawalEligibility(selectedPolicy?.value, undefined, Boolean(selectedPolicy))
  const estimateMutation = useEstimateWithdrawalMutation()
  const requestMutation = useRequestWithdrawalMutation()
  const policyOptions = policyQuery.data?.results ?? []
  const eligibility = eligibilityQuery.data
  const estimate = estimateMutation.data
  const availableLimit = eligibility?.availableLimit ?? "0.00"
  const currency = eligibility?.currency ?? String(selectedPolicy?.meta?.currency ?? "TZS")
  const hasLoanBalance = amountNumber(eligibility?.loanBalance ?? "0") > 0

  useEffect(() => {
    if (!initialPolicyId || selectedPolicy || !policyOptions.length) return
    const matching = policyOptions.find((option) => option.value === initialPolicyId)
    if (matching) setSelectedPolicy(matching)
  }, [initialPolicyId, policyOptions, selectedPolicy])

  useEffect(() => {
    const requested = amountNumber(amount)
    const maximum = amountNumber(availableLimit)
    if (!selectedPolicy || !eligibility?.eligible || !requested || requested > maximum) {
      estimateMutation.reset()
      return
    }
    const timer = window.setTimeout(() => estimateMutation.mutate({ policyId: selectedPolicy.value, amount }), 350)
    return () => window.clearTimeout(timer)
  }, [amount, availableLimit, eligibility?.eligible, estimateMutation, selectedPolicy])

  const selectPolicy = (option: WithdrawalOption) => {
    setSelectedPolicy(option)
    setAmount("")
    setReason("")
    setAmountError("")
    setReasonError("")
    setSubmissionError(null)
    setStep(1)
  }

  const validateAmount = () => {
    const requested = amountNumber(amount)
    const maximum = amountNumber(availableLimit)
    if (!amount || requested <= 0) return "Enter a requested amount greater than zero."
    if (requested > maximum) return "Amount exceeds available cash value limit."
    return ""
  }

  const next = () => {
    setSubmissionError(null)
    if (step === 1) {
      if (!selectedPolicy) {
        setSubmissionError({ message: "Select a policy before continuing.", resolutionSteps: ["Search active policies.", "Choose the policy you want to service."], fieldErrors: {} })
        return
      }
      if (eligibilityQuery.isLoading) return
      if (eligibilityQuery.error || !eligibility?.eligible) {
        const message = eligibility?.message || "Policy is not eligible for withdrawals."
        setSubmissionError({ message, resolutionSteps: eligibility?.resolutionSteps ?? ["Select an Active or Paid-up policy.", "Review the policy lifecycle status before requesting a withdrawal."], fieldErrors: {} })
        return
      }
      setStep(2)
      return
    }
    if (step === 2) {
      const nextAmountError = validateAmount()
      const nextReasonError = reason.trim() ? "" : "Enter a reason before submitting the withdrawal request."
      setAmountError(nextAmountError)
      setReasonError(nextReasonError)
      if (nextAmountError || nextReasonError) {
        setSubmissionError({ message: nextAmountError || nextReasonError, resolutionSteps: ["Enter an amount at or below the Available Limit.", "Explain why the policyholder is requesting the withdrawal."], fieldErrors: { ...(nextAmountError ? { amount: [nextAmountError] } : {}), ...(nextReasonError ? { reason: [nextReasonError] } : {}) } })
        return
      }
      setStep(3)
    }
  }

  const submit = async () => {
    if (!selectedPolicy) return
    const nextAmountError = validateAmount()
    const nextReasonError = reason.trim() ? "" : "Enter a reason before submitting the withdrawal request."
    setAmountError(nextAmountError)
    setReasonError(nextReasonError)
    if (nextAmountError || nextReasonError) {
      setStep(nextAmountError ? 2 : 2)
      setSubmissionError({ message: nextAmountError || nextReasonError, resolutionSteps: ["Correct the highlighted request details.", "Confirm the amount is within the Available Limit."], fieldErrors: { ...(nextAmountError ? { amount: [nextAmountError] } : {}), ...(nextReasonError ? { reason: [nextReasonError] } : {}) } })
      return
    }
    setSubmissionError(null)
    try {
      const result = await requestMutation.mutateAsync({ policyId: selectedPolicy.value, payload: { amount, reason: reason.trim() }, idempotencyKey: `ol-withdrawal-request:${selectedPolicy.value}:${Date.now()}` })
      const withdrawalId = result.withdrawal?.id || (typeof result.id === "string" ? result.id : "")
      if (!withdrawalId) throw new Error("The backend did not return the created withdrawal identifier.")
      toast({ tone: "success", title: "Withdrawal Request Submitted", message: "Status: Pending Approval." })
      navigate(`/ordinary-life/withdrawals/${withdrawalId}`)
    } catch (error) {
      const parsed = readError(error)
      setSubmissionError(parsed)
      setAmountError(parsed.fieldErrors.amount?.[0] ?? "")
      setReasonError(parsed.fieldErrors.reason?.[0] ?? "")
      setStep(2)
    }
  }

  const estimatedFee = estimate?.estimatedFee ?? "0.00"
  const estimatedNet = estimate?.estimatedNetPayout ?? (amount ? (amountNumber(amount) * 0.95).toFixed(2) : "0.00")

  return <div className="space-y-5 p-1 md:p-2">
    <MasterDetailPage eyebrow="Ordinary Life / Servicing" title="Request Withdrawal" description="Submit a controlled policy withdrawal request. Eligibility, available cash value, fees, and policy impact are calculated from backend policy and OL parameter data." actions={<button type="button" className="button-secondary inline-flex items-center gap-2" onClick={() => navigate("/ordinary-life/withdrawals")}><ArrowLeft size={16} aria-hidden="true" />Back to Withdrawals</button>}>
      <section className="surface-card p-4" aria-label="Withdrawal request steps"><div className="flex flex-wrap gap-2"><WizardStep number={1} label="Select Policy" active={step === 1} completed={step > 1} /><WizardStep number={2} label="Amount & Fees" active={step === 2} completed={step > 2} /><WizardStep number={3} label="Summary & Impact" active={step === 3} completed={false} /></div></section>
      {submissionError && <ErrorCoach title="Withdrawal request needs attention" message={submissionError.message} resolutionSteps={submissionError.resolutionSteps} />}
      {step === 1 && <section className="surface-card space-y-5 p-5" aria-labelledby="withdrawal-policy-heading"><div><h2 id="withdrawal-policy-heading" className="text-lg font-extrabold">Select Policy</h2><p className="mt-1 text-sm leading-6 text-[var(--muted-foreground)]">Only policies returned by the backend policy service are shown. Eligibility is rechecked before you continue.</p></div><label className="block space-y-1.5"><span className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Search active policies</span><span className="relative block"><Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)]" aria-hidden="true" /><input autoFocus value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Policy number or policyholder" className="h-10 w-full rounded-[10px] border bg-[var(--card)] pl-9 pr-3 text-sm outline-none focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)]" /></span></label>{policyQuery.error && <ErrorCoach title="Policy search needs attention" message={policyQuery.error.message} resolutionSteps={["Confirm the policy service is available.", "Search again or ask servicing support to verify access."]} />}<div className="max-h-72 space-y-2 overflow-y-auto" aria-live="polite">{policyQuery.isLoading && <div className="rounded-lg border border-dashed px-4 py-8 text-center text-sm text-[var(--muted-foreground)]">Loading active policies…</div>}{!policyQuery.isLoading && !policyQuery.error && policyOptions.length === 0 && <div className="rounded-lg border border-dashed px-4 py-8 text-center text-sm text-[var(--muted-foreground)]">No eligible policy matches this search.</div>}{policyOptions.map((option) => <button key={option.value} type="button" onClick={() => selectPolicy(option)} className={`flex w-full items-start justify-between gap-3 rounded-lg border px-4 py-3 text-left transition hover:border-[var(--primary)] hover:bg-[var(--secondary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] ${selectedPolicy?.value === option.value ? "border-[var(--primary)] bg-[var(--primary)]/5" : "bg-[var(--card)]"}`}><span className="min-w-0"><span className="block truncate text-sm font-bold">{option.label}</span><span className="mt-1 block text-xs text-[var(--muted-foreground)]">Cash Value: <MoneyCell value={option.meta?.cash_value as string | number | undefined} currency={String(option.meta?.currency ?? "TZS")} /> · Loan Balance: <MoneyCell value={option.meta?.loan_balance as string | number | undefined} currency={String(option.meta?.currency ?? "TZS")} /></span></span><span className="shrink-0 rounded-full bg-emerald-100 px-2 py-1 text-[11px] font-bold text-emerald-800">{formatPolicyStatus(String(option.meta?.status ?? "Active"))}</span></button>)}</div>{selectedPolicy && <div className="rounded-[10px] border border-[var(--info)]/25 bg-[var(--info)]/8 p-4" aria-live="polite">{eligibilityQuery.isLoading && <p className="text-sm text-[var(--muted-foreground)]">Calculating Available Limit from current Cash Value and Active Loans…</p>}{eligibilityQuery.error && <ErrorCoach title="Withdrawal eligibility could not be calculated" message={eligibilityQuery.error.message} resolutionSteps={["Confirm this policy has a current cash-value record.", "Retry eligibility or ask Policy Servicing to review the policy."]} />}{eligibility && <><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Available Limit</p><p className="mt-1 text-2xl font-extrabold"><MoneyCell value={eligibility.availableLimit} currency={currency} /></p></div><span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-bold ${eligibility.eligible ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"}`}>{eligibility.eligible ? <ShieldCheck size={14} aria-hidden="true" /> : <AlertTriangle size={14} aria-hidden="true" />}{eligibility.eligible ? "Eligible" : "Not eligible"}</span></div><p className="mt-2 text-xs text-[var(--muted-foreground)]">Cash Value <MoneyCell value={eligibility.cashValue} currency={currency} /> less Loan Balance <MoneyCell value={eligibility.loanBalance} currency={currency} />.</p>{hasLoanBalance && eligibility.eligible && <div className="mt-3 flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-950"><AlertTriangle size={16} className="mt-0.5 shrink-0" aria-hidden="true" /><span>Active loan reduces available withdrawal limit.</span></div>}{!eligibility.eligible && <p className="mt-3 text-sm font-semibold text-[var(--destructive)]">{eligibility.message || "Policy is not eligible for withdrawals."}</p>}</>}</div>}</section>}
      {step === 2 && selectedPolicy && <section className="surface-card space-y-5 p-5" aria-labelledby="withdrawal-amount-heading"><div><h2 id="withdrawal-amount-heading" className="text-lg font-extrabold">Amount & Fees</h2><p className="mt-1 text-sm leading-6 text-[var(--muted-foreground)]">{selectedPolicy.label} · Available Limit <MoneyCell value={availableLimit} currency={currency} /></p></div><div className="grid gap-4 sm:grid-cols-2"><label className="block space-y-1.5"><span className="text-xs font-bold">Requested Amount <span className="text-[var(--destructive)]">*</span></span><input inputMode="decimal" value={amount} onChange={(event) => { setAmount(event.target.value); setAmountError(""); setSubmissionError(null) }} aria-invalid={Boolean(amountError)} placeholder={`Up to ${availableLimit}`} className="h-11 w-full rounded-[10px] border bg-[var(--card)] px-3 text-sm outline-none focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)]" />{amountError && <span className="text-xs font-semibold text-[var(--destructive)]">{amountError}</span>}</label><div className="rounded-[10px] border bg-[var(--muted)]/30 p-3"><p className="text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">Estimated Fee</p><p className="mt-2 text-lg font-extrabold"><MoneyCell value={estimatedFee} currency={currency} /></p><p className="mt-1 text-xs text-[var(--muted-foreground)]">{estimate?.feeBasis ?? `${eligibility?.feeRate ?? "5.0000"}% configured withdrawal fee`}</p></div></div><label className="block space-y-1.5"><span className="text-xs font-bold">Reason <span className="text-[var(--destructive)]">*</span></span><textarea value={reason} onChange={(event) => { setReason(event.target.value); setReasonError(""); setSubmissionError(null) }} rows={4} aria-invalid={Boolean(reasonError)} placeholder="Explain why the policyholder is requesting this withdrawal." className="w-full rounded-[10px] border bg-[var(--card)] px-3 py-2 text-sm outline-none focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)]" />{reasonError && <span className="text-xs font-semibold text-[var(--destructive)]">{reasonError}</span>}</label><div className="rounded-[10px] border border-emerald-200 bg-emerald-50 p-4 text-emerald-950"><p className="text-xs font-bold uppercase tracking-[0.08em]">Estimated Net Payout</p><p className="mt-1 text-2xl font-extrabold"><MoneyCell value={estimatedNet} currency={currency} /></p><p className="mt-1 text-xs">Gross amount less the backend-estimated fee.</p></div>{estimateMutation.error && <ErrorCoach title="Fee estimate needs attention" message={estimateMutation.error.message} resolutionSteps={["Confirm the requested amount is within the Available Limit.", "Retry the estimate after correcting the amount."]} />}</section>}
      {step === 3 && selectedPolicy && <section className="surface-card space-y-5 p-5" aria-labelledby="withdrawal-summary-heading"><div><h2 id="withdrawal-summary-heading" className="text-lg font-extrabold">Summary & Impact</h2><p className="mt-1 text-sm leading-6 text-[var(--muted-foreground)]">Review the transaction before submitting it for controlled approval.</p></div><dl className="grid gap-4 rounded-[10px] border bg-[var(--muted)]/25 p-4 sm:grid-cols-2"><div><dt className="text-xs text-[var(--muted-foreground)]">Policy</dt><dd className="mt-1 text-sm font-bold">{selectedPolicy.label}</dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Policy status</dt><dd className="mt-1 text-sm font-bold">{formatPolicyStatus(eligibility?.policyStatus ?? "Active")}</dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Gross amount</dt><dd className="mt-1 text-sm font-bold"><MoneyCell value={amount} currency={currency} /></dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Estimated fee</dt><dd className="mt-1 text-sm font-bold"><MoneyCell value={estimatedFee} currency={currency} /></dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Estimated net payout</dt><dd className="mt-1 text-sm font-bold"><MoneyCell value={estimatedNet} currency={currency} /></dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Reason</dt><dd className="mt-1 text-sm">{reason}</dd></div></dl><ImpactAlert grossAmount={amount} currency={currency} message={`Policy Cash Value will be reduced by ${formatMoney(amount, currency)}.`} /><div className="rounded-[10px] border border-[var(--info)]/25 bg-[var(--info)]/8 px-4 py-3 text-sm"><p className="font-bold">Submission checks</p><p className="mt-1 text-[var(--muted-foreground)]">The backend will revalidate policy status, available cash value, active loan balances, fees, permissions, and duplicate submission protection.</p></div></section>}
      <div className="flex flex-wrap justify-between gap-3"><button type="button" className="button-secondary inline-flex items-center gap-2" onClick={() => step === 1 ? navigate("/ordinary-life/withdrawals") : setStep((current) => current - 1)}><ArrowLeft size={16} aria-hidden="true" />{step === 1 ? "Cancel" : "Back"}</button>{step < 3 ? <button type="button" className="button-primary inline-flex items-center gap-2" onClick={next} disabled={step === 1 && (eligibilityQuery.isLoading || Boolean(eligibilityQuery.error))}>Continue<ArrowRight size={16} aria-hidden="true" /></button> : <button type="button" className="button-primary inline-flex items-center gap-2" onClick={() => void submit()} disabled={requestMutation.isPending}> {requestMutation.isPending ? "Submitting…" : "Submit Request"}<CheckCircle2 size={16} aria-hidden="true" /></button>}</div>
    </MasterDetailPage>
  </div>
}

import { useMemo, useState } from "react"
import { AlertTriangle, Banknote, HandCoins } from "lucide-react"
import { ErrorCoach } from "../../components/commitments/ErrorCoach"
import { DecimalInput, TextInput, TextareaInput } from "../../components/ui/FormControls"
import { InfoBanner, Modal } from "../../components/ui/Overlays"
import { useToast } from "../../components/ui/Toast"
import { renderFk } from "../../lib/display"
import { dateLabel } from "../../lib/commitmentsDisplay"
import { useRequestPolicyLoanMutation, useRequestPolicyWithdrawalMutation } from "../../lib/policiesHooks"
import type { PolicyDetail } from "../../lib/policies"

function numberValue(value: unknown, fallback = 0) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

function rowValue(row: Record<string, unknown>, ...keys: string[]) {
  for (const key of keys) if (row[key] !== undefined && row[key] !== null && row[key] !== "") return row[key]
  return null
}

function money(value: unknown, currency: string) {
  const amount = numberValue(value)
  return new Intl.NumberFormat("en-TZ", { style: "currency", currency, maximumFractionDigits: 2 }).format(amount)
}

function statusTone(status: string): "success" | "warning" | "danger" | "info" | "neutral" {
  const value = status.toUpperCase()
  if (["DISBURSED", "APPROVED", "PAID", "REPAID"].includes(value)) return "success"
  if (["REQUESTED", "PENDING"].includes(value)) return "warning"
  if (["REJECTED", "CANCELLED"].includes(value)) return "danger"
  return "neutral"
}

function eligibility(policy: PolicyDetail, loans: Record<string, unknown>[], withdrawals: Record<string, unknown>[]) {
  const snapshot = policy.contractSnapshot
  const cashValue = numberValue(snapshot.cash_value)
  const loanBalance = loans.reduce((total, row) => total + numberValue(row.outstanding_principal) + numberValue(row.outstanding_interest), 0)
  const priorWithdrawals = numberValue(snapshot.withdrawals_total) || withdrawals.reduce((total, row) => total + numberValue(row.amount), 0)
  const maxLoanPercent = numberValue(snapshot.max_loan_percentage_of_cash_value ?? snapshot.max_loan_percentage ?? snapshot.loan_max_percentage, 0)
  const availableLoanLimit = Math.max(0, cashValue * maxLoanPercent / 100 - loanBalance)
  const availableWithdrawal = Math.max(0, cashValue - loanBalance - priorWithdrawals)
  return { cashValue, loanBalance, priorWithdrawals, maxLoanPercent, availableLoanLimit, availableWithdrawal }
}

function LoanRequestModal({ open, policy, availableLimit, onClose }: { open: boolean; policy: PolicyDetail; availableLimit: number; onClose: () => void }) {
  const { toast } = useToast()
  const [amount, setAmount] = useState("")
  const [reason, setReason] = useState("")
  const [error, setError] = useState("")
  const mutation = useRequestPolicyLoanMutation()
  const submit = () => {
    const value = numberValue(amount)
    if (value <= 0) return setError("Enter a loan amount greater than zero.")
    if (value > availableLimit) return setError(`The requested amount exceeds the available loan limit of ${money(availableLimit, policy.currency)}. Reduce the amount or review the policy cash value.`)
    setError("")
    mutation.mutate({ id: policy.id, payload: { amount, reason: reason.trim() || "Policy loan request." } }, { onSuccess: () => { toast({ title: "Loan request submitted", message: "The policy loan request was recorded for processing.", tone: "success" }); onClose() } })
  }
  return <Modal open={open} title="Request policy loan" description="Request a loan against the policy’s eligible cash value." onClose={onClose} footer={<><button type="button" className="button-secondary" onClick={onClose} disabled={mutation.isPending}>Cancel</button><button type="button" className="button-primary" onClick={submit} disabled={mutation.isPending}>{mutation.isPending ? "Submitting…" : "Request loan"}</button></>}>
    <div className="space-y-4"><InfoBanner title="Available loan limit">{money(availableLimit, policy.currency)} is available after the configured cash-value percentage and existing loan balances.</InfoBanner>{error && <p className="text-xs font-semibold text-[var(--destructive)]" role="alert">{error}</p>}{mutation.error ? <ErrorCoach error={mutation.error} title="Loan request could not be submitted" compact onRetry={submit} /> : null}<DecimalInput label="Loan amount" name="loan_amount" required value={amount} min="0" step="0.01" onChange={(event) => setAmount(event.target.value)} /><TextareaInput label="Reason" name="loan_reason" value={reason} hint="Optional context for the finance reviewer." onChange={(event) => setReason(event.target.value)} placeholder="Why is this loan being requested?" /></div>
  </Modal>
}

function WithdrawalRequestModal({ open, policy, availableCashValue, onClose }: { open: boolean; policy: PolicyDetail; availableCashValue: number; onClose: () => void }) {
  const { toast } = useToast()
  const [amount, setAmount] = useState("")
  const [reason, setReason] = useState("")
  const [error, setError] = useState("")
  const mutation = useRequestPolicyWithdrawalMutation()
  const submit = () => {
    const value = numberValue(amount)
    if (value <= 0) return setError("Enter a withdrawal amount greater than zero.")
    if (value > availableCashValue) return setError(`The requested amount exceeds available cash value of ${money(availableCashValue, policy.currency)}. Reduce the amount before submitting.`)
    setError("")
    mutation.mutate({ id: policy.id, payload: { amount, reason: reason.trim() || "Policy withdrawal request." } }, { onSuccess: () => { toast({ title: "Withdrawal request submitted", message: "The withdrawal request was recorded for processing.", tone: "success" }); onClose() } })
  }
  return <Modal open={open} title="Request withdrawal" description="Request a withdrawal from the policy’s available cash value." onClose={onClose} footer={<><button type="button" className="button-secondary" onClick={onClose} disabled={mutation.isPending}>Cancel</button><button type="button" className="button-primary" onClick={submit} disabled={mutation.isPending}>{mutation.isPending ? "Submitting…" : "Request withdrawal"}</button></>}>
    <div className="space-y-4"><InfoBanner title="Important">Withdrawals may reduce your Sum Assured.</InfoBanner><InfoBanner title="Available cash value">{money(availableCashValue, policy.currency)} remains available after loan balances and prior withdrawals.</InfoBanner>{error && <p className="text-xs font-semibold text-[var(--destructive)]" role="alert">{error}</p>}{mutation.error ? <ErrorCoach error={mutation.error} title="Withdrawal request could not be submitted" compact onRetry={submit} /> : null}<DecimalInput label="Withdrawal amount" name="withdrawal_amount" required value={amount} min="0" step="0.01" onChange={(event) => setAmount(event.target.value)} /><TextInput label="Reason" name="withdrawal_reason" value={reason} hint="Optional context for the finance reviewer." onChange={(event) => setReason(event.target.value)} placeholder="Why is this withdrawal being requested?" /></div>
  </Modal>
}

export default function PolicyFinancialsTab({ policy, loans, withdrawals, canRequestLoan, canRequestWithdrawal, loanModalOpen, withdrawalModalOpen, onLoanModalChange, onWithdrawalModalChange }: { policy: PolicyDetail; loans: Record<string, unknown>[]; withdrawals: Record<string, unknown>[]; canRequestLoan: boolean; canRequestWithdrawal: boolean; loanModalOpen: boolean; withdrawalModalOpen: boolean; onLoanModalChange: (open: boolean) => void; onWithdrawalModalChange: (open: boolean) => void }) {
  const [subTab, setSubTab] = useState<"loans" | "withdrawals">("loans")
  const values = useMemo(() => eligibility(policy, loans, withdrawals), [policy, loans, withdrawals])
  const lapsed = policy.status.toUpperCase() === "LAPSED"
  return <div className="space-y-4"><nav className="surface-card flex gap-1 p-1" aria-label="Financial sub-tabs"><button type="button" className={`rounded-[9px] px-4 py-2 text-sm font-bold ${subTab === "loans" ? "bg-[var(--primary)] text-[var(--primary-foreground)]" : "text-[var(--muted-foreground)]"}`} onClick={() => setSubTab("loans")}>Loans</button><button type="button" className={`rounded-[9px] px-4 py-2 text-sm font-bold ${subTab === "withdrawals" ? "bg-[var(--primary)] text-[var(--primary-foreground)]" : "text-[var(--muted-foreground)]"}`} onClick={() => setSubTab("withdrawals")}>Withdrawals</button></nav>
    {subTab === "loans" && <section className="surface-card p-4" aria-labelledby="loans-heading"><div className="mb-4 flex flex-wrap items-start justify-between gap-3"><div><h2 id="loans-heading" className="text-sm font-bold">Policy loans</h2><p className="mt-1 text-xs text-[var(--muted-foreground)]">Available limit: <strong>{money(values.availableLoanLimit, policy.currency)}</strong></p></div>{lapsed ? <div className="inline-flex items-center gap-2 text-xs font-semibold text-[var(--destructive)]"><AlertTriangle size={15} aria-hidden="true" />Loan requests are blocked while lapsed</div> : canRequestLoan && <button type="button" className="button-primary inline-flex items-center gap-2" onClick={() => onLoanModalChange(true)}><Banknote size={15} aria-hidden="true" />Request Loan</button>}</div>{lapsed && <ErrorCoach error={new Error("A lapsed policy cannot request a loan until it is reinstated.")} title="Loan request blocked" compact />}{loans.length ? <div className="overflow-x-auto"><table className="w-full min-w-[720px] text-left text-sm"><thead><tr className="border-b text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><th className="px-3 py-2">Loan number</th><th className="px-3 py-2 text-right">Amount</th><th className="px-3 py-2 text-right">Interest rate</th><th className="px-3 py-2 text-right">Balance</th><th className="px-3 py-2">Status</th><th className="px-3 py-2">Repayment view</th></tr></thead><tbody>{loans.map((loan, index) => { const loanNumber = rowValue(loan, "loan_number", "loanNumber"); const status = String(rowValue(loan, "status") ?? "—"); return <tr key={String(rowValue(loan, "id") ?? loanNumber ?? index)} className="border-b last:border-0"><td className="px-3 py-3 font-mono font-semibold">{renderFk(loanNumber)}</td><td className="px-3 py-3 text-right">{money(rowValue(loan, "principal_amount", "amount"), policy.currency)}</td><td className="px-3 py-3 text-right">{numberValue(rowValue(loan, "interest_rate")).toFixed(2)}%</td><td className="px-3 py-3 text-right">{money(numberValue(rowValue(loan, "outstanding_principal")) + numberValue(rowValue(loan, "outstanding_interest")), policy.currency)}</td><td className="px-3 py-3"><span className={`inline-flex rounded-full px-2 py-1 text-[11px] font-bold ${statusTone(status) === "success" ? "bg-[var(--success)]/15 text-[var(--success)]" : statusTone(status) === "warning" ? "bg-[var(--warning)]/15 text-[var(--warning)]" : statusTone(status) === "danger" ? "bg-[var(--destructive)]/15 text-[var(--destructive)]" : "bg-[var(--secondary)] text-[var(--muted-foreground)]"}`}>{renderFk(status)}</span></td><td className="px-3 py-3"><button type="button" className="button-secondary min-h-8 px-2.5 text-xs" onClick={() => onLoanModalChange(true)}>View repayments</button></td></tr> })}</tbody></table></div> : <InfoBanner title="No policy loans">No active or historical loans are linked to this policy.</InfoBanner>}</section>}
    {subTab === "withdrawals" && <section className="surface-card p-4" aria-labelledby="withdrawals-heading"><div className="mb-4 flex flex-wrap items-start justify-between gap-3"><div><h2 id="withdrawals-heading" className="text-sm font-bold">Withdrawals</h2><p className="mt-1 text-xs text-[var(--muted-foreground)]">Available cash value: <strong>{money(values.availableWithdrawal, policy.currency)}</strong></p></div>{canRequestWithdrawal && <button type="button" className="button-primary inline-flex items-center gap-2" onClick={() => onWithdrawalModalChange(true)}><HandCoins size={15} aria-hidden="true" />Request Withdrawal</button>}</div><InfoBanner title="Important">Withdrawals may reduce your Sum Assured.</InfoBanner>{withdrawals.length ? <div className="mt-4 overflow-x-auto"><table className="w-full min-w-[620px] text-left text-sm"><thead><tr className="border-b text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><th className="px-3 py-2">Request number</th><th className="px-3 py-2">Request date</th><th className="px-3 py-2 text-right">Amount</th><th className="px-3 py-2 text-right">Net amount</th><th className="px-3 py-2">Status</th></tr></thead><tbody>{withdrawals.map((withdrawal, index) => { const requestNumber = rowValue(withdrawal, "request_number", "requestNumber"); const status = String(rowValue(withdrawal, "status") ?? "—"); return <tr key={String(rowValue(withdrawal, "id") ?? requestNumber ?? index)} className="border-b last:border-0"><td className="px-3 py-3 font-mono font-semibold">{renderFk(requestNumber)}</td><td className="px-3 py-3">{dateLabel(String(rowValue(withdrawal, "request_date", "requestDate") ?? ""))}</td><td className="px-3 py-3 text-right">{money(rowValue(withdrawal, "amount"), policy.currency)}</td><td className="px-3 py-3 text-right">{money(rowValue(withdrawal, "net_amount", "netAmount"), policy.currency)}</td><td className="px-3 py-3"><span className="inline-flex rounded-full bg-[var(--secondary)] px-2 py-1 text-[11px] font-bold">{renderFk(status)}</span></td></tr> })}</tbody></table></div> : <div className="mt-4"><InfoBanner title="No withdrawals">No withdrawals are linked to this policy.</InfoBanner></div>}</section>}
    <LoanRequestModal open={loanModalOpen} policy={policy} availableLimit={values.availableLoanLimit} onClose={() => onLoanModalChange(false)} />
    <WithdrawalRequestModal open={withdrawalModalOpen} policy={policy} availableCashValue={values.availableWithdrawal} onClose={() => onWithdrawalModalChange(false)} />
  </div>
}

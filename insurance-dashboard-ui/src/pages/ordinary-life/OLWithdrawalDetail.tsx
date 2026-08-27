import { useState } from "react"
import { ArrowLeft, Clipboard, Check, FileText, RotateCcw, ShieldCheck, XCircle } from "lucide-react"
import { useNavigate, useParams, useSearchParams } from "react-router-dom"
import { DocumentInstancesPanel } from "../../components/documents/DocumentInstancesPanel"
import { ErrorCoach } from "../../components/ErrorCoach"
import Modal from "../../components/shared/Modal"
import { MasterDetailPage } from "../../components/ui/Patterns"
import { useToast } from "../../components/ui/Toast"
import { MoneyCell, WithdrawalMoneySummary, WithdrawalStatusBadge } from "../../components/withdrawals/WithdrawalPrimitives"
import { dateLabel } from "../../lib/commitmentsDisplay"
import { useAccess } from "../../lib/access"
import { useWithdrawalActionMutation, useWithdrawalAudit, useWithdrawalBreakdown, useWithdrawalDetail, useWithdrawalOptions, useWithdrawalPayments } from "../../lib/withdrawalsHooks"
import type { WithdrawalAction, WithdrawalAuditEntry, WithdrawalBreakdown, WithdrawalDetail, WithdrawalPayment } from "../../lib/withdrawals"

type DetailTab = "overview" | "breakdown" | "payments" | "documents" | "audit"
type ActionKey = "approve" | "reject" | "process_payout" | "cancel" | "reverse"

const TABS: Array<{ id: DetailTab; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "breakdown", label: "Breakdown" },
  { id: "payments", label: "Payments" },
  { id: "documents", label: "Documents" },
  { id: "audit", label: "Audit" },
]

const STATUS_ACTIONS: Record<string, ActionKey[]> = {
  REQUESTED: ["approve", "reject", "cancel"],
  APPROVED: ["process_payout", "cancel"],
  PROCESSING: ["cancel"],
  PAID: ["reverse"],
  REVERSED: [],
  DECLINED: [],
  CANCELLED: [],
}

const ACTION_LABELS: Record<ActionKey, string> = {
  approve: "Approve",
  reject: "Reject",
  process_payout: "Process Payout",
  cancel: "Cancel",
  reverse: "Reverse",
}

function safeText(value: unknown, fallback = "—"): string {
  return value === null || value === undefined || value === "" ? fallback : String(value)
}

function actionPermission(action: ActionKey): string {
  if (action === "approve" || action === "reject") return "ol_withdrawals.approve"
  if (action === "process_payout") return "ol_withdrawals.process_payout"
  if (action === "cancel") return "ol_withdrawals.cancel"
  return "ol_withdrawals.reverse"
}

function StatRow({ label, value }: { label: string; value: React.ReactNode }) {
  return <div className="flex flex-wrap items-start justify-between gap-3 border-b py-3 last:border-b-0"><dt className="text-sm text-[var(--muted-foreground)]">{label}</dt><dd className="text-right text-sm font-bold">{value}</dd></div>
}

function Timeline({ entries }: { entries: WithdrawalAuditEntry[] }) {
  if (!entries.length) return <p className="rounded-lg border border-dashed px-4 py-6 text-sm text-[var(--muted-foreground)]">No status timeline events have been recorded yet.</p>
  return <ol className="space-y-3" aria-label="Withdrawal status timeline">{entries.map((entry) => <li key={entry.id || `${entry.action}-${entry.createdAt}`} className="flex items-start gap-3"><span className="mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[var(--primary)]/10 text-[var(--primary)]"><Check size={14} aria-hidden="true" /></span><div className="min-w-0 flex-1 rounded-lg border px-3 py-2"><div className="flex flex-wrap items-center justify-between gap-2"><span className="text-sm font-bold">{safeText(entry.action)}</span><span className="text-xs text-[var(--muted-foreground)]">{dateLabel(entry.createdAt)}</span></div><p className="mt-1 text-xs text-[var(--muted-foreground)]">{safeText(entry.actorDisplay, "System")} · {safeText(entry.sourceChannel, "API")}</p>{entry.reason && <p className="mt-1 text-sm">{entry.reason}</p>}</div></li>)}</ol>
}

function BreakdownSection({ breakdown, currency }: { breakdown: WithdrawalBreakdown; currency: string }) {
  return <div className="space-y-5"><section className="rounded-[10px] border p-4"><h2 className="text-base font-extrabold">Withdrawal Calculation</h2><dl className="mt-3"><StatRow label="Cash Value Before" value={<MoneyCell value={breakdown.cashValueBefore} currency={currency} />} /><StatRow label="Gross Withdrawal" value={<MoneyCell value={breakdown.grossWithdrawal} currency={currency} />} /><StatRow label={`Withdrawal Fee${breakdown.feeBasis ? ` · ${breakdown.feeBasis}` : ""}`} value={<MoneyCell value={breakdown.withdrawalFee} currency={currency} />} /><StatRow label="Net Payout" value={<MoneyCell value={breakdown.netPayout} currency={currency} />} /><StatRow label="Cash Value After" value={<MoneyCell value={breakdown.cashValueAfter} currency={currency} />} /></dl></section><section className="rounded-[10px] border p-4"><h2 className="text-base font-extrabold">Policy Impact</h2><dl className="mt-3"><StatRow label="Sum Assured Before" value={<MoneyCell value={breakdown.sumAssuredBefore} currency={currency} />} /><StatRow label="Sum Assured After" value={<MoneyCell value={breakdown.sumAssuredAfter} currency={currency} />} /><StatRow label="Adjustment Ratio" value={breakdown.adjustmentRatio ? `${breakdown.adjustmentRatio}%` : "—"} /></dl></section>{breakdown.auditTrail.length > 0 && <section className="rounded-[10px] border p-4"><h2 className="text-base font-extrabold">Calculation Audit Trail</h2><ul className="mt-3 space-y-2">{breakdown.auditTrail.map((item, index) => <li key={`${String(item.action ?? "event")}-${index}`} className="rounded-lg bg-[var(--muted)]/30 px-3 py-2 text-sm">{safeText(item.action, "Calculation event")} · {safeText(item.actor_name, "System")} · {dateLabel(safeText(item.created_at, ""))}</li>)}</ul></section>}</div>
}

function PaymentsTable({ payments }: { payments: WithdrawalPayment[] }) {
  if (!payments.length) return <p className="rounded-lg border border-dashed px-4 py-8 text-center text-sm text-[var(--muted-foreground)]">No payout payment has been recorded for this withdrawal.</p>
  return <div className="overflow-x-auto"><table className="w-full min-w-[700px] text-left text-sm"><caption className="sr-only">Withdrawal payments</caption><thead className="bg-[var(--muted)]/45 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><tr><th scope="col" className="px-4 py-3">Payment mode</th><th scope="col" className="px-4 py-3">Receipt reference</th><th scope="col" className="px-4 py-3 text-right">Amount</th><th scope="col" className="px-4 py-3">Payment date</th><th scope="col" className="px-4 py-3">Status</th></tr></thead><tbody className="divide-y">{payments.map((payment) => <tr key={payment.id}><td className="px-4 py-3 font-semibold">{safeText(payment.paymentModeDisplay || payment.paymentMode)}</td><td className="px-4 py-3">{safeText(payment.receiptReference)}</td><td className="px-4 py-3 text-right"><MoneyCell value={payment.amount} currency={payment.currency} /></td><td className="px-4 py-3">{dateLabel(payment.paymentDate)}</td><td className="px-4 py-3"><WithdrawalStatusBadge status={payment.status} /></td></tr>)}</tbody></table></div>
}

function ActionDialog({ action, detail, open, onClose, permitted }: { action: ActionKey | null; detail: WithdrawalDetail; open: boolean; onClose: () => void; permitted: boolean }) {
  const actionMutation = useWithdrawalActionMutation()
  const paymentModeQuery = useWithdrawalOptions("payment-modes", {}, open && action === "process_payout")
  const { toast } = useToast()
  const [reason, setReason] = useState("")
  const [paymentMode, setPaymentMode] = useState("")
  const [receiptReference, setReceiptReference] = useState("")
  const [validationError, setValidationError] = useState("")
  const paymentModes = paymentModeQuery.data?.results ?? []

  const close = () => {
    if (actionMutation.isPending) return
    setReason("")
    setPaymentMode("")
    setReceiptReference("")
    setValidationError("")
    onClose()
  }

  const submit = async () => {
    if (!action || !permitted) return
    const needsReason = action !== "process_payout"
    if (needsReason && !reason.trim()) {
      const label = action === "reject" ? "Reason for Rejection" : action === "cancel" ? "Reason for Cancellation" : action === "reverse" ? "Reason for Reversal" : "Reason for approval"
      setValidationError(`${label} is required before you can continue.`)
      return
    }
    if (action === "process_payout" && (!paymentMode || !receiptReference.trim())) {
      setValidationError("Payment Mode and Receipt Reference are required before payout processing.")
      return
    }
    setValidationError("")
    try {
      const payload = action === "process_payout" ? { payment_mode: paymentMode, receipt_reference: receiptReference.trim() } : { reason: reason.trim() }
      const result = await actionMutation.mutateAsync({ id: detail.id, action: action as WithdrawalAction, payload, idempotencyKey: `ol-withdrawal:${action}:${detail.id}:${Date.now()}` })
      const fallbackStatus: Record<ActionKey, string> = { approve: "Approved", reject: "Rejected", process_payout: "Paid", cancel: "Cancelled", reverse: "Reversed" }
      const status = result.withdrawal?.statusDisplay || fallbackStatus[action]
      toast({ tone: "success", title: `${ACTION_LABELS[action]} withdrawal`, message: `Status updated to ${status}.` })
      close()
    } catch (caught) {
      setValidationError(caught instanceof Error ? caught.message : "The withdrawal action could not be completed.")
    }
  }

  const reasonLabel = action === "reject" ? "Reason for Rejection" : action === "cancel" ? "Reason for Cancellation" : action === "reverse" ? "Reason for Reversal" : "Reason for Approval"
  const submitLabel = action === "approve" ? "Confirm Approval" : action === "reject" ? "Reject" : action === "process_payout" ? "Confirm Payout Processed" : action === "cancel" ? "Cancel Request" : "Reverse Withdrawal"

  return <Modal open={open} title={`${action ? ACTION_LABELS[action] : "Withdrawal"} withdrawal`} onClose={close}><div className="space-y-4"><div className="rounded-lg border bg-[var(--muted)]/30 p-4"><p className="text-sm font-bold">{detail.withdrawalNumber}</p><p className="mt-1 text-xs text-[var(--muted-foreground)]">{detail.policyholderName} · {detail.policyNumber}</p><div className="mt-3 flex flex-wrap items-center gap-3"><WithdrawalStatusBadge status={detail.status} statusDisplay={detail.statusDisplay} /><MoneyCell value={detail.netPayout} currency={detail.currency} label="Net payout" /></div></div>{!permitted ? <ErrorCoach title="Action not permitted" message="Your access metadata does not include permission to perform this withdrawal action." resolutionSteps={["Close this dialog and return to the detail page.", "Ask an administrator for the required OL Withdrawals permission."]} /> : <><p className="text-sm leading-6 text-[var(--muted-foreground)]">Confirm the controlled {action ? ACTION_LABELS[action].toLowerCase() : "withdrawal"} action. The latest status, permission, and policy financial state will be validated again by the backend.</p>{action === "process_payout" && <div className="grid gap-4 sm:grid-cols-2"><label className="block space-y-1.5"><span className="text-xs font-bold">Payment Mode <span className="text-[var(--destructive)]">*</span></span><select value={paymentMode} onChange={(event) => { setPaymentMode(event.target.value); setValidationError("") }} aria-label="Payment Mode" className="h-11 w-full rounded-[10px] border bg-[var(--card)] px-3 text-sm outline-none focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)]"><option value="">Select payment mode</option>{paymentModes.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label><label className="block space-y-1.5"><span className="text-xs font-bold">Receipt Reference <span className="text-[var(--destructive)]">*</span></span><input value={receiptReference} onChange={(event) => { setReceiptReference(event.target.value); setValidationError("") }} aria-label="Receipt Reference" className="h-11 w-full rounded-[10px] border bg-[var(--card)] px-3 text-sm outline-none focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)]" placeholder="Front Office receipt reference" /></label></div>}{action === "process_payout" && <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-950">Net Payout to process: <strong><MoneyCell value={detail.netPayout} currency={detail.currency} /></strong></div>}{action === "reverse" && <div className="flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950"><RotateCcw size={16} className="mt-0.5 shrink-0" aria-hidden="true" /><span>This will restore the policy cash value. Are you sure?</span></div>}{action !== "process_payout" && action && <label className="block space-y-1.5" htmlFor={`withdrawal-action-reason-${action}`}><span className="text-xs font-bold">{reasonLabel} <span className="text-[var(--destructive)]">*</span></span><textarea id={`withdrawal-action-reason-${action}`} rows={4} value={reason} onChange={(event) => { setReason(event.target.value); setValidationError("") }} aria-invalid={Boolean(validationError)} className="w-full rounded-[10px] border bg-[var(--card)] px-3 py-2 text-sm outline-none focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)]" placeholder={`Enter ${reasonLabel.toLowerCase()}.`} /></label>}{validationError && <ErrorCoach title="Withdrawal action needs attention" message={validationError} resolutionSteps={["Complete every required action field.", "If the backend rejects the action, verify the withdrawal status and your permission."]} />}<div className="flex justify-end gap-2 border-t pt-4"><button type="button" className="button-secondary" onClick={close} disabled={actionMutation.isPending}>Cancel</button><button type="button" className="button-primary" onClick={() => void submit()} disabled={actionMutation.isPending}>{actionMutation.isPending ? "Submitting…" : submitLabel}</button></div></>}</div></Modal>
}

function OverviewTab({ detail, breakdown, audit }: { detail: WithdrawalDetail; breakdown: WithdrawalBreakdown | null; audit: WithdrawalAuditEntry[] }) {
  const context = detail.policyContext ?? {}
  return <div className="space-y-5"><section className="rounded-[10px] border p-4"><h2 className="text-base font-extrabold">Withdrawal Details</h2><dl className="mt-3"><StatRow label="Product" value={detail.productDisplay} /><StatRow label="Currency" value={detail.currency} /><StatRow label="Reason for Withdrawal" value={detail.reason} /></dl></section><section className="rounded-[10px] border p-4"><h2 className="text-base font-extrabold">Policy Context</h2><dl className="mt-3"><StatRow label="Cash Value Before" value={<MoneyCell value={breakdown?.cashValueBefore ?? detail.cashValueBefore} currency={detail.currency} />} /><StatRow label="Cash Value After" value={<MoneyCell value={breakdown?.cashValueAfter ?? detail.cashValueAfter} currency={detail.currency} />} /><StatRow label="Loan Balance Before" value={<MoneyCell value={detail.loanBalanceBefore} currency={detail.currency} />} /><StatRow label="Sum Assured Before" value={<MoneyCell value={breakdown?.sumAssuredBefore ?? context.sum_assured_before as string | undefined} currency={detail.currency} />} /><StatRow label="Sum Assured After" value={<MoneyCell value={breakdown?.sumAssuredAfter ?? context.sum_assured_after as string | undefined} currency={detail.currency} />} /></dl></section><section className="rounded-[10px] border p-4"><h2 className="text-base font-extrabold">Status Timeline</h2><div className="mt-3"><Timeline entries={audit} /></div></section></div>
}

export default function OLWithdrawalDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { access, hasPermission, isSuperAdmin } = useAccess()
  const { toast } = useToast()
  const [activeTab, setActiveTab] = useState<DetailTab>((searchParams.get("tab") as DetailTab) || "overview")
  const [copied, setCopied] = useState(false)
  const [action, setAction] = useState<ActionKey | null>((searchParams.get("action") as ActionKey) || null)
  const detailQuery = useWithdrawalDetail(id)
  const breakdownQuery = useWithdrawalBreakdown(id, Boolean(id))
  const paymentsQuery = useWithdrawalPayments(id, 1, 50, Boolean(id))
  const auditQuery = useWithdrawalAudit(id, 1, 100, Boolean(id))
  const detail = detailQuery.data

  const can = (permission: string) => {
    if (isSuperAdmin) return true
    const keys = access.permissions.map((item) => `${item.module}.${item.action}`.toLowerCase())
    return Boolean(hasPermission?.(permission) || keys.includes(permission.toLowerCase()))
  }

  if (detailQuery.isLoading || !detail) return <div className="p-5" role="status">Loading withdrawal detail…</div>
  if (detailQuery.error) return <div className="space-y-4 p-5"><ErrorCoach title="Withdrawal detail could not be loaded" message={detailQuery.error.message} resolutionSteps={["Return to the Withdrawals register and select an available request.", "Confirm the backend is running and your session has ol_withdrawals.view."]} /><button type="button" className="button-secondary inline-flex items-center gap-2" onClick={() => navigate("/ordinary-life/withdrawals")}><ArrowLeft size={16} aria-hidden="true" />Back to Withdrawals</button></div>

  const status = String(detail.status).toUpperCase()
  const backendActions = new Set(detail.allowedActions.map((item) => item.toLowerCase().replace(/-/g, "_")))
  const visibleActions = (STATUS_ACTIONS[status] ?? []).filter((item) => (backendActions.size === 0 || backendActions.has(item)) && can(actionPermission(item)))
  const policyPath = detail.policyId || detail.policyNumber
  const setTab = (tab: DetailTab) => { setActiveTab(tab); setSearchParams((current) => { current.set("tab", tab); current.delete("action"); return current }) }
  const copyNumber = async () => { try { await navigator.clipboard.writeText(detail.withdrawalNumber); setCopied(true); window.setTimeout(() => setCopied(false), 1800) } catch { toast({ tone: "warning", title: "Copy unavailable", message: "Select the withdrawal number manually to copy it." }) } }

  const breakdown = breakdownQuery.data ?? detail.breakdown ?? null
  const payments = paymentsQuery.data?.results ?? detail.payments
  const audit = auditQuery.data?.results ?? detail.auditTimeline
  const actionDialogOpen = Boolean(action)

  return <div className={`relative space-y-5 p-1 md:p-2 ${status === "REVERSED" ? "overflow-hidden" : ""}`}>
    {status === "REVERSED" && <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center"><span className="rotate-[-24deg] select-none text-7xl font-black uppercase tracking-[0.2em] text-red-500/10">Reversed</span></div>}
    <MasterDetailPage eyebrow="Ordinary Life / Servicing" title={detail.withdrawalNumber || "Withdrawal detail"} description={`${detail.policyholderDisplay || detail.policyholderName} · ${detail.productDisplay || "Ordinary Life policy withdrawal"}`} status={{ value: detail.statusDisplay || status }} actions={<div className="flex flex-wrap gap-2"><button type="button" className="button-secondary inline-flex items-center gap-2" onClick={() => navigate("/ordinary-life/withdrawals")}><ArrowLeft size={15} aria-hidden="true" />Withdrawals</button><button type="button" className="button-secondary inline-flex items-center gap-2" onClick={() => void copyNumber()}><Clipboard size={15} aria-hidden="true" />{copied ? "Copied" : "Copy number"}</button></div>}>
      <section className="surface-card p-5" aria-label="Withdrawal header"><div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Withdrawal Number</p><div className="mt-1 flex flex-wrap items-center gap-2"><span className="text-lg font-extrabold">{detail.withdrawalNumber}</span><button type="button" className="rounded-md p-1.5 text-[var(--muted-foreground)] hover:bg-[var(--secondary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]" aria-label="Copy withdrawal number" onClick={() => void copyNumber()}>{copied ? <Check size={15} aria-hidden="true" /> : <Clipboard size={15} aria-hidden="true" />}</button></div></div><div className="flex flex-wrap items-center gap-2"><WithdrawalStatusBadge status={detail.status} statusDisplay={detail.statusDisplay} /><a className="inline-flex items-center gap-1 text-sm font-bold text-[var(--primary)] underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]" href={`/ordinary-life/policies/${encodeURIComponent(policyPath)}`}>Policy {detail.policyNumber}</a></div></div><p className="mt-3 text-sm">Policyholder: <strong>{detail.policyholderDisplay || detail.policyholderName}</strong></p><div className="mt-4"><WithdrawalMoneySummary grossAmount={detail.grossAmount} feeAmount={detail.feeAmount} netPayout={detail.netPayout} currency={detail.currency} /></div><dl className="mt-4 grid gap-3 border-t pt-4 sm:grid-cols-2 lg:grid-cols-4"><StatRow label="Requested" value={dateLabel(detail.requestedAt)} /><StatRow label="Approved" value={dateLabel(detail.approvedAt)} /><StatRow label="Processed" value={dateLabel(detail.processedAt)} /><StatRow label="Paid" value={dateLabel(detail.paidAt)} /></dl></section>
      <section className="surface-card flex flex-wrap items-center gap-2 p-4" aria-label="Withdrawal actions"><span className="mr-2 text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Actions</span>{visibleActions.map((item) => <button key={item} type="button" className={`button-secondary inline-flex items-center gap-2 ${["reject", "cancel", "reverse"].includes(item) ? "!text-[var(--destructive)]" : ""}`} onClick={() => { setAction(item); setSearchParams((current) => { current.set("action", item); return current }) }}>{item === "approve" ? <ShieldCheck size={15} aria-hidden="true" /> : item === "reverse" ? <RotateCcw size={15} aria-hidden="true" /> : item === "reject" ? <XCircle size={15} aria-hidden="true" /> : <FileText size={15} aria-hidden="true" />}{ACTION_LABELS[item]}</button>)}{can("ol_withdrawals.print") && <button type="button" className="button-secondary inline-flex items-center gap-2" onClick={() => setTab("documents")}><FileText size={15} aria-hidden="true" />Print</button>}{visibleActions.length === 0 && !can("ol_withdrawals.print") && <span className="text-sm text-[var(--muted-foreground)]">No actions are available for this status.</span>}</section>
      <nav className="surface-card flex gap-1 overflow-x-auto p-1" aria-label="Withdrawal detail tabs">{TABS.map((tab) => <button key={tab.id} type="button" className={`whitespace-nowrap rounded-[9px] px-4 py-2.5 text-sm font-bold transition ${activeTab === tab.id ? "bg-[var(--primary)] text-[var(--primary-foreground)]" : "text-[var(--muted-foreground)] hover:bg-[var(--secondary)]"}`} aria-current={activeTab === tab.id ? "page" : undefined} onClick={() => setTab(tab.id)}>{tab.label}</button>)}</nav>
      {activeTab === "overview" && <OverviewTab detail={detail} breakdown={breakdown} audit={audit} />}
      {activeTab === "breakdown" && (breakdownQuery.isLoading ? <div className="surface-card p-5" role="status">Loading withdrawal breakdown…</div> : breakdownQuery.error ? <ErrorCoach title="Breakdown could not be loaded" message={breakdownQuery.error.message} resolutionSteps={["Retry the breakdown request.", "Confirm that the withdrawal calculation is available."]} /> : breakdown ? <BreakdownSection breakdown={breakdown} currency={detail.currency} /> : <div className="surface-card p-5 text-sm text-[var(--muted-foreground)]">No financial breakdown has been returned for this withdrawal.</div>)}
      {activeTab === "payments" && <section className="surface-card p-5"><h2 className="text-base font-extrabold">Payout Payments</h2><p className="mt-1 text-sm text-[var(--muted-foreground)]">Payments are read-only and linked to the withdrawal requisition.</p><div className="mt-4"><PaymentsTable payments={payments} /></div></section>}
      {activeTab === "documents" && <DocumentInstancesPanel sourceType="ol_policies.withdrawalrequest" objectId={detail.id} documentType="OL_WITHDRAWAL_STATEMENT" title="Withdrawal documents" description="Generated statements retain the withdrawal source transaction and approved template version." renderLabel="Generate statement" />}
      {activeTab === "audit" && <section className="surface-card p-5"><h2 className="text-base font-extrabold">Audit History</h2><p className="mt-1 text-sm text-[var(--muted-foreground)]">Every status and calculation event is displayed with its actor and source channel.</p><div className="mt-4"><Timeline entries={audit} /></div></section>}
    </MasterDetailPage>
    <ActionDialog action={action} detail={detail} open={actionDialogOpen} permitted={action ? can(actionPermission(action)) : false} onClose={() => { setAction(null); setSearchParams((current) => { current.delete("action"); return current }) }} />
  </div>
}

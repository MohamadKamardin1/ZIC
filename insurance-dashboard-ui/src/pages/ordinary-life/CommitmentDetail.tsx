import { useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { ArrowLeft, ExternalLink, Undo2 } from "lucide-react"
import { useCommitmentDetail, useCommitmentOptions } from "../../lib/commitmentsHooks"
import { CommitmentStatusBadge } from "../../components/commitments/CommitmentStatusBadge"
import { DueDateWarning, dueDateWarning } from "../../components/commitments/DueDateWarning"
import { ErrorCoach } from "../../components/commitments/ErrorCoach"
import { RecordPaymentModal } from "../../components/commitments/RecordPaymentModal"
import { ReverseAllocationModal } from "../../components/commitments/ReverseAllocationModal"
import { LifecycleActionModal, LIFECYCLE_ACTIONS, type LifecycleAction } from "../../components/commitments/LifecycleActionModal"
import { StatusBadge, type StatusTone } from "../../components/ui/StatusBadge"
import { useToast } from "../../components/ui/Toast"
import { formatMoney, sourceLabel } from "../../lib/commitmentsDisplay"
import type { CommitmentAllocation, CommitmentHistoryEntry } from "../../lib/commitments"

export type CommitmentDetailTab = "overview" | "allocations" | "history" | "notifications"

const TABS: Array<{ id: CommitmentDetailTab; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "allocations", label: "Allocations" },
  { id: "history", label: "History" },
  { id: "notifications", label: "Notifications" },
]

const ACTION_LABELS: Record<string, string> = {
  record_payment: "Record Payment",
  reverse: "Reverse",
  suspend: "Suspend",
  reactivate: "Reactivate",
  waive: "Waive",
  cancel: "Cancel",
  reschedule: "Reschedule",
}

export function paymentProgress(due: number, paid: number): number {
  if (due <= 0) return 0
  return Math.min(100, Math.max(0, Math.round((paid / due) * 100)))
}

function dateTimeLabel(value?: string | null): string {
  if (!value) return "—"
  const parsed = new Date(String(value))
  return Number.isNaN(parsed.getTime()) ? String(value) : new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" }).format(parsed)
}

function SourceChannelBadge({ channel }: { channel?: string }) {
  const tone: StatusTone = channel === "API" || channel === "IMPORT" || channel === "BATCH" ? "info" : channel === "SYSTEM" ? "neutral" : "info"
  return channel ? <StatusBadge value={channel} tone={tone} /> : <span className="text-xs text-[var(--muted-foreground)]">—</span>
}

function textOrDash(value?: string | null): string {
  return value ? value : "—"
}

export function CommitmentDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { toast } = useToast()
  const detail = useCommitmentDetail(id)
  const optionsQuery = useCommitmentOptions()
  const [tab, setTab] = useState<CommitmentDetailTab>("overview")
  const [paymentOpen, setPaymentOpen] = useState(false)
  const [reverseTarget, setReverseTarget] = useState<CommitmentAllocation | null>(null)
  const [lifecycleAction, setLifecycleAction] = useState<LifecycleAction | null>(null)

  if (!id) return null

  if (detail.isLoading) {
    return (
      <div className="space-y-5 p-4 md:p-6" role="status" aria-label="Loading commitment detail">
        <div className="surface-card flex items-center justify-between gap-3 px-5 py-4">
          <div className="space-y-2">
            <span className="block h-3 w-40 animate-pulse rounded bg-[var(--muted)]" />
            <span className="block h-4 w-64 animate-pulse rounded bg-[var(--muted)]" />
          </div>
          <span className="block h-8 w-28 animate-pulse rounded bg-[var(--muted)]" />
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {[0, 1, 2].map((index) => (
            <span key={index} className="block h-24 animate-pulse rounded-[10px] bg-[var(--muted)]" />
          ))}
        </div>
      </div>
    )
  }

  if (detail.isError || !detail.data) {
    const fallback = new Error("The commitment could not be loaded.")
    return (
      <div className="p-4 md:p-6">
        <button type="button" className="button-secondary mb-4" onClick={() => navigate("/ordinary-life/commitments")}>
          <ArrowLeft size={15} aria-hidden="true" />
          Back to register
        </button>
        <ErrorCoach error={detail.error ?? fallback} onRetry={() => detail.refetch()} title="Commitment detail could not be loaded" />
      </div>
    )
  }

  const d = detail.data

  const allowedActions = (d.allowedActions ?? []).filter((action) => ACTION_LABELS[action])

  const due = Number(d.premiumAmount) || 0
  const paid = Number(d.amountPaid) || 0
  const progress = paymentProgress(due, paid)
  const warning = dueDateWarning(d.dueDate, d.graceDate, d.lapseDate)

  const runAction = (action: string) => {
    if (action === "record_payment") {
      setPaymentOpen(true)
      return
    }
    if (action === "reverse") {
      const target = d.allocations.find((allocation) => !allocation.reversalOf)
      if (target) {
        setReverseTarget(target)
        return
      }
      toast({ tone: "info", title: "Nothing to reverse", message: "No reversible allocation exists for this commitment." })
      return
    }
    if ((LIFECYCLE_ACTIONS as readonly string[]).includes(action)) {
      setLifecycleAction(action as LifecycleAction)
      return
    }
    navigate(`/ordinary-life/commitments/${encodeURIComponent(id)}?action=${encodeURIComponent(action)}`)
  }

  const historyEntries: CommitmentHistoryEntry[] = d.statusHistory ?? []

  return (
    <div className="space-y-5 p-4 md:p-6">
      <header className="surface-card px-5 py-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="mb-1 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--muted-foreground)]">
              <span>ZIC</span><span>/</span><span>Ordinary Life</span><span>/</span><span>Commitments</span>
            </div>
            <h1 className="truncate text-2xl font-semibold tracking-[-0.04em] text-[var(--foreground)]">{d.commitmentNumber}</h1>
            <p className="mt-1 text-sm text-[var(--muted-foreground)]">
              {textOrDash(d.partnerName)} · {d.productName && d.planName ? `${d.productName} / ${d.planName}` : textOrDash(d.productName || d.planName)}
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <CommitmentStatusBadge value={d.status} config={optionsQuery.data?.statuses} />
              <StatusBadge value={`${d.currency} ${Number(d.balance) > 0 ? `balance ${formatMoney(d.balance, d.currency)}` : "settled"}`} tone={Number(d.balance) > 0 ? "warning" : "success"} />
            </div>
          </div>
          <div className="flex flex-col items-end gap-2">
            <DueDateWarning dueDate={d.dueDate} graceDate={d.graceDate} lapseDate={d.lapseDate} />
            <span className="text-xs text-[var(--muted-foreground)]">Due {dateTimeLabel(d.dueDate)}</span>
            <button type="button" className="button-secondary" onClick={() => navigate("/ordinary-life/commitments")}>
              <ArrowLeft size={15} aria-hidden="true" />
              Back to register
            </button>
          </div>
        </div>
      </header>

      <section className="surface-card px-5 py-4" aria-label="Payment status">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-bold text-[var(--foreground)]">Payment status</h2>
            <p className="mt-1 text-xs text-[var(--muted-foreground)]">
              {formatMoney(d.amountPaid, d.currency)} of {formatMoney(d.premiumAmount, d.currency)} allocated · {progress}%
            </p>
            <div className="mt-3 h-2.5 w-full max-w-md overflow-hidden rounded-full bg-[var(--muted)]" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress} aria-label="Payment progress" data-testid="payment-progress">
              <div className="h-full rounded-full bg-[var(--primary)] transition-all" style={{ width: `${progress}%` }} />
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {allowedActions.map((action) => (
              <button key={action} type="button" className={action === "reverse" || action === "cancel" ? "button-secondary" : "button-primary"} onClick={() => runAction(action)}>
                {ACTION_LABELS[action]}
              </button>
            ))}
            {allowedActions.length === 0 && <span className="text-xs text-[var(--muted-foreground)]">No actions available for this commitment.</span>}
          </div>
        </div>
      </section>

      <nav className="flex gap-1 overflow-x-auto rounded-xl border border-[var(--border)] bg-[var(--card)] p-1" aria-label="Commitment tabs">
        {TABS.map((item) => (
          <button key={item.id} type="button" onClick={() => setTab(item.id)} aria-selected={tab === item.id} className={`whitespace-nowrap rounded-lg px-4 py-2 text-xs font-semibold transition ${tab === item.id ? "bg-[var(--primary)] text-[var(--primary-foreground)]" : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]"}`}>
            {item.label}
          </button>
        ))}
      </nav>

      {tab === "overview" && (
        <div className="grid gap-4 lg:grid-cols-3">
          <section className="surface-card px-5 py-4 lg:col-span-1">
            <h3 className="text-[10px] font-bold uppercase tracking-[0.12em] text-[var(--muted-foreground)]">Source</h3>
            <dl className="mt-3 space-y-2 text-sm">
              <div><dt className="text-xs text-[var(--muted-foreground)]">Type</dt><dd className="font-medium text-[var(--foreground)]">{sourceLabel(d.sourceType)}</dd></div>
              <div><dt className="text-xs text-[var(--muted-foreground)]">Reference</dt><dd className="text-[var(--foreground)]">{textOrDash(d.sourceReference)}</dd></div>
              <div><dt className="text-xs text-[var(--muted-foreground)]">Channel</dt><dd><SourceChannelBadge channel={d.sourceChannel} /></dd></div>
              <div><dt className="text-xs text-[var(--muted-foreground)]">Installment</dt><dd className="tabular-nums text-[var(--foreground)]">{d.installmentNumber} of {d.installmentCount}</dd></div>
            </dl>
          </section>

          <section className="surface-card px-5 py-4 lg:col-span-1">
            <h3 className="text-[10px] font-bold uppercase tracking-[0.12em] text-[var(--muted-foreground)]">Amounts</h3>
            <dl className="mt-3 space-y-2 text-sm">
              <div className="flex items-center justify-between"><dt className="text-xs text-[var(--muted-foreground)]">Amount due</dt><dd className="tabular-nums text-[var(--foreground)]">{formatMoney(d.premiumAmount, d.currency)}</dd></div>
              <div className="flex items-center justify-between"><dt className="text-xs text-[var(--muted-foreground)]">Paid</dt><dd className="tabular-nums text-[var(--foreground)]">{formatMoney(d.amountPaid, d.currency)}</dd></div>
              {Number(d.amountWaived) > 0 && <div className="flex items-center justify-between"><dt className="text-xs text-[var(--muted-foreground)]">Waived</dt><dd className="tabular-nums text-[var(--foreground)]">{formatMoney(d.amountWaived, d.currency)}</dd></div>}
              <div className="flex items-center justify-between"><dt className="text-xs text-[var(--muted-foreground)]">Balance</dt><dd className={`tabular-nums font-semibold ${Number(d.balance) > 0 ? "text-[var(--destructive)]" : "text-[var(--foreground)]"}`}>{formatMoney(d.balance, d.currency)}</dd></div>
              <div className="flex items-center justify-between"><dt className="text-xs text-[var(--muted-foreground)]">Currency</dt><dd className="text-[var(--foreground)]">{d.currency}</dd></div>
            </dl>
          </section>

          <section className="surface-card px-5 py-4 lg:col-span-1">
            <h3 className="text-[10px] font-bold uppercase tracking-[0.12em] text-[var(--muted-foreground)]">Parameters applied</h3>
            <dl className="mt-3 space-y-2 text-sm">
              <div className="flex items-center justify-between"><dt className="text-xs text-[var(--muted-foreground)]">Payment frequency</dt><dd className="uppercase text-[var(--foreground)]">{d.premiumFrequency || "—"}</dd></div>
              <div className="flex items-center justify-between"><dt className="text-xs text-[var(--muted-foreground)]">Grace days</dt><dd className="tabular-nums text-[var(--foreground)]">{d.graceDays ?? "—"}</dd></div>
              <div className="flex items-center justify-between"><dt className="text-xs text-[var(--muted-foreground)]">Grace date</dt><dd className="text-[var(--foreground)]">{dateTimeLabel(d.graceDate) }</dd></div>
              <div className="flex items-center justify-between"><dt className="text-xs text-[var(--muted-foreground)]">Lapse date</dt><dd className="text-[var(--foreground)]">{dateTimeLabel(d.lapseDate)}</dd></div>
              <div className="flex items-center justify-between"><dt className="text-xs text-[var(--muted-foreground)]">Approval required</dt><dd>{d.approvalRequired ? <StatusBadge value="Required" tone="warning" /> : <StatusBadge value="No" tone="neutral" />}</dd></div>
            </dl>
            {(d.reasonCode || d.reasonText) && (
              <div className="mt-4 rounded-[10px] border border-[var(--border)] bg-[var(--muted)]/25 px-3 py-2">
                <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-[var(--muted-foreground)]">Reason {d.reasonCode ? `· ${d.reasonCode}` : ""}</p>
                <p className="mt-1 text-xs text-[var(--foreground)]">{d.reasonText || "—"}</p>
              </div>
            )}
          </section>
        </div>
      )}

      {tab === "allocations" && (
        <section className="surface-card overflow-hidden">
          <div className="border-b bg-[var(--muted)]/35 px-5 py-3"><h3 className="text-sm font-bold text-[var(--foreground)]">Allocations</h3><p className="text-xs text-[var(--muted-foreground)]">{d.allocations.length} payment allocation(s)</p></div>
          {d.allocations.length === 0 ? (
            <p className="px-5 py-8 text-center text-sm text-[var(--muted-foreground)]">No allocations recorded for this commitment.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead className="bg-[var(--muted)]/45 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]">
                  <tr>{["Payment mode", "Amount", "Currency", "Exchange rate", "Receipt reference", "Reversal", "Allocated at", "Reverse"].map((heading) => <th key={heading} scope="col" className="px-4 py-2.5 font-bold">{heading}</th>)}</tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  {d.allocations.map((allocation) => (
                    <tr key={allocation.id} className="hover:bg-[var(--muted)]/25">
                      <td className="px-4 py-2.5">{allocation.paymentMode || "—"}</td>
                      <td className="px-4 py-2.5 tabular-nums">{formatMoney(allocation.amount, allocation.currency)}</td>
                      <td className="px-4 py-2.5">{allocation.currency}</td>
                      <td className="px-4 py-2.5 tabular-nums">{allocation.exchangeRate}</td>
                      <td className="px-4 py-2.5 font-mono text-xs">{allocation.receiptReference || "—"}</td>
                      <td className="px-4 py-2.5">
                        {allocation.reversalOf ? <span className="inline-flex items-center gap-1 text-xs text-[var(--muted-foreground)]"><ExternalLink size={12} aria-hidden="true" />Reversal of {allocation.reversalOf}</span> : "—"}
                      </td>
                      <td className="px-4 py-2.5 text-xs">{dateTimeLabel(allocation.allocatedAt)}</td>
                      <td className="px-4 py-2.5 text-right">
                        {(d.allowedActions ?? []).includes("reverse") && !allocation.reversalOf ? (
                          <button type="button" className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-semibold text-[var(--destructive)] outline-none transition hover:bg-[var(--destructive)]/10 focus-visible:ring-2 focus-visible:ring-[var(--ring)]" onClick={() => setReverseTarget(allocation)} data-testid={`reverse-${allocation.id}`}>
                            <Undo2 size={13} aria-hidden="true" />
                            Reverse
                          </button>
                        ) : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {tab === "history" && (
        <section className="surface-card overflow-hidden">
          <div className="border-b bg-[var(--muted)]/35 px-5 py-3"><h3 className="text-sm font-bold text-[var(--foreground)]">Status history</h3><p className="text-xs text-[var(--muted-foreground)]">{historyEntries.length} recorded change(s)</p></div>
          {historyEntries.length === 0 ? (
            <p className="px-5 py-8 text-center text-sm text-[var(--muted-foreground)]">No status changes recorded for this commitment.</p>
          ) : (
            <ol className="divide-y divide-[var(--border)]">
              {historyEntries.map((entry, index) => (
                <li key={`${entry.createdAt}-${index}`} className="flex flex-wrap items-start gap-3 px-5 py-3">
                  <span className="mt-1.5 h-2 w-2 flex-none rounded-full bg-[var(--primary)]" aria-hidden="true" />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-[var(--foreground)]">
                      {entry.toStatus ? <span className="font-semibold">{entry.toStatus}</span> : "Status"} {entry.fromStatus && `from ${entry.fromStatus}`}
                    </p>
                    {entry.reason && <p className="mt-0.5 text-xs text-[var(--muted-foreground)]">{entry.reason}</p>}
                    <p className="mt-1 text-xs text-[var(--muted-foreground)]">
                      {entry.actorName || "System"} · {dateTimeLabel(entry.createdAt)}
                    </p>
                  </div>
                  <SourceChannelBadge channel={entry.sourceChannel} />
                </li>
              ))}
            </ol>
          )}
        </section>
      )}

      {tab === "notifications" && (
        <section className="surface-card overflow-hidden">
          <div className="border-b bg-[var(--muted)]/35 px-5 py-3"><h3 className="text-sm font-bold text-[var(--foreground)]">Notifications</h3><p className="text-xs text-[var(--muted-foreground)]">{d.notificationLogs.length} grace/overdue notification(s)</p></div>
          {d.notificationLogs.length === 0 ? (
            <p className="px-5 py-8 text-center text-sm text-[var(--muted-foreground)]">No notifications recorded for this commitment.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[680px] text-left text-sm">
                <thead className="bg-[var(--muted)]/45 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]">
                  <tr>{["Event", "Dispatch date", "Channel", "Recipient", "Status"].map((heading) => <th key={heading} scope="col" className="px-4 py-2.5 font-bold">{heading}</th>)}</tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  {d.notificationLogs.map((log) => (
                    <tr key={log.id} className="hover:bg-[var(--muted)]/25">
                      <td className="px-4 py-2.5 font-semibold">{log.eventType}</td>
                      <td className="px-4 py-2.5">{dateTimeLabel(log.dispatchOn)}</td>
                      <td className="px-4 py-2.5"><StatusBadge value={log.channel} tone="info" /></td>
                      <td className="px-4 py-2.5"><StatusBadge value={log.recipientType} tone="neutral" />{log.recipientIdentifier && <span className="ml-2 text-xs text-[var(--muted-foreground)]">{log.recipientIdentifier}</span>}</td>
                      <td className="px-4 py-2.5"><StatusBadge value={log.status} tone={log.status === "DISPATCHED" ? "success" : log.status === "FAILED" ? "danger" : "neutral"} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      <RecordPaymentModal
        open={paymentOpen}
        onClose={() => setPaymentOpen(false)}
        commitment={d}
        onSuccess={() => {
          setPaymentOpen(false)
          void detail.refetch()
        }}
      />
      {reverseTarget ? (
        <ReverseAllocationModal
          open
          onClose={() => setReverseTarget(null)}
          commitmentId={id}
          allocation={reverseTarget}
          onSuccess={() => {
            setReverseTarget(null)
            void detail.refetch()
          }}
        />
      ) : null}
      <LifecycleActionModal
        open={Boolean(lifecycleAction)}
        onClose={() => setLifecycleAction(null)}
        commitmentId={id}
        action={lifecycleAction}
        commitment={d}
        onSuccess={() => {
          setLifecycleAction(null)
          void detail.refetch()
        }}
      />
    </div>
  )
}

export default CommitmentDetailPage
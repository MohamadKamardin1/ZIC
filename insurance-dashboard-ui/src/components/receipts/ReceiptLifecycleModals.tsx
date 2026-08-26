import { useQuery } from "@tanstack/react-query"
import { AlertTriangle, CheckCircle2, LoaderCircle, RotateCcw, XCircle } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { ErrorCoach } from "../../components/ErrorCoach"
import { AmountCell, ReceiptStatusBadge } from "../../components/receipts/ReceiptPrimitives"
import { TextareaInput } from "../../components/ui/FormControls"
import { InfoBanner, Modal } from "../../components/ui/Overlays"
import { useToast } from "../../components/ui/Toast"
import { ApiClientError } from "../../lib/apiClient"
import { receiptsApi, type ReceiptAllocation, type ReceiptRecord } from "../../lib/receipts-api"

const dangerButton = "inline-flex min-h-10 items-center justify-center gap-2 rounded-[10px] bg-[var(--destructive)] px-4 text-sm font-bold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"

type LifecycleErrorProps = { title: string; error: unknown }

function LifecycleError({ title, error }: LifecycleErrorProps) {
  const props = error instanceof ApiClientError
    ? { message: error.message, resolutionSteps: error.resolutionSteps, loginUrl: error.deepLink, actionLabel: error.deepLink ? "Open resolution page" : undefined }
    : { message: error instanceof Error ? error.message : "This action could not be completed. Review the instructions and try again." }
  return <ErrorCoach title={title} message={props.message} resolutionSteps={props.resolutionSteps} loginUrl={props.loginUrl} actionLabel={props.actionLabel} />
}

function lifecycleReasonError(reason: string): string | undefined {
  return reason.trim() ? undefined : "Enter a reason so the audit trail explains why this financial action was taken."
}

function allocationTarget(allocation: ReceiptAllocation): string {
  return allocation.target_display || [allocation.commitment_number, allocation.source_display].filter(Boolean).join(" · ") || "Unspecified commitment"
}

function isFirstPremiumAllocation(allocation: ReceiptAllocation): boolean {
  return allocation.is_first_premium === true || Boolean(allocation.proposal_number) || String(allocation.source_display ?? "").toLowerCase().includes("proposal")
}

export interface ReceiptReversalModalProps {
  open: boolean
  receipt: ReceiptRecord
  onClose: () => void
  onSuccess: (receipt: ReceiptRecord) => void
}

export function ReceiptReversalModal({ open, receipt, onClose, onSuccess }: ReceiptReversalModalProps) {
  const { toast } = useToast()
  const [reason, setReason] = useState("")
  const [reasonError, setReasonError] = useState<string>()
  const [submitError, setSubmitError] = useState<unknown>(null)
  const [saving, setSaving] = useState(false)
  const allocationsQuery = useQuery({ queryKey: ["receipts", "reversal-impact", receipt.id], queryFn: () => receiptsApi.allocations(receipt.id), enabled: open, retry: false })
  const allocations = allocationsQuery.data?.results ?? []
  const firstPremiumAllocation = useMemo(() => allocations.find(isFirstPremiumAllocation), [allocations])

  useEffect(() => {
    if (!open) return
    setReason("")
    setReasonError(undefined)
    setSubmitError(null)
    setSaving(false)
  }, [open, receipt.id])

  const submit = async () => {
    const validationError = lifecycleReasonError(reason)
    setReasonError(validationError)
    if (validationError) return
    setSaving(true)
    setSubmitError(null)
    try {
      const result = await receiptsApi.reverse(receipt.id, { reason: reason.trim() })
      toast({ title: "Receipt reversed", message: `${receipt.receipt_number} was reversed and its allocations will be restored.`, tone: "success" })
      onSuccess(result)
      onClose()
    } catch (error) {
      setSubmitError(error)
    } finally {
      setSaving(false)
    }
  }

  return <Modal open={open} title="Reverse receipt" description={`This is a dangerous financial action. Review every allocation and enter a reason before reversing ${receipt.receipt_number}.`} onClose={() => { if (!saving) onClose() }} size="lg" footer={<><button type="button" className="button-secondary" onClick={onClose} disabled={saving}>Keep receipt</button><button type="button" className={dangerButton} onClick={() => void submit()} disabled={saving}>{saving ? <><LoaderCircle size={16} className="animate-spin" aria-hidden="true" />Reversing…</> : <><RotateCcw size={16} aria-hidden="true" />Confirm reversal</>}</button></>}>
    <div className="space-y-5">
      <div className="rounded-[10px] border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950" role="alert"><p className="flex items-center gap-2 font-bold"><AlertTriangle size={17} aria-hidden="true" />Impact preview</p><p className="mt-1 leading-6">Reversing this receipt will reverse every active allocation listed below and restore its commitment balance. This cannot be undone from the receipt screen.</p></div>
      {firstPremiumAllocation && <InfoBanner title="First-premium conversion guard"><span>Proposal conversion guard will return to false unless the policy is already issued. The first-premium allocation for <strong>{allocationTarget(firstPremiumAllocation)}</strong> will be reversed.</span></InfoBanner>}
      {allocationsQuery.isLoading && <div className="rounded-[10px] border border-[var(--border)] px-4 py-6 text-center text-sm text-[var(--muted-foreground)]" role="status">Loading reversal impact…</div>}
      {allocationsQuery.isError && <LifecycleError title="Reversal impact could not be loaded" error={allocationsQuery.error} />}
      {!allocationsQuery.isLoading && !allocationsQuery.isError && allocations.length === 0 && <div className="rounded-[10px] border border-dashed border-[var(--border)] px-4 py-6 text-center text-sm text-[var(--muted-foreground)]">No active allocations were returned. The receipt state will still be changed to Reversed.</div>}
      {!allocationsQuery.isLoading && !allocationsQuery.isError && allocations.length > 0 && <div className="overflow-x-auto rounded-[10px] border border-[var(--border)]"><table className="w-full min-w-[650px] text-left text-sm"><caption className="sr-only">Allocations affected by receipt reversal</caption><thead className="bg-[var(--muted)]/45 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><tr><th className="px-4 py-3">Commitment / source</th><th className="px-4 py-3">Current allocation</th><th className="px-4 py-3">Restored balance</th><th className="px-4 py-3">Status</th></tr></thead><tbody className="divide-y divide-[var(--border)]">{allocations.map((allocation) => <tr key={allocation.id}><td className="px-4 py-3"><p className="font-semibold">{allocationTarget(allocation)}</p>{isFirstPremiumAllocation(allocation) && <p className="mt-1 text-xs font-bold text-amber-800">First premium · {allocation.proposal_number ?? "proposal conversion linked"}</p>}</td><td className="px-4 py-3"><AmountCell amount={allocation.amount} currency={allocation.currency} /></td><td className="px-4 py-3"><AmountCell amount={allocation.restored_balance ?? allocation.amount} currency={allocation.currency} /></td><td className="px-4 py-3"><ReceiptStatusBadge status={allocation.status} /></td></tr>)}</tbody></table></div>}
      <TextareaInput label="Reason" name="receipt-reversal-reason" required value={reason} onChange={(event) => { setReason(event.target.value); setReasonError(undefined); setSubmitError(null) }} error={reasonError} placeholder="Explain why this receipt is being reversed" hint="This reason is written to the immutable audit timeline." />
      {submitError !== null && <LifecycleError title="Receipt reversal failed" error={submitError} />}
    </div>
  </Modal>
}

export interface AllocationReversalModalProps {
  open: boolean
  receipt: ReceiptRecord
  allocation: ReceiptAllocation | null
  onClose: () => void
  onSuccess: (allocation: ReceiptAllocation) => void
}

export function AllocationReversalModal({ open, receipt, allocation, onClose, onSuccess }: AllocationReversalModalProps) {
  const { toast } = useToast()
  const [reason, setReason] = useState("")
  const [reasonError, setReasonError] = useState<string>()
  const [submitError, setSubmitError] = useState<unknown>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) return
    setReason("")
    setReasonError(undefined)
    setSubmitError(null)
    setSaving(false)
  }, [open, allocation?.id])

  const submit = async () => {
    if (!allocation) return
    const validationError = lifecycleReasonError(reason)
    setReasonError(validationError)
    if (validationError) return
    setSaving(true)
    setSubmitError(null)
    try {
      const result = await receiptsApi.reverseAllocation(receipt.id, allocation.id, { reason: reason.trim() })
      toast({ title: "Allocation reversed", message: `${allocationTarget(allocation)} was reversed and its balance will be restored.`, tone: "success" })
      onSuccess(result)
      onClose()
    } catch (error) {
      setSubmitError(error)
    } finally {
      setSaving(false)
    }
  }

  if (!allocation) return null
  const firstPremium = isFirstPremiumAllocation(allocation)
  return <Modal open={open} title="Reverse allocation" description={`Review the impact before reversing the allocation for ${allocationTarget(allocation)}.`} onClose={() => { if (!saving) onClose() }} size="md" footer={<><button type="button" className="button-secondary" onClick={onClose} disabled={saving}>Keep allocation</button><button type="button" className={dangerButton} onClick={() => void submit()} disabled={saving}>{saving ? <><LoaderCircle size={16} className="animate-spin" aria-hidden="true" />Reversing…</> : "Confirm allocation reversal"}</button></>}>
    <div className="space-y-5">
      {firstPremium && <InfoBanner title="First-premium conversion guard"><span>Reversing this allocation may return proposal conversion guard to false unless the policy is already issued.</span></InfoBanner>}
      <div className="grid gap-3 sm:grid-cols-2"><div className="rounded-[10px] border border-[var(--border)] bg-[var(--muted)]/20 p-3"><p className="text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">Allocation being reversed</p><p className="mt-1 font-bold">{allocationTarget(allocation)}</p><p className="mt-1"><AmountCell amount={allocation.amount} currency={allocation.currency} /></p></div><div className="rounded-[10px] border border-emerald-300 bg-emerald-50 p-3 text-emerald-950"><p className="text-xs font-bold uppercase tracking-[0.08em]">Balance restored</p><p className="mt-1 font-bold"><AmountCell amount={allocation.restored_balance ?? allocation.amount} currency={allocation.currency} /></p><p className="mt-1 text-xs">The linked commitment receives this amount back.</p></div></div>
      <TextareaInput label="Reason" name="allocation-reversal-reason" required value={reason} onChange={(event) => { setReason(event.target.value); setReasonError(undefined); setSubmitError(null) }} error={reasonError} placeholder="Explain why this allocation is being reversed" hint="A reason is required for audit and reconciliation." />
      {submitError !== null && <LifecycleError title="Allocation reversal failed" error={submitError} />}
    </div>
  </Modal>
}

export interface CancelDraftModalProps {
  open: boolean
  receipt: ReceiptRecord
  onClose: () => void
  onSuccess: (receipt: ReceiptRecord) => void
}

export function CancelDraftModal({ open, receipt, onClose, onSuccess }: CancelDraftModalProps) {
  const { toast } = useToast()
  const [reason, setReason] = useState("")
  const [reasonError, setReasonError] = useState<string>()
  const [submitError, setSubmitError] = useState<unknown>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) return
    setReason("")
    setReasonError(undefined)
    setSubmitError(null)
    setSaving(false)
  }, [open, receipt.id])

  const submit = async () => {
    const validationError = lifecycleReasonError(reason)
    setReasonError(validationError)
    if (validationError) return
    setSaving(true)
    setSubmitError(null)
    try {
      const result = await receiptsApi.cancel(receipt.id, { reason: reason.trim() })
      toast({ title: "Draft cancelled", message: `${receipt.receipt_number} is now cancelled and cannot be edited.`, tone: "success" })
      onSuccess(result)
      onClose()
    } catch (error) {
      setSubmitError(error)
    } finally {
      setSaving(false)
    }
  }

  return <Modal open={open} title="Cancel draft receipt" description={`Cancel ${receipt.receipt_number}? A cancelled draft cannot be posted or edited.`} onClose={() => { if (!saving) onClose() }} size="md" footer={<><button type="button" className="button-secondary" onClick={onClose} disabled={saving}>Keep draft</button><button type="button" className={dangerButton} onClick={() => void submit()} disabled={saving || receipt.status.toUpperCase() !== "DRAFT"}>{saving ? <><LoaderCircle size={16} className="animate-spin" aria-hidden="true" />Cancelling…</> : <><XCircle size={16} aria-hidden="true" />Confirm cancellation</>}</button></>}>
    <div className="space-y-5">
      {receipt.status.toUpperCase() !== "DRAFT" && <InfoBanner title="Cancellation is unavailable"><span>Only receipts in Draft status can be cancelled. This receipt is currently <strong>{receipt.status}</strong>.</span></InfoBanner>}
      <div className="rounded-[10px] border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950"><p className="flex items-center gap-2 font-bold"><AlertTriangle size={17} aria-hidden="true" />This action is permanent</p><p className="mt-1">Cancel only when the draft should no longer be used. The reason will remain in the audit history.</p></div>
      <TextareaInput label="Reason" name="draft-cancellation-reason" required value={reason} onChange={(event) => { setReason(event.target.value); setReasonError(undefined); setSubmitError(null) }} error={reasonError} placeholder="Explain why this draft is being cancelled" />
      {submitError !== null && <LifecycleError title="Draft cancellation failed" error={submitError} />}
    </div>
  </Modal>
}

import { useState } from "react"
import { AlertTriangle, ShieldCheck } from "lucide-react"
import { ErrorCoach } from "../../components/commitments/ErrorCoach"
import { TextareaInput } from "../../components/ui/FormControls"
import { InfoBanner, Modal } from "../../components/ui/Overlays"
import { useToast } from "../../components/ui/Toast"
import { renderFk } from "../../lib/display"
import { useCancelPolicyMutation, useRequestPolicyPaidUpMutation, useRequestPolicySurrenderMutation } from "../../lib/policiesHooks"
import type { PolicyDetail } from "../../lib/policies"

function numberValue(value: unknown) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

function money(value: unknown, currency: string) {
  return new Intl.NumberFormat("en-TZ", { style: "currency", currency, maximumFractionDigits: 2 }).format(numberValue(value))
}

function recordValue(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {}
}

function snapshotPick(snapshot: Record<string, unknown>, ...keys: string[]) {
  for (const key of keys) if (snapshot[key] !== undefined && snapshot[key] !== null && snapshot[key] !== "") return snapshot[key]
  return null
}

function StrongConfirmation({ label, checked, onChange }: { label: string; checked: boolean; onChange: (checked: boolean) => void }) {
  return <label className="flex cursor-pointer items-start gap-3 rounded-[10px] border border-[var(--destructive)]/25 bg-[var(--destructive)]/8 p-3 text-sm"><input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} className="mt-0.5 h-4 w-4 accent-[var(--destructive)]" /> <span>{label}</span></label>
}

function SurrenderModal({ open, policy, onClose }: { open: boolean; policy: PolicyDetail; onClose: () => void }) {
  const { toast } = useToast()
  const mutation = useRequestPolicySurrenderMutation()
  const [reason, setReason] = useState("")
  const [confirmed, setConfirmed] = useState(false)
  const [error, setError] = useState("")
  const estimated = snapshotPick(policy.contractSnapshot, "estimated_surrender_value", "cash_surrender_value", "surrender_value", "cash_value")
  const estimatedLabel = estimated === null ? "Confirmed by server after request" : money(estimated, policy.currency)
  const submit = () => {
    if (!reason.trim()) return setError("Enter the reason for surrender so the request can be reviewed.")
    if (!confirmed) return setError("Confirm that you understand this action will terminate the policy.")
    setError("")
    mutation.mutate({ id: policy.id, payload: { reason: reason.trim() } }, { onSuccess: (data) => { const surrenderRequest = recordValue(recordValue(data).surrender_request); const netValue = surrenderRequest.net_surrender_value; toast({ title: "Surrender requested", message: `The policy is Surrender Pending. Server-calculated net surrender value: ${netValue === undefined ? "available in the refreshed policy record" : money(netValue, policy.currency)}.`, tone: "success" }); onClose() } })
  }
  return <Modal open={open} title="Surrender Policy" description="Review the estimated value and confirm this terminal policy action." onClose={onClose} footer={<><button type="button" className="button-secondary" onClick={onClose} disabled={mutation.isPending}>Cancel</button><button type="button" className="button-primary bg-[var(--destructive)] hover:bg-[var(--destructive)]/90" onClick={submit} disabled={mutation.isPending}>{mutation.isPending ? "Submitting…" : "Confirm surrender"}</button></>}>
    <div className="space-y-4"><InfoBanner title="Estimated Surrender Value"><span className="text-lg font-extrabold">{estimatedLabel}</span><span className="mt-1 block text-xs">This value is shown only when supplied by the issued policy snapshot. The final payable amount is calculated and confirmed by the backend at submission.</span></InfoBanner><div className="flex items-start gap-2 rounded-[10px] border border-[var(--warning)]/30 bg-[var(--warning)]/10 p-3 text-sm"><AlertTriangle size={17} className="mt-0.5 text-[var(--warning)]" aria-hidden="true" /><span>This will terminate the policy. Cover stops according to the effective surrender process.</span></div>{error && reason.trim() && <p className="text-xs font-semibold text-[var(--destructive)]" role="alert">{error}</p>}{mutation.error ? <ErrorCoach error={mutation.error} title="Surrender request could not be submitted" compact onRetry={submit} /> : null}<TextareaInput label="Reason for surrender" name="surrender_reason" required value={reason} error={error && !reason.trim() ? error : undefined} onChange={(event) => setReason(event.target.value)} placeholder="Explain why the policyholder is requesting surrender" /><StrongConfirmation label="I understand that surrender will terminate this policy and create a terminal servicing record." checked={confirmed} onChange={setConfirmed} /></div>
  </Modal>
}

function PaidUpModal({ open, policy, onClose }: { open: boolean; policy: PolicyDetail; onClose: () => void }) {
  const { toast } = useToast()
  const mutation = useRequestPolicyPaidUpMutation()
  const [confirmed, setConfirmed] = useState(false)
  const [error, setError] = useState("")
  const originalSumAssured = numberValue(policy.sumAssured)
  const paidUpSumAssured = snapshotPick(policy.contractSnapshot, "paid_up_sum_assured", "estimated_paid_up_sum_assured")
  const reduction = paidUpSumAssured === null ? null : Math.max(0, originalSumAssured - numberValue(paidUpSumAssured))
  const submit = () => {
    if (!confirmed) return setError("Confirm that you understand paid-up conversion reduces the remaining cover.")
    setError("")
    mutation.mutate({ id: policy.id, payload: {} }, { onSuccess: () => { toast({ title: "Policy converted to paid-up", message: "The policy status and cover have been refreshed.", tone: "success" }); onClose() } })
  }
  return <Modal open={open} title="Convert to Paid-Up" description="Convert the lapsed policy to paid-up status using the configured policy rules." onClose={onClose} footer={<><button type="button" className="button-secondary" onClick={onClose} disabled={mutation.isPending}>Cancel</button><button type="button" className="button-primary" onClick={submit} disabled={mutation.isPending}>{mutation.isPending ? "Converting…" : "Confirm paid-up conversion"}</button></>}>
    <div className="space-y-4"><InfoBanner title="Cover reduction"><div className="space-y-1 text-sm"><p>Current sum assured: <strong>{money(originalSumAssured, policy.currency)}</strong></p><p>Configured paid-up sum assured: <strong>{paidUpSumAssured === null ? "Calculated by the backend" : money(paidUpSumAssured, policy.currency)}</strong></p>{reduction !== null && <p>Estimated reduction: <strong>{money(reduction, policy.currency)}</strong></p>}</div></InfoBanner><div className="flex items-start gap-2 rounded-[10px] border border-[var(--warning)]/30 bg-[var(--warning)]/10 p-3 text-sm"><AlertTriangle size={17} className="mt-0.5 text-[var(--warning)]" aria-hidden="true" /><span>Paid-up conversion stops regular premium collection and may reduce the policy’s sum assured.</span></div>{error && <p className="text-xs font-semibold text-[var(--destructive)]" role="alert">{error}</p>}{mutation.error ? <ErrorCoach error={mutation.error} title="Paid-up conversion could not be completed" compact onRetry={submit} /> : null}<StrongConfirmation label="I understand that this lapsed policy will convert to paid-up status with reduced remaining cover." checked={confirmed} onChange={setConfirmed} /></div>
  </Modal>
}

function CancelModal({ open, policy, onClose }: { open: boolean; policy: PolicyDetail; onClose: () => void }) {
  const { toast } = useToast()
  const mutation = useCancelPolicyMutation()
  const [reason, setReason] = useState("")
  const [confirmed, setConfirmed] = useState(false)
  const [error, setError] = useState("")
  const withinFreeLook = policy.contractSnapshot.within_free_look !== false && policy.contractSnapshot.free_look_active !== false
  const submit = () => {
    if (!reason.trim()) return setError("Enter a cancellation reason before submitting.")
    if (!confirmed) return setError("Confirm that you understand this action cancels the policy and triggers the configured refund process.")
    setError("")
    mutation.mutate({ id: policy.id, payload: { reason: reason.trim() } }, { onSuccess: (data) => { const refund = recordValue(recordValue(data).refund); const refundAmount = refund.amount; const requisition = refund.requisition_number; toast({ title: "Policy cancelled", message: `The policy status is now Cancelled. Refund: ${refundAmount === undefined ? "not applicable" : money(refundAmount, policy.currency)}${requisition ? ` · Requisition ${String(requisition)}` : ""}.`, tone: "success" }); onClose() } })
  }
  return <Modal open={open} title="Cancel Policy" description="Cancel this policy during the configured free-look period." onClose={onClose} footer={<><button type="button" className="button-secondary" onClick={onClose} disabled={mutation.isPending}>Keep policy</button><button type="button" className="button-primary bg-[var(--destructive)] hover:bg-[var(--destructive)]/90" onClick={submit} disabled={mutation.isPending}>{mutation.isPending ? "Cancelling…" : "Confirm cancellation"}</button></>}>
    <div className="space-y-4">{withinFreeLook ? <InfoBanner title="Free-look cancellation"><span>The policy is marked as eligible for the configured free-look cancellation process. Any refund is calculated by the backend.</span></InfoBanner> : <InfoBanner title="Eligibility will be checked"><span>The backend will verify free-look eligibility again before cancelling the policy.</span></InfoBanner>}{error && reason.trim() && <p className="text-xs font-semibold text-[var(--destructive)]" role="alert">{error}</p>}{mutation.error ? <ErrorCoach error={mutation.error} title="Cancellation could not be completed" compact onRetry={submit} /> : null}<TextareaInput label="Cancellation reason" name="cancellation_reason" required value={reason} error={error && !reason.trim() ? error : undefined} onChange={(event) => setReason(event.target.value)} placeholder="Explain why the policy is being cancelled" /><StrongConfirmation label="I understand that cancellation is a terminal action and may create a refund requisition." checked={confirmed} onChange={setConfirmed} /></div>
  </Modal>
}

export default function PolicyTerminalActions({ policy, surrenderOpen, paidUpOpen, cancelOpen, onSurrenderChange, onPaidUpChange, onCancelChange }: { policy: PolicyDetail; surrenderOpen: boolean; paidUpOpen: boolean; cancelOpen: boolean; onSurrenderChange: (open: boolean) => void; onPaidUpChange: (open: boolean) => void; onCancelChange: (open: boolean) => void }) {
  return <><SurrenderModal open={surrenderOpen} policy={policy} onClose={() => onSurrenderChange(false)} /><PaidUpModal open={paidUpOpen} policy={policy} onClose={() => onPaidUpChange(false)} /><CancelModal open={cancelOpen} policy={policy} onClose={() => onCancelChange(false)} /><span className="sr-only">Terminal actions for {renderFk(policy.policyNumber)}</span></>
}

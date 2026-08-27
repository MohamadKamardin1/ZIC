import { AlertTriangle, CheckCircle2, ShieldCheck } from "lucide-react"
import { useEffect, useState } from "react"
import { ErrorCoach } from "../../components/ErrorCoach"
import { DecimalInput, FormGrid, ReadOnlyField, TextInput } from "../../components/ui/FormControls"
import { InfoBanner, Modal } from "../../components/ui/Overlays"
import { SmartSelect } from "../../components/ui/SmartSelect"
import { useToast } from "../../components/ui/Toast"
import { useLoanActionMutation } from "../../lib/loansHooks"
import type { LoanActionResult, LoanDetail } from "../../lib/loans"
import { formatMoney } from "../../lib/commitmentsDisplay"

export interface LoanActionModalProps {
  open: boolean
  loan: LoanDetail
  onClose: () => void
  onSuccess: (result: LoanActionResult) => void
}

function idempotencyKey(action: string, loanId: string): string {
  const random = typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`
  return `ol-loan-${action}-${loanId}-${random}`
}

function errorMessage(error: unknown): string {
  if (error instanceof Error && error.message) return error.message
  return "The financial action could not be completed."
}

function ActionConfirmation({ checked, onChange, label }: { checked: boolean; onChange: (checked: boolean) => void; label: string }) {
  return <label className="flex cursor-pointer items-start gap-3 rounded-[10px] border border-[var(--border)] bg-[var(--muted)]/25 px-3 py-3 text-sm leading-6"><input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} className="mt-1 h-4 w-4 accent-[var(--primary)]" /> <span>{label}</span></label>
}

function ModalFooter({ onClose, onSubmit, submitLabel, pending, disabled }: { onClose: () => void; onSubmit: () => void; submitLabel: string; pending: boolean; disabled?: boolean }) {
  return <><button type="button" className="button-secondary" onClick={onClose} disabled={pending}>Cancel</button><button type="button" className="button-primary inline-flex items-center gap-2" onClick={onSubmit} disabled={pending || disabled}>{pending ? "Processing…" : <><CheckCircle2 size={16} aria-hidden="true" />{submitLabel}</>}</button></>
}

export function RepayLoanModal({ open, loan, onClose, onSuccess }: LoanActionModalProps) {
  const { toast } = useToast()
  const { mutate, isPending, reset } = useLoanActionMutation()
  const [amount, setAmount] = useState("")
  const [paymentMode, setPaymentMode] = useState("")
  const [receiptReference, setReceiptReference] = useState("")
  const [reason, setReason] = useState("")
  const [confirmed, setConfirmed] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [submitError, setSubmitError] = useState<unknown>(null)
  const balance = Number(loan.outstandingBalance || 0)
  const amountValue = Number(amount || 0)

  useEffect(() => {
    if (!open) return
    setAmount("")
    setPaymentMode("")
    setReceiptReference("")
    setReason("")
    setConfirmed(false)
    setErrors({})
    setSubmitError(null)
    reset()
  }, [loan.id, open, reset])

  const submit = () => {
    const next: Record<string, string> = {}
    if (!amount || !Number.isFinite(amountValue) || amountValue <= 0) next.amount = "Enter a repayment amount greater than zero."
    else if (amountValue > balance) next.amount = `Enter an amount no greater than the outstanding balance of ${formatMoney(loan.outstandingBalance, loan.currency)}.`
    if (!paymentMode) next.paymentMode = "Select the verified payment mode used for this repayment."
    if (!receiptReference.trim()) next.receiptReference = "Enter the receipt reference or an approved manual reference."
    if (!confirmed) next.confirmed = "Confirm that the payment has been verified before processing it."
    setErrors(next)
    setSubmitError(null)
    if (Object.keys(next).length > 0) return
    mutate(
      {
        id: loan.id,
        action: "repay",
        idempotencyKey: idempotencyKey("repay", loan.id),
        payload: {
          amount: amountValue.toFixed(2),
          currency: loan.currency,
          payment_mode: paymentMode,
          receipt_ref: receiptReference.trim(),
          reason: reason.trim(),
        },
      },
      {
        onSuccess: (result) => {
          toast({ title: "Repayment processed", message: `${formatMoney(amountValue, loan.currency)} was allocated against ${loan.loanNumber}.`, tone: "success" })
          onSuccess(result)
        },
        onError: setSubmitError,
      },
    )
  }

  return <Modal open={open} title="Repay Loan" description={`Post a verified payment against ${loan.loanNumber}. This action is recorded in the immutable loan history.`} onClose={onClose} size="lg" footer={<ModalFooter onClose={onClose} onSubmit={submit} submitLabel="Process Repayment" pending={isPending} />}><div className="space-y-4"><div className="grid gap-3 sm:grid-cols-3"><ReadOnlyField label="Outstanding balance" value={formatMoney(loan.outstandingBalance, loan.currency)} /><ReadOnlyField label="Currency" value={loan.currency} /><ReadOnlyField label="Loan status" value={loan.statusDisplay || loan.status} /></div><FormGrid columns={2}><DecimalInput label="Repayment amount" name="repayment-amount" required hint={`Maximum ${formatMoney(loan.outstandingBalance, loan.currency)}`} value={amount} onChange={(event) => { setAmount(event.target.value); setErrors((current) => ({ ...current, amount: "" })) }} error={errors.amount} data-testid="repayment-amount" /><SmartSelect entity="payment-modes" label="Payment mode" name="repayment-payment-mode" required value={paymentMode} onChange={(value) => { setPaymentMode(value); setErrors((current) => ({ ...current, paymentMode: "" })) }} error={errors.paymentMode} placeholder="Select payment mode" /><TextInput label="Receipt reference" name="receipt-reference" required placeholder="Receipt number or manual reference" value={receiptReference} onChange={(event) => { setReceiptReference(event.target.value); setErrors((current) => ({ ...current, receiptReference: "" })) }} error={errors.receiptReference} /><TextInput label="Reason" name="repayment-reason" placeholder="Optional servicing note" value={reason} onChange={(event) => setReason(event.target.value)} /></FormGrid><ActionConfirmation checked={confirmed} onChange={(value) => { setConfirmed(value); setErrors((current) => ({ ...current, confirmed: "" })) }} label="I confirm that the payment and receipt reference have been verified and may be posted to this loan." />{errors.confirmed && <p className="text-xs font-medium text-[var(--destructive)]" role="alert">{errors.confirmed}</p>}{submitError ? <ErrorCoach title="Repayment could not be processed" message={errorMessage(submitError)} resolutionSteps={["Review the highlighted payment details and confirm the receipt reference.", "Ensure the amount does not exceed the current outstanding balance.", "Retry only after the payment has been verified."]} /> : null}</div></Modal>
}

export function DisburseLoanModal({ open, loan, onClose, onSuccess }: LoanActionModalProps) {
  const { toast } = useToast()
  const { mutate, isPending, reset } = useLoanActionMutation()
  const [paymentMode, setPaymentMode] = useState("")
  const [reason, setReason] = useState("")
  const [confirmed, setConfirmed] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [submitError, setSubmitError] = useState<unknown>(null)
  const bankDetails = loan.disbursement?.bankAccountCode ? `Settlement account ${loan.disbursement.bankAccountCode}` : `Active company settlement account selected by backend in ${loan.currency}`

  useEffect(() => {
    if (!open) return
    setPaymentMode("")
    setReason("")
    setConfirmed(false)
    setErrors({})
    setSubmitError(null)
    reset()
  }, [loan.id, open, reset])

  const submit = () => {
    const next: Record<string, string> = {}
    if (!paymentMode) next.paymentMode = "Select an active outgoing payment mode."
    if (!confirmed) next.confirmed = "Confirm the amount and destination before disbursing funds."
    setErrors(next)
    setSubmitError(null)
    if (Object.keys(next).length > 0) return
    mutate(
      {
        id: loan.id,
        action: "disburse",
        idempotencyKey: idempotencyKey("disburse", loan.id),
        payload: { payment_mode: paymentMode, reason: reason.trim() },
      },
      {
        onSuccess: (result) => {
          toast({ title: "Loan disbursed", message: `${formatMoney(loan.principalAmount, loan.currency)} was submitted for settlement.`, tone: "success" })
          onSuccess(result)
        },
        onError: setSubmitError,
      },
    )
  }

  return <Modal open={open} title="Disburse Loan" description={`Release the approved amount for ${loan.loanNumber} through the configured settlement process.`} onClose={onClose} size="lg" footer={<ModalFooter onClose={onClose} onSubmit={submit} submitLabel="Disburse Funds" pending={isPending} />}><div className="space-y-4"><InfoBanner title="Strict financial confirmation">Verify the approved loan amount and settlement destination before submitting. The backend will re-check approval, payment setup, currency, and idempotency.</InfoBanner><div className="grid gap-3 sm:grid-cols-2"><ReadOnlyField label="Loan amount" value={formatMoney(loan.principalAmount, loan.currency)} /><ReadOnlyField label="Bank details" value={bankDetails} /></div><FormGrid columns={2}><SmartSelect entity="payment-modes" label="Payment mode" name="disbursement-payment-mode" required value={paymentMode} onChange={(value) => { setPaymentMode(value); setErrors((current) => ({ ...current, paymentMode: "" })) }} error={errors.paymentMode} placeholder="Select outgoing payment mode" /><TextInput label="Reason" name="disbursement-reason" placeholder="Optional disbursement note" value={reason} onChange={(event) => setReason(event.target.value)} /></FormGrid><p className="rounded-[10px] border border-[var(--border)] bg-[var(--muted)]/25 px-3 py-3 text-sm font-semibold">Confirm disbursement of {formatMoney(loan.principalAmount, loan.currency)} to {bankDetails}?</p><ActionConfirmation checked={confirmed} onChange={(value) => { setConfirmed(value); setErrors((current) => ({ ...current, confirmed: "" })) }} label="I confirm that this approved loan may be disbursed to the displayed settlement destination." />{errors.confirmed && <p className="text-xs font-medium text-[var(--destructive)]" role="alert">{errors.confirmed}</p>}{submitError ? <ErrorCoach title="Disbursement could not be completed" message={errorMessage(submitError)} resolutionSteps={["Confirm the loan is Approved and has not already been disbursed.", "Select an active outgoing payment mode and verify the currency setup.", "Retry after resolving the configuration message."]} /> : null}</div></Modal>
}

export function OffsetLoanModal({ open, loan, onClose, onSuccess }: LoanActionModalProps) {
  const { toast } = useToast()
  const { mutate, isPending, reset } = useLoanActionMutation()
  const [sourceType, setSourceType] = useState("CLAIM")
  const [sourceId, setSourceId] = useState("")
  const [payoutAmount, setPayoutAmount] = useState(loan.outstandingBalance)
  const [reason, setReason] = useState("")
  const [confirmed, setConfirmed] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [submitError, setSubmitError] = useState<unknown>(null)

  useEffect(() => {
    if (!open) return
    setSourceType("CLAIM")
    setSourceId("")
    setPayoutAmount(loan.outstandingBalance)
    setReason("")
    setConfirmed(false)
    setErrors({})
    setSubmitError(null)
    reset()
  }, [loan.id, loan.outstandingBalance, open, reset])

  const submit = () => {
    const parsedPayout = Number(payoutAmount || 0)
    const next: Record<string, string> = {}
    if (!sourceType) next.sourceType = "Select whether this payout is from a claim, surrender, or maturity transaction."
    if (!sourceId.trim()) next.sourceId = "Enter the source transaction reference."
    if (!payoutAmount || !Number.isFinite(parsedPayout) || parsedPayout <= 0) next.payoutAmount = "Enter a payout amount greater than zero."
    if (!confirmed) next.confirmed = "Confirm that the payout deduction has been reviewed."
    setErrors(next)
    setSubmitError(null)
    if (Object.keys(next).length > 0) return
    mutate(
      {
        id: loan.id,
        action: "offset",
        idempotencyKey: idempotencyKey("offset", loan.id),
        payload: { source_type: sourceType, source_id: sourceId.trim(), payout_amount: parsedPayout.toFixed(2), reason: reason.trim() },
      },
      {
        onSuccess: (result) => {
          toast({ title: "Loan offset applied", message: `${formatMoney(parsedPayout, loan.currency)} was reconciled against ${loan.loanNumber}.`, tone: "success" })
          onSuccess(result)
        },
        onError: setSubmitError,
      },
    )
  }

  return <Modal open={open} title="Offset Loan" description={`Reconcile ${loan.loanNumber} against a claim, surrender, or maturity payout.`} onClose={onClose} size="lg" footer={<ModalFooter onClose={onClose} onSubmit={submit} submitLabel="Confirm Offset" pending={isPending} />}><div className="space-y-4"><div className="flex items-start gap-3 rounded-[10px] border border-[var(--warning)]/35 bg-[var(--warning)]/10 px-4 py-3 text-sm text-[var(--foreground)]"><AlertTriangle size={18} className="mt-0.5 shrink-0 text-[var(--warning)]" aria-hidden="true" /><p><strong>This amount will be deducted from the policy payout.</strong> The backend will cap the applied offset at the outstanding balance and preserve any remaining payout.</p></div><div className="grid gap-3 sm:grid-cols-2"><ReadOnlyField label="Outstanding balance" value={formatMoney(loan.outstandingBalance, loan.currency)} /><ReadOnlyField label="Currency" value={loan.currency} /></div><FormGrid columns={2}><div className="space-y-1"><label htmlFor="offset-source-type" className="text-sm font-semibold">Payout source<span className="ml-1 text-[var(--destructive)]" aria-label="required">*</span></label><select id="offset-source-type" value={sourceType} onChange={(event) => { setSourceType(event.target.value); setErrors((current) => ({ ...current, sourceType: "" })) }} className="h-10 w-full rounded-[10px] border bg-[var(--card)] px-3 text-sm text-[var(--foreground)] outline-none focus:border-[var(--ring)] focus:ring-2 focus:ring-[var(--ring)]"><option value="CLAIM">Claim</option><option value="SURRENDER">Surrender</option><option value="MATURITY">Maturity</option></select>{errors.sourceType && <p className="text-xs font-medium text-[var(--destructive)]" role="alert">{errors.sourceType}</p>}</div><TextInput label="Source transaction reference" name="offset-source-reference" required placeholder="Claim, surrender, or maturity reference" value={sourceId} onChange={(event) => { setSourceId(event.target.value); setErrors((current) => ({ ...current, sourceId: "" })) }} error={errors.sourceId} /><DecimalInput label="Offset amount" name="offset-amount" required hint="Defaults to full outstanding balance" value={payoutAmount} onChange={(event) => { setPayoutAmount(event.target.value); setErrors((current) => ({ ...current, payoutAmount: "" })) }} error={errors.payoutAmount} /><TextInput label="Reason" name="offset-reason" placeholder="Optional reconciliation note" value={reason} onChange={(event) => setReason(event.target.value)} /></FormGrid><ActionConfirmation checked={confirmed} onChange={(value) => { setConfirmed(value); setErrors((current) => ({ ...current, confirmed: "" })) }} label="I confirm that the policy payout deduction, source reference, and offset amount have been reviewed." />{errors.confirmed && <p className="text-xs font-medium text-[var(--destructive)]" role="alert">{errors.confirmed}</p>}{submitError ? <ErrorCoach title="Offset could not be completed" message={errorMessage(submitError)} resolutionSteps={["Confirm the source transaction reference belongs to this loan.", "Use a positive payout amount in the loan currency.", "Retry after resolving any balance or lifecycle warning."]} /> : null}</div></Modal>
}

export function LoanActionModal({ action, ...props }: LoanActionModalProps & { action: "repay" | "disburse" | "offset" }) {
  if (action === "repay") return <RepayLoanModal {...props} />
  if (action === "disburse") return <DisburseLoanModal {...props} />
  return <OffsetLoanModal {...props} />
}

export default LoanActionModal

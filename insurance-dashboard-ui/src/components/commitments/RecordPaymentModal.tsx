import { useEffect, useState } from "react"
import { Ban, CheckCircle2 } from "lucide-react"
import { Modal } from "../../components/ui/Overlays"
import { FormGrid, TextInput, DecimalInput, ReadOnlyField } from "../../components/ui/FormControls"
import { SmartSelect } from "../../components/ui/SmartSelect"
import { ErrorCoach } from "./ErrorCoach"
import { StatusBadge } from "../ui/StatusBadge"
import { useToast } from "../ui/Toast"
import { useCommitmentActionMutation } from "../../lib/commitmentsHooks"
import type { CommitmentDetail } from "../../lib/commitments"
import { formatMoney } from "../../lib/commitmentsDisplay"
import { notifyCommitmentSuccess } from "../../lib/commitmentsNotify"

export interface RecordPaymentModalProps {
  open: boolean
  onClose: () => void
  commitment: CommitmentDetail
  onSuccess: () => void
}

export function remainingAfterPayment(balance: number, amount: number): number {
  return balance - (Number.isFinite(amount) ? amount : 0)
}

export function isOverpayment(balance: number, amount: number): boolean {
  return remainingAfterPayment(balance, amount) < 0
}

export function RecordPaymentModal({ open, onClose, commitment, onSuccess }: RecordPaymentModalProps) {
  const { toast } = useToast()
  const action = useCommitmentActionMutation()

  const [amount, setAmount] = useState("")
  const [paymentMode, setPaymentMode] = useState("")
  const [currency, setCurrency] = useState(commitment.currency)
  const [exchangeRate, setExchangeRate] = useState("")
  const [receiptReference, setReceiptReference] = useState("")
  const [error, setError] = useState<Record<string, string>>({})
  const [showErrors, setShowErrors] = useState(false)
  const [submitError, setSubmitError] = useState<unknown>(null)

  const balance = Number(commitment.balance) || 0
  const parsedAmount = Number(amount) || 0
  const remaining = remainingAfterPayment(balance, parsedAmount)
  const over = isOverpayment(balance, parsedAmount)
  const crossCurrency = Boolean(currency) && currency !== commitment.currency
  const sourceChannel = commitment.sourceChannel || "API"

  useEffect(() => {
    if (!open) return
    setAmount("")
    setPaymentMode("")
    setCurrency(commitment.currency)
    setExchangeRate("")
    setReceiptReference("")
    setError({})
    setShowErrors(false)
    setSubmitError(null)
  }, [open, commitment.currency])

  const clear = (field: string) =>
    setError((current) => {
      if (!(field in current)) return current
      const next = { ...current }
      delete next[field]
      return next
    })

  const validate = () => {
    const next: Record<string, string> = {}
    if (!amount || Number(amount) <= 0) next.amount = "Enter an amount greater than zero."
    if (crossCurrency && (!exchangeRate || Number(exchangeRate) <= 0)) next.exchangeRate = "An exchange rate greater than zero is required for a cross-currency payment."
    if (!paymentMode) next.paymentMode = "Select a payment mode."
    if (!receiptReference.trim()) next.receiptReference = "Enter a receipt reference or a manual reference."
    setError(next)
    setShowErrors(true)
    return Object.keys(next).length === 0
  }

  const submit = () => {
    if (!validate()) return
    action.mutate(
      {
        id: commitment.id,
        action: "record_payment",
        payload: {
          amount: String(parsedAmount.toFixed(2)),
          payment_mode: paymentMode,
          currency,
          ...(crossCurrency ? { exchange_rate: String(Number(exchangeRate) || 1) } : {}),
          receipt_reference: receiptReference.trim(),
          source_channel: sourceChannel,
        },
      },
      {
        onSuccess: (result) => {
          const numberLabel = result?.commitmentNumber ?? commitment.commitmentNumber
          notifyCommitmentSuccess(toast, "Payment recorded", `Recorded ${formatMoney(String(parsedAmount), currency)} against ${numberLabel}. Open History to see the change.`)
          onSuccess()
        },
        onError: (reason) => setSubmitError(reason),
      },
    )
  }

  const footer = (
    <>
      <button type="button" className="button-secondary" onClick={onClose}>Cancel</button>
      <button type="button" className="button-primary" disabled={action.isPending} onClick={submit} data-testid="record-payment-submit">
        <CheckCircle2 size={16} aria-hidden="true" />
        {action.isPending ? "Recording…" : "Record Payment"}
      </button>
    </>
  )

  return (
    <Modal open={open} title="Record Payment" description={`Allocate a payment to ${commitment.commitmentNumber}. An amount above the balance is rejected as an overpayment.`} onClose={onClose} footer={footer} size="lg">
      <div className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <ReadOnlyField label="Outstanding balance" value={formatMoney(commitment.balance, commitment.currency)} />
          <ReadOnlyField label="Remaining after payment" value={formatMoney(String(remaining), commitment.currency)} />
          <div className="flex items-end">
            <span data-testid="balance-preview" className={`mb-1 w-full rounded-[10px] border px-3 py-2 text-sm font-semibold ${over ? "border-[var(--destructive)] bg-[var(--destructive)]/10 text-[var(--destructive)]" : "border-[var(--border)] bg-[var(--card)] text-[var(--foreground)]"}`}>
              {over ? <span className="inline-flex items-center gap-1"><Ban size={14} aria-hidden="true" />Exceeds balance</span> : "Within balance"}
            </span>
          </div>
        </div>

        <FormGrid columns={2}>
          <DecimalInput
            label="Amount"
            name="amount"
            required
            hint={`In ${currency}`}
            value={amount}
            onChange={(event) => { setAmount(event.target.value); clear("amount"); setShowErrors(false) }}
            error={showErrors ? error.amount : undefined}
            data-testid="payment-amount"
          />
          <SmartSelect
            entity="payment-modes"
            label="Payment mode"
            name="payment-mode"
            value={paymentMode}
            onChange={(value) => { setPaymentMode(value); clear("paymentMode"); setShowErrors(false) }}
            placeholder="Select payment mode"
            required
          />
          <SmartSelect
            entity="currencies"
            label="Currency"
            name="payment-currency"
            value={currency}
            onChange={(value) => { setCurrency(value); clear("currency"); setShowErrors(false) }}
            placeholder="Select currency"
          />
          {crossCurrency && (
            <DecimalInput
              label="Exchange rate"
              name="exchangeRate"
              required
              hint={`1 ${currency} in ${commitment.currency}`}
              value={exchangeRate}
              onChange={(event) => { setExchangeRate(event.target.value); clear("exchangeRate"); setShowErrors(false) }}
              error={showErrors ? error.exchangeRate : undefined}
              data-testid="exchange-rate-field"
            />
          )}
          <TextInput
            label="Receipt reference"
            name="receiptReference"
            required
            placeholder="Receipt number or manual reference"
            value={receiptReference}
            onChange={(event) => { setReceiptReference(event.target.value); clear("receiptReference"); setShowErrors(false) }}
            error={showErrors ? error.receiptReference : undefined}
          />
        </FormGrid>

        <div className="flex items-center gap-2 rounded-[10px] border border-[var(--border)] bg-[var(--muted)]/25 px-3 py-2 text-xs text-[var(--muted-foreground)]">
          <span>Source channel</span>
          <StatusBadge value={sourceChannel} tone="info" />
          <span>— recorded on this allocation and its audit entry.</span>
        </div>

        {submitError ? <ErrorCoach error={submitError} title="Payment could not be recorded" /> : null}
      </div>
    </Modal>
  )
}

export default RecordPaymentModal
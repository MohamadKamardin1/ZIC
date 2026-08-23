import { useEffect, useMemo, useState } from "react"
import { FilePlus2 } from "lucide-react"
import { Modal } from "../../components/ui/Overlays"
import { FormGrid, SelectInput, SearchableSelect, DateInput, DecimalInput, TextInput } from "../../components/ui/FormControls"
import { SmartSelect } from "../../components/ui/SmartSelect"
import { ErrorCoach } from "./ErrorCoach"
import { ReasonField, reasonError } from "./ReasonField"
import { useToast } from "../../components/ui/Toast"
import {
  useCommitmentOptions,
  useCommitmentReferenceOptions,
  useCreateManualCommitmentMutation,
} from "../../lib/commitmentsHooks"
import type { CommitmentDetail } from "../../lib/commitments"
import { notifyCommitmentSuccess } from "../../lib/commitmentsNotify"

export interface ManualCommitmentModalProps {
  open: boolean
  onClose: () => void
  onCreated: (commitment: CommitmentDetail) => void
}

const DEFAULT_CURRENCIES = ["TZS", "USD"]

export function ManualCommitmentModal({ open, onClose, onCreated }: ManualCommitmentModalProps) {
  const { toast } = useToast()
  const options = useCommitmentOptions()
  const references = useCommitmentReferenceOptions()
  const create = useCreateManualCommitmentMutation()

  const [partner, setPartner] = useState("")
  const [product, setProduct] = useState("")
  const [plan, setPlan] = useState("")
  const [currency, setCurrency] = useState("TZS")
  const [installmentNumber, setInstallmentNumber] = useState("1")
  const [dueDate, setDueDate] = useState("")
  const [amount, setAmount] = useState("")
  const [paymentMode, setPaymentMode] = useState("")
  const [reason, setReason] = useState("")
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [showErrors, setShowErrors] = useState(false)
  const [submitError, setSubmitError] = useState<unknown>(null)

  const currencyOptions = useMemo(
    () => (options.data?.currencies?.length ? options.data.currencies : DEFAULT_CURRENCIES).map((value) => ({ value, label: value })),
    [options.data],
  )
  const partnerOptions = useMemo(() => (references.data?.partners ?? []).map((option) => ({ value: option.id, label: option.label })), [references.data])
  const productOptions = useMemo(() => (references.data?.products ?? []).map((option) => ({ value: option.id, label: option.label })), [references.data])
  const planOptions = useMemo(() => (references.data?.plans ?? []).map((option) => ({ value: option.id, label: option.label })), [references.data])

  useEffect(() => {
    if (open) {
      setPartner(""); setProduct(""); setPlan(""); setCurrency(options.data?.currencies?.[0] ?? "TZS")
      setInstallmentNumber("1"); setDueDate(""); setAmount(""); setPaymentMode(""); setReason("")
      setErrors({}); setShowErrors(false); setSubmitError(null)
    }
  }, [open, options.data])

  const clearError = (field: string) =>
    setErrors((current) => {
      if (!(field in current)) return current
      const next = { ...current }
      delete next[field]
      return next
    })

  const validate = () => {
    const next: Record<string, string> = {}
    if (!partner) next.partner = "Select a partner."
    if (!product) next.product = "Select a product."
    if (!dueDate) next.dueDate = "Choose a due date."
    if (!amount || Number(amount) <= 0) next.premiumAmount = "Amount must be greater than zero."
    const reasonMessage = reasonError(reason)
    if (reasonMessage) next.reason = reasonMessage
    setErrors(next)
    setShowErrors(true)
    return Object.keys(next).length === 0
  }

  const submit = () => {
    if (!validate()) return
    create.mutate(
      {
        partner: partner || undefined,
        product: product || undefined,
        plan: plan || undefined,
        currency,
        installmentNumber: Number(installmentNumber) || 1,
        dueDate,
        premiumAmount: amount,
        paymentMode: paymentMode || undefined,
        reason,
      },
      {
        onSuccess: (commitment) => {
          notifyCommitmentSuccess(
            toast,
            "Commitment created",
            `Open ${commitment.commitmentNumber} to record its first payment.`,
          )
          onCreated(commitment)
        },
        onError: (error) => setSubmitError(error),
      },
    )
  }

  const footer = (
    <>
      <button type="button" className="button-secondary" onClick={onClose}>Cancel</button>
      <button type="button" className="button-primary" disabled={create.isPending} onClick={submit} data-testid="manual-submit">
        <FilePlus2 size={16} aria-hidden="true" />
        {create.isPending ? "Creating…" : "Create Commitment"}
      </button>
    </>
  )

  return (
    <Modal open={open} title="Create New Commitment" description="A manual commitment is a single obligation with full control over dates and amounts." onClose={onClose} footer={footer} size="lg">
      <div className="space-y-4">
        <FormGrid columns={2}>
          <SearchableSelect
            label="Partner"
            name="partner"
            required
            options={partnerOptions}
            value={partner}
            onChange={(value) => { setPartner(value); clearError("partner"); setShowErrors(false) }}
            placeholder="Search partners"
            error={showErrors ? errors.partner : undefined}
          />
          <SearchableSelect
            label="Product"
            name="product"
            required
            options={productOptions}
            value={product}
            onChange={(value) => { setProduct(value); clearError("product"); setShowErrors(false) }}
            placeholder="Search products"
            error={showErrors ? errors.product : undefined}
          />
          <SearchableSelect
            label="Plan"
            name="plan"
            options={planOptions}
            value={plan}
            onChange={setPlan}
            placeholder="Search plans (optional)"
          />
          <SelectInput
            label="Currency"
            name="currency"
            value={currency}
            onChange={(event) => setCurrency(event.target.value)}
          >
            {currencyOptions.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </SelectInput>
          <TextInput
            label="Installment number"
            name="installment_number"
            type="number"
            inputMode="numeric"
            min={1}
            value={installmentNumber}
            onChange={(event) => setInstallmentNumber(event.target.value)}
          />
          <DateInput
            label="Due date"
            name="dueDate"
            required
            value={dueDate}
            onChange={(event) => { setDueDate(event.target.value); clearError("dueDate"); setShowErrors(false) }}
            error={showErrors ? errors.dueDate : undefined}
          />
          <DecimalInput
            label="Amount"
            name="premiumAmount"
            required
            hint="Premium due for this installment"
            value={amount}
            onChange={(event) => { setAmount(event.target.value); clearError("premiumAmount"); setShowErrors(false) }}
            error={showErrors ? errors.premiumAmount : undefined}
          />
          <SmartSelect
            entity="payment-modes"
            label="Payment mode"
            name="payment-mode"
            value={paymentMode}
            onChange={setPaymentMode}
            placeholder="Select payment mode"
            createPermission="ol_commitments.record_payment"
          />
        </FormGrid>

        <ReasonField
          value={reason}
          onChange={(value) => { setReason(value); clearError("reason") }}
          label="Reason"
          showError={showErrors}
        />

        {submitError ? <ErrorCoach error={submitError} title="Commitment could not be created" /> : null}
      </div>
    </Modal>
  )
}

export default ManualCommitmentModal
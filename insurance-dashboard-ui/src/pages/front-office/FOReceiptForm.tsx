import { useQuery } from "@tanstack/react-query"
import { AlertCircle, ArrowLeft, CheckCircle2, LockKeyhole, Save } from "lucide-react"
import { useEffect, useMemo, useRef, useState } from "react"
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom"
import { ErrorCoach } from "../../components/ErrorCoach"
import { SmartSelect } from "../../components/ui/SmartSelect"
import { ConfirmModal, InfoBanner } from "../../components/ui/Overlays"
import { DateInput, DecimalInput, FormGrid, SelectInput, TextareaInput, TextInput } from "../../components/ui/FormControls"
import { useAccess } from "../../lib/access"
import { ApiClientError } from "../../lib/apiClient"
import { amountToWords } from "../../lib/amountToWords"
import { receiptsApi, type DisplayOption, type ReceiptRecord, type ReceiptWritePayload } from "../../lib/receipts-api"
import { useToast } from "../../components/ui/Toast"

type ReceiptFormValues = {
  receipt_date: string
  branch: string
  payer: string
  source_module: string
  source_reference: string
  currency: string
  payment_mode: string
  payment_reference: string
  bank_account: string
  receipt_amount: string
  narration: string
}

type FieldErrors = Record<string, string>
type SubmitMode = "draft" | "post"

function today(): string {
  const date = new Date()
  const offset = date.getTimezoneOffset()
  return new Date(date.getTime() - offset * 60_000).toISOString().slice(0, 10)
}

function makeIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID()
  return `receipt-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function initialValues(): ReceiptFormValues {
  return {
    receipt_date: today(),
    branch: "",
    payer: "",
    source_module: "DIRECT",
    source_reference: "",
    currency: "TZS",
    payment_mode: "",
    payment_reference: "",
    bank_account: "",
    receipt_amount: "",
    narration: "",
  }
}

function asString(value: unknown): string {
  return typeof value === "string" ? value : value === null || value === undefined ? "" : String(value)
}

function formValuesFromRecord(record: ReceiptRecord): ReceiptFormValues {
  return {
    receipt_date: asString(record.receipt_date),
    branch: asString(record.branch_id),
    payer: asString(record.payer_id),
    source_module: asString(record.source_module) || "DIRECT",
    source_reference: asString(record.source_reference),
    currency: asString(record.currency),
    payment_mode: asString(record.payment_mode),
    payment_reference: asString(record.payment_reference),
    bank_account: asString(record.bank_account_id),
    receipt_amount: asString(record.receipt_amount),
    narration: asString(record.narration),
  }
}

function toPayload(values: ReceiptFormValues): ReceiptWritePayload {
  return {
    receipt_date: values.receipt_date,
    branch: values.branch,
    payer: values.payer,
    source_module: values.source_module || undefined,
    source_reference: values.source_module === "OL_PROPOSAL" ? values.source_reference : undefined,
    currency: values.currency,
    payment_mode: values.payment_mode,
    payment_reference: values.payment_reference || undefined,
    bank_account: values.bank_account || undefined,
    receipt_amount: values.receipt_amount,
    narration: values.narration.trim() || undefined,
  }
}

function normalizeFieldErrors(error: unknown): { message: string; fieldErrors: FieldErrors; resolutionSteps?: string[]; deepLink?: string } {
  if (error instanceof ApiClientError) {
    return {
      message: error.message,
      fieldErrors: Object.fromEntries(Object.entries(error.fieldErrors).map(([key, messages]) => [key, messages.join(" ")])),
      resolutionSteps: error.resolutionSteps,
      deepLink: error.deepLink,
    }
  }
  return { message: error instanceof Error ? error.message : "The receipt could not be saved. Review the form and try again.", fieldErrors: {} }
}

function isDuplicate(error: unknown): error is ApiClientError {
  return error instanceof ApiClientError && (error.status === 409 || error.code === "RECEIPT_DUPLICATE")
}

function validate(values: ReceiptFormValues, rules: { requiresReference: boolean; requiresBankAccount: boolean }): FieldErrors {
  const errors: FieldErrors = {}
  if (!values.receipt_date) errors.receipt_date = "Choose the date the payment was received."
  if (!values.branch) errors.branch = "Select the branch that received this payment."
  if (!values.payer) errors.payer = "Select the payer or partner who made this payment."
  if (values.source_module === "OL_PROPOSAL" && !values.source_reference) errors.source_reference = "Select the proposal linked to this first-premium payment."
  if (!values.currency) errors.currency = "Select the currency received."
  if (!values.payment_mode) errors.payment_mode = "Select how the payment was made."
  if (!values.receipt_amount || Number(values.receipt_amount) <= 0) errors.receipt_amount = "Enter an amount greater than zero."
  if (rules.requiresReference && !values.payment_reference.trim()) errors.payment_reference = "This payment mode requires a payment reference. Enter the bank, mobile-money, cheque, or card reference."
  if (rules.requiresBankAccount && !values.bank_account) errors.bank_account = "This payment mode requires the receiving bank account. Select the masked account from the list."
  return errors
}

export default function FOReceiptForm() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { toast } = useToast()
  const { isSuperAdmin, hasPermission: accessHasPermission } = useAccess()
  const [values, setValues] = useState<ReceiptFormValues>(() => initialValues())
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [submitError, setSubmitError] = useState<unknown>(null)
  const [duplicateUrl, setDuplicateUrl] = useState<string | null>(null)
  const [confirmPostOpen, setConfirmPostOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [currencyLabel, setCurrencyLabel] = useState("TZS — Tanzanian Shilling")
  const [paymentModeLabel, setPaymentModeLabel] = useState("")
  const [branchLabel, setBranchLabel] = useState("")
  const [payerLabel, setPayerLabel] = useState("")
  const [sourceReferenceHint, setSourceReferenceHint] = useState("")
  const [paymentRule, setPaymentRule] = useState({ requiresReference: false, requiresBankAccount: false })
  const autoPostOpened = useRef(false)
  const isNew = !id

  const hasPermission = (permission: string) => isSuperAdmin || Boolean(accessHasPermission?.(permission))
  const receiptQuery = useQuery({
    queryKey: ["receipts", "detail", id],
    queryFn: () => receiptsApi.get(id as string),
    enabled: Boolean(id),
    retry: false,
  })
  const sourceModulesQuery = useQuery({
    queryKey: ["receipts", "options", "source-modules"],
    queryFn: () => receiptsApi.options.sourceModules(),
    staleTime: 5 * 60_000,
  })
  const paymentModesQuery = useQuery({
    queryKey: ["receipts", "options", "payment-modes", "rules"],
    queryFn: () => receiptsApi.options.paymentModes(),
    staleTime: 5 * 60_000,
  })

  const receipt = receiptQuery.data
  const status = asString(receipt?.status).toUpperCase()
  const readOnly = Boolean(receipt && status !== "DRAFT")
  const canCreate = hasPermission("front_office.receipts.create")
  const canEdit = hasPermission("front_office.receipts.edit")
  const canPost = hasPermission("front_office.receipts.post")
  const canSave = !readOnly && (isNew ? canCreate : canEdit)
  const canSaveAndPost = !readOnly && canPost && (isNew ? canCreate : canEdit)

  useEffect(() => {
    if (!receipt) return
    setValues(formValuesFromRecord(receipt))
    setCurrencyLabel(receipt.currency_display || receipt.currency)
    setPaymentModeLabel(receipt.payment_mode_display || receipt.payment_mode)
    setBranchLabel(receipt.branch_display || receipt.branch_id || "")
    setPayerLabel(receipt.payer_display || receipt.payer_id || "")
    setSourceReferenceHint(asString(receipt.source_reference_display))
  }, [receipt])

  useEffect(() => {
    if (!receipt || autoPostOpened.current || searchParams.get("action") !== "post" || readOnly || !canSaveAndPost) return
    autoPostOpened.current = true
    setConfirmPostOpen(true)
  }, [canSaveAndPost, readOnly, receipt, searchParams])

  const selectedPaymentMode = useMemo(() => paymentModesQuery.data?.results.find((option) => option.value === values.payment_mode), [paymentModesQuery.data?.results, values.payment_mode])
  useEffect(() => {
    const meta = selectedPaymentMode?.meta
    if (!meta) return
    setPaymentRule({ requiresReference: meta.requires_reference === true, requiresBankAccount: meta.requires_bank_account === true })
  }, [selectedPaymentMode?.meta])
  const amountWords = amountToWords(values.receipt_amount, values.currency, currencyLabel)
  const confirmationBranchLabel = branchLabel || receipt?.branch_display || "Selected branch"
  const confirmationPayerLabel = payerLabel || receipt?.payer_display || "Selected payer"
  const modeLabel = paymentModeLabel || selectedPaymentMode?.label || values.payment_mode || "Selected payment mode"
  const amountLabel = values.receipt_amount ? `${values.currency || ""} ${Number(values.receipt_amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`.trim() : "No amount entered"

  const update = (field: keyof ReceiptFormValues, value: string) => {
    setValues((current) => ({ ...current, [field]: value }))
    setFieldErrors((current) => {
      if (!(field in current)) return current
      const next = { ...current }
      delete next[field]
      return next
    })
    setSubmitError(null)
    setDuplicateUrl(null)
  }

  const submit = async (mode: SubmitMode) => {
    const nextErrors = validate(values, paymentRule)
    setFieldErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) return
    setSaving(true)
    setSubmitError(null)
    setDuplicateUrl(null)
    const idempotencyKey = makeIdempotencyKey()
    try {
      const payload = toPayload(values)
      const saved = id ? await receiptsApi.patchDraft(id, payload) : await receiptsApi.create(payload, idempotencyKey)
      if (mode === "post") {
        const posted = await receiptsApi.post(saved.id, `${idempotencyKey}:post`)
        toast({ title: "Receipt posted", message: `${posted.receipt_number} is posted. Next step: Allocate to commitments.`, tone: "success" })
        navigate(`/front-office/receipts/${posted.id}`)
      } else {
        toast({ title: "Receipt draft saved", message: `${saved.receipt_number} is available in the Receipts Work Queue.`, tone: "success" })
        navigate(`/front-office/receipts/${saved.id}?action=edit`)
      }
    } catch (error) {
      setSubmitError(error)
      const normalized = normalizeFieldErrors(error)
      setFieldErrors(normalized.fieldErrors)
      if (isDuplicate(error)) setDuplicateUrl(error.deepLink ?? "/front-office/receipts")
    } finally {
      setSaving(false)
    }
  }

  if (receiptQuery.isLoading) return <div className="flex min-h-[52vh] items-center justify-center text-sm text-[var(--muted-foreground)]" role="status">Loading receipt…</div>
  if (receiptQuery.isError) {
    const normalized = normalizeFieldErrors(receiptQuery.error)
    return <div className="space-y-4 p-4 md:p-6"><Link to="/front-office/receipts" className="inline-flex items-center gap-2 text-sm font-semibold text-[var(--primary)]"><ArrowLeft size={16} aria-hidden="true" />Back to receipts</Link><ErrorCoach title="Receipt could not be loaded" message={normalized.message} resolutionSteps={normalized.resolutionSteps} loginUrl={normalized.deepLink} actionLabel={normalized.deepLink ? "Open resolution page" : undefined} /></div>
  }

  const normalizedSubmitError = submitError ? normalizeFieldErrors(submitError) : null
  const sourceOptions = (sourceModulesQuery.data?.results ?? []).map((option) => <option key={option.value} value={option.value}>{option.label}</option>)
  const title = isNew ? "New Receipt" : readOnly ? "Receipt Details" : "Edit Receipt Draft"
  const description = isNew ? "Record an incoming payment. Save a draft for later completion or save and post when the payment has been verified." : readOnly ? "This receipt is posted and cannot be changed." : "Complete the draft details, then save the changes or post the receipt when verification is complete."

  return <div className="space-y-5 p-4 md:p-6">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="min-w-0">
        <Link to="/front-office/receipts" className="inline-flex items-center gap-2 text-sm font-semibold text-[var(--primary)] hover:underline"><ArrowLeft size={16} aria-hidden="true" />Back to Receipts Work Queue</Link>
        <p className="mt-3 text-xs font-bold uppercase tracking-[0.14em] text-[var(--muted-foreground)]">Front Office</p>
        <h1 className="mt-1 text-2xl font-bold tracking-tight">{title}</h1>
        <p className="mt-1 max-w-3xl text-sm text-[var(--muted-foreground)]">{description}</p>
      </div>
      {receipt && <span className="inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--muted)]/40 px-3 py-1.5 text-xs font-bold"><span className={`h-2 w-2 rounded-full ${readOnly ? "bg-[var(--success)]" : "bg-[var(--warning)]"}`} aria-hidden="true" />{receipt.receipt_number} · {receipt.status}</span>}
    </div>

    {readOnly && <InfoBanner title="Posted receipt is read-only"><span className="inline-flex items-center gap-2"><LockKeyhole size={15} aria-hidden="true" />Posted receipts are immutable. Use the work queue for allocation, reversal, print, or other permitted follow-up actions.</span></InfoBanner>}
    {!isNew && !readOnly && !canEdit && <InfoBanner title="Draft editing is restricted">You can view this draft, but your access profile does not include the receipt edit permission.</InfoBanner>}
    {isNew && !canCreate && <InfoBanner title="Receipt creation is restricted">Your access profile does not include the receipt create permission. Ask an administrator to grant Front Office Receipts create access.</InfoBanner>}
    {duplicateUrl && <InfoBanner title="This receipt was already submitted"><span className="flex flex-wrap items-center gap-2">The server found an existing receipt for this submission. Open it instead of submitting the payment again.<a className="font-bold text-[var(--primary)] underline-offset-2 hover:underline" href={duplicateUrl}>Open existing receipt</a></span></InfoBanner>}
    {normalizedSubmitError && !duplicateUrl && <ErrorCoach title="Receipt could not be saved" message={normalizedSubmitError.message} resolutionSteps={normalizedSubmitError.resolutionSteps} loginUrl={normalizedSubmitError.deepLink} actionLabel={normalizedSubmitError.deepLink ? "Open resolution page" : undefined} />}

    <section className="surface-card overflow-hidden">
      <div className="border-b bg-gradient-to-r from-[var(--primary)] to-indigo-500 px-5 py-4 text-white"><div className="flex items-center gap-3"><div className="flex h-9 w-9 items-center justify-center rounded-[10px] bg-white/15"><Save size={18} aria-hidden="true" /></div><div><h2 className="font-bold">Payment details</h2><p className="text-xs text-white/80">Fields marked with <span aria-label="required">*</span> are required. Payment-mode rules update as soon as the mode changes.</p></div></div></div>
      <div className="space-y-5 p-5">
        <FormGrid columns={2}>
          <DateInput label="Receipt date" name="receipt_date" required value={values.receipt_date} onChange={(event) => update("receipt_date", event.target.value)} error={fieldErrors.receipt_date} disabled={readOnly || !canSave} />
          <SmartSelect entity="branches" optionsUrl="/api/v1/front-office/options/branches/" label="Branch" name="branch" required value={values.branch} onChange={(value) => update("branch", value)} onOptionChange={(option) => setBranchLabel(option.label)} error={fieldErrors.branch} disabled={readOnly || !canSave} createPermission="front_office.receipts.create" manageHref="/system-parameters/partner/branches" emptyEntityLabel="branch" quickCreateSchemaUrl="/api/v1/front-office/options/branches/quick-create-schema/" quickCreateUrl="/api/v1/front-office/options/branches/quick-create/" />
          <SmartSelect entity="payers" optionsUrl="/api/v1/front-office/options/payers/" label="Payer / partner" name="payer" required value={values.payer} onChange={(value) => update("payer", value)} onOptionChange={(option) => setPayerLabel(option.label)} error={fieldErrors.payer} disabled={readOnly || !canSave} createPermission="partners.create" manageHref="/partners" emptyEntityLabel="payer or partner" quickCreateSchemaUrl="/api/v1/front-office/options/payers/quick-create-schema/" quickCreateUrl="/api/v1/front-office/options/payers/quick-create/" />
          <SelectInput label="Source module" name="source_module" required value={values.source_module} onChange={(event) => update("source_module", event.target.value)} error={undefined} disabled={readOnly || !canSave}><option value="">{sourceModulesQuery.isLoading ? "Loading source modules…" : "Select source module"}</option>{sourceOptions}</SelectInput>
          {values.source_module === "OL_PROPOSAL" && <SmartSelect entity="proposals" optionsUrl="/api/v1/front-office/options/proposals/" label="Source reference" name="source_reference" required value={values.source_reference} onChange={(value) => update("source_reference", value)} onOptionChange={(option) => setSourceReferenceHint(typeof option.meta?.status_hint === "string" ? option.meta.status_hint : "")} hint={sourceReferenceHint || "Only proposals with a first-premium status should be selected."} error={fieldErrors.source_reference} disabled={readOnly || !canSave} emptyEntityLabel="proposal" placeholder="Search first-premium proposals" />}
          <SmartSelect entity="currencies" label="Currency" name="currency" required value={values.currency} onChange={(value) => update("currency", value)} onOptionChange={(option) => setCurrencyLabel(option.label)} error={fieldErrors.currency} disabled={readOnly || !canSave} />
          <SmartSelect entity="payment-modes" label="Payment mode" name="payment_mode" required value={values.payment_mode} onChange={(value) => { update("payment_mode", value); setPaymentModeLabel("") }} onOptionChange={(option) => { setPaymentModeLabel(option.label); setPaymentRule({ requiresReference: option.meta?.requires_reference === true, requiresBankAccount: option.meta?.requires_bank_account === true }) }} error={fieldErrors.payment_mode} disabled={readOnly || !canSave} hint={paymentRule.requiresReference || paymentRule.requiresBankAccount ? "This mode adds required fields below." : "No additional fields required for this mode."} />
          {paymentRule.requiresReference && <TextInput label="Payment reference" name="payment_reference" required value={values.payment_reference} onChange={(event) => update("payment_reference", event.target.value)} error={fieldErrors.payment_reference} disabled={readOnly || !canSave} placeholder="Bank, mobile-money, cheque, or card reference" />}
          {paymentRule.requiresBankAccount && <SmartSelect entity="bank-accounts" optionsUrl="/api/v1/front-office/options/bank-accounts/" label="Receiving bank account" name="bank_account" required value={values.bank_account} onChange={(value) => update("bank_account", value)} error={fieldErrors.bank_account} disabled={readOnly || !canSave} emptyEntityLabel="bank account" placeholder="Select masked receiving account" />}
          <DecimalInput label="Amount" name="receipt_amount" required value={values.receipt_amount} onChange={(event) => update("receipt_amount", event.target.value)} error={fieldErrors.receipt_amount} disabled={readOnly || !canSave} min="0.01" placeholder="0.00" />
        </FormGrid>

        <div className="rounded-[10px] border border-[var(--primary)]/25 bg-[var(--primary)]/5 px-4 py-3" aria-live="polite"><div className="flex items-start gap-3"><CheckCircle2 size={17} className="mt-0.5 shrink-0 text-[var(--primary)]" aria-hidden="true" /><div><p className="text-xs font-bold uppercase tracking-[0.12em] text-[var(--primary)]">Amount in words</p><p data-testid="amount-in-words" className="mt-1 text-sm font-semibold text-[var(--foreground)]">{amountWords}</p></div></div></div>
        <TextareaInput label="Narration" name="narration" value={values.narration} onChange={(event) => update("narration", event.target.value)} disabled={readOnly || !canSave} placeholder="Add context that helps the allocation or reconciliation team." />
      </div>
    </section>

    {!readOnly && <div className="flex flex-wrap items-center justify-end gap-3">
      <button type="button" className="button-secondary" onClick={() => navigate("/front-office/receipts")} disabled={saving}>Cancel</button>
      <button type="button" className="button-secondary" onClick={() => void submit("draft")} disabled={saving || !canSave}><Save size={16} aria-hidden="true" />{saving ? "Saving…" : "Save Draft"}</button>
      <button type="button" className="button-primary" onClick={() => { const errors = validate(values, paymentRule); setFieldErrors(errors); if (Object.keys(errors).length === 0) setConfirmPostOpen(true) }} disabled={saving || !canSaveAndPost}><CheckCircle2 size={16} aria-hidden="true" />Save &amp; Post</button>
    </div>}

    <ConfirmModal open={confirmPostOpen} title="Confirm Save & Post" confirmLabel={saving ? "Posting…" : "Save & Post"} onClose={() => { if (!saving) setConfirmPostOpen(false) }} onConfirm={() => { setConfirmPostOpen(false); void submit("post") }} tone="primary" description={`Branch: ${confirmationBranchLabel}. Payer: ${confirmationPayerLabel}. Payment mode: ${modeLabel}. Amount: ${amountLabel}. The receipt will become immutable after posting.`} />
    {receipt && readOnly && <div className="flex flex-wrap items-center justify-between gap-3 rounded-[10px] border border-[var(--border)] bg-[var(--muted)]/25 px-4 py-3 text-sm"><span className="inline-flex items-center gap-2 text-[var(--muted-foreground)]"><AlertCircle size={16} aria-hidden="true" />Follow-up actions are available from the Receipts Work Queue according to your permissions.</span><Link to="/front-office/receipts" className="font-bold text-[var(--primary)] hover:underline">Open work queue</Link></div>}
  </div>
}

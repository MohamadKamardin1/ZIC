import { useQuery } from "@tanstack/react-query"
import { CheckCircle2, CircleAlert, LoaderCircle, Zap } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { ErrorCoach } from "../../components/ErrorCoach"
import { AmountCell, FirstPremiumBadge } from "../../components/receipts/ReceiptPrimitives"
import { DecimalInput } from "../../components/ui/FormControls"
import { ConfirmModal, InfoBanner, Modal } from "../../components/ui/Overlays"
import { useToast } from "../../components/ui/Toast"
import { ApiClientError } from "../../lib/apiClient"
import { receiptsApi, type ReceiptAllocationOption, type ReceiptAllocationResult, type ReceiptRecord } from "../../lib/receipts-api"

export interface ReceiptAllocationModalProps {
  open: boolean
  receipt: ReceiptRecord
  onClose: () => void
  onSuccess: (result: ReceiptAllocationResult) => void
}

type RowErrors = Record<string, string>
type RowValues = Record<string, { amount: string; exchangeRate: string }>

function errorCoachProps(error: unknown) {
  if (error instanceof ApiClientError) return { message: error.message, resolutionSteps: error.resolutionSteps, loginUrl: error.deepLink, actionLabel: error.deepLink ? "Open resolution page" : undefined }
  return { message: error instanceof Error ? error.message : "The allocation could not be recorded. Review the rows and try again." }
}

function formatMoney(value: number, currency: string): string {
  if (!Number.isFinite(value)) return `${currency} —`
  return new Intl.NumberFormat("en-TZ", { style: "currency", currency, minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value)
}

function isMissingRateError(row: ReceiptAllocationOption, value: { amount: string; exchangeRate: string }, receiptCurrency: string): boolean {
  return Number(value.amount) > 0 && row.currency !== receiptCurrency && (!value.exchangeRate || Number(value.exchangeRate) <= 0)
}

function convertedAmount(option: ReceiptAllocationOption, value: { amount: string; exchangeRate: string }, receiptCurrency: string): number {
  const amount = Number(value.amount) || 0
  if (option.currency === receiptCurrency) return amount
  const rate = Number(value.exchangeRate) || 0
  return amount * rate
}

export function ReceiptAllocationModal({ open, receipt, onClose, onSuccess }: ReceiptAllocationModalProps) {
  const { toast } = useToast()
  const [search, setSearch] = useState("")
  const [rows, setRows] = useState<RowValues>({})
  const [rowErrors, setRowErrors] = useState<RowErrors>({})
  const [submitError, setSubmitError] = useState<unknown>(null)
  const [saving, setSaving] = useState(false)
  const [confirmAuto, setConfirmAuto] = useState(false)
  const [autoResult, setAutoResult] = useState<ReceiptAllocationResult | null>(null)
  const [resultMode, setResultMode] = useState<"manual" | "auto" | null>(null)

  const optionsQuery = useQuery({ queryKey: ["receipts", "allocation-options", receipt.id, search], queryFn: () => receiptsApi.allocationOptions(receipt.id, { search: search || undefined }), enabled: open, retry: false })
  const options = optionsQuery.data?.results ?? []
  const unallocated = Number(receipt.unallocated_amount) || 0
  const selectedRows = useMemo(() => options.map((option) => ({ option, value: rows[option.id] ?? { amount: "", exchangeRate: "" } })).filter(({ value }) => Number(value.amount) > 0), [options, rows])
  const runningTotal = selectedRows.reduce((sum, row) => sum + convertedAmount(row.option, row.value, receipt.currency), 0)
  const remaining = unallocated - runningTotal

  useEffect(() => {
    if (!open) return
    setSearch("")
    setRows({})
    setRowErrors({})
    setSubmitError(null)
    setSaving(false)
    setConfirmAuto(false)
    setAutoResult(null)
    setResultMode(null)
  }, [open, receipt.id])

  const updateRow = (option: ReceiptAllocationOption, key: "amount" | "exchangeRate", value: string) => {
    setRows((current) => ({ ...current, [option.id]: { ...(current[option.id] ?? { amount: "", exchangeRate: "" }), [key]: value } }))
    setRowErrors((current) => { const next = { ...current }; delete next[option.id]; delete next[`${option.id}.${key}`]; return next })
    setSubmitError(null)
  }

  const validate = () => {
    const errors: RowErrors = {}
    if (selectedRows.length === 0) errors.general = "Select at least one commitment amount before recording an allocation."
    selectedRows.forEach(({ option, value }) => {
      const amount = Number(value.amount)
      if (!Number.isFinite(amount) || amount <= 0) errors[option.id] = "Enter an amount greater than zero."
      if (amount > Number(option.balance)) errors[option.id] = `Amount cannot exceed this commitment balance of ${formatMoney(Number(option.balance), option.currency)}.`
      if (option.currency !== receipt.currency && (!value.exchangeRate || Number(value.exchangeRate) <= 0)) errors[`${option.id}.exchangeRate`] = `An exchange rate is required because this commitment is in ${option.currency} while the receipt is in ${receipt.currency}.`
    })
    if (runningTotal > unallocated) errors.general = `Allocation total ${formatMoney(runningTotal, receipt.currency)} exceeds the unallocated receipt balance of ${formatMoney(unallocated, receipt.currency)}. Reduce one or more row amounts.`
    setRowErrors(errors)
    return Object.keys(errors).length === 0
  }

  const recordAllocation = async () => {
    if (!validate()) return
    setSaving(true)
    setSubmitError(null)
    try {
      const result = await receiptsApi.allocate(receipt.id, { allocations: selectedRows.map(({ option, value }) => ({ commitment: option.id, amount: String(Number(value.amount).toFixed(2)), ...(option.currency !== receipt.currency ? { exchange_rate: String(Number(value.exchangeRate)) } : {}) })) })
      toast({ title: "Allocation recorded", message: "The receipt allocation was recorded successfully.", tone: "success" })
      setAutoResult(result)
      setResultMode("manual")
      onSuccess(result)
    } catch (error) {
      setSubmitError(error)
    } finally {
      setSaving(false)
    }
  }

  const runAutoAllocate = async () => {
    setSaving(true)
    setSubmitError(null)
    setConfirmAuto(false)
    try {
      const result = await receiptsApi.autoAllocate(receipt.id)
      toast({ title: "Allocation recorded", message: "Oldest-first auto-allocation completed.", tone: "success" })
      setAutoResult(result)
      setResultMode("auto")
      onSuccess(result)
    } catch (error) {
      setSubmitError(error)
    } finally {
      setSaving(false)
    }
  }

  const firstPremiumProposal = autoResult?.first_premium_proposal_number ?? autoResult?.allocations.find((allocation) => allocation.is_first_premium)?.proposal_number
  const firstPremiumCompleted = autoResult?.first_premium_completed === true || Boolean(firstPremiumProposal)
  const missingExchangeRate = selectedRows.find(({ option, value }) => isMissingRateError(option, value, receipt.currency))
  const apiError = submitError ? errorCoachProps(submitError) : null

  return <>
    <Modal open={open} title="Allocate receipt" description={`Allocate ${receipt.receipt_number} for ${receipt.payer_display}. The total cannot exceed ${formatMoney(unallocated, receipt.currency)} currently unallocated.`} onClose={() => { if (!saving) onClose() }} size="xl" footer={<><button type="button" className="button-secondary" onClick={onClose} disabled={saving}>Close</button><button type="button" className="button-primary" onClick={() => void recordAllocation()} disabled={saving || Boolean(autoResult)}>{saving ? <><LoaderCircle size={16} className="animate-spin" aria-hidden="true" />Recording…</> : "Record Allocation"}</button></>}>
      <div className="space-y-5">
        <div className="grid gap-3 sm:grid-cols-3"><div className="rounded-[10px] border border-[var(--border)] bg-[var(--muted)]/20 p-3"><p className="text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">Unallocated balance</p><p className="mt-1 text-lg font-bold">{formatMoney(unallocated, receipt.currency)}</p></div><div className={`rounded-[10px] border p-3 ${remaining < 0 ? "border-[var(--destructive)] bg-[var(--destructive)]/10" : "border-[var(--border)] bg-[var(--muted)]/20"}`}><p className="text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">Remaining after selection</p><p className="mt-1 text-lg font-bold">{formatMoney(remaining, receipt.currency)}</p></div><div className="rounded-[10px] border border-[var(--border)] bg-[var(--muted)]/20 p-3"><p className="text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">Running total</p><p className="mt-1 text-lg font-bold">{formatMoney(runningTotal, receipt.currency)}</p></div></div>
        {rowErrors.general && <div className="rounded-[10px] border border-[var(--destructive)] bg-[var(--destructive)]/10 px-4 py-3 text-sm font-semibold text-[var(--destructive)]" role="alert"><CircleAlert size={16} className="mr-2 inline" aria-hidden="true" />{rowErrors.general}</div>}
        {apiError && <ErrorCoach title="Allocation could not be recorded" message={apiError.message} resolutionSteps={apiError.resolutionSteps} loginUrl={apiError.loginUrl} actionLabel={apiError.actionLabel} />}
        {missingExchangeRate && !submitError && <ErrorCoach title="Exchange rate is required" message={`The ${missingExchangeRate.option.currency} commitment cannot be allocated against this ${receipt.currency} receipt without an exchange rate.`} resolutionSteps={["Enter the effective exchange rate for this row.", "If the rate is not configured, ask a parameter administrator to add it before retrying."]} loginUrl="/ordinary-life/parameters/default-setup?focus=exchange-rate" actionLabel="Open exchange-rate parameters" />}
        {autoResult && <div className="space-y-3"><InfoBanner title={resultMode === "auto" ? "Auto-allocation complete" : "Allocation recorded"}><span>{resultMode === "auto" ? "Oldest-first allocation created" : "The allocation was recorded for"} {autoResult.allocations.length} allocation{autoResult.allocations.length === 1 ? "" : "s"}. Remaining unallocated amount: <strong>{formatMoney(Number(autoResult.remaining_unallocated_amount), receipt.currency)}</strong>.</span></InfoBanner>{firstPremiumCompleted && firstPremiumProposal && <div className="rounded-[10px] border border-emerald-300 bg-emerald-50 px-4 py-3 text-sm text-emerald-950" role="status"><p className="flex items-center gap-2 font-bold"><CheckCircle2 size={17} aria-hidden="true" />First premium posted.</p><p className="mt-1">Proposal <Link className="font-bold underline" to={`/ordinary-life/quotations?search=${encodeURIComponent(firstPremiumProposal)}`} onClick={onClose}>{firstPremiumProposal}</Link> can now convert to policy.</p></div>}<div className="rounded-[10px] border border-[var(--border)] p-3"><p className="text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">Created allocations</p><ul className="mt-2 space-y-2 text-sm">{autoResult.allocations.map((allocation, index) => <li key={allocation.id ?? `${allocation.commitment ?? "allocation"}-${index}`} className="flex flex-wrap items-center justify-between gap-2"><span className="font-semibold">{allocation.target_display ?? allocation.commitment ?? "Commitment allocation"}</span><AmountCell amount={allocation.amount} currency={allocation.currency ?? receipt.currency} /></li>)}</ul></div></div>}
        {!autoResult && <><div className="flex flex-wrap items-end justify-between gap-3"><div><p className="font-bold">Open commitments for {receipt.payer_display}</p><p className="mt-1 text-sm text-[var(--muted-foreground)]">Choose one or more rows. First-premium commitments are marked because completing them unlocks proposal conversion.</p></div><div className="flex flex-wrap gap-2"><input aria-label="Search commitments" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search commitments" className="h-10 min-w-[220px] rounded-[10px] border bg-[var(--card)] px-3 text-sm outline-none focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)]" /><button type="button" className="button-secondary" onClick={() => setConfirmAuto(true)} disabled={saving}><Zap size={16} aria-hidden="true" />Auto-Allocate oldest-first</button></div></div>{optionsQuery.isLoading && <div className="py-8 text-center text-sm text-[var(--muted-foreground)]" role="status">Loading open commitments…</div>}{optionsQuery.isError && <ErrorCoach title="Commitments could not be loaded" message={errorCoachProps(optionsQuery.error).message} resolutionSteps={errorCoachProps(optionsQuery.error).resolutionSteps} loginUrl={errorCoachProps(optionsQuery.error).loginUrl} actionLabel={errorCoachProps(optionsQuery.error).actionLabel} />}{!optionsQuery.isLoading && !optionsQuery.isError && options.length === 0 && <div className="py-8"><p className="text-center font-bold">No open commitments found</p><p className="mt-1 text-center text-sm text-[var(--muted-foreground)]">Try a different search or confirm that the payer has due commitments.</p></div>}{!optionsQuery.isLoading && !optionsQuery.isError && options.length > 0 && <div className="overflow-x-auto"><table className="w-full min-w-[980px] text-left text-sm"><caption className="sr-only">Open commitments for allocation</caption><thead className="bg-[var(--muted)]/45 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><tr><th className="px-3 py-3">Commitment / source</th><th className="px-3 py-3">Product / plan</th><th className="px-3 py-3">Due</th><th className="px-3 py-3">Balance</th><th className="px-3 py-3">Allocation amount</th><th className="px-3 py-3">Exchange rate</th></tr></thead><tbody className="divide-y divide-[var(--border)]">{options.map((option) => { const value = rows[option.id] ?? { amount: "", exchangeRate: "" }; const error = rowErrors[option.id]; const exchangeError = rowErrors[`${option.id}.exchangeRate`]; const converted = Number(value.amount) > 0 && Number(value.exchangeRate) > 0 ? Number(value.amount) * Number(value.exchangeRate) : 0; return <tr key={option.id} className={option.is_first_premium ? "bg-amber-50/40 dark:bg-amber-950/10" : undefined}><td className="px-3 py-3 align-top"><p className="font-semibold">{option.commitment_number}</p><p className="text-xs text-[var(--muted-foreground)]">{option.source_display}</p>{option.is_first_premium && <div className="mt-2"><FirstPremiumBadge proposalNumber={option.proposal_number} /></div>}</td><td className="px-3 py-3 align-top"><p>{option.product_display}</p><p className="text-xs text-[var(--muted-foreground)]">{option.plan_display}</p></td><td className="px-3 py-3 align-top">{option.due_date}</td><td className="px-3 py-3 align-top"><AmountCell amount={option.balance} currency={option.currency} /></td><td className="px-3 py-3 align-top"><DecimalInput label={`Amount for ${option.commitment_number}`} name={`allocation-${option.id}`} value={value.amount} onChange={(event) => updateRow(option, "amount", event.target.value)} error={error} min="0" placeholder="0.00" /></td><td className="px-3 py-3 align-top">{option.currency !== receipt.currency ? <div className="space-y-1"><DecimalInput label={`Exchange rate for ${option.commitment_number}`} name={`exchange-rate-${option.id}`} value={value.exchangeRate} onChange={(event) => updateRow(option, "exchangeRate", event.target.value)} error={exchangeError} min="0" placeholder={`1 ${option.currency} in ${receipt.currency}`} /><p className="text-xs text-[var(--muted-foreground)]">Converted: {formatMoney(converted, receipt.currency)}</p></div> : <span className="text-xs text-[var(--muted-foreground)]">Same currency as receipt</span>}</td></tr>})}</tbody></table></div>}</>}
      </div>
    </Modal>
    <ConfirmModal open={confirmAuto} title="Confirm oldest-first auto-allocation" description={`The system will allocate ${formatMoney(unallocated, receipt.currency)} from this receipt to the oldest eligible open commitments first. First-premium commitments are prioritized according to their due date, and any remaining amount stays unallocated. Continue?`} confirmLabel={saving ? "Allocating…" : "Run Auto-Allocate"} onClose={() => { if (!saving) setConfirmAuto(false) }} onConfirm={() => void runAutoAllocate()} tone="primary" />
  </>
}

export default ReceiptAllocationModal

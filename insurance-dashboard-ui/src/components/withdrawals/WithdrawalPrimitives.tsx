import { CircleAlert, HandCoins } from "lucide-react"
import { formatMoney } from "../../lib/commitmentsDisplay"
import { StatusBadge, type StatusTone } from "../ui/StatusBadge"

const STATUS_LABELS: Record<string, string> = {
  REQUESTED: "Requested",
  APPROVED: "Approved",
  PROCESSING: "Processing",
  PAID: "Paid",
  REVERSED: "Reversed",
  DECLINED: "Declined",
  CANCELLED: "Cancelled",
}

const STATUS_TONES: Record<string, StatusTone> = {
  REQUESTED: "warning",
  APPROVED: "info",
  PROCESSING: "info",
  PAID: "success",
  REVERSED: "neutral",
  DECLINED: "danger",
  CANCELLED: "neutral",
}

function titleCase(value: string): string {
  return value.toLowerCase().split(/[\s_]+/).map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" ")
}

export function withdrawalStatusLabel(status?: string | null, statusDisplay?: string | null): string {
  if (statusDisplay && !/^[0-9a-f]{8}-[0-9a-f-]{27,}$/i.test(statusDisplay)) return statusDisplay
  const normalized = String(status ?? "").trim().toUpperCase()
  return STATUS_LABELS[normalized] ?? (normalized ? titleCase(normalized) : "—")
}

export function withdrawalStatusTone(status?: string | null): StatusTone {
  return STATUS_TONES[String(status ?? "").trim().toUpperCase()] ?? "neutral"
}

export function WithdrawalStatusBadge({ status, statusDisplay, className = "" }: { status?: string | null; statusDisplay?: string | null; className?: string }) {
  return <StatusBadge value={withdrawalStatusLabel(status, statusDisplay)} tone={withdrawalStatusTone(status)} className={className} />
}

export function MoneyCell({ value, currency = "TZS", label, className = "" }: { value: string | number | null | undefined; currency?: string | null; label?: string; className?: string }) {
  const display = formatMoney(value, currency || "TZS")
  return <span className={`tabular-nums ${className}`} aria-label={label ? `${label}: ${display}` : display}>{display}</span>
}

export function ImpactAlert({ grossAmount, currency = "TZS", message, className = "" }: { grossAmount: string | number | null | undefined; currency?: string | null; message?: string; className?: string }) {
  const amount = formatMoney(grossAmount, currency || "TZS")
  return (
    <div className={`flex items-start gap-3 rounded-[10px] border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950 ${className}`} role="alert">
      <CircleAlert className="mt-0.5 shrink-0" size={18} aria-hidden="true" />
      <div>
        <p className="font-bold">Policy impact</p>
        <p className="mt-1 leading-6">{message ?? `Cash Value will reduce by ${amount}.`}</p>
      </div>
    </div>
  )
}

export function WithdrawalMoneySummary({ grossAmount, feeAmount, netPayout, currency = "TZS" }: { grossAmount: string | number | null | undefined; feeAmount: string | number | null | undefined; netPayout: string | number | null | undefined; currency?: string | null }) {
  return (
    <div className="grid gap-3 sm:grid-cols-3" aria-label="Withdrawal financial summary">
      <div className="rounded-[10px] border p-3"><div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><HandCoins size={14} aria-hidden="true" />Gross Amount</div><p className="mt-2 font-extrabold"><MoneyCell value={grossAmount} currency={currency} label="Gross amount" /></p></div>
      <div className="rounded-[10px] border p-3"><p className="text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">Fee Amount</p><p className="mt-2 font-extrabold"><MoneyCell value={feeAmount} currency={currency} label="Fee amount" /></p></div>
      <div className="rounded-[10px] border border-emerald-200 bg-emerald-50 p-3 text-emerald-950"><p className="text-xs font-bold uppercase tracking-[0.08em]">Net Payout</p><p className="mt-2 font-extrabold"><MoneyCell value={netPayout} currency={currency} label="Net payout" /></p></div>
    </div>
  )
}

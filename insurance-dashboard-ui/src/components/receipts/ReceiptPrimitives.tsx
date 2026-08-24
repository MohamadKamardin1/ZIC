import { Eye, EyeOff, ShieldCheck } from "lucide-react"
import { useState } from "react"
import { StatusBadge, type StatusTone } from "../ui/StatusBadge"

const statusLabels: Record<string, string> = {
  DRAFT: "Draft",
  POSTED: "Posted",
  PARTIALLY_ALLOCATED: "Partially allocated",
  ALLOCATED: "Allocated",
  REVERSED: "Reversed",
  CANCELLED: "Cancelled",
}

const statusTones: Record<string, StatusTone> = {
  DRAFT: "warning",
  POSTED: "info",
  PARTIALLY_ALLOCATED: "warning",
  ALLOCATED: "success",
  REVERSED: "danger",
  CANCELLED: "danger",
}

const paymentModeLabels: Record<string, string> = {
  CASH: "Cash",
  BANK_TRANSFER: "Bank transfer",
  MOBILE_MONEY: "Mobile money",
  CARD: "Card",
  CHEQUE: "Cheque",
}

function titleCase(value: string): string {
  return value.toLowerCase().replace(/(^|[_\s-])\w/g, (letter) => letter.toUpperCase()).replace(/_/g, " ")
}

export function ReceiptStatusBadge({ status }: { status: string }) {
  const normalized = status.toUpperCase()
  return <StatusBadge value={statusLabels[normalized] ?? titleCase(status)} tone={statusTones[normalized] ?? "neutral"} />
}

export function formatReceiptAmount(value: string | number, currency = "TZS"): string {
  const amount = Number(value)
  if (!Number.isFinite(amount)) return `${currency} —`
  return new Intl.NumberFormat("en-TZ", { style: "currency", currency, minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(amount)
}

export function AmountCell({ amount, currency, amountInWords }: { amount: string | number; currency: string; amountInWords?: string | null }) {
  const label = formatReceiptAmount(amount, currency)
  return <span className="whitespace-nowrap" title={amountInWords ?? undefined} aria-label={amountInWords ? `${label}. ${amountInWords}` : label}>{label}</span>
}

export function AllocationProgressBar({ allocated, total, currency = "TZS" }: { allocated: string | number; total: string | number; currency?: string }) {
  const totalValue = Number(total)
  const allocatedValue = Number(allocated)
  const ratio = totalValue > 0 && Number.isFinite(totalValue) ? Math.max(0, Math.min(100, allocatedValue / totalValue * 100)) : 0
  return (
    <div className="min-w-[150px] space-y-1" aria-label={`${formatReceiptAmount(allocated, currency)} allocated of ${formatReceiptAmount(total, currency)}`}>
      <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground"><span>{formatReceiptAmount(allocated, currency)}</span><span>{ratio.toFixed(0)}%</span></div>
      <div className="h-2 overflow-hidden rounded-full bg-secondary" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Number(ratio.toFixed(2))}>
        <div className="h-full rounded-full bg-primary transition-[width] duration-300" style={{ width: `${ratio}%` }} />
      </div>
    </div>
  )
}

export function MaskedAccount({ account, canReveal }: { account?: string | null; canReveal: boolean }) {
  const [visible, setVisible] = useState(false)
  if (!account) return <span className="text-muted-foreground">Not provided</span>
  if (!canReveal) return <span className="font-mono text-sm">{account}</span>
  return (
    <span className="inline-flex items-center gap-2">
      <span className="font-mono text-sm">{visible ? account : "•••• ••••"}</span>
      <button type="button" className="rounded-md p-1 text-muted-foreground transition hover:bg-secondary hover:text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50" aria-label={visible ? "Hide bank account" : "Show bank account"} onClick={() => setVisible((current) => !current)}>
        {visible ? <EyeOff size={14} aria-hidden="true" /> : <Eye size={14} aria-hidden="true" />}
      </button>
    </span>
  )
}

export function PaymentModeBadge({ mode, label }: { mode: string; label?: string }) {
  return <StatusBadge value={label ?? paymentModeLabels[mode.toUpperCase()] ?? titleCase(mode)} tone="info" />
}

export function FirstPremiumBadge({ proposalNumber }: { proposalNumber?: string | null }) {
  return <span className="inline-flex items-center gap-1 rounded-full border border-amber-300 bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-900" title={proposalNumber ? `First premium for proposal ${proposalNumber}` : "First premium commitment"}><ShieldCheck size={13} aria-hidden="true" />First premium</span>
}

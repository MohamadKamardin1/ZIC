import { formatMoney } from "../../lib/commitmentsDisplay"
import { StatusBadge, type StatusTone } from "../ui/StatusBadge"

const PLAN_STATUS_LABELS: Record<string, string> = {
  CREATED: "Created",
  ACTIVE: "Active",
  COMPLETED: "Completed",
  TERMINATED: "Terminated",
  CANCELLED: "Cancelled",
}

const PLAN_STATUS_TONES: Record<string, StatusTone> = {
  CREATED: "info",
  ACTIVE: "success",
  COMPLETED: "success",
  TERMINATED: "danger",
  CANCELLED: "neutral",
}

const ITEM_STATUS_LABELS: Record<string, string> = {
  SCHEDULED: "Scheduled",
  PAYMENT_PENDING: "Payment pending",
  PAID: "Paid",
  MISSED: "Missed",
  WAIVED: "Waived",
}

const ITEM_STATUS_TONES: Record<string, StatusTone> = {
  SCHEDULED: "info",
  PAYMENT_PENDING: "warning",
  PAID: "success",
  MISSED: "danger",
  WAIVED: "neutral",
}

function titleCase(value: string): string {
  return value.toLowerCase().split(/[\s_]+/).map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" ")
}

/** True when the string looks like a UUID, so a missing display label never leaks raw ids to the user. */
function isUuidLike(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)
}

export function planStatusLabel(status?: string | null, statusDisplay?: string | null): string {
  if (statusDisplay && !isUuidLike(statusDisplay)) return statusDisplay
  const normalized = String(status ?? "").trim().toUpperCase()
  if (isUuidLike(normalized)) return "—"
  return PLAN_STATUS_LABELS[normalized] ?? (normalized ? titleCase(normalized) : "—")
}

export function planStatusTone(status?: string | null): StatusTone {
  return PLAN_STATUS_TONES[String(status ?? "").trim().toUpperCase()] ?? "neutral"
}

export function PlanStatusBadge({ status, statusDisplay, className = "" }: { status?: string | null; statusDisplay?: string | null; className?: string }) {
  return <StatusBadge value={planStatusLabel(status, statusDisplay)} tone={planStatusTone(status)} className={className} />
}

export function itemStatusLabel(status?: string | null, statusDisplay?: string | null): string {
  if (statusDisplay && !isUuidLike(statusDisplay)) return statusDisplay
  const normalized = String(status ?? "").trim().toUpperCase()
  if (isUuidLike(normalized)) return "—"
  return ITEM_STATUS_LABELS[normalized] ?? (normalized ? titleCase(normalized) : "—")
}

export function itemStatusTone(status?: string | null): StatusTone {
  return ITEM_STATUS_TONES[String(status ?? "").trim().toUpperCase()] ?? "neutral"
}

export function ItemStatusBadge({ status, statusDisplay, className = "" }: { status?: string | null; statusDisplay?: string | null; className?: string }) {
  return <StatusBadge value={itemStatusLabel(status, statusDisplay)} tone={itemStatusTone(status)} className={className} />
}

export type MIMoneyVariant = "payable" | "paid" | "balance"

const MONEY_TONES: Record<MIMoneyVariant, string> = {
  payable: "text-slate-700",
  paid: "text-emerald-700 font-extrabold",
  balance: "text-[var(--brand)]",
}

export function MoneyCell({ value, currency = "TZS", variant = "payable", label, className = "" }: { value: string | number | null | undefined; currency?: string | null; variant?: MIMoneyVariant; label?: string; className?: string }) {
  const display = formatMoney(value, currency || "TZS")
  return (
    <span className={`tabular-nums ${MONEY_TONES[variant]} ${className}`} aria-label={label ? `${label}: ${display}` : display}>
      {display}
    </span>
  )
}

export function ProgressCell({ paid, maturityValue, currency = "TZS", label = "Payout progress", className = "" }: { paid: string | number | null | undefined; maturityValue: string | number | null | undefined; currency?: string | null; label?: string; className?: string }) {
  const total = Number(maturityValue ?? 0)
  const safeTotal = Number.isFinite(total) && total > 0 ? total : 0
  const safePaid = Number.isFinite(Number(paid ?? 0)) ? Math.max(0, Number(paid ?? 0)) : 0
  const percent = safeTotal > 0 ? Math.min(100, (safePaid / safeTotal) * 100) : 0
  const fillClass = percent >= 100 ? "bg-emerald-500" : percent > 0 ? "bg-[var(--brand)]" : "bg-slate-200"
  return (
    <div className={`flex items-center gap-2 ${className}`} role="progressbar" aria-label={label} aria-valuenow={Math.round(percent)} aria-valuemin={0} aria-valuemax={100}>
      <div className="h-2 min-w-[72px] flex-1 overflow-hidden rounded-full bg-slate-200">
        <div className={`h-full rounded-full ${fillClass}`} style={{ width: `${percent}%` }} />
      </div>
      <span className="tabular-nums text-xs font-semibold">{percent.toFixed(0)}%</span>
      <span className="tabular-nums text-xs text-[var(--muted-foreground)]" aria-hidden="true">
        {formatMoney(safePaid, currency || "TZS")} / {formatMoney(safeTotal, currency || "TZS")}
      </span>
    </div>
  )
}

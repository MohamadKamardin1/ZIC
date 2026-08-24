import { StatusBadge, type StatusTone } from "../ui/StatusBadge"

export type ExpiryLevel = "valid" | "expiring" | "expired"

export interface ExpiryResult {
  level: ExpiryLevel
  tone: StatusTone
  label: string
  detail: string
  days: number
}

function parseDate(value?: string | null): Date | null {
  if (!value) return null
  const match = String(value).match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (!match) return null
  return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]))
}

function startOfDay(value: Date): Date {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate())
}

/**
 * Resolve the expiry warning for a proposal.
 *
 * - no expiry date          → "valid"    (hidden by the component)
 * - expired before today    → "expired"  (red)
 * - today up to 7 days out  → "expiring" (amber window)
 * - more than a week away   → "valid"    (neutral, shows the date)
 */
export function expiryWarning(expiryDate?: string | null, today: Date = new Date()): ExpiryResult {
  const expiry = parseDate(expiryDate)
  if (!expiry) return { level: "valid", tone: "neutral", label: "No expiry", detail: "", days: Infinity }

  const now = startOfDay(today)
  const day = 86_400_000
  const days = Math.round((expiry.getTime() - now.getTime()) / day)

  if (days < 0) {
    return {
      level: "expired",
      tone: "danger",
      label: "Expired",
      detail: `${Math.abs(days)} day${Math.abs(days) === 1 ? "" : "s"} past expiry`,
      days,
    }
  }
  if (days <= 7) {
    return {
      level: "expiring",
      tone: "warning",
      label: days === 0 ? "Expires today" : `Expires in ${days} day${days === 1 ? "" : "s"}`,
      detail: `Expiry ${expiryDate}`,
      days,
    }
  }
  return {
    level: "valid",
    tone: "neutral",
    label: "Valid",
    detail: `Expiry ${expiryDate}`,
    days,
  }
}

export function ExpiryWarning({
  expiryDate,
  today = new Date(),
  showDetail = true,
  className = "",
}: {
  expiryDate?: string | null
  today?: Date
  showDetail?: boolean
  className?: string
}) {
  const warning = expiryWarning(expiryDate, today)
  if (!expiryDate) return null
  return (
    <span className={`inline-flex items-center gap-2 ${className}`} data-expiry-warning={warning.level}>
      <StatusBadge value={warning.label} tone={warning.tone} />
      {showDetail && warning.detail && <span className="text-xs text-[var(--muted-foreground)]">{warning.detail}</span>}
    </span>
  )
}

export default ExpiryWarning

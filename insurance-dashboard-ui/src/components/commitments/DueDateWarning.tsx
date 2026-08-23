import { StatusBadge, type StatusTone } from "../ui/StatusBadge"

export type DueDateWarningLevel = "on-time" | "in-grace" | "overdue" | "lapsed"

export interface DueDateWarningResult {
  level: DueDateWarningLevel
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

function daysBetween(later: Date, earlier: Date): number {
  return Math.max(0, Math.round((startOfDay(later).getTime() - startOfDay(earlier).getTime()) / 86_400_000))
}

/**
 * Resolve the due-date warning level for a commitment.
 *
 * - before due date            → "on-time"  (neutral)
 * - between due and grace date → "in-grace" (amber)
 * - between grace and lapse    → "overdue"  (red)
 * - after lapse date           → "lapsed"   (red)
 */
export function dueDateWarning(
  dueDate?: string | null,
  graceDate?: string | null,
  lapseDate?: string | null,
  today: Date = new Date(),
): DueDateWarningResult {
  const due = parseDate(dueDate)
  if (!due) return { level: "on-time", tone: "neutral", label: "No due date", detail: "", days: 0 }

  const grace = parseDate(graceDate)
  const lapse = parseDate(lapseDate)
  const now = startOfDay(today)

  if (lapse && now > lapse) {
    return {
      level: "lapsed",
      tone: "danger",
      label: "Lapsed",
      detail: `${daysBetween(now, lapse)} days past lapse`,
      days: daysBetween(now, lapse),
    }
  }
  if (grace && now > grace) {
    return {
      level: "overdue",
      tone: "danger",
      label: "Overdue",
      detail: `${daysBetween(now, grace)} days past grace`,
      days: daysBetween(now, grace),
    }
  }
  if (now > due) {
    return {
      level: "in-grace",
      tone: "warning",
      label: "In grace",
      detail: `${daysBetween(now, due)} days past due`,
      days: daysBetween(now, due),
    }
  }
  return {
    level: "on-time",
    tone: "neutral",
    label: "On time",
    detail: `Due ${dueDate}`,
    days: daysBetween(due, now),
  }
}

export function DueDateWarning({
  dueDate,
  graceDate,
  lapseDate,
  today = new Date(),
  showDetail = true,
  className = "",
}: {
  dueDate?: string | null
  graceDate?: string | null
  lapseDate?: string | null
  today?: Date
  showDetail?: boolean
  className?: string
}) {
  const warning = dueDateWarning(dueDate, graceDate, lapseDate, today)
  return (
    <span className={`inline-flex items-center gap-2 ${className}`} data-due-date-warning="true">
      <StatusBadge value={warning.label} tone={warning.tone} />
      {showDetail && warning.detail && <span className="text-xs text-[var(--muted-foreground)]">{warning.detail}</span>}
    </span>
  )
}

export default DueDateWarning
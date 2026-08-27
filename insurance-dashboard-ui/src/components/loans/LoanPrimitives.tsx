import { ArrowDownToLine, Banknote, CheckCircle2, CircleAlert, CircleDot, FileText, HandCoins, RotateCcw } from "lucide-react"
import { formatMoney } from "../../lib/commitmentsDisplay"
import { StatusBadge, type StatusTone } from "../ui/StatusBadge"
import type { LoanRecord } from "../../lib/loans"

const STATUS_LABELS: Record<string, string> = {
  REQUESTED: "Requested",
  APPROVED: "Approved",
  DISBURSED: "Disbursed",
  ACTIVE: "Active",
  PARTIALLY_REPAID: "Partially repaid",
  SETTLED: "Settled",
  DEFAULTED: "Defaulted",
  OFFSET_ON_SURRENDER: "Offset on surrender",
  OFFSET_ON_MATURITY: "Offset on maturity",
  OFFSET_ON_CLAIM: "Offset on claim",
  CLOSED: "Closed",
  REJECTED: "Rejected",
}

const STATUS_TONES: Record<string, StatusTone> = {
  REQUESTED: "warning",
  APPROVED: "info",
  DISBURSED: "info",
  ACTIVE: "success",
  PARTIALLY_REPAID: "success",
  SETTLED: "neutral",
  DEFAULTED: "danger",
  OFFSET_ON_SURRENDER: "neutral",
  OFFSET_ON_MATURITY: "neutral",
  OFFSET_ON_CLAIM: "neutral",
  CLOSED: "neutral",
  REJECTED: "danger",
}

function titleCase(value: string): string {
  return value.toLowerCase().split(/[\s_]+/).map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" ")
}

export function loanStatusLabel(status?: string | null, statusDisplay?: string | null): string {
  if (!status && !statusDisplay) return "—"
  if (statusDisplay && !/^[0-9a-f]{8}-[0-9a-f-]{27,}$/i.test(statusDisplay)) return statusDisplay
  const normalized = String(status ?? "").toUpperCase()
  return STATUS_LABELS[normalized] ?? titleCase(normalized)
}

export function loanStatusTone(status?: string | null): StatusTone {
  return STATUS_TONES[String(status ?? "").toUpperCase()] ?? "neutral"
}

export function LoanStatusBadge({ status, statusDisplay, className = "" }: { status?: string | null; statusDisplay?: string | null; className?: string }) {
  return <StatusBadge value={loanStatusLabel(status, statusDisplay)} tone={loanStatusTone(status)} className={className} />
}

export function MoneyCell({ value, currency = "TZS", label, className = "" }: { value: string | number | null | undefined; currency?: string | null; label?: string; className?: string }) {
  const display = formatMoney(value, currency || "TZS")
  return <span className={`tabular-nums ${className}`} aria-label={label ? `${label}: ${display}` : display}>{display}</span>
}

export function ProgressCell({ principal, balance, currency = "TZS", className = "" }: { principal: string | number | null | undefined; balance: string | number | null | undefined; currency?: string | null; className?: string }) {
  const principalValue = Number(principal ?? 0)
  const balanceValue = Number(balance ?? 0)
  const safePrincipal = Number.isFinite(principalValue) && principalValue > 0 ? principalValue : 0
  const safeBalance = Number.isFinite(balanceValue) && balanceValue >= 0 ? balanceValue : 0
  const remainingPercent = safePrincipal > 0 ? Math.max(0, Math.min(100, (safeBalance / safePrincipal) * 100)) : 0
  const paidPercent = Math.max(0, Math.min(100, 100 - remainingPercent))
  return (
    <div className={`min-w-40 space-y-1 ${className}`}>
      <div className="flex items-center justify-between gap-2 text-xs">
        <span className="font-semibold text-[var(--foreground)]">{formatMoney(safeBalance, currency || "TZS")}</span>
        <span className="text-[var(--muted-foreground)]">{paidPercent.toFixed(0)}% paid</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-[var(--muted)]" role="progressbar" aria-label="Loan balance remaining" aria-valuemin={0} aria-valuemax={safePrincipal} aria-valuenow={safeBalance}>
        <div className={`h-full rounded-full transition-[width] duration-200 ${remainingPercent > 75 ? "bg-[var(--warning)]" : remainingPercent > 0 ? "bg-[var(--primary)]" : "bg-[var(--success)]"}`} style={{ width: `${remainingPercent}%` }} />
      </div>
      <span className="block text-[11px] text-[var(--muted-foreground)]">of {formatMoney(safePrincipal, currency || "TZS")}</span>
    </div>
  )
}

type LoanAction = "approve" | "disburse" | "repay" | "offset" | "reverse" | "reject" | "print"

const ACTION_CONFIG: Record<LoanAction, { label: string; permission: string; tone?: "default" | "danger"; Icon: typeof Banknote }> = {
  approve: { label: "Approve", permission: "ol_loans.approve", Icon: CheckCircle2 },
  disburse: { label: "Disburse", permission: "ol_loans.disburse", Icon: ArrowDownToLine },
  repay: { label: "Repay", permission: "ol_loans.repay", Icon: HandCoins },
  offset: { label: "Offset", permission: "ol_loans.offset", Icon: Banknote },
  reverse: { label: "Reverse", permission: "ol_loans.reverse", tone: "danger", Icon: RotateCcw },
  reject: { label: "Reject", permission: "ol_loans.approve", tone: "danger", Icon: CircleAlert },
  print: { label: "Print", permission: "ol_loans.print", Icon: FileText },
}

const STATUS_ACTIONS: Record<string, LoanAction[]> = {
  REQUESTED: ["approve", "reject", "print"],
  APPROVED: ["disburse", "print"],
  DISBURSED: ["repay", "offset", "print"],
  ACTIVE: ["repay", "offset", "print"],
  PARTIALLY_REPAID: ["repay", "offset", "print"],
  DEFAULTED: ["repay", "offset", "print"],
  SETTLED: ["print"],
  OFFSET_ON_SURRENDER: ["print"],
  OFFSET_ON_MATURITY: ["print"],
  OFFSET_ON_CLAIM: ["print"],
  CLOSED: ["print"],
  REJECTED: ["print"],
}

export interface ActionButtonGroupProps {
  loan: Pick<LoanRecord, "status" | "allowedActions"> | { status: string; allowedActions?: string[] }
  onAction: (action: LoanAction) => void
  permissions?: string[]
  hasPermission?: (permission: string) => boolean
  actions?: LoanAction[]
  className?: string
}

export function ActionButtonGroup({ loan, onAction, permissions, hasPermission, actions, className = "" }: ActionButtonGroupProps) {
  const status = String(loan.status ?? "").toUpperCase()
  const backendAllowed = Array.isArray(loan.allowedActions) ? new Set(loan.allowedActions.map((value) => value.toLowerCase())) : null
  const candidates = actions ?? STATUS_ACTIONS[status] ?? []
  const visible = candidates.filter((action) => {
    if (backendAllowed && !backendAllowed.has(action)) return false
    const permission = ACTION_CONFIG[action].permission
    if (hasPermission) return hasPermission(permission)
    if (permissions) return permissions.includes(permission) || permissions.includes(action)
    return true
  })

  if (visible.length === 0) return null
  return (
    <div className={`flex flex-wrap items-center gap-2 ${className}`} aria-label="Loan actions">
      {visible.map((action) => {
        const config = ACTION_CONFIG[action]
        const Icon = config.Icon
        return <button key={action} type="button" className={`button-secondary inline-flex min-h-9 items-center gap-1.5 text-xs ${config.tone === "danger" ? "!text-[var(--destructive)]" : ""}`} onClick={() => onAction(action)}><Icon size={14} aria-hidden="true" />{config.label}</button>
      })}
    </div>
  )
}

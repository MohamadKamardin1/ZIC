import { CircleAlert, ShieldCheck, User, Users } from "lucide-react"
import { formatMoney } from "../../lib/commitmentsDisplay"
import { StatusBadge, type StatusTone } from "../ui/StatusBadge"

const STATUS_LABELS: Record<string, string> = {
  REGISTERED: "Registered",
  PENDING_MEDICAL: "Pending Medical",
  ASSESSMENT: "In Assessment",
  ASSESSED: "Assessed",
  REQUISITION: "In Requisition",
  REQUISITIONED: "Requisitioned",
  APPROVED: "Approved",
  SETTLED: "Settled",
  REJECTED: "Rejected",
  CANCELLED: "Cancelled",
}

const STATUS_TONES: Record<string, StatusTone> = {
  REGISTERED: "info",
  PENDING_MEDICAL: "warning",
  ASSESSMENT: "warning",
  ASSESSED: "info",
  REQUISITION: "warning",
  REQUISITIONED: "info",
  APPROVED: "info",
  SETTLED: "success",
  REJECTED: "danger",
  CANCELLED: "neutral",
}

const CLAIMANT_LABELS: Record<string, string> = {
  POLICYHOLDER: "Policyholder",
  INSURED: "Insured",
  DEPENDENT: "Dependent",
}

const CLAIMANT_TONES: Record<string, StatusTone> = {
  POLICYHOLDER: "info",
  INSURED: "success",
  DEPENDENT: "neutral",
}

function titleCase(value: string): string {
  return value.toLowerCase().split(/[\s_]+/).map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" ")
}

/** True when the string looks like a UUID, so a missing display label never leaks raw ids to the user. */
function isUuidLike(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)
}

export function claimStatusLabel(status?: string | null, statusDisplay?: string | null): string {
  if (statusDisplay && !isUuidLike(statusDisplay)) return statusDisplay
  const normalized = String(status ?? "").trim().toUpperCase()
  if (isUuidLike(normalized)) return "—"
  return STATUS_LABELS[normalized] ?? (normalized ? titleCase(normalized) : "—")
}

export function claimStatusTone(status?: string | null): StatusTone {
  return STATUS_TONES[String(status ?? "").trim().toUpperCase()] ?? "neutral"
}

export function ClaimStatusBadge({ status, statusDisplay, className = "" }: { status?: string | null; statusDisplay?: string | null; className?: string }) {
  return <StatusBadge value={claimStatusLabel(status, statusDisplay)} tone={claimStatusTone(status)} className={className} />
}

export function claimantLabel(claimantType?: string | null, claimantTypeDisplay?: string | null): string {
  if (claimantTypeDisplay && !isUuidLike(claimantTypeDisplay)) return claimantTypeDisplay
  const normalized = String(claimantType ?? "").trim().toUpperCase()
  if (isUuidLike(normalized)) return "—"
  return CLAIMANT_LABELS[normalized] ?? (normalized ? titleCase(normalized) : "—")
}

export function claimantTone(claimantType?: string | null): StatusTone {
  return CLAIMANT_TONES[String(claimantType ?? "").trim().toUpperCase()] ?? "neutral"
}

export function ClaimantBadge({ claimantType, claimantTypeDisplay, className = "" }: { claimantType?: string | null; claimantTypeDisplay?: string | null; className?: string }) {
  return <StatusBadge value={claimantLabel(claimantType, claimantTypeDisplay)} tone={claimantTone(claimantType)} className={className} />
}

export type MoneyVariant = "calculated" | "approved" | "net"

const MONEY_TONES: Record<MoneyVariant, string> = {
  calculated: "text-slate-700",
  approved: "text-[var(--brand)]",
  net: "text-emerald-700 font-extrabold",
}

export function MoneyCell({ value, currency = "TZS", variant = "calculated", label, className = "" }: { value: string | number | null | undefined; currency?: string | null; variant?: MoneyVariant; label?: string; className?: string }) {
  const display = formatMoney(value, currency || "TZS")
  return (
    <span className={`tabular-nums ${MONEY_TONES[variant]} ${className}`} aria-label={label ? `${label}: ${display}` : display}>
      {display}
    </span>
  )
}

export interface ProgressionStep {
  key: string
  label: string
  complete: boolean
  hint?: string
}

export function ProgressionGuardBanner({ steps, blockedActionLabel = "proceed", className = "" }: { steps: ProgressionStep[]; blockedActionLabel?: string; className?: string }) {
  const incomplete = steps.filter((step) => !step.complete)
  if (incomplete.length === 0) return null
  return (
    <div className={`flex items-start gap-3 rounded-[10px] border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950 ${className}`} role="alert">
      <CircleAlert className="mt-0.5 shrink-0" size={18} aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <p className="font-bold">Complete the mandatory steps before you can {blockedActionLabel}.</p>
        <ul className="mt-2 list-disc space-y-1 pl-5 leading-5">
          {incomplete.map((step) => (
            <li key={step.key}>
              <span className="font-bold">{step.label}</span>
              {step.hint ? <span className="text-amber-800"> — {step.hint}</span> : null}
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

export function ClaimantIdentity({ claimant }: { claimant: { claimantType?: string | null; claimantTypeDisplay?: string | null; name?: string | null; relationship?: string | null } | null }) {
  if (!claimant || !claimant.name) {
    return (
      <span className="inline-flex items-center gap-1.5 text-sm text-[var(--muted-foreground)]">
        <Users size={14} aria-hidden="true" /> No claimant recorded
      </span>
    )
  }
  return (
    <span className="inline-flex flex-wrap items-center gap-1.5 text-sm">
      <User size={14} aria-hidden="true" />
      <span className="font-semibold">{claimant.name}</span>
      <ClaimantBadge claimantType={claimant.claimantType} claimantTypeDisplay={claimant.claimantTypeDisplay} />
      {claimant.relationship ? <span className="text-xs text-[var(--muted-foreground)]">({claimant.relationship})</span> : null}
    </span>
  )
}

export function ClaimMoneySummary({ calculated, approved, net, currency = "TZS" }: { calculated: string | number | null | undefined; approved: string | number | null | undefined; net: string | number | null | undefined; currency?: string | null }) {
  return (
    <div className="grid gap-3 sm:grid-cols-3" aria-label="Claim financial summary">
      <div className="rounded-[10px] border p-3">
        <p className="text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">Calculated</p>
        <p className="mt-2 font-extrabold"><MoneyCell value={calculated} currency={currency} variant="calculated" label="Calculated amount" /></p>
      </div>
      <div className="rounded-[10px] border p-3">
        <p className="text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">Approved</p>
        <p className="mt-2 font-extrabold"><MoneyCell value={approved} currency={currency} variant="approved" label="Approved amount" /></p>
      </div>
      <div className="rounded-[10px] border border-emerald-200 bg-emerald-50 p-3 text-emerald-950">
        <p className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-[0.08em]"><ShieldCheck size={13} aria-hidden="true" />Net Payout</p>
        <p className="mt-2 font-extrabold"><MoneyCell value={net} currency={currency} variant="net" label="Net payout" /></p>
      </div>
    </div>
  )
}

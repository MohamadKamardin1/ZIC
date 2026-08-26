import { Check, Copy, ShieldCheck } from "lucide-react"
import { useState } from "react"
import { formatMoney } from "../../lib/commitmentsDisplay"
import { renderFk } from "../../lib/display"
import { StatusBadge, type StatusTone } from "../ui/StatusBadge"

export interface PolicyStatusOption {
  value: string
  label: string
  meta?: Record<string, unknown>
}

const STATUS_TONES: Record<string, StatusTone> = {
  ACTIVE: "success",
  GRACE: "warning",
  LAPSED: "danger",
  PAID_UP: "info",
  SURRENDER_PENDING: "warning",
  SURRENDERED: "neutral",
  MATURED_PENDING_PAYMENT: "info",
  MATURED: "success",
  EXPIRED: "danger",
  CANCELLED: "danger",
  CLAIM_SETTLED: "danger",
  TERMINATED: "neutral",
}

const STATUS_LABELS: Record<string, string> = {
  ACTIVE: "Active",
  GRACE: "Grace period",
  LAPSED: "Lapsed",
  PAID_UP: "Paid-up",
  SURRENDER_PENDING: "Surrender pending",
  SURRENDERED: "Surrendered",
  MATURED_PENDING_PAYMENT: "Maturity pending payment",
  MATURED: "Matured",
  EXPIRED: "Expired",
  CANCELLED: "Cancelled",
  CLAIM_SETTLED: "Claim settled",
  TERMINATED: "Terminated",
}

function titleCase(value: string): string {
  return value.toLowerCase().split(/[\s_]+/).map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" ")
}

function toneFromOption(option?: PolicyStatusOption): StatusTone | undefined {
  const configured = String(option?.meta?.badge_type ?? option?.meta?.tone ?? "").toUpperCase()
  if (["POSITIVE", "SUCCESS", "GREEN"].includes(configured)) return "success"
  if (["WARNING", "AMBER", "CAUTION"].includes(configured)) return "warning"
  if (["NEGATIVE", "DANGER", "RED"].includes(configured)) return "danger"
  if (["INFO", "BLUE"].includes(configured)) return "info"
  if (["NEUTRAL", "GREY", "GRAY"].includes(configured)) return "neutral"
  return undefined
}

export function policyStatusLabel(status?: string | null, statusOptions: PolicyStatusOption[] = []): string {
  if (!status) return "—"
  const option = statusOptions.find((item) => item.value.toUpperCase() === status.toUpperCase())
  return option?.label ?? STATUS_LABELS[status.toUpperCase()] ?? titleCase(status)
}

export function policyStatusTone(status?: string | null, statusOptions: PolicyStatusOption[] = []): StatusTone {
  if (!status) return "neutral"
  const option = statusOptions.find((item) => item.value.toUpperCase() === status.toUpperCase())
  return toneFromOption(option) ?? STATUS_TONES[status.toUpperCase()] ?? "neutral"
}

export function PolicyStatusBadge({ status, statusOptions, className = "" }: { status?: string | null; statusOptions?: PolicyStatusOption[]; className?: string }) {
  return <StatusBadge value={policyStatusLabel(status, statusOptions)} tone={policyStatusTone(status, statusOptions)} className={className} />
}

export type LifeStage = "GRACE" | "LAPSE" | "PAID_UP"

export function LifeStageBadge({ stage, status, className = "" }: { stage?: LifeStage | null; status?: string | null; className?: string }) {
  const inferred: LifeStage | null = stage ?? (status?.toUpperCase() === "PAID_UP" ? "PAID_UP" : status?.toUpperCase() === "LAPSED" ? "LAPSE" : null)
  if (!inferred) return null
  const values: Record<LifeStage, { label: string; tone: StatusTone }> = {
    GRACE: { label: "Grace period", tone: "warning" },
    LAPSE: { label: "Lapse", tone: "danger" },
    PAID_UP: { label: "Paid-up", tone: "info" },
  }
  return <StatusBadge value={values[inferred].label} tone={values[inferred].tone} className={className} />
}

export function MoneyCell({ value, currency = "TZS", className = "" }: { value: string | number | null | undefined; currency?: string | null; className?: string }) {
  const display = formatMoney(value, currency || "TZS")
  return <span className={`tabular-nums ${className}`} aria-label={display}>{display}</span>
}

export interface PolicyHeaderData {
  policyNumber: string
  policyholderDisplay: string
  policyholderIdentity?: string | null
  productPlanDisplay: string
  sumAssured: string | number | null
  premiumAmount: string | number | null
  premiumFrequency?: string | null
  currency?: string | null
  status: string
  statusDisplay?: string | null
  riskCommencementDate?: string | null
  maturityDate?: string | null
}

function dateDisplay(value?: string | null): string {
  if (!value) return "—"
  const date = new Date(`${value.slice(0, 10)}T00:00:00`)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat("en-GB", { dateStyle: "medium" }).format(date)
}

function HeaderMetric({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="min-w-0 rounded-xl border border-[var(--border)] bg-[var(--card)]/70 p-3"><p className="text-[11px] font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">{label}</p><div className="mt-1 truncate text-sm font-semibold text-[var(--foreground)]">{children}</div></div>
}

export function PolicyHeader({ data, statusOptions = [], actionSlot }: { data: PolicyHeaderData; statusOptions?: PolicyStatusOption[]; actionSlot?: React.ReactNode }) {
  const [copied, setCopied] = useState(false)
  const copyPolicyNumber = async () => {
    try {
      await navigator.clipboard.writeText(data.policyNumber)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1600)
    } catch {
      setCopied(false)
    }
  }

  return (
    <section className="surface-card overflow-hidden" aria-label="Policy summary">
      <div className="bg-gradient-to-r from-[var(--primary)] to-[#4050b8] px-5 py-5 text-white sm:px-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-white/70">Ordinary Life Policy</p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <h1 className="truncate text-2xl font-extrabold tracking-tight">{renderFk(data.policyNumber, undefined, "Policy")}</h1>
              <button type="button" onClick={() => void copyPolicyNumber()} className="inline-flex min-h-8 items-center gap-1 rounded-md border border-white/25 px-2 text-xs font-semibold transition hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white" aria-label={`Copy policy number ${data.policyNumber}`}>
                {copied ? <Check size={14} aria-hidden="true" /> : <Copy size={14} aria-hidden="true" />}
                {copied ? "Copied" : "Copy"}
              </button>
            </div>
            <p className="mt-1 text-sm text-white/80">{data.policyholderDisplay}{data.policyholderIdentity ? ` · ${data.policyholderIdentity}` : ""}</p>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-2">
            <PolicyStatusBadge status={data.status} statusOptions={statusOptions} />
            {actionSlot}
          </div>
        </div>
      </div>
      <div className="grid gap-3 p-4 sm:grid-cols-2 xl:grid-cols-5">
        <HeaderMetric label="Product / plan">{data.productPlanDisplay}</HeaderMetric>
        <HeaderMetric label="Sum assured"><MoneyCell value={data.sumAssured} currency={data.currency} /></HeaderMetric>
        <HeaderMetric label="Premium"><MoneyCell value={data.premiumAmount} currency={data.currency} /> <span className="text-xs font-medium text-[var(--muted-foreground)]">{data.premiumFrequency ?? ""}</span></HeaderMetric>
        <HeaderMetric label="Issue date">{dateDisplay(data.riskCommencementDate)}</HeaderMetric>
        <HeaderMetric label="Maturity date">{dateDisplay(data.maturityDate)}</HeaderMetric>
      </div>
      <div className="flex items-center gap-2 border-t border-[var(--border)] px-4 py-3 text-xs text-[var(--muted-foreground)] sm:px-6">
        <ShieldCheck size={14} className="text-[var(--success)]" aria-hidden="true" />
        Contract details are sourced from the immutable issuance snapshot.
      </div>
    </section>
  )
}

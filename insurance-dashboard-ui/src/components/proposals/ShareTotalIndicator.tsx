import { CheckCircle2, XCircle } from "lucide-react"

const TOTAL_TARGET = 100
/** Beneficiary shares are stored to four decimals; tolerate float dust. */
const TOLERANCE = 0.0001

export type ShareTotalState = "valid" | "under" | "over"

export function shareTotal(totalPercent: number): ShareTotalState {
  if (Math.abs(totalPercent - TOTAL_TARGET) <= TOLERANCE) return "valid"
  return totalPercent < TOTAL_TARGET ? "under" : "over"
}

/**
 * Live total of beneficiary shares against the mandatory 100% target.
 *
 * The backend enforces the same rule (``PROPOSAL_BENEFICIARY_SHARES_INVALID``);
 * this indicator teaches the operator before they submit.
 */
export function ShareTotalIndicator({
  shares,
  className = "",
}: {
  shares: number[]
  className?: string
}) {
  const total = shares.reduce((sum, value) => sum + (Number.isFinite(value) ? value : 0), 0)
  const state = shareTotal(total)
  const valid = state === "valid"
  const Icon = valid ? CheckCircle2 : XCircle
  const toneClass = valid ? "text-[var(--success)]" : state === "under" ? "text-[var(--warning)]" : "text-[var(--destructive)]"

  return (
    <span
      className={`inline-flex items-center gap-2 text-[13px] font-semibold ${toneClass} ${className}`}
      data-share-total={state}
      data-share-value={total.toFixed(4)}
      role="status"
    >
      <Icon size={14} aria-hidden="true" />
      <span>
        Total {total.toFixed(2)}% of {TOTAL_TARGET}%
        {valid
          ? " — ready to save"
          : state === "under"
            ? ` — allocate ${(TOTAL_TARGET - total).toFixed(2)}% more`
            : ` — reduce ${(total - TOTAL_TARGET).toFixed(2)}%`}
      </span>
    </span>
  )
}

export default ShareTotalIndicator

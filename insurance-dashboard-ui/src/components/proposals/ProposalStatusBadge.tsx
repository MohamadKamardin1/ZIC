import { StatusBadge, type StatusTone } from "../ui/StatusBadge"

/**
 * Parameter-driven tone map for proposal status catalog codes.
 *
 * The status list itself lives in OL Parameters (seeded by
 * ``seed_ol_proposal_statuses``); these tones mirror the documented lifecycle:
 * work-in-progress states are informational, gates are amber, terminal
 * outcomes are green or red.
 */
const PROPOSAL_STATUS_TONES: Record<string, StatusTone> = {
  DRAFT: "neutral",
  ENRICHMENT: "info",
  PENDING_UNDERWRITING: "warning",
  PAYMENT_READY: "info",
  AWAITING_FIRST_PREMIUM: "warning",
  CONVERTED: "success",
  CANCELLED: "danger",
  EXPIRED: "danger",
}

const PROPOSAL_STATUS_LABELS: Record<string, string> = {
  DRAFT: "Draft",
  ENRICHMENT: "Enrichment",
  PENDING_UNDERWRITING: "Pending underwriting",
  PAYMENT_READY: "Payment ready",
  AWAITING_FIRST_PREMIUM: "Awaiting first premium",
  CONVERTED: "Converted",
  CANCELLED: "Cancelled",
  EXPIRED: "Expired",
}

export function proposalStatusTone(status?: string | null): StatusTone {
  if (!status) return "neutral"
  return PROPOSAL_STATUS_TONES[status.toUpperCase()] ?? "neutral"
}

/** Human label for a status code; unknown parameterized codes fall back to Title Case. */
export function proposalStatusLabel(status?: string | null): string {
  if (!status) return "—"
  const known = PROPOSAL_STATUS_LABELS[status.toUpperCase()]
  if (known) return known
  return status
    .toLowerCase()
    .split(/[\s_]+/)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ")
}

export function ProposalStatusBadge({ status, className = "" }: { status?: string | null; className?: string }) {
  return <StatusBadge value={proposalStatusLabel(status)} tone={proposalStatusTone(status)} className={className} />
}

export default ProposalStatusBadge

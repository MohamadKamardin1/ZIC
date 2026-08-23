/**
 * OL Proposals — proposal-specific primitives.
 *
 * Prompt 1 foundation kit: parameter-driven status badge, expiry warning,
 * payment readiness checklist, first premium settlement card, and the
 * beneficiary share-total indicator.
 */

export { ProposalStatusBadge, proposalStatusTone, proposalStatusLabel } from "./ProposalStatusBadge"
export { ExpiryWarning, expiryWarning } from "./ExpiryWarning"
export type { ExpiryLevel, ExpiryResult } from "./ExpiryWarning"
export { ReadinessChecklist } from "./ReadinessChecklist"
export { FirstPremiumCard } from "./FirstPremiumCard"
export { ShareTotalIndicator, shareTotal } from "./ShareTotalIndicator"
export type { ShareTotalState } from "./ShareTotalIndicator"

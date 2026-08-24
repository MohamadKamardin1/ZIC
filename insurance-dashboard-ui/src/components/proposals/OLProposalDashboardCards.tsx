import { useNavigate } from "react-router-dom"
import { AlertTriangle, CalendarClock, CircleDollarSign } from "lucide-react"
import { useAccess } from "../../lib/access"
import { useProposalDashboardKpis } from "../../lib/proposalsHooks"
import { formatMoney } from "../../lib/commitmentsDisplay"

export interface OLProposalDashboardCardsProps {
  className?: string
}

/**
 * Staff oversight cards for the proposals register: Awaiting First Premium
 * (count + amount), Expiring in 7 Days, and Pending Underwriting. Each card
 * deep-links to the filtered proposals list. Hidden for users without
 * `ol_proposals.view`.
 */
export function OLProposalDashboardCards({ className = "" }: OLProposalDashboardCardsProps) {
  const navigate = useNavigate()
  const { hasPermission, isSuperAdmin } = useAccess()
  const kpis = useProposalDashboardKpis()

  if (!(isSuperAdmin || (hasPermission?.("ol_proposals.view") ?? false))) return null

  const openFiltered = (query: string) => navigate(`/ordinary-life/proposals${query}`)

  const cards = [
    {
      key: "awaiting_first_premium",
      label: "Awaiting First Premium",
      value: kpis.data ? kpis.data.awaitingFirstPremium.toLocaleString() : "—",
      helper: kpis.data ? formatMoney(kpis.data.awaitingFirstPremiumAmount) : "Unallocated premium",
      icon: CircleDollarSign,
      onOpen: () => openFiltered("?preset=awaiting_first_premium"),
      linkLabel: "View awaiting premium",
    },
    {
      key: "expiring_7_days",
      label: "Expiring in 7 Days",
      value: kpis.data ? kpis.data.expiringIn7Days.toLocaleString() : "—",
      helper: "Expiry date within a week",
      icon: CalendarClock,
      onOpen: () => openFiltered("?preset=expiring_7_days"),
      linkLabel: "View expiring",
    },
    {
      key: "pending_underwriting",
      label: "Pending Underwriting",
      value: kpis.data ? kpis.data.pendingUnderwriting.toLocaleString() : "—",
      helper: "Awaiting a UW decision",
      icon: AlertTriangle,
      onOpen: () => openFiltered("?preset=pending_underwriting"),
      linkLabel: "View pending decisions",
    },
  ]

  return (
    <section className={`grid gap-3 sm:grid-cols-2 xl:grid-cols-3 ${className}`} aria-label="Proposals oversight">
      {cards.map((card) => {
        const Icon = card.icon
        return (
          <article key={card.key} className="surface-card flex items-center gap-3 px-4 py-3" data-testid={`proposal-card-${card.key}`}>
            <span className="flex h-10 w-10 flex-none items-center justify-center rounded-[10px] bg-[var(--secondary)] text-[var(--primary)]">
              <Icon size={18} aria-hidden="true" />
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-semibold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">{card.label}</p>
              <p className="mt-0.5 text-lg font-bold tabular-nums text-[var(--foreground)]" data-testid={`card-value-${card.key}`}>{card.value}</p>
              <p className="text-xs text-[var(--muted-foreground)]">{card.helper}</p>
            </div>
            <button type="button" className="shrink-0 text-xs font-semibold text-[var(--primary)] underline-offset-2 outline-none transition hover:underline focus-visible:ring-2 focus-visible:ring-[var(--ring)]" onClick={card.onOpen} data-testid={`card-link-${card.key}`}>
              {card.linkLabel} →
            </button>
          </article>
        )
      })}
    </section>
  )
}

export default OLProposalDashboardCards

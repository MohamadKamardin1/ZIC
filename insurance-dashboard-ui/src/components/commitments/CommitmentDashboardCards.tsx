import { useNavigate } from "react-router-dom"
import { AlertTriangle, CircleDollarSign, ShieldCheck } from "lucide-react"
import { useAccess } from "../../lib/access"
import { useCommitmentKPIs } from "../../lib/commitmentsHooks"
import { formatMoney } from "../../lib/commitmentsDisplay"

export interface CommitmentDashboardCardsProps {
  className?: string
}

/**
 * Staff oversight cards: Overdue Commitments, Outstanding Premium, and
 * Approvals Pending (waivers). Each card deep-links to the filtered
 * commitments register. Hidden for users without `ol_commitments.view`.
 */
export function CommitmentDashboardCards({ className = "" }: CommitmentDashboardCardsProps) {
  const navigate = useNavigate()
  const { hasPermission, isSuperAdmin } = useAccess()
  const kpis = useCommitmentKPIs()

  if (!(isSuperAdmin || (hasPermission?.("ol_commitments.view") ?? false))) return null

  const openFiltered = (query: string) => navigate(`/ordinary-life/commitments${query}`)

  const cards = [
    {
      key: "overdue",
      label: "Overdue Commitments",
      value: kpis.data ? kpis.data.overdueCount.toLocaleString() : "—",
      helper: "Past the grace date",
      icon: AlertTriangle,
      onOpen: () => openFiltered("?overdue_only=true"),
      linkLabel: "View all overdue",
    },
    {
      key: "outstanding",
      label: "Outstanding Premium",
      value: kpis.data ? formatMoney(kpis.data.totalOutstanding) : "—",
      helper: "Unpaid balance",
      icon: CircleDollarSign,
      onOpen: () => openFiltered("?balance_only=true"),
      linkLabel: "View outstanding",
    },
    {
      key: "approvals",
      label: "Approvals Pending",
      value: kpis.data ? (kpis.data.approvalsPending ?? 0).toLocaleString() : "—",
      helper: "Waivers and exceptions",
      icon: ShieldCheck,
      onOpen: () => openFiltered("?approval_required=true"),
      linkLabel: "View approvals",
    },
  ]

  return (
    <section className={`grid gap-3 sm:grid-cols-2 xl:grid-cols-3 ${className}`} aria-label="Commitments oversight">
      {cards.map((card) => {
        const Icon = card.icon
        return (
          <article key={card.key} className="surface-card flex items-center gap-3 px-4 py-3">
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

export default CommitmentDashboardCards
import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import type { ReactNode } from "react"
import { HeroBanner } from "../components/dashboard/HeroBanner"
import {
  ClaimsCard,
  DebitedGauge,
  NotificationsPanel,
  PartnersCard,
  PoliciesCard,
  QuotationsChart,
  TodoWidget,
  LeadsWidget,
} from "../components/dashboard/widgets"
import { DashboardSkeleton } from "../components/shared/Skeleton"
import { getDashboard } from "../lib/api"
import { useAuth } from "../lib/auth"
import { CommitmentDashboardCards } from "../components/commitments/CommitmentDashboardCards"
import { OLProposalDashboardCards } from "../components/proposals/OLProposalDashboardCards"
import type { DashboardData } from "../lib/types"

export default function Dashboard() {
  const navigate = useNavigate()
  const { signOut } = useAuth()
  const [data, setData] = useState<DashboardData | null>(null)
  const [error, setError] = useState("")

  useEffect(() => {
    let active = true
    getDashboard()
      .then((d) => active && setData(d))
      .catch((e) => {
        if (!active) return
        const msg = e instanceof Error ? e.message : "Failed to load dashboard."
        if (msg.includes("Session expired") || msg.includes("401")) {
          signOut()
          navigate("/login", { replace: true })
          return
        }
        setError(msg)
      })
    return () => {
      active = false
    }
  }, [signOut, navigate])

  return (
    <>
      {error && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm font-medium text-destructive">
          {error}
        </div>
      )}

      {!data ? (
        <DashboardSkeleton />
      ) : (
        <div className="flex flex-col gap-5">
          <HeroBanner stats={data.hero} />

          <CommitmentDashboardCards />

          <OLProposalDashboardCards />

          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-4">
            <DashboardWidgetLink label="Open ordinary-life policies" route="/ordinary-life/policies" onNavigate={navigate}><PoliciesCard data={data.policies} /></DashboardWidgetLink>
            <DashboardWidgetLink label="Open claims" route="/ordinary-life/claims" onNavigate={navigate}><ClaimsCard data={data.claims} /></DashboardWidgetLink>
            <DashboardWidgetLink label="Open partners" route="/partners" onNavigate={navigate}><PartnersCard data={data.partners} /></DashboardWidgetLink>
            <DashboardWidgetLink label="Open receipts" route="/front-office/receipts" onNavigate={navigate}><DebitedGauge data={data.debited} /></DashboardWidgetLink>
          </div>

          <div className="grid grid-cols-1 gap-5 xl:grid-cols-4">
            <div className="xl:col-span-2">
              <DashboardWidgetLink label="Open quotations" route="/ordinary-life/quotations" onNavigate={navigate}><QuotationsChart data={data.quotations} /></DashboardWidgetLink>
            </div>
            <DashboardWidgetLink label="Open notifications" route="/notifications" onNavigate={navigate}><NotificationsPanel data={data.notifications} /></DashboardWidgetLink>
            <div className="flex flex-col gap-5">
              <DashboardWidgetLink label="Open tasks" route="/tasks" onNavigate={navigate}><TodoWidget todos={data.todos} /></DashboardWidgetLink>
              <DashboardWidgetLink label="Open onboarding leads" route="/onboarding" onNavigate={navigate}><LeadsWidget leads={data.leads} /></DashboardWidgetLink>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

function DashboardWidgetLink({ children, label, route, onNavigate }: { children: ReactNode; label: string; route: string; onNavigate: (route: string) => void }) {
  return <div role="link" tabIndex={0} aria-label={label} onClick={() => onNavigate(route)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onNavigate(route) } }} className="h-full cursor-pointer rounded-2xl outline-none transition hover:-translate-y-0.5 hover:shadow-md focus-visible:ring-2 focus-visible:ring-primary">{children}</div>
}


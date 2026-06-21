import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
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
import { getDashboard } from "../lib/api"
import { useAuth } from "../lib/auth"
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

          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-4">
            <PoliciesCard data={data.policies} />
            <ClaimsCard data={data.claims} />
            <PartnersCard data={data.partners} />
            <DebitedGauge data={data.debited} />
          </div>

          <div className="grid grid-cols-1 gap-5 xl:grid-cols-4">
            <div className="xl:col-span-2">
              <QuotationsChart data={data.quotations} />
            </div>
            <NotificationsPanel data={data.notifications} />
            <div className="flex flex-col gap-5">
              <TodoWidget todos={data.todos} />
              <LeadsWidget leads={data.leads} />
            </div>
          </div>
        </div>
      )}
    </>
  )
}

function DashboardSkeleton() {
  return (
    <div className="flex flex-col gap-5">
      <div className="h-28 animate-pulse rounded-2xl bg-muted" />
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-64 animate-pulse rounded-xl bg-muted" />
        ))}
      </div>
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-4">
        <div className="h-96 animate-pulse rounded-xl bg-muted xl:col-span-2" />
        <div className="h-96 animate-pulse rounded-xl bg-muted" />
        <div className="flex flex-col gap-5">
          <div className="h-44 animate-pulse rounded-xl bg-muted" />
          <div className="h-44 animate-pulse rounded-xl bg-muted" />
        </div>
      </div>
    </div>
  )
}

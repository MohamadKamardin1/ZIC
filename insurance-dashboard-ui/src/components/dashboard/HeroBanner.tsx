import { BarChart3, DollarSign, Users } from "lucide-react"
import { useEffect, useState } from "react"
import type { HeroStat } from "../../lib/types"

const DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

function formatOrdinal(n: number): string {
  if (n > 3 && n < 21) return `${n}th`
  const suffix = ["st", "nd", "rd"][(n % 10) - 1] || "th"
  return `${n}${suffix}`
}

function useClock() {
  const [now, setNow] = useState(new Date())
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(id)
  }, [])
  return now
}

const ICONS = {
  growth: BarChart3,
  users: Users,
  revenue: DollarSign,
} as const

export function HeroBanner({ stats }: { stats: HeroStat[] }) {
  const now = useClock()
  const dayName = DAYS[now.getDay()]
  const monthFull = MONTHS[now.getMonth()]

  return (
    <section
      className="flex flex-col gap-6 rounded-2xl px-6 py-6 text-white shadow-lg shadow-primary/20 lg:flex-row lg:items-center"
      style={{ background: "linear-gradient(110deg, var(--hero-from), var(--hero-to))" }}
    >
      <div className="flex items-center gap-4">
        <div className="flex h-16 w-16 flex-none flex-col items-center justify-center rounded-full bg-white/15 leading-none backdrop-blur">
          <span className="text-2xl font-extrabold">
            {now.getDate()}<sup className="text-xs">{formatOrdinal(now.getDate()).match(/\D+$/)?.[0]}</sup>
          </span>
        </div>
        <div className="leading-tight">
          <p className="text-lg font-semibold">{dayName},</p>
          <p className="text-lg font-semibold text-white/80">{monthFull}</p>
        </div>
      </div>

      <div className="grid flex-1 grid-cols-1 gap-3 sm:grid-cols-3">
        {stats.map((s) => {
          const Icon = ICONS[s.icon]
          return (
            <div
              key={s.label}
              className="flex items-center gap-3 rounded-xl bg-white/10 px-4 py-3 backdrop-blur transition hover:bg-white/15"
            >
              <span className="flex h-11 w-11 flex-none items-center justify-center rounded-lg bg-white/15">
                <Icon className="h-5 w-5" />
              </span>
              <div className="leading-tight">
                <p className="text-xs font-medium text-white/75">{s.label}</p>
                <p className="text-xl font-bold">{s.value}</p>
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}

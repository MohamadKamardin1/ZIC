import { useQuery } from "@tanstack/react-query"
import { ListTodo, Sparkles } from "lucide-react"
import { useAI } from "../ai/AIContext"
import { getExchangeRate } from "../../lib/apiClient"

export function Footer() {
  const { togglePanel } = useAI()
  const exchangeRate = useQuery({
    queryKey: ["dashboard", "exchange-rate"],
    queryFn: getExchangeRate,
    staleTime: 15 * 60 * 1000,
    retry: false,
  })
  const rate = exchangeRate.data
  const connectionLabel = exchangeRate.isError ? "Connection check unavailable" : "Connection stable"

  return (
    <footer className="mt-2 flex flex-wrap items-center gap-x-6 gap-y-2 border-t border-border bg-card px-4 py-3 text-xs md:px-6">
      <button onClick={() => window.location.assign("/tasks")} className="inline-flex items-center gap-1.5 rounded-full border border-border px-3 py-1 font-medium text-muted-foreground transition hover:bg-secondary" type="button">
        <ListTodo className="h-3.5 w-3.5" />
        Task
      </button>
      <span className="font-semibold text-success">
        {rate ? `${rate.rate} ${rate.baseCurrency}/${rate.quoteCurrency}` : exchangeRate.isLoading ? "Loading exchange rate…" : "Exchange rate unavailable"}
      </span>
      <span className="inline-flex items-center gap-1.5 text-muted-foreground" role="status">
        <span className={`h-2 w-2 rounded-full ${exchangeRate.isError ? "bg-warning" : "bg-success"}`} />
        {connectionLabel}
      </span>
      <button
        onClick={togglePanel}
        className="inline-flex cursor-pointer items-center gap-1.5 rounded-full border border-border px-3 py-1 font-medium text-primary transition-colors hover:bg-accent"
        type="button"
      >
        <Sparkles className="h-3.5 w-3.5" />
        AI
      </button>
      <span className="ml-auto text-muted-foreground">
        Powered by <span className="font-semibold text-foreground">ZIC AIMS Life</span>
      </span>
    </footer>
  )
}

import { useQuery } from "@tanstack/react-query"
import { AlertTriangle, CircleDollarSign, Inbox, ReceiptText } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { useAccess } from "../../lib/access"
import { receiptsApi } from "../../lib/receipts-api"

function amountLabel(value: string, currency?: string): string {
  const number = Number(value)
  const formatted = Number.isFinite(number) ? number.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : value
  return currency ? `${currency} ${formatted}` : formatted
}

export function ReceiptDashboardCards({ className = "" }: { className?: string }) {
  const navigate = useNavigate()
  const { isSuperAdmin, hasPermission } = useAccess()
  const canView = isSuperAdmin || Boolean(hasPermission?.("front_office.receipts.view"))
  const kpis = useQuery({ queryKey: ["receipts", "dashboard-kpis"], queryFn: () => receiptsApi.kpis(), enabled: canView, staleTime: 30_000, retry: false })
  if (!canView) return null

  const data = kpis.data
  const cards = [
    { key: "today", label: "Receipts Today", value: data ? (data.receipts_today ?? data.receipt_count).toLocaleString() : "—", helper: "Received today", icon: ReceiptText, route: "/front-office/receipts?today=true", linkLabel: "View today" },
    { key: "received", label: "Amount Received Today", value: data ? amountLabel(data.received_today, data.currency) : "—", helper: "Today’s collections", icon: CircleDollarSign, route: "/front-office/receipts?today=true", linkLabel: "Open receipts" },
    { key: "unallocated", label: "Unallocated Receipts", value: data ? (data.unallocated_receipt_count !== undefined ? data.unallocated_receipt_count.toLocaleString() : amountLabel(data.unallocated_amount, data.currency)) : "—", helper: data?.unallocated_receipt_count !== undefined ? "Awaiting allocation" : "Unallocated amount", icon: Inbox, route: "/front-office/receipts?unallocated_only=true", linkLabel: "View unallocated" },
    { key: "reversed", label: "Reversed Amount", value: data ? amountLabel(data.reversed_amount, data.currency) : "—", helper: "Receipts reversed", icon: AlertTriangle, route: "/front-office/receipts?reversed_only=true", linkLabel: "View reversed" },
  ]

  return <section className={`grid gap-3 sm:grid-cols-2 xl:grid-cols-4 ${className}`} aria-label="Receipts oversight">{cards.map((card) => { const Icon = card.icon; return <article key={card.key} className="surface-card flex items-center gap-3 px-4 py-3"><span className="flex h-10 w-10 flex-none items-center justify-center rounded-[10px] bg-[var(--secondary)] text-[var(--primary)]"><Icon size={18} aria-hidden="true" /></span><div className="min-w-0 flex-1"><p className="truncate text-xs font-semibold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">{card.label}</p><p className="mt-0.5 text-lg font-bold tabular-nums text-[var(--foreground)]" data-testid={`receipt-card-value-${card.key}`}>{kpis.isError ? "Unavailable" : card.value}</p><p className="text-xs text-[var(--muted-foreground)]">{kpis.isError ? "Refresh to retry" : card.helper}</p></div><button type="button" className="shrink-0 text-xs font-semibold text-[var(--primary)] underline-offset-2 outline-none transition hover:underline focus-visible:ring-2 focus-visible:ring-[var(--ring)]" onClick={() => navigate(card.route)} data-testid={`receipt-card-link-${card.key}`}>{card.linkLabel} →</button></article> })}</section>
}

export default ReceiptDashboardCards

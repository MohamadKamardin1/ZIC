import { useQuery } from "@tanstack/react-query"
import { HelpCircle, LifeBuoy } from "lucide-react"
import { Link, useParams } from "react-router-dom"
import { ErrorCoach } from "../../components/ErrorCoach"
import { AmountCell, PaymentModeBadge, ReceiptStatusBadge } from "../../components/receipts/ReceiptPrimitives"
import { InfoBanner } from "../../components/ui/Overlays"
import { ApiClientError } from "../../lib/apiClient"
import { receiptsApi, type PortalReceiptAllocation, type PortalReceiptRecord } from "../../lib/receipts-api"

export const PORTAL_RECEIPTS_HELP_MESSAGE = "For disputes or corrections, contact your ZIC representative or raise a ticket."

export function sanitizePortalReceiptError(error: unknown) {
  const code = error instanceof ApiClientError ? error.code : undefined
  return {
    error_code: code === "RECEIPT_NOT_FOUND" ? "RECEIPT_NOT_FOUND" : "PORTAL_UNAVAILABLE",
    message: code === "RECEIPT_NOT_FOUND" ? "That receipt is not available in your partner portal." : "The request could not be completed. Please try again or contact your ZIC representative.",
    resolution_steps: code === "RECEIPT_NOT_FOUND" ? ["Return to My Receipts and select a receipt shown in your portal.", "Contact your ZIC representative if you believe a receipt is missing."] : ["Try again in a few moments.", "Contact your ZIC representative if the issue continues."],
  }
}

function PortalBanner() {
  return <InfoBanner title="Read-only view"><p className="flex flex-wrap items-start gap-2 text-sm"><HelpCircle size={16} className="mt-0.5 shrink-0" aria-hidden="true" />{PORTAL_RECEIPTS_HELP_MESSAGE}<Link to="/tickets" className="inline-flex items-center gap-1 font-semibold text-[var(--primary)] underline-offset-2 hover:underline" data-testid="raise-ticket"><LifeBuoy size={14} aria-hidden="true" />Raise Ticket</Link></p></InfoBanner>
}

function dateLabel(value: string): string {
  if (!value) return "—"
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString()
}

function formatDateTime(value: string): string {
  if (!value) return "—"
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function PortalError({ error, title }: { error: unknown; title: string }) {
  const safe = sanitizePortalReceiptError(error)
  return <ErrorCoach title={title} message={safe.message} resolutionSteps={safe.resolution_steps} />
}

export function PortalReceipts() {
  const list = useQuery({ queryKey: ["portal", "receipts"], queryFn: () => receiptsApi.portal.list({ page: 1, page_size: 50 }), retry: false })
  const rows = list.data?.results ?? []

  return <div className="min-h-full px-4 py-5 sm:px-6 lg:px-8"><div className="mx-auto max-w-[1560px] space-y-5"><header className="flex flex-wrap items-end justify-between gap-4 border-b border-[var(--border)] pb-5"><div><div className="mb-2 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--muted-foreground)]"><span>ZIC</span><span>/</span><span>Partner Portal</span><span>/</span><span>Receipts</span></div><h1 className="text-2xl font-semibold tracking-[-0.04em] text-[var(--foreground)]">My Receipts</h1><p className="mt-1 text-sm text-[var(--muted-foreground)]">Payments received for your linked partner account. This view is read-only and partner-scoped.</p></div><Link to="/tickets" className="inline-flex items-center gap-2 text-sm font-semibold text-[var(--primary)] underline-offset-2 hover:underline"><LifeBuoy size={15} aria-hidden="true" />Raise Ticket</Link></header><PortalBanner />{list.isLoading && <div className="surface-card py-10 text-center text-sm text-[var(--muted-foreground)]" role="status">Loading your receipts…</div>}{list.isError && <PortalError error={list.error} title="Receipts could not be loaded" />}{!list.isLoading && !list.isError && rows.length === 0 && <div className="surface-card py-10 text-center text-sm text-[var(--muted-foreground)]">No receipts are available for your partner account at this time.</div>}{rows.length > 0 && <section className="surface-card overflow-hidden"><div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><caption className="sr-only">Your receipts</caption><thead className="bg-[var(--muted)]/45 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><tr>{["Receipt number", "Date", "Amount", "Payment mode", "Status"].map((heading) => <th key={heading} scope="col" className="px-4 py-3 font-bold">{heading}</th>)}</tr></thead><tbody className="divide-y divide-[var(--border)]">{rows.map((row) => <tr key={row.id} className="transition hover:bg-[var(--muted)]/25"><td className="px-4 py-3 font-semibold"><Link to={`/portal/receipts/${row.id}`} className="text-[var(--primary)] underline-offset-2 hover:underline">{row.receipt_number}</Link></td><td className="px-4 py-3">{dateLabel(row.receipt_date)}</td><td className="px-4 py-3"><AmountCell amount={row.receipt_amount} currency={row.currency} amountInWords={row.amount_in_words} /></td><td className="px-4 py-3"><PaymentModeBadge mode={row.payment_mode} label={row.payment_mode_display} /></td><td className="px-4 py-3"><ReceiptStatusBadge status={row.status} /></td></tr>)}</tbody></table></div></section>}{rows.length > 0 && <p className="text-xs text-[var(--muted-foreground)]">Select a receipt number to view its own payment allocations. No staff actions are available in the partner portal.</p>}</div></div>
}

function AllocationRow({ allocation }: { allocation: PortalReceiptAllocation }) {
  return <tr><td className="px-4 py-3 font-semibold">{allocation.commitment_display}</td><td className="px-4 py-3"><AmountCell amount={allocation.amount} currency={allocation.currency} /></td><td className="px-4 py-3"><PaymentModeBadge mode={allocation.payment_mode_display} label={allocation.payment_mode_display} /></td><td className="px-4 py-3">{allocation.receipt_reference || "—"}</td><td className="px-4 py-3 text-xs">{formatDateTime(allocation.allocated_at)}</td></tr>
}

export function PortalReceiptDetail() {
  const { id } = useParams()
  const detail = useQuery({ queryKey: ["portal", "receipts", id], queryFn: () => receiptsApi.portal.get(id as string), enabled: Boolean(id), retry: false })
  if (!id) return <div className="p-8 text-sm text-[var(--muted-foreground)]">Receipt reference is missing.</div>
  if (detail.isLoading) return <div className="p-8 text-center text-sm text-[var(--muted-foreground)]" role="status">Loading receipt…</div>
  if (detail.isError || !detail.data) return <div className="space-y-4 px-4 py-6"><Link to="/portal/receipts" className="button-secondary">← Back to My Receipts</Link><PortalError error={detail.error} title="Receipt could not be loaded" /></div>

  const receipt: PortalReceiptRecord = detail.data
  const allocations = receipt.allocations ?? []
  return <div className="min-h-full space-y-5 px-4 py-5 sm:px-6 lg:px-8"><header className="surface-card px-5 py-4"><div className="flex flex-wrap items-start justify-between gap-4"><div><div className="mb-1 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--muted-foreground)]"><span>ZIC</span><span>/</span><span>Partner Portal</span><span>/</span><span>{receipt.receipt_number}</span></div><h1 className="text-2xl font-semibold tracking-[-0.04em] text-[var(--foreground)]">{receipt.receipt_number}</h1><p className="mt-1 text-sm text-[var(--muted-foreground)]">{receipt.payer_display} · {receipt.branch_display}</p><div className="mt-3 flex flex-wrap items-center gap-3"><ReceiptStatusBadge status={receipt.status} /><AmountCell amount={receipt.receipt_amount} currency={receipt.currency} /></div></div><Link to="/portal/receipts" className="button-secondary">← Back</Link></div></header><PortalBanner /><div className="grid gap-4 lg:grid-cols-2"><section className="surface-card px-5 py-4"><h2 className="text-[10px] font-bold uppercase tracking-[0.12em] text-[var(--muted-foreground)]">Receipt overview</h2><dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2"><div><dt className="text-xs text-[var(--muted-foreground)]">Receipt date</dt><dd>{dateLabel(receipt.receipt_date)}</dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Payment mode</dt><dd><PaymentModeBadge mode={receipt.payment_mode} label={receipt.payment_mode_display} /></dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Currency</dt><dd>{receipt.currency_display}</dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Payment reference</dt><dd>{receipt.payment_reference || "—"}</dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Allocated</dt><dd><AmountCell amount={receipt.allocated_amount} currency={receipt.currency} /></dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Unallocated</dt><dd><AmountCell amount={receipt.unallocated_amount} currency={receipt.currency} /></dd></div></dl></section><section className="surface-card px-5 py-4"><h2 className="text-[10px] font-bold uppercase tracking-[0.12em] text-[var(--muted-foreground)]">Source</h2><dl className="mt-3 grid gap-3 text-sm"><div><dt className="text-xs text-[var(--muted-foreground)]">Source module</dt><dd>{receipt.source_module || "—"}</dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Source reference</dt><dd>{receipt.source_reference_display || "—"}</dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Narration</dt><dd>{receipt.narration || "—"}</dd></div></dl></section></div><section className="surface-card overflow-hidden"><div className="border-b bg-[var(--muted)]/35 px-5 py-4"><h2 className="font-bold">My payment allocations</h2><p className="mt-1 text-sm text-[var(--muted-foreground)]">Only allocations linked to your partner account are shown. Staff allocation, reversal, and cancellation actions are not available here.</p></div>{allocations.length === 0 ? <p className="px-5 py-8 text-center text-sm text-[var(--muted-foreground)]">No payment allocations are recorded for this receipt.</p> : <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><caption className="sr-only">Your receipt allocations</caption><thead className="bg-[var(--muted)]/45 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><tr>{["Commitment", "Amount", "Payment mode", "Receipt reference", "Allocated at"].map((heading) => <th key={heading} scope="col" className="px-4 py-3 font-bold">{heading}</th>)}</tr></thead><tbody className="divide-y divide-[var(--border)]">{allocations.map((allocation) => <AllocationRow key={allocation.id} allocation={allocation} />)}</tbody></table></div>}</section></div>
}

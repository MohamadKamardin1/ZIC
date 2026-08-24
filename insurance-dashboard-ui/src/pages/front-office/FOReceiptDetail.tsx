import { useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowLeft, ChevronRight, Download, Eye, EyeOff, FileText, LockKeyhole, Printer, RefreshCw, RotateCcw, ShieldCheck } from "lucide-react"
import { useCallback, useMemo, useState } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import { ErrorCoach } from "../../components/ErrorCoach"
import { AllocationProgressBar, AmountCell, PaymentModeBadge } from "../../components/receipts/ReceiptPrimitives"
import { ReceiptAllocationModal } from "../../components/receipts/ReceiptAllocationModal"
import { AllocationReversalModal, CancelDraftModal, ReceiptReversalModal } from "../../components/receipts/ReceiptLifecycleModals"
import { InfoBanner } from "../../components/ui/Overlays"
import { MasterDetailPage } from "../../components/ui/Patterns"
import { useAccess } from "../../lib/access"
import { ApiClientError } from "../../lib/apiClient"
import { receiptsApi, type ReceiptAllocation, type ReceiptAuditEvent, type ReceiptDocument, type ReceiptRecord, type ReceiptReversal } from "../../lib/receipts-api"
import { receiptRowActionEnabled } from "./FOReceipts"

const DETAIL_TABS = [
  { id: "allocations", label: "Allocations" },
  { id: "reversals", label: "Reversals" },
  { id: "documents", label: "Documents" },
  { id: "audit", label: "Audit Timeline" },
] as const

type DetailTab = typeof DETAIL_TABS[number]["id"]
type DetailRow = ReceiptRecord & Record<string, unknown>

const ACTIONS = [
  { key: "edit", label: "Edit", permission: "front_office.receipts.edit", tone: "secondary" as const },
  { key: "post", label: "Post", permission: "front_office.receipts.post", tone: "primary" as const },
  { key: "allocate", label: "Allocate", permission: "front_office.receipts.allocate", tone: "secondary" as const },
  { key: "auto_allocate", label: "Auto-Allocate", permission: "front_office.receipts.allocate", tone: "secondary" as const },
  { key: "reverse", label: "Reverse", permission: "front_office.receipts.reverse", tone: "danger" as const },
  { key: "cancel", label: "Cancel", permission: "front_office.receipts.cancel", tone: "danger" as const },
  { key: "print", label: "Print", permission: "front_office.receipts.print", tone: "secondary" as const },
]

function asErrorProps(error: unknown): { message: string; resolutionSteps?: string[]; loginUrl?: string; actionLabel?: string } {
  if (error instanceof ApiClientError) return { message: error.message, resolutionSteps: error.resolutionSteps, loginUrl: error.deepLink, actionLabel: error.deepLink ? "Open resolution page" : undefined }
  return { message: error instanceof Error ? error.message : "The receipt detail could not be loaded. Refresh and try again." }
}

function formatDateTime(value?: string | null): string {
  if (!value) return "—"
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date)
}

function textValue(value: unknown, fallback = "—"): string {
  return typeof value === "string" && value.trim() ? value : fallback
}

function actionLabel(value: string): string {
  return value.replace(/[-_]/g, " ").replace(/\b\w/g, (character) => character.toUpperCase())
}

function getAllocationTarget(row: { target_display: string; commitment_number?: string; source_display?: string }): string {
  if (row.target_display) return row.target_display
  return [row.commitment_number, row.source_display].filter(Boolean).join(" · ") || "Unspecified commitment"
}

function DetailSkeleton() {
  return <div className="space-y-5 p-4 md:p-6" role="status" aria-label="Loading receipt detail"><div className="h-36 animate-pulse rounded-[12px] bg-[var(--muted)]" /><div className="grid gap-4 md:grid-cols-2"><div className="h-28 animate-pulse rounded-[12px] bg-[var(--muted)]" /><div className="h-28 animate-pulse rounded-[12px] bg-[var(--muted)]" /></div><div className="h-64 animate-pulse rounded-[12px] bg-[var(--muted)]" /></div>
}

function EmptyTab({ title, description }: { title: string; description: string }) {
  return <div className="rounded-[10px] border border-dashed border-[var(--border)] bg-[var(--muted)]/20 px-5 py-10 text-center"><p className="font-bold">{title}</p><p className="mt-1 text-sm text-[var(--muted-foreground)]">{description}</p></div>
}

function DetailError({ title, error }: { title: string; error: unknown }) {
  const props = asErrorProps(error)
  return <ErrorCoach title={title} message={props.message} resolutionSteps={props.resolutionSteps} loginUrl={props.loginUrl} actionLabel={props.actionLabel} />
}

export default function FOReceiptDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { isSuperAdmin, hasPermission: accessHasPermission } = useAccess()
  const [activeTab, setActiveTab] = useState<DetailTab>("allocations")
  const [accountRevealed, setAccountRevealed] = useState(false)
  const [revealedAccount, setRevealedAccount] = useState("")
  const [revealError, setRevealError] = useState<unknown>(null)
  const [actionMessage, setActionMessage] = useState<string | null>(null)
  const [allocationModalOpen, setAllocationModalOpen] = useState(false)
  const [receiptReversalOpen, setReceiptReversalOpen] = useState(false)
  const [cancelDraftOpen, setCancelDraftOpen] = useState(false)
  const [allocationForReversal, setAllocationForReversal] = useState<ReceiptAllocation | null>(null)

  const hasPermission = useCallback((permission: string) => isSuperAdmin || Boolean(accessHasPermission?.(permission)), [accessHasPermission, isSuperAdmin])
  const receiptQuery = useQuery({ queryKey: ["receipts", "detail", id], queryFn: () => receiptsApi.get(id as string), enabled: Boolean(id), retry: false })
  const receipt = receiptQuery.data
  const row = receipt as DetailRow | undefined
  const allocationsQuery = useQuery({ queryKey: ["receipts", "detail", id, "allocations"], queryFn: () => receiptsApi.allocations(id as string), enabled: Boolean(id) && activeTab === "allocations", retry: false })
  const reversalsQuery = useQuery({ queryKey: ["receipts", "detail", id, "reversals"], queryFn: () => receiptsApi.reversals(id as string), enabled: Boolean(id) && activeTab === "reversals", retry: false })
  const documentsQuery = useQuery({ queryKey: ["receipts", "detail", id, "documents"], queryFn: () => receiptsApi.documents(id as string), enabled: Boolean(id) && activeTab === "documents", retry: false })
  const auditQuery = useQuery({ queryKey: ["receipts", "detail", id, "audit"], queryFn: () => receiptsApi.auditTimeline(id as string), enabled: Boolean(id) && activeTab === "audit", retry: false })

  const actionAvailability = useMemo(() => ACTIONS.filter((action) => row && receiptRowActionEnabled(action.key, row, isSuperAdmin, hasPermission)), [hasPermission, isSuperAdmin, row])
  const canRevealAccount = hasPermission("front_office.receipts.view_bank_account")

  const revealBankAccount = async () => {
    if (!id || !canRevealAccount) return
    setRevealError(null)
    if (accountRevealed) {
      setAccountRevealed(false)
      return
    }
    try {
      const result = await receiptsApi.revealBankAccount(id)
      setRevealedAccount(result.bank_account_display)
      setAccountRevealed(true)
    } catch (error) {
      setRevealError(error)
    }
  }

  const selectAction = (key: string) => {
    if (!id) return
    if (key === "edit" || key === "post") {
      navigate(`/front-office/receipts/${id}/edit?action=${key}`)
      return
    }
    if (key === "allocate" || key === "auto_allocate") {
      setAllocationModalOpen(true)
      return
    }
    if (key === "reverse") {
      setReceiptReversalOpen(true)
      return
    }
    if (key === "cancel") {
      setCancelDraftOpen(true)
      return
    }
    setActionMessage(`${actionLabel(key)} is available from this receipt. The dedicated action screen will open when that workflow is enabled for your role.`)
  }

  const refreshAfterLifecycleAction = () => {
    if (!id) return
    void queryClient.invalidateQueries({ queryKey: ["receipts", "detail", id] })
    void queryClient.invalidateQueries({ queryKey: ["receipts", "detail", id, "allocations"] })
    void queryClient.invalidateQueries({ queryKey: ["receipts", "detail", id, "reversals"] })
    void queryClient.invalidateQueries({ queryKey: ["receipts", "detail", id, "audit"] })
    setActiveTab("audit")
  }

  if (!id) return <div className="space-y-4 p-4 md:p-6"><Link to="/front-office/receipts" className="inline-flex items-center gap-2 text-sm font-semibold text-[var(--primary)]"><ArrowLeft size={16} aria-hidden="true" />Back to receipts</Link><DetailError title="Receipt reference is missing" error={new Error("Open the receipt from the Receipts Work Queue so its reference can be loaded.")} /></div>
  if (receiptQuery.isLoading) return <DetailSkeleton />
  if (receiptQuery.isError || !receipt) return <div className="space-y-4 p-4 md:p-6"><Link to="/front-office/receipts" className="inline-flex items-center gap-2 text-sm font-semibold text-[var(--primary)]"><ArrowLeft size={16} aria-hidden="true" />Back to receipts</Link><DetailError title="Receipt could not be loaded" error={receiptQuery.error ?? new Error("The receipt was not returned by the server.")} /></div>

  const isCrossCurrency = (currency: string) => currency !== receipt.currency
  const accountDisplay = accountRevealed ? revealedAccount : textValue(receipt.bank_account_display, "No bank account recorded")
  const postedLabel = receipt.posted_by_display ? `${receipt.posted_by_display} · ${formatDateTime(receipt.posted_at)}` : "Not posted"
  const status = receipt.status.toUpperCase()

  return <div className="space-y-5 p-4 md:p-6">
    <Link to="/front-office/receipts" className="inline-flex items-center gap-2 text-sm font-semibold text-[var(--primary)] hover:underline"><ArrowLeft size={16} aria-hidden="true" />Back to Receipts Work Queue</Link>
    <MasterDetailPage
      eyebrow="Front Office · Receipt Detail"
      title={receipt.receipt_number}
      description={`${receipt.payer_display} · ${receipt.branch_display} · ${receipt.receipt_date}`}
      status={{ value: receipt.status }}
      actions={<div className="flex flex-wrap gap-2">{actionAvailability.map((action) => <button key={action.key} type="button" className={action.tone === "primary" ? "button-primary" : action.tone === "danger" ? "inline-flex min-h-10 items-center justify-center rounded-[10px] bg-[var(--destructive)] px-3 text-sm font-bold text-white transition hover:opacity-90" : "button-secondary"} onClick={() => selectAction(action.key)}>{action.key === "print" ? <Printer size={15} aria-hidden="true" /> : action.key === "reverse" ? <RotateCcw size={15} aria-hidden="true" /> : action.key === "auto_allocate" ? <RefreshCw size={15} aria-hidden="true" /> : null}{action.label}</button>)}</div>}
    >
      <div className="space-y-5">
        {status === "REVERSED" && <InfoBanner title="Receipt reversed"><span>{textValue(receipt.reversed_reason, "This receipt has been reversed and is no longer available for allocation.")} Printed copies will carry a REVERSED watermark.</span></InfoBanner>}
        {status === "CANCELLED" && <InfoBanner title="Receipt cancelled"><span>{textValue(receipt.cancelled_reason, "This receipt has been cancelled and is no longer editable.")} Printed copies will carry a CANCELLED watermark.</span></InfoBanner>}
        {actionMessage && <InfoBanner title="Action entry point"><span className="flex flex-wrap items-center gap-2">{actionMessage}<button type="button" className="font-bold text-[var(--primary)] underline-offset-2 hover:underline" onClick={() => setActionMessage(null)}>Dismiss</button></span></InfoBanner>}
        {revealError !== null && <DetailError title="Bank account could not be revealed" error={revealError} />}

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4" aria-label="Receipt summary">
          <div className="surface-card p-4"><p className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Payment mode</p><div className="mt-2"><PaymentModeBadge mode={receipt.payment_mode} label={receipt.payment_mode_display} /></div></div>
          <div className="surface-card p-4"><p className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Currency and amount</p><div className="mt-2"><AmountCell amount={receipt.receipt_amount} currency={receipt.currency} amountInWords={receipt.amount_in_words} /></div></div>
          <div className="surface-card p-4"><p className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Allocation progress</p><div className="mt-2"><AllocationProgressBar allocated={receipt.allocated_amount} total={receipt.receipt_amount} currency={receipt.currency} /></div></div>
          <div className="surface-card p-4"><p className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Posted by / at</p><p className="mt-2 text-sm font-semibold">{postedLabel}</p></div>
        </section>

        <section className="surface-card p-5" aria-labelledby="receipt-account-details"><div className="flex flex-wrap items-start justify-between gap-3"><div><h2 id="receipt-account-details" className="text-base font-bold">Account details</h2><p className="mt-1 text-sm text-[var(--muted-foreground)]">Sensitive bank details remain masked unless your access profile allows a temporary reveal.</p></div><ShieldCheck size={20} className="text-[var(--primary)]" aria-hidden="true" /></div><div className="mt-4 grid gap-4 md:grid-cols-3"><div><p className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Receiving account</p><p className="mt-1 flex items-center gap-2 text-sm font-semibold"><LockKeyhole size={14} aria-hidden="true" />{accountDisplay}</p>{canRevealAccount && receipt.bank_account_display && <button type="button" className="mt-2 inline-flex items-center gap-1 text-xs font-bold text-[var(--primary)] hover:underline" onClick={() => void revealBankAccount()}>{accountRevealed ? <EyeOff size={13} aria-hidden="true" /> : <Eye size={13} aria-hidden="true" />}{accountRevealed ? "Hide account" : "Show account"}</button>}</div><div><p className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Payment reference</p><p className="mt-1 text-sm font-semibold">{textValue(receipt.payment_reference)}</p></div><div><p className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">Source</p><p className="mt-1 text-sm font-semibold">{textValue(receipt.source_module)}{receipt.source_reference_display ? ` · ${receipt.source_reference_display}` : ""}</p></div></div></section>

        <nav className="surface-card flex gap-1 overflow-x-auto p-1" aria-label="Receipt detail tabs">{DETAIL_TABS.map((tab) => <button key={tab.id} type="button" className={`whitespace-nowrap rounded-[9px] px-4 py-2.5 text-sm font-bold transition ${activeTab === tab.id ? "bg-[var(--primary)] text-[var(--primary-foreground)]" : "text-[var(--muted-foreground)] hover:bg-[var(--secondary)] hover:text-[var(--foreground)]"}`} aria-current={activeTab === tab.id ? "page" : undefined} onClick={() => setActiveTab(tab.id)}>{tab.label}</button>)}</nav>

        {activeTab === "allocations" && <section className="surface-card overflow-hidden" aria-labelledby="allocations-heading"><div className="border-b px-5 py-4"><h2 id="allocations-heading" className="font-bold">Allocations</h2><p className="mt-1 text-sm text-[var(--muted-foreground)]">Commitments and source transactions receiving this payment.</p></div>{allocationsQuery.isLoading && <div className="p-6 text-sm text-[var(--muted-foreground)]" role="status">Loading allocations…</div>}{allocationsQuery.isError && <div className="p-5"><DetailError title="Allocations could not be loaded" error={allocationsQuery.error} /></div>}{!allocationsQuery.isLoading && !allocationsQuery.isError && !allocationsQuery.data?.results.length && <div className="p-5"><EmptyTab title="No allocations recorded" description="This receipt currently has no allocation rows. The next permitted action may be Allocate or Auto-Allocate." /></div>}{!allocationsQuery.isLoading && !allocationsQuery.isError && Boolean(allocationsQuery.data?.results.length) && <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><caption className="sr-only">Receipt allocations</caption><thead className="bg-[var(--muted)]/45 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><tr><th className="px-5 py-3">Target / source</th><th className="px-5 py-3">Amount</th><th className="px-5 py-3">Currency</th><th className="px-5 py-3">Exchange rate</th><th className="px-5 py-3">Status</th><th className="px-5 py-3">Action</th></tr></thead><tbody className="divide-y divide-[var(--border)]">{allocationsQuery.data?.results.map((allocation) => <tr key={allocation.id}><td className="px-5 py-3"><p className="font-semibold">{getAllocationTarget(allocation)}</p><p className="text-xs text-[var(--muted-foreground)]">{textValue(allocation.source_display)}</p></td><td className="px-5 py-3"><AmountCell amount={allocation.amount} currency={allocation.currency} /></td><td className="px-5 py-3">{allocation.currency}</td><td className="px-5 py-3">{isCrossCurrency(allocation.currency) ? textValue(allocation.exchange_rate) : "—"}</td><td className="px-5 py-3"><span className="rounded-full bg-[var(--secondary)] px-2.5 py-1 text-xs font-bold">{allocation.status}</span></td><td className="px-5 py-3">{allocation.reversed_at && <span className="text-xs text-[var(--muted-foreground)]">Reversed {formatDateTime(allocation.reversed_at)}</span>}{!allocation.reversed_at && hasPermission("front_office.receipts.reverse_allocation") && <button type="button" className="inline-flex items-center gap-1 text-xs font-bold text-[var(--primary)] hover:underline" onClick={() => setAllocationForReversal(allocation)}
>Reverse allocation<ChevronRight size={13} aria-hidden="true" /></button>}</td></tr>)}</tbody></table></div>}</section>}

        {activeTab === "reversals" && <section className="surface-card overflow-hidden" aria-labelledby="reversals-heading"><div className="border-b px-5 py-4"><h2 id="reversals-heading" className="font-bold">Reversal history</h2><p className="mt-1 text-sm text-[var(--muted-foreground)]">Immutable reversal records linked to this receipt.</p></div>{reversalsQuery.isLoading && <div className="p-6 text-sm text-[var(--muted-foreground)]" role="status">Loading reversals…</div>}{reversalsQuery.isError && <div className="p-5"><DetailError title="Reversal history could not be loaded" error={reversalsQuery.error} /></div>}{!reversalsQuery.isLoading && !reversalsQuery.isError && !reversalsQuery.data?.results.length && <div className="p-5"><EmptyTab title="No reversals recorded" description="No reversal has been posted for this receipt." /></div>}{!reversalsQuery.isLoading && !reversalsQuery.isError && Boolean(reversalsQuery.data?.results.length) && <div className="overflow-x-auto"><table className="w-full min-w-[720px] text-left text-sm"><caption className="sr-only">Receipt reversal history</caption><thead className="bg-[var(--muted)]/45 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><tr><th className="px-5 py-3">Reversal number</th><th className="px-5 py-3">Reason</th><th className="px-5 py-3">Created by / at</th><th className="px-5 py-3">Source channel</th></tr></thead><tbody className="divide-y divide-[var(--border)]">{reversalsQuery.data?.results.map((reversal: ReceiptReversal) => <tr key={reversal.id}><td className="px-5 py-3 font-semibold">{reversal.reversal_number}</td><td className="px-5 py-3">{reversal.reason}</td><td className="px-5 py-3">{reversal.created_by_display} · {formatDateTime(reversal.created_at)}</td><td className="px-5 py-3">{textValue(reversal.source_channel)}</td></tr>)}</tbody></table></div>}</section>}

        {activeTab === "documents" && <section className="surface-card overflow-hidden" aria-labelledby="documents-heading"><div className="border-b px-5 py-4"><h2 id="documents-heading" className="font-bold">Documents</h2><p className="mt-1 text-sm text-[var(--muted-foreground)]">Generated receipt printouts retain their template version and source transaction.</p></div>{documentsQuery.isLoading && <div className="p-6 text-sm text-[var(--muted-foreground)]" role="status">Loading receipt documents…</div>}{documentsQuery.isError && <div className="p-5"><DetailError title="Receipt documents could not be loaded" error={documentsQuery.error} /></div>}{!documentsQuery.isLoading && !documentsQuery.isError && !documentsQuery.data?.results.length && <div className="p-5"><EmptyTab title="No generated printouts" description="Use Print when the receipt is ready to generate its branded document." /></div>}{!documentsQuery.isLoading && !documentsQuery.isError && Boolean(documentsQuery.data?.results.length) && <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><caption className="sr-only">Generated receipt documents</caption><thead className="bg-[var(--muted)]/45 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><tr><th className="px-5 py-3">Document</th><th className="px-5 py-3">Template version</th><th className="px-5 py-3">Generated by / at</th><th className="px-5 py-3">Pages</th><th className="px-5 py-3">Actions</th></tr></thead><tbody className="divide-y divide-[var(--border)]">{documentsQuery.data?.results.map((document: ReceiptDocument) => <tr key={document.id}><td className="px-5 py-3"><span className="inline-flex items-center gap-2 font-semibold"><FileText size={15} aria-hidden="true" />{document.template_name}</span></td><td className="px-5 py-3">v{document.template_version}</td><td className="px-5 py-3">{document.generated_by_display} · {formatDateTime(document.generated_at)}</td><td className="px-5 py-3">{document.page_count}</td><td className="px-5 py-3"><span className="flex flex-wrap gap-3">{document.preview_url && <a href={document.preview_url} className="inline-flex items-center gap-1 text-xs font-bold text-[var(--primary)] hover:underline"><Eye size={13} aria-hidden="true" />Preview</a>}{(document.download_url || document.signed_download_url) && <a href={document.signed_download_url || document.download_url || "#"} className="inline-flex items-center gap-1 text-xs font-bold text-[var(--primary)] hover:underline"><Download size={13} aria-hidden="true" />Download</a>}</span></td></tr>)}</tbody></table></div>}</section>}

        {activeTab === "audit" && <section className="surface-card p-5" aria-labelledby="audit-heading"><div className="border-b pb-4"><h2 id="audit-heading" className="font-bold">Audit Timeline</h2><p className="mt-1 text-sm text-[var(--muted-foreground)]">Every receipt lifecycle event is shown with its actor, source channel, reason, and before/after summary.</p></div>{auditQuery.isLoading && <div className="py-6 text-sm text-[var(--muted-foreground)]" role="status">Loading audit timeline…</div>}{auditQuery.isError && <div className="py-5"><DetailError title="Audit timeline could not be loaded" error={auditQuery.error} /></div>}{!auditQuery.isLoading && !auditQuery.isError && !auditQuery.data?.results.length && <div className="pt-5"><EmptyTab title="No audit events returned" description="The service did not return lifecycle history for this receipt." /></div>}{!auditQuery.isLoading && !auditQuery.isError && Boolean(auditQuery.data?.results.length) && <ol className="mt-5 space-y-5">{auditQuery.data?.results.map((event: ReceiptAuditEvent) => <li key={event.id} className="relative pl-8"><span className="absolute left-0 top-1.5 h-3 w-3 rounded-full bg-[var(--primary)] ring-4 ring-[var(--primary)]/10" aria-hidden="true" /><div className="flex flex-wrap items-start justify-between gap-2"><div><p className="font-bold">{actionLabel(event.action)}</p><p className="mt-1 text-xs text-[var(--muted-foreground)]">{event.actor_display} · {formatDateTime(event.occurred_at)}</p></div><span className="rounded-full bg-[var(--secondary)] px-2.5 py-1 text-xs font-bold">{textValue(event.source_channel)}</span></div><div className="mt-3 grid gap-3 md:grid-cols-2"><div className="rounded-[9px] border border-[var(--border)] bg-[var(--muted)]/20 p-3"><p className="text-[11px] font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">Before</p><p className="mt-1 text-sm">{textValue(event.before_summary, "No prior state")}</p></div><div className="rounded-[9px] border border-[var(--border)] bg-[var(--muted)]/20 p-3"><p className="text-[11px] font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">After</p><p className="mt-1 text-sm">{textValue(event.after_summary, "No after-state summary")}</p></div></div>{event.reason && <p className="mt-2 text-sm text-[var(--muted-foreground)]"><span className="font-semibold">Reason:</span> {event.reason}</p>}</li>)}</ol>}</section>}
      </div>
    </MasterDetailPage>
    <ReceiptAllocationModal open={allocationModalOpen} receipt={receipt} onClose={() => setAllocationModalOpen(false)} onSuccess={() => {
      void queryClient.invalidateQueries({ queryKey: ["receipts", "detail", id] })
      void queryClient.invalidateQueries({ queryKey: ["receipts", "detail", id, "allocations"] })
    }} />
    <ReceiptReversalModal open={receiptReversalOpen} receipt={receipt} onClose={() => setReceiptReversalOpen(false)} onSuccess={() => refreshAfterLifecycleAction()} />
    <CancelDraftModal open={cancelDraftOpen} receipt={receipt} onClose={() => setCancelDraftOpen(false)} onSuccess={() => refreshAfterLifecycleAction()} />
    <AllocationReversalModal open={Boolean(allocationForReversal)} receipt={receipt} allocation={allocationForReversal} onClose={() => setAllocationForReversal(null)} onSuccess={() => refreshAfterLifecycleAction()} />
  </div>
}

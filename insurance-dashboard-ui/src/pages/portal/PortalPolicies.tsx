import { HelpCircle, LifeBuoy } from "lucide-react"
import { Link, useNavigate, useParams } from "react-router-dom"
import { ErrorCoach } from "../../components/commitments/ErrorCoach"
import { InfoBanner } from "../../components/ui/Overlays"
import { formatMoney, dateLabel } from "../../lib/commitmentsDisplay"
import { usePortalPolicies, usePortalPolicy, usePortalPolicyDocuments } from "../../lib/policyPortalHooks"
import { sanitizePortalError } from "./PartnerCommitments"

export const POLICY_PORTAL_HELP_MESSAGE = "Contact agent for changes."

function PortalBanner() {
  return <InfoBanner title="Read-only view"><p className="flex flex-wrap items-start gap-2 text-sm"><HelpCircle size={16} className="mt-0.5 shrink-0" aria-hidden="true" /><span>{POLICY_PORTAL_HELP_MESSAGE}</span><Link to="/tickets" className="inline-flex items-center gap-1 font-semibold text-[var(--primary)] underline-offset-2 hover:underline" data-testid="policy-portal-raise-ticket"><LifeBuoy size={14} aria-hidden="true" />Raise Ticket</Link></p></InfoBanner>
}

function statusClass(status: string) {
  const normalized = status.toUpperCase()
  if (["ACTIVE", "PAID_UP", "MATURED"].includes(normalized)) return "badge-success"
  if (["LAPSED", "SURRENDER_PENDING"].includes(normalized)) return "badge-warning"
  if (["CANCELLED", "SURRENDERED", "TERMINATED"].includes(normalized)) return "badge-danger"
  return "badge-info"
}

function PolicyStatus({ status }: { status: string }) {
  return <span className={statusClass(status)} role="status">{status.split("_").join(" ")}</span>
}

export function PortalPolicies() {
  const navigate = useNavigate()
  const list = usePortalPolicies()
  const rows = list.data?.results ?? []

  return <div className="min-h-full px-4 py-5 sm:px-6 lg:px-8" data-testid="portal-policies"><div className="mx-auto max-w-[1560px] space-y-5"><header className="flex flex-wrap items-end justify-between gap-4 border-b border-[var(--border)] pb-5"><div><div className="mb-2 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--muted-foreground)]"><span>ZIC</span><span>/</span><span>Partner Portal</span><span>/</span><span>Policies</span></div><h1 className="text-2xl font-semibold tracking-[-0.04em] text-[var(--foreground)]">My Policies</h1><p className="mt-1 text-sm text-[var(--muted-foreground)]">Your Ordinary Life policies scoped to your linked partner account.</p></div><Link to="/tickets" className="inline-flex items-center gap-2 text-sm font-semibold text-[var(--primary)] underline-offset-2 hover:underline"><LifeBuoy size={15} aria-hidden="true" />Raise Ticket</Link></header><PortalBanner />{list.isLoading && <p className="py-10 text-center text-sm text-[var(--muted-foreground)]" role="status">Loading your policies…</p>}{list.isError && <ErrorCoach error={sanitizePortalError(list.error)} title="Policies could not be loaded" />}{!list.isLoading && !list.isError && rows.length === 0 && <p className="py-10 text-center text-sm text-[var(--muted-foreground)]" data-testid="portal-policies-empty">You have no policies at this time.</p>}{rows.length > 0 && <section className="surface-card overflow-hidden"><div className="overflow-x-auto"><table className="w-full min-w-[860px] text-left text-sm" data-testid="portal-policies-table"><caption className="sr-only">Your policies</caption><thead className="bg-[var(--muted)]/45 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><tr>{["Policy", "Product / Plan", "Status", "Commenced", "Maturity", "Currency"].map((heading) => <th key={heading} scope="col" className="px-4 py-2.5 font-bold">{heading}</th>)}</tr></thead><tbody className="divide-y divide-[var(--border)]">{rows.map((row) => <tr key={row.id} data-testid={`portal-policy-row-${row.id}`} className="cursor-pointer transition hover:bg-[var(--muted)]/25" tabIndex={0} onClick={() => navigate(`/portal/policies/${row.id}`)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); navigate(`/portal/policies/${row.id}`) } }}><td className="px-4 py-2.5 font-semibold text-[var(--foreground)]">{row.policyNumber}</td><td className="px-4 py-2.5">{row.productPlanDisplay}</td><td className="px-4 py-2.5"><PolicyStatus status={row.status} /></td><td className="px-4 py-2.5">{dateLabel(row.riskCommencementDate)}</td><td className="px-4 py-2.5">{dateLabel(row.maturityDate)}</td><td className="px-4 py-2.5">{row.currency}</td></tr>)}</tbody></table></div></section>}</div></div>
}

function PortalPolicyDocuments({ policyId }: { policyId: string }) {
  const documents = usePortalPolicyDocuments(policyId)
  const rows = documents.data ?? []
  return <section className="surface-card overflow-hidden" data-testid="portal-policy-documents"><div className="border-b bg-[var(--muted)]/35 px-5 py-3"><h2 className="text-sm font-bold text-[var(--foreground)]">Documents</h2><p className="text-xs text-[var(--muted-foreground)]">{rows.length} document(s) on file</p></div>{documents.isLoading && <p className="px-5 py-6 text-sm text-[var(--muted-foreground)]" role="status">Loading policy documents…</p>}{documents.isError && <div className="p-5"><ErrorCoach error={sanitizePortalError(documents.error)} title="Policy documents could not be loaded" /></div>}{!documents.isLoading && !documents.isError && rows.length === 0 && <p className="px-5 py-6 text-center text-sm text-[var(--muted-foreground)]">No policy documents are available in the portal.</p>}{rows.length > 0 && <div className="overflow-x-auto"><table className="w-full min-w-[680px] text-left text-sm"><caption className="sr-only">Your policy documents</caption><thead className="bg-[var(--muted)]/45 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><tr>{["Document", "Template version", "Generated by", "Generated at", "Pages"].map((heading) => <th key={heading} scope="col" className="px-4 py-2.5 font-bold">{heading}</th>)}</tr></thead><tbody className="divide-y divide-[var(--border)]">{rows.map((row) => <tr key={row.id}><td className="px-4 py-2.5 font-semibold">{row.templateName || row.documentType}</td><td className="px-4 py-2.5">{row.templateVersion == null ? "—" : `v${row.templateVersion}`}</td><td className="px-4 py-2.5">{row.generatedByDisplay}</td><td className="px-4 py-2.5 text-xs">{dateLabel(row.generatedAt)}</td><td className="px-4 py-2.5">{row.pageCount ?? "—"}</td></tr>)}</tbody></table></div>}</section>
}

export function PortalPolicyDetail() {
  const { id } = useParams()
  const detail = usePortalPolicy(id)
  const d = detail.data
  if (!id) return null
  if (detail.isLoading) return <p className="p-8 text-center text-sm text-[var(--muted-foreground)]" role="status">Loading policy…</p>
  if (detail.isError || !d) return <div className="space-y-4 px-4 py-6"><Link to="/portal/policies" className="button-secondary">← Back to my policies</Link><ErrorCoach error={sanitizePortalError(detail.error)} title="Policy could not be loaded" /></div>

  return <div className="min-h-full space-y-5 px-4 py-5 sm:px-6 lg:px-8" data-testid="portal-policy-detail"><header className="surface-card px-5 py-4"><div className="flex flex-wrap items-start justify-between gap-4"><div><div className="mb-1 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--muted-foreground)]"><span>ZIC</span><span>/</span><span>Partner Portal</span><span>/</span><span>{d.policyNumber}</span></div><h1 className="text-2xl font-semibold tracking-[-0.04em] text-[var(--foreground)]">{d.policyNumber}</h1><p className="mt-1 text-sm text-[var(--muted-foreground)]">{d.productPlanDisplay}</p><div className="mt-3"><PolicyStatus status={d.status} /></div></div><Link to="/portal/policies" className="button-secondary">← Back</Link></div></header><PortalBanner /><div className="grid gap-4 lg:grid-cols-2"><section className="surface-card px-5 py-4" data-testid="portal-policy-overview"><h2 className="text-[10px] font-bold uppercase tracking-[0.12em] text-[var(--muted-foreground)]">Overview</h2><dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2"><div><dt className="text-xs text-[var(--muted-foreground)]">Policy</dt><dd className="font-semibold">{d.policyNumber}</dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Product / plan</dt><dd>{d.productPlanDisplay}</dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Commencement</dt><dd>{dateLabel(d.riskCommencementDate)}</dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Maturity</dt><dd>{dateLabel(d.maturityDate)}</dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Currency</dt><dd>{d.currency}</dd></div>{d.sumAssured != null && <div><dt className="text-xs text-[var(--muted-foreground)]">Sum assured</dt><dd>{formatMoney(d.sumAssured, d.currency)}</dd></div>}{d.premiumAmount != null && <div><dt className="text-xs text-[var(--muted-foreground)]">Premium</dt><dd>{formatMoney(d.premiumAmount, d.currency)}</dd></div>}{d.premiumFrequency && <div><dt className="text-xs text-[var(--muted-foreground)]">Premium frequency</dt><dd>{d.premiumFrequency}</dd></div>}</dl></section><section className="surface-card px-5 py-4" data-testid="portal-policy-members"><h2 className="text-[10px] font-bold uppercase tracking-[0.12em] text-[var(--muted-foreground)]">Members</h2><p className="mt-3 text-sm text-[var(--muted-foreground)]">Member coverage details are shown only when included by the partner-safe policy response. Contact agent for changes.</p></section></div><PortalPolicyDocuments policyId={id} /></div>
}

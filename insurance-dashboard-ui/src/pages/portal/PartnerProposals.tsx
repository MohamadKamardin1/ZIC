import { Link, useNavigate, useParams } from "react-router-dom"
import { HelpCircle, LifeBuoy } from "lucide-react"
import { InfoBanner } from "../../components/ui/Overlays"
import { ErrorCoach } from "../../components/commitments/ErrorCoach"
import { ProposalStatusBadge } from "../../components/proposals/ProposalStatusBadge"
import { usePortalProposal, usePortalProposals } from "../../lib/proposalsHooks"
import type { PortalProposalDetail } from "../../lib/proposals"
import { dateLabel, formatMoney } from "../../lib/commitmentsDisplay"
import { sanitizePortalError } from "./PartnerCommitments"

export const PROPOSAL_PORTAL_HELP_MESSAGE =
  "For changes, contact your ZIC representative or raise a ticket."

export function PortalBanner() {
  return (
    <InfoBanner title="Read-only view">
      <p className="flex items-start gap-2 text-sm">
        <HelpCircle size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
        {PROPOSAL_PORTAL_HELP_MESSAGE}
        <Link
          to="/tickets"
          className="inline-flex items-center gap-1 font-semibold text-[var(--primary)] underline-offset-2 hover:underline"
          data-testid="raise-ticket"
        >
          <LifeBuoy size={14} aria-hidden="true" />
          Raise Ticket
        </Link>
      </p>
    </InfoBanner>
  )
}

export function PartnerProposals() {
  const navigate = useNavigate()
  const list = usePortalProposals()
  const rows = list.data?.results ?? []

  return (
    <div className="min-h-full px-4 py-5 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-[1560px] space-y-5">
        <header className="flex flex-wrap items-end justify-between gap-4 border-b border-[var(--border)] pb-5">
          <div>
            <div className="mb-2 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--muted-foreground)]">
              <span>ZIC</span><span>/</span><span>Partner Portal</span><span>/</span><span>Proposals</span>
            </div>
            <h1 className="text-2xl font-semibold tracking-[-0.04em] text-[var(--foreground)]">My Proposals</h1>
            <p className="mt-1 text-sm text-[var(--muted-foreground)]">
              Your Ordinary Life insurance applications, scoped to your linked partner account.
            </p>
          </div>
          <Link to="/tickets" className="inline-flex items-center gap-2 text-sm font-semibold text-[var(--primary)] underline-offset-2 hover:underline">
            <LifeBuoy size={15} aria-hidden="true" />
            Raise Ticket
          </Link>
        </header>

        <PortalBanner />

        {list.isLoading && <p className="py-10 text-center text-sm text-[var(--muted-foreground)]">Loading your proposals…</p>}
        {list.isError && <ErrorCoach error={sanitizePortalError(list.error)} title="Proposals could not be loaded" />}
        {!list.isLoading && !list.isError && rows.length === 0 && (
          <p className="py-10 text-center text-sm text-[var(--muted-foreground)]" data-testid="portal-proposals-empty">
            You have no proposals at this time.
          </p>
        )}

        {rows.length > 0 && (
          <section className="surface-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm" data-testid="portal-proposals-table">
                <caption className="sr-only">Your proposals</caption>
                <thead className="bg-[var(--muted)]/45 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]">
                  <tr>
                    {["Proposal", "Product", "Status", "Premium", "Expiry"].map((heading) => (
                      <th key={heading} scope="col" className="px-4 py-2.5 font-bold">{heading}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  {rows.map((row) => (
                    <tr
                      key={row.id}
                      data-testid={`portal-proposal-row-${row.id}`}
                      className="cursor-pointer transition hover:bg-[var(--muted)]/25"
                      onClick={() => navigate(`/portal/proposals/${row.id}`)}
                    >
                      <td className="px-4 py-2.5 font-semibold text-[var(--foreground)]">{row.proposalNumber || "—"}</td>
                      <td className="px-4 py-2.5">{[row.product, row.plan].filter((part) => part && part !== "—").join(" / ") || "—"}</td>
                      <td className="px-4 py-2.5"><ProposalStatusBadge status={row.statusCode} /></td>
                      <td className="px-4 py-2.5 tabular-nums">{formatMoney(row.totalPremium ?? null, row.currency)}</td>
                      <td className="px-4 py-2.5">{dateLabel(row.expiryDate)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </div>
    </div>
  )
}

function FirstPremiumSection({ detail }: { detail: PortalProposalDetail }) {
  const premium = detail.firstPremium
  return (
    <section className="surface-card px-5 py-4" data-testid="portal-first-premium">
      <h3 className="text-[10px] font-bold uppercase tracking-[0.12em] text-[var(--muted-foreground)]">First Premium</h3>
      {!premium.linked ? (
        <p className="mt-3 text-sm text-[var(--muted-foreground)]">
          No first premium commitment has been raised for this proposal yet.
        </p>
      ) : (
        <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
          <div><dt className="text-xs text-[var(--muted-foreground)]">Commitment</dt><dd className="text-[var(--foreground)]">{premium.commitmentNumber || "—"}</dd></div>
          <div><dt className="text-xs text-[var(--muted-foreground)]">Commitment status</dt><dd className="text-[var(--foreground)]">{premium.status || "—"}</dd></div>
          <div><dt className="text-xs text-[var(--muted-foreground)]">Amount due</dt><dd className="tabular-nums text-[var(--foreground)]">{formatMoney(premium.amountDue ?? null, premium.currency)}</dd></div>
          <div><dt className="text-xs text-[var(--muted-foreground)]">Amount paid</dt><dd className="tabular-nums text-[var(--foreground)]">{formatMoney(premium.amountPaid ?? null, premium.currency)}</dd></div>
          <div><dt className="text-xs text-[var(--muted-foreground)]">Balance</dt><dd className="tabular-nums font-semibold text-[var(--foreground)]">{formatMoney(premium.balance ?? null, premium.currency)}</dd></div>
          <div>
            <dt className="text-xs text-[var(--muted-foreground)]">Fully paid</dt>
            <dd
              data-testid="portal-first-premium-posted"
              className={premium.posted ? "font-semibold text-[var(--success)]" : "font-semibold text-[var(--warning)]"}
            >
              {premium.posted ? "Yes — fully posted" : "Not yet"}
            </dd>
          </div>
        </dl>
      )}
    </section>
  )
}

function DocumentsSection({ detail }: { detail: PortalProposalDetail }) {
  return (
    <section className="surface-card overflow-hidden" data-testid="portal-documents">
      <div className="border-b bg-[var(--muted)]/35 px-5 py-3">
        <h3 className="text-sm font-bold text-[var(--foreground)]">Documents</h3>
        <p className="text-xs text-[var(--muted-foreground)]">{detail.documents.length} document(s) on file</p>
      </div>
      {detail.documents.length === 0 ? (
        <p className="px-5 py-6 text-center text-sm text-[var(--muted-foreground)]">No documents uploaded yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead className="bg-[var(--muted)]/45 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]">
              <tr>
                {["Document", "Status", "Mandatory", "Uploaded"].map((heading) => (
                  <th key={heading} scope="col" className="px-4 py-2.5 font-bold">{heading}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {detail.documents.map((doc) => (
                <tr key={doc.id} data-testid={`portal-document-row-${doc.id}`}>
                  <td className="px-4 py-2.5">
                    <span className="font-medium text-[var(--foreground)]">{doc.documentType}</span>
                    {doc.fileReference && <span className="ml-1 font-mono text-xs text-[var(--muted-foreground)]">{doc.fileReference}</span>}
                  </td>
                  <td className="px-4 py-2.5">{doc.status}</td>
                  <td className="px-4 py-2.5">{doc.mandatory ? "Mandatory" : "Optional"}</td>
                  <td className="px-4 py-2.5 text-xs">{dateLabel(doc.uploadedAt)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

export function PartnerProposalDetail() {
  const { id } = useParams()
  const detail = usePortalProposal(id)

  if (!id) return null
  if (detail.isLoading) return <p className="p-8 text-center text-sm text-[var(--muted-foreground)]">Loading proposal…</p>
  if (detail.isError || !detail.data) {
    return (
      <div className="px-4 py-6">
        <Link to="/portal/proposals" className="button-secondary">← Back to my proposals</Link>
        <div className="mt-4"><ErrorCoach error={sanitizePortalError(detail.error)} title="Proposal could not be loaded" /></div>
      </div>
    )
  }

  const d = detail.data

  return (
    <div className="min-h-full space-y-5 px-4 py-5 sm:px-6 lg:px-8" data-testid="portal-proposal-detail">
      <header className="surface-card px-5 py-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="mb-1 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--muted-foreground)]">
              <span>ZIC</span><span>/</span><span>Partner Portal</span><span>/</span><span>{d.proposalNumber}</span>
            </div>
            <h1 className="text-2xl font-semibold tracking-[-0.04em] text-[var(--foreground)]">{d.proposalNumber}</h1>
            <p className="mt-1 text-sm text-[var(--muted-foreground)]">
              {[d.product, d.plan].filter((part) => part && part !== "—").join(" / ") || "Ordinary Life proposal"}
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <ProposalStatusBadge status={d.statusCode} />
              <span className="text-sm font-semibold text-[var(--foreground)]">{formatMoney(d.totalPremium ?? null, d.currency)}</span>
            </div>
          </div>
          <Link to="/portal/proposals" className="button-secondary">← Back</Link>
        </div>
      </header>

      <PortalBanner />

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="surface-card px-5 py-4" data-testid="portal-overview">
          <h3 className="text-[10px] font-bold uppercase tracking-[0.12em] text-[var(--muted-foreground)]">Overview</h3>
          <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
            <div><dt className="text-xs text-[var(--muted-foreground)]">Policyholder</dt><dd className="text-[var(--foreground)]">{d.policyholder}</dd></div>
            <div><dt className="text-xs text-[var(--muted-foreground)]">Quotation</dt><dd className="text-[var(--foreground)]">{d.quotationNumber || "—"}</dd></div>
            <div><dt className="text-xs text-[var(--muted-foreground)]">Premium</dt><dd className="tabular-nums text-[var(--foreground)]">{formatMoney(d.totalPremium ?? null, d.currency)}</dd></div>
            <div><dt className="text-xs text-[var(--muted-foreground)]">Expiry</dt><dd className="text-[var(--foreground)]">{dateLabel(d.expiryDate)}</dd></div>
            <div><dt className="text-xs text-[var(--muted-foreground)]">Created</dt><dd className="text-[var(--foreground)]">{dateLabel(d.createdAt)}</dd></div>
            <div><dt className="text-xs text-[var(--muted-foreground)]">Beneficiaries</dt><dd className="text-[var(--foreground)]">{d.beneficiaries.length}</dd></div>
          </dl>
        </section>

        <FirstPremiumSection detail={d} />
      </div>

      <DocumentsSection detail={d} />
    </div>
  )
}


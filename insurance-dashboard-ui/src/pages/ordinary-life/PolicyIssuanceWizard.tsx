import { useMemo, useState } from "react"
import { ClipboardCheck, FileCheck2, Search, ShieldAlert, UserRound } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { ErrorCoach } from "../../components/commitments/ErrorCoach"
import { InfoBanner } from "../../components/ui/Overlays"
import { Wizard, type WizardStep } from "../../components/ui/Wizard"
import { StatusBadge } from "../../components/ui/StatusBadge"
import { useToast } from "../../components/ui/Toast"
import { ProposalStatusBadge } from "../../components/proposals/ProposalStatusBadge"
import { MoneyCell } from "../../components/policies"
import { formatMoney } from "../../lib/commitmentsDisplay"
import { useIssuePolicyMutation, useIssuableProposals } from "../../lib/policiesHooks"
import type { ProposalListItem } from "../../lib/proposals"

function proposalProduct(proposal: ProposalListItem): string {
  return [proposal.productName, proposal.planName].filter(Boolean).join(" — ") || "Unspecified product / plan"
}

function proposalPremium(proposal: ProposalListItem): string {
  return proposal.totalPremium === null || proposal.totalPremium === undefined ? "—" : formatMoney(proposal.totalPremium, proposal.currency ?? "TZS")
}

function proposalReady(proposal: ProposalListItem): boolean {
  return proposal.paymentReady || proposal.firstPremiumPosted
}

function ProposalCard({ proposal, selected, onSelect }: { proposal: ProposalListItem; selected: boolean; onSelect: () => void }) {
  const ready = proposalReady(proposal)
  return (
    <button type="button" onClick={onSelect} aria-pressed={selected} className={`w-full rounded-[12px] border p-4 text-left transition hover:border-[var(--ring)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] ${selected ? "border-[var(--primary)] bg-[var(--primary)]/5 ring-1 ring-[var(--primary)]" : "border-[var(--border)] bg-[var(--card)]"}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-mono text-xs font-bold text-[var(--primary)]">{proposal.proposalNumber}</p>
          <h3 className="mt-1 truncate text-sm font-bold text-[var(--foreground)]">{proposal.partnerName}</h3>
          <p className="mt-1 text-xs text-[var(--muted-foreground)]">{proposalProduct(proposal)}</p>
        </div>
        <ProposalStatusBadge status={proposal.status} />
      </div>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-[var(--border)] pt-3 text-xs">
        <span className="font-semibold text-[var(--foreground)]">Premium <MoneyCell value={proposal.totalPremium} currency={proposal.currency} /></span>
        <span className={`inline-flex items-center gap-1 font-bold ${ready ? "text-[var(--success)]" : "text-[var(--warning)]"}`}>
          {ready ? <ClipboardCheck size={13} aria-hidden="true" /> : <ShieldAlert size={13} aria-hidden="true" />}
          {ready ? "First premium ready" : "First premium not fully paid"}
        </span>
      </div>
    </button>
  )
}

function ProposalSnapshot({ proposal }: { proposal: ProposalListItem | null }) {
  if (!proposal) return <InfoBanner title="Select a proposal first">Choose one of the eligible proposals to review its issuance snapshot.</InfoBanner>
  return (
    <div className="space-y-4">
      <InfoBanner title="One-way policy issuance">Issuing creates the policy from this proposal and locks the contract to its immutable issuance snapshot. Confirm the details before continuing.</InfoBanner>
      {!proposalReady(proposal) && <div className="flex items-start gap-3 rounded-[10px] border border-[var(--warning)]/35 bg-[var(--warning)]/10 p-3 text-sm" role="alert"><ShieldAlert size={18} className="mt-0.5 shrink-0 text-[var(--warning)]" aria-hidden="true" /><div><p className="font-bold">First premium is not fully posted</p><p className="mt-1 text-xs leading-5 text-[var(--muted-foreground)]">This proposal is shown for safety review, but production issuance will be rejected until the first premium commitment is fully funded and posted.</p></div></div>}
      <dl className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-[10px] border border-[var(--border)] p-3"><dt className="text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">Proposal number</dt><dd className="mt-1 font-mono text-sm font-bold">{proposal.proposalNumber}</dd></div>
        <div className="rounded-[10px] border border-[var(--border)] p-3"><dt className="text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">Quotation reference</dt><dd className="mt-1 text-sm font-bold">{proposal.quotationNumber ?? "—"}</dd></div>
        <div className="rounded-[10px] border border-[var(--border)] p-3"><dt className="text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">Applicant</dt><dd className="mt-1 text-sm font-bold">{proposal.partnerName || "—"}</dd></div>
        <div className="rounded-[10px] border border-[var(--border)] p-3"><dt className="text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">Product / plan</dt><dd className="mt-1 text-sm font-bold">{proposalProduct(proposal)}</dd></div>
        <div className="rounded-[10px] border border-[var(--border)] p-3"><dt className="text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">Premium</dt><dd className="mt-1 text-sm font-bold"><MoneyCell value={proposal.totalPremium} currency={proposal.currency} /></dd></div>
        <div className="rounded-[10px] border border-[var(--border)] p-3"><dt className="text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">Readiness</dt><dd className="mt-1"><StatusBadge value={proposalReady(proposal) ? "First premium ready" : "Payment required"} tone={proposalReady(proposal) ? "success" : "warning"} /></dd></div>
      </dl>
    </div>
  )
}

export default function PolicyIssuanceWizard() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [search, setSearch] = useState("")
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [issueError, setIssueError] = useState<unknown>(null)
  const proposals = useIssuableProposals(search)
  const issue = useIssuePolicyMutation()
  const selectedProposal = useMemo(() => proposals.data?.find((proposal) => proposal.id === selectedId) ?? null, [proposals.data, selectedId])

  const selectProposal = (proposal: ProposalListItem) => {
    setIssueError(null)
    setSelectedId(proposal.id)
  }

  const completeIssuance = () => {
    if (!selectedProposal || issue.isPending) return
    setIssueError(null)
    issue.mutate(selectedProposal.id, {
      onSuccess: (payload) => {
        const record = payload as Record<string, unknown>
        const policyId = typeof record.id === "string" ? record.id : ""
        const policyNumber = typeof record.policy_number === "string" ? record.policy_number : typeof record.policyNumber === "string" ? record.policyNumber : "the policy"
        toast({ title: `Policy ${policyNumber} Issued Successfully.`, message: "The immutable policy snapshot was created.", tone: "success" })
        navigate(policyId ? `/ordinary-life/policies/${policyId}` : `/ordinary-life/policies?policy_number=${encodeURIComponent(policyNumber)}`)
      },
      onError: (error) => setIssueError(error),
    })
  }

  const steps = useMemo<WizardStep[]>(() => [
    {
      id: "proposal",
      label: "Select Proposal",
      icon: UserRound,
      validate: () => Boolean(selectedProposal),
      content: (
        <div className="space-y-4" data-testid="issuance-select-step">
          <div>
            <p className="text-sm font-bold">Choose an eligible proposal</p>
            <p className="mt-1 text-xs leading-5 text-[var(--muted-foreground)]">Only proposals in AWAITING_FIRST_PREMIUM or PAYMENT_READY are listed. The first premium check is repeated by the backend at issue time.</p>
          </div>
          <label className="relative block" htmlFor="issuance-proposal-search"><span className="sr-only">Search proposals</span><Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)]" aria-hidden="true" /><input id="issuance-proposal-search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search proposal number, applicant, or product" className="h-10 w-full rounded-[10px] border bg-[var(--card)] pl-9 pr-3 text-sm outline-none focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)]" /></label>
          {proposals.isPending && <div className="space-y-3" aria-busy="true" aria-label="Loading eligible proposals"><div className="h-28 animate-pulse rounded-[12px] bg-[var(--muted)]" /><div className="h-28 animate-pulse rounded-[12px] bg-[var(--muted)]" /></div>}
          {proposals.isError && <ErrorCoach error={proposals.error} title="Eligible proposals could not be loaded" onRetry={() => void proposals.refetch()} />}
          {!proposals.isPending && !proposals.isError && proposals.data?.length === 0 && <InfoBanner title="No eligible proposals">No proposal is currently ready for policy issuance. Complete the proposal payment gate, then return here.</InfoBanner>}
          {!proposals.isPending && !proposals.isError && proposals.data && proposals.data.length > 0 && <div className="grid gap-3 lg:grid-cols-2" role="list" aria-label="Eligible proposals">{proposals.data.map((proposal) => <div key={proposal.id} role="listitem"><ProposalCard proposal={proposal} selected={proposal.id === selectedId} onSelect={() => selectProposal(proposal)} /></div>)}</div>}
          {!selectedProposal && !proposals.isError && <p className="text-xs font-semibold text-[var(--muted-foreground)]">Select one proposal to continue.</p>}
        </div>
      ),
    },
    {
      id: "confirm",
      label: "Confirm & Issue",
      icon: FileCheck2,
      validate: () => Boolean(selectedProposal),
      content: (
        <div className="space-y-4" data-testid="issuance-confirm-step">
          <div><p className="text-sm font-bold">Review Proposal Snapshot</p><p className="mt-1 text-xs leading-5 text-[var(--muted-foreground)]">Confirm the applicant, plan, premium, and first-premium readiness before issuing the contract.</p></div>
          <ProposalSnapshot proposal={selectedProposal} />
          {issueError ? <ErrorCoach error={issueError} title="Proposal not eligible for issuance" onRetry={completeIssuance} /> : null}
          {selectedProposal && proposalReady(selectedProposal) && <p className="rounded-[10px] bg-[var(--success)]/10 px-3 py-3 text-sm font-semibold text-[var(--success)]">This proposal passed the client-side readiness check. The server will perform the final BR-03 validation.</p>}
        </div>
      ),
    },
  ], [completeIssuance, issueError, proposals.data, proposals.error, proposals.isError, proposals.isPending, proposals.refetch, search, selectedId, selectedProposal])

  return (
    <div className="space-y-5">
      <header className="section-header p-5">
        <p className="text-xs font-bold uppercase tracking-[0.15em] text-white/70">Ordinary Life · Policies</p>
        <h1 className="mt-2 text-2xl font-extrabold tracking-tight">New Policy</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-white/80">Issue an immutable policy contract from a proposal that has cleared the first-premium gate.</p>
      </header>
      <Wizard steps={steps} completeLabel={issue.isPending ? "Issuing Policy…" : "Issue Policy"} completeDisabled={!selectedProposal || !proposalReady(selectedProposal) || issue.isPending} onCancel={() => navigate("/ordinary-life/policies")} onComplete={completeIssuance} />
    </div>
  )
}

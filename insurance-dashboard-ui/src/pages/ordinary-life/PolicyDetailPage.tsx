import { useMemo, useState } from "react"
import { useSearchParams, useNavigate, useParams } from "react-router-dom"
import { ArrowLeft, Banknote, Ban, CalendarDays, FileText, HandCoins, Landmark, RotateCcw, ShieldAlert, ShieldCheck, UserRound } from "lucide-react"
import { ErrorCoach } from "../../components/commitments/ErrorCoach"
import { InfoBanner, Modal } from "../../components/ui/Overlays"
import PolicyEndorsementModal from "./PolicyEndorsementModal"
import PolicyFinancialsTab from "./PolicyFinancialsTab"
import PolicyTerminalActions from "./PolicyTerminalActions"
import PolicyPrintPreviewModal from "./PolicyPrintPreviewModal"
import { DocumentInstancesPanel } from "../../components/documents/DocumentInstancesPanel"
import { MasterDetailPage } from "../../components/ui/Patterns"
import { StatusBadge } from "../../components/ui/StatusBadge"
import { MoneyCell, PolicyHeader } from "../../components/policies"
import { useAccess } from "../../lib/access"
import { renderFk, sanitizeForDisplay } from "../../lib/display"
import { dateLabel } from "../../lib/commitmentsDisplay"
import { usePolicyBenefits, usePolicyDetail, usePolicyEndorsements, usePolicyLoans, usePolicyMembers, usePolicyOptions, usePolicyRiders, usePolicyWithdrawals } from "../../lib/policiesHooks"
import type { PolicyAuditEntry, PolicyDetail, PolicyEndorsement } from "../../lib/policies"

const ACTION_PERMISSION: Record<string, string> = {
  endorse: "ol_policies.endorse",
  loan: "ol_policies.service",
  withdraw: "ol_policies.service",
  surrender: "ol_policies.service",
  paid_up: "ol_policies.service",
  cancel: "ol_policies.cancel",
  print: "ol_policies.print",
  reinstate: "ol_policies.reinstate",
}

const ACTION_ALIASES: Record<string, string[]> = {
  loan: ["loan", "service"],
  withdraw: ["withdraw", "service"],
  surrender: ["surrender", "service"],
  paid_up: ["paid_up", "service"],
  cancel: ["cancel"],
}

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "members", label: "Members & Riders" },
  { id: "endorsements", label: "Endorsements" },
  { id: "financials", label: "Financials" },
  { id: "documents", label: "Documents" },
  { id: "audit", label: "Audit" },
]

function snapshotValue(value: unknown): string {
  if (typeof value === "boolean") return value ? "Yes" : "No"
  if (value === null || value === undefined || value === "") return "—"
  if (Array.isArray(value)) return value.map((item) => renderFk(item)).join(", ") || "—"
  if (typeof value === "object") return renderFk(value)
  return renderFk(value)
}

function snapshotPick(snapshot: Record<string, unknown>, ...keys: string[]): unknown {
  for (const key of keys) if (snapshot[key] !== undefined && snapshot[key] !== null && snapshot[key] !== "") return snapshot[key]
  return null
}

function actionList(policy: PolicyDetail): string[] {
  return policy.allowedActions.map((action) => action.toLowerCase())
}

function DetailAction({ label, icon, onClick, disabled = false, danger = false }: { label: string; icon: React.ReactNode; onClick: () => void; disabled?: boolean; danger?: boolean }) {
  return <button type="button" onClick={onClick} disabled={disabled} className={danger ? "inline-flex min-h-9 items-center gap-1.5 rounded-[9px] border border-white/25 bg-white/10 px-3 text-xs font-bold text-white transition hover:bg-white/20 disabled:cursor-not-allowed disabled:opacity-45" : "inline-flex min-h-9 items-center gap-1.5 rounded-[9px] border border-white/25 bg-white/10 px-3 text-xs font-bold text-white transition hover:bg-white/20 disabled:cursor-not-allowed disabled:opacity-45"}>{icon}{label}</button>
}

function SnapshotCard({ policy }: { policy: PolicyDetail }) {
  const snapshot = policy.contractSnapshot
  const facts: Array<[string, unknown]> = [
    ["Policy term", snapshotPick(snapshot, "term_years", "policy_term_years", "policy_term")],
    ["Payment period", snapshotPick(snapshot, "payment_period_years", "payment_period")],
    ["Payment frequency", snapshotPick(snapshot, "premium_frequency", "payment_frequency")],
    ["Quote basis", snapshotPick(snapshot, "quote_basis", "premium_basis")],
    ["Premium factor", snapshotPick(snapshot, "premium_factor", "premium_factor_display")],
    ["Estimated maturity", snapshotPick(snapshot, "estimated_maturity_value", "maturity_value")],
    ["Estimated bonus rate", snapshotPick(snapshot, "estimated_bonus_rate", "bonus_rate")],
    ["Joint life", snapshotPick(snapshot, "joint_life", "is_joint_life")],
    ["Mortgage", snapshotPick(snapshot, "mortgage", "mortgage_selected")],
    ["Personal accident", snapshotPick(snapshot, "pa", "personal_accident")],
    ["Premium waiver", snapshotPick(snapshot, "wp", "premium_waiver")],
  ]
  return <section className="surface-card p-4" aria-labelledby="snapshot-heading"><div className="mb-4 flex items-center justify-between gap-3"><div><h2 id="snapshot-heading" className="text-sm font-bold">Contract snapshot</h2><p className="mt-1 text-xs text-[var(--muted-foreground)]">Immutable terms captured at issuance.</p></div><ShieldCheck size={18} className="text-[var(--success)]" aria-hidden="true" /></div><dl className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{facts.map(([label, value]) => <div key={label} className="rounded-[10px] border border-[var(--border)] p-3"><dt className="text-[11px] font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">{label}</dt><dd className="mt-1 text-sm font-semibold">{snapshotValue(value)}</dd></div>)}</dl></section>
}

function LinkedContext({ policy }: { policy: PolicyDetail }) {
  const proposal = policy.linkedProposal ?? {}
  const hasProposal = Object.keys(proposal).length > 0
  return <div className="grid gap-4 lg:grid-cols-2"><section className="surface-card p-4" aria-labelledby="proposal-reference-heading"><div className="mb-3 flex items-center gap-2"><FileText size={17} className="text-[var(--primary)]" aria-hidden="true" /><h2 id="proposal-reference-heading" className="text-sm font-bold">Linked proposal reference</h2></div>{hasProposal ? <dl className="grid gap-3 sm:grid-cols-2"><div><dt className="text-xs text-[var(--muted-foreground)]">Proposal number</dt><dd className="mt-1 text-sm font-semibold">{renderFk(proposal.proposal_number ?? proposal.proposalNumber ?? proposal.proposal_display)}</dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Status</dt><dd className="mt-1"><StatusBadge value={renderFk(proposal.status, undefined, "Unknown")} /></dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Quotation</dt><dd className="mt-1 text-sm font-semibold">{renderFk(proposal.quotation_number ?? proposal.quote_number ?? proposal.quotation_display)}</dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Applicant</dt><dd className="mt-1 text-sm font-semibold">{renderFk(proposal.partner_display ?? proposal.applicant_display ?? proposal.partner_name)}</dd></div></dl> : <InfoBanner>No linked proposal reference was supplied by the policy record.</InfoBanner>}</section><section className="surface-card p-4" aria-labelledby="agent-details-heading"><div className="mb-3 flex items-center gap-2"><UserRound size={17} className="text-[var(--primary)]" aria-hidden="true" /><h2 id="agent-details-heading" className="text-sm font-bold">Agent details</h2></div><dl className="grid gap-3 sm:grid-cols-2"><div><dt className="text-xs text-[var(--muted-foreground)]">Agent / intermediary</dt><dd className="mt-1 text-sm font-semibold">{renderFk(policy.agentDisplay)}</dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Policyholder identity</dt><dd className="mt-1 text-sm font-semibold">{renderFk(policy.policyholderDisplay)}</dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Currency</dt><dd className="mt-1 text-sm font-semibold">{renderFk(policy.currency)}</dd></div><div><dt className="text-xs text-[var(--muted-foreground)]">Policy version</dt><dd className="mt-1 text-sm font-semibold">{policy.version ?? 1}</dd></div></dl></section></div>
}

function AuditTimeline({ entries }: { entries: PolicyAuditEntry[] }) {
  if (!entries.length) return <InfoBanner title="No status history yet">The policy has no recorded lifecycle events to display.</InfoBanner>
  return <ol className="relative ml-3 border-l border-[var(--border)]" aria-label="Policy status history">{entries.map((entry) => <li key={entry.id} className="relative pb-5 pl-6 last:pb-0"><span className="absolute -left-[7px] top-1 h-3 w-3 rounded-full border-2 border-[var(--card)] bg-[var(--primary)]" aria-hidden="true" /><div className="flex flex-wrap items-start justify-between gap-2"><div><p className="text-sm font-bold">{entry.eventType}</p><p className="mt-1 text-xs text-[var(--muted-foreground)]">{entry.fromStatus ? `${renderFk(entry.fromStatus)} → ` : ""}{renderFk(entry.toStatus, undefined, "Recorded")} · {renderFk(entry.actorDisplay, undefined, "System")}</p></div><time className="text-xs text-[var(--muted-foreground)]">{dateLabel(entry.createdAt)}</time></div>{entry.reason && <p className="mt-2 text-xs leading-5 text-[var(--muted-foreground)]">{entry.reason}</p>}{entry.sourceChannel && <span className="mt-2 inline-flex rounded-full bg-[var(--secondary)] px-2 py-1 text-[11px] font-semibold text-[var(--muted-foreground)]">Source: {entry.sourceChannel}</span>}</li>)}</ol>
}

function endorsementTone(status: string): "success" | "warning" | "danger" | "info" | "neutral" {
  const value = status.toUpperCase()
  if (value === "APPLIED" || value === "APPROVED") return "success"
  if (value === "PENDING" || value === "DRAFT") return "warning"
  if (value === "REJECTED") return "danger"
  return "neutral"
}

function EndorsementsTab({ rows, canCreate, onCreate }: { rows: PolicyEndorsement[]; canCreate: boolean; onCreate: () => void }) {
  const [selected, setSelected] = useState<PolicyEndorsement | null>(null)
  return <section className="surface-card p-4" aria-labelledby="endorsements-heading"><div className="mb-4 flex flex-wrap items-start justify-between gap-3"><div><h2 id="endorsements-heading" className="text-sm font-bold">Endorsement history</h2><p className="mt-1 text-xs text-[var(--muted-foreground)]">Append-only requests preserve before and after values for every material change.</p></div>{canCreate && <button type="button" className="button-primary" onClick={onCreate}>Endorse</button>}</div>{rows.length ? <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead><tr className="border-b text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><th className="px-3 py-2">Endorsement number</th><th className="px-3 py-2">Type</th><th className="px-3 py-2">Date</th><th className="px-3 py-2">Status</th><th className="px-3 py-2">Description</th><th className="px-3 py-2 text-right">Action</th></tr></thead><tbody>{rows.map((endorsement) => <tr key={endorsement.id} className="border-b last:border-0"><td className="px-3 py-3 font-mono font-semibold">{renderFk(endorsement.endorsementNumber)}</td><td className="px-3 py-3">{renderFk(endorsement.endorsementType)}</td><td className="px-3 py-3">{dateLabel(endorsement.effectiveDate)}</td><td className="px-3 py-3"><StatusBadge value={renderFk(endorsement.status)} tone={endorsementTone(endorsement.status)} /></td><td className="max-w-[260px] truncate px-3 py-3">{renderFk(endorsement.description, undefined, "—")}</td><td className="px-3 py-3 text-right"><button type="button" className="button-secondary min-h-8 px-2.5 text-xs" onClick={() => setSelected(endorsement)}>View Detail</button></td></tr>)}</tbody></table></div> : <InfoBanner title="No endorsements">No endorsement requests have been appended to this policy.</InfoBanner>}
    <Modal open={Boolean(selected)} title={selected ? `Endorsement ${selected.endorsementNumber}` : "Endorsement detail"} onClose={() => setSelected(null)} size="lg" footer={<button type="button" className="button-secondary" onClick={() => setSelected(null)}>Close</button>}>
      {selected && <div className="space-y-4"><div className="grid gap-3 sm:grid-cols-2"><div><p className="text-xs text-[var(--muted-foreground)]">Type</p><p className="mt-1 text-sm font-semibold">{renderFk(selected.endorsementType)}</p></div><div><p className="text-xs text-[var(--muted-foreground)]">Status</p><StatusBadge value={renderFk(selected.status)} tone={endorsementTone(selected.status)} /></div></div><div className="grid gap-4 md:grid-cols-2"><div><h3 className="mb-2 text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">Before</h3><pre className="max-h-72 overflow-auto rounded-[10px] bg-[var(--muted)] p-3 text-xs leading-5">{JSON.stringify(sanitizeForDisplay(selected.beforeSnapshot ?? {}), null, 2)}</pre></div><div><h3 className="mb-2 text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">After</h3><pre className="max-h-72 overflow-auto rounded-[10px] bg-[var(--muted)] p-3 text-xs leading-5">{JSON.stringify(sanitizeForDisplay(selected.afterSnapshot ?? {}), null, 2)}</pre></div></div></div>}
    </Modal>
  </section>
}

function CompositionTab({ policy, members, riders, benefits, canAdd, onAddMember, onAddRider }: { policy: PolicyDetail; members: PolicyDetail["members"]; riders: PolicyDetail["riders"]; benefits: PolicyDetail["benefits"]; canAdd: boolean; onAddMember: () => void; onAddRider: () => void }) {
  return <div className="space-y-4">
    <section className="surface-card p-4" aria-labelledby="members-heading">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3"><div><h2 id="members-heading" className="text-sm font-bold">Members</h2><p className="mt-1 text-xs text-[var(--muted-foreground)]">Read-only covered lives linked to this policy.</p></div>{canAdd && <button type="button" className="button-secondary inline-flex items-center gap-2" onClick={onAddMember}>Add Member</button>}</div>
      {members.length ? <div className="overflow-x-auto"><table className="w-full min-w-[720px] text-left text-sm"><thead><tr className="border-b text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><th className="px-3 py-2">Name</th><th className="px-3 py-2">Relation</th><th className="px-3 py-2">DOB</th><th className="px-3 py-2">Gender</th><th className="px-3 py-2 text-right">Sum assured / cover</th></tr></thead><tbody>{members.map((member) => <tr key={member.id} className="border-b last:border-0"><td className="px-3 py-3 font-semibold">{renderFk(member.name)}</td><td className="px-3 py-3">{renderFk(member.memberRelation)}</td><td className="px-3 py-3">{dateLabel(member.dob)}</td><td className="px-3 py-3">{renderFk(member.gender)}</td><td className="px-3 py-3 text-right"><MoneyCell value={member.benefitAmount} currency={policy.currency} /></td></tr>)}</tbody></table></div> : <InfoBanner title="No covered lives">The principal member is not present in the composition response.</InfoBanner>}
    </section>
    <section className="surface-card p-4" aria-labelledby="riders-heading">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3"><div><h2 id="riders-heading" className="text-sm font-bold">Attached riders</h2><p className="mt-1 text-xs text-[var(--muted-foreground)]">Riders are displayed from policy composition; changes are made through an endorsement.</p></div>{canAdd && <button type="button" className="button-secondary inline-flex items-center gap-2" onClick={onAddRider}>Add Rider</button>}</div>
      {riders.length ? <div className="overflow-x-auto"><table className="w-full min-w-[620px] text-left text-sm"><thead><tr className="border-b text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><th className="px-3 py-2">Rider name</th><th className="px-3 py-2 text-right">Benefit amount</th><th className="px-3 py-2 text-right">Premium load</th></tr></thead><tbody>{riders.map((rider) => <tr key={rider.id} className="border-b last:border-0"><td className="px-3 py-3 font-semibold">{renderFk(rider.riderCode)}</td><td className="px-3 py-3 text-right"><MoneyCell value={rider.sumAssured ?? rider.amount} currency={policy.currency} /></td><td className="px-3 py-3 text-right"><MoneyCell value={rider.premium} currency={policy.currency} /></td></tr>)}</tbody></table></div> : <InfoBanner title="No riders attached">This policy has no riders in its issued composition.</InfoBanner>}
    </section>
    <section className="surface-card p-4" aria-labelledby="benefits-heading"><div className="mb-4"><h2 id="benefits-heading" className="text-sm font-bold">Benefits</h2><p className="mt-1 text-xs text-[var(--muted-foreground)]">Benefit basis and values retained in the policy snapshot.</p></div>{benefits.length ? <div className="overflow-x-auto"><table className="w-full min-w-[560px] text-left text-sm"><thead><tr className="border-b text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><th className="px-3 py-2">Benefit type</th><th className="px-3 py-2">Basis</th><th className="px-3 py-2 text-right">Value</th></tr></thead><tbody>{benefits.map((benefit) => <tr key={benefit.id} className="border-b last:border-0"><td className="px-3 py-3 font-semibold">{renderFk(benefit.benefitType)}</td><td className="px-3 py-3">{renderFk(benefit.calculationBasis)}</td><td className="px-3 py-3 text-right"><MoneyCell value={benefit.amount} currency={policy.currency} /></td></tr>)}</tbody></table></div> : <InfoBanner title="No benefits listed">Benefits are not present in the composition response.</InfoBanner>}</section>
  </div>
}

export default function PolicyDetailPage() {
  const { policyId } = useParams<{ policyId: string }>()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [endorsementModalOpen, setEndorsementModalOpen] = useState(false)
  const [loanModalOpen, setLoanModalOpen] = useState(false)
  const [withdrawalModalOpen, setWithdrawalModalOpen] = useState(false)
  const [surrenderModalOpen, setSurrenderModalOpen] = useState(false)
  const [paidUpModalOpen, setPaidUpModalOpen] = useState(false)
  const [cancelModalOpen, setCancelModalOpen] = useState(false)
  const [policyPrintModalOpen, setPolicyPrintModalOpen] = useState(false)
  const { access, isSuperAdmin } = useAccess()
  const detailQuery = usePolicyDetail(policyId)
  const statusOptions = usePolicyOptions("statuses", {}, Boolean(detailQuery.data))
  const memberQuery = usePolicyMembers(policyId, Boolean(detailQuery.data))
  const riderQuery = usePolicyRiders(policyId, Boolean(detailQuery.data))
  const benefitQuery = usePolicyBenefits(policyId, Boolean(detailQuery.data))
  const endorsementQuery = usePolicyEndorsements(policyId, Boolean(detailQuery.data))
  const loanQuery = usePolicyLoans(policyId, Boolean(detailQuery.data))
  const withdrawalQuery = usePolicyWithdrawals(policyId, Boolean(detailQuery.data))
  const policy = detailQuery.data ?? null
  const activeTab = TABS.some((tab) => tab.id === searchParams.get("tab")) ? searchParams.get("tab") ?? "overview" : "overview"

  const permissions = useMemo(() => new Set(access.permissions.map((permission) => `${permission.module}.${permission.action}`)), [access.permissions])
  const allowed = useMemo(() => policy ? new Set(actionList(policy)) : new Set<string>(), [policy])
  const canAction = (key: string) => Boolean(policy && (ACTION_ALIASES[key] ?? [key]).some((alias) => allowed.has(alias)) && (isSuperAdmin || permissions.has(ACTION_PERMISSION[key])))
  const goAction = (key: string) => navigate(`/ordinary-life/policies/${policyId}?action=${key}`)

  if (detailQuery.isPending) return <div className="space-y-4" aria-busy="true"><div className="h-52 animate-pulse rounded-[12px] bg-[var(--muted)]" /><div className="h-48 animate-pulse rounded-[12px] bg-[var(--muted)]" /></div>
  if (detailQuery.isError || !policy) return <div className="space-y-4"><button type="button" className="button-secondary" onClick={() => navigate("/ordinary-life/policies")}><ArrowLeft size={15} aria-hidden="true" />Back to policies</button><ErrorCoach error={detailQuery.error ?? new Error("Policy record not found")} title="Policy details could not be loaded" onRetry={() => void detailQuery.refetch()} /></div>

  const lapsed = policy.status.toUpperCase() === "LAPSED"
  const matured = policy.status.toUpperCase().startsWith("MATURED")
  const lapseDate = snapshotPick(policy.contractSnapshot, "lapsed_since", "lapse_date", "lapse_effective_date")
  const isActive = policy.status.toUpperCase() === "ACTIVE"
  const canFinancialService = !lapsed && !matured
  const actionSlot = <div className="flex flex-wrap justify-end gap-2">{canAction("endorse") ? <DetailAction label="Endorse" icon={<FileText size={14} aria-hidden="true" />} onClick={() => setEndorsementModalOpen(true)} /> : null}{canFinancialService && canAction("loan") ? <DetailAction label="Loan" icon={<Banknote size={14} aria-hidden="true" />} onClick={() => setLoanModalOpen(true)} /> : null}{canFinancialService && canAction("withdraw") ? <DetailAction label="Withdraw" icon={<HandCoins size={14} aria-hidden="true" />} onClick={() => setWithdrawalModalOpen(true)} /> : null}{isActive && canAction("surrender") ? <DetailAction label="Surrender" icon={<Landmark size={14} aria-hidden="true" />} onClick={() => setSurrenderModalOpen(true)} /> : null}{canAction("cancel") ? <DetailAction label="Cancel Policy" icon={<Ban size={14} aria-hidden="true" />} onClick={() => setCancelModalOpen(true)} danger /> : null}{canAction("print") ? <DetailAction label="Print Contract" icon={<FileText size={14} aria-hidden="true" />} onClick={() => setPolicyPrintModalOpen(true)} /> : null}</div>

  return <><MasterDetailPage eyebrow="Ordinary Life · Policy detail" title={policy.policyNumber} description="Read-only contract overview sourced from the immutable issuance snapshot." status={{ value: policy.statusDisplay, tone: lapsed ? "danger" : matured ? "success" : "info" }} actions={<button type="button" className="button-secondary border-white/30 bg-white/10 text-white hover:bg-white/20" onClick={() => navigate("/ordinary-life/policies")}><ArrowLeft size={15} aria-hidden="true" />Back to policies</button>}>
    <PolicyHeader data={policy} statusOptions={statusOptions.data ?? []} actionSlot={actionSlot} />
    {lapsed && <div className="flex flex-wrap items-center justify-between gap-3 rounded-[12px] border border-[var(--destructive)]/30 bg-[var(--destructive)]/10 px-4 py-3" role="alert"><div className="flex items-start gap-2"><ShieldAlert size={18} className="mt-0.5 text-[var(--destructive)]" aria-hidden="true" /><div><p className="text-sm font-bold">Lapsed Since {dateLabel(typeof lapseDate === "string" ? lapseDate : null)}</p><p className="mt-1 text-xs text-[var(--muted-foreground)]">Premiums are not currently in force. Reinstate the policy within the configured window to restore cover.</p></div></div><div className="flex flex-wrap gap-2">{canAction("reinstate") && <button type="button" className="button-primary inline-flex items-center gap-2" onClick={() => goAction("reinstate")}><RotateCcw size={15} aria-hidden="true" />Reinstate</button>}{canAction("paid_up") && <button type="button" className="button-secondary inline-flex items-center gap-2" onClick={() => setPaidUpModalOpen(true)}><ShieldCheck size={15} aria-hidden="true" />Convert to Paid-Up</button>}</div></div>}
    {matured && <InfoBanner title="Matured policy"><span className="inline-flex items-center gap-2"><StatusBadge value="Matured" tone="success" />Maturity processing and payment records are available in the Financials tab.</span></InfoBanner>}
    <nav className="surface-card flex gap-1 overflow-x-auto p-1" aria-label="Policy detail tabs">{TABS.map((tab) => <button type="button" key={tab.id} onClick={() => setSearchParams({ tab: tab.id })} className={`whitespace-nowrap rounded-[9px] px-4 py-2.5 text-sm font-bold transition ${activeTab === tab.id ? "bg-[var(--primary)] text-[var(--primary-foreground)]" : "text-[var(--muted-foreground)] hover:bg-[var(--secondary)] hover:text-[var(--foreground)]"}`} aria-current={activeTab === tab.id ? "page" : undefined}>{tab.label}</button>)}</nav>
    {activeTab === "overview" && <div className="space-y-4"><SnapshotCard policy={policy} /><LinkedContext policy={policy} /><section className="surface-card p-4" aria-labelledby="history-heading"><div className="mb-4 flex items-center gap-2"><CalendarDays size={17} className="text-[var(--primary)]" aria-hidden="true" /><h2 id="history-heading" className="text-sm font-bold">Status history</h2></div><AuditTimeline entries={policy.auditLogs} /></section></div>}
    {activeTab === "members" && <CompositionTab policy={policy} members={memberQuery.data ?? policy.members} riders={riderQuery.data ?? policy.riders} benefits={benefitQuery.data ?? policy.benefits} canAdd={canAction("endorse")} onAddMember={() => goAction("endorse")} onAddRider={() => goAction("endorse")} />}
    {activeTab === "endorsements" && <EndorsementsTab rows={endorsementQuery.data?.results ?? policy.endorsements} canCreate={canAction("endorse")} onCreate={() => setEndorsementModalOpen(true)} />}
    {activeTab === "financials" && <PolicyFinancialsTab policy={policy} loans={loanQuery.data?.results ?? []} withdrawals={withdrawalQuery.data?.results ?? []} canRequestLoan={canFinancialService && canAction("loan")} canRequestWithdrawal={canFinancialService && canAction("withdraw")} loanModalOpen={loanModalOpen} withdrawalModalOpen={withdrawalModalOpen} onLoanModalChange={setLoanModalOpen} onWithdrawalModalChange={setWithdrawalModalOpen} />}
    {activeTab === "documents" && <DocumentInstancesPanel sourceType="ol_policies.policy" objectId={policy.id} documentType="POLICY_CONTRACT" title="Policy documents" description="Generated policy contracts, schedules, and premium statements are retained against this policy with their template versions." renderLabel="Generate policy contract PDF" />}
    {activeTab === "audit" && <section className="surface-card p-4"><h2 className="text-sm font-bold">Audit trail</h2><div className="mt-4"><AuditTimeline entries={policy.auditLogs} /></div></section>}
  </MasterDetailPage><PolicyEndorsementModal open={endorsementModalOpen} policy={policy} onClose={() => setEndorsementModalOpen(false)} /><PolicyTerminalActions policy={policy} surrenderOpen={surrenderModalOpen} paidUpOpen={paidUpModalOpen} cancelOpen={cancelModalOpen} onSurrenderChange={setSurrenderModalOpen} onPaidUpChange={setPaidUpModalOpen} onCancelChange={setCancelModalOpen} /><PolicyPrintPreviewModal open={policyPrintModalOpen} policy={policy} onClose={() => setPolicyPrintModalOpen(false)} /></>
}

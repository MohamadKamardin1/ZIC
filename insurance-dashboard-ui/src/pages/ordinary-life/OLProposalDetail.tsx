/**
 * OL Proposal Detail — master-detail shell.
 *
 * Left: header, action bar, and Overview / Quotation Source / History tabs.
 * Right: the payment-readiness panel stays visible at all times so operators
 * can resolve checklist items while working any tab. Failures render through
 * ErrorCoach; payloads carry names — never UUIDs.
 */

import { useMemo, useState, useCallback } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  ArrowLeft,
  BadgeCheck,
  CheckCircle2,
  CircleSlash,
  Clock3,
  FileText,
  Landmark,
  Minus,
  Printer,
  ScrollText,
  ShieldCheck,
  XCircle,
} from "lucide-react"
import { ErrorCoach } from "../../components/commitments/ErrorCoach"
import { InfoBanner } from "../../components/ui/Overlays"
import ExpiryWarning from "../../components/proposals/ExpiryWarning"
import FirstPremiumCard from "../../components/proposals/FirstPremiumCard"
import ProposalStatusBadge, { proposalStatusLabel } from "../../components/proposals/ProposalStatusBadge"
import ReadinessChecklist from "../../components/proposals/ReadinessChecklist"
import {
  convertToPolicy,
  getQuotationVersionSnapshot,
  markPaymentReady,
  type ProposalDetail,
} from "../../lib/proposals"
import { proposalDetailKey, useProposalDetail, useProposalHistory } from "../../lib/proposalsHooks"
import { useAccess } from "../../lib/access"
import { dateLabel, formatMoney } from "../../lib/commitmentsDisplay"
import { useToast } from "../../components/ui/Toast"
import OLEnrichmentModal from "./OLEnrichmentModal"
import { OLBeneficiariesPanel } from "./OLBeneficiaries"
import { OLProposalDocuments } from "./OLProposalDocuments"
import { OLHealth } from "./OLHealth"

type TabId = "overview" | "beneficiaries" | "health" | "documents" | "source" | "history"

const TABS: Array<{ id: TabId; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "beneficiaries", label: "Beneficiaries" },
  { id: "health", label: "Health & Underwriting" },
  { id: "documents", label: "Documents" },
  { id: "source", label: "Quotation Source" },
  { id: "history", label: "History" },
]

const EVENT_ICONS: Record<string, typeof CheckCircle2> = {
  ProposalCreated: FileText,
  ProposalEnriched: BadgeCheck,
  ProposalPaymentReady: ShieldCheck,
  ProposalConverted: BadgeCheck,
  ProposalCancelled: XCircle,
  ProposalExpired: Clock3,
}

function Tick({ on, testId }: { on: boolean | null | undefined; testId: string }) {
  return on ? (
    <CheckCircle2 size={16} aria-label="Yes" data-testid={testId} className="text-[var(--success)]" />
  ) : (
    <Minus size={16} aria-label="No" data-testid={`${testId}-off`} className="text-[var(--muted-foreground)]" />
  )
}

function triLabel(value: boolean | null | undefined): string {
  if (value === true) return "Yes"
  if (value === false) return "No"
  return "Not declared"
}

function DefinitionList({ entries }: { entries: Array<[string, React.ReactNode]> }) {
  return (
    <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
      {entries.map(([label, value]) => (
        <div key={label}>
          <dt className="text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">{label}</dt>
          <dd className="mt-0.5 text-sm font-semibold text-[var(--foreground)]">{value === undefined || value === null || value === "" ? "—" : value}</dd>
        </div>
      ))}
    </dl>
  )
}

/** Read-only generic renderer for a quotation version snapshot blob. */
function SnapshotViewer({ snapshot }: { snapshot: Record<string, unknown> }) {
  const scalars = Object.entries(snapshot).filter(
    ([, value]) => ["string", "number", "boolean"].includes(typeof value) && value !== null && value !== "",
  )
  const collections = Object.entries(snapshot).filter(([, value]) => Array.isArray(value))
  const financial = snapshot.financial_summary as Record<string, unknown> | null | undefined

  return (
    <div data-testid="quotation-snapshot-panel" className="space-y-3">
      {financial && typeof financial === "object" && (
        <div className="rounded-md border bg-[var(--muted)]/30 p-2">
          <p className="mb-1 text-[11px] font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">Financial summary</p>
          <DefinitionList
            entries={Object.entries(financial)
              .filter(([, value]) => ["string", "number"].includes(typeof value))
              .slice(0, 8)
              .map(([key, value]) => [key.replace(/_/g, " "), String(value)])}
          />
        </div>
      )}
      <DefinitionList
        entries={scalars
          .filter(([key]) => !/^id$|_id$|^quotation$/.test(key))
          .slice(0, 12)
          .map(([key, value]) => [key.replace(/_/g, " "), String(value)])}
      />
      {collections.length > 0 && (
        <ul className="flex flex-wrap gap-2">
          {collections.map(([key, value]) => (
            <li key={key} className="rounded-full border border-[var(--border)] px-2.5 py-1 text-xs font-semibold">
              {key.replace(/_/g, " ")}: {(value as unknown[]).length}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default function OLProposalDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const access = useAccess()
  const [activeTab, setActiveTab] = useState<TabId>("overview")
  const [snapshotVersion, setSnapshotVersion] = useState<number | null>(null)
  const [actionError, setActionError] = useState<unknown>(null)
  const [enrichOpen, setEnrichOpen] = useState(false)

  const detailQuery = useProposalDetail(id)
  const detail = detailQuery.data ?? null
  const historyQuery = useProposalHistory(id, activeTab === "history")

  const carriedVersion = detail?.quotationVersion ?? detail?.quotationVersions[0]?.versionNumber ?? null
  const selectedSnapshotVersion = snapshotVersion ?? carriedVersion
  const isPriorVersion = selectedSnapshotVersion != null && carriedVersion != null && selectedSnapshotVersion !== carriedVersion

  const snapshotQuery = useQuery({
    queryKey: ["proposals", "quotation-snapshot", detail?.quotationId ?? "none", selectedSnapshotVersion],
    queryFn: () => getQuotationVersionSnapshot(String(detail!.quotationId), Number(selectedSnapshotVersion)),
    enabled: Boolean(detail?.quotationId) && selectedSnapshotVersion != null,
  })

  const markReady = useMutation({
    mutationFn: () => markPaymentReady(String(id)),
    onSuccess: () => {
      setActionError(null)
      toast({ title: "Payment readiness confirmed", message: "The first premium commitment was generated.", tone: "success" })
      void queryClient.invalidateQueries({ queryKey: proposalDetailKey(id) })
    },
    onError: (error) => setActionError(error),
  })

  const convert = useMutation({
    mutationFn: () => convertToPolicy(String(id)),
    onSuccess: (payload) => {
      setActionError(null)
      const record = (payload as { policy?: { id?: string }; id?: string }).policy ?? (payload as Record<string, unknown>)
      const policyId = String(record.id ?? "")
      toast({ title: "Proposal converted", message: "The policy was issued from this proposal.", tone: "success" })
      void queryClient.invalidateQueries({ queryKey: proposalDetailKey(id) })
      if (policyId) navigate(`/ordinary-life/policies?policy_number=${encodeURIComponent(policyId)}`)
    },
    onError: (error) => setActionError(error),
  })

  const totals = useMemo(() => {
    if (!detail) return { totalPremium: null as number | null }
    const premiums = detail.planConfigs.filter((plan) => plan.isSelected)
    const total = premiums.reduce((sum, plan) => sum + (plan.premiumAmount ?? 0), 0)
    return { totalPremium: total > 0 ? total : null }
  }, [detail])

  const permissionKeys = useMemo(
    () => access.access.permissions.map((permission) => `${permission.module}.${permission.action}`.toLowerCase()),
    [access.access.permissions],
  )
  const hasPermission = useCallback(
    (code: string) => {
      if (access.isSuperAdmin) return true
      if (access.access.permissions.length === 0) return code.endsWith(".view") ? access.canAccess("ol_proposals") : false
      return permissionKeys.includes(code.toLowerCase())
    },
    [access.access.permissions.length, access.canAccess, access.isSuperAdmin, permissionKeys],
  )

  const canAct = (action: string): boolean => {
    if (!detail) return false
    const allowed = detail.allowedActions.length > 0 ? detail.allowedActions.includes(action as never) : true
    const permissionMap: Record<string, string> = {
      enrich: "ol_proposals.enrich",
      upload_documents: "ol_proposals.upload_documents",
      mark_payment_ready: "ol_proposals.mark_payment_ready",
      convert: "ol_proposals.convert",
      cancel: "ol_proposals.cancel",
      print: "ol_proposals.print",
    }
    const permission = permissionMap[action]
    return allowed && (!permission || hasPermission(permission))
  }

  if (detailQuery.isLoading) {
    return (
      <div className="space-y-4 p-4 md:p-6" aria-busy="true">
        <div className="surface-card h-28 animate-pulse" />
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
          <div className="surface-card h-96 animate-pulse" />
          <div className="surface-card h-96 animate-pulse" />
        </div>
      </div>
    )
  }

  if (detailQuery.isError || !detail) {
    return (
      <div className="p-4 md:p-6">
        <ErrorCoach
          error={detailQuery.error ?? new Error("The proposal could not be loaded.")}
          title="Proposal detail could not be loaded"
          onRetry={() => void detailQuery.refetch()}
        />
      </div>
    )
  }

  const showReason = Boolean(detail.reasonCode || detail.reasonText)

  return (
    <div className="space-y-5 p-4 md:p-6">
      <nav aria-label="Breadcrumb" className="text-sm">
        <Link to="/ordinary-life/proposals" className="inline-flex items-center gap-1.5 font-semibold text-[var(--muted-foreground)] transition hover:text-[var(--foreground)]">
          <ArrowLeft size={15} aria-hidden="true" />
          Proposals register
        </Link>
      </nav>

      {/* Header */}
      <header className="section-header flex flex-wrap items-start justify-between gap-4" data-testid="proposal-detail-header">
        <div className="min-w-0 space-y-2">
          <h1 className="truncate text-xl font-extrabold tracking-tight">{detail.proposalNumber}</h1>
          <p className="text-sm font-semibold text-white/85">{detail.partnerName}</p>
          <p className="text-xs font-semibold uppercase tracking-[0.08em] text-white/70">
            {[detail.productName, detail.planName].filter(Boolean).join(" · ") || "—"}
            {detail.quotationNumber ? ` · from ${detail.quotationNumber}` : ""}
          </p>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-2 pt-1 text-white">
            <ProposalStatusBadge status={detail.status} />
            <span className="rounded-full border border-white/30 px-2 py-0.5 text-xs font-bold">{detail.currency || "TZS"}</span>
            <ExpiryWarning expiryDate={detail.expiryDate} />
            <span className="flex items-center gap-1 text-xs font-bold" data-testid="header-payment-ready">
              Payment ready <Tick on={detail.paymentReady} testId="tick-payment-ready" />
            </span>
            <span className="flex items-center gap-1 text-xs font-bold" data-testid="header-first-premium">
              First premium <Tick on={detail.firstPremium?.posted} testId="tick-first-premium" />
            </span>
          </div>
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs font-semibold text-white/75">
            <span>Agent: {detail.agentName || "—"}</span>
            {detail.employerName && detail.employerName !== "-" && <span>Employer: {detail.employerName}</span>}
          </div>
        </div>

        {/* Action bar */}
        <div role="toolbar" aria-label="Proposal actions" className="flex flex-wrap items-center justify-end gap-2" data-testid="proposal-action-bar">
          {canAct("enrich") && (
            <button type="button" className="button-secondary" onClick={() => setEnrichOpen(true)} data-testid="open-enrichment">
              Enrich
            </button>
          )}
          {canAct("upload_documents") && (
            <button type="button" className="button-secondary" onClick={() => setActiveTab("documents")}>
              Documents
            </button>
          )}
          {canAct("mark_payment_ready") && (
            <button type="button" className="button-secondary" onClick={() => markReady.mutate()} disabled={markReady.isPending}>
              Mark Payment Ready
            </button>
          )}
          {canAct("convert") && (
            <button type="button" className="button-primary" onClick={() => convert.mutate()} disabled={convert.isPending}>
              Convert to Policy
            </button>
          )}
          {canAct("cancel") && (
            <button type="button" className="button-secondary" disabled title="Cancellation moves with the lifecycle actions release">
              Cancel
            </button>
          )}
          {canAct("print") && (
            <button type="button" className="button-secondary" disabled title="Printing arrives with the documents release">
              <Printer size={15} aria-hidden="true" />
              Print
            </button>
          )}
        </div>
      </header>

      {showReason && (
        <InfoBanner title={`Reason · ${proposalStatusLabel(detail.status)}`}>
          <p className="text-sm font-semibold">
            {detail.reasonCode ? `${detail.reasonCode} — ` : ""}
            {detail.reasonText}
          </p>
        </InfoBanner>
      )}

      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
        {/* Master column */}
        <div className="space-y-4">
          <nav className="ol-detail-tabs surface-card flex gap-1 overflow-x-auto p-1" aria-label="Proposal detail tabs" data-testid="proposal-tabs">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                aria-current={activeTab === tab.id ? "page" : undefined}
                className={`whitespace-nowrap rounded-[8px] px-4 py-2.5 text-sm font-semibold transition ${
                  activeTab === tab.id
                    ? "bg-white text-[var(--foreground)] shadow-sm dark:bg-[var(--muted)]"
                    : "text-[var(--muted-foreground)] hover:bg-[var(--secondary)]"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>

          {activeTab === "overview" && (
            <div className="space-y-4" data-testid="tab-overview">
              <section className="surface-card p-4">
                <h2 className="mb-3 font-bold">Personal details</h2>
                <DefinitionList
                  entries={[
                    ["Policyholder", detail.partnerName],
                    ["Agent", detail.agentName],
                    ["Employer", detail.employerName],
                    ["Employment reference", detail.employmentReference],
                    ["Payroll deduction", triLabel(detail.payrollDeduction)],
                    ["Intermediary channel", detail.intermediaryChannel],
                    ["Occupation risk note", detail.occupationRiskNote],
                    ["Existing policies", detail.existingPoliciesCount ?? undefined],
                    ["Source channel", detail.sourceChannel],
                    ["Created", dateLabel(detail.createdAt)],
                  ]}
                />
              </section>

              <section className="surface-card p-4">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <h2 className="font-bold">Financial summary</h2>
                  <span className="text-sm font-bold tabular-nums">
                    Total premium {formatMoney(totals.totalPremium, detail.currency)}
                  </span>
                </div>
                {detail.installmentConfigs.length > 0 ? (
                  <table className="w-full text-left text-sm" data-testid="installments-table">
                    <thead>
                      <tr className="border-b text-xs font-bold uppercase tracking-wide text-[var(--muted-foreground)]">
                        <th className="py-2 pr-3">Frequency</th>
                        <th className="py-2 pr-3">Installments</th>
                        <th className="py-2 pr-3">Amount</th>
                        <th className="py-2">First due</th>
                      </tr>
                    </thead>
                    <tbody>
                      {detail.installmentConfigs.map((row) => (
                        <tr key={row.frequency ?? row.id} className="border-b last:border-0">
                          <td className="py-2 pr-3 font-semibold capitalize">{row.frequency}</td>
                          <td className="py-2 pr-3 tabular-nums">{row.numberOfInstallments ?? "—"}</td>
                          <td className="py-2 pr-3 tabular-nums">{formatMoney(row.installmentAmount, row.currency ?? detail.currency)}</td>
                          <td className="py-2">{dateLabel(row.firstDueDate)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <p className="text-sm text-[var(--muted-foreground)]">No installment schedule was carried onto this proposal.</p>
                )}
              </section>

              <section className="surface-card p-4" data-testid="declarations-summary">
                <h2 className="mb-3 font-bold">Declarations summary</h2>
                <DefinitionList
                  entries={[
                    ["PEP declaration", triLabel(detail.declarationPep)],
                    ["AML declaration", triLabel(detail.declarationAml)],
                    ["Free-text note", detail.declarationsFreeText],
                  ]}
                />
              </section>

              <section className="surface-card p-4">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <h2 className="flex items-center gap-2 font-bold">
                    <ScrollText size={16} aria-hidden="true" />
                    Quotation reference
                  </h2>
                  {detail.quotationNumber && (
                    <Link to={`/ordinary-life/quotations/${detail.quotationId ?? ""}`} className="text-sm font-bold underline-offset-2 hover:underline">
                      {detail.quotationNumber}
                    </Link>
                  )}
                </div>
                {detail.quotationVersions.length > 0 && (
                  <label className="mb-3 flex w-full max-w-xs flex-col gap-1 text-sm">
                    <span className="font-semibold">Snapshot version</span>
                    <select
                      data-testid="snapshot-version-select"
                      value={String(selectedSnapshotVersion ?? "")}
                      onChange={(event) => setSnapshotVersion(Number(event.target.value))}
                      className="h-10 rounded-[10px] border bg-[var(--card)] px-3 text-sm outline-none focus:border-[var(--ring)]"
                    >
                      {[...detail.quotationVersions]
                        .sort((a, b) => b.versionNumber - a.versionNumber)
                        .map((row) => (
                          <option key={row.versionNumber} value={String(row.versionNumber)}>
                            Version {row.versionNumber}
                            {row.versionNumber === carriedVersion ? " (carried)" : ""}
                          </option>
                        ))}
                    </select>
                  </label>
                )}
                {!isPriorVersion ? (
                  <p className="text-sm text-[var(--muted-foreground)]" data-testid="carried-version-note">
                    This proposal carries version {carriedVersion ?? "—"} of the source quotation. Choose an earlier version to
                    inspect its read-only snapshot.
                  </p>
                ) : snapshotQuery.isLoading ? (
                  <p className="text-sm text-[var(--muted-foreground)]">Loading version snapshot…</p>
                ) : snapshotQuery.isError ? (
                  <ErrorCoach error={snapshotQuery.error} title="The version snapshot could not be loaded" compact />
                ) : snapshotQuery.data ? (
                  <div className="space-y-2">
                    <p className="text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">
                      Version {snapshotQuery.data.versionNumber} · {dateLabel(snapshotQuery.data.createdAt)}
                    </p>
                    {snapshotQuery.data.changeReason && (
                      <p className="text-sm font-semibold" data-testid="snapshot-change-reason">
                        Change reason: {snapshotQuery.data.changeReason}
                      </p>
                    )}
                    <SnapshotViewer snapshot={snapshotQuery.data.snapshot} />
                    <InfoBanner title="Read-only snapshot">
                      <p className="text-xs">Historic view — this proposal continues to carry version {carriedVersion}.</p>
                    </InfoBanner>
                  </div>
                ) : null}
              </section>
            </div>
          )}

          {activeTab === "beneficiaries" && <OLBeneficiariesPanel detail={detail} canEnrich={canAct("enrich")} />}

          {activeTab === "health" && <OLHealth detail={detail} canEnrich={canAct("enrich")} onActionError={setActionError} />}

          {activeTab === "documents" && <OLProposalDocuments detail={detail} onActionError={setActionError} />}

          {activeTab === "source" && (
            <div className="space-y-4" data-testid="tab-source">
              <section className="surface-card p-4">
                <h2 className="mb-3 font-bold">Plans</h2>
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b text-xs font-bold uppercase tracking-wide text-[var(--muted-foreground)]">
                      <th className="py-2 pr-3">Plan</th>
                      <th className="py-2 pr-3">Term</th>
                      <th className="py-2 pr-3">Sum assured</th>
                      <th className="py-2">Premium</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detail.planConfigs.map((plan) => (
                      <tr key={plan.id} className="border-b last:border-0">
                        <td className="py-2 pr-3 font-semibold">
                          {plan.planName}
                          {plan.isSelected ? <span className="ml-2 rounded-full bg-[var(--secondary)] px-1.5 py-0.5 text-[10px] font-bold">Selected</span> : null}
                        </td>
                        <td className="py-2 pr-3 tabular-nums">{plan.termYears ?? "—"} yrs</td>
                        <td className="py-2 pr-3 tabular-nums">{formatMoney(plan.baseSumAssured, detail.currency)}</td>
                        <td className="py-2 tabular-nums">{formatMoney(plan.premiumAmount, detail.currency)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>

              <section className="surface-card p-4">
                <h2 className="mb-3 font-bold">Members</h2>
                <ul className="divide-y">
                  {detail.members.map((member) => (
                    <li key={member.fullName + member.identityNumber} className="py-2">
                      <p className="text-sm font-semibold">
                        {member.fullName}
                        {member.relationship ? ` · ${member.relationship}` : ""}
                      </p>
                      <p className="text-xs text-[var(--muted-foreground)]">
                        {[`Age ${member.ageAtQuote ?? "—"}`, member.gender, member.smokerStatus, member.coverageBasis]
                          .filter(Boolean)
                          .join(" · ")}
                      </p>
                    </li>
                  ))}
                </ul>
              </section>

              <section className="surface-card p-4">
                <h2 className="mb-3 font-bold">Funds</h2>
                {detail.fundAllocations.length === 0 ? (
                  <p className="text-sm text-[var(--muted-foreground)]">No fund allocations were carried.</p>
                ) : (
                  <ul className="divide-y">
                    {detail.fundAllocations.map((fund) => (
                      <li key={fund.fundName + fund.allocationPercentage} className="flex items-center justify-between py-2 text-sm">
                        <span className="font-semibold">{fund.fundName}</span>
                        <span className="font-bold tabular-nums">{fund.allocationPercentage}%</span>
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              <section className="surface-card p-4">
                <h2 className="mb-3 font-bold">Riders</h2>
                {detail.riders.length === 0 ? (
                  <p className="text-sm text-[var(--muted-foreground)]">No riders were carried.</p>
                ) : (
                  <ul className="divide-y">
                    {detail.riders.map((rider) => (
                      <li key={rider.riderName + rider.premiumAmount} className="flex items-center justify-between py-2 text-sm">
                        <span className="font-semibold">{rider.riderName}</span>
                        <span className="font-bold tabular-nums">{formatMoney(rider.premiumAmount, detail.currency)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              <section className="surface-card p-4">
                <h2 className="mb-3 font-bold">Benefits</h2>
                {detail.benefits.length === 0 ? (
                  <p className="text-sm text-[var(--muted-foreground)]">No benefits were carried.</p>
                ) : (
                  <ul className="divide-y">
                    {detail.benefits.map((benefit) => (
                      <li key={benefit.name + benefit.code} className="flex items-center justify-between py-2 text-sm">
                        <span className="font-semibold">
                          {benefit.name}
                          {benefit.code ? ` (${benefit.code})` : ""}
                        </span>
                        <span className="font-bold tabular-nums">{formatMoney(benefit.sumAssured ?? benefit.value, detail.currency)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              <section className="surface-card p-4">
                <h2 className="mb-3 flex items-center gap-2 font-bold">
                  <Landmark size={16} aria-hidden="true" />
                  Bank details
                </h2>
                <DefinitionList
                  entries={[
                    ["Bank", detail.bankName],
                    ["Account name", detail.bankAccountName],
                    ["Account number", detail.bankAccountNumberMasked],
                  ]}
                />
              </section>
            </div>
          )}

          {activeTab === "history" && (
            <div className="space-y-4" data-testid="tab-history">
              {historyQuery.isLoading && <div className="surface-card h-40 animate-pulse" />}
              {historyQuery.isError && (
                <ErrorCoach error={historyQuery.error} title="The status timeline could not be loaded" onRetry={() => void historyQuery.refetch()} />
              )}
              {historyQuery.data && historyQuery.data.length === 0 && (
                <div className="surface-card p-4 text-sm text-[var(--muted-foreground)]">No recorded events for this proposal yet.</div>
              )}
              {historyQuery.data && historyQuery.data.length > 0 && (
                <ol className="surface-card space-y-0 p-4" data-testid="history-timeline">
                  {historyQuery.data.map((event, index) => {
                    const EventIcon = EVENT_ICONS[event.eventType] ?? CircleSlash
                    return (
                      <li key={event.id} className="relative flex gap-3 pb-5 last:pb-0" data-history-event={event.eventType}>
                        {index < historyQuery.data.length - 1 && <span aria-hidden="true" className="absolute left-[11px] top-7 h-full w-px bg-[var(--border)]" />}
                        <EventIcon size={24} aria-hidden="true" className="z-10 mt-0.5 flex-none rounded-full bg-[var(--card)] p-0.5 text-[var(--primary)]" />
                        <div className="min-w-0">
                          <p className="text-sm font-bold">{event.eventTypeLabel}</p>
                          <p className="text-xs text-[var(--muted-foreground)]">
                            {dateLabel(event.occurredAt)} · {event.actor || "System"}
                          </p>
                          {(event.fromStatus || event.toStatus) && (
                            <p className="mt-0.5 text-xs font-semibold">
                              {proposalStatusLabel(event.fromStatus) || "—"} → {proposalStatusLabel(event.toStatus) || "—"}
                            </p>
                          )}
                          {event.reason && <p className="mt-0.5 text-xs italic text-[var(--muted-foreground)]">“{event.reason}”</p>}
                          {event.sourceChannel && (
                            <p className="text-[11px] font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">
                              via {event.sourceChannel}
                            </p>
                          )}
                        </div>
                      </li>
                    )
                  })}
                </ol>
              )}
            </div>
          )}
        </div>

        {/* Detail column — always visible readiness panel */}
        <aside className="space-y-4 lg:sticky lg:top-6" data-testid="readiness-panel">
          <section className="surface-card p-4">
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <h2 className="font-bold">Payment readiness</h2>
              {detail.readiness && (
                <span
                  className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${
                    detail.readiness.passed ? "bg-[var(--success)]/15 text-[var(--success)]" : "bg-[var(--destructive)]/15 text-[var(--destructive)]"
                  }`}
                  data-testid="readiness-verdict"
                >
                  {detail.readiness.passed ? "All checks passed" : `${detail.readiness.items.filter((item) => !item.passed).length} to resolve`}
                </span>
              )}
            </div>
            {detail.completeness && !detail.completeness.complete && (
              <p className="mb-2 text-xs text-[var(--muted-foreground)]" data-testid="completeness-line">
                Missing sections:{" "}
                <span className="font-bold capitalize">{detail.completeness.requiredMissing.join(", ") || detail.completeness.missing.join(", ")}</span>
              </p>
            )}
            <ReadinessChecklist items={detail.readiness?.items ?? []} proposalId={detail.id} />
            {canAct("mark_payment_ready") && (
              <button
                type="button"
                className="button-primary mt-3 w-full justify-center"
                data-testid="panel-mark-payment-ready"
                disabled={markReady.isPending}
                onClick={() => markReady.mutate()}
              >
                {markReady.isPending ? "Evaluating…" : "Mark Payment Ready"}
              </button>
            )}
            {Boolean(actionError) && (
              <div className="mt-3">
                <ErrorCoach error={actionError} title="The action could not be completed" compact onRetry={() => setActionError(null)} />
              </div>
            )}
          </section>

          <FirstPremiumCard status={detail.firstPremium} />
        </aside>
      </div>

      <OLEnrichmentModal open={enrichOpen} onClose={() => setEnrichOpen(false)} detail={detail} />
    </div>
  )
}

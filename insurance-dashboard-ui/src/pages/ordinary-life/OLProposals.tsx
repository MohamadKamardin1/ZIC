import { useCallback, useMemo, useRef, useState } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { keepPreviousData, useQuery, useQueryClient } from "@tanstack/react-query"
import { CheckCircle2, Download, FilePlus2, Minus, Search, ShieldAlert, ShieldCheck } from "lucide-react"
import { useAccess } from "../../lib/access"
import type { TableQuery } from "../../lib/apiClient"
import { DataTable, normalizeTableResponse, type TableFetcher } from "../../components/ui/DataTable"
import { FilterBar, type FilterValues } from "../../components/ui/FilterBar"
import { InfoBanner, Modal } from "../../components/ui/Overlays"
import { MasterDetailPage } from "../../components/ui/Patterns"
import { useToast } from "../../components/ui/Toast"
import { ErrorCoach } from "../../components/commitments/ErrorCoach"
import { ProposalStatusBadge } from "../../components/proposals/ProposalStatusBadge"
import { ExpiryWarning } from "../../components/proposals/ExpiryWarning"
import { dateLabel, formatMoney } from "../../lib/commitmentsDisplay"
import { useProposalKPIs, useProposalOptions } from "../../lib/proposalsHooks"
import {
  createProposalFromQuotation,
  exportProposalsCsv,
  listFinalizedQuotations,
  listProposals,
  listQuotationVersions,
  normalizeProposalListItem,
  printProposal,
  type QuotationOption,
  type ProposalListItem,
  type ProposalListParams,
  type RegisterKPIs,
} from "../../lib/proposals"
import type { FilterDefinition, RowAction, TableColumn } from "../../components/ui/types"

type ProposalListRow = ProposalListItem & Record<string, unknown>
type PresetKey = "pending_underwriting" | "payment_ready" | "awaiting_first_premium" | "converted_period" | "expiring_7_days"

const DEFAULT_PROPOSAL_STATUSES = [
  "DRAFT",
  "ENRICHMENT",
  "PENDING_UNDERWRITING",
  "PAYMENT_READY",
  "AWAITING_FIRST_PREMIUM",
  "CONVERTED",
  "CANCELLED",
  "EXPIRED",
]

function statusLabel(code: string): string {
  return code
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ")
}

function isoDate(offsetDays = 0): string {
  const value = new Date()
  value.setDate(value.getDate() + offsetDays)
  const month = String(value.getMonth() + 1).padStart(2, "0")
  const day = String(value.getDate()).padStart(2, "0")
  return `${value.getFullYear()}-${month}-${day}`
}

const PRESET_FILTERS: Record<PresetKey, FilterValues> = {
  pending_underwriting: { status: "PENDING_UNDERWRITING" },
  payment_ready: { payment_ready: "true" },
  awaiting_first_premium: { status: "AWAITING_FIRST_PREMIUM" },
  converted_period: { status: "CONVERTED" },
  expiring_7_days: { expiry_window: { from: isoDate(), to: isoDate(7) } },
}

const CHIPS: Array<{ key: PresetKey; label: string }> = [
  { key: "awaiting_first_premium", label: "Awaiting First Premium" },
  { key: "expiring_7_days", label: "Expiring 7 Days" },
  { key: "pending_underwriting", label: "Pending Underwriting" },
]

const ACTION_PERMISSION: Record<string, string> = {
  view: "ol_proposals.view",
  enrich: "ol_proposals.enrich",
  mark_payment_ready: "ol_proposals.mark_payment_ready",
  convert: "ol_proposals.convert",
  cancel: "ol_proposals.cancel",
  print: "ol_proposals.print",
}

/** Row actions follow backend allowed_actions first, then IAM permissions. */
export function proposalRowActionEnabled(
  key: string,
  row: Pick<ProposalListRow, "allowedActions">,
  isSuperAdmin: boolean,
  hasPermission: (code: string) => boolean,
): boolean {
  const has = (code: string) => isSuperAdmin || hasPermission(code)
  if (!has(ACTION_PERMISSION[key] ?? "ol_proposals.view")) return false
  if (key === "view") return true
  const allowed = (row.allowedActions ?? []).map((action) => String(action).toLowerCase())
  const backendDecides = allowed.length > 0
  return backendDecides ? allowed.includes(key.toLowerCase()) : true
}

function optString(value: unknown): string | undefined {
  if (typeof value === "string" && value.trim()) return value
  return undefined
}

function boolParam(value: unknown): boolean | undefined {
  if (value === "true") return true
  if (value === "false") return false
  return undefined
}

function rangeOf(value: unknown): { from?: string; to?: string } {
  if (value && typeof value === "object" && !Array.isArray(value)) return value as { from?: string; to?: string }
  if (typeof value === "string") {
    const [from, to] = value.split(",")
    return { from: from || undefined, to: to || undefined }
  }
  return {}
}

const ORDERING_MAP: Record<string, string> = {
  proposalNumber: "proposal_number",
  createdAt: "created_at",
  expiryDate: "expiry_date",
  status: "status",
}

function toBackendOrdering(value?: string): string | undefined {
  if (!value) return undefined
  const negative = value.startsWith("-") ? "-" : ""
  const key = value.replace(/^-/, "")
  return `${negative}${ORDERING_MAP[key] ?? key}`
}

function mapFilters(query: TableQuery): ProposalListParams {
  const filters = query.filters ?? {}
  const expiry = rangeOf(filters.expiry_window)
  return {
    status: optString(filters.status),
    product: optString(filters.product),
    agent: optString(filters.agent),
    hasEmployer: boolParam(filters.has_employer),
    expiryFrom: expiry.from,
    expiryTo: expiry.to,
    paymentReady: boolParam(filters.payment_ready),
    firstPremiumPosted: boolParam(filters.first_premium_posted),
    search: typeof query.search === "string" && query.search ? query.search : optString(filters.search),
    ordering: toBackendOrdering(query.ordering),
    page: query.page,
    pageSize: query.pageSize,
  }
}

function Tick({ on, label, testId }: { on: boolean; label: string; testId: string }) {
  return (
    <span
      data-testid={testId}
      role="img"
      aria-label={`${label}: ${on ? "yes" : "no"}`}
      className={`inline-flex ${on ? "text-[var(--success)]" : "text-[var(--muted-foreground)]"}`}
    >
      {on ? <CheckCircle2 size={16} aria-hidden="true" /> : <Minus size={14} aria-hidden="true" />}
    </span>
  )
}

interface KpiCardConfig {
  key: string
  label: string
  pick: (kpis: RegisterKPIs) => number
  helper?: (kpis: RegisterKPIs) => string
  preset?: PresetKey
  clear?: boolean
}

const KPI_CARDS: KpiCardConfig[] = [
  { key: "total", label: "Total Proposals", pick: (kpis) => kpis.totalProposals, clear: true },
  { key: "pending_underwriting", label: "Pending Underwriting", pick: (kpis) => kpis.pendingUnderwriting, preset: "pending_underwriting" },
  { key: "payment_ready", label: "Payment Ready", pick: (kpis) => kpis.paymentReady, preset: "payment_ready" },
  {
    key: "awaiting_first_premium",
    label: "Awaiting First Premium",
    pick: (kpis) => kpis.awaitingFirstPremium,
    helper: (kpis) => `${formatMoney(kpis.awaitingFirstPremiumAmount)} outstanding`,
    preset: "awaiting_first_premium",
  },
  { key: "converted_period", label: "Converted in Period", pick: (kpis) => kpis.convertedInPeriod, preset: "converted_period" },
  { key: "expiring_soon", label: "Expiring Soon", pick: (kpis) => kpis.expiringIn7Days, helper: () => "Next 7 days", preset: "expiring_7_days" },
]

function KpiGrid({
  kpis,
  loading,
  activePreset,
  onApplyPreset,
}: {
  kpis?: RegisterKPIs
  loading: boolean
  activePreset: PresetKey | null
  onApplyPreset: (key: PresetKey | null) => void
}) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {KPI_CARDS.map((card) => {
        const value = kpis ? card.pick(kpis).toLocaleString() : "—"
        return (
          <button
            key={card.key}
            type="button"
            data-testid={`kpi-${card.key}`}
            aria-pressed={card.preset ? activePreset === card.preset : undefined}
            onClick={() => onApplyPreset(card.preset ?? null)}
            className={`surface-card p-4 text-left transition hover:border-[var(--ring)] ${
              card.preset && activePreset === card.preset ? "border-[var(--primary)] ring-1 ring-[var(--primary)]" : ""
            }`}
          >
            <p className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">{card.label}</p>
            <p className="mt-2 text-2xl font-extrabold tracking-tight tabular-nums">{value}</p>
            {card.helper && kpis && <p className="mt-1 text-xs text-[var(--muted-foreground)]">{card.helper(kpis)}</p>}
          </button>
        )
      })}
    </div>
  )
}

interface ConvertQuotationModalProps {
  open: boolean
  onClose: () => void
  onCreated: (proposalId: string, proposalNumber: string) => void
}

function VerifiedBadge({ verified, testId }: { verified: boolean; testId?: string }) {
  return (
    <span
      data-testid={testId}
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-bold ${
        verified
          ? "bg-[var(--success)]/12 text-[var(--success)]"
          : "bg-[var(--destructive)]/12 text-[var(--destructive)]"
      }`}
    >
      {verified ? <ShieldCheck size={12} aria-hidden="true" /> : <ShieldAlert size={12} aria-hidden="true" />}
      {verified ? "Verified" : "Unverified"}
    </span>
  )
}

function QuotationPicker({
  options,
  loading,
  selected,
  onSelect,
}: {
  options: QuotationOption[]
  loading: boolean
  selected: QuotationOption | null
  onSelect: (option: QuotationOption) => void
}) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState("")

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase()
    if (!needle) return options
    return options.filter((option) =>
      `${option.quoteNumber} ${option.quoteName} ${option.policyholder}`.toLowerCase().includes(needle),
    )
  }, [options, query])

  return (
    <div className="relative space-y-1">
      <span className="text-sm font-semibold">Finalized quotation</span>
      <button
        type="button"
        data-testid="quotation-picker-trigger"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
        className="flex h-10 w-full items-center justify-between rounded-[10px] border bg-[var(--card)] px-3 text-left text-sm outline-none focus:border-[var(--ring)]"
      >
        <span className={selected ? "text-[var(--foreground)]" : "text-[var(--muted-foreground)]"}>
          {selected ? `${selected.quoteNumber} — ${selected.quoteName || selected.policyholder}` : "Search finalized quotations…"}
        </span>
        <Search size={15} aria-hidden="true" />
      </button>
      {open && (
        <div
          role="listbox"
          aria-label="Finalized quotations"
          className="absolute z-[70] mt-1 w-full overflow-hidden rounded-[10px] border bg-[var(--popover)] p-1 shadow-lg"
        >
          <input
            data-testid="quotation-picker-search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search by number, name, or policyholder…"
            aria-label="Search finalized quotations"
            className="h-9 w-full border-b bg-transparent px-2 text-sm outline-none"
          />
          <div className="max-h-56 overflow-auto py-1">
            {loading && <p className="px-2 py-3 text-center text-xs text-[var(--muted-foreground)]">Loading quotations…</p>}
            {!loading && filtered.length === 0 && (
              <p className="px-2 py-3 text-center text-xs text-[var(--muted-foreground)]">
                No finalized quotations match. Finalize a quotation first.
              </p>
            )}
            {!loading &&
              filtered.map((option) => (
                <button
                  key={option.id}
                  type="button"
                  role="option"
                  aria-selected={selected?.id === option.id}
                  data-testid={`quotation-option-${option.id}`}
                  className={`flex w-full items-start justify-between gap-2 rounded-md px-2 py-2 text-left text-sm transition hover:bg-[var(--secondary)] ${
                    selected?.id === option.id ? "bg-[var(--secondary)]" : ""
                  }`}
                  onClick={() => {
                    onSelect(option)
                    setOpen(false)
                    setQuery("")
                  }}
                >
                  <span className="min-w-0">
                    <span className="block font-semibold">
                      {option.quoteNumber} — {option.quoteName || option.policyholder}
                    </span>
                    <span className="block truncate text-xs text-[var(--muted-foreground)]">
                      {option.policyholder || "—"}
                    </span>
                  </span>
                  <span className="flex shrink-0 items-center gap-1.5">
                    <VerifiedBadge verified={option.partnerVerified} testId={`quotation-badge-${option.id}`} />
                    <span className="rounded-full border border-[var(--border)] px-1.5 py-0.5 text-[11px] font-bold text-[var(--muted-foreground)]">
                      v{option.version}
                    </span>
                  </span>
                </button>
              ))}
          </div>
        </div>
      )}
    </div>
  )
}

interface ConversionErrorState {
  kind: "br01" | "generic"
  error: unknown
  quotationId?: string
}

function ConvertQuotationModal({ open, onClose, onCreated }: ConvertQuotationModalProps) {
  const navigate = useNavigate()
  const [selected, setSelected] = useState<QuotationOption | null>(null)
  const [versionNumber, setVersionNumber] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)
  const [errorState, setErrorState] = useState<ConversionErrorState | null>(null)
  const [duplicate, setDuplicate] = useState<{ id: string; proposalNumber: string } | null>(null)

  const optionsQuery = useQuery({
    queryKey: ["proposals", "conversion-options"],
    queryFn: () => listFinalizedQuotations(),
    enabled: open,
    placeholderData: keepPreviousData,
  })
  const versionsQuery = useQuery({
    queryKey: ["proposals", "conversion-versions", selected?.id ?? "none"],
    queryFn: () => listQuotationVersions(String(selected!.id)),
    enabled: open && Boolean(selected),
  })

  if (!open) return null

  const options = optionsQuery.data ?? []
  const versionsResult = versionsQuery.data
  const versions = versionsResult?.versions ?? []
  const currentVersion = versionsResult?.currentVersionNumber ?? selected?.version ?? null
  const effectiveVersion = versionNumber ?? currentVersion

  const selectQuotation = (option: QuotationOption) => {
    setSelected(option)
    setVersionNumber(null)
    setErrorState(null)
    setDuplicate(null)
  }

  const submit = async () => {
    if (!selected || busy) return
    setBusy(true)
    setErrorState(null)
    setDuplicate(null)
    try {
      const payload = (await createProposalFromQuotation(selected.id, effectiveVersion ?? undefined)) as Record<string, unknown>
      const proposal = (payload.proposal ?? payload) as Record<string, unknown>
      const id = String(proposal.id ?? "")
      const number = String(proposal.proposal_number ?? "")
      if (payload.duplicate === true || payload.already_converted === true) {
        setDuplicate({ id, proposalNumber: number })
        return
      }
      onCreated(id, number)
    } catch (caught) {
      const apiError = caught as { code?: string }
      setErrorState(
        apiError.code === "PROPOSAL_PARTNER_NOT_VERIFIED"
          ? { kind: "br01", error: caught, quotationId: selected.id }
          : { kind: "generic", error: caught },
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open={open}
      title="Create proposal from quotation"
      description="Convert a finalized quotation into a draft proposal."
      onClose={onClose}
      footer={
        <>
          <button type="button" className="button-secondary" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button
            type="button"
            className="button-primary"
            data-testid="convert-quotation-submit"
            disabled={busy || !selected}
            onClick={() => void submit()}
          >
            Create Proposal
          </button>
        </>
      }
    >
      <div className="space-y-4">
        <p data-testid="convert-quotation-helper" className="text-xs leading-5 text-[var(--muted-foreground)]">
          The quotation must be finalized and the prospect verified as a compliant partner (BR-01).
        </p>

        <QuotationPicker options={options} loading={optionsQuery.isLoading} selected={selected} onSelect={selectQuotation} />

        {versions.length > 1 && (
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-semibold">Version</span>
            <select
              data-testid="quotation-version-select"
              value={String(effectiveVersion ?? "")}
              onChange={(event) => setVersionNumber(Number(event.target.value))}
              className="h-10 rounded-[10px] border bg-[var(--card)] px-3 text-sm outline-none focus:border-[var(--ring)]"
            >
              {[...versions]
                .sort((a, b) => b.versionNumber - a.versionNumber)
                .map((row) => (
                  <option key={row.versionNumber} value={String(row.versionNumber)}>
                    Version {row.versionNumber}
                    {row.versionNumber === currentVersion ? " (current)" : ""}
                  </option>
                ))}
            </select>
          </label>
        )}

        {selected && (
          <div data-testid="quotation-summary" className="rounded-[10px] border bg-[var(--muted)]/30 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-bold">{selected.quoteNumber}</p>
              <VerifiedBadge verified={selected.partnerVerified} testId="quotation-summary-badge" />
            </div>
            <dl className="mt-2 grid grid-cols-2 gap-2 text-xs">
              <div>
                <dt className="font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">Policyholder</dt>
                <dd className="mt-0.5 font-semibold">{selected.policyholder || "—"}</dd>
              </div>
              <div>
                <dt className="font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">Plans</dt>
                <dd className="mt-0.5 font-semibold">{selected.plansSummary || "—"}</dd>
              </div>
              <div>
                <dt className="font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">Total premium</dt>
                <dd className="mt-0.5 font-semibold tabular-nums">{formatMoney(selected.totalPremium, selected.currency)}</dd>
              </div>
              <div>
                <dt className="font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">Currency</dt>
                <dd className="mt-0.5 font-semibold">{selected.currency || "—"}</dd>
              </div>
            </dl>
          </div>
        )}

        {duplicate && (
          <InfoBanner title="Already converted">
            <p className="text-sm">
              This quotation already produced proposal{" "}
              <strong>{duplicate.proposalNumber || duplicate.id}</strong>. Converting again is safe — the existing proposal is
              returned unchanged.
            </p>
            <button
              type="button"
              className="button-secondary mt-2"
              data-testid="view-existing-proposal"
              onClick={() => navigateToProposal(duplicate.id)}
            >
              View existing proposal
            </button>
          </InfoBanner>
        )}

        {errorState?.kind === "br01" && (
          <div className="space-y-2">
            <ErrorCoach error={errorState.error} title="Partner not verified (BR-01)" />
            <button
              type="button"
              className="button-secondary"
              data-testid="br01-deep-link"
              onClick={() => navigateToQuotation(errorState.quotationId)}
            >
              Open quotation partner verification
            </button>
          </div>
        )}

        {errorState?.kind === "generic" && (
          <ErrorCoach
            error={errorState.error}
            title="The quotation could not be converted"
            onRetry={() => setErrorState(null)}
          />
        )}
      </div>
    </Modal>
  )

  function navigateToProposal(id: string) {
    navigate(`/ordinary-life/proposals/${id}`)
  }

  function navigateToQuotation(id?: string) {
    if (!id) return
    navigate(`/ordinary-life/quotations/${id}`)
  }
}

export default function OLProposals() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { access, isSuperAdmin, canAccess } = useAccess()

  // Deep links (dashboard cards, notifications) may carry ?preset=<key> so the
  // register opens already filtered; the preset stays shareable in the URL.
  const urlPresetParam = searchParams.get("preset")
  const initialPreset: PresetKey | null =
    urlPresetParam && urlPresetParam in PRESET_FILTERS ? (urlPresetParam as PresetKey) : null

  const [filters, setFilters] = useState<FilterValues>(initialPreset ? { ...PRESET_FILTERS[initialPreset] } : {})
  const [presetKey, setPresetKey] = useState<PresetKey | null>(initialPreset)
  const [refreshKey, setRefreshKey] = useState(0)
  const [listError, setListError] = useState<unknown>(null)
  const [resultCount, setResultCount] = useState<number | null>(null)
  const [convertOpen, setConvertOpen] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [printingId, setPrintingId] = useState<string | null>(null)

  const lastParamsRef = useRef<ProposalListParams>({})

  const statusesQuery = useProposalOptions("statuses")
  const intermediariesQuery = useProposalOptions("intermediaries")
  const kpisQuery = useProposalKPIs()

  const permissionKeys = useMemo(
    () => access.permissions.map((permission) => `${permission.module}.${permission.action}`.toLowerCase()),
    [access.permissions],
  )
  const hasPermission = useCallback(
    (code: string) => {
      if (isSuperAdmin) return true
      if (access.permissions.length === 0) return code.endsWith(".view") ? canAccess("ol_proposals") : false
      return permissionKeys.includes(code.toLowerCase())
    },
    [access.permissions.length, canAccess, isSuperAdmin, permissionKeys],
  )

  const optionRows = useCallback((data: unknown): Record<string, unknown>[] => {
    const record = (data ?? {}) as { results?: unknown }
    return Array.isArray(record.results) ? record.results.map((row) => row as Record<string, unknown>) : []
  }, [])

  const optionStatuses = useMemo(() => {
    const mapped = optionRows(statusesQuery.data)
      .map((row) => ({
        label: optString(row.label) ?? optString(row.id) ?? "",
        value: optString(row.value) ?? optString(row.id) ?? "",
      }))
      .filter((option) => option.value)
    return mapped.length > 0
      ? mapped
      : DEFAULT_PROPOSAL_STATUSES.map((code) => ({ label: statusLabel(code), value: code }))
  }, [optionRows, statusesQuery.data])

  const agentOptions = useMemo(
    () =>
      optionRows(intermediariesQuery.data)
        .map((row) => ({ label: optString(row.label) ?? "—", value: optString(row.id) ?? "" }))
        .filter((option) => option.value),
    [intermediariesQuery.data, optionRows],
  )

  const filterDefinitions = useMemo(
    () =>
      [
        { key: "status", label: "Status", type: "select", options: optionStatuses, placeholder: "Any status" },
        { key: "agent", label: "Agent", type: "select", options: agentOptions, placeholder: "Any agent" },
        {
          key: "has_employer",
          label: "Employer",
          type: "select",
          options: [
            { label: "With employer", value: "true" },
            { label: "Without employer", value: "false" },
          ],
          placeholder: "Any employer presence",
        },
        { key: "expiry_window", label: "Expiry window", type: "date-range" },
        {
          key: "payment_ready",
          label: "Payment ready",
          type: "select",
          options: [
            { label: "Yes", value: "true" },
            { label: "No", value: "false" },
          ],
          placeholder: "Any",
        },
        {
          key: "first_premium_posted",
          label: "First premium posted",
          type: "select",
          options: [
            { label: "Yes", value: "true" },
            { label: "No", value: "false" },
          ],
          placeholder: "Any",
        },
      ] satisfies FilterDefinition[],
    [agentOptions, optionStatuses],
  )

  const fetcher: TableFetcher<ProposalListRow> = useCallback(async (query: TableQuery) => {
    try {
      const params = mapFilters(query)
      lastParamsRef.current = params
      const payload = await listProposals(params)
      const normalized = normalizeTableResponse<Record<string, unknown>>(payload)
      setListError(null)
      setResultCount(normalized.count)
      return {
        ...normalized,
        results: normalized.results.map((row) => normalizeProposalListItem(row) as ProposalListRow),
      }
    } catch (error) {
      setListError(error)
      setResultCount(null)
      return { results: [], count: 0, page: 1, page_size: 0 }
    }
  }, [])

  const columns: TableColumn<ProposalListRow>[] = useMemo(
    () => [
      {
        key: "proposal_number",
        label: "Proposal",
        field: "proposalNumber",
        sortable: true,
        render: (_value, row) => (
          <button
            type="button"
            className="font-semibold text-[var(--foreground)] underline-offset-2 hover:underline"
            onClick={() => navigate(`/ordinary-life/proposals/${row.id}`)}
          >
            {row.proposalNumber || "—"}
          </button>
        ),
      },
      { key: "policyholder", label: "Policyholder", render: (_value, row) => row.partnerName || "—" },
      { key: "agent_name", label: "Agent", render: (_value, row) => row.agentName || "—" },
      {
        key: "employer",
        label: "Employer",
        render: (_value, row) =>
          row.employerName && row.employerName !== "-" ? (
            <span
              data-testid={`employer-badge-${row.id}`}
              className="inline-flex max-w-40 truncate rounded-full border border-[var(--border)] bg-[var(--secondary)] px-2 py-0.5 text-xs font-semibold"
              title={row.employerName}
            >
              {row.employerName}
            </span>
          ) : (
            "—"
          ),
      },
      {
        key: "product_plan",
        label: "Product / Plan",
        render: (_value, row) => {
          if (row.productName && row.planName) return `${row.productName} / ${row.planName}`
          return row.productName || row.planName || "—"
        },
      },
      {
        key: "total_premium",
        label: "Total premium",
        field: "totalPremium",
        align: "right",
        render: (_value, row) => <span className="tabular-nums">{formatMoney(row.totalPremium, row.currency)}</span>,
      },
      { key: "currency", label: "Currency", field: "currency", align: "center" },
      {
        key: "state",
        label: "Status",
        field: "status",
        sortable: true,
        render: (_value, row) => <ProposalStatusBadge status={row.status} />,
      },
      {
        key: "payment_ready_flag",
        label: "Payment ready",
        align: "center",
        render: (_value, row) => <Tick on={Boolean(row.paymentReady)} label="Payment ready" testId={`payment-ready-${row.id}`} />,
      },
      {
        key: "first_premium_flag",
        label: "First premium",
        align: "center",
        render: (_value, row) => (
          <Tick on={Boolean(row.firstPremiumPosted)} label="First premium posted" testId={`first-premium-${row.id}`} />
        ),
      },
      {
        key: "expiry_date",
        label: "Expiry",
        field: "expiryDate",
        sortable: true,
        render: (_value, row) => (
          <div className="flex flex-col items-start gap-1">
            <span>{dateLabel(row.expiryDate)}</span>
            <ExpiryWarning expiryDate={row.expiryDate} />
          </div>
        ),
      },
      {
        key: "created_at",
        label: "Created",
        field: "createdAt",
        sortable: true,
        render: (value) => dateLabel(value as string | null),
      },
    ],
    [navigate],
  )

  const handlePrint = useCallback(
    async (row: ProposalListRow) => {
      if (printingId) return
      setPrintingId(row.id)
      try {
        const result = await printProposal(row.id)
        const link = document.createElement("a")
        link.href = result.blobUrl
        link.download = result.fileName
        link.click()
        URL.revokeObjectURL(result.blobUrl)
        toast({
          title: `Printing ${row.proposalNumber}`,
          message: "The proposal document download has started.",
          tone: "success",
        })
      } catch (error) {
        toast({
          title: `Could not print ${row.proposalNumber}`,
          message: error instanceof Error ? error.message : "Unexpected error.",
          tone: "danger",
        })
      } finally {
        setPrintingId(null)
      }
    },
    [printingId, toast],
  )

  const actions: RowAction<ProposalListRow>[] = useMemo(
    () => [
      { key: "view", label: "View", onSelect: (row) => navigate(`/ordinary-life/proposals/${row.id}`) },
      {
        key: "enrich",
        label: "Enrich",
        onSelect: (row) => navigate(`/ordinary-life/proposals/${row.id}?tab=enrichment`),
      },
      {
        key: "mark_payment_ready",
        label: "Mark Payment Ready",
        onSelect: (row) => navigate(`/ordinary-life/proposals/${row.id}?action=mark-payment-ready`),
      },
      {
        key: "convert",
        label: "Convert to Policy",
        onSelect: (row) => navigate(`/ordinary-life/proposals/${row.id}?action=convert`),
      },
      {
        key: "cancel",
        label: "Cancel",
        tone: "danger",
        onSelect: (row) => navigate(`/ordinary-life/proposals/${row.id}?action=cancel`),
      },
      {
        key: "print",
        label: "Print",
        onSelect: (row) => void handlePrint(row),
      },
    ],
    [handlePrint, navigate],
  )

  const canAction = useCallback(
    (action: RowAction<ProposalListRow>, row: ProposalListRow) =>
      proposalRowActionEnabled(action.key, row, isSuperAdmin, hasPermission),
    [hasPermission, isSuperAdmin],
  )

  const applyPreset = (key: PresetKey | null) => {
    if (!key || presetKey === key) {
      setFilters({})
      setPresetKey(null)
      setSearchParams({}, { replace: true })
      return
    }
    setFilters({ ...PRESET_FILTERS[key] })
    setPresetKey(key)
    setSearchParams({ preset: key }, { replace: true })
  }

  const handleExport = async () => {
    if (exporting) return
    setExporting(true)
    try {
      const result = await exportProposalsCsv({ ...lastParamsRef.current, page: undefined, pageSize: undefined })
      const link = document.createElement("a")
      link.href = result.blobUrl
      link.download = result.fileName
      link.click()
      URL.revokeObjectURL(result.blobUrl)
      toast({ title: "Export ready", message: "The filtered proposals register was downloaded as CSV.", tone: "success" })
    } catch (error) {
      toast({
        title: "Export failed",
        message: error instanceof Error ? error.message : "Unexpected error.",
        tone: "danger",
      })
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="space-y-5 p-4 md:p-6">
      <MasterDetailPage
        eyebrow="Ordinary Life"
        title="Ordinary Life Proposals"
        description="Track proposals from quotation conversion through enrichment, underwriting, and first premium to policy issue. Actions follow the service's allowed-actions and your permissions."
        actions={
          <>
            <button
              type="button"
              className="button-secondary"
              data-testid="export-proposals-csv"
              disabled={exporting}
              onClick={() => void handleExport()}
            >
              <Download size={16} aria-hidden="true" />
              {exporting ? "Exporting…" : "Export CSV"}
            </button>
            <button
              type="button"
              className="button-primary"
              data-testid="convert-quotation-button"
              disabled={!hasPermission("ol_proposals.create")}
              onClick={() => setConvertOpen(true)}
            >
              <FilePlus2 size={16} aria-hidden="true" />
              Convert Quotation
            </button>
          </>
        }
      >
        <div className="space-y-3">
          <KpiGrid kpis={kpisQuery.data} loading={kpisQuery.isLoading} activePreset={presetKey} onApplyPreset={applyPreset} />
          <div className="flex flex-wrap items-end gap-3">
            <ChipsRow presetKey={presetKey} onApplyPreset={applyPreset} />
            <div className="flex min-w-44 flex-col gap-1">
              <label
                htmlFor="filter-product"
                className="text-xs font-bold uppercase tracking-[0.12em] text-[var(--muted-foreground)]"
              >
                Product
              </label>
              <input
                id="filter-product"
                type="text"
                value={typeof filters.product === "string" ? filters.product : ""}
                onChange={(event) => {
                  setFilters((current) => ({ ...current, product: event.target.value }))
                  setPresetKey(null)
                }}
                placeholder="Product code"
                className="h-10 w-full min-w-44 rounded-[10px] border bg-[var(--card)] px-3 text-sm outline-none focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)]"
              />
            </div>
          </div>
          <FilterBar
            definitions={filterDefinitions}
            value={filters}
            onChange={(key, value) => {
              setFilters((current) => ({ ...current, [key]: value }))
              setPresetKey(null)
            }}
            onReset={() => {
              setFilters({})
              setPresetKey(null)
            }}
          />
          {listError ? <ErrorCoach error={listError} onRetry={() => setRefreshKey((value) => value + 1)} title="Proposals could not be loaded" /> : null}
          {resultCount === 0 && !listError && <EmptyRegister />}
          <DataTable<ProposalListRow>
            metadata={{ columns, defaultOrdering: "-createdAt", pageSize: 20, totalLabel: "Proposals" }}
            fetcher={fetcher}
            filters={filters}
            refreshKey={refreshKey}
            actions={actions}
            permissions={[]}
            canAction={canAction}
            exportFileName="ol-proposals-page.csv"
            caption="Ordinary Life proposals register"
          />
        </div>
      </MasterDetailPage>

      <ConvertQuotationModal
        open={convertOpen}
        onClose={() => setConvertOpen(false)}
        onCreated={(id, number) => {
          setConvertOpen(false)
          toast({ title: "Proposal created", message: `Draft proposal ${number || ""} created from the quotation.`.trim(), tone: "success" })
          void queryClient.invalidateQueries({ queryKey: ["proposals"] })
          if (id) navigate(`/ordinary-life/proposals/${id}`)
        }}
      />
    </div>
  )
}

function ChipsRow({ presetKey, onApplyPreset }: { presetKey: PresetKey | null; onApplyPreset: (key: PresetKey | null) => void }) {
  return (
    <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Proposal quick filters">
      {CHIPS.map((chip) => (
        <button
          key={chip.key}
          type="button"
          data-testid={`chip-${chip.key}`}
          onClick={() => onApplyPreset(chip.key)}
          aria-pressed={presetKey === chip.key}
          className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
            presetKey === chip.key
              ? "border-[var(--primary)] bg-[var(--primary)]/10 text-[var(--primary)]"
              : "border-[var(--border)] text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
          }`}
        >
          {chip.label}
        </button>
      ))}
      {presetKey && (
        <button type="button" className="text-xs underline-offset-2 hover:underline" onClick={() => onApplyPreset(null)}>
          Clear chip
        </button>
      )}
    </div>
  )
}

function EmptyRegister() {
  const navigate = useNavigate()
  return (
    <InfoBanner title="No proposals yet">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm">
          Proposals start as approved quotations. Open the quotation register and convert a quotation, or use “Convert Quotation”
          in the header.
        </p>
        <button
          type="button"
          className="button-secondary"
          data-testid="empty-proposals-link"
          onClick={() => navigate("/ordinary-life/quotations")}
        >
          Go to quotations
        </button>
      </div>
    </InfoBanner>
  )
}

import {
  ArrowLeft,
  Check,
  ChevronRight,
  CircleAlert,
  Download,
  Eye,
  FileCheck2,
  FileText,
  History,
  LoaderCircle,
  Pencil,
  RefreshCcw,
  ShieldCheck,
  UserRound,
  X,
} from "lucide-react"
import { useCallback, useEffect, useMemo, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { ApiClientError, request } from "../../lib/apiClient"
import { useAccess } from "../../lib/access"
import { DateInput, FormGrid, SelectInput, TextInput, TextareaInput } from "../../components/ui/FormControls"
import { ConfirmModal, Drawer, InfoBanner, Modal } from "../../components/ui/Overlays"
import { MasterDetailPage } from "../../components/ui/Patterns"
import { StatusBadge, type StatusTone } from "../../components/ui/StatusBadge"
import { useToast } from "../../components/ui/Toast"

const API_PREFIX = "/api/v1/ol-quotations/quotations/"

type DetailTab = "overview" | "plans" | "members" | "installments" | "funds" | "riders" | "financials" | "versions" | "documents"

type RecordValue = Record<string, unknown>

type QuotationDetail = RecordValue & {
  id: string
  quote_number?: string | null
  quote_name?: string | null
  status?: string | null
  currency?: string | null
  quote_date?: string | null
  expiry_date?: string | null
  current_version_number?: number | null
  partner_verified?: boolean
  approval_required?: boolean
  approval_reason?: string | null
  total_premium?: string | number | null
  total_sum_assured?: string | number | null
  identity_type?: string | null
  identity_number?: string | null
  date_of_birth?: string | null
  age_at_quote?: number | null
  gender?: string | null
  smoker_status?: string | null
  location?: string | null
  address?: string | null
  wizard_step_completion?: Record<string, boolean>
  plan_configurations?: RecordValue[]
  members?: RecordValue[]
  installment_configurations?: RecordValue[]
  fund_allocations?: RecordValue[]
  rider_selections?: RecordValue[]
  benefits?: RecordValue[]
  documents?: RecordValue[]
  versions?: RecordValue[]
  financial_summary?: RecordValue | null
}

type VersionRow = {
  id?: string
  version_number?: number
  status?: string
  created_by?: string | null
  created_at?: string
  change_reason?: string | null
}

type PartnerVerification = {
  partner_exists?: boolean
  partner_id?: string | null
  compliant?: boolean
  missing_fields?: string[]
  partner_number?: string | null
  partner_display_name?: string | null
}

type DocumentRow = RecordValue & {
  id?: string
  source_version_number?: number | null
  template_code?: string | null
  template_version?: string | number | null
  document_type?: string | null
  status?: string | null
  generated_at?: string | null
  pdf_url?: string | null
  html_url?: string | null
}

type FinancialDetails = RecordValue & {
  recalculation_required?: boolean
  summary?: RecordValue | null
  projections?: RecordValue[]
  installment_payouts?: RecordValue[]
  plan_breakdowns?: RecordValue[]
  rider_breakdowns?: RecordValue[]
  tax_breakdown?: RecordValue[]
}

type PartnerForm = {
  first_name: string
  surname: string
  other_name: string
  email: string
  mobile_number: string
  gender: string
  date_of_birth: string
  identification_type: string
  identification_number: string
  nationality: string
  occupation: string
}

const tabs: Array<{ id: DetailTab; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "plans", label: "Plans" },
  { id: "members", label: "Members" },
  { id: "installments", label: "Installments" },
  { id: "funds", label: "Funds" },
  { id: "riders", label: "Riders & Benefits" },
  { id: "financials", label: "Financials" },
  { id: "versions", label: "Versions" },
  { id: "documents", label: "Documents" },
]

function asRecord(value: unknown): RecordValue {
  return value && typeof value === "object" && !Array.isArray(value) ? value as RecordValue : {}
}

function listValue(value: unknown): RecordValue[] {
  return Array.isArray(value) ? value.filter((item): item is RecordValue => Boolean(item && typeof item === "object" && !Array.isArray(item))) : []
}

function stringValue(value: unknown, fallback = "—"): string {
  return value === null || value === undefined || value === "" ? fallback : String(value)
}

function numberValue(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function dateLabel(value: unknown): string {
  if (!value) return "—"
  const raw = String(value)
  const parsed = new Date(`${raw.slice(0, 10)}T00:00:00`)
  return Number.isNaN(parsed.getTime()) ? raw : new Intl.DateTimeFormat("en-GB", { dateStyle: "medium" }).format(parsed)
}

function moneyLabel(value: unknown, currency?: unknown): string {
  const numeric = numberValue(value)
  if (numeric === null) return "—"
  const formatted = numeric.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return currency ? `${String(currency)} ${formatted}` : formatted
}

function statusTone(status?: string | null): StatusTone {
  switch (String(status ?? "").toUpperCase()) {
    case "FINALIZED": return "success"
    case "CONVERTED": return "info"
    case "EXPIRED": return "danger"
    case "DRAFT": return "neutral"
    default: return "neutral"
  }
}

function errorMessages(error: unknown): string[] {
  if (error instanceof ApiClientError) {
    const field = Object.values(error.fieldErrors).flat()
    return field.length ? field : [error.message]
  }
  return [error instanceof Error ? error.message : "The request was rejected."]
}

function cell(row: RecordValue, ...keys: string[]): string {
  for (const key of keys) {
    if (row[key] !== null && row[key] !== undefined && row[key] !== "") return stringValue(row[key])
  }
  return "—"
}

function TableEmpty({ message }: { message: string }) {
  return <div className="surface-card p-8 text-center text-sm text-[var(--muted-foreground)]">{message}</div>
}

function DataTableShell({ children, caption }: { children: React.ReactNode; caption: string }) {
  return <div className="surface-card overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><caption className="sr-only">{caption}</caption>{children}</table></div>
}

function TableHead({ children }: { children: React.ReactNode }) {
  return <thead className="border-b bg-[var(--muted)]/45 text-xs uppercase tracking-[0.1em] text-[var(--muted-foreground)]"><tr>{children}</tr></thead>
}

function Th({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <th scope="col" className={`px-4 py-3 font-bold ${className}`}>{children}</th>
}

function Td({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <td className={`border-b px-4 py-3 align-top ${className}`}>{children}</td>
}

function StepChecklist({ completion, onJump }: { completion?: Record<string, boolean>; onJump: (id: string) => void }) {
  const rows = [
    ["personal", "Personal Details"],
    ["plans", "Plan & Sub-Products"],
    ["members", "Member Coverage"],
    ["installments", "Installments"],
    ["funds", "Investment Funds"],
    ["riders", "Riders & Benefits"],
    ["financial", "Financial Details"],
  ] as const
  return <div className="surface-card p-4"><div className="mb-3 flex items-center gap-2"><FileCheck2 size={18} className="text-[var(--primary)]" aria-hidden="true" /><h2 className="font-bold">Completion checklist</h2></div><div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">{rows.map(([id, label]) => { const complete = Boolean(completion?.[id] ?? completion?.[`step_${id}`]); return <button key={id} type="button" onClick={() => onJump(id)} className="flex items-center justify-between rounded-[10px] border px-3 py-2 text-left text-sm hover:bg-[var(--secondary)]"><span>{label}</span>{complete ? <Check size={17} className="text-[var(--success)]" aria-label={`${label} complete`} /> : <CircleAlert size={17} className="text-[var(--warning)]" aria-label={`${label} incomplete`} />}</button> })}</div></div>
}

export default function OLQuotationDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { canAccess, isSuperAdmin } = useAccess()
  const { toast } = useToast()
  const [quotation, setQuotation] = useState<QuotationDetail | null>(null)
  const [financial, setFinancial] = useState<FinancialDetails | null>(null)
  const [partner, setPartner] = useState<PartnerVerification | null>(null)
  const [versions, setVersions] = useState<VersionRow[]>([])
  const [documents, setDocuments] = useState<DocumentRow[]>([])
  const [activeTab, setActiveTab] = useState<DetailTab>("overview")
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [versionsOpen, setVersionsOpen] = useState(false)
  const [selectedVersion, setSelectedVersion] = useState<RecordValue | null>(null)
  const [printDocument, setPrintDocument] = useState<DocumentRow | null>(null)
  const [partnerOpen, setPartnerOpen] = useState(false)
  const [partnerForm, setPartnerForm] = useState<PartnerForm>({ first_name: "", surname: "", other_name: "", email: "", mobile_number: "", gender: "", date_of_birth: "", identification_type: "", identification_number: "", nationality: "", occupation: "" })
  const [partnerErrors, setPartnerErrors] = useState<string[]>([])
  const [convertOpen, setConvertOpen] = useState(false)
  const [convertErrors, setConvertErrors] = useState<string[]>([])
  const [finalizeOpen, setFinalizeOpen] = useState(false)
  const [finalizeErrors, setFinalizeErrors] = useState<string[]>([])

  const isAllowed = useCallback((permission: string) => isSuperAdmin || canAccess(permission), [canAccess, isSuperAdmin])

  const loadDetail = useCallback(async () => {
    if (!id) return
    setLoading(true)
    try {
      const payload = await request<QuotationDetail>(`${API_PREFIX}${id}/`)
      setQuotation(payload)
      setFinancial(payload.financial_summary ? { ...payload.financial_summary, recalculation_required: false } : null)
    } catch (error) {
      toast({ tone: "danger", title: "Unable to load quotation", message: error instanceof Error ? error.message : "The quotation detail could not be loaded." })
    } finally { setLoading(false) }
  }, [id, toast])

  const loadLifecycleData = useCallback(async () => {
    if (!id) return
    const [versionsResult, documentsResult, partnerResult, financialResult] = await Promise.allSettled([
      request<{ versions?: VersionRow[] }>(`${API_PREFIX}${id}/versions/`),
      request<DocumentRow[]>(`${API_PREFIX}${id}/documents/`),
      request<PartnerVerification>(`${API_PREFIX}${id}/partner-verification/`),
      request<FinancialDetails>(`${API_PREFIX}${id}/financial-details/`),
    ])
    if (versionsResult.status === "fulfilled") setVersions(listValue(versionsResult.value.versions))
    if (documentsResult.status === "fulfilled") setDocuments(listValue(documentsResult.value) as DocumentRow[])
    if (partnerResult.status === "fulfilled") setPartner(partnerResult.value)
    if (financialResult.status === "fulfilled") setFinancial(financialResult.value)
  }, [id])

  useEffect(() => { void loadDetail(); void loadLifecycleData() }, [loadDetail, loadLifecycleData])

  const runRevision = useCallback(async () => {
    if (!id) return
    setBusy(true)
    try {
      const response = await request<QuotationDetail>(`${API_PREFIX}${id}/revise/`, { method: "POST" })
      setQuotation(response)
      toast({ tone: "success", title: "Quotation revision created" })
      setActiveTab("overview")
      await loadLifecycleData()
    } catch (error) { toast({ tone: "danger", title: "Unable to revise quotation", message: error instanceof Error ? error.message : "The quotation could not be revised." }) } finally { setBusy(false) }
  }, [id, loadLifecycleData, toast])

  const openPartner = useCallback(() => {
    if (!quotation) return
    setPartnerForm({ first_name: "", surname: "", other_name: "", email: "", mobile_number: "", gender: String(quotation.gender ?? ""), date_of_birth: String(quotation.date_of_birth ?? "").slice(0, 10), identification_type: String(quotation.identity_type ?? ""), identification_number: String(quotation.identity_number ?? ""), nationality: "", occupation: "" })
    setPartnerErrors([])
    setPartnerOpen(true)
  }, [quotation])

  const completePartner = useCallback(async () => {
    if (!id) return
    setBusy(true)
    setPartnerErrors([])
    try {
      const response = await request<{ partner_verified?: boolean }>(`${API_PREFIX}${id}/partner-completion/`, { method: "POST", body: JSON.stringify(partnerForm) })
      setPartner((current) => ({ ...current, partner_exists: true, compliant: true, partner_verified: response.partner_verified }))
      setPartnerOpen(false)
      toast({ tone: "success", title: "Partner completed and linked" })
      await loadDetail()
      await loadLifecycleData()
    } catch (error) { setPartnerErrors(errorMessages(error)) } finally { setBusy(false) }
  }, [id, loadDetail, loadLifecycleData, partnerForm, toast])

  const generatePrint = useCallback(async () => {
    if (!id) return
    setBusy(true)
    try {
      const document = await request<DocumentRow>(`${API_PREFIX}${id}/print/`, { method: "POST", body: JSON.stringify({ preview: true }) })
      setPrintDocument(document)
      setDocuments((current) => [document, ...current.filter((row) => row.id !== document.id)])
    } catch (error) { toast({ tone: "danger", title: "Unable to generate printout", message: error instanceof Error ? error.message : "The printout could not be generated." }) } finally { setBusy(false) }
  }, [id, toast])

  const finalize = useCallback(async () => {
    if (!id) return
    setBusy(true)
    setFinalizeErrors([])
    try {
      const response = await request<QuotationDetail>(`${API_PREFIX}${id}/finalize/`, { method: "POST" })
      setQuotation(response)
      setFinalizeOpen(false)
      toast({ tone: "success", title: "Quotation finalized" })
      await loadLifecycleData()
    } catch (error) { setFinalizeErrors(errorMessages(error)) } finally { setBusy(false) }
  }, [id, loadLifecycleData, toast])

  const eligibilityErrors = useMemo(() => {
    const errors: string[] = []
    const status = String(quotation?.status ?? "").toUpperCase()
    if (status !== "FINALIZED") errors.push("Quotation must be finalized before conversion.")
    if (quotation?.expiry_date && new Date(`${String(quotation.expiry_date).slice(0, 10)}T23:59:59`) < new Date()) errors.push("Quotation has expired.")
    if (quotation?.partner_verified !== true || partner?.compliant !== true) errors.push("Partner verification must be completed and compliant.")
    if (quotation?.approval_required) errors.push("Approval is required before conversion can proceed.")
    return errors
  }, [partner?.compliant, quotation?.approval_required, quotation?.expiry_date, quotation?.partner_verified, quotation?.status])

  const convertToProposal = useCallback(async () => {
    if (!id) return
    if (eligibilityErrors.length) { setConvertErrors(eligibilityErrors); return }
    setBusy(true)
    setConvertErrors([])
    try {
      await request(`${API_PREFIX}${id}/convert-to-proposal/`, { method: "POST", body: JSON.stringify({}) })
      toast({ tone: "success", title: "Quotation converted to proposal" })
      setConvertOpen(false)
      navigate(`/ordinary-life/proposals?quotation=${id}`)
    } catch (error) { setConvertErrors(errorMessages(error)) } finally { setBusy(false) }
  }, [eligibilityErrors, id, navigate, toast])

  const loadVersion = useCallback(async (versionNumber: number) => {
    if (!id) return
    try {
      const response = await request<RecordValue>(`${API_PREFIX}${id}/as-of-version/${versionNumber}/`)
      setSelectedVersion(response)
    } catch (error) { toast({ tone: "danger", title: "Unable to load version", message: error instanceof Error ? error.message : "The version snapshot could not be loaded." }) }
  }, [id, toast])

  const status = String(quotation?.status ?? "DRAFT")
  const currency = quotation?.currency ?? undefined
  const summary = financial?.summary ?? (financial && !("summary" in financial) ? financial : quotation?.financial_summary) ?? null
  const projections = listValue(financial?.projections ?? summary?.projections)
  const payouts = listValue(financial?.installment_payouts ?? summary?.installment_payouts)
  const completion = quotation?.wizard_step_completion
  const hasRevision = status === "FINALIZED" && isAllowed("ol_quotations.update")
  const canFinalize = status === "DRAFT" && isAllowed("ol_quotations.finalize")
  const canPrint = ["FINALIZED", "CONVERTED"].includes(status) && isAllowed("ol_quotations.print")
  const canConvert = status === "FINALIZED" && isAllowed("ol_quotations.convert")

  const stats = [
    { label: "Version", value: stringValue(quotation?.current_version_number) },
    { label: "Total premium", value: moneyLabel(quotation?.total_premium ?? summary?.total_premium, currency) },
    { label: "Sum assured", value: moneyLabel(quotation?.total_sum_assured ?? summary?.total_sum_assured, currency) },
    { label: "Expiry", value: dateLabel(quotation?.expiry_date) },
  ]

  const jumpTo = (step: string) => {
    const map: Record<string, DetailTab> = { personal: "overview", plans: "plans", members: "members", installments: "installments", funds: "funds", riders: "riders", financial: "financials" }
    setActiveTab(map[step] ?? "overview")
  }

  if (loading && !quotation) return <div className="flex min-h-64 items-center justify-center"><LoaderCircle className="animate-spin text-[var(--primary)]" aria-label="Loading quotation" /></div>
  if (!quotation) return <InfoBanner title="Quotation unavailable">The requested quotation could not be loaded.</InfoBanner>

  return <div className="space-y-5 p-4 md:p-6">
    <MasterDetailPage
      eyebrow="Ordinary Life / Quotations"
      title={stringValue(quotation.quote_number, `Quotation ${id ?? ""}`)}
      description={`${stringValue(quotation.quote_name)} · Created ${dateLabel(quotation.created_at)}`}
      status={{ value: status, tone: statusTone(status) }}
      stats={stats}
      tabs={tabs}
      activeTab={activeTab}
      onTabChange={(tab) => setActiveTab(tab as DetailTab)}
      actions={<><button type="button" className="button-secondary" onClick={() => navigate("/ordinary-life/quotations")}><ArrowLeft size={16} aria-hidden="true" />Back</button>{hasRevision && <button type="button" className="button-secondary" onClick={() => void runRevision()} disabled={busy}><RefreshCcw size={16} aria-hidden="true" />Revise</button>}{canPrint && <button type="button" className="button-secondary" onClick={() => void generatePrint()} disabled={busy}><FileText size={16} aria-hidden="true" />Print preview</button>}{canConvert && <button type="button" className="button-primary" onClick={() => { setConvertErrors([]); setConvertOpen(true) }}><ChevronRight size={16} aria-hidden="true" />Convert to Proposal</button>}</>}
    >
      {quotation.approval_required && <div className="flex items-start gap-3 rounded-[10px] border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950" role="alert"><CircleAlert className="mt-0.5 shrink-0" size={18} aria-hidden="true" /><div><p className="font-bold">Approval required</p><p className="mt-1">{stringValue(quotation.approval_reason, "This quotation requires approval before downstream conversion.")}</p></div></div>}
      {partner && (!partner.compliant || quotation.partner_verified !== true) && <InfoBanner title="Partner verification pending"><div className="flex flex-wrap items-center justify-between gap-3"><span>{partner.partner_exists ? "A matching partner exists but is not compliant." : "No compliant partner is linked to this quotation."}{partner.missing_fields?.length ? ` Missing: ${partner.missing_fields.join(", ")}.` : ""}</span><button type="button" className="button-primary" onClick={openPartner}><UserRound size={16} aria-hidden="true" />Complete partner</button></div></InfoBanner>}
      {activeTab === "overview" && <div className="space-y-4"><StepChecklist completion={completion} onJump={jumpTo} /><div className="grid gap-4 lg:grid-cols-2"><section className="surface-card p-4"><h2 className="mb-3 font-bold">Quotation summary</h2><dl className="grid gap-3 sm:grid-cols-2">{[["Quote name", quotation.quote_name], ["Quote date", dateLabel(quotation.quote_date)], ["Currency", quotation.currency], ["Identity type", quotation.identity_type], ["Identity number", quotation.identity_number], ["Date of birth", dateLabel(quotation.date_of_birth)], ["Age at quote", quotation.age_at_quote], ["Gender", quotation.gender], ["Smoker status", quotation.smoker_status], ["Location", quotation.location], ["Address", quotation.address]].map(([label, value]) => <div key={String(label)}><dt className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">{label}</dt><dd className="mt-1 text-sm font-semibold">{stringValue(value)}</dd></div>)}</dl></section><section className="surface-card p-4"><h2 className="mb-3 font-bold">Review actions</h2><div className="space-y-3">{canFinalize && <button type="button" className="button-primary w-full justify-center" onClick={() => { setFinalizeErrors([]); setFinalizeOpen(true) }}><Check size={16} aria-hidden="true" />Finalize quotation</button>}{canConvert && <button type="button" className="button-secondary w-full justify-center" onClick={() => { setConvertErrors([]); setConvertOpen(true) }}><ChevronRight size={16} aria-hidden="true" />Convert to proposal</button>}<button type="button" className="button-secondary w-full justify-center" onClick={() => setVersionsOpen(true)}><History size={16} aria-hidden="true" />View versions</button></div></section></div></div>}
      {activeTab === "plans" && <PlansTab rows={listValue(quotation.plan_configurations)} currency={currency} />}
      {activeTab === "members" && <MembersTab rows={listValue(quotation.members)} />}
      {activeTab === "installments" && <InstallmentsTab rows={listValue(quotation.installment_configurations)} currency={currency} />}
      {activeTab === "funds" && <FundsTab rows={listValue(quotation.fund_allocations)} currency={currency} />}
      {activeTab === "riders" && <RidersTab rows={listValue(quotation.rider_selections)} benefits={listValue(quotation.benefits)} currency={currency} />}
      {activeTab === "financials" && <FinancialsTab financial={financial} summary={summary} projections={projections} payouts={payouts} currency={currency} recalculationRequired={Boolean(financial?.recalculation_required)} onCalculate={async () => { if (!id) return; setBusy(true); try { const response = await request<FinancialDetails>(`${API_PREFIX}${id}/calculate/`, { method: "POST", body: JSON.stringify({}) }); setFinancial(response); toast({ tone: "success", title: "Financial details recalculated" }); await loadDetail() } catch (error) { toast({ tone: "danger", title: "Calculation failed", message: error instanceof Error ? error.message : "The rating engine rejected the calculation." }) } finally { setBusy(false) } }} busy={busy} />}
      {activeTab === "versions" && <VersionsTab versions={versions} onOpenDrawer={() => setVersionsOpen(true)} onView={(version) => void loadVersion(version)} />}
      {activeTab === "documents" && <DocumentsTab rows={documents} onPreview={setPrintDocument} onGenerate={() => void generatePrint()} busy={busy} />}
    </MasterDetailPage>

    <Drawer open={versionsOpen} title="Quotation versions" description="Review historical snapshots or revise from the current finalized version." onClose={() => setVersionsOpen(false)} width="max-w-2xl"><div className="space-y-3">{versions.length === 0 ? <TableEmpty message="No versions are available." /> : versions.map((version) => <article key={String(version.id ?? version.version_number)} className="rounded-[10px] border p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-bold">Version {stringValue(version.version_number)}</p><p className="mt-1 text-xs text-[var(--muted-foreground)]">{dateLabel(version.created_at)} · {stringValue(version.created_by, "System")}</p><p className="mt-2 text-sm">{stringValue(version.change_reason, "No change reason recorded.")}</p></div><StatusBadge value={String(version.status ?? "Superseded")} tone={String(version.status).toUpperCase() === "CURRENT" ? "success" : "neutral"} /></div><div className="mt-3 flex gap-2"><button type="button" className="button-secondary" onClick={() => void loadVersion(Number(version.version_number))}><Eye size={15} aria-hidden="true" />Switch view</button>{hasRevision && <button type="button" className="button-secondary" onClick={() => void runRevision()}><Pencil size={15} aria-hidden="true" />Open revise</button>}</div></article>)}</div>{selectedVersion && <div className="mt-5 rounded-[10px] border bg-[var(--muted)]/35 p-4"><div className="mb-2 flex items-center justify-between"><h3 className="font-bold">Version {stringValue(selectedVersion.version_number)} snapshot</h3><button type="button" aria-label="Close version snapshot" className="rounded-md p-1 hover:bg-[var(--secondary)]" onClick={() => setSelectedVersion(null)}><X size={16} aria-hidden="true" /></button></div><pre className="max-h-80 overflow-auto whitespace-pre-wrap text-xs leading-5">{JSON.stringify(selectedVersion.snapshot ?? selectedVersion, null, 2)}</pre></div>}</Drawer>

    <Modal open={Boolean(printDocument)} title="Quotation print preview" description="Generated from the quotation’s source version and active template." onClose={() => setPrintDocument(null)} size="xl" footer={<><button type="button" className="button-secondary" onClick={() => setPrintDocument(null)}>Close</button>{printDocument?.pdf_url && <a className="button-primary" href={String(printDocument.pdf_url)} target="_blank" rel="noreferrer"><Download size={16} aria-hidden="true" />Download PDF</a>}</>}>
      {printDocument?.html_url ? <iframe title="Quotation document preview" src={String(printDocument.html_url)} className="h-[65vh] w-full rounded-[10px] border bg-white" sandbox="allow-same-origin" /> : <div className="space-y-3"><InfoBanner title="Preview generated">The document was generated successfully, but an HTML preview URL was not returned.</InfoBanner><dl className="grid gap-3 sm:grid-cols-2"><div><dt className="text-xs font-bold uppercase text-[var(--muted-foreground)]">Template</dt><dd>{stringValue(printDocument?.template_code)}</dd></div><div><dt className="text-xs font-bold uppercase text-[var(--muted-foreground)]">Template version</dt><dd>{stringValue(printDocument?.template_version)}</dd></div></dl></div>}
    </Modal>

    <Modal open={partnerOpen} title="Complete partner verification" description="Complete the missing compliant-partner fields before conversion." onClose={() => { if (!busy) setPartnerOpen(false) }} footer={<><button type="button" className="button-secondary" onClick={() => setPartnerOpen(false)} disabled={busy}>Cancel</button><button type="button" className="button-primary" onClick={() => void completePartner()} disabled={busy}>{busy ? "Saving…" : "Save and verify"}</button></>}>
      {partnerErrors.length > 0 && <div className="mb-4 space-y-1 rounded-[10px] border border-red-200 bg-red-50 p-3 text-sm text-red-900" role="alert">{partnerErrors.map((error) => <p key={error}>{error}</p>)}</div>}
      <FormGrid columns={2}>{(["first_name", "surname", "other_name", "email", "mobile_number", "nationality", "occupation", "identification_number"] as const).map((field) => <TextInput key={field} label={field.replace(/_/g, " ").replace(/\b\w/g, (letter: string) => letter.toUpperCase())} name={field} value={partnerForm[field]} onChange={(event) => setPartnerForm((current) => ({ ...current, [field]: event.target.value }))} required={field === "first_name" || field === "surname" || field === "identification_number"} />)}<SelectInput label="Gender" name="gender" value={partnerForm.gender} onChange={(event) => setPartnerForm((current) => ({ ...current, gender: event.target.value }))}><option value="">Select gender</option><option value="MALE">Male</option><option value="FEMALE">Female</option></SelectInput><DateInput label="Date of birth" name="date_of_birth" value={partnerForm.date_of_birth} onChange={(event) => setPartnerForm((current) => ({ ...current, date_of_birth: event.target.value }))} /><TextInput label="Identification type" name="identification_type" value={partnerForm.identification_type} onChange={(event) => setPartnerForm((current) => ({ ...current, identification_type: event.target.value }))} /></FormGrid>
    </Modal>

    <Modal open={convertOpen} title="Convert to Proposal" description="The quotation must satisfy BR-01 before handoff to OL Proposals." onClose={() => setConvertOpen(false)} footer={<><button type="button" className="button-secondary" onClick={() => setConvertOpen(false)} disabled={busy}>Close</button><button type="button" className="button-primary" onClick={() => void convertToProposal()} disabled={busy}>{busy ? "Converting…" : "Convert to Proposal"}</button></>}>
      {eligibilityErrors.length || convertErrors.length ? <div className="space-y-2 rounded-[10px] border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950" role="alert"><p className="font-bold">Conversion is blocked</p>{[...eligibilityErrors, ...convertErrors].map((error) => <p key={error}>• {error}</p>)}</div> : <InfoBanner title="Ready for conversion">Partner verification, quotation finalization, expiry, and approval checks have passed.</InfoBanner>}
    </Modal>

    <ConfirmModal open={finalizeOpen} title="Finalize quotation" description="Finalize this quotation? It will become read-only until revised." confirmLabel="Finalize" onClose={() => setFinalizeOpen(false)} onConfirm={() => void finalize()} tone="primary" />
    {finalizeErrors.length > 0 && <div className="fixed bottom-5 right-5 z-40 max-w-md rounded-[10px] border border-red-200 bg-red-50 p-4 text-sm text-red-900 shadow-xl" role="alert"><div className="flex items-start justify-between gap-3"><p className="font-bold">Finalization blocked</p><button type="button" aria-label="Dismiss finalization errors" onClick={() => setFinalizeErrors([])}><X size={16} aria-hidden="true" /></button></div>{finalizeErrors.map((error) => <button type="button" className="mt-2 block text-left underline" key={error} onClick={() => { setFinalizeErrors([]); jumpTo("financial") }}>{error}</button>)}</div>}
  </div>
}

function PlansTab({ rows, currency }: { rows: RecordValue[]; currency?: unknown }) {
  if (rows.length === 0) return <TableEmpty message="No plan configurations are attached." />
  return <DataTableShell caption="Quotation plans"><TableHead><Th>Section</Th><Th>Plan</Th><Th>Term</Th><Th>Payment period</Th><Th>Frequency</Th><Th>Quote basis</Th><Th>Estimated maturity</Th></TableHead><tbody>{rows.map((row, index) => <tr key={String(row.id ?? index)}><Td>{cell(row, "section_number")}</Td><Td><p className="font-semibold">{cell(row, "sub_product_code", "plan_code", "plan")}</p><p className="text-xs text-[var(--muted-foreground)]">{cell(row, "plan_name", "product_name")}</p></Td><Td>{cell(row, "term_years", "policy_term_years")} years</Td><Td>{cell(row, "payment_period_years")} years</Td><Td>{cell(row, "premium_frequency", "payment_mode")}</Td><Td>{cell(row, "quote_basis")}</Td><Td>{moneyLabel(row.estimated_maturity_value, currency)}</Td></tr>)}</tbody></DataTableShell>
}

function MembersTab({ rows }: { rows: RecordValue[] }) {
  if (rows.length === 0) return <TableEmpty message="No members are recorded for this quotation." />
  return <DataTableShell caption="Quotation members"><TableHead><Th>Name</Th><Th>Relation</Th><Th>Date of birth</Th><Th>Age</Th><Th>Gender</Th><Th>Sum assured</Th></TableHead><tbody>{rows.map((row, index) => <tr key={String(row.id ?? index)}><Td>{cell(row, "full_name", "name")}{row.is_principal ? <span className="ml-2 text-xs font-bold text-[var(--primary)]">Principal</span> : null}</Td><Td>{cell(row, "relation", "member_type")}</Td><Td>{dateLabel(row.date_of_birth)}</Td><Td>{cell(row, "age_at_quote", "age")}</Td><Td>{cell(row, "gender")}</Td><Td>{moneyLabel(row.sum_assured)}</Td></tr>)}</tbody></DataTableShell>
}

function InstallmentsTab({ rows, currency }: { rows: RecordValue[]; currency?: unknown }) {
  if (rows.length === 0) return <TableEmpty message="No installment configurations are recorded." />
  return <DataTableShell caption="Quotation installments"><TableHead><Th>Plan</Th><Th>Policy term</Th><Th>Payment mode</Th><Th>Installments</Th><Th>Status</Th><Th>Benefits</Th></TableHead><tbody>{rows.map((row, index) => <tr key={String(row.id ?? index)}><Td>{cell(row, "plan_name", "plan", "sub_product_code")}</Td><Td>{cell(row, "policy_term_years", "term_years")} years</Td><Td>{cell(row, "payment_mode", "premium_frequency")}</Td><Td>{cell(row, "total_number_of_installments", "installment_count")}</Td><Td><StatusBadge value={String(row.status ?? "Configured")} tone={String(row.status).toUpperCase() === "CONFIGURED" ? "success" : "neutral"} /></Td><Td>{[row.after_maturity_benefits ? "After maturity" : "", row.before_maturity_benefits ? "Before maturity" : ""].filter(Boolean).join(" · ") || "—"}{currency ? ` · ${String(currency)}` : ""}</Td></tr>)}</tbody></DataTableShell>
}

function FundsTab({ rows, currency }: { rows: RecordValue[]; currency?: unknown }) {
  if (rows.length === 0) return <TableEmpty message="No investment-fund allocations are recorded." />
  return <DataTableShell caption="Quotation investment funds"><TableHead><Th>Fund</Th><Th>Fund type</Th><Th>Risk profile</Th><Th>Currency</Th><Th>Allocation</Th><Th>Amount</Th></TableHead><tbody>{rows.map((row, index) => <tr key={String(row.id ?? index)}><Td>{cell(row, "fund_name", "investment_fund_name", "fund")}</Td><Td>{cell(row, "fund_type")}</Td><Td>{cell(row, "risk_profile")}</Td><Td>{cell(row, "currency", "fund_currency")}</Td><Td>{cell(row, "allocation_percent")} %</Td><Td>{moneyLabel(row.allocated_amount, currency ?? row.currency)}</Td></tr>)}</tbody></DataTableShell>
}

function RidersTab({ rows, benefits, currency }: { rows: RecordValue[]; benefits: RecordValue[]; currency?: unknown }) {
  return <div className="space-y-5"><section><div className="mb-3 flex items-center gap-2"><ShieldCheck size={18} className="text-[var(--primary)]" aria-hidden="true" /><h2 className="font-bold">Attached riders</h2></div>{rows.length === 0 ? <TableEmpty message="No riders are attached." /> : <DataTableShell caption="Quotation riders"><TableHead><Th>Rider</Th><Th>Category</Th><Th>Benefit</Th><Th>Term</Th><Th>Waiting period</Th><Th>Underwriting</Th></TableHead><tbody>{rows.map((row, index) => <tr key={String(row.id ?? index)}><Td>{cell(row, "rider_name", "name", "rider_code")}</Td><Td>{cell(row, "category")}</Td><Td>{moneyLabel(row.sum_assured ?? row.benefit_amount, currency)}</Td><Td>{cell(row, "term_years", "term")}</Td><Td>{cell(row, "waiting_period_days")} days</Td><Td>{row.requires_underwriting ? "Required" : "Not required"}</Td></tr>)}</tbody></DataTableShell>}</section><section><h2 className="mb-3 font-bold">Benefits</h2>{benefits.length === 0 ? <TableEmpty message="No benefits are configured." /> : <DataTableShell caption="Quotation benefits"><TableHead><Th>Type</Th><Th>Basis</Th><Th>Value</Th><Th>Loading</Th><Th>Discount</Th><Th>Cap</Th></TableHead><tbody>{benefits.map((row, index) => <tr key={String(row.id ?? index)}><Td>{cell(row, "benefit_type", "type")}</Td><Td>{cell(row, "basis", "calculation_basis")}</Td><Td>{cell(row, "value")}</Td><Td>{cell(row, "loading")}</Td><Td>{cell(row, "discount")}</Td><Td>{cell(row, "maximum_cap", "cap")}</Td></tr>)}</tbody></DataTableShell>}</section></div>
}

function FinancialsTab({ financial, summary, projections, payouts, currency, recalculationRequired, onCalculate, busy }: { financial: FinancialDetails | null; summary: RecordValue | null; projections: RecordValue[]; payouts: RecordValue[]; currency?: unknown; recalculationRequired: boolean; onCalculate: () => Promise<void>; busy: boolean }) {
  if (!financial || !summary) return <div className="space-y-4"><InfoBanner title="Financial details not calculated">Calculate the quotation to load backend rating outputs, projections, and installment payouts.</InfoBanner><button type="button" className="button-primary" onClick={() => void onCalculate()} disabled={busy}>{busy ? "Calculating…" : "Calculate financial details"}</button></div>
  const cards: [string, unknown][] = [["Base premium", summary.base_premium], ["Rider premiums", summary.rider_premium ?? summary.rider_premiums], ["Loadings", summary.total_loadings ?? summary.loadings], ["Discounts", summary.total_discounts ?? summary.discounts], ["Taxes", summary.total_taxes ?? summary.taxes], ["Total premium", summary.total_premium]]
  return <div className="space-y-5"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-lg font-bold">Financial details</h2><p className="text-sm text-[var(--muted-foreground)]">All values below are returned by the backend rating engine.</p></div><button type="button" className="button-primary" onClick={() => void onCalculate()} disabled={busy}>{busy ? <LoaderCircle size={16} className="animate-spin" aria-hidden="true" /> : <RefreshCcw size={16} aria-hidden="true" />}{busy ? "Calculating…" : "Recalculate"}</button></div>{recalculationRequired && <div className="flex items-start gap-3 rounded-[10px] border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950" role="alert"><CircleAlert size={18} className="mt-0.5 shrink-0" aria-hidden="true" /><span>Inputs changed after the last calculation. Recalculate before finalizing.</span></div>}<div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{cards.map(([label, value]) => <article key={String(label)} className={`surface-card p-4 ${label === "Total premium" ? "ring-2 ring-[var(--primary)]/25" : ""}`}><p className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">{String(label)}</p><p className="mt-2 text-xl font-extrabold">{moneyLabel(value, currency)}</p><p className="mt-1 text-xs text-[var(--muted-foreground)]">{String(summary.frequency_label ?? summary.payment_frequency ?? "Backend output")}</p></article>)}</div><div className="rounded-[12px] border border-[var(--primary)]/30 bg-[var(--primary)]/8 p-5"><p className="text-xs font-bold uppercase tracking-[0.12em] text-[var(--muted-foreground)]">Estimated maturity value</p><p className="mt-2 text-3xl font-extrabold">{moneyLabel(summary.estimated_maturity_value, currency)}</p></div><section><h3 className="mb-3 font-bold">Policy-year projections</h3>{projections.length === 0 ? <TableEmpty message="No projection rows returned." /> : <DataTableShell caption="Policy year projections"><TableHead><Th>Policy year</Th><Th>Premiums paid</Th><Th>Bonuses</Th><Th>Surrender value</Th><Th>Paid-up value</Th><Th>Maturity value</Th></TableHead><tbody>{projections.map((row, index) => <tr key={String(row.policy_year ?? index)}><Td>{cell(row, "policy_year")}</Td><Td>{moneyLabel(row.premiums_paid, currency)}</Td><Td>{moneyLabel(row.estimated_bonus, currency)}</Td><Td>{moneyLabel(row.surrender_value, currency)}</Td><Td>{moneyLabel(row.paid_up_value, currency)}</Td><Td>{moneyLabel(row.estimated_maturity_value, currency)}</Td></tr>)}</tbody></DataTableShell>}</section><section><h3 className="mb-3 font-bold">Installment payout schedule</h3>{payouts.length === 0 ? <TableEmpty message="No installment payouts returned." /> : <DataTableShell caption="Installment payout schedule"><TableHead><Th>Installment</Th><Th>Date</Th><Th>Description</Th><Th>Rate</Th><Th>Payout amount</Th></TableHead><tbody>{payouts.map((row, index) => <tr key={String(row.sequence ?? index)}><Td>{cell(row, "sequence")}</Td><Td>{dateLabel(row.payout_date)}</Td><Td>{cell(row, "description")}</Td><Td>{cell(row, "rate_percent")} %</Td><Td>{moneyLabel(row.payout_amount, currency)}</Td></tr>)}</tbody></DataTableShell>}</section></div>
}

function VersionsTab({ versions, onOpenDrawer, onView }: { versions: VersionRow[]; onOpenDrawer: () => void; onView: (version: number) => void }) {
  return <div className="space-y-4"><div className="flex items-center justify-between gap-3"><div><h2 className="text-lg font-bold">Quotation versions</h2><p className="text-sm text-[var(--muted-foreground)]">Historical snapshots are retained under BR-02.</p></div><button type="button" className="button-secondary" onClick={onOpenDrawer}><History size={16} aria-hidden="true" />Open versions drawer</button></div>{versions.length === 0 ? <TableEmpty message="No quotation versions are available." /> : <DataTableShell caption="Quotation versions"><TableHead><Th>Version</Th><Th>Status</Th><Th>Created by</Th><Th>Created at</Th><Th>Change reason</Th><Th>Action</Th></TableHead><tbody>{versions.map((version, index) => <tr key={String(version.id ?? index)}><Td>{cell(version, "version_number")}</Td><Td><StatusBadge value={String(version.status ?? "Superseded")} tone={String(version.status).toUpperCase() === "CURRENT" ? "success" : "neutral"} /></Td><Td>{cell(version, "created_by", "created_by_name")}</Td><Td>{dateLabel(version.created_at)}</Td><Td>{cell(version, "change_reason")}</Td><Td><button type="button" className="button-secondary" onClick={() => onView(Number(version.version_number))}><Eye size={15} aria-hidden="true" />View</button></Td></tr>)}</tbody></DataTableShell>}</div>
}

function DocumentsTab({ rows, onPreview, onGenerate, busy }: { rows: DocumentRow[]; onPreview: (row: DocumentRow) => void; onGenerate: () => void; busy: boolean }) {
  return <div className="space-y-4"><div className="flex items-center justify-between gap-3"><div><h2 className="text-lg font-bold">Generated documents</h2><p className="text-sm text-[var(--muted-foreground)]">Each printout retains its source quotation version and template version.</p></div><button type="button" className="button-primary" onClick={onGenerate} disabled={busy}><FileText size={16} aria-hidden="true" />{busy ? "Generating…" : "Generate printout"}</button></div>{rows.length === 0 ? <TableEmpty message="No generated printouts are available." /> : <DataTableShell caption="Quotation documents"><TableHead><Th>Document</Th><Th>Source version</Th><Th>Template</Th><Th>Template version</Th><Th>Status</Th><Th>Generated at</Th><Th>Action</Th></TableHead><tbody>{rows.map((row, index) => <tr key={String(row.id ?? index)}><Td>{cell(row, "document_type", "mime_type")}</Td><Td>{cell(row, "source_version_number")}</Td><Td>{cell(row, "template_code")}</Td><Td>{cell(row, "template_version")}</Td><Td><StatusBadge value={String(row.status ?? "Generated")} tone="success" /></Td><Td>{dateLabel(row.generated_at)}</Td><Td><div className="flex gap-2"><button type="button" className="button-secondary" onClick={() => onPreview(row)}><Eye size={15} aria-hidden="true" />Preview</button>{row.pdf_url && <a className="button-secondary" href={String(row.pdf_url)} target="_blank" rel="noreferrer"><Download size={15} aria-hidden="true" />PDF</a>}</div></Td></tr>)}</tbody></DataTableShell>}</div>
}

export { default as OLQuotationWizard } from "./OLQuotationWizard"

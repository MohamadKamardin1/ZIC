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
import { getPartner, listPartners } from "../../lib/api"
import type { PartnerListItem } from "../../lib/types"
import { useAccess } from "../../lib/access"
import { DateInput, FormGrid, SelectInput, TextInput, TextareaInput } from "../../components/ui/FormControls"
import { ConfirmModal, Drawer, InfoBanner, Modal } from "../../components/ui/Overlays"
import { StatusBadge, type StatusTone } from "../../components/ui/StatusBadge"
import { SmartSelect } from "../../components/ui/SmartSelect"
import { useToast } from "../../components/ui/Toast"
import { DocumentInstancesPanel } from "../../components/documents/DocumentInstancesPanel"
import { renderFk, sanitizeForDisplay } from "../../lib/display"

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
  created_by_display?: string | null
  created_at?: string
  change_reason?: string | null
  quote_number?: string | null
  sum_assured?: string | number | null
  total_sum_assured?: string | number | null
  gross_premium?: string | number | null
  total_premium?: string | number | null
  currency?: string | null
}

type PartnerVerification = {
  partner_exists?: boolean
  partner_id?: string | null
  compliant?: boolean
  missing_fields?: string[]
  partner_number?: string | null
  partner_display_name?: string | null
  partner_verified?: boolean
  application_id?: string | null
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

function toSnake(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(toSnake)
  if (value && typeof value === "object") {
    const result: Record<string, unknown> = {}
    for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
      result[key.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`)] = toSnake(item)
    }
    return result
  }
  return value
}

async function requestSnake<T>(path: string, options?: Parameters<typeof request>[1]): Promise<T> {
  return toSnake(await request<T>(path, options)) as T
}

function asRecord(value: unknown): RecordValue {
  return value && typeof value === "object" && !Array.isArray(value) ? value as RecordValue : {}
}

function listValue(value: unknown): RecordValue[] {
  return Array.isArray(value) ? value.filter((item): item is RecordValue => Boolean(item && typeof item === "object" && !Array.isArray(item))) : []
}

function scalarValue(value: unknown): string | number | null | undefined {
  return typeof value === "string" || typeof value === "number" || value === null ? value : undefined
}

function responseRows(value: unknown, key?: string): RecordValue[] {
  if (Array.isArray(value)) return listValue(value)
  const record = asRecord(value)
  return listValue(record.results ?? (key ? record[key] : undefined) ?? record.data)
}

function stageFailure(label: string, result: PromiseSettledResult<unknown>): string | null {
  if (result.status !== "rejected") return null
  return `${label}: ${result.reason instanceof Error ? result.reason.message : "The service did not return data."}`
}

function mergeStageAggregate(
  base: QuotationDetail,
  stages: { summary?: unknown; partner?: unknown; plans?: unknown; members?: unknown; installments?: unknown; funds?: unknown; riders?: unknown; financial?: unknown },
): QuotationDetail {
  const summary = asRecord(stages.summary)
  const partnerState = asRecord(stages.partner)
  const planState = asRecord(stages.plans)
  const memberState = asRecord(stages.members)
  const installmentState = asRecord(stages.installments)
  const fundState = asRecord(stages.funds)
  const riderState = asRecord(stages.riders)
  const financial = asRecord(stages.financial)
  const financialSummary = asRecord(financial.summary)
  const planRows = listValue(planState.configurations ?? planState.plan_configurations)
  const fundRows = listValue(fundState.plan_rows).flatMap((row) => listValue(row.allocations).map((allocation) => ({ ...allocation, plan_configuration_id: allocation.plan_configuration_id ?? row.plan_configuration_id, plan_name: allocation.plan_name ?? row.plan_name, plan_code: allocation.plan_code ?? row.plan_code })))
  const riderRows = listValue(riderState.plan_rows).flatMap((row) => listValue(row.riders).map((rider) => ({ ...rider, plan_configuration_id: rider.plan_configuration_id ?? row.plan_configuration_id, plan_name: rider.plan_name ?? row.plan_name, plan_code: rider.plan_code ?? row.plan_code })))
  const benefitRows = listValue(riderState.plan_rows).flatMap((row) => listValue(row.benefits).map((benefit) => ({ ...benefit, plan_configuration_id: benefit.plan_configuration_id ?? row.plan_configuration_id, plan_name: benefit.plan_name ?? row.plan_name, plan_code: benefit.plan_code ?? row.plan_code })))
  const completion = normalizeCompletion({
    ...asRecord(base.wizard_step_completion),
    ...asRecord(summary.completion),
    ...asRecord(summary.steps),
    ...(typeof memberState.wizard_step_complete === "boolean" ? { members: memberState.wizard_step_complete } : {}),
    ...(typeof installmentState.wizard_step_complete === "boolean" ? { installments: installmentState.wizard_step_complete } : {}),
    ...(typeof fundState.wizard_complete === "boolean" ? { funds: fundState.wizard_complete } : {}),
    ...(typeof riderState.wizard_complete === "boolean" ? { riders: riderState.wizard_complete } : {}),
    ...(financial && Object.keys(financial).length ? { financial: !financial.recalculation_required } : {}),
  })
  return {
    ...base,
    wizard_step_completion: completion,
    plan_configurations: planRows.length ? planRows : listValue(base.plan_configurations),
    members: listValue(memberState.members).length ? listValue(memberState.members) : listValue(base.members),
    installment_configurations: listValue(installmentState.rows).length ? listValue(installmentState.rows) : listValue(base.installment_configurations),
    fund_allocations: fundRows.length ? fundRows : listValue(base.fund_allocations),
    rider_selections: riderRows.length ? riderRows : listValue(base.rider_selections),
    benefits: benefitRows.length ? benefitRows : listValue(base.benefits),
    financial_summary: Object.keys(financialSummary).length ? financialSummary : (Object.keys(financial).length && !("summary" in financial) ? financial : base.financial_summary),
    total_premium: scalarValue(base.total_premium) ?? scalarValue(financialSummary.total_premium) ?? scalarValue(financial.total_premium) ?? null,
    total_sum_assured: scalarValue(base.total_sum_assured) ?? scalarValue(financialSummary.total_sum_assured) ?? scalarValue(financial.total_sum_assured) ?? null,
    partner_verified: typeof partnerState.compliant === "boolean" ? partnerState.compliant : base.partner_verified,
    partner_display: partnerState.partner_display_name ?? base.partner_display,
  }
}

function stringValue(value: unknown, fallback = "—"): string {
  return value === null || value === undefined || value === "" ? fallback : String(value)
}

function numberValue(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function normalizeCompletion(value: unknown): Record<string, boolean> {
  const source = asRecord(value)
  const aliases: Record<string, string> = {
    personal: "1_personal_details",
    personal_details: "1_personal_details",
    plans: "2_plan_and_sub_products",
    product_plan: "2_plan_and_sub_products",
    members: "3_member_coverage",
    installments: "4_installments",
    funds: "5_investment_funds",
    riders: "6_riders_and_benefits",
    financial: "7_financial_details",
  }
  const legacyAliases: Record<string, string> = {
    "1_product_plan": "plans",
    "2_members": "members",
    "3_installments": "installments",
    "4_funds": "funds",
    "5_riders": "riders",
    "6_payment": "payment_details",
    "7_underwriting": "underwriting",
  }
  const completion: Record<string, boolean> = {}
  Object.entries(source).forEach(([key, item]) => { if (typeof item === "boolean") completion[key] = item })
  Object.entries(legacyAliases).forEach(([legacy, friendly]) => {
    if (typeof source[legacy] === "boolean") completion[friendly] = source[legacy] as boolean
  })
  Object.entries(aliases).forEach(([friendly, canonical]) => {
    const valueForStep = source[friendly] ?? source[canonical] ?? source[`step_${friendly}`] ?? completion[friendly]
    if (typeof valueForStep === "boolean") {
      completion[friendly] = valueForStep
      completion[canonical] = valueForStep
    }
  })
  return completion
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
    const value = row[key]
    const display = row[`${key}_display`]
    if (value !== null && value !== undefined && value !== "") return renderFk(value, display)
    if (display !== null && display !== undefined && display !== "") return renderFk(display)
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
  const resolvedCompletion = normalizeCompletion(completion)
  const rows = [
    ["personal", "Personal Details"],
    ["plans", "Plan & Sub-Products"],
    ["members", "Member Coverage"],
    ["installments", "Installments"],
    ["funds", "Investment Funds"],
    ["riders", "Riders & Benefits"],
    ["financial", "Financial Details"],
  ] as const
  return <div className="surface-card p-4"><div className="mb-3 flex items-center gap-2"><FileCheck2 size={18} className="text-[var(--primary)]" aria-hidden="true" /><h2 className="font-bold">Completion checklist</h2></div><div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">{rows.map(([id, label]) => { const complete = Boolean(resolvedCompletion[id]); return <button key={id} type="button" onClick={() => onJump(id)} className="flex items-center justify-between rounded-[10px] border px-3 py-2 text-left text-sm hover:bg-[var(--secondary)]"><span>{label}</span>{complete ? <Check size={17} className="text-[var(--success)]" aria-label={`${label} complete`} /> : <CircleAlert size={17} className="text-[var(--warning)]" aria-label={`${label} incomplete`} />}</button> })}</div></div>
}

function SummaryGrid({ rows, className = "sm:grid-cols-2" }: { rows: Array<[string, unknown]>; className?: string }) {
  return <dl className={`grid gap-3 ${className}`}>{rows.map(([label, value]) => <div key={String(label)}><dt className="text-xs font-bold uppercase tracking-[0.1em] text-[var(--muted-foreground)]">{label}</dt><dd className="mt-1 text-sm font-semibold">{stringValue(value)}</dd></div>)}</dl>
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
  const [stageErrors, setStageErrors] = useState<string[]>([])
  const [activeTab, setActiveTab] = useState<DetailTab>("overview")
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [versionsOpen, setVersionsOpen] = useState(false)
  const [selectedVersion, setSelectedVersion] = useState<RecordValue | null>(null)
  const [partnerOpen, setPartnerOpen] = useState(false)
  const [partnerForm, setPartnerForm] = useState<PartnerForm>({ first_name: "", surname: "", other_name: "", email: "", mobile_number: "", gender: "", date_of_birth: "", identification_type: "", identification_number: "", nationality: "", occupation: "" })
  const [partnerSearch, setPartnerSearch] = useState("")
  const [partnerResults, setPartnerResults] = useState<PartnerListItem[]>([])
  const [partnerSearching, setPartnerSearching] = useState(false)
  const [selectedPartner, setSelectedPartner] = useState<PartnerListItem | null>(null)
  const [partnerErrors, setPartnerErrors] = useState<string[]>([])
  const [convertOpen, setConvertOpen] = useState(false)
  const [convertErrors, setConvertErrors] = useState<string[]>([])
  const [finalizeOpen, setFinalizeOpen] = useState(false)
  const [finalizeErrors, setFinalizeErrors] = useState<string[]>([])
  const [summaryOpen, setSummaryOpen] = useState(false)

  const isAllowed = useCallback((permission: string) => isSuperAdmin || canAccess(permission), [canAccess, isSuperAdmin])

  const loadDetail = useCallback(async (): Promise<QuotationDetail | null> => {
    if (!id) return null
    setLoading(true)
    try {
      const payload = await requestSnake<QuotationDetail>(`${API_PREFIX}${id}/`)
      setQuotation(payload)
      setFinancial(payload.financial_summary ? { ...payload.financial_summary, recalculation_required: false } : null)
      return payload
    } catch (error) {
      toast({ tone: "danger", title: "Unable to load quotation", message: error instanceof Error ? error.message : "The quotation detail could not be loaded." })
      return null
    } finally { setLoading(false) }
  }, [id, toast])

  const loadLifecycleData = useCallback(async (baseOverride?: QuotationDetail | null) => {
    if (!id) return
    const [summaryResult, versionsResult, partnerResult, plansResult, financialResult, membersResult, installmentsResult, fundsResult, ridersResult] = await Promise.allSettled([
      requestSnake<RecordValue>(`${API_PREFIX}${id}/wizard-summary/`),
      requestSnake<RecordValue>(`${API_PREFIX}${id}/versions/`),
      requestSnake<PartnerVerification>(`${API_PREFIX}${id}/partner-verification/`),
      requestSnake<RecordValue>(`${API_PREFIX}${id}/plan-details/`),
      requestSnake<FinancialDetails>(`${API_PREFIX}${id}/financial-details/`),
      requestSnake<RecordValue>(`${API_PREFIX}${id}/members/`),
      requestSnake<RecordValue>(`${API_PREFIX}${id}/installments/`),
      requestSnake<RecordValue>(`${API_PREFIX}${id}/investment-funds/`),
      requestSnake<RecordValue>(`${API_PREFIX}${id}/riders/`),
    ])
    const failedStages = [
      stageFailure("wizard summary", summaryResult),
      stageFailure("quotation versions", versionsResult),
      stageFailure("partner verification", partnerResult),
      stageFailure("selected plans", plansResult),
      stageFailure("financial details", financialResult),
      stageFailure("member coverage", membersResult),
      stageFailure("installments", installmentsResult),
      stageFailure("investment funds", fundsResult),
      stageFailure("riders and benefits", ridersResult),
    ].filter((message): message is string => Boolean(message))
    setStageErrors(failedStages)
    if (versionsResult.status === "fulfilled") setVersions(responseRows(versionsResult.value, "versions") as VersionRow[])
    if (partnerResult.status === "fulfilled") setPartner(partnerResult.value)
    if (financialResult.status === "fulfilled") setFinancial(financialResult.value)
    const stageResults = {
      summary: summaryResult.status === "fulfilled" ? summaryResult.value : undefined,
      partner: partnerResult.status === "fulfilled" ? partnerResult.value : undefined,
      plans: plansResult.status === "fulfilled" ? plansResult.value : undefined,
      members: membersResult.status === "fulfilled" ? membersResult.value : undefined,
      installments: installmentsResult.status === "fulfilled" ? installmentsResult.value : undefined,
      funds: fundsResult.status === "fulfilled" ? fundsResult.value : undefined,
      riders: ridersResult.status === "fulfilled" ? ridersResult.value : undefined,
      financial: financialResult.status === "fulfilled" ? financialResult.value : undefined,
    }
    setQuotation((current) => {
      const base = baseOverride ?? current
      return base ? mergeStageAggregate(base, stageResults) : current
    })
  }, [id])

  useEffect(() => {
    void (async () => {
      const base = await loadDetail()
      await loadLifecycleData(base)
    })()
  }, [loadDetail, loadLifecycleData])

  const runRevision = useCallback(async () => {
    if (!id) return
    setBusy(true)
    try {
      const response = await requestSnake<QuotationDetail>(`${API_PREFIX}${id}/revise/`, { method: "POST" })
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
    setSelectedPartner(null)
    setPartnerSearch("")
    setPartnerResults([])
    setPartnerOpen(true)
  }, [quotation])

  const searchPartners = useCallback(async (term: string) => {
    if (!term.trim()) { setPartnerResults([]); return }
    setPartnerSearching(true)
    try {
      const result = await listPartners({ search: term.trim(), per_page: 10 })
      setPartnerResults(result.results ?? [])
    } catch {
      setPartnerResults([])
    } finally {
      setPartnerSearching(false)
    }
  }, [])

  const selectPartner = useCallback(async (row: PartnerListItem) => {
    setPartnerSearching(true)
    try {
      const detail = await getPartner(row.id)
      setPartnerForm({
        first_name: detail.firstName ?? "",
        surname: detail.surname ?? "",
        other_name: detail.otherName ?? "",
        email: detail.email ?? "",
        mobile_number: detail.mobileNumber ?? "",
        gender: detail.gender ?? "",
        date_of_birth: detail.dateOfBirth ? String(detail.dateOfBirth).slice(0, 10) : "",
        identification_type: detail.identificationType ?? "",
        identification_number: detail.identificationNumber ?? "",
        nationality: detail.nationality ?? "",
        occupation: detail.occupation ?? "",
      })
      setSelectedPartner(row)
      setPartnerSearch("")
      setPartnerResults([])
    } catch {
      setSelectedPartner(null)
    } finally {
      setPartnerSearching(false)
    }
  }, [])

  const completePartner = useCallback(async () => {
    if (!id) return
    setBusy(true)
    setPartnerErrors([])
    try {
      const body = selectedPartner ? { ...partnerForm, partner_id: selectedPartner.id } : partnerForm
      const response = await requestSnake<PartnerVerification & { partner_verified?: boolean }>(`${API_PREFIX}${id}/partner-completion/`, { method: "POST", body: JSON.stringify(body) })
      setPartner((current) => ({ ...current, partner_exists: true, compliant: response.compliant ?? true, partner_verified: response.partner_verified, partner_number: response.partner_number, partner_display_name: response.partner_display_name, missing_fields: response.missing_fields ?? [] }))
      setPartnerOpen(false)
      setSelectedPartner(null)
      toast({ tone: "success", title: selectedPartner ? "Partner linked and verified" : "Partner completed and linked" })
      await loadDetail()
      await loadLifecycleData()
    } catch (error) { setPartnerErrors(errorMessages(error)) } finally { setBusy(false) }
  }, [id, loadDetail, loadLifecycleData, partnerForm, selectedPartner, toast])

  const finalize = useCallback(async () => {
    if (!id) return
    setBusy(true)
    setFinalizeErrors([])
    try {
      const response = await requestSnake<QuotationDetail>(`${API_PREFIX}${id}/finalize/`, { method: "POST" })
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
      await requestSnake(`${API_PREFIX}${id}/convert-to-proposal/`, { method: "POST", body: JSON.stringify({}) })
      toast({ tone: "success", title: "Quotation converted to proposal" })
      setConvertOpen(false)
      navigate(`/ordinary-life/proposals?quotation=${id}`)
    } catch (error) { setConvertErrors(errorMessages(error)) } finally { setBusy(false) }
  }, [eligibilityErrors, id, navigate, toast])

  const loadVersion = useCallback(async (versionNumber: number) => {
    if (!id) return
    try {
      const response = await requestSnake<RecordValue>(`${API_PREFIX}${id}/as-of-version/${versionNumber}/`)
      setSelectedVersion(response)
    } catch (error) { toast({ tone: "danger", title: "Unable to load version", message: error instanceof Error ? error.message : "The version snapshot could not be loaded." }) }
  }, [id, toast])

  const status = String(quotation?.status ?? "DRAFT")
  const currency = renderFk(quotation?.currency, quotation?.currency_display, "")
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

  const prospectName = stringValue(quotation.quote_name ?? quotation.prospect_name ?? quotation.partner_display, "Quotation")
  const linkedPartnerName = stringValue(partner?.partner_display_name ?? quotation.linked_partner_display ?? quotation.partner_display, "")
  const displayQuoteNumber = quotation.quote_number ? (quotation.quote_number.includes("-v") ? quotation.quote_number : `${quotation.quote_number}-v${quotation.current_version_number ?? 1}`) : "—"
  const firstPlan = quotation.plan_configurations?.[0] ?? {}
  const planTerm = scalarValue(firstPlan.policy_term_years) ?? scalarValue(firstPlan.term_years)
  const planPaymentPeriod = scalarValue(firstPlan.payment_period_years)
  const planSumAssured = scalarValue(firstPlan.base_sum_assured) ?? scalarValue(firstPlan.sum_assured)
  const planFrequency = scalarValue(firstPlan.premium_frequency)
  const paymentDetail = asRecord(quotation.payment_detail)
  const underwriting = asRecord(quotation.underwriting_detail)
  const beneficiaryRows = listValue(quotation.beneficiaries)
  const memberRows = listValue(quotation.members)
  const fundRows = listValue(quotation.fund_allocations)
  const riderRows = listValue(quotation.rider_selections)
  const lifeAssuredCount = memberRows.filter((member) => String(member.member_type).toUpperCase() === "LIFE_ASSURED").length
  const riderPremiumTotal = riderRows.reduce((total, rider) => total + (numberValue(rider.premium_amount) ?? numberValue(rider.premium) ?? 0), 0)
  const sumAssured = scalarValue(summary?.total_sum_assured) ?? scalarValue(quotation.total_sum_assured) ?? planSumAssured ?? null
  const basicPremium = scalarValue(summary?.base_premium) ?? scalarValue(quotation.base_premium) ?? scalarValue(quotation.total_premium) ?? scalarValue(firstPlan.premium_amount) ?? scalarValue(firstPlan.premium) ?? null
  const riderPremium = scalarValue(summary?.total_rider_premium) ?? scalarValue(summary?.rider_premium) ?? scalarValue(summary?.rider_premiums) ?? (riderPremiumTotal > 0 ? riderPremiumTotal : null)
  const basicPremiumNumber = numberValue(basicPremium)
  const riderPremiumNumber = numberValue(riderPremium)
  const totalPremium = scalarValue(summary?.total_premium) ?? scalarValue(quotation.total_premium) ?? (basicPremiumNumber !== null && riderPremiumNumber !== null ? basicPremiumNumber + riderPremiumNumber : basicPremium ?? null)
  const summaryRows: Array<[string, unknown]> = [
    ["Quote name", quotation.quote_name],
    ["Quote date", dateLabel(quotation.quote_date)],
    ["Currency", renderFk(quotation.currency, quotation.currency_display)],
    ["Identity type", renderFk(quotation.identity_type, quotation.identity_type_display)],
    ["Identity number", quotation.identity_number],
    ["Date of birth", dateLabel(quotation.date_of_birth)],
    ["Age at quote", quotation.age_at_quote],
    ["Gender", renderFk(quotation.gender, quotation.gender_display)],
    ["Smoker status", renderFk(quotation.smoker_status, quotation.smoker_status_display)],
    ["Location", renderFk(quotation.location, quotation.location_display)],
    ["Agent", renderFk(quotation.agent_partner, quotation.agent_display)],
    ["Partner", linkedPartnerName],
    ["Address", quotation.address],
    ["Status", quotation.status],
    ["Version", stringValue(quotation.current_version_number)],
    ["Expiry date", dateLabel(quotation.expiry_date)],
    ["Plan", stringValue(firstPlan.plan_name ?? firstPlan.plan_display ?? firstPlan.plan_code ?? firstPlan.plan, "—")],
    ["Sub-Product", stringValue(firstPlan.sub_product_name ?? firstPlan.sub_product_display ?? firstPlan.sub_product_code ?? firstPlan.sub_product, "—")],
    ["Policy Term", planTerm ? `${stringValue(planTerm)} years` : "—"],
    ["Payment Period", planPaymentPeriod ? `${stringValue(planPaymentPeriod)} years` : "—"],
    ["Sum Assured", moneyLabel(planSumAssured, currency)],
    ["Premium Frequency", stringValue(planFrequency, "—")],
    ["Base Premium", moneyLabel(basicPremium, currency)],
    ["Rider Premium", moneyLabel(riderPremium, currency)],
    ["Total Premium", moneyLabel(totalPremium, currency)],
    ["Total Loadings", moneyLabel(summary?.total_loading ?? summary?.total_loadings, currency)],
    ["Total Taxes", moneyLabel(summary?.total_tax ?? summary?.total_taxes, currency)],
    ["Estimated Maturity Value", moneyLabel(summary?.estimated_maturity_value, currency)],
    ["Payment Method", stringValue(paymentDetail.payment_method, "—")],
    ["Account Reference", stringValue(paymentDetail.account_reference, "—")],
    ["Risk Class", stringValue(underwriting.risk_class, "—")],
    ["Medical Underwriting", underwriting.medical_required ? "Required" : "Not required"],
    ["Members", memberRows.length ? `${stringValue(memberRows.length)} (${stringValue(lifeAssuredCount)} life assured)` : "—"],
    ["Fund Allocations", fundRows.length ? `${stringValue(fundRows.length)} allocation${fundRows.length === 1 ? "" : "s"}: ${fundRows.map((fund) => `${stringValue(fund.allocation_percentage ?? fund.allocation_percent)}%`).join(" + ")}` : "—"],
    ["Riders", riderRows.length ? `${stringValue(riderRows.length)} selected` : "—"],
    ["Beneficiaries", beneficiaryRows.length ? `${stringValue(beneficiaryRows.length)}: ${beneficiaryRows.map((b) => `${stringValue(b.name ?? b.relationship)} ${stringValue(b.percentage)}%`).join(" + ")}` : "—"],
  ]
  const compactSummaryRows = summaryRows.filter(([label]) => ["Quote name", "Quote date", "Currency", "Identity number", "Location", "Plan", "Policy Term", "Premium Frequency", "Total Premium", "Members"].includes(String(label)))
  const visibleTabs: Array<{ id: DetailTab; label: string }> = [
    { id: "overview", label: "Overview" },
    { id: "plans", label: "Plans & Sub-Products" },
    { id: "members", label: "Member Coverage" },
    { id: "funds", label: "Investment Funds" },
    { id: "riders", label: "Riders" },
    { id: "financials", label: "Projections" },
    { id: "installments", label: "Installment Payouts" },
    { id: "versions", label: "Quote Versions" },
    { id: "documents", label: "Documents" },
  ]

  return <div className="ol-detail-page space-y-4 p-3 sm:p-4 md:p-5">
    <section className="ol-detail-header surface-card overflow-hidden">
      <div className="flex flex-wrap items-start justify-between gap-4 px-5 py-4">
        <div className="flex min-w-0 items-start gap-3"><span className="ol-detail-doc-icon"><FileText size={20} aria-hidden="true" /></span><div className="min-w-0"><h1 className="truncate text-2xl font-bold tracking-tight">{prospectName}</h1><div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-[var(--muted-foreground)]"><span>{quotation.quote_number ?? displayQuoteNumber}</span><span className="text-[var(--muted-foreground)]">-v{quotation.current_version_number ?? 1}</span><StatusBadge value="Latest" tone="success" /><StatusBadge value={status === "CONVERTED" ? "Converted" : "Not Converted"} tone={status === "CONVERTED" ? "info" : "neutral"} /><span className="inline-flex items-center gap-1"><FileText size={12} aria-hidden="true" />{dateLabel(quotation.quote_date)}</span></div></div></div>
        <div className="flex flex-wrap justify-end gap-2"><button type="button" className="button-secondary" onClick={() => navigate("/ordinary-life/quotations")}><ArrowLeft size={15} aria-hidden="true" />Back to Quote Listing</button>{status === "DRAFT" && isAllowed("ol_quotations.update") && <button type="button" className="button-secondary" onClick={() => navigate(`/ordinary-life/quotations/${id}/edit`)}><Pencil size={15} aria-hidden="true" />Edit</button>}{canConvert && <button type="button" className="button-secondary border-emerald-300 text-emerald-700" onClick={() => { setConvertErrors([]); setConvertOpen(true) }}><FileCheck2 size={15} aria-hidden="true" />Convert to Proposal</button>}{canPrint && <button type="button" className="button-secondary border-sky-300 text-sky-700" onClick={() => setActiveTab("documents")} disabled={busy}><Download size={15} aria-hidden="true" />Print Quote</button>}
</div>
      </div>
      <div className="grid gap-3 border-t px-4 py-4 sm:grid-cols-2 xl:grid-cols-4"><article className="ol-detail-kpi ol-detail-kpi-green"><span className="ol-detail-kpi-icon">▰</span><strong>{moneyLabel(sumAssured, currency)}</strong><small>Total Sum Assured</small></article><article className="ol-detail-kpi ol-detail-kpi-blue"><span className="ol-detail-kpi-icon">▣</span><strong>{moneyLabel(basicPremium, currency)}</strong><small>Total Basic Premium</small></article><article className="ol-detail-kpi ol-detail-kpi-purple"><span className="ol-detail-kpi-icon">＋</span><strong>{moneyLabel(riderPremium, currency)}</strong><small>Total Rider Premium</small></article><article className="ol-detail-kpi ol-detail-kpi-amber"><span className="ol-detail-kpi-icon">◈</span><strong>{moneyLabel(totalPremium, currency)}</strong><small>Total Premium</small></article></div><div className="flex justify-end px-5 pb-3"><button type="button" className="text-xs font-semibold text-[var(--muted-foreground)] underline underline-offset-2" onClick={() => setActiveTab("overview")}>More Details</button></div>
    </section>
    <nav className="ol-detail-tabs surface-card flex gap-1 overflow-x-auto p-1" aria-label="Quotation detail tabs">{visibleTabs.map((tab) => <button type="button" key={tab.id} onClick={() => setActiveTab(tab.id)} className={`whitespace-nowrap rounded-[8px] px-4 py-2.5 text-sm font-semibold transition ${activeTab === tab.id ? "bg-white text-[var(--foreground)] shadow-sm dark:bg-[var(--muted)]" : "text-[var(--muted-foreground)] hover:bg-[var(--secondary)]"}`} aria-current={activeTab === tab.id ? "page" : undefined}>{tab.label}</button>)}</nav>
    <section className="space-y-4">{quotation.approval_required && <div className="flex items-start gap-3 rounded-[10px] border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950" role="alert"><CircleAlert className="mt-0.5 shrink-0" size={18} aria-hidden="true" /><div><p className="font-bold">Approval required</p><p className="mt-1">{stringValue(quotation.approval_reason, "This quotation requires approval before downstream conversion.")}</p></div></div>}      {partner && partner.compliant && quotation.partner_verified === true && <div className="flex flex-wrap items-center gap-3 rounded-[10px] border border-emerald-300 bg-emerald-50 px-4 py-3 text-sm text-emerald-950" role="status"><ShieldCheck className="shrink-0" size={18} aria-hidden="true" /><div><p className="font-bold">Partner verified</p><p className="mt-1">{linkedPartnerName || "The compliant partner is linked to this quotation."}{partner.partner_number ? ` · ${partner.partner_number}` : ""}</p></div></div>}{partner && (!partner.compliant || quotation.partner_verified !== true) && <InfoBanner title="Partner verification pending"><div className="flex flex-wrap items-center justify-between gap-3"><span>{partner.partner_exists ? "A matching partner exists but is not compliant." : "No compliant partner is linked to this quotation."}{partner.missing_fields?.length ? ` Missing: ${partner.missing_fields.join(", ")}.` : " Complete the required KYC fields, save the partner, then verify again before conversion."}</span><button type="button" className="button-primary" onClick={openPartner}><UserRound size={16} aria-hidden="true" />Complete partner</button></div></InfoBanner>}

      {stageErrors.length > 0 && <div className="rounded-[10px] border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950" role="alert"><p className="font-bold">Some quotation detail data needs attention</p><p className="mt-1">The quotation header loaded, but one or more supporting sections could not be retrieved.</p><ul className="mt-2 list-disc space-y-1 pl-5">{stageErrors.map((error) => <li key={error}>{error}</li>)}</ul><button type="button" className="button-secondary mt-3" onClick={() => void loadLifecycleData()}>Retry detail data</button></div>}
      {activeTab === "overview" && <div className="space-y-4"><StepChecklist completion={completion} onJump={jumpTo} /><div className="grid gap-4 lg:grid-cols-2"><section className="surface-card p-4"><h2 className="mb-3 font-bold">Quotation summary</h2><SummaryGrid rows={compactSummaryRows} /><button type="button" className="button-secondary mt-4 w-full justify-center" onClick={() => setSummaryOpen(true)}><Eye size={15} aria-hidden="true" />Show full summary</button></section><section className="surface-card p-4"><h2 className="mb-3 font-bold">Review actions</h2><div className="space-y-3">{canFinalize && <button type="button" className="button-primary w-full justify-center" onClick={() => { setFinalizeErrors([]); setFinalizeOpen(true) }}><Check size={16} aria-hidden="true" />Finalize quotation</button>}{canConvert && <button type="button" className="button-secondary w-full justify-center" onClick={() => { setConvertErrors([]); setConvertOpen(true) }}><ChevronRight size={16} aria-hidden="true" />Convert to proposal</button>}<button type="button" className="button-secondary w-full justify-center" onClick={() => setVersionsOpen(true)}><History size={16} aria-hidden="true" />View versions</button></div></section></div></div>}
      {activeTab === "plans" && <PlansTab rows={listValue(quotation.plan_configurations)} currency={currency} />}
      {activeTab === "members" && <MembersTab rows={listValue(quotation.members)} />}
      {activeTab === "installments" && <InstallmentPayoutsTab rows={listValue(quotation.installment_configurations)} payouts={payouts} summary={summary} currency={currency} />}
      {activeTab === "funds" && <FundsTab rows={listValue(quotation.fund_allocations)} currency={currency} />}
      {activeTab === "riders" && <RidersTab rows={listValue(quotation.rider_selections)} benefits={listValue(quotation.benefits)} currency={currency} />}
      {activeTab === "financials" && <ProjectionsTab financial={financial} summary={summary} projections={projections} currency={currency} recalculationRequired={Boolean(financial?.recalculation_required)} onCalculate={async () => { if (!id) return; setBusy(true); try { const response = await requestSnake<FinancialDetails>(`${API_PREFIX}${id}/calculate/`, { method: "POST", body: JSON.stringify({}) }); setFinancial(response); toast({ tone: "success", title: "Financial details recalculated" }); await loadDetail() } catch (error) { toast({ tone: "danger", title: "Calculation failed", message: error instanceof Error ? error.message : "The rating engine rejected the calculation." }) } finally { setBusy(false) } }} busy={busy} />}
      {activeTab === "versions" && <VersionsTab versions={versions} currency={currency} onOpenDrawer={() => setVersionsOpen(true)} onView={(version) => void loadVersion(version)} />}
      {activeTab === "documents" && id && <DocumentInstancesPanel sourceType="ol_quotations.olquotation" objectId={id} documentType="OL_QUOTATION" title="Quotation documents" renderLabel="Generate quotation PDF" fallbackDocumentEndpoint={`${API_PREFIX}${id}/documents/`} />}
    </section>

    <Drawer open={versionsOpen} title="Quotation versions" description="Review historical snapshots or revise from the current finalized version." onClose={() => setVersionsOpen(false)} width="max-w-2xl"><div className="space-y-3">{versions.length === 0 ? <TableEmpty message="No versions are available." /> : versions.map((version) => <article key={String(version.id ?? version.version_number)} className="rounded-[10px] border p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-bold">Version {stringValue(version.version_number)}</p><p className="mt-1 text-xs text-[var(--muted-foreground)]">{dateLabel(version.created_at)} · {renderFk(version.created_by, version.created_by_display, "System")}</p><p className="mt-2 text-sm">{stringValue(version.change_reason, "No change reason recorded.")}</p></div><StatusBadge value={String(version.status ?? "Superseded")} tone={String(version.status).toUpperCase() === "CURRENT" ? "success" : "neutral"} /></div><div className="mt-3 flex gap-2"><button type="button" className="button-secondary" onClick={() => void loadVersion(Number(version.version_number))}><Eye size={15} aria-hidden="true" />Switch view</button>{hasRevision && <button type="button" className="button-secondary" onClick={() => void runRevision()}><Pencil size={15} aria-hidden="true" />Open revise</button>}</div></article>)}</div>{selectedVersion && <div className="mt-5 rounded-[10px] border bg-[var(--muted)]/35 p-4"><div className="mb-2 flex items-center justify-between"><h3 className="font-bold">Version {stringValue(selectedVersion.version_number)} snapshot</h3><button type="button" aria-label="Close version snapshot" className="rounded-md p-1 hover:bg-[var(--secondary)]" onClick={() => setSelectedVersion(null)}><X size={16} aria-hidden="true" /></button></div><pre className="max-h-80 overflow-auto whitespace-pre-wrap text-xs leading-5">{JSON.stringify(sanitizeForDisplay(selectedVersion.snapshot ?? selectedVersion), null, 2)}</pre></div>}</Drawer>

    <Modal open={partnerOpen} title="Complete partner verification" description="Complete the missing compliant-partner fields before conversion." onClose={() => { if (!busy) setPartnerOpen(false) }} footer={<><button type="button" className="button-secondary" onClick={() => setPartnerOpen(false)} disabled={busy}>Cancel</button><button type="button" className="button-primary" onClick={() => void completePartner()} disabled={busy}>{busy ? (selectedPartner ? "Linking…" : "Saving…") : (selectedPartner ? "Link and verify" : "Save and verify")}</button></>}>
      {partnerErrors.length > 0 && <div className="mb-4 space-y-1 rounded-[10px] border border-red-200 bg-red-50 p-3 text-sm text-red-900" role="alert">{partnerErrors.map((error) => <p key={error}>{error}</p>)}</div>}
      <div className="mb-4 rounded-[10px] border border-[var(--border)] bg-[var(--secondary)] p-3">
        <p className="mb-2 text-sm font-semibold">Link an existing partner</p>
        <div className="flex gap-2">
          <input name="partner-search" aria-label="Search existing partner" placeholder="Search by partner number or name…" value={partnerSearch} onChange={(event) => { setPartnerSearch(event.target.value); if (selectedPartner) setSelectedPartner(null) }} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); void searchPartners(partnerSearch) } }} className="h-10 w-full rounded-[10px] border bg-[var(--card)] px-3 text-sm text-[var(--foreground)] shadow-sm outline-none transition placeholder:text-[var(--muted-foreground)] focus:border-[var(--ring)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)]" />
          <button type="button" className="button-secondary" onClick={() => void searchPartners(partnerSearch)} disabled={partnerSearching}>{partnerSearching ? "Searching…" : "Search"}</button>
        </div>
        {selectedPartner && <div className="mt-2 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-2 text-sm text-emerald-900"><span className="inline-flex items-center gap-1"><Check size={14} aria-hidden="true" /><strong>{selectedPartner.displayName}</strong> · {selectedPartner.partnerNumber}</span><button type="button" className="text-xs font-semibold underline underline-offset-2" onClick={() => { setSelectedPartner(null); setPartnerResults([]) }}>Change</button></div>}
        {!selectedPartner && partnerResults.length > 0 && <ul className="mt-2 max-h-48 space-y-1 overflow-y-auto">{partnerResults.map((row) => <li key={row.id}><button type="button" className="flex w-full items-start justify-between gap-3 rounded-lg border bg-[var(--card)] px-3 py-2 text-left transition hover:border-[var(--primary)]" onClick={() => void selectPartner(row)}><span className="min-w-0"><span className="block truncate text-sm font-bold">{row.displayName}</span><span className="block text-xs text-[var(--muted-foreground)]">{row.partnerNumber} · {row.email || "no email"}</span></span><span className="shrink-0 rounded-full bg-emerald-100 px-2 py-1 text-[11px] font-bold text-emerald-700">{row.status}</span></button></li>)}</ul>}
        {!selectedPartner && partnerSearch.trim() && partnerResults.length === 0 && !partnerSearching && <p className="mt-2 text-xs text-[var(--muted-foreground)]">No existing partner matched "{partnerSearch}". Fill the fields below to create a new partner instead.</p>}
      </div>
      <FormGrid columns={2}>{(["first_name", "surname", "other_name", "email", "mobile_number", "nationality", "occupation", "identification_number"] as const).map((field) => <TextInput key={field} label={field.replace(/_/g, " ").replace(/\b\w/g, (letter: string) => letter.toUpperCase())} name={field} value={partnerForm[field]} onChange={(event) => setPartnerForm((current) => ({ ...current, [field]: event.target.value }))} required={field === "first_name" || field === "surname" || field === "identification_number"} />)}<SmartSelect entity="identity-types" label="Identification type" name="identification_type" value={partnerForm.identification_type} onChange={(value) => setPartnerForm((current) => ({ ...current, identification_type: value }))} required placeholder="Select identification type" /><SelectInput label="Gender" name="gender" value={partnerForm.gender} onChange={(event) => setPartnerForm((current) => ({ ...current, gender: event.target.value }))}><option value="">Select gender</option><option value="MALE">Male</option><option value="FEMALE">Female</option></SelectInput><DateInput label="Date of birth" name="date_of_birth" value={partnerForm.date_of_birth} onChange={(event) => setPartnerForm((current) => ({ ...current, date_of_birth: event.target.value }))} /></FormGrid>
    </Modal>

    <Modal open={convertOpen} title="Convert to Proposal" description="The quotation must satisfy BR-01 before handoff to OL Proposals." onClose={() => setConvertOpen(false)} footer={<><button type="button" className="button-secondary" onClick={() => setConvertOpen(false)} disabled={busy}>Close</button><button type="button" className="button-primary" onClick={() => void convertToProposal()} disabled={busy}>{busy ? "Converting…" : "Convert to Proposal"}</button></>}>
      {eligibilityErrors.length || convertErrors.length ? <div className="space-y-2 rounded-[10px] border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950" role="alert"><p className="font-bold">Conversion is blocked</p>{[...eligibilityErrors, ...convertErrors].map((error) => <p key={error}>• {error}</p>)}</div> : <InfoBanner title="Ready for conversion">Partner verification, quotation finalization, expiry, and approval checks have passed.</InfoBanner>}
    </Modal>

    <Modal open={summaryOpen} title="Full quotation summary" description="Complete snapshot of the quotation and its selected plan configuration." onClose={() => setSummaryOpen(false)} size="xl" footer={<button type="button" className="button-secondary" onClick={() => setSummaryOpen(false)}>Close</button>}><SummaryGrid rows={summaryRows} className="sm:grid-cols-2 lg:grid-cols-3" /></Modal>

    <ConfirmModal open={finalizeOpen} title="Finalize quotation" description="Finalize this quotation? It will become read-only until revised." confirmLabel="Finalize" onClose={() => setFinalizeOpen(false)} onConfirm={() => void finalize()} tone="primary" />
    {finalizeErrors.length > 0 && <div className="fixed bottom-5 right-5 z-40 max-w-md rounded-[10px] border border-red-200 bg-red-50 p-4 text-sm text-red-900 shadow-xl" role="alert"><div className="flex items-start justify-between gap-3"><p className="font-bold">Finalization blocked</p><button type="button" aria-label="Dismiss finalization errors" onClick={() => setFinalizeErrors([])}><X size={16} aria-hidden="true" /></button></div>{finalizeErrors.map((error) => <button type="button" className="mt-2 block text-left underline" key={error} onClick={() => { setFinalizeErrors([]); jumpTo("financial") }}>{error}</button>)}</div>}
  </div>
}

function DetailTableToolbar({ label }: { label: string }) {
  return <div className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3"><label className="sr-only" htmlFor={`detail-search-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}>Search {label}</label><select aria-label="Rows per page" defaultValue="10" className="h-9 rounded-[8px] border bg-[var(--card)] px-3 text-sm"><option value="10">10 entries</option><option value="25">25 entries</option><option value="50">50 entries</option></select><input id={`detail-search-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`} aria-label={`Search ${label}`} placeholder="Search..." className="h-9 w-full max-w-[190px] rounded-[8px] border bg-[var(--card)] px-3 text-sm outline-none focus:border-[var(--ring)]" /></div>
}

function DetailTableFooter() {
  return <div className="flex flex-wrap items-center justify-between gap-3 border-t px-4 py-3 text-xs text-[var(--muted-foreground)]"><span>Showing Page 1 of 1</span><div className="flex items-center gap-1"><button type="button" className="rounded-[8px] border px-3 py-1.5 disabled:opacity-50" disabled>Previous</button><button type="button" className="rounded-[8px] bg-[var(--primary)] px-3 py-1.5 font-bold text-white" aria-current="page">1</button><button type="button" className="rounded-[8px] border px-3 py-1.5 disabled:opacity-50" disabled>Next</button></div></div>
}

function PlansTab({ rows, currency }: { rows: RecordValue[]; currency?: unknown }) {
  return <div className="surface-card overflow-hidden"><DetailTableToolbar label="plans and sub-products" /><div className="overflow-x-auto"><table className="w-full min-w-[1180px] text-left text-sm"><caption className="sr-only">Plans and sub-products</caption><thead className="bg-[var(--muted)]/35 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><tr><th className="px-4 py-3">No.</th><th className="px-4 py-3">Plan</th><th className="px-4 py-3">Sub-Product</th><th className="px-4 py-3">Policy Term</th><th className="px-4 py-3">Payment Period</th><th className="px-4 py-3">Sum Assured</th><th className="px-4 py-3">Premium</th><th className="px-4 py-3">Total Premium</th><th className="px-4 py-3">Actions</th></tr></thead><tbody className="divide-y divide-[var(--border)]">{rows.map((row, index) => <tr key={String(row.id ?? index)}><Td>{index + 1}</Td><Td className="font-semibold">{cell(row, "plan_name", "plan_display", "plan_code", "plan")}</Td><Td>{cell(row, "sub_product_name", "sub_product_display", "sub_product_code", "sub_product")}</Td><Td>{cell(row, "policy_term_years", "term_years")} years</Td><Td>{cell(row, "payment_period_years")} (years)</Td><Td>{moneyLabel(row.base_sum_assured ?? row.sum_assured, currency)}</Td><Td>{moneyLabel(row.premium_amount ?? row.premium, currency)} {row.premium_frequency ? `(${cell(row, "premium_frequency")})` : ""}</Td><Td className="font-semibold text-[var(--success)]">{moneyLabel(row.total_premium ?? row.gross_premium, currency)}</Td><Td>—</Td></tr>)}</tbody></table></div><DetailTableFooter /></div>
}

function MembersTab({ rows }: { rows: RecordValue[] }) {
  if (rows.length === 0) return <TableEmpty message="No members are recorded for this quotation." />
  return <div className="surface-card overflow-hidden"><div className="border-b px-4 py-3"><h2 className="font-bold">{cell(rows[0], "plan_name", "plan_display", "plan_code", "plan")}</h2></div><div className="overflow-x-auto"><table className="w-full min-w-[1050px] text-left text-sm"><caption className="sr-only">Quotation member coverage</caption><thead className="bg-[var(--muted)]/35 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><tr><th className="px-4 py-3">Member Name</th><th className="px-4 py-3">Age</th><th className="px-4 py-3">Gender</th><th className="px-4 py-3">Coverage %</th><th className="px-4 py-3">Sum Assured</th><th className="px-4 py-3">Basic Premium</th><th className="px-4 py-3">Rider Premium</th><th className="px-4 py-3">Total Premium</th></tr></thead><tbody className="divide-y divide-[var(--border)]">{rows.map((row, index) => <tr key={String(row.id ?? index)}><Td><span className="font-semibold">{cell(row, "full_name", "member_name", "name")}</span>{row.is_principal || String(row.member_type).toUpperCase() === "POLICYHOLDER" ? <StatusBadge value="Principal" tone="info" className="ml-2" /> : null}</Td><Td>{cell(row, "age_at_quote", "age")}</Td><Td>{cell(row, "gender")}</Td><Td>{cell(row, "coverage_percent", "coverage_percentage", "coverage")} %</Td><Td>{moneyLabel(row.member_sum_assured ?? row.sum_assured, row.currency)}</Td><Td>{moneyLabel(row.basic_premium, row.currency)}</Td><Td>{moneyLabel(row.rider_premium, row.currency)}</Td><Td className="font-semibold text-[var(--success)]">{moneyLabel(row.total_premium, row.currency)}</Td></tr>)}</tbody></table></div></div>
}

function InstallmentsTab({ rows, currency }: { rows: RecordValue[]; currency?: unknown }) {
  if (rows.length === 0) return <TableEmpty message="No installment configurations are recorded." />
  return <DataTableShell caption="Quotation installments"><TableHead><Th>Plan</Th><Th>Policy term</Th><Th>Payment mode</Th><Th>Installments</Th><Th>Status</Th><Th>Benefits</Th></TableHead><tbody>{rows.map((row, index) => <tr key={String(row.id ?? index)}><Td>{cell(row, "plan_name", "plan_display", "plan", "sub_product_code")}</Td><Td>{cell(row, "policy_term_years", "term_years")} years</Td><Td>{cell(row, "payment_mode", "frequency", "premium_frequency")}</Td><Td>{cell(row, "total_number_of_installments", "installment_count")}</Td><Td><StatusBadge value={String(row.status ?? "Configured")} tone={String(row.status).toUpperCase() === "CONFIGURED" ? "success" : "neutral"} /></Td><Td>{[row.after_maturity_benefits ? "After maturity" : "", row.before_maturity_benefits ? "Before maturity" : ""].filter(Boolean).join(" · ") || "—"}{currency ? ` · ${String(currency)}` : ""}</Td></tr>)}</tbody></DataTableShell>
}

function FundsTab({ rows, currency }: { rows: RecordValue[]; currency?: unknown }) {
  if (rows.length === 0) return <TableEmpty message="No investment-fund allocations are recorded." />
  return <DataTableShell caption="Quotation investment funds"><TableHead><Th>Fund</Th><Th>Fund type</Th><Th>Risk profile</Th><Th>Currency</Th><Th>Allocation</Th><Th>Amount</Th></TableHead><tbody>{rows.map((row, index) => <tr key={String(row.id ?? index)}><Td>{cell(row, "fund_name", "investment_fund_name", "fund_display", "fund")}</Td><Td>{cell(row, "fund_type", "fund_type_display")}</Td><Td>{cell(row, "risk_profile")}</Td><Td>{cell(row, "currency", "fund_currency", "currency_display")}</Td><Td>{cell(row, "allocation_percent", "allocation_percentage")} %</Td><Td>{moneyLabel(row.allocated_amount ?? row.allocation_amount, currency ?? row.currency)}</Td></tr>)}</tbody></DataTableShell>
}

function RidersTab({ rows, benefits, currency }: { rows: RecordValue[]; benefits: RecordValue[]; currency?: unknown }) {
  if (rows.length === 0 && benefits.length === 0) return <TableEmpty message="No riders or benefit selections are recorded for this quotation." />
  const benefitLabel = (row: RecordValue) => { const amount = row.rider_benefit ?? row.benefit_amount ?? row.sum_assured ?? row.value; const basis = String(row.benefit_basis ?? row.basis ?? row.calculation_basis ?? "").replace(/_/g, " "); const ratio = row.benefit_ratio ?? row.ratio; if (ratio !== undefined && ratio !== null && ratio !== "") return `Ratio based (${ratio}%)`; return amount === undefined || amount === null || amount === "" ? `—${basis ? ` (${basis})` : ""}` : `${moneyLabel(amount, currency)}${basis ? ` (${basis})` : ""}` }
  return <div className="surface-card overflow-hidden"><DetailTableToolbar label="riders" /><div className="overflow-x-auto"><table className="w-full min-w-[900px] text-left text-sm"><caption className="sr-only">Quotation riders</caption><thead className="bg-[var(--muted)]/35 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><tr><th className="px-4 py-3">No.</th><th className="px-4 py-3">Rider</th><th className="px-4 py-3">Plan</th><th className="px-4 py-3">Sub Product</th><th className="px-4 py-3">Rider Benefit</th></tr></thead><tbody className="divide-y divide-[var(--border)]">{rows.map((row, index) => <tr key={String(row.id ?? index)}><Td>{index + 1}</Td><Td className="font-semibold">{cell(row, "rider_name", "rider_display", "name", "rider_code")}</Td><Td>{cell(row, "plan_name", "plan_display", "plan_code", "plan")}</Td><Td>{cell(row, "sub_product_name", "sub_product_display", "sub_product_code", "sub_product")}</Td><Td>{benefitLabel(row)}</Td></tr>)}</tbody></table></div><DetailTableFooter />{benefits.length > 0 && <p className="border-t px-4 py-3 text-xs text-[var(--muted-foreground)]">{benefits.length} benefit configuration{benefits.length === 1 ? "" : "s"} included.</p>}</div>
}

function ProjectionsTab({ financial, summary, projections, currency, recalculationRequired, onCalculate, busy }: { financial: FinancialDetails | null; summary: RecordValue | null; projections: RecordValue[]; currency?: unknown; recalculationRequired: boolean; onCalculate: () => Promise<void>; busy: boolean }) {
  if (!financial || !summary) return <div className="space-y-4"><InfoBanner title="Financial details not calculated">Calculate the quotation to load backend rating outputs and projections.</InfoBanner><button type="button" className="button-primary" onClick={() => void onCalculate()} disabled={busy}>{busy ? "Calculating…" : "Calculate financial details"}</button></div>
  const planName = String(summary.plan_name ?? summary.product_name ?? "Quotation projection")
  const financialCards = [
    ["Base premium", summary.base_premium],
    ["Rider premium", summary.total_rider_premium ?? summary.rider_premium ?? summary.rider_premiums],
    ["Loadings", summary.total_loading ?? summary.total_loadings],
    ["Discounts", summary.total_discount ?? summary.total_discounts],
    ["Taxes", summary.total_tax ?? summary.total_taxes],
    ["Total premium", summary.total_premium],
    ["Estimated maturity value", summary.estimated_maturity_value],
  ] as const
  return <div className="surface-card overflow-hidden"><div className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3"><div className="flex items-center gap-2"><ChevronRight size={15} className="rotate-90 text-[var(--muted-foreground)]" aria-hidden="true" /><h2 className="font-bold">{planName}</h2></div><div className="flex gap-2"><StatusBadge value={String(summary.plan_type ?? "Whole Life")} tone="success" /><StatusBadge value={String(summary.payment_count ?? projections.length ?? 0) + " Payments"} tone="neutral" /></div></div><div className="grid gap-3 border-b px-4 py-4 sm:grid-cols-2 lg:grid-cols-4">{financialCards.map(([label, value]) => <article key={label} className="rounded-[10px] border bg-[var(--muted)]/20 p-3"><p className="text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">{label}</p><p className="mt-1 font-extrabold">{moneyLabel(value, currency)}</p></article>)}</div><div className="overflow-x-auto p-3"><table className="w-full min-w-[1040px] text-left text-sm"><caption className="sr-only">Policy year projections</caption><thead className="bg-[var(--muted)]/35 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><tr><th className="px-3 py-3">Payment</th><th className="px-3 py-3">Year</th><th className="px-3 py-3">Date</th><th className="px-3 py-3">Basic Premium</th><th className="px-3 py-3">Adjusted Basic</th><th className="px-3 py-3">Rider Premium</th><th className="px-3 py-3">Adjusted Rider</th><th className="px-3 py-3">Savings</th><th className="px-3 py-3">Commission</th><th className="px-3 py-3">Net Premium</th></tr></thead><tbody className="divide-y divide-[var(--border)]">{projections.map((row, index) => <tr key={String(row.policy_year ?? index)}><Td>{index + 1}</Td><Td>{cell(row, "policy_year", "year")}</Td><Td>{dateLabel(row.date ?? row.payment_date ?? row.payout_date)}</Td><Td>{moneyLabel(row.basic_premium ?? row.premiums_paid, currency)}</Td><Td>{moneyLabel(row.adjusted_basic_premium ?? row.basic_premium ?? row.premiums_paid, currency)}</Td><Td>{moneyLabel(row.rider_premium, currency)}</Td><Td>{moneyLabel(row.adjusted_rider_premium ?? row.rider_premium, currency)}</Td><Td>{moneyLabel(row.savings, currency)}</Td><Td>{moneyLabel(row.commission, currency)}</Td><Td className="font-semibold">{moneyLabel(row.net_premium ?? row.premiums_paid, currency)}</Td></tr>)}</tbody></table></div><p className="px-4 pb-4 text-xs text-[var(--muted-foreground)]">Generated {dateLabel(financial.calculated_at ?? financial.created_at)}</p>{recalculationRequired && <div className="mx-4 mb-4 rounded-[10px] border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950" role="alert">Inputs changed after the last calculation. Recalculate before finalizing.</div>}</div>
}

function InstallmentPayoutsTab({ rows, payouts, summary, currency }: { rows: RecordValue[]; payouts: RecordValue[]; summary: RecordValue | null; currency?: unknown }) {
  if (payouts.length === 0 && rows.length === 0) return <TableEmpty message="No installment configuration or payout schedule is recorded for this quotation." />
  if (payouts.length === 0) return <div className="space-y-3"><InfoBanner title="Installment payout schedule not generated">The saved installment configuration is available below. Configure payout rows in the quotation wizard or recalculate the quotation to generate the payout schedule.</InfoBanner><InstallmentsTab rows={rows} currency={currency} /></div>
  const planName = String(rows[0]?.plan_name ?? rows[0]?.plan_display ?? rows[0]?.plan ?? "Quotation installment plan")
  const maturity = summary?.estimated_maturity_value
  const schedule = String(rows[0]?.payment_mode ?? rows[0]?.frequency ?? "Annual")
  const annuity = String(rows[0]?.annuity_period_years ?? 1)
  return <div className="surface-card overflow-hidden"><div className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3"><h2 className="font-bold">{planName}</h2><div className="flex gap-4 text-xs text-[var(--muted-foreground)]"><span>{payouts.length} installments ({schedule})</span><span>Annuity Period: {annuity} years</span></div></div><div className="grid gap-3 border-b px-4 py-4 sm:grid-cols-2"><div><p className="text-xs text-[var(--muted-foreground)]">Estimated Maturity Value</p><p className="mt-1 font-extrabold text-[var(--success)]">{moneyLabel(maturity, currency)}</p></div><div><p className="text-xs text-[var(--muted-foreground)]">Payment Schedule</p><StatusBadge value={String(rows[0]?.after_maturity_benefits ? "After Maturity" : rows[0]?.before_maturity_benefits ? "Before Maturity" : "Configured")} tone="warning" /></div></div><div className="overflow-x-auto p-3"><table className="w-full min-w-[760px] text-left text-sm"><caption className="sr-only">Installment payout schedule</caption><thead className="bg-[var(--muted)]/35 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><tr><th className="px-3 py-3">#</th><th className="px-3 py-3">Description</th><th className="px-3 py-3">Installment Rate</th><th className="px-3 py-3">Installment Payout</th><th className="px-3 py-3">Paid Up Rate</th></tr></thead><tbody className="divide-y divide-[var(--border)]">{payouts.map((row, index) => <tr key={String(row.sequence ?? index)}><Td>{cell(row, "sequence")}</Td><Td>{cell(row, "description")}</Td><Td>{cell(row, "rate_percent", "rate")} %</Td><Td className="font-semibold">{moneyLabel(row.payout_amount, currency)}</Td><Td>{cell(row, "paid_up_rate")} %</Td></tr>)}</tbody></table></div></div>
}

function VersionsTab({ versions, currency, onOpenDrawer, onView }: { versions: VersionRow[]; currency?: unknown; onOpenDrawer: () => void; onView: (version: number) => void }) {
  if (versions.length === 0) return <div className="space-y-3"><TableEmpty message="No quotation versions are available yet." /><button type="button" className="button-secondary" onClick={onOpenDrawer}><History size={15} aria-hidden="true" />Open versions drawer</button></div>
  return <div className="surface-card overflow-hidden"><div className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3"><div><h2 className="font-bold">Quote Versions</h2><p className="text-xs text-[var(--muted-foreground)]">Historical quotation snapshots are preserved.</p></div><button type="button" className="button-secondary" onClick={onOpenDrawer}><History size={15} aria-hidden="true" />Open versions drawer</button></div><DetailTableToolbar label="quote versions" /><div className="overflow-x-auto"><table className="w-full min-w-[980px] text-left text-sm"><caption className="sr-only">Quote versions</caption><thead className="bg-[var(--muted)]/35 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><tr><th className="px-4 py-3">Version</th><th className="px-4 py-3">Quote Number</th><th className="px-4 py-3">Sum Assured</th><th className="px-4 py-3">Gross Premium</th><th className="px-4 py-3">Created Date</th><th className="px-4 py-3">Created By</th><th className="px-4 py-3">Actions</th></tr></thead><tbody className="divide-y divide-[var(--border)]">{versions.map((version, index) => { const current = String(version.status ?? "").toUpperCase() === "CURRENT"; return <tr key={String(version.id ?? index)}><Td><span className="rounded-[6px] bg-emerald-100 px-2 py-1 text-xs font-extrabold text-emerald-700">v{stringValue(version.version_number, "1")}</span>{current ? <span className="ml-2 text-amber-500" aria-label="Current version">★</span> : null}{current ? <span className="ml-1 text-xs text-[var(--muted-foreground)]">(Current)</span> : null}<span className="sr-only">{cell(version, "change_reason")}</span></Td><Td className="font-semibold text-[var(--primary)]">{cell(version, "quote_number")}</Td><Td>{moneyLabel(version.sum_assured ?? version.total_sum_assured, version.currency ?? currency)}</Td><Td className="font-semibold text-[var(--primary)]">{moneyLabel(version.gross_premium ?? version.total_premium, version.currency ?? currency)}</Td><Td>{dateLabel(version.created_at)}</Td><Td>{cell(version, "created_by", "created_by_name")}</Td><Td>{current ? <button type="button" className="button-secondary text-xs" aria-label="View" onClick={() => onView(Number(version.version_number))}>Current View</button> : <button type="button" className="button-secondary" onClick={() => onView(Number(version.version_number))}><Eye size={14} aria-hidden="true" />View</button>}</Td></tr>})}</tbody></table></div><DetailTableFooter /></div>
}


export { default as OLQuotationWizard } from "./OLQuotationWizard"

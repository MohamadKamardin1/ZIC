import {
  CalendarClock,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  FileText,
  Layers3,
  LoaderCircle,
  MapPin,
  PanelLeft,
  Pencil,
  Plus,
  RotateCcw,
  Save,
  Search,
  ShieldCheck,
  Trash2,
  UserRound,
  UsersRound,
  WalletCards,
  X,
} from "lucide-react"
import { useCallback, useEffect, useMemo, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { ApiClientError, request } from "../../lib/apiClient"
import { useAccess } from "../../lib/access"
import { useToast } from "../../components/ui/Toast"
import {
  DateInput,
  DecimalInput,
  FieldLabel,
  FormGrid,
  ReadOnlyField,
  SearchableSelect,
  SelectInput,
  TextInput,
  TextareaInput,
  Toggle,
} from "../../components/ui/FormControls"
import type { FilterOption } from "../../components/ui/types"
import { InfoBanner, Modal } from "../../components/ui/Overlays"
import { QuickCreateModal, type QuickCreateOption } from "../../components/ui/QuickCreateModal"
import { SmartSelect, type SmartOption } from "../../components/ui/SmartSelect"

const QUOTATION_PREFIX = "/api/v1/ol-quotations/quotations/"
const PLAN_SEARCH_ENDPOINT = "/api/v1/ol/plans/search/"
const LOCATION_MASTER_ENDPOINT = "/api/v1/onboarding/locations/"
const LOCAL_DRAFT_KEY = "zic.ol-quotation.resume"

const today = () => new Date().toISOString().slice(0, 10)

const steps = [
  { id: "personal", label: "Personal Details", icon: UserRound },
  { id: "plans", label: "Plan & Sub-Products", icon: Layers3 },
  { id: "members", label: "Member Coverage", icon: UsersRound },
  { id: "installments", label: "Installments", icon: CalendarClock },
  { id: "funds", label: "Investment Funds", icon: WalletCards },
  { id: "riders", label: "Riders & Benefits", icon: ShieldCheck },
  { id: "financial", label: "Financial Details", icon: FileText },
] as const

type StepId = (typeof steps)[number]["id"]

type Choice = { value: string; label: string }

type PlanCard = {
  id: string
  plan_id: string
  product_version_id: string
  product_code: string
  product_name: string
  product_version?: number
  code: string
  name: string
  description?: string | null
  badges?: string[]
  plan_type_badges?: string[]
  with_profit?: boolean
  joint_life?: boolean
  mortgage?: boolean
  personal_accident?: boolean
  premium_waiver?: boolean
  payment_frequencies?: string[]
  min_entry_age?: number
  max_entry_age?: number
  min_term_years?: number
  max_term_years?: number
  currency?: string
}

type PlanConfiguration = {
  id: string
  plan?: string | null
  plan_id?: string | null
  product_version?: string | null
  product_version_id?: string | null
  sub_product_code?: string
  section_number?: number | null
  term_years?: number | null
  payment_period_years?: number | null
  premium_frequency?: string | null
  quote_basis?: string | null
  estimated_maturity_value?: string | number | null
  premium_factor?: string | null
  joint_life?: boolean
  mortgage?: boolean
  personal_accident?: boolean
  premium_waiver?: boolean
  estimated_bonus_rate?: string | number | null
  base_sum_assured?: string | number | null
  is_selected?: boolean
}

type Quotation = {
  id: string
  quote_number?: string | null
  quote_name?: string | null
  quote_date?: string | null
  status?: string | null
  currency?: string | null
  expiry_date?: string | null
  identity_type?: string | null
  identity_number?: string | null
  date_of_birth?: string | null
  age_at_quote?: number | null
  gender?: string | null
  smoker_status?: string | null
  location?: string | null
  location_id?: string | null
  agent_id?: string | null
  address?: string | null
  wizard_step_completion?: Record<string, boolean>
  plan_configurations?: PlanConfiguration[]
}

type PersonalForm = {
  quote_name: string
  quote_date: string
  identity_type: string
  identity_number: string
  date_of_birth: string
  gender: string
  smoker_status: string
  location_id: string
  agent_id: string
  address: string
}

type PlanOptions = {
  payment_frequencies: Choice[]
  quote_bases: Choice[]
  premium_factors: Choice[]
  plan_features?: {
    joint_life?: boolean
    mortgage?: boolean
    personal_accident?: boolean
    premium_waiver?: boolean
  }
}

type ApiFieldErrors = Record<string, string[]>

type MemberRow = {
  id: string | null
  member_type?: string
  full_name: string
  first_name?: string
  last_name?: string
  relation: string
  date_of_birth: string | null
  age_at_quote: number | null
  gender: string
  sum_assured: string | number | null
  coverage_basis?: string
  cover_type?: string
  waiting_period_days?: number
  is_principal?: boolean
}

type MemberCoverageState = {
  quotation_id?: string
  principal_member?: MemberRow | null
  members?: MemberRow[]
  additional_members?: MemberRow[]
  requires_additional_coverage: boolean
  info_banner?: string | null
  allowed_configurations?: Array<{ relation: string; cover_type?: string; min_age?: number | null; max_age?: number | null; waiting_period_days?: number; benefit_limit?: string | number | null; coverage_basis?: string }>
  wizard_step_complete?: boolean
}

type InstallmentRateRow = {
  sequence: number
  description: string
  rate_percent: string | number
  paid_up_rate: string | number | null
}

type InstallmentPlanRow = {
  plan_configuration_id: string
  plan_code: string
  plan_name: string
  policy_term_years: number
  payment_mode: string
  total_number_of_installments: number
  status: "READY_TO_CONFIGURE" | "CONFIGURED"
  can_configure: boolean
}

type InstallmentState = {
  rows: InstallmentPlanRow[]
  requires_configuration: boolean
  wizard_complete: boolean
}

type InstallmentTemplate = {
  plan_configuration_id: string
  has_template: boolean
  banner: string
  policy_term_years: number
  payment_mode: string
  available_payment_modes: string[]
  rate_rows: InstallmentRateRow[]
}

type FundOption = {
  id: string
  code: string
  name: string
  description?: string
  fund_type_name?: string
  risk_profile?: string
  currency?: string
  valuation_frequency?: string
  unit_price?: string | number | null
  currency_compatible: boolean
  currency_conversion_allowed: boolean
  selectable: boolean
}

type FundAllocation = {
  id?: string
  plan_config_id: string
  fund_id: string
  allocation_percent: string | number
  allocated_amount: string | number | null
  fund_name?: string
  fund_code?: string
}

type InvestmentFundState = {
  plan_rows: Array<{ plan_configuration_id: string; plan_code: string; plan_name: string; investment_linked: boolean; status: string; allocation_total: string | number; allocations: FundAllocation[]; can_configure: boolean }>
  requires_allocation: boolean
  not_applicable: boolean
  wizard_complete: boolean
}

type InvestmentFundOptions = {
  plan_configuration_id: string | null
  not_applicable: boolean
  quotation_currency: string
  funds: FundOption[]
}

type RiderOption = {
  id: string
  code: string
  name: string
  rider_category: string
  benefit_type: string
  calculation_basis: string
  min_age: number
  max_age: number
  min_term: number
  max_term: number
  min_sum_assured: string | number | null
  max_sum_assured: string | number | null
  waiting_period_days: number
  allows_standalone: boolean
  requires_underwriting: boolean
  product_id: string | null
  plan_id: string | null
  selectable: boolean
  synchronized_option: string
}

type RiderBenefit = {
  id?: string
  beneficial_type_id?: string | null
  benefit_type?: string
  basis: string
  value?: string | number | null
  loading?: string | number
  discount?: string | number
  maximum_cap?: string | number | null
  code?: string
  name?: string
}

type RiderSelection = {
  id?: string
  rider_id: string
  rider_code?: string
  rider_name?: string
  rider_category?: string
  benefit_type?: string
  plan_config_id?: string | null
  rider_sum_assured: string | number
  rider_term_years?: number | null
  waiting_period_days?: number
  requires_underwriting?: boolean
  synchronized_option?: string
  benefit_basis?: string
  benefit_value?: string | number | null
  loading?: string | number
  discount?: string | number
  maximum_cap?: string | number | null
  benefits?: RiderBenefit[]
}

type RiderPlanRow = {
  plan_configuration_id: string
  plan_code: string
  plan_name: string
  personal_accident?: boolean
  premium_waiver?: boolean
  riders: RiderSelection[]
  available_riders?: RiderOption[]
  benefits?: RiderBenefit[]
  status?: string
  can_configure?: boolean
}

type RiderState = {
  plan_rows: RiderPlanRow[]
  available_benefit_types: Choice[] | Array<Record<string, unknown>>
  requires_configuration: boolean
  wizard_complete: boolean
}

type RiderOptions = {
  plan_configuration_id: string | null
  quotation_age: number | null
  quotation_currency: string
  riders: RiderOption[]
  benefit_types: Array<Record<string, unknown>>
}

type FinancialProjection = {
  plan_configuration_id?: string | null
  policy_year: number
  premiums_paid: string | number
  estimated_bonus: string | number
  surrender_value: string | number
  paid_up_value: string | number
  estimated_maturity_value: string | number
}

type InstallmentPayout = {
  plan_configuration_id?: string | null
  installment_configuration_id?: string | null
  sequence: number
  description?: string
  payout_amount: string | number
  payout_date: string
  rate_percent: string | number
  paid_up_rate?: string | number
}

type FinancialDetails = {
  quotation_id?: string
  total_sum_assured: string | number
  total_premium: string | number
  total_rider_premium: string | number
  total_benefit_premium: string | number
  base_premium: string | number
  total_loading: string | number
  total_discount: string | number
  total_tax: string | number
  installment_charge: string | number
  estimated_maturity_value: string | number
  quotation_version_number?: number
  recalculation_required?: boolean
  calculated_at?: string | null
  currency?: string
  projections: FinancialProjection[]
  installment_payouts: InstallmentPayout[]
  plan_breakdowns?: Array<Record<string, unknown>>
  rider_breakdowns?: Array<Record<string, unknown>>
  tax_breakdown?: Array<Record<string, unknown>>
}

type FinalizeState = {
  detail?: string
  errors?: Record<string, unknown>
}

type ApiPayload = {
  quotation?: Quotation
  configurations?: PlanConfiguration[]
  configuration?: PlanConfiguration
  selected_plan_count?: number
  wizard_step_complete?: boolean
  plans?: PlanCard[]
  count?: number
  identity_types?: Choice[]
  genders?: Choice[]
  smoker_statuses?: Choice[]
  locations?: Choice[]
  agents?: Choice[]
  payment_frequencies?: Choice[]
  quote_bases?: Choice[]
  premium_factors?: Choice[]
  plan_features?: PlanOptions["plan_features"]
  principal_member?: MemberRow | null
  members?: MemberRow[]
  additional_members?: MemberRow[]
  requires_additional_coverage?: boolean
  info_banner?: string | null
  allowed_configurations?: MemberCoverageState["allowed_configurations"]
  rows?: InstallmentPlanRow[]
  requires_configuration?: boolean
  has_template?: boolean
  banner?: string
  policy_term_years?: number
  payment_mode?: string
  available_payment_modes?: string[]
  rate_rows?: InstallmentRateRow[]
  plan_configuration_id?: string | null
  not_applicable?: boolean
  funds?: FundOption[]
  plan_rows?: RiderPlanRow[]
  available_benefit_types?: Choice[] | Array<Record<string, unknown>>
  wizard_complete?: boolean
  quotation_age?: number | null
  quotation_currency?: string
  riders?: RiderOption[]
  benefit_types?: Array<Record<string, unknown>>
  summary?: FinancialDetails | null
  total_sum_assured?: string | number
  total_premium?: string | number
  total_rider_premium?: string | number
  total_benefit_premium?: string | number
  base_premium?: string | number
  total_loading?: string | number
  total_discount?: string | number
  total_tax?: string | number
  installment_charge?: string | number
  estimated_maturity_value?: string | number
  quotation_version_number?: number
  recalculation_required?: boolean
  calculated_at?: string | null
  currency?: string
  projections?: FinancialProjection[]
  installment_payouts?: InstallmentPayout[]
  plan_breakdowns?: Array<Record<string, unknown>>
  rider_breakdowns?: Array<Record<string, unknown>>
  tax_breakdown?: Array<Record<string, unknown>>
  errors?: Record<string, unknown>
  detail?: string
  state?: MemberCoverageState | InstallmentState | InvestmentFundState | RiderState
}

function apiKeyToSnakeCase(key: string): string {
  return key.replace(/[A-Z]/g, (character) => `_${character.toLowerCase()}`)
}

function normalizeApiValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(normalizeApiValue)
  if (!value || typeof value !== "object") return value
  return Object.fromEntries(Object.entries(value as Record<string, unknown>).map(([key, nested]) => [apiKeyToSnakeCase(key), normalizeApiValue(nested)]))
}

async function requestNormalized<T>(path: string, options: Parameters<typeof request>[1] = {}): Promise<T> {
  return normalizeApiValue(await request<unknown>(path, options)) as T
}

function normalizePlanCard(value: unknown): PlanCard | null {
  if (!value || typeof value !== "object") return null
  const record = value as Record<string, unknown>
  const planId = record.plan_id ?? record.id ?? record.planId
  const productVersionId = record.product_version_id ?? record.productVersionId ?? record.product_version ?? ""
  if (planId === undefined || planId === null || planId === "") return null
  return {
    ...(record as unknown as PlanCard),
    id: String(record.id ?? planId),
    plan_id: String(planId),
    product_version_id: String(productVersionId),
    product_code: String(record.product_code ?? record.productCode ?? ""),
    product_name: String(record.product_name ?? record.productName ?? ""),
    code: String(record.code ?? record.plan_code ?? record.planCode ?? planId),
    name: String(record.name ?? record.plan_name ?? record.planName ?? record.code ?? planId),
    description: record.description as string | null | undefined,
    badges: Array.isArray(record.badges) ? record.badges.map(String) : undefined,
    plan_type_badges: Array.isArray(record.plan_type_badges) ? record.plan_type_badges.map(String) : undefined,
  }
}

function asChoices(value: unknown): Choice[] {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    const record = value as Record<string, unknown>
    for (const key of ["results", "items", "rows", "choices", "data"]) {
      if (key in record) return asChoices(record[key])
    }
    return []
  }
  if (!Array.isArray(value)) return []
  return value.map((item) => {
    if (typeof item === "string") return { value: item, label: item.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase()) }
    const record = item as Record<string, unknown>
    const rawValue = record.value ?? record.id ?? record.code ?? ""
    const rawLabel = record.label ?? record.name ?? record.code ?? rawValue
    return { value: String(rawValue), label: String(rawLabel) }
  }).filter((item) => item.value)
}

function fieldError(errors: ApiFieldErrors, field: string): string | undefined {
  return errors[field]?.[0]
}

function validatePersonalForm(form: PersonalForm, age: number | null): ApiFieldErrors {
  const errors: ApiFieldErrors = {}
  const required: Array<keyof PersonalForm> = ["quote_name", "quote_date", "identity_type", "identity_number", "date_of_birth", "gender", "smoker_status", "location_id", "agent_id", "address"]
  required.forEach((field) => { if (!form[field].trim()) errors[field] = ["This field is required."] })
  if (form.date_of_birth && form.quote_date && form.date_of_birth > form.quote_date) errors.date_of_birth = ["Date of birth cannot be after the quote date."]
  if (form.date_of_birth && form.date_of_birth > today()) errors.date_of_birth = ["Date of birth cannot be in the future."]
  if (age !== null && (age < 0 || age > 120)) errors.date_of_birth = ["Computed age must be between 0 and 120 years."]
  return errors
}

function parseApiError(error: unknown): { message: string; fieldErrors: ApiFieldErrors } {
  if (error instanceof ApiClientError) return { message: error.message, fieldErrors: error.fieldErrors }
  return { message: error instanceof Error ? error.message : "The request could not be completed.", fieldErrors: {} }
}

function computeAge(dateOfBirth: string, quoteDate: string): number | null {
  if (!dateOfBirth || !quoteDate) return null
  const dob = new Date(`${dateOfBirth}T00:00:00`)
  const quote = new Date(`${quoteDate}T00:00:00`)
  if (Number.isNaN(dob.getTime()) || Number.isNaN(quote.getTime())) return null
  let age = quote.getFullYear() - dob.getFullYear()
  const birthdayPassed = quote.getMonth() > dob.getMonth() || (quote.getMonth() === dob.getMonth() && quote.getDate() >= dob.getDate())
  if (!birthdayPassed) age -= 1
  return age >= 0 ? age : null
}

function planBadgeLabel(value: string): string {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function configurationPlanId(configuration: PlanConfiguration): string | null {
  const planId = configuration.plan ?? configuration.plan_id
  return planId ? String(planId) : null
}
function draftConfiguration(plan: PlanCard, sectionNumber: number): PlanConfiguration {
  return {
    id: `draft:${plan.plan_id}`,
    plan: plan.plan_id,
    product_version: plan.product_version_id,
    product_version_id: plan.product_version_id,
    sub_product_code: plan.code,
    section_number: sectionNumber,
    is_selected: true,
  }
}

function initialPersonal(quotation?: Quotation): PersonalForm {
  return {
    quote_name: quotation?.quote_name ?? "",
    quote_date: quotation?.quote_date?.slice(0, 10) ?? today(),
    identity_type: quotation?.identity_type ?? "",
    identity_number: quotation?.identity_number ?? "",
    date_of_birth: quotation?.date_of_birth?.slice(0, 10) ?? "",
    gender: quotation?.gender ?? "",
    smoker_status: quotation?.smoker_status ?? "",
    location_id: quotation?.location_id ?? "",
    agent_id: quotation?.agent_id ?? "",
    address: quotation?.address ?? "",
  }
}

function createDraftSnapshot(quotation: Quotation, personal: PersonalForm, selectedPlanIds: string[], configurations: PlanConfiguration[]) {
  return JSON.stringify({ quotationId: quotation.id, personal, selectedPlanIds, configurations })
}

function readDraftSnapshot(): Partial<{ quotationId: string; personal: PersonalForm; selectedPlanIds: string[]; configurations: PlanConfiguration[] }> | null {
  try {
    const raw = localStorage.getItem(LOCAL_DRAFT_KEY)
    return raw ? JSON.parse(raw) as Partial<{ quotationId: string; personal: PersonalForm; selectedPlanIds: string[]; configurations: PlanConfiguration[] }> : null
  } catch {
    return null
  }
}

function ChoiceSelect({ label, name, value, options, required, error, onChange, placeholder = "Select an option" }: { label: string; name: string; value: string; options: Choice[]; required?: boolean; error?: string; onChange: (value: string) => void; placeholder?: string }) {
  return <SelectInput label={label} name={name} required={required} error={error} value={value} onChange={(event) => onChange(event.target.value)}>
    <option value="">{placeholder}</option>
    {options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
  </SelectInput>
}

function PlanSelectionPanel({ plans, selectedPlanIds, search, loading, onSearch, onToggle, onProductCreated }: { plans: PlanCard[]; selectedPlanIds: string[]; search: string; loading: boolean; onSearch: (value: string) => void; onToggle: (plan: PlanCard) => void; onProductCreated: (option: QuickCreateOption) => void | Promise<void> }) {
  const { hasPermission, isSuperAdmin } = useAccess()
  const [quickCreateOpen, setQuickCreateOpen] = useState(false)
  const canCreateProducts = isSuperAdmin || Boolean(hasPermission?.("ol_parameters.create"))
  return <aside className="w-full shrink-0 lg:w-[320px] xl:w-[360px]" aria-label="Plan selection panel">
    <div className="surface-card overflow-hidden">
      <div className="border-b bg-[var(--muted)]/35 p-4">
        <div className="mb-3 flex items-center justify-between gap-2"><div className="flex min-w-0 items-center gap-2"><PanelLeft size={17} aria-hidden="true" /><h2 className="truncate text-base font-bold">Plans & Sub-Products</h2></div>{canCreateProducts && <button type="button" className="button-secondary !min-h-8 !px-2.5" aria-label="Add product" onClick={() => setQuickCreateOpen(true)}><Plus size={15} aria-hidden="true" /><span className="hidden sm:inline">Add product</span></button>}</div>
        <div className="relative"><Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted-foreground)]" size={16} aria-hidden="true" /><input aria-label="Search plans and sub-products" value={search} onChange={(event) => onSearch(event.target.value)} placeholder="Search plans and sub-products..." className="h-10 w-full rounded-[10px] border bg-[var(--card)] pl-9 pr-3 text-sm outline-none focus:border-[var(--ring)]" /></div>
        <p className="mt-3 text-xs font-semibold text-[var(--muted-foreground)]">{selectedPlanIds.length ? `${selectedPlanIds.length} ${selectedPlanIds.length === 1 ? "Plan" : "Plans"} selected` : "No products selected"}</p>
      </div>
      <div className="max-h-[calc(100vh-360px)] space-y-2 overflow-auto p-3">
        {loading && <div className="py-10 text-center text-sm text-[var(--muted-foreground)]"><LoaderCircle className="mx-auto mb-2 animate-spin" size={22} aria-hidden="true" />Loading plans…</div>}
        {!loading && !plans.length && <div className="rounded-[10px] border border-dashed p-6 text-center text-sm text-[var(--muted-foreground)]">No active plans match your search.</div>}
        {!loading && plans.map((plan) => {
          const selected = selectedPlanIds.includes(plan.plan_id)
          const badges = plan.badges?.length ? plan.badges : plan.plan_type_badges ?? []
          return <button key={`${plan.product_version_id}-${plan.plan_id}`} type="button" aria-pressed={selected} onClick={() => onToggle(plan)} className={`w-full rounded-[10px] border p-3 text-left transition ${selected ? "border-[var(--primary)] bg-[var(--primary)]/5 shadow-sm" : "border-[var(--border)] bg-[var(--card)] hover:border-[var(--ring)] hover:bg-[var(--muted)]/25"}`}>
            <div className="flex items-start justify-between gap-3"><div className="min-w-0"><div className="mb-1 flex flex-wrap items-center gap-2"><span className="rounded-md bg-[var(--muted)] px-2 py-0.5 text-[10px] font-bold tracking-[0.1em]">{plan.code}</span>{badges.map((badge) => <span key={badge} className="rounded-md border px-2 py-0.5 text-[10px] font-semibold">{planBadgeLabel(badge)}</span>)}</div><h3 className="truncate text-sm font-bold">{plan.name}</h3><p className="mt-1 line-clamp-2 text-xs text-[var(--muted-foreground)]">{plan.description || plan.product_name || "Configured Ordinary Life plan"}</p></div><span className={`mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border ${selected ? "border-[var(--primary)] bg-[var(--primary)] text-[var(--primary-foreground)]" : "border-[var(--border)]"}`}>{selected && <Check size={15} aria-hidden="true" />}</span></div>
          </button>
        })}
      </div>
      {canCreateProducts && <QuickCreateModal open={quickCreateOpen} entity="products" entityLabel="Product" permissionCode="ol_parameters.create" onClose={() => setQuickCreateOpen(false)} onCreated={(option) => { setQuickCreateOpen(false); return onProductCreated(option) }} />}
    </div>
  </aside>
}

function WizardTabs({ activeStep, completedSteps, invalidSteps, onSelect }: { activeStep: number; completedSteps: Set<number>; invalidSteps: Set<number>; onSelect: (index: number) => void }) {
  return <nav className="surface-card overflow-x-auto border-b" aria-label="Quotation wizard steps"><ol className="flex min-w-max items-stretch gap-1 p-2">{steps.map((step, index) => { const Icon = step.icon; const active = activeStep === index; const completed = completedSteps.has(index); const invalid = invalidSteps.has(index); return <li key={step.id} className="flex items-center"><button type="button" aria-current={active ? "step" : undefined} onClick={() => onSelect(index)} className={`flex items-center gap-2 rounded-[10px] px-3 py-2.5 text-left text-xs font-bold transition md:text-sm ${active ? "bg-[var(--primary)] text-[var(--primary-foreground)] shadow-sm" : invalid ? "text-[var(--destructive)] hover:bg-[var(--muted)]" : "text-[var(--muted-foreground)] hover:bg-[var(--muted)]"}`}><span className={`flex h-7 w-7 items-center justify-center rounded-full border ${active ? "border-white/40 bg-white/15" : completed ? "border-[var(--success)] text-[var(--success)]" : invalid ? "border-[var(--destructive)]" : "border-current/25"}`}>{completed && !active ? <Check size={14} aria-hidden="true" /> : invalid ? <CircleAlert size={14} aria-hidden="true" /> : <Icon size={14} aria-hidden="true" />}</span><span>{step.label}</span></button>{index < steps.length - 1 && <span className="mx-1 hidden h-px w-4 bg-[var(--border)] xl:block" aria-hidden="true" />}</li> })}</ol></nav>
}

function StepHeader({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return <div className="border-b bg-[linear-gradient(110deg,#f8fafc,#eef2ff)] px-5 py-5 dark:bg-[linear-gradient(110deg,#171717,#262626)]"><p className="text-[11px] font-bold uppercase tracking-[0.16em] text-[var(--muted-foreground)]">{eyebrow}</p><h2 className="mt-1 text-xl font-bold tracking-tight">{title}</h2><p className="mt-1 text-sm text-[var(--muted-foreground)]">{description}</p></div>
}

function PersonalDetailsStep({ form, options, errors, age, onChange }: { form: PersonalForm; options: { identityTypes: Choice[]; genders: Choice[]; smokerStatuses: Choice[]; locations: Choice[]; agents: Choice[] }; errors: ApiFieldErrors; age: number | null; onChange: (field: keyof PersonalForm, value: string) => void }) {
  return <div className="surface-card overflow-visible"><StepHeader eyebrow="Step 1 of 7" title="Personal Details" description="Capture the prospect information used to calculate eligibility, partner matching, and quotation rating." /><div className="space-y-6 p-5"><FormGrid columns={2}>
    <TextInput label="Quote Name" name="quote_name" required value={form.quote_name} onChange={(event) => onChange("quote_name", event.target.value)} error={fieldError(errors, "quote_name")} placeholder="Enter quote name" />
    <DateInput label="Quote Date" name="quote_date" required value={form.quote_date} onChange={(event) => onChange("quote_date", event.target.value)} error={fieldError(errors, "quote_date")} />
    <SmartSelect entity="identity-types" label="Identity Type" name="identity_type" required value={form.identity_type} onChange={(value) => onChange("identity_type", value)} error={fieldError(errors, "identity_type")} placeholder="Search and select identity type" />
    <TextInput label="Identity Number" name="identity_number" required value={form.identity_number} onChange={(event) => onChange("identity_number", event.target.value)} error={fieldError(errors, "identity_number")} placeholder="Enter identity number" />
    <DateInput label="Date of Birth" name="date_of_birth" required value={form.date_of_birth} onChange={(event) => onChange("date_of_birth", event.target.value)} error={fieldError(errors, "date_of_birth")} />
    <ReadOnlyField label="Age" value={age === null ? "—" : `${age} years`} />
    <ChoiceSelect label="Gender" name="gender" required value={form.gender} options={options.genders} onChange={(value) => onChange("gender", value)} error={fieldError(errors, "gender")} />
    <ChoiceSelect label="Smoker" name="smoker_status" required value={form.smoker_status} options={options.smokerStatuses} onChange={(value) => onChange("smoker_status", value)} error={fieldError(errors, "smoker_status")} />
    <SmartSelect entity="locations" label="Location" name="location_id" required value={form.location_id} onChange={(value) => onChange("location_id", value)} error={fieldError(errors, "location_id") ?? fieldError(errors, "location")} placeholder="Search and select location" manageHref="/system-parameters/locations" />
    <SmartSelect entity="agents" label="Agent" name="agent_id" required value={form.agent_id} onChange={(value) => onChange("agent_id", value)} error={fieldError(errors, "agent_id")} placeholder="Search and select agent" />
  </FormGrid>
  <TextareaInput label="Address" name="address" required value={form.address} onChange={(event) => onChange("address", event.target.value)} error={fieldError(errors, "address")} placeholder="Enter residential or postal address" />
  </div></div>
}

function PlanConfigurationSection({ index, config, card, options, errors, onChange }: { index: number; config: PlanConfiguration; card?: PlanCard; options: PlanOptions; errors: ApiFieldErrors; onChange: (field: string, value: string | boolean) => void }) {
  const features = { ...(options.plan_features ?? {}), joint_life: card?.joint_life ?? options.plan_features?.joint_life, mortgage: card?.mortgage ?? options.plan_features?.mortgage, personal_accident: card?.personal_accident ?? options.plan_features?.personal_accident, premium_waiver: card?.premium_waiver ?? options.plan_features?.premium_waiver }
  const planName = card?.name ?? card?.code ?? "Selected plan"
  return <section className="rounded-[12px] border bg-[var(--card)] shadow-sm"><div className="flex flex-wrap items-center justify-between gap-3 border-b bg-[var(--muted)]/35 px-4 py-3"><div><p className="text-[11px] font-bold uppercase tracking-[0.14em] text-[var(--muted-foreground)]">Section {index + 1}</p><h3 className="mt-1 text-base font-bold">{planName}</h3></div><span className="rounded-full border px-3 py-1 text-xs font-semibold text-[var(--muted-foreground)]">Plan-only configuration</span></div><div className="space-y-5 p-4"><FormGrid columns={2}>
    <TextInput label="Policy Term (Years)" name={`term_years_${config.id}`} required type="number" min={1} value={String(config.term_years ?? "")} onChange={(event) => onChange("term_years", event.target.value)} error={fieldError(errors, "term_years")} />
    <TextInput label="Payment Period (Years)" name={`payment_period_years_${config.id}`} required type="number" min={1} value={String(config.payment_period_years ?? "")} onChange={(event) => onChange("payment_period_years", event.target.value)} error={fieldError(errors, "payment_period_years")} />
    <SmartSelect entity="payment-frequencies" label="Payment Frequency" name={`premium_frequency_${config.id}`} required value={String(config.premium_frequency ?? "")} onChange={(value) => onChange("premium_frequency", value)} error={fieldError(errors, "premium_frequency")} placeholder="Search and select payment frequency" />
    <SmartSelect entity="quote-bases" label="Quote Basis" name={`quote_basis_${config.id}`} required value={String(config.quote_basis ?? "")} onChange={(value) => onChange("quote_basis", value)} error={fieldError(errors, "quote_basis")} placeholder="Search and select quote basis" />
    <DecimalInput label="Estimated Maturity Value" name={`estimated_maturity_value_${config.id}`} required value={String(config.estimated_maturity_value ?? "")} onChange={(event) => onChange("estimated_maturity_value", event.target.value)} error={fieldError(errors, "estimated_maturity_value")} />
    <SmartSelect entity="premium-factors" label="Premium Factor" name={`premium_factor_${config.id}`} value={String(config.premium_factor ?? "")} onChange={(value) => onChange("premium_factor", value)} error={fieldError(errors, "premium_factor")} placeholder="None" />
    <DecimalInput label="Estimated Bonus Rate (per mille)" name={`estimated_bonus_rate_${config.id}`} value={String(config.estimated_bonus_rate ?? "")} onChange={(event) => onChange("estimated_bonus_rate", event.target.value)} error={fieldError(errors, "estimated_bonus_rate")} />
  </FormGrid>
  <div className="grid gap-4 rounded-[10px] border bg-[var(--muted)]/25 p-4 md:grid-cols-2 xl:grid-cols-4"><Toggle label="Joint Life" checked={Boolean(config.joint_life)} disabled={!features.joint_life} onChange={(checked) => onChange("joint_life", checked)} hint={!features.joint_life ? "Not available for this plan" : "Apply joint-life rules"} /><Toggle label="Mortgage" checked={Boolean(config.mortgage)} disabled={!features.mortgage} onChange={(checked) => onChange("mortgage", checked)} hint={!features.mortgage ? "Not available for this plan" : "Apply mortgage factor"} /><Toggle label="Personal Accident (PA)" checked={Boolean(config.personal_accident)} disabled={!features.personal_accident} onChange={(checked) => onChange("personal_accident", checked)} hint={!features.personal_accident ? "Not available for this plan" : "Attach PA rider option"} /><Toggle label="Premium Waiver (WP)" checked={Boolean(config.premium_waiver)} disabled={!features.premium_waiver} onChange={(checked) => onChange("premium_waiver", checked)} hint={!features.premium_waiver ? "Not available for this plan" : "Attach WP rider option"} /></div>
  {card && <p className="text-xs text-[var(--muted-foreground)]">Configured term range: {card.min_term_years ?? "—"}–{card.max_term_years ?? "—"} years. Entry age range: {card.min_entry_age ?? "—"}–{card.max_entry_age ?? "—"} years.</p>}
  </div></section>
}

type MemberForm = { full_name: string; relation: string; cover_type: string; date_of_birth: string; gender: string; sum_assured: string }

function MemberCoverageStep({ quotation, state, genderOptions, errors, onSaveMember, onRemoveMember }: { quotation: Quotation; state: MemberCoverageState | null; genderOptions: Choice[]; errors: ApiFieldErrors; onSaveMember: (member: MemberForm, memberId?: string) => Promise<boolean>; onRemoveMember: (memberId: string) => Promise<void> }) {
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<MemberRow | null>(null)
  const [member, setMember] = useState<MemberForm>({ full_name: "", relation: "", cover_type: "", date_of_birth: "", gender: "", sum_assured: "" })
  const age = computeAge(member.date_of_birth, quotation.quote_date ?? today())
  const allowedRelations = (state?.allowed_configurations ?? []).map((configuration) => ({ value: configuration.relation, label: configuration.relation.replace(/_/g, " ").replace(/\\b\\w/g, (letter) => letter.toUpperCase()) }))
  const additionalMembers = state?.additional_members ?? state?.members?.filter((item) => !item.is_principal) ?? []
  const openAdd = () => { const relation = allowedRelations[0]?.value ?? ""; const configuration = state?.allowed_configurations?.find((item) => item.relation === relation); setEditing(null); setMember({ full_name: "", relation, cover_type: configuration?.cover_type ?? "", date_of_birth: "", gender: "", sum_assured: "" }); setModalOpen(true) }
  const openEdit = (row: MemberRow) => { const configuration = state?.allowed_configurations?.find((item) => item.relation === row.relation); setEditing(row); setMember({ full_name: row.full_name, relation: row.relation, cover_type: row.cover_type ?? configuration?.cover_type ?? "", date_of_birth: row.date_of_birth ?? "", gender: row.gender, sum_assured: row.sum_assured == null ? "" : String(row.sum_assured) }); setModalOpen(true) }
  const save = async () => { if (await onSaveMember(member, editing?.id ?? undefined)) { setModalOpen(false); setEditing(null) } }
  const principal = state?.principal_member
  return <div className="space-y-4">
    <div className="surface-card overflow-hidden"><StepHeader eyebrow="Step 3 of 7" title="Member Coverage" description="Configure the principal member and any additional members required by the selected plans." /><div className="p-5">
      <div className="rounded-[12px] border bg-[var(--muted)]/25 p-4"><div className="mb-3 flex items-center gap-2"><UserRound size={17} aria-hidden="true" /><h3 className="font-bold">Principal Member (Policy Holder)</h3><span className="rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.08em]">Automatic</span></div>{principal ? <div className="grid gap-4 md:grid-cols-3"><ReadOnlyField label="Name" value={principal.full_name || quotation.quote_name || "—"} /><ReadOnlyField label="Date of Birth" value={principal.date_of_birth ?? quotation.date_of_birth ?? "—"} /><ReadOnlyField label="Gender" value={principal.gender || quotation.gender || "—"} /></div> : <p className="text-sm text-[var(--muted-foreground)]">Save Personal Details to configure the principal member automatically.</p>}</div>
      {!state?.requires_additional_coverage ? <InfoBanner title="No additional coverage required" className="mt-5">{state?.info_banner ?? "Selected plans do not require additional member coverage configuration. Principal member is configured automatically."}</InfoBanner> : <div className="mt-5 space-y-4"><div className="flex flex-wrap items-center justify-between gap-3"><div><h3 className="font-bold">Additional Members</h3><p className="text-xs text-[var(--muted-foreground)]">Add dependents only when selected plan configurations permit additional coverage.</p></div><button type="button" className="button-primary" onClick={openAdd}><Plus size={15} aria-hidden="true" />Add member</button></div>{fieldError(errors, "members") && <p className="text-sm font-semibold text-[var(--destructive)]" role="alert">{fieldError(errors, "members")}</p>}{additionalMembers.length ? <div className="overflow-x-auto rounded-[10px] border"><table className="w-full min-w-[700px] text-left text-sm"><thead className="bg-[var(--muted)]/40 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><tr><th scope="col" className="px-3 py-3">Relation</th><th scope="col" className="px-3 py-3">Name</th><th scope="col" className="px-3 py-3">Date of Birth</th><th scope="col" className="px-3 py-3">Age</th><th scope="col" className="px-3 py-3">Gender</th><th scope="col" className="px-3 py-3">Sum Assured</th><th scope="col" className="px-3 py-3"><span className="sr-only">Actions</span></th></tr></thead><tbody className="divide-y divide-[var(--border)]">{additionalMembers.map((row) => <tr key={row.id ?? row.full_name}><td className="px-3 py-3 font-semibold">{row.relation}</td><td className="px-3 py-3">{row.full_name}</td><td className="px-3 py-3">{row.date_of_birth ?? "—"}</td><td className="px-3 py-3">{row.age_at_quote ?? "—"}</td><td className="px-3 py-3">{row.gender || "—"}</td><td className="px-3 py-3">{row.sum_assured ?? "—"}</td><td className="px-3 py-3"><div className="flex justify-end gap-1"><button type="button" className="rounded-md p-2 hover:bg-[var(--muted)]" aria-label={`Edit ${row.full_name}`} onClick={() => openEdit(row)}><Pencil size={15} aria-hidden="true" /></button><button type="button" className="rounded-md p-2 text-[var(--destructive)] hover:bg-[var(--destructive)]/10" aria-label={`Remove ${row.full_name}`} onClick={() => row.id && void onRemoveMember(row.id)}><Trash2 size={15} aria-hidden="true" /></button></div></td></tr>)}</tbody></table></div> : <div className="rounded-[10px] border border-dashed p-8 text-center text-sm text-[var(--muted-foreground)]">No additional members configured.</div>}</div>}
    </div></div>
    <Modal open={modalOpen} title={editing ? "Edit Additional Member" : "Add Additional Member"} description="Member limits and waiting periods are determined by OL Member Cover Configuration." onClose={() => setModalOpen(false)} size="lg" footer={<><button type="button" className="button-secondary" onClick={() => setModalOpen(false)}>Cancel</button><button type="button" className="button-primary" onClick={() => void save()}>Save member</button></>}><div className="space-y-5"><FormGrid columns={2}><SmartSelect entity="member-relations" label="Relation" name="member_relation" required value={member.relation} error={fieldError(errors, "relation")} onChange={(value) => { const configuration = state?.allowed_configurations?.find((item) => item.relation === value); setMember((current) => ({ ...current, relation: value, cover_type: configuration?.cover_type ?? current.cover_type })) }} placeholder="Search and select member relation" /><SmartSelect entity="cover-types" label="Cover Type" name="member_cover_type" required value={member.cover_type} error={fieldError(errors, "cover_type")} onChange={(value) => setMember((current) => ({ ...current, cover_type: value }))} placeholder="Search and select cover type" /><TextInput label="Full Name" name="member_full_name" required value={member.full_name} error={fieldError(errors, "full_name")} onChange={(event) => setMember((current) => ({ ...current, full_name: event.target.value }))} /><DateInput label="Date of Birth" name="member_date_of_birth" required value={member.date_of_birth} error={fieldError(errors, "date_of_birth")} onChange={(event) => setMember((current) => ({ ...current, date_of_birth: event.target.value }))} /><ReadOnlyField label="Age" value={age === null ? "—" : `${age} years`} /><ChoiceSelect label="Gender" name="member_gender" required value={member.gender} options={genderOptions} error={fieldError(errors, "gender")} onChange={(value) => setMember((current) => ({ ...current, gender: value }))} /><DecimalInput label="Sum Assured" name="member_sum_assured" value={member.sum_assured} error={fieldError(errors, "sum_assured")} onChange={(event) => setMember((current) => ({ ...current, sum_assured: event.target.value }))} /></FormGrid></div></Modal>
  </div>
}

function InstallmentRateGrid({ rows, onChange, error }: { rows: InstallmentRateRow[]; onChange: (rows: InstallmentRateRow[]) => void; error?: string }) {
  const total = rows.reduce((sum, row) => sum + (Number(row.rate_percent) || 0), 0)
  const update = (index: number, patch: Partial<InstallmentRateRow>) => onChange(rows.map((row, rowIndex) => rowIndex === index ? { ...row, ...patch } : row))
  return <div className="overflow-hidden rounded-[10px] border"><div className="flex items-center justify-between border-b bg-[var(--muted)]/40 px-4 py-3"><div><h3 className="text-sm font-bold">Installment Rate Details</h3><p className="text-xs text-[var(--muted-foreground)]">Rates must sum exactly to 100%.</p></div><button type="button" className="button-secondary !min-h-9 !px-3" onClick={() => onChange([...rows, { sequence: rows.length + 1, description: `Installment ${rows.length + 1}`, rate_percent: "", paid_up_rate: null }])}><Plus size={15} aria-hidden="true" />Add row</button></div><div className="overflow-x-auto"><table className="w-full min-w-[720px] text-left text-sm"><thead className="bg-[var(--muted)]/25 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><tr><th className="px-3 py-3">Installment #</th><th className="px-3 py-3">Description<span className="ml-1 text-[var(--destructive)]">*</span></th><th className="px-3 py-3">Rate (%)<span className="ml-1 text-[var(--destructive)]">*</span></th><th className="px-3 py-3">Paid Up Rate</th><th className="px-3 py-3"><span className="sr-only">Remove</span></th></tr></thead><tbody className="divide-y divide-[var(--border)]">{rows.map((row, index) => <tr key={`${row.sequence}-${index}`}><td className="px-3 py-2"><div className="flex h-10 items-center rounded-[10px] border bg-[var(--muted)] px-3 text-sm font-semibold text-[var(--muted-foreground)]">{row.sequence}</div></td><td className="px-3 py-2"><input aria-label={`Installment ${index + 1} description`} value={row.description} onChange={(event) => update(index, { description: event.target.value })} className="h-10 w-full rounded-[10px] border bg-[var(--card)] px-3 text-sm outline-none focus:border-[var(--ring)]" /></td><td className="px-3 py-2"><input aria-label={`Installment ${index + 1} rate`} type="number" step="0.0001" min="0" max="100" value={String(row.rate_percent)} onChange={(event) => update(index, { rate_percent: event.target.value })} className="h-10 w-full rounded-[10px] border bg-[var(--card)] px-3 text-sm outline-none focus:border-[var(--ring)]" /></td><td className="px-3 py-2"><div className="flex h-10 items-center rounded-[10px] border bg-[var(--muted)] px-3 text-sm text-[var(--muted-foreground)]">{row.paid_up_rate ?? "—"}</div></td><td className="px-3 py-2"><button type="button" className="rounded-md p-2 text-[var(--destructive)] hover:bg-[var(--destructive)]/10" aria-label={`Remove installment row ${index + 1}`} onClick={() => onChange(rows.filter((_, rowIndex) => rowIndex !== index))}><Trash2 size={16} aria-hidden="true" /></button></td></tr>)}</tbody><tfoot className="border-t bg-[var(--muted)]/35"><tr><th colSpan={4} className="px-3 py-3 text-right">Total Rate</th><td className={`px-3 py-3 text-right font-extrabold ${Math.abs(total - 100) < 0.0001 ? "text-[var(--success)]" : "text-[var(--destructive)]"}`}>{total.toFixed(2)} / 100.00</td></tr></tfoot></table></div>{error && <p className="border-t px-4 py-3 text-sm font-semibold text-[var(--destructive)]" role="alert">{error}</p>}</div>
}

function ConfigureInstallmentModal({ open, plan, template, loading, saving, errors, onClose, onSave }: { open: boolean; plan: InstallmentPlanRow | null; template: InstallmentTemplate | null; loading: boolean; saving: boolean; errors: ApiFieldErrors; onClose: () => void; onSave: (payload: { annuity_period_years: number; payment_mode: string; after_maturity_benefits: boolean; before_maturity_benefits: boolean; rate_rows: InstallmentRateRow[] }) => Promise<boolean> }) {
  const [annuityPeriod, setAnnuityPeriod] = useState("1")
  const [paymentMode, setPaymentMode] = useState("")
  const [afterMaturity, setAfterMaturity] = useState(false)
  const [beforeMaturity, setBeforeMaturity] = useState(false)
  const [rows, setRows] = useState<InstallmentRateRow[]>([])
  useEffect(() => { if (open && template) { setAnnuityPeriod("1"); setPaymentMode(template.payment_mode || template.available_payment_modes[0] || ""); setRows(template.rate_rows?.length ? template.rate_rows : [{ sequence: 1, description: "Installment 1", rate_percent: "", paid_up_rate: null }]); setAfterMaturity(false); setBeforeMaturity(false) } }, [open, template])
  const total = rows.reduce((sum, row) => sum + (Number(row.rate_percent) || 0), 0)
  const save = async () => { const ok = await onSave({ annuity_period_years: Number(annuityPeriod), payment_mode: paymentMode, after_maturity_benefits: afterMaturity, before_maturity_benefits: beforeMaturity, rate_rows: rows }) ; if (ok) onClose() }
  return <Modal open={open} title="Configure Installments" description={plan ? `${plan.plan_code} — ${plan.plan_name}` : undefined} onClose={onClose} size="xl" footer={<><button type="button" className="button-secondary" onClick={onClose} disabled={saving}>Cancel</button><button type="button" className="button-primary" onClick={() => void save()} disabled={saving || loading}>{saving ? "Saving…" : "Save configuration"}</button></>}><div className="space-y-5">{loading ? <div className="py-12 text-center text-sm text-[var(--muted-foreground)]"><LoaderCircle className="mx-auto mb-2 animate-spin" size={22} aria-hidden="true" />Loading installment template…</div> : <><InfoBanner title={template?.has_template ? "Template loaded" : "Manual configuration available"}>{template?.banner || "Template rows were loaded from the configured installment parameters."}</InfoBanner><FormGrid columns={2}><TextInput label="Annuity Period (years)" name="annuity_period_years" required type="number" min={1} max={plan?.policy_term_years} value={annuityPeriod} error={fieldError(errors, "annuity_period_years")} onChange={(event) => setAnnuityPeriod(event.target.value)} /><SmartSelect entity="payment-modes" label="Payment Mode" name="installment_payment_mode" required value={paymentMode} error={fieldError(errors, "payment_mode")} onChange={setPaymentMode} placeholder="Search and select payment mode" /><ReadOnlyField label="Policy Term" value={plan?.policy_term_years ? `${plan.policy_term_years} years` : "—"} /><ReadOnlyField label="Total Number of Installments" value={rows.length} /></FormGrid><div className="grid gap-3 rounded-[10px] border bg-[var(--muted)]/25 p-4 md:grid-cols-2"><Toggle label="After Maturity Benefits" checked={afterMaturity} onChange={setAfterMaturity} hint="Include installment payouts after the maturity date." /><Toggle label="Before Maturity Benefits" checked={beforeMaturity} onChange={setBeforeMaturity} hint="Include installment payouts before the maturity date." /></div><InstallmentRateGrid rows={rows} onChange={setRows} error={fieldError(errors, "rate_rows") || (Math.abs(total - 100) >= 0.0001 ? "Installment rates must sum exactly to 100." : undefined)} /></>}</div></Modal>
}

function InstallmentsStep({ rows, loading, selectedPlan, template, templateLoading, saving, errors, onConfigure, onCloseModal, onSave, modalOpen }: { rows: InstallmentPlanRow[]; loading: boolean; selectedPlan: InstallmentPlanRow | null; template: InstallmentTemplate | null; templateLoading: boolean; saving: boolean; errors: ApiFieldErrors; onConfigure: (plan: InstallmentPlanRow) => void; onCloseModal: () => void; onSave: (payload: { annuity_period_years: number; payment_mode: string; after_maturity_benefits: boolean; before_maturity_benefits: boolean; rate_rows: InstallmentRateRow[] }) => Promise<boolean>; modalOpen: boolean }) {
  return <div className="surface-card overflow-hidden"><StepHeader eyebrow="Step 4 of 7" title="Installments" description="Review installment requirements for each selected plan and configure the rate schedule when required." /><div className="p-5">{loading ? <div className="py-12 text-center text-sm text-[var(--muted-foreground)]"><LoaderCircle className="mx-auto mb-2 animate-spin" size={22} aria-hidden="true" />Loading installment requirements…</div> : rows.length ? <div className="overflow-x-auto rounded-[10px] border"><table className="w-full min-w-[800px] text-left text-sm"><thead className="bg-[var(--muted)]/35 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><tr><th className="px-3 py-3">Plan/Sub-Product</th><th className="px-3 py-3">Policy Term (Years)</th><th className="px-3 py-3">Payment Mode</th><th className="px-3 py-3">No. of Installments</th><th className="px-3 py-3">Status</th><th className="px-3 py-3"><span className="sr-only">Action</span></th></tr></thead><tbody className="divide-y divide-[var(--border)]">{rows.map((row) => <tr key={row.plan_configuration_id}><td className="px-3 py-3"><p className="font-semibold">{row.plan_code}</p><p className="text-xs text-[var(--muted-foreground)]">{row.plan_name}</p></td><td className="px-3 py-3">{row.policy_term_years}</td><td className="px-3 py-3">{row.payment_mode || "—"}</td><td className="px-3 py-3">{row.total_number_of_installments}</td><td className="px-3 py-3"><span className={`rounded-full border px-2.5 py-1 text-xs font-bold ${row.status === "CONFIGURED" ? "border-[var(--success)]/40 text-[var(--success)]" : "border-[var(--warning)]/50 text-[var(--warning)]"}`}>{row.status === "CONFIGURED" ? "Configured" : "Ready to Configure"}</span></td><td className="px-3 py-3 text-right"><button type="button" className="button-secondary !min-h-9 !px-3" disabled={!row.can_configure} onClick={() => onConfigure(row)}>{row.status === "CONFIGURED" ? "Edit" : "Configure"}<ChevronRight size={14} aria-hidden="true" /></button></td></tr>)}</tbody></table></div> : <div className="rounded-[10px] border border-dashed p-8 text-center text-sm text-[var(--muted-foreground)]">Select plans in Step 2 to configure installments.</div>}</div><ConfigureInstallmentModal open={modalOpen} plan={selectedPlan} template={template} loading={templateLoading} saving={saving} errors={errors} onClose={onCloseModal} onSave={onSave} /></div>
}

function InvestmentFundsStep({ quotation, state, optionsByPlan, allocations, errors, onChange, onSave }: { quotation: Quotation; state: InvestmentFundState | null; optionsByPlan: Record<string, InvestmentFundOptions>; allocations: Record<string, FundAllocation[]>; errors: ApiFieldErrors; onChange: (planConfigId: string, rows: FundAllocation[]) => void; onSave: () => Promise<boolean> }) {
  const applicableRows = state?.plan_rows.filter((row) => row.investment_linked) ?? []
  return <div className="surface-card overflow-hidden"><StepHeader eyebrow="Step 5 of 7" title="Investment Funds" description="Allocate investment-linked quotation amounts across active, currency-compatible funds." /><div className="space-y-5 p-5">{state?.not_applicable && <InfoBanner title="Not applicable">The selected plans are not investment-linked, so investment fund allocation is not required.</InfoBanner>}{state?.requires_allocation === false && !state?.not_applicable && <InfoBanner title="Investment funds configured">All applicable investment-linked plans have valid 100% allocations.</InfoBanner>}{applicableRows.map((plan) => { const options = optionsByPlan[plan.plan_configuration_id]?.funds ?? []; const rows = allocations[plan.plan_configuration_id] ?? []; const total = rows.reduce((sum, row) => sum + (Number(row.allocation_percent) || 0), 0); return <section key={plan.plan_configuration_id} className="rounded-[12px] border"><div className="flex flex-wrap items-center justify-between gap-3 border-b bg-[var(--muted)]/35 px-4 py-3"><div><p className="text-[11px] font-bold uppercase tracking-[0.14em] text-[var(--muted-foreground)]">{plan.plan_code}</p><h3 className="mt-1 font-bold">{plan.plan_name}</h3></div><span className={`rounded-full border px-3 py-1 text-xs font-bold ${plan.status === "CONFIGURED" ? "border-[var(--success)]/40 text-[var(--success)]" : "border-[var(--warning)]/50 text-[var(--warning)]"}`}>{plan.status === "CONFIGURED" ? "Configured" : "Ready to Configure"}</span></div><div className="space-y-4 p-4"><div className="flex items-center justify-between text-sm"><span className="font-semibold">Allocation total</span><span className={Math.abs(total - 100) < 0.0001 ? "font-bold text-[var(--success)]" : "font-bold text-[var(--destructive)]"}>{total.toFixed(2)} / 100.00%</span></div><div className="overflow-x-auto rounded-[10px] border"><table className="w-full min-w-[760px] text-left text-sm"><thead className="bg-[var(--muted)]/30 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><tr><th className="px-3 py-3">Investment Fund</th><th className="px-3 py-3">Risk Profile</th><th className="px-3 py-3">Currency</th><th className="px-3 py-3">Allocation (%)</th><th className="px-3 py-3">Allocated Amount</th><th className="px-3 py-3"><span className="sr-only">Remove</span></th></tr></thead><tbody className="divide-y divide-[var(--border)]">{rows.map((row, index) => { const option = options.find((item) => item.id === row.fund_id); return <tr key={`${plan.plan_configuration_id}-${index}`}><td className="px-3 py-2"><SmartSelect entity="investment-funds" label="" name={`fund_${plan.plan_configuration_id}_${index}`} value={row.fund_id} onChange={(value) => { const selected = options.find((fund) => fund.id === value); onChange(plan.plan_configuration_id, rows.map((item, rowIndex) => rowIndex === index ? { ...item, fund_id: value, fund_name: selected?.name, fund_code: selected?.code } : item)) }} error={fieldError(errors, `fund_${plan.plan_configuration_id}_${index}`)} placeholder="Search and select investment fund" emptyEntityLabel="investment fund" /></td><td className="px-3 py-2">{option?.risk_profile ?? "—"}</td><td className="px-3 py-2">{option?.currency ?? quotation.currency ?? "—"}</td><td className="px-3 py-2"><input aria-label={`Allocation percentage ${index + 1}`} type="number" step="0.0001" min="0" max="100" value={String(row.allocation_percent)} onChange={(event) => onChange(plan.plan_configuration_id, rows.map((item, rowIndex) => rowIndex === index ? { ...item, allocation_percent: event.target.value } : item))} className="h-10 w-full rounded-[10px] border bg-[var(--card)] px-3 text-sm outline-none focus:border-[var(--ring)]" /></td><td className="px-3 py-2"><input aria-label={`Allocated amount ${index + 1}`} type="number" step="0.01" min="0" value={row.allocated_amount == null ? "" : String(row.allocated_amount)} onChange={(event) => onChange(plan.plan_configuration_id, rows.map((item, rowIndex) => rowIndex === index ? { ...item, allocated_amount: event.target.value } : item))} className="h-10 w-full rounded-[10px] border bg-[var(--card)] px-3 text-sm outline-none focus:border-[var(--ring)]" /></td><td className="px-3 py-2"><button type="button" className="rounded-md p-2 text-[var(--destructive)]" aria-label={`Remove fund allocation ${index + 1}`} onClick={() => onChange(plan.plan_configuration_id, rows.filter((_, rowIndex) => rowIndex !== index))}><Trash2 size={15} aria-hidden="true" /></button></td></tr>})}</tbody></table></div>{fieldError(errors, "allocations") && <p className="text-sm font-semibold text-[var(--destructive)]" role="alert">{fieldError(errors, "allocations")}</p>}<button type="button" className="button-secondary" onClick={() => onChange(plan.plan_configuration_id, [...rows, { plan_config_id: plan.plan_configuration_id, fund_id: "", allocation_percent: "", allocated_amount: null }])}><Plus size={15} aria-hidden="true" />Add fund</button></div></section>})}{!state?.not_applicable && applicableRows.length > 0 && <div className="flex justify-end"><button type="button" className="button-primary" onClick={() => void onSave()}>Save fund allocations</button></div>}</div></div>
}

function formatMoney(value: string | number | null | undefined, currency = "TZS") {
  const amount = Number(value ?? 0)
  return `${currency} ${Number.isFinite(amount) ? amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "0.00"}`
}

function RiderPlanEditor({ row, options, errors, onSave }: { row: RiderPlanRow; options: RiderOptions | null; errors: ApiFieldErrors; onSave: (planConfigId: string, selections: RiderSelection[]) => Promise<boolean> }) {
  const [selections, setSelections] = useState<RiderSelection[]>(row.riders ?? [])
  useEffect(() => setSelections(row.riders ?? []), [row.riders])
  const available = options?.riders ?? row.available_riders ?? []
  const selectedIds = new Set(selections.map((selection) => selection.rider_id))
  const addRider = (option: RiderOption) => setSelections((current) => current.some((selection) => selection.rider_id === option.id) ? current : [...current, { rider_id: option.id, plan_config_id: row.plan_configuration_id, rider_code: option.code, rider_name: option.name, rider_category: option.rider_category, benefit_type: option.benefit_type, rider_sum_assured: "", rider_term_years: null, waiting_period_days: option.waiting_period_days, requires_underwriting: option.requires_underwriting, synchronized_option: option.synchronized_option, benefit_basis: "FIXED", benefit_value: "", loading: 0, discount: 0, maximum_cap: "", benefits: [] }])
  const addRiderFromOption = (selected: SmartOption) => {
    const existing = available.find((option) => option.id === selected.value)
    if (existing) { addRider(existing); return }
    const meta = selected.meta ?? {}
    addRider({
      id: selected.value,
      code: String(meta.code ?? meta.rider_code ?? selected.label),
      name: selected.label,
      rider_category: String(meta.rider_category ?? meta.category ?? "GENERAL"),
      benefit_type: String(meta.benefit_type ?? "FIXED"),
      calculation_basis: String(meta.calculation_basis ?? "FIXED"),
      min_age: Number(meta.min_age ?? 0),
      max_age: Number(meta.max_age ?? 120),
      min_term: Number(meta.min_term ?? 1),
      max_term: Number(meta.max_term ?? 99),
      min_sum_assured: (meta.min_sum_assured as string | number | null | undefined) ?? null,
      max_sum_assured: (meta.max_sum_assured as string | number | null | undefined) ?? null,
      waiting_period_days: Number(meta.waiting_period_days ?? 0),
      allows_standalone: Boolean(meta.allows_standalone ?? false),
      requires_underwriting: Boolean(meta.requires_underwriting ?? false),
      product_id: (meta.product_id as string | null | undefined) ?? null,
      plan_id: (meta.plan_id as string | null | undefined) ?? null,
      selectable: true,
      synchronized_option: String(meta.synchronized_option ?? ""),
    })
  }
  const update = (index: number, patch: Partial<RiderSelection>) => setSelections((current) => current.map((selection, selectionIndex) => selectionIndex === index ? { ...selection, ...patch } : selection))
  const updateBenefit = (index: number, patch: Partial<RiderBenefit>) => setSelections((current) => current.map((selection, selectionIndex) => selectionIndex === index ? { ...selection, benefits: [{ ...(selection.benefits?.[0] ?? { basis: selection.benefit_basis ?? "FIXED" }), ...patch }] } : selection))
  return <section className="rounded-[12px] border bg-[var(--card)]"><div className="flex flex-wrap items-center justify-between gap-3 border-b bg-[var(--muted)]/35 px-4 py-3"><div><p className="text-[11px] font-bold uppercase tracking-[0.14em] text-[var(--muted-foreground)]">{row.plan_code}</p><h3 className="mt-1 font-bold">{row.plan_name}</h3></div><div className="flex flex-wrap gap-2">{row.personal_accident && <span className="rounded-full border px-2.5 py-1 text-xs font-semibold">PA synchronized</span>}{row.premium_waiver && <span className="rounded-full border px-2.5 py-1 text-xs font-semibold">WP synchronized</span>}</div></div><div className="space-y-5 p-4"><div><div className="mb-3 flex items-center justify-between"><div><h4 className="font-bold">Applicable Riders</h4><p className="text-xs text-[var(--muted-foreground)]">Riders are filtered by the selected plan, age, term, and underwriting rules.</p></div></div><div className="mb-4"><SmartSelect entity="riders" label="Rider" name={`rider_picker_${row.plan_configuration_id}`} required placeholder="Search and select rider" emptyEntityLabel="rider" onOptionChange={addRiderFromOption} /></div><div className="grid gap-2 md:grid-cols-2">{available.map((option) => { const selected = selectedIds.has(option.id); return <button key={option.id} type="button" aria-pressed={selected} disabled={!option.selectable || selected} onClick={() => addRider(option)} className={`rounded-[10px] border p-3 text-left ${selected ? "border-[var(--success)] bg-[var(--muted)]/35" : option.selectable ? "hover:border-[var(--ring)]" : "cursor-not-allowed opacity-50"}`}><div className="flex items-start justify-between gap-3"><div><div className="flex flex-wrap gap-2"><span className="rounded-md bg-[var(--muted)] px-2 py-0.5 text-[10px] font-bold">{option.code}</span><span className="rounded-md border px-2 py-0.5 text-[10px] font-semibold">{option.rider_category}</span><span className="rounded-md border px-2 py-0.5 text-[10px] font-semibold">{option.benefit_type}</span></div><p className="mt-2 text-sm font-bold">{option.name}</p><p className="mt-1 text-xs text-[var(--muted-foreground)]">Waiting period: {option.waiting_period_days} days · Ages {option.min_age}–{option.max_age}</p></div>{selected && <Check size={18} className="text-[var(--success)]" aria-label="Attached" />}</div></button>})}</div></div>{selections.length ? <div className="space-y-3"><h4 className="font-bold">Attached Riders & Benefits</h4>{selections.map((selection, index) => { const option = available.find((item) => item.id === selection.rider_id); const benefit = selection.benefits?.[0] ?? { basis: selection.benefit_basis ?? "FIXED", value: selection.benefit_value ?? "", maximum_cap: selection.maximum_cap ?? null }; return <div key={`${selection.rider_id}-${index}`} className="rounded-[10px] border p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><div className="flex flex-wrap gap-2"><span className="rounded-md bg-[var(--muted)] px-2 py-0.5 text-[10px] font-bold">{selection.rider_code ?? option?.code}</span><span className="rounded-md border px-2 py-0.5 text-[10px] font-semibold">{selection.rider_category ?? option?.rider_category}</span>{selection.synchronized_option && <span className="rounded-md border px-2 py-0.5 text-[10px] font-semibold">{selection.synchronized_option} synchronized</span>}</div><h5 className="mt-2 font-bold">{selection.rider_name ?? option?.name}</h5><p className="mt-1 text-xs text-[var(--muted-foreground)]">Waiting period: {selection.waiting_period_days ?? option?.waiting_period_days ?? 0} days{selection.requires_underwriting ? " · Underwriting required" : ""}</p></div><button type="button" className="rounded-md p-2 text-[var(--destructive)] hover:bg-[var(--destructive)]/10" aria-label={`Detach ${selection.rider_name ?? option?.name ?? "rider"}`} onClick={() => setSelections((current) => current.filter((_, selectionIndex) => selectionIndex !== index))}><Trash2 size={16} aria-hidden="true" /></button></div><div className="mt-4 grid gap-4 md:grid-cols-2"><DecimalInput label="Rider Sum Assured / Amount" name={`rider_sum_assured_${index}`} required value={String(selection.rider_sum_assured ?? "")} error={fieldError(errors, "rider_sum_assured")} onChange={(event) => update(index, { rider_sum_assured: event.target.value })} /><TextInput label="Rider Term (Years)" name={`rider_term_${index}`} type="number" min={1} value={selection.rider_term_years == null ? "" : String(selection.rider_term_years)} error={fieldError(errors, "rider_term_years")} onChange={(event) => update(index, { rider_term_years: event.target.value === "" ? null : Number(event.target.value) })} /></div><div className="mt-4 rounded-[10px] border bg-[var(--muted)]/20 p-3"><div className="mb-3 flex items-center justify-between"><h6 className="text-sm font-bold">Benefits</h6><span className="text-xs text-[var(--muted-foreground)]">Backend rating applies the configured basis.</span></div><div className="grid gap-4 md:grid-cols-3"><SmartSelect entity="benefit-types" label="Benefit Type" name={`benefit_type_${index}`} required value={String(benefit.beneficial_type_id ?? benefit.benefit_type ?? "")} error={fieldError(errors, "beneficial_type_id")} onChange={(value) => updateBenefit(index, { beneficial_type_id: value })} /><ChoiceSelect label="Basis" name={`benefit_basis_${index}`} required value={String(benefit.basis ?? "FIXED")} options={["FIXED", "RATIO", "LOADED", "DISCOUNTED", "CAPPED"].map((value) => ({ value, label: value }))} error={fieldError(errors, "benefit_basis")} onChange={(value) => update(index, { benefit_basis: value, benefits: [{ ...benefit, basis: value }] })} /><DecimalInput label="Value" name={`benefit_value_${index}`} value={benefit.value == null ? "" : String(benefit.value)} error={fieldError(errors, "benefit_value")} onChange={(event) => update(index, { benefit_value: event.target.value, benefits: [{ ...benefit, value: event.target.value }] })} /><DecimalInput label="Maximum Cap" name={`benefit_cap_${index}`} value={benefit.maximum_cap == null ? "" : String(benefit.maximum_cap)} error={fieldError(errors, "maximum_cap")} onChange={(event) => update(index, { maximum_cap: event.target.value, benefits: [{ ...benefit, maximum_cap: event.target.value }] })} /></div></div></div>})}</div> : <div className="rounded-[10px] border border-dashed p-6 text-center text-sm text-[var(--muted-foreground)]">No riders attached to this plan.</div>}<div className="flex justify-end"><button type="button" className="button-primary" onClick={() => void onSave(row.plan_configuration_id, selections)}><Save size={15} aria-hidden="true" />Save rider configuration</button></div></div></section>
}

function RidersBenefitsStep({ state, optionsByPlan, errors, onSave }: { state: RiderState | null; optionsByPlan: Record<string, RiderOptions>; errors: ApiFieldErrors; onSave: (planConfigId: string, selections: RiderSelection[]) => Promise<boolean> }) {
  return <div className="surface-card overflow-hidden"><StepHeader eyebrow="Step 6 of 7" title="Riders & Benefits" description="Attach applicable riders and configure benefits. Premium previews are produced by the backend rating engine." /><div className="space-y-5 p-5">{state?.requires_configuration === false && <InfoBanner title="No rider configuration required">The selected plans do not require additional rider configuration.</InfoBanner>}{(state?.plan_rows ?? []).map((row) => <RiderPlanEditor key={row.plan_configuration_id} row={row} options={optionsByPlan[row.plan_configuration_id] ?? null} errors={errors} onSave={onSave} />)}</div></div>
}

function FinancialDetailsStep({ summary, loading, calculating, onCalculate }: { summary: FinancialDetails | null; loading: boolean; calculating: boolean; onCalculate: () => Promise<boolean> }) {
  const currency = summary?.currency ?? "TZS"
  const cards = [{ label: "Base Premium", value: summary?.base_premium }, { label: "Rider Premiums", value: summary?.total_rider_premium }, { label: "Loadings", value: summary?.total_loading }, { label: "Discounts", value: summary?.total_discount }, { label: "Taxes", value: summary?.total_tax }, { label: "Total Premium", value: summary?.total_premium }]
  return <div className="space-y-4"><div className="surface-card overflow-hidden"><StepHeader eyebrow="Step 7 of 7" title="Financial Details" description="Review premiums, projections, and installment payouts returned by the OL rating engine." /><div className="space-y-5 p-5">{summary?.recalculation_required && <InfoBanner title="Recalculation required">Quotation inputs changed after the last calculation. Recalculate before finalizing.</InfoBanner>}<div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-sm font-semibold">{summary?.calculated_at ? `Calculated ${new Date(summary.calculated_at).toLocaleString()}` : "No current calculation"}</p><p className="text-xs text-[var(--muted-foreground)]">Premiums and projections are display-only outputs from the backend rating engine.</p></div><button type="button" className="button-primary" onClick={() => void onCalculate()} disabled={loading || calculating}>{calculating ? <><LoaderCircle size={15} className="animate-spin" aria-hidden="true" />Calculating…</> : <><RotateCcw size={15} aria-hidden="true" />{summary ? "Recalculate" : "Calculate"}</>}</button></div>{loading ? <div className="py-10 text-center text-sm text-[var(--muted-foreground)]"><LoaderCircle className="mx-auto mb-2 animate-spin" size={22} aria-hidden="true" />Loading financial summary…</div> : summary ? <><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{cards.map((card) => <div key={card.label} className="rounded-[10px] border bg-[var(--muted)]/20 p-4"><p className="text-xs font-semibold text-[var(--muted-foreground)]">{card.label}</p><p className={`mt-2 text-lg font-extrabold ${card.label === "Total Premium" ? "text-[var(--primary)]" : ""}`}>{formatMoney(card.value, currency)}</p><p className="mt-1 text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">{summary.currency ?? "TZS"} · quotation frequency applied by engine</p></div>)}</div><div className="rounded-[12px] border border-[var(--primary)]/40 bg-[var(--primary)]/5 p-4"><p className="text-xs font-bold uppercase tracking-[0.12em] text-[var(--muted-foreground)]">Estimated Maturity Value</p><p className="mt-1 text-2xl font-extrabold">{formatMoney(summary.estimated_maturity_value, currency)}</p></div><div><h3 className="mb-3 font-bold">Policy-Year Projections</h3><div className="overflow-x-auto rounded-[10px] border"><table className="w-full min-w-[800px] text-left text-sm"><thead className="bg-[var(--muted)]/35 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><tr><th className="px-3 py-3">Policy Year</th><th className="px-3 py-3">Premiums Paid</th><th className="px-3 py-3">Bonuses</th><th className="px-3 py-3">Surrender Value</th><th className="px-3 py-3">Paid-Up Value</th></tr></thead><tbody className="divide-y divide-[var(--border)]">{(summary.projections ?? []).map((row) => <tr key={`${row.plan_configuration_id ?? "all"}-${row.policy_year}`}><td className="px-3 py-3 font-semibold">{row.policy_year}</td><td className="px-3 py-3">{formatMoney(row.premiums_paid, currency)}</td><td className="px-3 py-3">{formatMoney(row.estimated_bonus, currency)}</td><td className="px-3 py-3">{formatMoney(row.surrender_value, currency)}</td><td className="px-3 py-3">{formatMoney(row.paid_up_value, currency)}</td></tr>)}</tbody></table></div></div><div><h3 className="mb-3 font-bold">Installment Payout Schedule</h3><div className="overflow-x-auto rounded-[10px] border"><table className="w-full min-w-[800px] text-left text-sm"><thead className="bg-[var(--muted)]/35 text-xs uppercase tracking-[0.08em] text-[var(--muted-foreground)]"><tr><th className="px-3 py-3">Installment #</th><th className="px-3 py-3">Date</th><th className="px-3 py-3">Description</th><th className="px-3 py-3">Rate %</th><th className="px-3 py-3">Payout Amount</th></tr></thead><tbody className="divide-y divide-[var(--border)]">{(summary.installment_payouts ?? []).map((row) => <tr key={`${row.installment_configuration_id ?? "payout"}-${row.sequence}`}><td className="px-3 py-3 font-semibold">{row.sequence}</td><td className="px-3 py-3">{row.payout_date}</td><td className="px-3 py-3">{row.description ?? "—"}</td><td className="px-3 py-3">{row.rate_percent}</td><td className="px-3 py-3">{formatMoney(row.payout_amount, currency)}</td></tr>)}</tbody></table></div></div></> : <div className="rounded-[10px] border border-dashed p-8 text-center text-sm text-[var(--muted-foreground)]">Calculate the quotation to view financial details.</div>}</div></div></div>
}

function ReviewFinalize({ completedSteps, invalidSteps, errors, onJump, onFinalize, disabled }: { completedSteps: Set<number>; invalidSteps: Set<number>; errors: Record<string, unknown>; onJump: (step: number) => void; onFinalize: () => Promise<boolean>; disabled: boolean }) {
  const [confirmOpen, setConfirmOpen] = useState(false)
  const checklist = steps.map((step, index) => ({ ...step, index, complete: completedSteps.has(index) }))
  const errorEntries = Object.entries(errors)
  return <div className="surface-card overflow-hidden"><div className="border-b bg-[var(--muted)]/35 px-5 py-4"><h3 className="text-lg font-bold">Review & Finalize</h3><p className="mt-1 text-sm text-[var(--muted-foreground)]">Confirm that every required wizard step is complete before finalizing this quotation.</p></div><div className="space-y-5 p-5"><div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">{checklist.map((item) => <button type="button" key={item.id} className={`flex items-center gap-3 rounded-[10px] border p-3 text-left ${item.complete ? "border-[var(--success)]/50" : "border-[var(--border)]"}`} onClick={() => onJump(item.index)}><span className={item.complete ? "text-[var(--success)]" : "text-[var(--muted-foreground)]"}>{item.complete ? <Check size={17} aria-hidden="true" /> : <CircleAlert size={17} aria-hidden="true" />}</span><span className="text-sm font-semibold">{item.label}</span></button>)}</div>{invalidSteps.size > 0 && <div className="rounded-[10px] border border-[var(--destructive)]/40 bg-[var(--destructive)]/5 p-4"><p className="font-bold text-[var(--destructive)]">Please resolve the following steps:</p><ul className="mt-2 space-y-1 text-sm">{Array.from(invalidSteps).map((step) => <li key={step}><button type="button" className="underline" onClick={() => onJump(step)}>Go to {steps[step]?.label ?? "step"}</button></li>)}</ul></div>}{errorEntries.length > 0 && <div className="rounded-[10px] border border-[var(--destructive)]/40 p-4" role="alert"><p className="font-bold text-[var(--destructive)]">Finalize validation errors</p><ul className="mt-2 space-y-1 text-sm">{errorEntries.map(([key, value]) => <li key={key}><button type="button" className="mr-2 underline" onClick={() => onJump(key === "financial_details" ? 6 : Number(key) || 0)}>Review</button>{Array.isArray(value) ? value.join(", ") : String(value)}</li>)}</ul></div>}<div className="flex justify-end"><button type="button" className="button-primary" disabled={disabled} onClick={() => setConfirmOpen(true)}><Check size={15} aria-hidden="true" />Finalize quotation</button></div></div><Modal open={confirmOpen} title="Finalize quotation" description="Finalizing locks the current quotation version for downstream printing and conversion." onClose={() => setConfirmOpen(false)} footer={<><button type="button" className="button-secondary" onClick={() => setConfirmOpen(false)}>Cancel</button><button type="button" className="button-primary" onClick={() => void onFinalize().then((ok) => { if (ok) setConfirmOpen(false) })}>Confirm finalize</button></>}><p className="text-sm text-[var(--muted-foreground)]">Are you sure you want to finalize this quotation?</p></Modal></div>
}

function FutureStep({ step, index }: { step: string; index: number }) {
  return <div className="surface-card overflow-hidden"><StepHeader eyebrow={`Step ${index + 1} of 7`} title={step} description="This wizard step is reserved for the next quotation module increment." /><div className="p-5"><div className="rounded-[10px] border border-dashed p-8 text-center text-sm text-[var(--muted-foreground)]">Complete the Personal Details and Plan & Sub-Products steps first. Your draft will remain available to resume later.</div></div></div>
}

export default function OLQuotationWizard() {
  const navigate = useNavigate()
  const { id: routeId } = useParams()
  const { toast } = useToast()
  const [quotation, setQuotation] = useState<Quotation | null>(null)
  const [quotationId, setQuotationId] = useState(routeId ?? "")
  const [activeStep, setActiveStep] = useState(0)
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set())
  const [invalidSteps, setInvalidSteps] = useState<Set<number>>(new Set())
  const [personal, setPersonal] = useState<PersonalForm>(initialPersonal())
  const [personalOptions, setPersonalOptions] = useState<{ identityTypes: Choice[]; genders: Choice[]; smokerStatuses: Choice[]; locations: Choice[]; agents: Choice[] }>({ identityTypes: [], genders: [], smokerStatuses: [], locations: [], agents: [] })
  const [personalErrors, setPersonalErrors] = useState<ApiFieldErrors>({})
  const [plans, setPlans] = useState<PlanCard[]>([])
  const [planSearch, setPlanSearch] = useState("")
  const [plansLoading, setPlansLoading] = useState(false)
  const [selectedPlanIds, setSelectedPlanIds] = useState<string[]>([])
  const [configurations, setConfigurations] = useState<PlanConfiguration[]>([])
  const [planOptions, setPlanOptions] = useState<PlanOptions>({ payment_frequencies: [], quote_bases: [], premium_factors: [] })
  const [planErrors, setPlanErrors] = useState<Record<string, ApiFieldErrors>>({})
  const [memberState, setMemberState] = useState<MemberCoverageState | null>(null)
  const [memberErrors, setMemberErrors] = useState<ApiFieldErrors>({})
  const [installmentState, setInstallmentState] = useState<InstallmentState | null>(null)
  const [installmentTemplate, setInstallmentTemplate] = useState<InstallmentTemplate | null>(null)
  const [installmentTemplateLoading, setInstallmentTemplateLoading] = useState(false)
  const [installmentModalOpen, setInstallmentModalOpen] = useState(false)
  const [selectedInstallmentPlan, setSelectedInstallmentPlan] = useState<InstallmentPlanRow | null>(null)
  const [installmentErrors, setInstallmentErrors] = useState<ApiFieldErrors>({})
  const [fundState, setFundState] = useState<InvestmentFundState | null>(null)
  const [fundOptions, setFundOptions] = useState<Record<string, InvestmentFundOptions>>({})
  const [fundAllocations, setFundAllocations] = useState<Record<string, FundAllocation[]>>({})
  const [fundErrors, setFundErrors] = useState<ApiFieldErrors>({})
  const [riderState, setRiderState] = useState<RiderState | null>(null)
  const [riderOptions, setRiderOptions] = useState<Record<string, RiderOptions>>({})
  const [riderSelections, setRiderSelections] = useState<Record<string, RiderSelection[]>>({})
  const [riderErrors, setRiderErrors] = useState<ApiFieldErrors>({})
  const [financialSummary, setFinancialSummary] = useState<FinancialDetails | null>(null)
  const [financialLoading, setFinancialLoading] = useState(false)
  const [calculating, setCalculating] = useState(false)
  const [finalizeErrors, setFinalizeErrors] = useState<Record<string, unknown>>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [detailsOpen, setDetailsOpen] = useState(false)
  const [resumeNotice, setResumeNotice] = useState(false)

  const loadQuotation = useCallback(async (id: string) => {
    const payload = await requestNormalized<Quotation>(`${QUOTATION_PREFIX}${id}/`)
    setQuotation(payload)
    setQuotationId(id)
    setPersonal(initialPersonal(payload))
    const configs = payload.plan_configurations ?? []
    setConfigurations(configs)
    setSelectedPlanIds(configs.filter((config) => config.is_selected !== false).map((config) => configurationPlanId(config)).filter((value): value is string => Boolean(value)))
    const completion = payload.wizard_step_completion ?? {}
    const completionKeys = ["1_personal_details", "2_plan_and_sub_products", "3_member_coverage", "4_installments", "5_investment_funds", "6_riders_and_benefits", "7_financial_details"]
    setCompletedSteps(new Set(completionKeys.map((key, index) => completion[key] ? index : -1).filter((value) => value >= 0)))
  }, [])

  const createQuotation = useCallback(async () => {
    const saved = readDraftSnapshot()
    const explicitResume = new URLSearchParams(window.location.search).get("resume") === "1"
    if (!routeId && explicitResume && saved?.quotationId) {
      try {
        await loadQuotation(saved.quotationId)
        if (saved.personal) setPersonal(saved.personal)
        if (saved.configurations) setConfigurations(saved.configurations)
        if (saved.selectedPlanIds) setSelectedPlanIds(saved.selectedPlanIds)
        setResumeNotice(true)
        return
      } catch {
        localStorage.removeItem(LOCAL_DRAFT_KEY)
      }
    }
    if (routeId) {
      await loadQuotation(routeId)
      return
    }
    const payload = await requestNormalized<Quotation>(QUOTATION_PREFIX, { method: "POST", body: JSON.stringify({ currency: "TZS" }) })
    await loadQuotation(payload.id)
  }, [loadQuotation, routeId])

  useEffect(() => {
    let mounted = true
    setLoading(true)
    createQuotation().catch((error) => {
      if (!mounted) return
      const parsed = parseApiError(error)
      toast({ tone: "danger", title: "Unable to open quotation draft", message: parsed.message })
    }).finally(() => { if (mounted) setLoading(false) })
    return () => { mounted = false }
  }, [createQuotation, toast])

  const loadPersonalOptions = useCallback(async () => {
    const payload = await requestNormalized<ApiPayload>(`${QUOTATION_PREFIX}personal-details-options/`)
    let locations = asChoices(payload.locations)
    if (locations.length === 0) {
      const masterLocations = await requestNormalized<unknown>(LOCATION_MASTER_ENDPOINT)
      locations = asChoices(masterLocations)
    }
    setPersonalOptions({ identityTypes: asChoices(payload.identity_types), genders: asChoices(payload.genders), smokerStatuses: asChoices(payload.smoker_statuses), locations, agents: asChoices(payload.agents) })
  }, [])

  const loadPlans = useCallback(async (searchOverride?: string): Promise<PlanCard[]> => {
    if (!quotationId) return []
    setPlansLoading(true)
    try {
      const query = new URLSearchParams({ quotation_id: quotationId, limit: "200" })
      const effectiveSearch = searchOverride ?? planSearch
      if (effectiveSearch.trim()) query.set("search", effectiveSearch.trim())
      const payload = await requestNormalized<ApiPayload>(`${PLAN_SEARCH_ENDPOINT}?${query.toString()}`)
      const nextPlans = (payload.plans ?? []).map(normalizePlanCard).filter((plan): plan is PlanCard => Boolean(plan))
      setPlans(nextPlans)
      setSelectedPlanIds((current) => current.filter((planId) => nextPlans.some((plan) => plan.plan_id === planId)))
      return nextPlans
    } catch (error) {
      toast({ tone: "danger", title: "Unable to load plans", message: parseApiError(error).message })
      return []
    } finally { setPlansLoading(false) }
  }, [planSearch, quotationId, toast])

  useEffect(() => { if (quotationId) void loadPersonalOptions().catch((error) => toast({ tone: "danger", title: "Unable to load quotation options", message: parseApiError(error).message })) }, [loadPersonalOptions, quotationId, toast])
  useEffect(() => { void loadPlans() }, [loadPlans])

  const loadPlanOptions = useCallback(async (planId?: string) => {
    if (!quotationId) return
    try {
      const payload = await requestNormalized<ApiPayload>(`${QUOTATION_PREFIX}${quotationId}/plan-options/${planId ? `?plan_id=${encodeURIComponent(planId)}` : ""}`)
      setPlanOptions({ payment_frequencies: asChoices(payload.payment_frequencies), quote_bases: asChoices(payload.quote_bases), premium_factors: asChoices(payload.premium_factors), plan_features: payload.plan_features })
    } catch (error) {
      toast({ tone: "danger", title: "Unable to load plan options", message: parseApiError(error).message })
    }
  }, [quotationId, toast])

  const loadMemberCoverage = useCallback(async () => {
    if (!quotationId) return
    try {
      const payload = await requestNormalized<MemberCoverageState>(`${QUOTATION_PREFIX}${quotationId}/members/`)
      setMemberState(payload)
    } catch (error) {
      toast({ tone: "danger", title: "Unable to load member coverage", message: parseApiError(error).message })
    }
  }, [quotationId, toast])

  const loadInstallments = useCallback(async () => {
    if (!quotationId) return
    try {
      const payload = await requestNormalized<InstallmentState>(`${QUOTATION_PREFIX}${quotationId}/installments/`)
      setInstallmentState(payload)
    } catch (error) {
      toast({ tone: "danger", title: "Unable to load installments", message: parseApiError(error).message })
    }
  }, [quotationId, toast])

  const loadInstallmentTemplate = useCallback(async (plan: InstallmentPlanRow) => {
    if (!quotationId) return
    setSelectedInstallmentPlan(plan)
    setInstallmentTemplate(null)
    setInstallmentErrors({})
    setInstallmentModalOpen(true)
    setInstallmentTemplateLoading(true)
    try {
      const payload = await requestNormalized<InstallmentTemplate>(`${QUOTATION_PREFIX}${quotationId}/installments/${plan.plan_configuration_id}/template/`)
      setInstallmentTemplate(payload)
    } catch (error) {
      setInstallmentErrors(parseApiError(error).fieldErrors)
      toast({ tone: "danger", title: "Unable to load installment template", message: parseApiError(error).message })
    } finally {
      setInstallmentTemplateLoading(false)
    }
  }, [quotationId, toast])

  const saveInstallment = useCallback(async (payload: { annuity_period_years: number; payment_mode: string; after_maturity_benefits: boolean; before_maturity_benefits: boolean; rate_rows: InstallmentRateRow[] }) => {
    if (!quotationId || !selectedInstallmentPlan) return false
    const total = payload.rate_rows.reduce((sum, row) => sum + (Number(row.rate_percent) || 0), 0)
    if (Math.abs(total - 100) >= 0.0001) {
      setInstallmentErrors({ rate_rows: ["Installment rates must sum exactly to 100."] })
      return false
    }
    setSaving(true)
    setInstallmentErrors({})
    try {
      await requestNormalized(`${QUOTATION_PREFIX}${quotationId}/installments/${selectedInstallmentPlan.plan_configuration_id}/configure/`, { method: "POST", body: JSON.stringify(payload) })
      await loadInstallments()
      setCompletedSteps((current) => new Set(current).add(3))
      toast({ tone: "success", title: "Installments configured" })
      return true
    } catch (error) {
      const parsed = parseApiError(error)
      setInstallmentErrors(parsed.fieldErrors)
      toast({ tone: "danger", title: "Installment configuration needs attention", message: parsed.message })
      return false
    } finally { setSaving(false) }
  }, [loadInstallments, quotationId, selectedInstallmentPlan, toast])

  const loadInvestmentFunds = useCallback(async () => {
    if (!quotationId) return
    try {
      const payload = await requestNormalized<InvestmentFundState>(`${QUOTATION_PREFIX}${quotationId}/investment-funds/`)
      setFundState(payload)
      const nextAllocations: Record<string, FundAllocation[]> = {}
      for (const row of payload.plan_rows ?? []) nextAllocations[row.plan_configuration_id] = row.allocations ?? []
      setFundAllocations(nextAllocations)
      const applicable = (payload.plan_rows ?? []).filter((row) => row.investment_linked)
      await Promise.all(applicable.map(async (row) => {
        try {
          const options = await requestNormalized<InvestmentFundOptions>(`${QUOTATION_PREFIX}${quotationId}/investment-funds/options/?plan_config_id=${encodeURIComponent(row.plan_configuration_id)}`)
          setFundOptions((current) => ({ ...current, [row.plan_configuration_id]: options }))
        } catch (error) {
          toast({ tone: "danger", title: "Unable to load investment funds", message: parseApiError(error).message })
        }
      }))
    } catch (error) {
      toast({ tone: "danger", title: "Unable to load investment fund allocations", message: parseApiError(error).message })
    }
  }, [quotationId, toast])

  const loadRiders = useCallback(async () => {
    if (!quotationId) return
    try {
      const payload = await requestNormalized<ApiPayload>(`${QUOTATION_PREFIX}${quotationId}/riders/`)
      const state = (payload.state as RiderState | undefined) ?? { plan_rows: payload.plan_rows ?? [], available_benefit_types: payload.available_benefit_types ?? [], requires_configuration: payload.requires_configuration ?? false, wizard_complete: payload.wizard_complete ?? false }
      setRiderState(state)
      const nextSelections: Record<string, RiderSelection[]> = {}
      for (const row of state.plan_rows ?? []) nextSelections[row.plan_configuration_id] = row.riders ?? []
      setRiderSelections(nextSelections)
      await Promise.all((state.plan_rows ?? []).map(async (row) => {
        try {
          const options = await requestNormalized<RiderOptions>(`${QUOTATION_PREFIX}${quotationId}/riders/options/?plan_config_id=${encodeURIComponent(row.plan_configuration_id)}`)
          setRiderOptions((current) => ({ ...current, [row.plan_configuration_id]: options }))
        } catch (error) {
          toast({ tone: "danger", title: "Unable to load rider options", message: parseApiError(error).message })
        }
      }))
    } catch (error) {
      toast({ tone: "danger", title: "Unable to load riders", message: parseApiError(error).message })
    }
  }, [quotationId, toast])

  const saveRiders = useCallback(async (planConfigId: string, selections: RiderSelection[]) => {
    if (!quotationId) return false
    const nextSelections = { ...riderSelections, [planConfigId]: selections.map((selection) => ({ ...selection, plan_config_id: planConfigId })) }
    const payloadSelections = Object.values(nextSelections).flat().map((selection) => ({ rider_id: selection.rider_id, plan_config_id: selection.plan_config_id, rider_sum_assured: selection.rider_sum_assured, rider_term_years: selection.rider_term_years, beneficial_type_id: selection.benefits?.[0]?.beneficial_type_id ?? null, benefit_basis: selection.benefit_basis ?? "FIXED", benefit_value: selection.benefit_value, loading: selection.loading ?? 0, discount: selection.discount ?? 0, maximum_cap: selection.maximum_cap, benefits: selection.benefits ?? [] }))
    setSaving(true)
    setRiderErrors({})
    try {
      await requestNormalized(`${QUOTATION_PREFIX}${quotationId}/riders/`, { method: "POST", body: JSON.stringify({ selections: payloadSelections }) })
      setRiderSelections(nextSelections)
      await loadRiders()
      setCompletedSteps((current) => new Set(current).add(5))
      toast({ tone: "success", title: "Rider configuration saved" })
      return true
    } catch (error) {
      const parsed = parseApiError(error)
      setRiderErrors(parsed.fieldErrors)
      setInvalidSteps((current) => new Set(current).add(5))
      toast({ tone: "danger", title: "Rider configuration needs attention", message: parsed.message })
      return false
    } finally { setSaving(false) }
  }, [loadRiders, quotationId, riderSelections, toast])

  const loadFinancialSummary = useCallback(async () => {
    if (!quotationId) return
    setFinancialLoading(true)
    try {
      const payload = await requestNormalized<ApiPayload>(`${QUOTATION_PREFIX}${quotationId}/financial-details/`)
      setFinancialSummary(payload.summary ?? (payload.total_premium != null ? payload as unknown as FinancialDetails : null))
    } catch (error) {
      toast({ tone: "danger", title: "Unable to load financial details", message: parseApiError(error).message })
    } finally { setFinancialLoading(false) }
  }, [quotationId, toast])

  const calculateFinancials = useCallback(async () => {
    if (!quotationId) return false
    setCalculating(true)
    try {
      const payload = await requestNormalized<FinancialDetails>(`${QUOTATION_PREFIX}${quotationId}/calculate/`, { method: "POST", body: JSON.stringify({}) })
      setFinancialSummary(payload)
      setCompletedSteps((current) => new Set(current).add(6))
      setInvalidSteps((current) => { const next = new Set(current); next.delete(6); return next })
      toast({ tone: "success", title: "Quotation calculated" })
      return true
    } catch (error) {
      const parsed = parseApiError(error)
      setFinalizeErrors(parsed.fieldErrors)
      setInvalidSteps((current) => new Set(current).add(6))
      toast({ tone: "danger", title: "Calculation failed", message: parsed.message })
      return false
    } finally { setCalculating(false) }
  }, [quotationId, toast])

  const finalizeQuotation = useCallback(async () => {
    if (!quotationId) return false
    setSaving(true)
    setFinalizeErrors({})
    try {
      await requestNormalized(`${QUOTATION_PREFIX}${quotationId}/finalize/`, { method: "POST", body: JSON.stringify({}) })
      setQuotation((current) => current ? { ...current, status: "FINALIZED" } : current)
      toast({ tone: "success", title: "Quotation finalized" })
      return true
    } catch (error) {
      const parsed = parseApiError(error)
      setFinalizeErrors(parsed.fieldErrors)
      for (const key of Object.keys(parsed.fieldErrors)) {
        const step = key.includes("personal") ? 0 : key.includes("plan") ? 1 : key.includes("member") ? 2 : key.includes("install") ? 3 : key.includes("fund") ? 4 : key.includes("rider") ? 5 : 6
        setInvalidSteps((current) => new Set(current).add(step))
      }
      toast({ tone: "danger", title: "Quotation cannot be finalized", message: parsed.message })
      return false
    } finally { setSaving(false) }
  }, [quotationId, toast])

  const saveFunds = useCallback(async () => {
    if (!quotationId || !fundState || fundState.not_applicable) return true
    const applicable = fundState.plan_rows.filter((row) => row.investment_linked)
    const invalid = applicable.some((row) => {
      const allocations = fundAllocations[row.plan_configuration_id] ?? []
      const total = allocations.reduce((sum, allocation) => sum + (Number(allocation.allocation_percent) || 0), 0)
      return !allocations.length || allocations.some((allocation) => !allocation.fund_id) || Math.abs(total - 100) >= 0.0001
    })
    if (invalid) {
      setFundErrors({ allocations: ["Each investment-linked plan must have fund allocations totaling exactly 100%."] })
      return false
    }
    setSaving(true)
    setFundErrors({})
    try {
      await requestNormalized(`${QUOTATION_PREFIX}${quotationId}/investment-funds/`, { method: "POST", body: JSON.stringify({ allocations: Object.values(fundAllocations).flat() }) })
      await loadInvestmentFunds()
      setCompletedSteps((current) => new Set(current).add(4))
      toast({ tone: "success", title: "Investment fund allocations saved" })
      return true
    } catch (error) {
      const parsed = parseApiError(error)
      setFundErrors(parsed.fieldErrors)
      toast({ tone: "danger", title: "Investment fund allocations need attention", message: parsed.message })
      return false
    } finally { setSaving(false) }
  }, [fundAllocations, fundState, loadInvestmentFunds, quotationId, toast])

  useEffect(() => {
    if (!quotationId) return
    if (activeStep === 2) void loadMemberCoverage()
    if (activeStep === 3) void loadInstallments()
    if (activeStep === 4) void loadInvestmentFunds()
    if (activeStep === 5) void loadRiders()
    if (activeStep === 6) void loadFinancialSummary()
  }, [activeStep, loadFinancialSummary, loadInstallments, loadInvestmentFunds, loadMemberCoverage, loadRiders, quotationId])

  const saveMember = useCallback(async (member: MemberForm, memberId?: string) => {
    if (!quotationId) return false
    setSaving(true)
    setMemberErrors({})
    try {
      const path = memberId ? `${QUOTATION_PREFIX}${quotationId}/members/${memberId}/` : `${QUOTATION_PREFIX}${quotationId}/members/`
      await requestNormalized(path, { method: memberId ? "PATCH" : "POST", body: JSON.stringify(member) })
      await loadMemberCoverage()
      setCompletedSteps((current) => new Set(current).add(2))
      toast({ tone: "success", title: memberId ? "Member updated" : "Member added" })
      return true
    } catch (error) {
      const parsed = parseApiError(error)
      setMemberErrors(parsed.fieldErrors)
      toast({ tone: "danger", title: "Member details need attention", message: parsed.message })
      return false
    } finally { setSaving(false) }
  }, [loadMemberCoverage, quotationId, toast])

  const removeMember = useCallback(async (memberId: string) => {
    if (!quotationId) return
    try {
      await requestNormalized(`${QUOTATION_PREFIX}${quotationId}/members/${memberId}/`, { method: "DELETE" })
      await loadMemberCoverage()
      toast({ tone: "success", title: "Member removed" })
    } catch (error) {
      toast({ tone: "danger", title: "Unable to remove member", message: parseApiError(error).message })
    }
  }, [loadMemberCoverage, quotationId, toast])

  const age = computeAge(personal.date_of_birth, personal.quote_date)

  const handlePersonalChange = (field: keyof PersonalForm, value: string) => {
    setPersonal((current) => ({ ...current, [field]: value }))
    setPersonalErrors((current) => { const next = { ...current }; delete next[field]; return next })
  }

  const handlePlanToggle = (plan: PlanCard) => {
    const isSelected = selectedPlanIds.includes(plan.plan_id)
    const next = isSelected ? selectedPlanIds.filter((id) => id !== plan.plan_id) : [...selectedPlanIds, plan.plan_id]
    setSelectedPlanIds(next)
    setConfigurations((configs) => {
      if (isSelected) return configs.filter((config) => configurationPlanId(config) !== plan.plan_id)
      if (configs.some((config) => configurationPlanId(config) === plan.plan_id)) return configs
      return [...configs, draftConfiguration(plan, next.length)]
    })
  }

  const handleProductCreated = async (option: QuickCreateOption) => {
    const refreshedPlans = await loadPlans("")
    const meta = option.meta ?? {}
    const productCode = String(meta.product_code ?? meta.code ?? "").trim().toLowerCase()
    const productName = String(meta.product_name ?? meta.name ?? option.label).trim().toLowerCase()
    const createdPlan = refreshedPlans.find((plan) => plan.plan_id === option.value || plan.product_version_id === option.value || (productCode && plan.code.toLowerCase() === productCode) || (productName && (plan.name.toLowerCase() === productName || plan.product_name?.toLowerCase() === productName)))
    if (!createdPlan) {
      toast({ tone: "success", title: "Product created", message: "The product was created. Refresh the plan search to make it available." })
      return
    }
    if (!selectedPlanIds.includes(createdPlan.plan_id)) handlePlanToggle(createdPlan)
    toast({ tone: "success", title: "Product created and selected", message: createdPlan.name })
  }

  const savePersonal = useCallback(async () => {
    if (!quotationId) return false
    const clientErrors = validatePersonalForm(personal, age)
    if (Object.keys(clientErrors).length) {
      setPersonalErrors(clientErrors)
      setInvalidSteps((current) => new Set(current).add(0))
      toast({ tone: "danger", title: "Complete the required personal details" })
      return false
    }
    setSaving(true)
    setPersonalErrors({})
    try {
      const payload = await requestNormalized<ApiPayload>(`${QUOTATION_PREFIX}${quotationId}/personal-details/`, { method: "POST", body: JSON.stringify({ ...personal, location_id: personal.location_id, agent_id: personal.agent_id }) })
      const updated = payload as unknown as Quotation
      setQuotation((current) => ({ ...current, ...updated, id: quotationId }))
      setCompletedSteps((current) => new Set(current).add(0))
      setInvalidSteps((current) => { const next = new Set(current); next.delete(0); return next })
      toast({ tone: "success", title: "Personal details saved" })
      return true
    } catch (error) {
      const parsed = parseApiError(error)
      setPersonalErrors(parsed.fieldErrors)
      setInvalidSteps((current) => new Set(current).add(0))
      toast({ tone: "danger", title: "Personal details need attention", message: parsed.message })
      return false
    } finally { setSaving(false) }
  }, [age, personal, quotationId, toast])

  const savePlans = useCallback(async () => {
    if (!quotationId || !selectedPlanIds.length) {
      const errors = { plans: ["Select at least one plan before continuing."] }
      setPlanErrors({ selection: errors })
      setInvalidSteps((current) => new Set(current).add(1))
      return false
    }
    setSaving(true)
    setPlanErrors({})
    try {
      const selections = selectedPlanIds.map((planId) => {
        const plan = plans.find((item) => item.plan_id === planId)
        const existing = configurations.find((config) => configurationPlanId(config) === planId)
        return { plan_id: planId, product_version_id: plan?.product_version_id, ...(existing ? { term_years: existing.term_years, payment_period_years: existing.payment_period_years, premium_frequency: existing.premium_frequency, quote_basis: existing.quote_basis, estimated_maturity_value: existing.estimated_maturity_value, premium_factor: existing.premium_factor, joint_life: existing.joint_life, mortgage: existing.mortgage, personal_accident: existing.personal_accident, premium_waiver: existing.premium_waiver, estimated_bonus_rate: existing.estimated_bonus_rate } : {}) }
      })
      const payload = await requestNormalized<ApiPayload>(`${QUOTATION_PREFIX}${quotationId}/plans/`, { method: "POST", body: JSON.stringify({ plans: selections }) })
      setConfigurations(payload.configurations ?? [])
      setQuotation((current) => current && payload.quotation ? { ...current, ...payload.quotation } : current)
      setCompletedSteps((current) => new Set(current).add(1))
      setInvalidSteps((current) => { const next = new Set(current); next.delete(1); return next })
      await loadPlanOptions(payload.configurations?.[0] ? configurationPlanId(payload.configurations[0]) ?? undefined : undefined)
      toast({ tone: "success", title: "Plans selected" })
      return true
    } catch (error) {
      const parsed = parseApiError(error)
      setPlanErrors({ selection: parsed.fieldErrors })
      setInvalidSteps((current) => new Set(current).add(1))
      toast({ tone: "danger", title: "Plan selection needs attention", message: parsed.message })
      return false
    } finally { setSaving(false) }
  }, [configurations, loadPlanOptions, plans, quotationId, selectedPlanIds, toast])

  const patchConfiguration = async (configuration: PlanConfiguration, field: string, value: string | boolean) => {
    if (!quotationId) return
    const numericFields = new Set(["term_years", "payment_period_years"])
    const decimalFields = new Set(["estimated_maturity_value", "estimated_bonus_rate"])
    const parsedValue = typeof value === "boolean" ? value : numericFields.has(field) ? (value === "" ? null : Number(value)) : decimalFields.has(field) ? (value === "" ? null : value) : value
    setConfigurations((current) => current.map((item) => item.id === configuration.id ? { ...item, [field]: parsedValue } : item))
    setPlanErrors((current) => { const next = { ...current }; if (next[configuration.id]) { const errors = { ...next[configuration.id] }; delete errors[field]; next[configuration.id] = errors } return next })
    if (!configuration.id || configuration.id.startsWith("draft:")) return
    if (activeStep !== 1) return
    try {
      const payload = await requestNormalized<ApiPayload>(`${QUOTATION_PREFIX}${quotationId}/plans/${configuration.id}/`, { method: "PATCH", body: JSON.stringify({ [field]: parsedValue }) })
      if (payload.configuration) setConfigurations((current) => current.map((item) => item.id === configuration.id ? payload.configuration as PlanConfiguration : item))
    } catch (error) {
      const parsed = parseApiError(error)
      setPlanErrors((current) => ({ ...current, [configuration.id]: parsed.fieldErrors }))
      toast({ tone: "danger", title: "Plan configuration was not saved", message: parsed.message })
    }
  }

  const validateAndNavigate = async (target: number) => {
    if (target > activeStep) {
      const valid = activeStep === 0 ? await savePersonal() : activeStep === 1 ? await savePlans() : activeStep === 4 ? await saveFunds() : activeStep === 5 ? (riderState?.requires_configuration === false || completedSteps.has(5)) : activeStep === 6 ? Boolean(financialSummary && !financialSummary.recalculation_required) : true
      if (!valid) {
        setInvalidSteps((current) => new Set(current).add(activeStep))
        return
      }
      setCompletedSteps((current) => new Set(current).add(activeStep))
    }
    setActiveStep(Math.min(Math.max(target, 0), steps.length - 1))
  }

  const selectStep = (target: number) => { void validateAndNavigate(target) }

  const selectedPlanCount = selectedPlanIds.length
  const selectedPlanLabel = selectedPlanCount === 0 ? "No products selected" : `${selectedPlanCount} ${selectedPlanCount === 1 ? "Plan" : "Plans"}`
  const cardByPlanId = useMemo(() => new Map(plans.map((plan) => [plan.plan_id, plan])), [plans])
  const visibleConfigurations = useMemo(() => selectedPlanIds.map((planId, index) => {
    const existing = configurations.find((config) => configurationPlanId(config) === planId)
    return existing ?? (cardByPlanId.get(planId) ? draftConfiguration(cardByPlanId.get(planId) as PlanCard, index + 1) : null)
  }).filter((config): config is PlanConfiguration => Boolean(config)), [cardByPlanId, configurations, selectedPlanIds])

  useEffect(() => {
    if (!quotation || !quotationId) return
    const timer = window.setTimeout(() => localStorage.setItem(LOCAL_DRAFT_KEY, createDraftSnapshot(quotation, personal, selectedPlanIds, configurations)), 300)
    return () => window.clearTimeout(timer)
  }, [configurations, personal, quotation, quotationId, selectedPlanIds])

  if (loading) return <div className="flex min-h-[420px] items-center justify-center p-6"><LoaderCircle className="animate-spin text-[var(--muted-foreground)]" size={28} aria-label="Loading quotation draft" /></div>
  if (!quotation) return <div className="p-6"><div className="surface-card p-8 text-center"><CircleAlert className="mx-auto mb-3 text-[var(--destructive)]" size={28} /><h1 className="text-lg font-bold">Quotation draft unavailable</h1><p className="mt-2 text-sm text-[var(--muted-foreground)]">The draft could not be opened. Return to the quotations work queue and try again.</p><button type="button" className="button-secondary mt-5" onClick={() => navigate("/ordinary-life/quotations")}><ChevronLeft size={15} aria-hidden="true" />Back to Quotations</button></div></div>

  const currentStep: StepId = steps[activeStep].id
  return <div className="space-y-4 p-4 md:p-6">
    <header className="surface-card relative overflow-visible"><div className="flex flex-wrap items-center justify-between gap-4 border-b bg-[linear-gradient(110deg,#f8fafc,#eef2ff)] px-5 py-4 dark:bg-[linear-gradient(110deg,#171717,#262626)]"><div><p className="text-[11px] font-bold uppercase tracking-[0.16em] text-[var(--muted-foreground)]">Ordinary Life / Quotations</p><div className="mt-1 flex flex-wrap items-center gap-3"><h1 className="text-2xl font-bold tracking-tight">Create New Quote</h1><span className="rounded-full border bg-[var(--card)] px-3 py-1 text-xs font-bold">{selectedPlanLabel}</span></div></div><div className="relative flex items-center gap-2"><span className="hidden items-center gap-1 text-xs text-[var(--muted-foreground)] sm:flex"><Save size={14} aria-hidden="true" />Draft autosave on</span><button type="button" className="button-secondary !min-h-9 !px-3" aria-expanded={detailsOpen} onClick={() => setDetailsOpen((current) => !current)}>Details<ChevronDown size={15} aria-hidden="true" /></button>{detailsOpen && <div className="absolute right-0 top-11 z-40 w-72 rounded-[10px] border bg-[var(--popover)] p-4 text-sm shadow-xl"><div className="mb-3 flex items-center justify-between border-b pb-3"><span className="font-semibold">Draft details</span><button type="button" aria-label="Close details" onClick={() => setDetailsOpen(false)}><X size={15} /></button></div><dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-xs"><dt className="text-[var(--muted-foreground)]">Quote number</dt><dd className="text-right font-semibold">{quotation.quote_number ?? "Pending"}</dd><dt className="text-[var(--muted-foreground)]">Status</dt><dd className="text-right font-semibold">{quotation.status ?? "DRAFT"}</dd><dt className="text-[var(--muted-foreground)]">Currency</dt><dd className="text-right font-semibold">{quotation.currency ?? "—"}</dd><dt className="text-[var(--muted-foreground)]">Expiry</dt><dd className="text-right font-semibold">{quotation.expiry_date ?? "—"}</dd></dl></div>}</div></div>{resumeNotice && <div className="flex items-center gap-2 border-b bg-[var(--muted)]/25 px-5 py-2.5 text-xs font-semibold text-[var(--muted-foreground)]"><RotateCcw size={14} aria-hidden="true" />Draft resumed from your last saved browser session.<button type="button" className="ml-auto underline" onClick={() => { localStorage.removeItem(LOCAL_DRAFT_KEY); setResumeNotice(false) }}>Dismiss</button></div>}</header>
    <WizardTabs activeStep={activeStep} completedSteps={completedSteps} invalidSteps={invalidSteps} onSelect={selectStep} />
    <div className="flex flex-col gap-4 lg:flex-row lg:items-start"><PlanSelectionPanel plans={plans} selectedPlanIds={selectedPlanIds} search={planSearch} loading={plansLoading} onSearch={setPlanSearch} onToggle={handlePlanToggle} onProductCreated={handleProductCreated} /><main className="min-w-0 flex-1">
      {currentStep === "personal" && <PersonalDetailsStep form={personal} options={personalOptions} errors={personalErrors} age={age} onChange={handlePersonalChange} />}
      {currentStep === "plans" && <div className="space-y-4"><div className="surface-card overflow-hidden"><StepHeader eyebrow="Step 2 of 7" title="Plan & Sub-Products" description="Configure each selected plan using effective product setup and Ordinary Life parameter options." /><div className="p-5">{fieldError(planErrors.selection ?? {}, "plans") && <div className="mb-4"><div className="rounded-[10px] border border-[var(--destructive)]/35 bg-[var(--destructive)]/5 p-3 text-sm font-semibold text-[var(--destructive)]" role="alert">{fieldError(planErrors.selection ?? {}, "plans")}</div></div>}{!visibleConfigurations.length && <div className="rounded-[10px] border border-dashed p-8 text-center text-sm text-[var(--muted-foreground)]">Select one or more plans from the left panel, then continue to create configuration sections.</div>}</div></div>{visibleConfigurations.map((config, index) => <PlanConfigurationSection key={config.id} index={index} config={config} card={cardByPlanId.get(configurationPlanId(config) ?? "")} options={planOptions} errors={planErrors[config.id] ?? {}} onChange={(field, value) => void patchConfiguration(config, field, value)} />)}</div>}
      {currentStep === "members" && <MemberCoverageStep quotation={quotation} state={memberState} genderOptions={personalOptions.genders} errors={memberErrors} onSaveMember={saveMember} onRemoveMember={removeMember} />}
      {currentStep === "installments" && <InstallmentsStep rows={installmentState?.rows ?? []} loading={!installmentState} selectedPlan={selectedInstallmentPlan} template={installmentTemplate} templateLoading={installmentTemplateLoading} saving={saving} errors={installmentErrors} onConfigure={(plan) => void loadInstallmentTemplate(plan)} onCloseModal={() => { setInstallmentModalOpen(false); setSelectedInstallmentPlan(null) }} onSave={saveInstallment} modalOpen={installmentModalOpen} />}
      {currentStep === "funds" && <InvestmentFundsStep quotation={quotation} state={fundState} optionsByPlan={fundOptions} allocations={fundAllocations} errors={fundErrors} onChange={(planConfigId, rows) => setFundAllocations((current) => ({ ...current, [planConfigId]: rows }))} onSave={saveFunds} />}
      {currentStep === "riders" && <RidersBenefitsStep state={riderState} optionsByPlan={riderOptions} errors={riderErrors} onSave={saveRiders} />}
      {currentStep === "financial" && <div className="space-y-4"><FinancialDetailsStep summary={financialSummary} loading={financialLoading} calculating={calculating} onCalculate={calculateFinancials} /><ReviewFinalize completedSteps={completedSteps} invalidSteps={invalidSteps} errors={finalizeErrors} onJump={(step) => setActiveStep(step)} onFinalize={finalizeQuotation} disabled={completedSteps.size < steps.length || !financialSummary || Boolean(financialSummary.recalculation_required) || quotation.status === "FINALIZED"} /></div>}
    </main></div>
    <footer className="surface-card flex flex-wrap items-center justify-between gap-3 px-5 py-4"><button type="button" className="button-secondary" onClick={() => navigate("/ordinary-life/quotations")}><X size={15} aria-hidden="true" />Cancel</button><div className="flex gap-2"><button type="button" className="button-secondary" disabled={activeStep === 0 || saving} onClick={() => setActiveStep((current) => Math.max(0, current - 1))}><ChevronLeft size={15} aria-hidden="true" />Previous</button><button type="button" className="button-primary" disabled={saving} onClick={() => void validateAndNavigate(activeStep + 1)}>{saving ? <LoaderCircle className="animate-spin" size={15} aria-hidden="true" /> : null}{activeStep === steps.length - 1 ? "Review & Finalize" : "Next"}<ChevronRight size={15} aria-hidden="true" /></button></div></footer>
  </div>
}

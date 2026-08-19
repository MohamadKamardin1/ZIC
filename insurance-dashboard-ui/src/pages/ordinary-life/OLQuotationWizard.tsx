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
  RotateCcw,
  Save,
  Search,
  ShieldCheck,
  UserRound,
  UsersRound,
  WalletCards,
  X,
} from "lucide-react"
import { useCallback, useEffect, useMemo, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { ApiClientError, request } from "../../lib/apiClient"
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

const QUOTATION_PREFIX = "/api/v1/ol-quotations/quotations/"
const PLAN_SEARCH_ENDPOINT = "/api/v1/ol/plans/search/"
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
  product_version?: string | null
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
}

function asChoices(value: unknown): Choice[] {
  if (!Array.isArray(value)) return []
  return value.map((item) => {
    if (typeof item === "string") return { value: item, label: item.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase()) }
    const record = item as Record<string, unknown>
    return { value: String(record.value ?? record.code ?? ""), label: String(record.label ?? record.name ?? record.value ?? "") }
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
  return configuration.plan ? String(configuration.plan) : null
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

function PlanSelectionPanel({ plans, selectedPlanIds, search, loading, onSearch, onToggle }: { plans: PlanCard[]; selectedPlanIds: string[]; search: string; loading: boolean; onSearch: (value: string) => void; onToggle: (plan: PlanCard) => void }) {
  return <aside className="w-full shrink-0 lg:w-[320px] xl:w-[360px]" aria-label="Plan selection panel">
    <div className="surface-card overflow-hidden">
      <div className="border-b bg-[var(--muted)]/35 p-4">
        <div className="mb-3 flex items-center gap-2"><PanelLeft size={17} aria-hidden="true" /><h2 className="text-base font-bold">Plans & Sub-Products</h2></div>
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
  return <div className="surface-card overflow-hidden"><StepHeader eyebrow="Step 1 of 7" title="Personal Details" description="Capture the prospect information used to calculate eligibility, partner matching, and quotation rating." /><div className="space-y-6 p-5"><FormGrid columns={2}>
    <TextInput label="Quote Name" name="quote_name" required value={form.quote_name} onChange={(event) => onChange("quote_name", event.target.value)} error={fieldError(errors, "quote_name")} placeholder="Enter quote name" />
    <DateInput label="Quote Date" name="quote_date" required value={form.quote_date} onChange={(event) => onChange("quote_date", event.target.value)} error={fieldError(errors, "quote_date")} />
    <ChoiceSelect label="Identity Type" name="identity_type" required value={form.identity_type} options={options.identityTypes} onChange={(value) => onChange("identity_type", value)} error={fieldError(errors, "identity_type")} />
    <TextInput label="Identity Number" name="identity_number" required value={form.identity_number} onChange={(event) => onChange("identity_number", event.target.value)} error={fieldError(errors, "identity_number")} placeholder="Enter identity number" />
    <DateInput label="Date of Birth" name="date_of_birth" required value={form.date_of_birth} onChange={(event) => onChange("date_of_birth", event.target.value)} error={fieldError(errors, "date_of_birth")} />
    <ReadOnlyField label="Age" value={age === null ? "—" : `${age} years`} />
    <ChoiceSelect label="Gender" name="gender" required value={form.gender} options={options.genders} onChange={(value) => onChange("gender", value)} error={fieldError(errors, "gender")} />
    <ChoiceSelect label="Smoker" name="smoker_status" required value={form.smoker_status} options={options.smokerStatuses} onChange={(value) => onChange("smoker_status", value)} error={fieldError(errors, "smoker_status")} />
    <SearchableSelect label="Location" name="location_id" required value={form.location_id} options={options.locations} onChange={(value) => onChange("location_id", value)} error={fieldError(errors, "location_id") ?? fieldError(errors, "location")} placeholder="Search and select location" />
    <SearchableSelect label="Agent" name="agent_id" required value={form.agent_id} options={options.agents} onChange={(value) => onChange("agent_id", value)} error={fieldError(errors, "agent_id")} placeholder="Search and select agent" />
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
    <ChoiceSelect label="Payment Frequency" name={`premium_frequency_${config.id}`} required value={String(config.premium_frequency ?? "")} options={options.payment_frequencies} onChange={(value) => onChange("premium_frequency", value)} error={fieldError(errors, "premium_frequency")} />
    <ChoiceSelect label="Quote Basis" name={`quote_basis_${config.id}`} required value={String(config.quote_basis ?? "")} options={options.quote_bases} onChange={(value) => onChange("quote_basis", value)} error={fieldError(errors, "quote_basis")} />
    <DecimalInput label="Estimated Maturity Value" name={`estimated_maturity_value_${config.id}`} required value={String(config.estimated_maturity_value ?? "")} onChange={(event) => onChange("estimated_maturity_value", event.target.value)} error={fieldError(errors, "estimated_maturity_value")} />
    <ChoiceSelect label="Premium Factor" name={`premium_factor_${config.id}`} value={String(config.premium_factor ?? "")} options={options.premium_factors} onChange={(value) => onChange("premium_factor", value)} error={fieldError(errors, "premium_factor")} placeholder="None" />
    <DecimalInput label="Estimated Bonus Rate (per mille)" name={`estimated_bonus_rate_${config.id}`} value={String(config.estimated_bonus_rate ?? "")} onChange={(event) => onChange("estimated_bonus_rate", event.target.value)} error={fieldError(errors, "estimated_bonus_rate")} />
  </FormGrid>
  <div className="grid gap-4 rounded-[10px] border bg-[var(--muted)]/25 p-4 md:grid-cols-2 xl:grid-cols-4"><Toggle label="Joint Life" checked={Boolean(config.joint_life)} disabled={!features.joint_life} onChange={(checked) => onChange("joint_life", checked)} hint={!features.joint_life ? "Not available for this plan" : "Apply joint-life rules"} /><Toggle label="Mortgage" checked={Boolean(config.mortgage)} disabled={!features.mortgage} onChange={(checked) => onChange("mortgage", checked)} hint={!features.mortgage ? "Not available for this plan" : "Apply mortgage factor"} /><Toggle label="Personal Accident (PA)" checked={Boolean(config.personal_accident)} disabled={!features.personal_accident} onChange={(checked) => onChange("personal_accident", checked)} hint={!features.personal_accident ? "Not available for this plan" : "Attach PA rider option"} /><Toggle label="Premium Waiver (WP)" checked={Boolean(config.premium_waiver)} disabled={!features.premium_waiver} onChange={(checked) => onChange("premium_waiver", checked)} hint={!features.premium_waiver ? "Not available for this plan" : "Attach WP rider option"} /></div>
  {card && <p className="text-xs text-[var(--muted-foreground)]">Configured term range: {card.min_term_years ?? "—"}–{card.max_term_years ?? "—"} years. Entry age range: {card.min_entry_age ?? "—"}–{card.max_entry_age ?? "—"} years.</p>}
  </div></section>
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
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [detailsOpen, setDetailsOpen] = useState(false)
  const [resumeNotice, setResumeNotice] = useState(false)

  const loadQuotation = useCallback(async (id: string) => {
    const payload = await request<Quotation>(`${QUOTATION_PREFIX}${id}/`)
    setQuotation(payload)
    setQuotationId(id)
    setPersonal(initialPersonal(payload))
    const configs = payload.plan_configurations ?? []
    setConfigurations(configs)
    setSelectedPlanIds(configs.filter((config) => config.is_selected !== false).map((config) => configurationPlanId(config)).filter((value): value is string => Boolean(value)))
    const completion = payload.wizard_step_completion ?? {}
    setCompletedSteps(new Set([completion["1_personal_details"] ? 0 : -1, completion["2_plan_and_sub_products"] ? 1 : -1].filter((value) => value >= 0)))
  }, [])

  const createQuotation = useCallback(async () => {
    const saved = readDraftSnapshot()
    if (!routeId && saved?.quotationId) {
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
    const payload = await request<Quotation>(QUOTATION_PREFIX, { method: "POST", body: JSON.stringify({ currency: "TZS" }) })
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

  const loadPersonalOptions = useCallback(async (id: string) => {
    const payload = await request<ApiPayload>(`${QUOTATION_PREFIX}${id}/personal-details-options/`)
    setPersonalOptions({ identityTypes: asChoices(payload.identity_types), genders: asChoices(payload.genders), smokerStatuses: asChoices(payload.smoker_statuses), locations: asChoices(payload.locations), agents: asChoices(payload.agents) })
  }, [])

  const loadPlans = useCallback(async () => {
    if (!quotationId) return
    setPlansLoading(true)
    try {
      const query = new URLSearchParams({ quotation_id: quotationId, limit: "200" })
      if (planSearch.trim()) query.set("search", planSearch.trim())
      const payload = await request<ApiPayload>(`${PLAN_SEARCH_ENDPOINT}?${query.toString()}`)
      setPlans(payload.plans ?? [])
    } catch (error) {
      toast({ tone: "danger", title: "Unable to load plans", message: parseApiError(error).message })
    } finally { setPlansLoading(false) }
  }, [planSearch, quotationId, toast])

  useEffect(() => { if (quotationId) void loadPersonalOptions(quotationId).catch((error) => toast({ tone: "danger", title: "Unable to load quotation options", message: parseApiError(error).message })) }, [loadPersonalOptions, quotationId, toast])
  useEffect(() => { void loadPlans() }, [loadPlans])

  const loadPlanOptions = useCallback(async (planId?: string) => {
    if (!quotationId) return
    try {
      const payload = await request<ApiPayload>(`${QUOTATION_PREFIX}${quotationId}/plan-options/${planId ? `?plan_id=${encodeURIComponent(planId)}` : ""}`)
      setPlanOptions({ payment_frequencies: asChoices(payload.payment_frequencies), quote_bases: asChoices(payload.quote_bases), premium_factors: asChoices(payload.premium_factors), plan_features: payload.plan_features })
    } catch (error) {
      toast({ tone: "danger", title: "Unable to load plan options", message: parseApiError(error).message })
    }
  }, [quotationId, toast])

  const age = computeAge(personal.date_of_birth, personal.quote_date)

  const handlePersonalChange = (field: keyof PersonalForm, value: string) => {
    setPersonal((current) => ({ ...current, [field]: value }))
    setPersonalErrors((current) => { const next = { ...current }; delete next[field]; return next })
  }

  const handlePlanToggle = (plan: PlanCard) => {
    setSelectedPlanIds((current) => current.includes(plan.plan_id) ? current.filter((id) => id !== plan.plan_id) : [...current, plan.plan_id])
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
      const payload = await request<ApiPayload>(`${QUOTATION_PREFIX}${quotationId}/personal-details/`, { method: "POST", body: JSON.stringify({ ...personal, location_id: personal.location_id, agent_id: personal.agent_id }) })
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
      const payload = await request<ApiPayload>(`${QUOTATION_PREFIX}${quotationId}/plans/`, { method: "POST", body: JSON.stringify({ plans: selections }) })
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
    if (!quotationId || !configuration.id) return
    const numericFields = new Set(["term_years", "payment_period_years"])
    const decimalFields = new Set(["estimated_maturity_value", "estimated_bonus_rate"])
    const parsedValue = typeof value === "boolean" ? value : numericFields.has(field) ? (value === "" ? null : Number(value)) : decimalFields.has(field) ? (value === "" ? null : value) : value
    setConfigurations((current) => current.map((item) => item.id === configuration.id ? { ...item, [field]: parsedValue } : item))
    setPlanErrors((current) => { const next = { ...current }; if (next[configuration.id]) { const errors = { ...next[configuration.id] }; delete errors[field]; next[configuration.id] = errors } return next })
    if (activeStep !== 1) return
    try {
      const payload = await request<ApiPayload>(`${QUOTATION_PREFIX}${quotationId}/plans/${configuration.id}/`, { method: "PATCH", body: JSON.stringify({ [field]: parsedValue }) })
      if (payload.configuration) setConfigurations((current) => current.map((item) => item.id === configuration.id ? payload.configuration as PlanConfiguration : item))
    } catch (error) {
      const parsed = parseApiError(error)
      setPlanErrors((current) => ({ ...current, [configuration.id]: parsed.fieldErrors }))
      toast({ tone: "danger", title: "Plan configuration was not saved", message: parsed.message })
    }
  }

  const validateAndNavigate = async (target: number) => {
    if (target > activeStep) {
      const valid = activeStep === 0 ? await savePersonal() : activeStep === 1 ? await savePlans() : true
      if (!valid) return
    }
    setActiveStep(Math.min(Math.max(target, 0), steps.length - 1))
  }

  const selectStep = (target: number) => { void validateAndNavigate(target) }

  const selectedPlanCount = selectedPlanIds.length
  const selectedPlanLabel = selectedPlanCount === 0 ? "No products selected" : `${selectedPlanCount} ${selectedPlanCount === 1 ? "Plan" : "Plans"}`
  const cardByPlanId = useMemo(() => new Map(plans.map((plan) => [plan.plan_id, plan])), [plans])

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
    <div className="flex flex-col gap-4 lg:flex-row lg:items-start"><PlanSelectionPanel plans={plans} selectedPlanIds={selectedPlanIds} search={planSearch} loading={plansLoading} onSearch={setPlanSearch} onToggle={handlePlanToggle} /><main className="min-w-0 flex-1">
      {currentStep === "personal" && <PersonalDetailsStep form={personal} options={personalOptions} errors={personalErrors} age={age} onChange={handlePersonalChange} />}
      {currentStep === "plans" && <div className="space-y-4"><div className="surface-card overflow-hidden"><StepHeader eyebrow="Step 2 of 7" title="Plan & Sub-Products" description="Configure each selected plan using effective product setup and Ordinary Life parameter options." /><div className="p-5">{fieldError(planErrors.selection ?? {}, "plans") && <div className="mb-4"><div className="rounded-[10px] border border-[var(--destructive)]/35 bg-[var(--destructive)]/5 p-3 text-sm font-semibold text-[var(--destructive)]" role="alert">{fieldError(planErrors.selection ?? {}, "plans")}</div></div>}{!configurations.length && <div className="rounded-[10px] border border-dashed p-8 text-center text-sm text-[var(--muted-foreground)]">Select one or more plans from the left panel, then continue to create configuration sections.</div>}</div></div>{configurations.map((config, index) => <PlanConfigurationSection key={config.id} index={index} config={config} card={cardByPlanId.get(configurationPlanId(config) ?? "")} options={planOptions} errors={planErrors[config.id] ?? {}} onChange={(field, value) => void patchConfiguration(config, field, value)} />)}</div>}
      {activeStep >= 2 && <FutureStep step={steps[activeStep].label} index={activeStep} />}
    </main></div>
    <footer className="surface-card flex flex-wrap items-center justify-between gap-3 px-5 py-4"><button type="button" className="button-secondary" onClick={() => navigate("/ordinary-life/quotations")}><X size={15} aria-hidden="true" />Cancel</button><div className="flex gap-2"><button type="button" className="button-secondary" disabled={activeStep === 0 || saving} onClick={() => setActiveStep((current) => Math.max(0, current - 1))}><ChevronLeft size={15} aria-hidden="true" />Previous</button><button type="button" className="button-primary" disabled={saving} onClick={() => void validateAndNavigate(activeStep + 1)}>{saving ? <LoaderCircle className="animate-spin" size={15} aria-hidden="true" /> : null}{activeStep === steps.length - 1 ? "Complete" : "Next"}<ChevronRight size={15} aria-hidden="true" /></button></div></footer>
  </div>
}

import { useCallback, useEffect, useMemo, useState } from "react"
import { Plus, X } from "lucide-react"
import { request } from "../../lib/apiClient"
import { useAccess } from "../../lib/access"
import { DataTable, normalizeTableResponse } from "../../components/ui/DataTable"
import { FilterBar } from "../../components/ui/FilterBar"
import { ConfirmModal, FormModal, InfoBanner } from "../../components/ui/Overlays"
import { DateInput, DecimalInput, FormGrid, SearchableSelect, SelectInput, TextInput, TextareaInput, Toggle } from "../../components/ui"
import { MasterDetailPage } from "../../components/ui/Patterns"
import { StatusBadge, type StatusTone } from "../../components/ui/StatusBadge"
import { useToast } from "../../components/ui/Toast"
import type { FilterValues } from "../../components/ui/FilterBar"
import type { FilterDefinition, FilterOption, RowAction, TableColumn } from "../../components/ui/types"
import type { TableQuery } from "../../lib/apiClient"

const API_PREFIX = "/api/v1/ol-parameters"

type ScreenKey =
  | "plan-types"
  | "products"
  | "plan-tax-configurations"
  | "plan-target-markets"
  | "plan-risk-categories"
  | "plan-occupation-risk-limits"
  | "investment-fund-types"
  | "investment-funds"

type ProductRecord = {
  id: string
  code: string
  name: string
  description?: string | null
  is_active: boolean
  effective_from?: string | null
  effective_to?: string | null
  plan_category?: string
  plan_type?: string | null
  plan_type_id?: string | null
  insurance_class?: string
  currency?: string
  min_entry_age?: number | null
  max_entry_age?: number | null
  min_term?: number | null
  max_term?: number | null
  min_sum_assured?: string | number | null
  max_sum_assured?: string | number | null
  premium_frequencies?: string[]
  allow_riders?: boolean
  allow_loans?: boolean
  allow_withdrawals?: boolean
  allow_surrender?: boolean
  allow_paidup?: boolean
  allow_bonus?: boolean
  investment_linked?: boolean
  product?: string | null
  product_id?: string | null
  plan?: string | null
  plan_id?: string | null
  tax_type?: string
  tax_basis?: string
  rate_type?: string
  rate_value?: string | number
  apply_on?: string
  sequence?: number
  country_or_branch?: string
  target_market_type?: string
  min_age?: number | null
  max_age?: number | null
  occupation_categories?: string[]
  residency_requirement?: string
  underwriting_class?: string
  loading_basis?: string
  occupation_risk_category?: string
  loading_rate?: string | number
  exclusion_flag?: boolean
  risk_profile?: string
  fund_type?: string | null
  fund_type_id?: string | null
  valuation_frequency?: string
  unit_price?: string | number | null
  allocation_rules?: Record<string, unknown>
}

type EditorValue = string | number | boolean | string[] | Record<string, unknown> | null | undefined
type EditorState = Record<string, EditorValue>
type ProductOptionRow = Pick<ProductRecord, "id" | "code" | "name" | "is_active"> & { plan_category?: string }

const today = () => new Date().toISOString().slice(0, 10)
const valueLabel = (value: unknown) => value === null || value === undefined || value === "" ? "—" : String(value)
const dateLabel = (value?: string | null) => value ? new Intl.DateTimeFormat("en-GB", { dateStyle: "medium" }).format(new Date(`${value}T00:00:00`)) : "Open ended"

function dateState(value?: string | null): { label: string; className: string } {
  if (!value) return { label: "Open ended", className: "text-[var(--muted-foreground)]" }
  if (value < today()) return { label: dateLabel(value), className: "font-semibold text-[var(--destructive)]" }
  if (value > today()) return { label: dateLabel(value), className: "font-semibold text-[var(--info)]" }
  return { label: dateLabel(value), className: "font-semibold text-[var(--success)]" }
}

function DateState({ value }: { value?: string | null }) {
  const state = dateState(value)
  return <span className={state.className}>{state.label}</span>
}

function activeTone(row: ProductRecord): StatusTone {
  if (!row.is_active) return "danger"
  if (row.effective_to && row.effective_to < today()) return "danger"
  if (row.effective_from && row.effective_from > today()) return "info"
  return "success"
}

function activeLabel(row: ProductRecord) {
  if (!row.is_active) return "Inactive"
  if (row.effective_to && row.effective_to < today()) return "Expired"
  if (row.effective_from && row.effective_from > today()) return "Scheduled"
  return "Active"
}

const commonColumns = (extra: TableColumn<ProductRecord>[], effectiveDated = false): TableColumn<ProductRecord>[] => {
  const columns: TableColumn<ProductRecord>[] = [
    { key: "code", label: "Code", field: "code", sortable: true },
    { key: "name", label: "Name", field: "name", sortable: true },
    ...extra,
  ]
  if (effectiveDated) columns.push(
    { key: "effective_from", label: "Effective from", field: "effective_from", sortable: true, render: (value: unknown) => <DateState value={value as string | null} /> },
    { key: "effective_to", label: "Effective to", field: "effective_to", sortable: true, render: (value: unknown) => <DateState value={value as string | null} /> },
  )
  columns.push({ key: "status", label: "Status", render: (_value: unknown, row: ProductRecord) => <StatusBadge value={activeLabel(row)} tone={activeTone(row)} /> })
  return columns
}

const scopeFilters: FilterDefinition[] = [
  { key: "product", label: "Product", type: "text", placeholder: "Product ID" },
  { key: "plan", label: "Plan", type: "text", placeholder: "Plan ID" },
  { key: "is_active", label: "Active status", type: "text", placeholder: "true or false" },
]

const screens: Record<ScreenKey, { key: ScreenKey; title: string; description: string; endpoint: string; effectiveDated: boolean; columns: TableColumn<ProductRecord>[]; filters: FilterDefinition[] }> = {
  "plan-types": {
    key: "plan-types", title: "OL Plan Types", description: "Backend-managed plan type catalog used by Ordinary Life products.", endpoint: `${API_PREFIX}/plan-types/`, effectiveDated: false,
    columns: commonColumns([{ key: "plan_category", label: "Plan category", field: "plan_category", sortable: true }]), filters: [{ key: "plan_category", label: "Plan category", type: "text", placeholder: "Configured category" }, { key: "is_active", label: "Active status", type: "text", placeholder: "true or false" }],
  },
  products: {
    key: "products", title: "OL Product", description: "Product definitions drive quotation eligibility, capabilities, and downstream rating behavior.", endpoint: `${API_PREFIX}/products/`, effectiveDated: true,
    columns: commonColumns([
      { key: "plan_type", label: "Plan type", field: "plan_type", sortable: true, render: (value) => valueLabel(value) },
      { key: "insurance_class", label: "Insurance class", field: "insurance_class", sortable: true },
      { key: "currency", label: "Currency", field: "currency", sortable: true },
      { key: "entry_age", label: "Entry ages", render: (_value, row) => `${valueLabel(row.min_entry_age)}–${valueLabel(row.max_entry_age)}` },
      { key: "term", label: "Terms", render: (_value, row) => `${valueLabel(row.min_term)}–${valueLabel(row.max_term)} years` },
      { key: "capabilities", label: "Capabilities", render: (_value, row) => [row.allow_riders && "Riders", row.allow_loans && "Loans", row.allow_surrender && "Surrender", row.investment_linked && "Linked"].filter(Boolean).join(", ") || "None" },
    ]), filters: [{ key: "plan_type", label: "Plan type", type: "text", placeholder: "Plan type ID" }, { key: "insurance_class", label: "Insurance class", type: "text", placeholder: "Configured class" }, { key: "currency", label: "Currency", type: "text", placeholder: "ISO currency" }, { key: "investment_linked", label: "Investment linked", type: "text", placeholder: "true or false" }, { key: "is_active", label: "Active status", type: "text", placeholder: "true or false" }],
  },
  "plan-tax-configurations": {
    key: "plan-tax-configurations", title: "Plan Tax Configurations", description: "Ordered tax components scoped to a product or operational plan.", endpoint: `${API_PREFIX}/plan-tax-configurations/`, effectiveDated: true,
    columns: commonColumns([{ key: "product", label: "Product", field: "product", sortable: true, render: (value) => valueLabel(value) }, { key: "plan", label: "Plan", field: "plan", sortable: true, render: (value) => valueLabel(value) }, { key: "tax_type", label: "Tax type", field: "tax_type", sortable: true }, { key: "tax_basis", label: "Basis", field: "tax_basis", sortable: true }, { key: "rate_value", label: "Rate", field: "rate_value", sortable: true, align: "right" }, { key: "sequence", label: "Sequence", field: "sequence", sortable: true, align: "right" }]), filters: [{ ...scopeFilters[0] }, { ...scopeFilters[1] }, { key: "tax_type", label: "Tax type", type: "text", placeholder: "Configured tax" }, { key: "rate_type", label: "Rate type", type: "text", placeholder: "Configured type" }, { key: "is_active", label: "Active status", type: "text", placeholder: "true or false" }],
  },
  "plan-target-markets": {
    key: "plan-target-markets", title: "Plan Target Market", description: "Eligibility configuration by age, occupation category, residency, product, and plan scope.", endpoint: `${API_PREFIX}/plan-target-markets/`, effectiveDated: true,
    columns: commonColumns([{ key: "product", label: "Product", field: "product", sortable: true, render: (value) => valueLabel(value) }, { key: "plan", label: "Plan", field: "plan", sortable: true, render: (value) => valueLabel(value) }, { key: "target_market_type", label: "Market type", field: "target_market_type", sortable: true }, { key: "age", label: "Age range", render: (_value, row) => `${valueLabel(row.min_age)}–${valueLabel(row.max_age)}` }, { key: "occupation_categories", label: "Occupations", field: "occupation_categories", render: (value) => Array.isArray(value) ? value.join(", ") || "All" : valueLabel(value) }, { key: "residency_requirement", label: "Residency", field: "residency_requirement", sortable: true }]), filters: [{ ...scopeFilters[0] }, { ...scopeFilters[1] }, { key: "target_market_type", label: "Market type", type: "text", placeholder: "Configured type" }, { key: "residency_requirement", label: "Residency", type: "text", placeholder: "Configured residency" }, { key: "is_active", label: "Active status", type: "text", placeholder: "true or false" }],
  },
  "plan-risk-categories": {
    key: "plan-risk-categories", title: "Plan Risk Categories", description: "Underwriting classes and loading bases used to categorize plan risk.", endpoint: `${API_PREFIX}/plan-risk-categories/`, effectiveDated: true,
    columns: commonColumns([{ key: "product", label: "Product", field: "product", sortable: true, render: (value) => valueLabel(value) }, { key: "plan", label: "Plan", field: "plan", sortable: true, render: (value) => valueLabel(value) }, { key: "underwriting_class", label: "Underwriting class", field: "underwriting_class", sortable: true }, { key: "loading_basis", label: "Loading basis", field: "loading_basis", sortable: true }]), filters: [{ ...scopeFilters[0] }, { ...scopeFilters[1] }, { key: "underwriting_class", label: "Underwriting class", type: "text", placeholder: "Configured class" }, { key: "is_active", label: "Active status", type: "text", placeholder: "true or false" }],
  },
  "plan-occupation-risk-limits": {
    key: "plan-occupation-risk-limits", title: "Plan Occupation Risk Limit", description: "Occupation-level maximum sum assured and loading controls.", endpoint: `${API_PREFIX}/plan-occupation-risk-limits/`, effectiveDated: true,
    columns: commonColumns([{ key: "product", label: "Product", field: "product", sortable: true, render: (value) => valueLabel(value) }, { key: "plan", label: "Plan", field: "plan", sortable: true, render: (value) => valueLabel(value) }, { key: "occupation_risk_category", label: "Occupation risk", field: "occupation_risk_category", sortable: true }, { key: "max_sum_assured", label: "Max sum assured", field: "max_sum_assured", sortable: true, align: "right" }, { key: "loading_rate", label: "Loading", field: "loading_rate", sortable: true, align: "right" }, { key: "exclusion_flag", label: "Excluded", field: "exclusion_flag", render: (value) => <StatusBadge value={value ? "Excluded" : "Allowed"} tone={value ? "danger" : "success"} /> }]), filters: [{ ...scopeFilters[0] }, { ...scopeFilters[1] }, { key: "occupation_risk_category", label: "Occupation risk", type: "text", placeholder: "Configured category" }, { key: "exclusion_flag", label: "Excluded", type: "text", placeholder: "true or false" }, { key: "is_active", label: "Active status", type: "text", placeholder: "true or false" }],
  },
  "investment-fund-types": {
    key: "investment-fund-types", title: "Investment Fund Type", description: "Backend-managed risk profile catalog for investment-linked funds.", endpoint: `${API_PREFIX}/investment-fund-types/`, effectiveDated: false,
    columns: commonColumns([{ key: "risk_profile", label: "Risk profile", field: "risk_profile", sortable: true, render: (value) => <StatusBadge value={valueLabel(value)} tone="neutral" /> }]), filters: [{ key: "risk_profile", label: "Risk profile", type: "text", placeholder: "Configured profile" }, { key: "is_active", label: "Active status", type: "text", placeholder: "true or false" }],
  },
  "investment-funds": {
    key: "investment-funds", title: "Investment Fund", description: "Fund catalog and allocation metadata for investment-linked products.", endpoint: `${API_PREFIX}/investment-funds/`, effectiveDated: true,
    columns: commonColumns([{ key: "fund_type", label: "Fund type", field: "fund_type", sortable: true, render: (value) => valueLabel(value) }, { key: "currency", label: "Currency", field: "currency", sortable: true }, { key: "valuation_frequency", label: "Valuation frequency", field: "valuation_frequency", sortable: true }, { key: "unit_price", label: "Unit price", field: "unit_price", sortable: true, align: "right" }]), filters: [{ key: "fund_type", label: "Fund type", type: "text", placeholder: "Fund type ID" }, { key: "currency", label: "Currency", type: "text", placeholder: "ISO currency" }, { key: "valuation_frequency", label: "Valuation frequency", type: "text", placeholder: "Configured frequency" }, { key: "is_active", label: "Active status", type: "text", placeholder: "true or false" }],
  },
}

const defaultValue = (screen: ScreenKey): EditorState => {
  const base: EditorState = { code: "", name: "", description: "", is_active: true }
  if (["products", "plan-tax-configurations", "plan-target-markets", "plan-risk-categories", "plan-occupation-risk-limits", "investment-funds"].includes(screen)) Object.assign(base, { effective_from: today(), effective_to: null, product: null, plan: null })
  if (screen === "plan-types") Object.assign(base, { plan_category: "" })
  if (screen === "products") Object.assign(base, { plan_type: null, insurance_class: "", currency: "", min_entry_age: 18, max_entry_age: 65, min_term: 1, max_term: 30, min_sum_assured: null, max_sum_assured: null, premium_frequencies: [], allow_riders: false, allow_loans: false, allow_withdrawals: false, allow_surrender: true, allow_paidup: false, allow_bonus: false, investment_linked: false })
  if (screen === "plan-tax-configurations") Object.assign(base, { tax_type: "", tax_basis: "", rate_type: "", rate_value: "", apply_on: "", sequence: 1, country_or_branch: "" })
  if (screen === "plan-target-markets") Object.assign(base, { target_market_type: "", min_age: null, max_age: null, occupation_categories: [], residency_requirement: "" })
  if (screen === "plan-risk-categories") Object.assign(base, { underwriting_class: "", loading_basis: "" })
  if (screen === "plan-occupation-risk-limits") Object.assign(base, { occupation_risk_category: "", max_sum_assured: null, loading_rate: "", exclusion_flag: false })
  if (screen === "investment-fund-types") Object.assign(base, { risk_profile: "" })
  if (screen === "investment-funds") Object.assign(base, { fund_type: null, currency: "", valuation_frequency: "", unit_price: null, allocation_rules: {} })
  return base
}

function optionRows(rows: ProductOptionRow[]): FilterOption[] {
  return rows.filter((row) => row.is_active !== false).map((row) => ({ value: row.id, label: `${row.code} — ${row.name}` }))
}

function TagEditor({ label, values, suggestions, onChange, error }: { label: string; values: string[]; suggestions: string[]; onChange: (values: string[]) => void; error?: string }) {
  const [draft, setDraft] = useState("")
  const add = (raw: string) => { const next = raw.trim().toUpperCase(); if (next && !values.includes(next)) onChange([...values, next]); setDraft("") }
  return <div className="space-y-2"><div className="flex items-baseline justify-between"><label className="text-sm font-semibold">{label}</label><span className="text-[11px] text-[var(--muted-foreground)]">Loaded from Product Setup data</span></div><div className="flex flex-wrap gap-2">{values.map((value) => <span key={value} className="inline-flex items-center gap-1 rounded-full border bg-[var(--muted)] px-2.5 py-1 text-xs font-semibold">{value}<button type="button" aria-label={`Remove ${value}`} onClick={() => onChange(values.filter((item) => item !== value))}><X size={13} /></button></span>)}</div><div className="flex gap-2"><input value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); add(draft) } }} className="h-10 min-w-0 flex-1 rounded-[10px] border bg-[var(--card)] px-3 text-sm" placeholder={suggestions.length ? "Add or type a frequency" : "Type a frequency"} list={`${label.replace(/\s+/g, "-")}-suggestions`} /><datalist id={`${label.replace(/\s+/g, "-")}-suggestions`}>{suggestions.map((value) => <option key={value} value={value} />)}</datalist><button type="button" className="button-secondary !min-h-10" onClick={() => add(draft)}>Add</button></div>{error && <p className="text-xs font-medium text-[var(--destructive)]" role="alert">{error}</p>}</div>
}

function ProductEditor({ value, update, errors, planTypeOptions, productOptions, fundTypeOptions, frequencyOptions }: { value: EditorState; update: (key: string, value: EditorValue) => void; errors: Record<string, string>; planTypeOptions: FilterOption[]; productOptions: FilterOption[]; fundTypeOptions: FilterOption[]; frequencyOptions: string[] }) {
  const screen = String(value.__screen ?? "") as ScreenKey
  const text = (key: string, label: string, required = false, placeholder?: string) => <TextInput label={label} required={required} name={key} value={String(value[key] ?? "")} onChange={(event) => update(key, event.target.value)} error={errors[key]} placeholder={placeholder} />
  const decimal = (key: string, label: string, required = false) => <DecimalInput label={label} required={required} name={key} value={value[key] === null || value[key] === undefined ? "" : String(value[key])} onChange={(event) => update(key, event.target.value)} error={errors[key]} />
  const number = (key: string, label: string, required = false) => <DecimalInput label={label} required={required} name={key} value={value[key] === null || value[key] === undefined ? "" : String(value[key])} onChange={(event) => update(key, event.target.value === "" ? null : Number(event.target.value))} error={errors[key]} />
  const select = (key: string, label: string, options: FilterOption[], required = false) => <SearchableSelect label={label} required={required} name={key} value={typeof value[key] === "string" ? value[key] : ""} options={options} onChange={(next) => update(key, next || null)} error={errors[key]} />
  const scope = <FormGrid columns={2}>{select("product", "Product", productOptions)}{select("plan", "Plan", productOptions)}</FormGrid>
  if (screen === "products") return <div className="space-y-5"><section><h3 className="mb-3 text-sm font-extrabold uppercase tracking-[0.12em] text-[var(--muted-foreground)]">Identity</h3><FormGrid columns={2}>{text("code", "Code", true)}{text("name", "Name", true)}{select("plan_type", "Plan type", planTypeOptions, true)}{text("insurance_class", "Insurance class", true, "Configured by Product Setup")}{text("currency", "Currency", true, "ISO 4217")}</FormGrid><div className="mt-4"><TextareaInput label="Description" name="description" value={String(value.description ?? "")} onChange={(event) => update("description", event.target.value)} error={errors.description} /></div></section><section><h3 className="mb-3 text-sm font-extrabold uppercase tracking-[0.12em] text-[var(--muted-foreground)]">Eligibility and limits</h3><FormGrid columns={3}>{number("min_entry_age", "Minimum entry age", true)}{number("max_entry_age", "Maximum entry age", true)}{number("min_term", "Minimum term", true)}{number("max_term", "Maximum term", true)}{decimal("min_sum_assured", "Minimum sum assured")}{decimal("max_sum_assured", "Maximum sum assured")}</FormGrid></section><section><h3 className="mb-3 text-sm font-extrabold uppercase tracking-[0.12em] text-[var(--muted-foreground)]">Premium frequencies</h3><TagEditor label="Premium frequencies" values={Array.isArray(value.premium_frequencies) ? value.premium_frequencies : []} suggestions={frequencyOptions} onChange={(next) => update("premium_frequencies", next)} error={errors.premium_frequencies} /></section><section><h3 className="mb-3 text-sm font-extrabold uppercase tracking-[0.12em] text-[var(--muted-foreground)]">Product capabilities</h3><div className="grid gap-3 rounded-[10px] border bg-[var(--muted)]/25 p-4 sm:grid-cols-2">{[["allow_riders", "Riders"], ["allow_loans", "Loans"], ["allow_withdrawals", "Withdrawals"], ["allow_surrender", "Surrender"], ["allow_paidup", "Paid-up"], ["allow_bonus", "Bonus"], ["investment_linked", "Investment-linked"]].map(([key, label]) => <Toggle key={key} label={label} checked={Boolean(value[key])} onChange={(checked) => update(key, checked)} />)}</div></section><section><h3 className="mb-3 text-sm font-extrabold uppercase tracking-[0.12em] text-[var(--muted-foreground)]">Effective dates and status</h3><FormGrid columns={2}><DateInput label="Effective from" required name="effective_from" value={String(value.effective_from ?? "")} onChange={(event) => update("effective_from", event.target.value)} error={errors.effective_from} /><DateInput label="Effective to" name="effective_to" value={String(value.effective_to ?? "")} onChange={(event) => update("effective_to", event.target.value || null)} error={errors.effective_to} /><Toggle label="Active" checked={Boolean(value.is_active)} onChange={(checked) => update("is_active", checked)} /></FormGrid></section></div>
  if (screen === "plan-types") return <div className="space-y-4"><FormGrid columns={2}>{text("code", "Code", true)}{text("name", "Name", true)}{text("plan_category", "Plan category", true)}</FormGrid><TextareaInput label="Description" name="description" value={String(value.description ?? "")} onChange={(event) => update("description", event.target.value)} error={errors.description} /></div>
  if (screen === "plan-tax-configurations") return <div className="space-y-4"><FormGrid columns={2}>{text("code", "Code", true)}{text("name", "Name", true)}{scope}{text("tax_type", "Tax type", true)}{text("tax_basis", "Tax basis", true)}{text("apply_on", "Apply on", true)}{text("rate_type", "Rate type", true)}{decimal("rate_value", "Rate value", true)}{number("sequence", "Sequence", true)}{text("country_or_branch", "Country or branch")}</FormGrid><EffectiveFields value={value} update={update} errors={errors} /></div>
  if (screen === "plan-target-markets") return <div className="space-y-4"><FormGrid columns={2}>{text("code", "Code", true)}{text("name", "Name", true)}{scope}{text("target_market_type", "Target-market type", true)}{number("min_age", "Minimum age")}{number("max_age", "Maximum age")}{text("residency_requirement", "Residency requirement")}</FormGrid><TagEditor label="Occupation categories" values={Array.isArray(value.occupation_categories) ? value.occupation_categories : []} suggestions={[]} onChange={(next) => update("occupation_categories", next)} error={errors.occupation_categories} /><EffectiveFields value={value} update={update} errors={errors} /></div>
  if (screen === "plan-risk-categories") return <div className="space-y-4"><FormGrid columns={2}>{text("code", "Code", true)}{text("name", "Name", true)}{scope}{text("underwriting_class", "Underwriting class", true)}{text("loading_basis", "Loading basis", true)}</FormGrid><EffectiveFields value={value} update={update} errors={errors} /></div>
  if (screen === "plan-occupation-risk-limits") return <div className="space-y-4"><FormGrid columns={2}>{text("code", "Code", true)}{text("name", "Name", true)}{scope}{text("occupation_risk_category", "Occupation risk category", true)}{decimal("max_sum_assured", "Maximum sum assured")}{decimal("loading_rate", "Loading rate", true)}<Toggle label="Exclusion flag" checked={Boolean(value.exclusion_flag)} onChange={(checked) => update("exclusion_flag", checked)} /></FormGrid><EffectiveFields value={value} update={update} errors={errors} /></div>
  if (screen === "investment-fund-types") return <div className="space-y-4"><FormGrid columns={2}>{text("code", "Code", true)}{text("name", "Name", true)}{text("risk_profile", "Risk profile", true)}</FormGrid><TextareaInput label="Description" name="description" value={String(value.description ?? "")} onChange={(event) => update("description", event.target.value)} error={errors.description} /></div>
  return <div className="space-y-4"><FormGrid columns={2}>{text("code", "Code", true)}{text("name", "Name", true)}{select("fund_type", "Fund type", fundTypeOptions, true)}{text("currency", "Currency", true, "ISO 4217")}{text("valuation_frequency", "Valuation frequency", true)}{decimal("unit_price", "Unit price")}</FormGrid><TextareaInput label="Allocation rules JSON" name="allocation_rules" value={typeof value.allocation_rules === "object" ? JSON.stringify(value.allocation_rules) : String(value.allocation_rules ?? "{}")} onChange={(event) => { try { update("allocation_rules", JSON.parse(event.target.value) as Record<string, unknown>); } catch { update("allocation_rules", event.target.value) } }} error={errors.allocation_rules} /><EffectiveFields value={value} update={update} errors={errors} /></div>
}

function EffectiveFields({ value, update, errors }: { value: EditorState; update: (key: string, value: EditorValue) => void; errors: Record<string, string> }) {
  return <div className="mt-2 border-t pt-4"><h3 className="mb-3 text-sm font-extrabold uppercase tracking-[0.12em] text-[var(--muted-foreground)]">Effective dates and status</h3><FormGrid columns={3}><DateInput label="Effective from" required name="effective_from" value={String(value.effective_from ?? "")} onChange={(event) => update("effective_from", event.target.value)} error={errors.effective_from} /><DateInput label="Effective to" name="effective_to" value={String(value.effective_to ?? "")} onChange={(event) => update("effective_to", event.target.value || null)} error={errors.effective_to} /><Toggle label="Active" checked={Boolean(value.is_active)} onChange={(checked) => update("is_active", checked)} /></FormGrid></div>
}

export default function OLProductSetup() {
  const { access, isSuperAdmin } = useAccess()
  const { toast } = useToast()
  const permissionKeys = useMemo(() => isSuperAdmin ? ["ol_parameters.view", "ol_parameters.create", "ol_parameters.update", "ol_parameters.deactivate"] : (access?.permissions ?? []).map((permission) => `${permission.module}.${permission.action}`), [access, isSuperAdmin])
  const canView = isSuperAdmin || permissionKeys.includes("ol_parameters.view")
  const canCreate = isSuperAdmin || permissionKeys.includes("ol_parameters.create")
  const canUpdate = isSuperAdmin || permissionKeys.includes("ol_parameters.update")
  const canDeactivate = isSuperAdmin || permissionKeys.includes("ol_parameters.deactivate")
  const [active, setActive] = useState<ScreenKey>("plan-types")
  const [filters, setFilters] = useState<FilterValues>({})
  const [refreshKey, setRefreshKey] = useState(0)
  const [editor, setEditor] = useState<{ open: boolean; row: ProductRecord | null; value: EditorState }>({ open: false, row: null, value: {} })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const [deactivateRow, setDeactivateRow] = useState<ProductRecord | null>(null)
  const [planTypes, setPlanTypes] = useState<ProductOptionRow[]>([])
  const [products, setProducts] = useState<ProductOptionRow[]>([])
  const [fundTypes, setFundTypes] = useState<ProductOptionRow[]>([])

  const screen = screens[active]
  const fetchOptions = useCallback(async () => {
    try {
      const [planTypePayload, productPayload, fundTypePayload] = await Promise.all([request<unknown>(`${API_PREFIX}/plan-types/?page_size=200`), request<unknown>(`${API_PREFIX}/products/?page_size=200`), request<unknown>(`${API_PREFIX}/investment-fund-types/?page_size=200`)]); setPlanTypes(normalizeTableResponse<ProductOptionRow>(planTypePayload).results); setProducts(normalizeTableResponse<ProductOptionRow>(productPayload).results); setFundTypes(normalizeTableResponse<ProductOptionRow>(fundTypePayload).results)
    } catch { toast({ tone: "warning", title: "Option lists unavailable", message: "Product Setup selectors will populate when the parameter APIs are reachable." }) }
  }, [toast])
  useEffect(() => { void fetchOptions() }, [fetchOptions])
  const planTypeOptions = useMemo(() => optionRows(planTypes), [planTypes])
  const productOptions = useMemo(() => optionRows(products), [products])
  const fundTypeOptions = useMemo(() => optionRows(fundTypes), [fundTypes])
  const frequencyOptions = useMemo(() => Array.from(new Set(products.flatMap((row) => Array.isArray((row as ProductRecord).premium_frequencies) ? (row as ProductRecord).premium_frequencies ?? [] : []))), [products])
  const fetcher = useCallback((query: TableQuery) => request<unknown>(`${screen.endpoint}${query.search ? `?search=${encodeURIComponent(query.search)}` : ""}`).then(normalizeTableResponse<ProductRecord>), [screen.endpoint])
  const update = (key: string, next: EditorValue) => setEditor((current) => ({ ...current, value: { ...current.value, [key]: next } }))
  const openCreate = () => { setErrors({}); setEditor({ open: true, row: null, value: { ...defaultValue(active), __screen: active } }) }
  const openEdit = (row: ProductRecord) => { setErrors({}); setEditor({ open: true, row, value: { ...defaultValue(active), ...row, __screen: active } }) }
  const closeEditor = () => { setEditor((current) => ({ ...current, open: false })); setErrors({}) }
  const validate = () => {
    const next: Record<string, string> = {}; const value = editor.value; const required = (key: string, label: string) => { if (value[key] === null || value[key] === undefined || value[key] === "" || (Array.isArray(value[key]) && value[key].length === 0)) next[key] = `${label} is required.` }
    required("code", "Code"); required("name", "Name")
    if (active === "products") { required("plan_type", "Plan type"); required("insurance_class", "Insurance class"); required("currency", "Currency"); required("min_entry_age", "Minimum entry age"); required("max_entry_age", "Maximum entry age"); required("min_term", "Minimum term"); required("max_term", "Maximum term"); required("premium_frequencies", "Premium frequencies"); if (String(value.currency ?? "").length !== 3) next.currency = "Currency must be a three-letter code."; if (Number(value.min_entry_age) > Number(value.max_entry_age)) next.max_entry_age = "Maximum entry age cannot be less than minimum entry age."; if (Number(value.min_term) < 1 || Number(value.min_term) > Number(value.max_term)) next.max_term = "Maximum term must be at least the minimum term."; if (value.min_sum_assured !== null && value.min_sum_assured !== "" && value.max_sum_assured !== null && value.max_sum_assured !== "" && Number(value.min_sum_assured) > Number(value.max_sum_assured)) next.max_sum_assured = "Maximum sum assured cannot be less than minimum sum assured." }
    if (["plan-tax-configurations", "plan-target-markets", "plan-occupation-risk-limits"].includes(active) && !value.product && !value.plan) next.product = "Select a product or plan scope.";
    if (active === "plan-tax-configurations") { required("tax_type", "Tax type"); required("tax_basis", "Tax basis"); required("apply_on", "Apply on"); required("rate_type", "Rate type"); required("rate_value", "Rate value"); if (Number(value.rate_value) < 0) next.rate_value = "Rate value cannot be negative."; if (String(value.rate_type).toUpperCase() === "PERCENTAGE" && Number(value.rate_value) > 100) next.rate_value = "Percentage rate cannot exceed 100."; if (Number(value.sequence) < 1) next.sequence = "Sequence must be positive." }
    if (active === "plan-target-markets") { required("target_market_type", "Target-market type"); if (value.min_age !== null && value.min_age !== "" && value.max_age !== null && value.max_age !== "" && Number(value.min_age) > Number(value.max_age)) next.max_age = "Maximum age cannot be less than minimum age." }
    if (active === "plan-risk-categories") { required("underwriting_class", "Underwriting class"); required("loading_basis", "Loading basis") }
    if (active === "plan-occupation-risk-limits") { required("occupation_risk_category", "Occupation risk category"); if (Number(value.loading_rate) < 0 || Number(value.loading_rate) > 100) next.loading_rate = "Loading rate must be between 0 and 100." }
    if (active === "investment-fund-types") required("risk_profile", "Risk profile")
    if (active === "investment-funds") { required("fund_type", "Fund type"); required("currency", "Currency"); required("valuation_frequency", "Valuation frequency"); if (String(value.currency ?? "").length !== 3) next.currency = "Currency must be a three-letter code."; if (value.unit_price !== null && value.unit_price !== "" && Number(value.unit_price) <= 0) next.unit_price = "Unit price must be greater than zero."; if (typeof value.allocation_rules === "string") next.allocation_rules = "Allocation rules must be valid JSON." }
    if (screen.effectiveDated) { required("effective_from", "Effective from"); if (value.effective_from && value.effective_to && String(value.effective_to) < String(value.effective_from)) next.effective_to = "Effective to cannot be before effective from." }
    setErrors(next); return Object.keys(next).length === 0
  }
  const cleanPayload = (value: EditorState) => Object.fromEntries(Object.entries(value).filter(([key]) => key !== "__screen" && key !== "id" && key !== "created_at" && key !== "updated_at" && key !== "plan_type_id" && key !== "product_id" && key !== "fund_type_id"))
  const save = async () => { if (!validate()) return; setSaving(true); try { const payload = cleanPayload(editor.value); const endpoint = editor.row ? `${screen.endpoint}${editor.row.id}/` : screen.endpoint; await request(endpoint, { method: editor.row ? "PATCH" : "POST", body: JSON.stringify(payload) }); toast({ tone: "success", title: editor.row ? "Product setup updated" : "Product setup created", message: `${screen.title} saved successfully.` }); closeEditor(); setRefreshKey((value) => value + 1); void fetchOptions() } catch (error) { toast({ tone: "danger", title: "Save failed", message: error instanceof Error ? error.message : "The Product Setup record could not be saved." }) } finally { setSaving(false) } }
  const deactivate = async () => { if (!deactivateRow) return; try { await request(`${screen.endpoint}${deactivateRow.id}/deactivate/`, { method: "POST" }); toast({ tone: "success", title: "Setup deactivated", message: `${deactivateRow.code} is now inactive.` }); setDeactivateRow(null); setRefreshKey((value) => value + 1) } catch (error) { toast({ tone: "danger", title: "Deactivation failed", message: error instanceof Error ? error.message : "The setup could not be deactivated." }) } }
  const actions = useMemo<RowAction<ProductRecord>[]>(() => [{ key: "edit", label: "Edit", permission: "ol_parameters.update", onSelect: openEdit }, { key: "deactivate", label: "Deactivate", permission: "ol_parameters.deactivate", tone: "danger", isVisible: (row) => row.is_active, onSelect: setDeactivateRow }], [active])
  const changeTab = (id: string) => { setActive(id as ScreenKey); setFilters({}); setErrors({}) }
  const tabs = Object.values(screens).map((item) => ({ id: item.key, label: item.title }))
  const stats = [{ label: "Workspace", value: screen.title, helper: "Product Setup parameter registry" }, { label: "Access", value: canCreate || canUpdate ? "Configure" : "Read only", helper: canDeactivate ? "Deactivation available" : "No mutation permission" }]

  return <MasterDetailPage eyebrow="Ordinary Life Parameters / Product Setup" title={screen.title} description={screen.description} stats={stats} tabs={tabs} activeTab={active} onTabChange={changeTab} actions={canCreate ? <button type="button" className="button-primary" onClick={openCreate}><Plus size={16} aria-hidden="true" /> New setup</button> : undefined}>
    <div className="space-y-4">
      {!canView && <InfoBanner title="Read access required">Your current IAM access metadata does not include the OL parameter view permission.</InfoBanner>}
      <FilterBar definitions={screen.filters} value={filters} onChange={(key, next) => setFilters((current) => ({ ...current, [key]: next }))} onApply={() => undefined} onReset={() => setFilters({})} />
      <DataTable<ProductRecord> metadata={{ columns: screen.columns, defaultOrdering: screen.effectiveDated ? "-effective_from" : "code", pageSize: 20, totalLabel: "product setup records" }} fetcher={fetcher} filters={filters} refreshKey={refreshKey} actions={canView && (canUpdate || canDeactivate) ? actions : []} permissions={permissionKeys} exportFileName={`${active}-product-setup.csv`} caption={screen.title} />
    </div>
    <FormModal open={editor.open} title={`${editor.row ? "Edit" : "Create"} ${screen.title}`} description="Save changes through the OL Product Setup API. Option values and business validation remain server-authoritative." onClose={closeEditor} onSave={save} saving={saving} saveLabel={editor.row ? "Save changes" : "Create setup"}><ProductEditor value={editor.value} update={update} errors={errors} planTypeOptions={planTypeOptions} productOptions={productOptions} fundTypeOptions={fundTypeOptions} frequencyOptions={frequencyOptions} /></FormModal>
    <ConfirmModal open={Boolean(deactivateRow)} title="Deactivate product setup" description={`Deactivate ${deactivateRow?.code ?? "this setup"}? It will remain available for audit history but will no longer be active.`} confirmLabel="Deactivate" onClose={() => setDeactivateRow(null)} onConfirm={deactivate} />
  </MasterDetailPage>
}

export { screens as olProductSetupScreens }

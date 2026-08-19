import { useCallback, useEffect, useMemo, useState, type ChangeEvent, type ReactNode } from "react"
import { Plus } from "lucide-react"
import { request } from "../../lib/apiClient"
import { useAccess } from "../../lib/access"
import { DataTable, normalizeTableResponse } from "../../components/ui/DataTable"
import { FilterBar } from "../../components/ui/FilterBar"
import { FormModal, ConfirmModal, InfoBanner } from "../../components/ui/Overlays"
import { DateInput, DecimalInput, EditableGrid, TextInput, TextareaInput, Toggle } from "../../components/ui"
import { MasterDetailPage } from "../../components/ui/Patterns"
import { StatusBadge, type StatusTone } from "../../components/ui/StatusBadge"
import type { FilterValues } from "../../components/ui/FilterBar"
import type { EditableGridColumn } from "../../components/ui/EditableGrid"
import type { FilterDefinition, RowAction, TableColumn, TableResponse } from "../../components/ui/types"
import { useToast } from "../../components/ui/Toast"

const API_PREFIX = "/api/v1/ol-parameters"

type ScreenKey = "rates" | "grace" | "status" | "renewal" | "beneficial" | "member"

type PolicyRecord = {
  id: string
  code: string
  name: string
  description?: string | null
  is_active: boolean
  effective_from: string
  effective_to?: string | null
  product?: string | null
  plan?: string | null
  installment_type?: string
  frequency?: string
  age_from?: number | null
  age_to?: number | null
  term_from?: number | null
  term_to?: number | null
  policy_year_from?: number | null
  policy_year_to?: number | null
  rate_factor?: string | number
  currency?: string
  premium_frequency?: string
  grace_days?: number
  warning_days?: number
  pre_lapse_days?: number
  lapse_days?: number
  minimum_due_amount?: string | number | null
  display_order?: number
  badge_type?: string
  is_terminal?: boolean
  allowed_transitions?: string[]
  renewal_action?: string
  category?: string
  calculation_basis?: string
  default_ratio?: string | number
  allows_multiple?: boolean
  cover_type?: string
  member_relation?: string
  min_age?: number | null
  max_age?: number | null
  waiting_period_days?: number
  benefit_limit?: string | number | null
  premium_basis?: string
  coverage_basis?: string
}

type EditorValue = string | number | boolean | string[] | null | undefined
type EditorState = Record<string, EditorValue>
type RateEditorRow = {
  age_from: string
  age_to: string
  term_from: string
  term_to: string
  policy_year_from: string
  policy_year_to: string
  rate_factor: string
  currency: string
}

type ScreenConfig = {
  key: ScreenKey
  title: string
  description: string
  endpoint: string
  columns: TableColumn<PolicyRecord>[]
  filters: FilterDefinition[]
}

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

function badgeTone(value?: string): StatusTone {
  const normalized = String(value ?? "").toUpperCase()
  if (["POSITIVE", "SUCCESS", "GOOD", "APPROVED"].includes(normalized)) return "success"
  if (["WARNING", "PENDING", "ATTENTION"].includes(normalized)) return "warning"
  if (["NEGATIVE", "DANGER", "ERROR", "REJECTED"].includes(normalized)) return "danger"
  if (["INFO", "INFORMATION"].includes(normalized)) return "info"
  return "neutral"
}

function activeTone(row: PolicyRecord): StatusTone {
  if (!row.is_active) return "danger"
  if (row.effective_to && row.effective_to < today()) return "danger"
  if (row.effective_from > today()) return "info"
  return "success"
}

const commonColumns = (extra: TableColumn<PolicyRecord>[]): TableColumn<PolicyRecord>[] => [
  { key: "code", label: "Code", field: "code", sortable: true },
  { key: "name", label: "Name", field: "name", sortable: true },
  ...extra,
  { key: "effective_from", label: "Effective from", field: "effective_from", sortable: true, render: (value) => <DateState value={value as string} /> },
  { key: "effective_to", label: "Effective to", field: "effective_to", sortable: true, render: (value) => <DateState value={value as string | null} /> },
  { key: "status", label: "Status", render: (_value, row) => <StatusBadge value={!row.is_active ? "Inactive" : row.effective_to && row.effective_to < today() ? "Expired" : row.effective_from > today() ? "Scheduled" : "Active"} tone={activeTone(row)} /> },
]

const screens: Record<ScreenKey, ScreenConfig> = {
  rates: {
    key: "rates",
    title: "Anticipated Endowment Installment Rate",
    description: "Effective-dated rate factors by product, plan, frequency, age, term, policy year, and currency.",
    endpoint: `${API_PREFIX}/anticipated-endowment-rates/`,
    columns: commonColumns([
      { key: "product", label: "Product", field: "product", sortable: true, render: (value) => valueLabel(value) },
      { key: "plan", label: "Plan", field: "plan", sortable: true, render: (value) => valueLabel(value) },
      { key: "frequency", label: "Frequency", field: "frequency", sortable: true },
      { key: "age", label: "Age range", render: (_value, row) => `${valueLabel(row.age_from)} – ${valueLabel(row.age_to)}` },
      { key: "term", label: "Term range", render: (_value, row) => `${valueLabel(row.term_from)} – ${valueLabel(row.term_to)}` },
      { key: "policy_year", label: "Policy year", render: (_value, row) => `${valueLabel(row.policy_year_from)} – ${valueLabel(row.policy_year_to)}` },
      { key: "rate_factor", label: "Rate factor", field: "rate_factor", sortable: true, align: "right" },
    ]),
    filters: [
      { key: "product", label: "Product ID", type: "text", placeholder: "Product identifier" },
      { key: "plan", label: "Plan ID", type: "text", placeholder: "Plan identifier" },
      { key: "frequency", label: "Frequency", type: "text", placeholder: "Configured frequency" },
      { key: "currency", label: "Currency", type: "text", placeholder: "ISO currency" },
      { key: "is_active", label: "Active status", type: "text", placeholder: "true or false" },
    ],
  },
  grace: {
    key: "grace",
    title: "OL Grace Period",
    description: "Premium warning, grace, pre-lapse, and lapse timing by optional product scope.",
    endpoint: `${API_PREFIX}/grace-periods/`,
    columns: commonColumns([
      { key: "product", label: "Product", field: "product", sortable: true, render: (value) => valueLabel(value) },
      { key: "plan", label: "Plan", field: "plan", sortable: true, render: (value) => valueLabel(value) },
      { key: "premium_frequency", label: "Premium frequency", field: "premium_frequency", sortable: true },
      { key: "grace_days", label: "Grace days", field: "grace_days", sortable: true, align: "right" },
      { key: "warning_days", label: "Warning days", field: "warning_days", sortable: true, align: "right" },
      { key: "pre_lapse_days", label: "Pre-lapse", field: "pre_lapse_days", sortable: true, align: "right" },
      { key: "lapse_days", label: "Lapse days", field: "lapse_days", sortable: true, align: "right" },
    ]),
    filters: [
      { key: "product", label: "Product ID", type: "text", placeholder: "Product identifier" },
      { key: "plan", label: "Plan ID", type: "text", placeholder: "Plan identifier" },
      { key: "premium_frequency", label: "Premium frequency", type: "text", placeholder: "Configured frequency" },
      { key: "is_active", label: "Active status", type: "text", placeholder: "true or false" },
    ],
  },
  status: {
    key: "status",
    title: "OL Policy Status",
    description: "Policy lifecycle status catalog with configured visual badges, terminal flags, and outgoing transitions.",
    endpoint: `${API_PREFIX}/policy-statuses/`,
    columns: commonColumns([
      { key: "display_order", label: "Order", field: "display_order", sortable: true, align: "right" },
      { key: "badge_type", label: "Configured badge", field: "badge_type", sortable: true, render: (value) => <StatusBadge value={valueLabel(value)} tone={badgeTone(String(value))} /> },
      { key: "is_terminal", label: "Terminal", field: "is_terminal", render: (value) => <StatusBadge value={value ? "Terminal" : "Non-terminal"} tone={value ? "danger" : "neutral"} /> },
      { key: "allowed_transitions", label: "Transitions", field: "allowed_transitions", render: (value) => valueLabel(Array.isArray(value) ? value.join(", ") : value) },
    ]),
    filters: [
      { key: "badge_type", label: "Badge type", type: "text", placeholder: "Configured badge" },
      { key: "is_terminal", label: "Terminal", type: "text", placeholder: "true or false" },
      { key: "is_active", label: "Active status", type: "text", placeholder: "true or false" },
    ],
  },
  renewal: {
    key: "renewal",
    title: "OL Policy Renewal Status",
    description: "Renewal status catalog with ordered workflow states and parameter-driven actions.",
    endpoint: `${API_PREFIX}/policy-renewal-statuses/`,
    columns: commonColumns([
      { key: "display_order", label: "Order", field: "display_order", sortable: true, align: "right" },
      { key: "renewal_action", label: "Renewal action", field: "renewal_action", sortable: true },
    ]),
    filters: [
      { key: "renewal_action", label: "Renewal action", type: "text", placeholder: "Configured action" },
      { key: "is_active", label: "Active status", type: "text", placeholder: "true or false" },
    ],
  },
  beneficial: {
    key: "beneficial",
    title: "OL Beneficial Type",
    description: "Beneficiary and benefit type catalog with calculation basis, ratio defaults, and multiplicity rules.",
    endpoint: `${API_PREFIX}/beneficial-types/`,
    columns: commonColumns([
      { key: "category", label: "Category", field: "category", sortable: true },
      { key: "calculation_basis", label: "Calculation basis", field: "calculation_basis", sortable: true },
      { key: "default_ratio", label: "Default ratio", field: "default_ratio", sortable: true, align: "right", render: (value) => `${valueLabel(value)}%` },
      { key: "allows_multiple", label: "Multiple", field: "allows_multiple", render: (value) => <StatusBadge value={value ? "Allowed" : "Single"} tone={value ? "success" : "neutral"} /> },
    ]),
    filters: [
      { key: "category", label: "Category", type: "text", placeholder: "Configured category" },
      { key: "calculation_basis", label: "Calculation basis", type: "text", placeholder: "Configured basis" },
      { key: "is_active", label: "Active status", type: "text", placeholder: "true or false" },
    ],
  },
  member: {
    key: "member",
    title: "OL Member Cover Configuration",
    description: "Effective-dated member and dependent eligibility, waiting period, premium basis, and benefit limits.",
    endpoint: `${API_PREFIX}/member-cover-configurations/`,
    columns: commonColumns([
      { key: "product", label: "Product", field: "product", sortable: true, render: (value) => valueLabel(value) },
      { key: "plan", label: "Plan", field: "plan", sortable: true, render: (value) => valueLabel(value) },
      { key: "cover_type", label: "Cover type", field: "cover_type", sortable: true },
      { key: "member_relation", label: "Relation", field: "member_relation", sortable: true },
      { key: "age_range", label: "Age range", render: (_value, row) => `${valueLabel(row.min_age)} – ${valueLabel(row.max_age)}` },
      { key: "waiting_period_days", label: "Waiting days", field: "waiting_period_days", sortable: true, align: "right" },
      { key: "benefit_limit", label: "Benefit limit", field: "benefit_limit", sortable: true, align: "right" },
    ]),
    filters: [
      { key: "product", label: "Product ID", type: "text", placeholder: "Product identifier" },
      { key: "plan", label: "Plan ID", type: "text", placeholder: "Plan identifier" },
      { key: "cover_type", label: "Cover type", type: "text", placeholder: "Configured cover" },
      { key: "member_relation", label: "Member relation", type: "text", placeholder: "Configured relation" },
      { key: "is_active", label: "Active status", type: "text", placeholder: "true or false" },
    ],
  },
}

const emptyEditor = (screen: ScreenKey): EditorState => ({
  code: "",
  name: "",
  description: "",
  effective_from: today(),
  effective_to: "",
  is_active: true,
  ...(screen === "rates" ? { product: "", plan: "", installment_type: "ANTICIPATED_ENDOWMENT", frequency: "ANNUAL", currency: "" } : {}),
  ...(screen === "grace" ? { product: "", plan: "", premium_frequency: "", grace_days: 0, warning_days: 0, pre_lapse_days: 0, lapse_days: 0, minimum_due_amount: "" } : {}),
  ...(screen === "status" ? { display_order: 0, badge_type: "NEUTRAL", is_terminal: false } : {}),
  ...(screen === "renewal" ? { display_order: 0, renewal_action: "NONE" } : {}),
  ...(screen === "beneficial" ? { category: "", calculation_basis: "PERCENTAGE", default_ratio: "0", allows_multiple: true } : {}),
  ...(screen === "member" ? { product: "", plan: "", cover_type: "INDIVIDUAL", member_relation: "MEMBER", min_age: "", max_age: "", waiting_period_days: 0, benefit_limit: "", premium_basis: "MEMBER_PREMIUM", coverage_basis: "SUM_ASSURED" } : {}),
})

const emptyRateRow = (): RateEditorRow => ({ age_from: "", age_to: "", term_from: "", term_to: "", policy_year_from: "", policy_year_to: "", rate_factor: "", currency: "" })

function toEditor(screen: ScreenKey, row: PolicyRecord): EditorState {
  return { ...emptyEditor(screen), ...row }
}

function numberValue(value: string): number | null {
  if (value.trim() === "") return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function cleanPayload(payload: Record<string, unknown>) {
  ;["product", "plan", "effective_to", "currency", "premium_frequency", "minimum_due_amount", "benefit_limit", "min_age", "max_age"].forEach((key) => {
    if (payload[key] === "") payload[key] = null
  })
  return payload
}

function validateRateRow(row: RateEditorRow): Record<string, string> {
  const errors: Record<string, string> = {}
  const ranges: Array<[keyof RateEditorRow, keyof RateEditorRow, string]> = [
    ["age_from", "age_to", "Age"],
    ["term_from", "term_to", "Term"],
    ["policy_year_from", "policy_year_to", "Policy year"],
  ]
  ranges.forEach(([from, to, label]) => {
    const lower = numberValue(row[from])
    const upper = numberValue(row[to])
    if (row[from] !== "" && lower === null) errors[from] = `${label} from must be numeric.`
    if (row[to] !== "" && upper === null) errors[to] = `${label} to must be numeric.`
    if (lower !== null && upper !== null && upper < lower) errors[to] = `${label} to cannot be less than ${label.toLowerCase()} from.`
  })
  if (row.rate_factor.trim() === "") errors.rate_factor = "Rate factor is required."
  else if (Number.isNaN(Number(row.rate_factor)) || Number(row.rate_factor) < 0) errors.rate_factor = "Rate factor must be non-negative."
  return errors
}

function EditorField({ label, name, value, onChange, error, required, type = "text", decimal = false }: { label: string; name: string; value: unknown; onChange: (event: ChangeEvent<HTMLInputElement>) => void; error?: string; required?: boolean; type?: string; decimal?: boolean }) {
  const Component = decimal ? DecimalInput : TextInput
  return <Component label={label} name={name} value={String(value ?? "")} onChange={onChange} error={error} required={required} type={type} />
}

function CommonEditorFields({ value, onChange, error }: { value: EditorState; onChange: (key: string, next: string | number | boolean | null) => void; error: (key: string) => string | undefined }) {
  const text = (key: string, label: string, required = false) => <EditorField label={label} name={key} value={value[key]} required={required} error={error(key)} onChange={(event) => onChange(key, event.target.value)} />
  return <>
    <div className="grid gap-4 sm:grid-cols-2">{text("code", "Code", true)}{text("name", "Name", true)}</div>
    <TextareaInput label="Description" name="description" value={String(value.description ?? "")} onChange={(event) => onChange("description", event.target.value)} />
    <div className="grid gap-4 sm:grid-cols-3">
      <DateInput label="Effective from" name="effective_from" required value={String(value.effective_from ?? "")} onChange={(event) => onChange("effective_from", event.target.value)} error={error("effective_from")} />
      <DateInput label="Effective to" name="effective_to" value={String(value.effective_to ?? "")} onChange={(event) => onChange("effective_to", event.target.value)} />
      <Toggle label="Active" checked={Boolean(value.is_active)} onChange={(checked) => onChange("is_active", checked)} />
    </div>
  </>
}

function RateEditor({ value, onChange, rateRows, setRateRows, error }: { value: EditorState; onChange: (key: string, next: string | number | boolean | null) => void; rateRows: RateEditorRow[]; setRateRows: (rows: RateEditorRow[]) => void; error: (key: string) => string | undefined }) {
  const rateColumns = useMemo<EditableGridColumn<RateEditorRow>[]>(() => {
    const input = (key: keyof RateEditorRow, label: string, decimal = false) => (row: RateEditorRow, _index: number, update: (patch: Partial<RateEditorRow>) => void) => <EditorField label={label} name={String(key)} value={row[key]} decimal={decimal} onChange={(event) => update({ [key]: event.target.value })} />
    return [
      { key: "age_from", label: "Age from", width: "110px", render: input("age_from", "Age from") },
      { key: "age_to", label: "Age to", width: "110px", render: input("age_to", "Age to") },
      { key: "term_from", label: "Term from", width: "110px", render: input("term_from", "Term from") },
      { key: "term_to", label: "Term to", width: "110px", render: input("term_to", "Term to") },
      { key: "policy_year_from", label: "Year from", width: "110px", render: input("policy_year_from", "Year from") },
      { key: "policy_year_to", label: "Year to", width: "110px", render: input("policy_year_to", "Year to") },
      { key: "rate_factor", label: "Rate factor", width: "130px", render: input("rate_factor", "Rate factor", true) },
      { key: "currency", label: "Currency", width: "110px", render: input("currency", "Currency") },
    ]
  }, [])
  return <div className="space-y-4">
    <CommonEditorFields value={value} onChange={onChange} error={error} />
    <div className="grid gap-4 sm:grid-cols-2">
      <EditorField label="Product ID" name="product" value={value.product} required error={error("product")} onChange={(event) => onChange("product", event.target.value)} />
      <EditorField label="Plan ID" name="plan" value={value.plan} onChange={(event) => onChange("plan", event.target.value)} />
      <EditorField label="Installment type" name="installment_type" value={value.installment_type} required error={error("installment_type")} onChange={(event) => onChange("installment_type", event.target.value)} />
      <EditorField label="Frequency" name="frequency" value={value.frequency} required error={error("frequency")} onChange={(event) => onChange("frequency", event.target.value)} />
    </div>
    <InfoBanner title="Rate row editor">Add one or more parameter-driven rows. The backend validates product/plan scope, range ordering, effective-date overlap, and decimal precision.</InfoBanner>
    <EditableGrid rows={rateRows} columns={rateColumns} getRowId={(_row, index) => `rate-row-${index}`} createRow={emptyRateRow} onChange={setRateRows} validateRow={validateRateRow} />
  </div>
}

function PolicyStatusEditor({ value, onChange, allowedTransitions, setAllowedTransitions, transitionOptions, error }: { value: EditorState; onChange: (key: string, next: string | number | boolean | null) => void; allowedTransitions: string[]; setAllowedTransitions: (values: string[]) => void; transitionOptions: PolicyRecord[]; error: (key: string) => string | undefined }) {
  const toggleTransition = (code: string) => setAllowedTransitions(allowedTransitions.includes(code) ? allowedTransitions.filter((item) => item !== code) : [...allowedTransitions, code])
  return <div className="space-y-4">
    <CommonEditorFields value={value} onChange={onChange} error={error} />
    <div className="grid gap-4 sm:grid-cols-2">
      <EditorField label="Display order" name="display_order" value={value.display_order} type="number" onChange={(event) => onChange("display_order", Number(event.target.value))} />
      <EditorField label="Configured badge type" name="badge_type" value={value.badge_type} required error={error("badge_type")} onChange={(event) => onChange("badge_type", event.target.value)} />
    </div>
    <Toggle label="Terminal status" checked={Boolean(value.is_terminal)} onChange={(checked) => onChange("is_terminal", checked)} />
    <div className="rounded-[10px] border p-4">
      <div className="mb-3"><p className="text-sm font-bold">Allowed transitions</p><p className="text-xs text-[var(--muted-foreground)]">Targets are loaded from the active Policy Status catalog. Terminal statuses must have no outgoing transitions.</p></div>
      {transitionOptions.length === 0 ? <p className="text-sm text-[var(--muted-foreground)]">No active policy statuses are available yet.</p> : <div className="grid gap-2 sm:grid-cols-2">{transitionOptions.filter((option) => option.code !== value.code).map((option) => <label key={option.id} className="flex items-center gap-3 rounded-md border px-3 py-2 text-sm"><input type="checkbox" checked={allowedTransitions.includes(option.code)} onChange={() => toggleTransition(option.code)} /> <span>{option.code}</span><span className="ml-auto text-xs text-[var(--muted-foreground)]">{option.name}</span></label>)}</div>}
      {error("allowed_transitions") && <p className="mt-2 text-xs font-medium text-[var(--destructive)]" role="alert">{error("allowed_transitions")}</p>}
    </div>
  </div>
}

function PolicyEditor({ screen, value, onChange, rateRows, setRateRows, allowedTransitions, setAllowedTransitions, transitionOptions, error }: { screen: ScreenKey; value: EditorState; onChange: (key: string, next: string | number | boolean | null) => void; rateRows: RateEditorRow[]; setRateRows: (rows: RateEditorRow[]) => void; allowedTransitions: string[]; setAllowedTransitions: (values: string[]) => void; transitionOptions: PolicyRecord[]; error: (key: string) => string | undefined }) {
  if (screen === "rates") return <RateEditor value={value} onChange={onChange} rateRows={rateRows} setRateRows={setRateRows} error={error} />
  if (screen === "status") return <PolicyStatusEditor value={value} onChange={onChange} allowedTransitions={allowedTransitions} setAllowedTransitions={setAllowedTransitions} transitionOptions={transitionOptions} error={error} />
  const text = (key: string, label: string, required = false) => <EditorField label={label} name={key} value={value[key]} required={required} error={error(key)} onChange={(event) => onChange(key, event.target.value)} />
  const numeric = (key: string, label: string, decimal = false) => <EditorField label={label} name={key} value={value[key]} decimal={decimal} type="number" error={error(key)} onChange={(event) => onChange(key, decimal ? event.target.value : Number(event.target.value))} />
  if (screen === "grace") return <div className="space-y-4"><CommonEditorFields value={value} onChange={onChange} error={error} /><div className="grid gap-4 sm:grid-cols-2">{text("product", "Product ID")}{text("plan", "Plan ID")}{text("premium_frequency", "Premium frequency")}{numeric("grace_days", "Grace days")}{numeric("warning_days", "Warning days")}{numeric("pre_lapse_days", "Pre-lapse days")}{numeric("lapse_days", "Lapse days")}{numeric("minimum_due_amount", "Minimum due amount", true)}</div><InfoBanner title="Timing validation">Grace, warning, and pre-lapse days cannot exceed the configured lapse days.</InfoBanner></div>
  if (screen === "renewal") return <div className="space-y-4"><CommonEditorFields value={value} onChange={onChange} error={error} /><div className="grid gap-4 sm:grid-cols-2">{numeric("display_order", "Display order")}{text("renewal_action", "Renewal action", true)}</div></div>
  if (screen === "beneficial") return <div className="space-y-4"><CommonEditorFields value={value} onChange={onChange} error={error} /><div className="grid gap-4 sm:grid-cols-2">{text("category", "Category", true)}{text("calculation_basis", "Calculation basis", true)}{numeric("default_ratio", "Default ratio (%)", true)}<Toggle label="Allows multiple" checked={Boolean(value.allows_multiple)} onChange={(checked) => onChange("allows_multiple", checked)} /></div><InfoBanner title="Ratio validation">Default ratio must be between 0 and 100 percent.</InfoBanner></div>
  return <div className="space-y-4"><CommonEditorFields value={value} onChange={onChange} error={error} /><div className="grid gap-4 sm:grid-cols-2">{text("product", "Product ID")}{text("plan", "Plan ID")}{text("cover_type", "Cover type", true)}{text("member_relation", "Member relation", true)}{numeric("min_age", "Minimum age")}{numeric("max_age", "Maximum age")}{numeric("waiting_period_days", "Waiting period days")}{numeric("benefit_limit", "Benefit limit", true)}{text("premium_basis", "Premium basis")}{text("coverage_basis", "Coverage basis")}</div><InfoBanner title="Eligibility validation">Maximum age cannot be less than minimum age, and benefit limits cannot be negative.</InfoBanner></div>
}

function validateEditor(screen: ScreenKey, value: EditorState, rateRows: RateEditorRow[], allowedTransitions: string[]): string | null {
  const required = ["code", "name", "effective_from"]
  if (screen === "rates") required.push("product", "installment_type", "frequency")
  if (screen === "status") required.push("badge_type")
  if (screen === "renewal") required.push("renewal_action")
  if (screen === "beneficial") required.push("category", "calculation_basis")
  if (screen === "member") required.push("cover_type", "member_relation")
  for (const key of required) if (!String(value[key] ?? "").trim()) return `${key.replace(/_/g, " ")} is required.`
  if (value.effective_to && String(value.effective_to) < String(value.effective_from)) return "effective to must be on or after effective from."
  if (screen === "rates") {
    if (!rateRows.length) return "At least one rate row is required."
    const rowError = rateRows.map(validateRateRow).find((errors) => Object.keys(errors).length > 0)
    if (rowError) return Object.values(rowError)[0]
  }
  if (screen === "grace") {
    const lapse = Number(value.lapse_days)
    if (["grace_days", "warning_days", "pre_lapse_days"].some((key) => Number(value[key]) > lapse)) return "Grace, warning, and pre-lapse days cannot exceed lapse days."
    if (Number(value.minimum_due_amount) < 0) return "Minimum due amount cannot be negative."
  }
  if (screen === "status") {
    if (Boolean(value.is_terminal) && allowedTransitions.length) return "Terminal policy statuses cannot have outgoing transitions."
    if (allowedTransitions.some((code) => code.toUpperCase() === String(value.code).toUpperCase())) return "A policy status cannot transition to itself."
  }
  if (screen === "beneficial" && (Number(value.default_ratio) < 0 || Number(value.default_ratio) > 100 || Number.isNaN(Number(value.default_ratio)))) return "Default ratio must be between 0 and 100."
  if (screen === "member") {
    if (value.min_age !== "" && value.max_age !== "" && Number(value.max_age) < Number(value.min_age)) return "Maximum age cannot be less than minimum age."
    if (value.benefit_limit !== "" && Number(value.benefit_limit) < 0) return "Benefit limit cannot be negative."
  }
  return null
}

function serializeEditor(value: EditorState, allowedTransitions: string[], rateRow?: RateEditorRow): Record<string, unknown> {
  const payload: Record<string, unknown> = { ...value }
  if (rateRow) {
    ;["age_from", "age_to", "term_from", "term_to", "policy_year_from", "policy_year_to"].forEach((key) => { payload[key] = numberValue(rateRow[key as keyof RateEditorRow]) })
    payload.rate_factor = rateRow.rate_factor
    payload.currency = rateRow.currency.toUpperCase()
  }
  if (allowedTransitions) payload.allowed_transitions = allowedTransitions
  return cleanPayload(payload)
}

export default function OLPolicySetup() {
  const { access, canAccess } = useAccess()
  const { toast } = useToast()
  const [active, setActive] = useState<ScreenKey>("rates")
  const [filters, setFilters] = useState<FilterValues>({})
  const [refreshKey, setRefreshKey] = useState(0)
  const [saving, setSaving] = useState(false)
  const [editor, setEditor] = useState<{ open: boolean; row?: PolicyRecord; value: EditorState }>({ open: false, value: emptyEditor("rates") })
  const [rateRows, setRateRows] = useState<RateEditorRow[]>([emptyRateRow()])
  const [allowedTransitions, setAllowedTransitions] = useState<string[]>([])
  const [transitionOptions, setTransitionOptions] = useState<PolicyRecord[]>([])
  const [deactivateRow, setDeactivateRow] = useState<PolicyRecord | null>(null)
  const screen = screens[active]

  const hasPermission = useCallback((permission: string) => {
    const [module, action] = permission.split(".")
    if (!access.permissions.length) return canAccess(module)
    return access.permissions.some((item) => item.module.toLowerCase() === module.toLowerCase() && item.action.toLowerCase() === action.toLowerCase())
  }, [access.permissions, canAccess])
  const canManage = hasPermission("ol_parameters.create") || hasPermission("ol_parameters.update")
  const canDeactivate = hasPermission("ol_parameters.deactivate") || canManage
  const permissionKeys = access.permissions.map((item) => `${item.module}.${item.action}`)

  useEffect(() => {
    if (!editor.open || active !== "status") return
    let mounted = true
    request<unknown>(`${screens.status.endpoint}?is_active=true&page_size=100&ordering=display_order`).then((payload) => {
      if (mounted) setTransitionOptions(normalizeTableResponse<PolicyRecord>(payload).results)
    }).catch(() => { if (mounted) setTransitionOptions([]) })
    return () => { mounted = false }
  }, [active, editor.open, refreshKey])

  const fetcher = useCallback(async (query: { page?: number; pageSize?: number; search?: string; ordering?: string; filters?: Record<string, string | number | boolean | null | undefined> }) => {
    const params = new URLSearchParams()
    if (query.page) params.set("page", String(query.page))
    if (query.pageSize) params.set("page_size", String(query.pageSize))
    if (query.search) params.set("search", query.search)
    if (query.ordering) params.set("ordering", query.ordering)
    Object.entries(query.filters ?? {}).forEach(([key, value]) => { if (value !== undefined && value !== null && value !== "") params.set(key, String(value)) })
    return normalizeTableResponse<PolicyRecord>(await request<unknown>(`${screen.endpoint}?${params.toString()}`))
  }, [screen.endpoint])

  const openCreate = () => {
    setEditor({ open: true, value: emptyEditor(active) })
    setRateRows([emptyRateRow()])
    setAllowedTransitions([])
  }
  const openEdit = (row: PolicyRecord) => {
    setEditor({ open: true, row, value: toEditor(active, row) })
    setRateRows(active === "rates" ? [{ ...emptyRateRow(), age_from: valueLabel(row.age_from) === "—" ? "" : valueLabel(row.age_from), age_to: valueLabel(row.age_to) === "—" ? "" : valueLabel(row.age_to), term_from: valueLabel(row.term_from) === "—" ? "" : valueLabel(row.term_from), term_to: valueLabel(row.term_to) === "—" ? "" : valueLabel(row.term_to), policy_year_from: valueLabel(row.policy_year_from) === "—" ? "" : valueLabel(row.policy_year_from), policy_year_to: valueLabel(row.policy_year_to) === "—" ? "" : valueLabel(row.policy_year_to), rate_factor: valueLabel(row.rate_factor) === "—" ? "" : valueLabel(row.rate_factor), currency: row.currency ?? "" }] : [emptyRateRow()])
    setAllowedTransitions(active === "status" ? row.allowed_transitions ?? [] : [])
  }
  const closeEditor = () => { if (!saving) setEditor({ open: false, value: emptyEditor(active) }) }
  const updateEditor = (key: string, next: string | number | boolean | null) => setEditor((current) => ({ ...current, value: { ...current.value, [key]: next } }))
  const editorError = (key: string) => {
    const value = editor.value[key]
    if (["code", "name", "effective_from"].includes(key) && !String(value ?? "").trim()) return "This field is required."
    if (["product", "installment_type", "frequency", "badge_type", "renewal_action", "category", "calculation_basis", "cover_type", "member_relation"].includes(key) && !String(value ?? "").trim()) return "This field is required."
    if (key === "effective_to" && value && String(value) < String(editor.value.effective_from)) return "Effective to must be on or after effective from."
    if (active === "beneficial" && key === "default_ratio" && (Number(value) < 0 || Number(value) > 100)) return "Enter a value between 0 and 100."
    if (active === "member" && key === "max_age" && editor.value.min_age !== "" && value !== "" && Number(value) < Number(editor.value.min_age)) return "Maximum age cannot be less than minimum age."
    return undefined
  }

  const saveEditor = async () => {
    const validationMessage = validateEditor(active, editor.value, rateRows, allowedTransitions)
    if (validationMessage) { toast({ tone: "danger", title: "Check the form", message: validationMessage }); return }
    try {
      setSaving(true)
      if (active === "rates") {
        if (editor.row) {
          await request(`${screen.endpoint}${editor.row.id}/`, { method: "PATCH", body: JSON.stringify(serializeEditor(editor.value, [], rateRows[0])) })
          for (const extraRow of rateRows.slice(1)) await request(screen.endpoint, { method: "POST", body: JSON.stringify(serializeEditor(editor.value, [], extraRow)) })
        } else {
          for (const rateRow of rateRows) await request(screen.endpoint, { method: "POST", body: JSON.stringify(serializeEditor(editor.value, [], rateRow)) })
        }
      } else {
        const payload = serializeEditor(editor.value, active === "status" ? allowedTransitions : [])
        const path = editor.row ? `${screen.endpoint}${editor.row.id}/` : screen.endpoint
        await request(path, { method: editor.row ? "PATCH" : "POST", body: JSON.stringify(payload) })
      }
      toast({ tone: "success", title: editor.row ? "Setup updated" : "Setup created", message: `${screen.title} saved successfully.` })
      closeEditor()
      setRefreshKey((current) => current + 1)
    } catch (error) {
      toast({ tone: "danger", title: "Save failed", message: error instanceof Error ? error.message : "The setup could not be saved." })
    } finally { setSaving(false) }
  }

  const deactivate = async () => {
    if (!deactivateRow) return
    try {
      await request(`${screen.endpoint}${deactivateRow.id}/deactivate/`, { method: "POST" })
      toast({ tone: "success", title: "Setup deactivated", message: `${deactivateRow.code} is now inactive.` })
      setDeactivateRow(null)
      setRefreshKey((current) => current + 1)
    } catch (error) {
      toast({ tone: "danger", title: "Deactivation failed", message: error instanceof Error ? error.message : "The setup could not be deactivated." })
    }
  }

  const actions = useMemo<RowAction<PolicyRecord>[]>(() => [
    { key: "edit", label: "Edit", permission: "ol_parameters.update", onSelect: openEdit },
    { key: "deactivate", label: "Deactivate", permission: "ol_parameters.deactivate", tone: "danger", isVisible: (row) => row.is_active, onSelect: setDeactivateRow },
  ], [active])
  const stats = [
    { label: "Workspace", value: screen.title, helper: "Backend parameter registry" },
    { label: "Access", value: canManage ? "Configure" : "Read only", helper: canDeactivate ? "Deactivation available" : "No mutation permission" },
  ]

  return <MasterDetailPage eyebrow="Ordinary Life Parameters / Policy Setup" title={screen.title} description={screen.description} stats={stats} tabs={Object.values(screens).map((item) => ({ id: item.key, label: item.title }))} activeTab={active} onTabChange={(id) => { setActive(id as ScreenKey); setFilters({}) }} actions={canManage ? <button type="button" className="button-primary" onClick={openCreate}><Plus size={16} aria-hidden="true" /> New setup</button> : undefined}>
    <div className="space-y-4">
      {!hasPermission("ol_parameters.view") && <InfoBanner title="Read access required">Your current IAM access metadata does not include the OL parameter view permission.</InfoBanner>}
      <FilterBar definitions={screen.filters} value={filters} onChange={(key, next) => setFilters((current) => ({ ...current, [key]: next }))} onApply={() => undefined} onReset={() => setFilters({})} />
      <DataTable<PolicyRecord> key={screen.key} metadata={{ columns: screen.columns, defaultOrdering: "-effective_from", pageSize: 20, totalLabel: "policy setups" }} fetcher={fetcher} filters={filters} refreshKey={refreshKey} actions={hasPermission("ol_parameters.view") && (canManage || canDeactivate) ? actions : []} permissions={permissionKeys} exportFileName={`${screen.key}-policy-setup.csv`} caption={screen.title} />
    </div>
    <FormModal open={editor.open} title={`${editor.row ? "Edit" : "Create"} ${screen.title}`} description="Save changes through the OL Parameters API. Effective dates and business validation remain server-authoritative." onClose={closeEditor} onSave={saveEditor} saving={saving} saveLabel={editor.row ? "Save changes" : "Create setup"}>
      <PolicyEditor screen={active} value={editor.value} onChange={updateEditor} rateRows={rateRows} setRateRows={setRateRows} allowedTransitions={allowedTransitions} setAllowedTransitions={setAllowedTransitions} transitionOptions={transitionOptions} error={editorError} />
    </FormModal>
    <ConfirmModal open={Boolean(deactivateRow)} title="Deactivate policy setup" description={`Deactivate ${deactivateRow?.code ?? "this setup"}? It will remain available for audit history but will no longer be active.`} confirmLabel="Deactivate" onClose={() => setDeactivateRow(null)} onConfirm={deactivate} />
  </MasterDetailPage>
}

export { screens as olPolicySetupScreens }

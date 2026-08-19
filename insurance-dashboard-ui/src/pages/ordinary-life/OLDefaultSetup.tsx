import { useCallback, useMemo, useState, type ChangeEvent } from "react"
import { Plus } from "lucide-react"
import { request } from "../../lib/apiClient"
import { useAccess } from "../../lib/access"
import { DataTable } from "../../components/ui/DataTable"
import { FilterBar } from "../../components/ui/FilterBar"
import { FormModal, InfoBanner, ConfirmModal } from "../../components/ui/Overlays"
import { DateInput, DecimalInput, SelectInput, TextareaInput, TextInput, Toggle } from "../../components/ui/FormControls"
import { MasterDetailPage } from "../../components/ui/Patterns"
import { StatusBadge } from "../../components/ui/StatusBadge"
import type { FilterValues } from "../../components/ui/FilterBar"
import type { FilterDefinition, RowAction, TableColumn, TableResponse } from "../../components/ui/types"
import { useToast } from "../../components/ui/Toast"
import type { FilterOption } from "../../components/ui/types"

type ParameterRecord = {
  id: string
  code: string
  name: string
  description?: string
  is_active: boolean
  effective_from: string
  effective_to?: string | null
  parameter_key?: string
  parameter_category?: string
  value_type?: string
  value?: unknown
  calculation_area?: string
  calculation_basis?: string
  formula_key?: string
  sequence?: number
  configuration?: Record<string, unknown>
  partner?: string | null
  product?: string | null
  plan?: string | null
  rider?: string | null
  channel?: string
  intermediary_type?: string
  branch?: string | null
  currency?: string
  rate_type?: string
  rate_value?: string | number
  priority?: number
  reason?: string
  auto_create_maturity_claim?: boolean
  days_before_maturity_to_initiate?: number
  notification_days?: number
  default_payout_method?: string
  require_documents?: boolean
  require_approval?: boolean
  maturity_claim_status_to_create?: string
}

type ScreenKey = "default" | "commission" | "computation" | "maturity"

type ScreenConfig = {
  key: ScreenKey
  title: string
  description: string
  endpoint: string
  permission: string
  columns: TableColumn<ParameterRecord>[]
  filters: FilterDefinition[]
}

type EditorState = Record<string, string | number | boolean | null | undefined>

const TextField = TextInput
const DecimalField = DecimalInput
const DateField = DateInput
const TextAreaField = TextareaInput
function SelectField({ label, name, required, value, options, onChange }: { label: string; name: string; required?: boolean; value: string; options: FilterOption[]; onChange: (event: ChangeEvent<HTMLSelectElement>) => void }) {
  return <SelectInput label={label} name={name} required={required} value={value} onChange={onChange}>{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</SelectInput>
}
function ToggleField({ label, checked, onChange }: { label: string; name?: string; checked: boolean; onChange: (checked: boolean) => void }) {
  return <Toggle label={label} checked={checked} onChange={onChange} />
}

const API_PREFIX = "/api/v1/ol-parameters"

const VALUE_TYPES = [
  { label: "String", value: "STRING" },
  { label: "Text", value: "TEXT" },
  { label: "Integer", value: "INTEGER" },
  { label: "Decimal", value: "DECIMAL" },
  { label: "Boolean", value: "BOOLEAN" },
  { label: "Date", value: "DATE" },
  { label: "JSON", value: "JSON" },
]

const RATE_TYPES = [
  { label: "Percentage", value: "PERCENTAGE" },
  { label: "Fixed", value: "FIXED" },
  { label: "Factor", value: "FACTOR" },
]

const tableDate = (value?: string | null) => value ? new Intl.DateTimeFormat("en-GB", { dateStyle: "medium" }).format(new Date(`${value}T00:00:00`)) : "—"
const valueLabel = (value: unknown) => value === null || value === undefined || value === "" ? "—" : typeof value === "object" ? JSON.stringify(value) : String(value)

const commonColumns = (extra: TableColumn<ParameterRecord>[]): TableColumn<ParameterRecord>[] => [
  { key: "code", label: "Code", field: "code", sortable: true },
  { key: "name", label: "Name", field: "name", sortable: true },
  ...extra,
  { key: "effective_from", label: "Effective from", field: "effective_from", sortable: true, render: (value) => tableDate(String(value)) },
  { key: "effective_to", label: "Effective to", field: "effective_to", sortable: true, render: (value) => tableDate(value as string | null) },
  { key: "is_active", label: "Status", field: "is_active", render: (value) => <StatusBadge value={value ? "Active" : "Inactive"} tone={value ? "success" : "neutral"} /> },
]

const screens: Record<ScreenKey, ScreenConfig> = {
  default: {
    key: "default",
    title: "Default System Parameters",
    description: "Typed, effective-dated defaults consumed by Ordinary Life workflows.",
    endpoint: `${API_PREFIX}/default-system-parameters/`,
    permission: "ol_parameters.update",
    columns: commonColumns([
      { key: "parameter_category", label: "Category", field: "parameter_category", sortable: true },
      { key: "parameter_key", label: "Parameter key", field: "parameter_key", sortable: true },
      { key: "value_type", label: "Type", field: "value_type", sortable: true },
      { key: "value", label: "Typed value", field: "value", render: (value) => <span className="max-w-[230px] truncate font-mono text-xs">{valueLabel(value)}</span> },
    ]),
    filters: [
      { key: "parameter_category", label: "Category", type: "text", placeholder: "e.g. QUOTATION" },
      { key: "value_type", label: "Value type", type: "select", options: VALUE_TYPES },
    ],
  },
  commission: {
    key: "commission",
    title: "Override Commission Setup",
    description: "Priority-ordered commission overrides scoped to partner, product, plan, channel, and effective dates.",
    endpoint: `${API_PREFIX}/override-commission-setups/`,
    permission: "ol_parameters.update",
    columns: commonColumns([
      { key: "partner", label: "Partner / agent", field: "partner", sortable: true, render: (value) => valueLabel(value) },
      { key: "product", label: "Product", field: "product", sortable: true, render: (value) => valueLabel(value) },
      { key: "plan", label: "Plan", field: "plan", sortable: true, render: (value) => valueLabel(value) },
      { key: "channel", label: "Channel", field: "channel", sortable: true },
      { key: "rate_value", label: "Rate", field: "rate_value", align: "right", render: (value, row) => `${valueLabel(value)}${row.rate_type === "PERCENTAGE" ? "%" : ""}` },
      { key: "priority", label: "Priority", field: "priority", sortable: true, align: "right" },
    ]),
    filters: [
      { key: "channel", label: "Channel", type: "text", placeholder: "Channel" },
      { key: "rate_type", label: "Rate type", type: "select", options: RATE_TYPES },
      { key: "is_active", label: "Status", type: "select", options: [{ label: "Active", value: "true" }, { label: "Inactive", value: "false" }] },
    ],
  },
  computation: {
    key: "computation",
    title: "Computation Approach",
    description: "Named calculation strategies selected by product and future transaction engines.",
    endpoint: `${API_PREFIX}/computation-approaches/`,
    permission: "ol_parameters.update",
    columns: commonColumns([
      { key: "calculation_area", label: "Module", field: "calculation_area", sortable: true },
      { key: "calculation_basis", label: "Basis", field: "calculation_basis", sortable: true },
      { key: "formula_key", label: "Formula key", field: "formula_key", sortable: true },
      { key: "sequence", label: "Sequence", field: "sequence", sortable: true, align: "right" },
    ]),
    filters: [
      { key: "calculation_area", label: "Module", type: "text", placeholder: "Premium, tax, claim…" },
      { key: "calculation_basis", label: "Basis", type: "text", placeholder: "Basis" },
    ],
  },
  maturity: {
    key: "maturity",
    title: "Maturity Claim Setup",
    description: "Configure automatic maturity claim initiation, notifications, payout, documents, and approvals.",
    endpoint: `${API_PREFIX}/maturity-claim-setups/`,
    permission: "ol_parameters.update",
    columns: commonColumns([
      { key: "product", label: "Product scope", field: "product", sortable: true, render: (value) => valueLabel(value) },
      { key: "plan", label: "Plan scope", field: "plan", sortable: true, render: (value) => valueLabel(value) },
      { key: "auto_create_maturity_claim", label: "Auto-create", field: "auto_create_maturity_claim", render: (value) => <StatusBadge value={value ? "Yes" : "No"} tone={value ? "success" : "neutral"} /> },
      { key: "days_before_maturity_to_initiate", label: "Days before", field: "days_before_maturity_to_initiate", sortable: true, align: "right" },
      { key: "default_payout_method", label: "Payout method", field: "default_payout_method", sortable: true },
      { key: "require_approval", label: "Approval", field: "require_approval", render: (value) => <StatusBadge value={value ? "Required" : "Not required"} tone={value ? "warning" : "neutral"} /> },
    ]),
    filters: [
      { key: "auto_create_maturity_claim", label: "Auto-create", type: "select", options: [{ label: "Yes", value: "true" }, { label: "No", value: "false" }] },
      { key: "require_approval", label: "Approval", type: "select", options: [{ label: "Required", value: "true" }, { label: "Not required", value: "false" }] },
    ],
  },
}

const emptyEditor = (key: ScreenKey): EditorState => ({
  code: "",
  name: "",
  description: "",
  effective_from: new Date().toISOString().slice(0, 10),
  effective_to: "",
  is_active: true,
  ...(key === "default" ? { parameter_key: "", parameter_category: "", value_type: "STRING", typed_value: "" } : {}),
  ...(key === "commission" ? { partner: "", product: "", plan: "", intermediary_type: "", channel: "", rate_type: "PERCENTAGE", rate_value: "", priority: 100, reason: "" } : {}),
  ...(key === "computation" ? { calculation_area: "", calculation_basis: "", formula_key: "", sequence: 1, configuration: "{}" } : {}),
  ...(key === "maturity" ? { product: "", plan: "", auto_create_maturity_claim: true, days_before_maturity_to_initiate: 0, notification_days: 0, default_payout_method: "BANK_TRANSFER", require_documents: true, require_approval: true, maturity_claim_status_to_create: "REPORTED" } : {}),
})

const toEditor = (key: ScreenKey, row: ParameterRecord): EditorState => ({
  ...emptyEditor(key),
  ...row,
  typed_value: row.value === null || row.value === undefined ? "" : String(row.value),
  configuration: row.configuration ? JSON.stringify(row.configuration, null, 2) : "{}",
}) as EditorState

function Editor({ screen, value, onChange, overlapWarning }: { screen: ScreenKey; value: EditorState; onChange: (key: string, next: string | number | boolean | null) => void; overlapWarning?: string }) {
  const field = (name: string) => value[name]
  const error = (name: string) => {
    const current = field(name)
    if (["code", "name", "effective_from"].includes(name) && !String(current ?? "").trim()) return "This field is required."
    if (screen === "default" && ["parameter_key", "parameter_category", "typed_value"].includes(name) && !String(current ?? "").trim()) return "This field is required."
    if (screen === "commission" && name === "rate_value" && (current === "" || Number(current) < 0)) return "Enter a non-negative rate."
    if (screen === "computation" && ["calculation_area", "calculation_basis", "formula_key"].includes(name) && !String(current ?? "").trim()) return "This field is required."
    if (screen === "maturity" && name === "default_payout_method" && !String(current ?? "").trim()) return "A payout method is required."
    return undefined
  }
  const common = <>
    <div className="grid gap-4 sm:grid-cols-2"><TextField label="Code" name="code" required value={String(field("code") ?? "")} onChange={(event) => onChange("code", event.target.value)} error={error("code")} /><TextField label="Name" name="name" required value={String(field("name") ?? "")} onChange={(event) => onChange("name", event.target.value)} error={error("name")} /></div>
    <TextAreaField label="Description" name="description" value={String(field("description") ?? "")} onChange={(event) => onChange("description", event.target.value)} />
    <div className="grid gap-4 sm:grid-cols-3"><DateField label="Effective from" name="effective_from" required value={String(field("effective_from") ?? "")} onChange={(event) => onChange("effective_from", event.target.value)} error={error("effective_from")} /><DateField label="Effective to" name="effective_to" value={String(field("effective_to") ?? "")} onChange={(event) => onChange("effective_to", event.target.value)} /><ToggleField label="Active" name="is_active" checked={Boolean(field("is_active"))} onChange={(checked) => onChange("is_active", checked)} /></div>
  </>

  if (screen === "default") {
    const type = String(field("value_type") ?? "STRING")
    return <div className="space-y-4">{common}<div className="grid gap-4 sm:grid-cols-2"><TextField label="Parameter key" name="parameter_key" required value={String(field("parameter_key") ?? "")} onChange={(event) => onChange("parameter_key", event.target.value)} error={error("parameter_key")} /><TextField label="Category" name="parameter_category" required value={String(field("parameter_category") ?? "")} onChange={(event) => onChange("parameter_category", event.target.value)} error={error("parameter_category")} /></div><SelectField label="Value type" name="value_type" required value={type} options={VALUE_TYPES} onChange={(event) => onChange("value_type", event.target.value)} />{type === "BOOLEAN" ? <ToggleField label="Typed value" name="typed_value" checked={Boolean(field("typed_value"))} onChange={(checked) => onChange("typed_value", checked)} /> : type === "DATE" ? <DateField label="Typed value" name="typed_value" required value={String(field("typed_value") ?? "")} onChange={(event) => onChange("typed_value", event.target.value)} error={error("typed_value")} /> : type === "DECIMAL" ? <DecimalField label="Typed value" name="typed_value" required value={String(field("typed_value") ?? "")} onChange={(event) => onChange("typed_value", event.target.value)} error={error("typed_value")} /> : <TextField label={type === "JSON" ? "Typed value (JSON)" : "Typed value"} name="typed_value" required value={String(field("typed_value") ?? "")} onChange={(event) => onChange("typed_value", event.target.value)} error={error("typed_value")} hint={type === "JSON" ? "Enter a valid JSON value." : undefined} />}</div>
  }

  if (screen === "commission") return <div className="space-y-4">{common}<InfoBanner title="Overlap warning">{overlapWarning ?? "The backend checks overlapping effective periods for matching scope during save."}</InfoBanner><div className="grid gap-4 sm:grid-cols-2"><TextField label="Partner / agent ID" name="partner" value={String(field("partner") ?? "")} onChange={(event) => onChange("partner", event.target.value)} /><TextField label="Product ID" name="product" value={String(field("product") ?? "")} onChange={(event) => onChange("product", event.target.value)} /><TextField label="Plan ID" name="plan" value={String(field("plan") ?? "")} onChange={(event) => onChange("plan", event.target.value)} /><TextField label="Channel" name="channel" value={String(field("channel") ?? "")} onChange={(event) => onChange("channel", event.target.value)} /><SelectField label="Rate type" name="rate_type" required value={String(field("rate_type") ?? "PERCENTAGE")} options={RATE_TYPES} onChange={(event) => onChange("rate_type", event.target.value)} /><DecimalField label="Rate value" name="rate_value" required value={String(field("rate_value") ?? "")} onChange={(event) => onChange("rate_value", event.target.value)} error={error("rate_value")} /><TextField label="Priority" name="priority" type="number" value={String(field("priority") ?? 100)} onChange={(event) => onChange("priority", Number(event.target.value))} /><TextAreaField label="Reason / narration" name="reason" value={String(field("reason") ?? "")} onChange={(event) => onChange("reason", event.target.value)} /></div></div>
  if (screen === "computation") return <div className="space-y-4">{common}<div className="grid gap-4 sm:grid-cols-2"><TextField label="Module" name="calculation_area" required value={String(field("calculation_area") ?? "")} onChange={(event) => onChange("calculation_area", event.target.value)} error={error("calculation_area")} /><TextField label="Basis" name="calculation_basis" required value={String(field("calculation_basis") ?? "")} onChange={(event) => onChange("calculation_basis", event.target.value)} error={error("calculation_basis")} /><TextField label="Formula key" name="formula_key" required value={String(field("formula_key") ?? "")} onChange={(event) => onChange("formula_key", event.target.value)} error={error("formula_key")} /><TextField label="Sequence" name="sequence" type="number" required value={String(field("sequence") ?? 1)} onChange={(event) => onChange("sequence", Number(event.target.value))} /></div><TextAreaField label="Configuration JSON" name="configuration" value={String(field("configuration") ?? "{}")} onChange={(event) => onChange("configuration", event.target.value)} hint="Optional JSON object consumed by the calculation engine." /></div>
  return <div className="space-y-4">{common}<div className="grid gap-4 sm:grid-cols-2"><TextField label="Product ID" name="product" value={String(field("product") ?? "")} onChange={(event) => onChange("product", event.target.value)} /><TextField label="Plan ID" name="plan" value={String(field("plan") ?? "")} onChange={(event) => onChange("plan", event.target.value)} /><TextField label="Days before maturity" name="days_before_maturity_to_initiate" type="number" value={String(field("days_before_maturity_to_initiate") ?? 0)} onChange={(event) => onChange("days_before_maturity_to_initiate", Number(event.target.value))} /><TextField label="Notification days" name="notification_days" type="number" value={String(field("notification_days") ?? 0)} onChange={(event) => onChange("notification_days", Number(event.target.value))} /><TextField label="Payout method" name="default_payout_method" required value={String(field("default_payout_method") ?? "BANK_TRANSFER")} onChange={(event) => onChange("default_payout_method", event.target.value)} error={error("default_payout_method")} /><TextField label="Claim status to create" name="maturity_claim_status_to_create" required value={String(field("maturity_claim_status_to_create") ?? "REPORTED")} onChange={(event) => onChange("maturity_claim_status_to_create", event.target.value)} /></div><div className="grid gap-4 sm:grid-cols-3"><ToggleField label="Auto-create maturity claim" name="auto_create_maturity_claim" checked={Boolean(field("auto_create_maturity_claim"))} onChange={(checked) => onChange("auto_create_maturity_claim", checked)} /><ToggleField label="Require documents" name="require_documents" checked={Boolean(field("require_documents"))} onChange={(checked) => onChange("require_documents", checked)} /><ToggleField label="Require approval" name="require_approval" checked={Boolean(field("require_approval"))} onChange={(checked) => onChange("require_approval", checked)} /></div></div>
}

function validateEditor(screen: ScreenKey, state: EditorState): string | null {
  const required = ["code", "name", "effective_from"]
  if (screen === "default") required.push("parameter_key", "parameter_category", "typed_value")
  if (screen === "computation") required.push("calculation_area", "calculation_basis", "formula_key")
  if (screen === "maturity") required.push("default_payout_method", "maturity_claim_status_to_create")
  for (const key of required) {
    if (!String(state[key] ?? "").trim()) return `${key.replace(/_/g, " ")} is required.`
  }
  if (screen === "commission" && (state.rate_value === "" || Number(state.rate_value) < 0 || Number.isNaN(Number(state.rate_value)))) return "rate value must be a non-negative number."
  if (screen === "default" && state.value_type === "JSON") {
    try { JSON.parse(String(state.typed_value ?? "")) } catch { return "typed value must contain valid JSON." }
  }
  if (screen === "computation") {
    try { JSON.parse(String(state.configuration || "{}")) } catch { return "configuration must contain valid JSON." }
  }
  if (state.effective_to && String(state.effective_to) < String(state.effective_from)) return "effective to must be on or after effective from."
  return null
}

function serializeEditor(screen: ScreenKey, state: EditorState) {
  const payload: Record<string, unknown> = { ...state }
  if (screen === "default") {
    payload.code = String(state.parameter_key ?? state.code ?? "").trim().toUpperCase()
    payload.parameter_key = payload.code
    if (state.value_type === "INTEGER") payload.typed_value = Number(state.typed_value)
    if (state.value_type === "DECIMAL") payload.typed_value = String(state.typed_value ?? "")
    if (state.value_type === "JSON") payload.typed_value = JSON.parse(String(state.typed_value || "null"))
  }
  if (screen === "computation") payload.configuration = JSON.parse(String(state.configuration || "{}"))
  ;["partner", "product", "plan", "rider", "branch"].forEach((key) => { if (payload[key] === "") payload[key] = null })
  return payload
}

export default function OLDefaultSetup() {
  const { canAccess } = useAccess()
  const { toast } = useToast()
  const [active, setActive] = useState<ScreenKey>("default")
  const [filters, setFilters] = useState<FilterValues>({})
  const [editor, setEditor] = useState<{ open: boolean; row?: ParameterRecord; state: EditorState }>({ open: false, state: emptyEditor("default") })
  const [saving, setSaving] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)
  const [deactivateRow, setDeactivateRow] = useState<ParameterRecord | null>(null)
  const screen = screens[active]
  const { access } = useAccess()
  const hasPermission = useCallback((permission: string) => {
    const [module, action] = permission.split(".")
    if (!access.permissions.length) return canAccess(module)
    return access.permissions.some((item) => item.module.toLowerCase() === module.toLowerCase() && item.action.toLowerCase() === action.toLowerCase())
  }, [access.permissions, canAccess])
  const canManage = hasPermission("ol_parameters.update") || hasPermission("ol_parameters.create")
  const canDeactivate = hasPermission("ol_parameters.deactivate") || canManage
  const permissionKeys = access.permissions.map((item) => `${item.module}.${item.action}`)

  const fetcher = useCallback(async (query: { page?: number; pageSize?: number; search?: string; ordering?: string; filters?: Record<string, string | number | boolean | null | undefined> }) => {
    const params = new URLSearchParams()
    if (query.page) params.set("page", String(query.page))
    if (query.pageSize) params.set("page_size", String(query.pageSize))
    if (query.search) params.set("search", query.search)
    if (query.ordering) params.set("ordering", query.ordering)
    Object.entries(query.filters ?? {}).forEach(([key, value]) => { if (value !== undefined && value !== null && value !== "") params.set(key, String(value)) })
    return request<TableResponse<ParameterRecord>>(`${screen.endpoint}?${params.toString()}`)
  }, [screen.endpoint])

  const openCreate = () => setEditor({ open: true, state: emptyEditor(active) })
  const openEdit = (row: ParameterRecord) => setEditor({ open: true, row, state: toEditor(active, row) })
  const closeEditor = () => { if (!saving) setEditor({ open: false, state: emptyEditor(active) }) }
  const updateEditor = (key: string, next: string | number | boolean | null) => setEditor((current) => ({ ...current, state: { ...current.state, [key]: next, ...(key === "parameter_key" ? { code: String(next).toUpperCase() } : {}) } }))

  const saveEditor = async () => {
    const validationMessage = validateEditor(active, editor.state)
    if (validationMessage) {
      toast({ tone: "danger", title: "Check required fields", message: validationMessage })
      return
    }
    try {
      setSaving(true)
      const payload = serializeEditor(active, editor.state)
      const path = editor.row ? `${screen.endpoint}${editor.row.id}/` : screen.endpoint
      await request(path, { method: editor.row ? "PATCH" : "POST", body: JSON.stringify(payload) })
      toast({ tone: "success", title: editor.row ? "Parameter updated" : "Parameter created", message: `${screen.title} saved successfully.` })
      closeEditor()
      setRefreshKey((current) => current + 1)
    } catch (error) {
      toast({ tone: "danger", title: "Save failed", message: error instanceof Error ? error.message : "The parameter could not be saved." })
    } finally { setSaving(false) }
  }

  const deactivate = async () => {
    if (!deactivateRow) return
    try {
      await request(`${screen.endpoint}${deactivateRow.id}/deactivate/`, { method: "POST" })
      toast({ tone: "success", title: "Parameter deactivated", message: `${deactivateRow.code} is now inactive.` })
      setDeactivateRow(null)
      setRefreshKey((current) => current + 1)
    } catch (error) { toast({ tone: "danger", title: "Deactivation failed", message: error instanceof Error ? error.message : "The parameter could not be deactivated." }) }
  }

  const actions = useMemo<RowAction<ParameterRecord>[]>(() => [
    { key: "edit", label: "Edit", permission: "ol_parameters.update", onSelect: openEdit },
    { key: "deactivate", label: "Deactivate", permission: "ol_parameters.deactivate", tone: "danger", isVisible: (row) => row.is_active, onSelect: setDeactivateRow },
  ], [active])

  const stats = [
    { label: "Workspace", value: screen.title, helper: "Backend parameter registry" },
    { label: "Actions", value: canManage ? "Create · Edit" : "Read only", helper: canDeactivate ? "Deactivation available" : "No mutation permission" },
  ]

  const filterDefinitions = screen.filters
  return <MasterDetailPage eyebrow="Ordinary Life Parameters" title={screen.title} description={screen.description} stats={stats} tabs={Object.values(screens).map((item) => ({ id: item.key, label: item.title }))} activeTab={active} onTabChange={(id) => setActive(id as ScreenKey)} actions={canManage ? <button type="button" className="button-primary" onClick={openCreate}><Plus size={16} aria-hidden="true" /> New setup</button> : undefined}>
    <div className="space-y-4">
      {!hasPermission("ol_parameters.view") && <InfoBanner title="Read access required">Your current IAM access metadata does not include the OL parameter view permission.</InfoBanner>}
      <FilterBar definitions={filterDefinitions} value={filters} onChange={(key, next) => setFilters((current) => ({ ...current, [key]: next }))} onApply={() => undefined} onReset={() => setFilters({})} />
      <DataTable<ParameterRecord> key={screen.key} metadata={{ columns: screen.columns, defaultOrdering: "-effective_from", pageSize: 20, totalLabel: "setups" }} fetcher={fetcher} filters={filters} refreshKey={refreshKey} actions={hasPermission("ol_parameters.view") ? (canManage || canDeactivate ? actions : []) : []} permissions={permissionKeys} exportFileName={`${screen.key}-setup.csv`} />
    </div>
    <FormModal open={editor.open} title={`${editor.row ? "Edit" : "Create"} ${screen.title}`} description="Save changes through the OL Parameters API. Effective dates and business validation remain server-authoritative." onClose={closeEditor} onSave={saveEditor} saving={saving} saveLabel={editor.row ? "Save changes" : "Create setup"}>
      <Editor screen={active} value={editor.state} onChange={updateEditor} overlapWarning={active === "commission" ? "Matching scope and overlapping effective periods are rejected by the backend." : undefined} />
    </FormModal>
    <ConfirmModal open={Boolean(deactivateRow)} title="Deactivate setup" description={`Deactivate ${deactivateRow?.code ?? "this setup"}? It will remain available for audit history but will no longer be active.`} confirmLabel="Deactivate" onClose={() => setDeactivateRow(null)} onConfirm={deactivate} />
  </MasterDetailPage>
}

export { screens as olDefaultSetupScreens }

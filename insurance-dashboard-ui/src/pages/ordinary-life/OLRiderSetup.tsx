import { useCallback, useEffect, useMemo, useState } from "react"
import { FileUp, Plus, Shield, Table2 } from "lucide-react"
import { request } from "../../lib/apiClient"
import { useAccess } from "../../lib/access"
import { DataTable, normalizeTableResponse } from "../../components/ui/DataTable"
import { FilterBar } from "../../components/ui/FilterBar"
import { ConfirmModal, FormModal, InfoBanner } from "../../components/ui/Overlays"
import { DateInput, DecimalInput, FormGrid, SelectInput, TextInput, TextareaInput, Toggle } from "../../components/ui"
import { StatusBadge } from "../../components/ui/StatusBadge"
import { useToast } from "../../components/ui/Toast"
import type { FilterValues } from "../../components/ui/FilterBar"
import type { FilterDefinition, FilterOption, RowAction, TableColumn, TableMetadata } from "../../components/ui/types"
import { buildTableQuery, type TableQuery } from "../../lib/apiClient"
import { optionLabel, useRemoteChoices } from "./OLParameterOptions"

const API_PREFIX = "/api/v1/ol-parameters"
type ScreenKey = "riders" | "rate-tables" | "rate-rows"
type Primitive = string | number | boolean | null | string[] | Record<string, unknown>
type EditorRecord = Record<string, Primitive | undefined>

type RiderRecord = EditorRecord & { id: string; code: string; name: string; is_active: boolean; rider_category?: string; benefit_type?: string; calculation_basis?: string; min_age?: number; max_age?: number; min_term?: number; max_term?: number; min_sum_assured?: string | number | null; max_sum_assured?: string | number | null; waiting_period_days?: number; allows_standalone?: boolean; requires_underwriting?: boolean; product?: string | null; plan?: string | null; effective_from?: string | null; effective_to?: string | null }
type RateTableRecord = EditorRecord & { id: string; table_code: string; name: string; rider?: string; product?: string | null; plan?: string | null; rating_basis?: string; version?: string; is_active: boolean; effective_from?: string | null; effective_to?: string | null }
type RateRowRecord = EditorRecord & { id: string; code: string; name: string; table: string; gender: string; smoker_status: string; age_from: number; age_to: number; term_from: number; term_to: number; frequency?: string; sum_assured_band_from?: string | number | null; sum_assured_band_to?: string | number | null; rate: string | number; rate_unit: string; is_active: boolean; effective_from?: string | null; effective_to?: string | null }
type AnyRecord = RiderRecord | RateTableRecord | RateRowRecord

const today = () => new Date().toISOString().slice(0, 10)
const asString = (value: unknown) => value === null || value === undefined ? "" : String(value)
const asNumber = (value: unknown, fallback = 0) => value === null || value === undefined || value === "" ? fallback : Number(value)
const status = (row: AnyRecord) => !row.is_active ? "Inactive" : row.effective_to && row.effective_to < today() ? "Expired" : row.effective_from && row.effective_from > today() ? "Scheduled" : "Active"
const statusTone = (value: string): "success" | "danger" | "info" | "neutral" => value === "Active" ? "success" : value === "Scheduled" ? "info" : value === "Expired" || value === "Inactive" ? "danger" : "neutral"
const formatValue = (value: unknown) => value === null || value === undefined || value === "" ? "—" : String(value)
const range = (from: unknown, to: unknown, suffix = "") => `${formatValue(from)}–${formatValue(to)}${suffix}`

const commonDateColumns = <T extends AnyRecord>(columns: TableColumn<T>[]): TableColumn<T>[] => [...columns, { key: "effective_from", label: "Effective from", field: "effective_from", sortable: true }, { key: "effective_to", label: "Effective to", field: "effective_to" }, { key: "status", label: "Status", render: (_value, row) => <StatusBadge value={status(row)} tone={statusTone(status(row))} /> }]

const riderColumns: TableColumn<RiderRecord>[] = commonDateColumns([
  { key: "code", label: "Code", field: "code", sortable: true },
  { key: "name", label: "Name", field: "name", sortable: true },
  { key: "rider_category", label: "Category", field: "rider_category", render: (value) => <StatusBadge value={formatValue(value)} tone="neutral" /> },
  { key: "benefit_type", label: "Benefit", field: "benefit_type", render: (value) => <StatusBadge value={formatValue(value)} tone="neutral" /> },
  { key: "age", label: "Ages", render: (_value, row) => range(row.min_age, row.max_age) },
  { key: "term", label: "Terms", render: (_value, row) => range(row.min_term, row.max_term, " years") },
  { key: "waiting_period_days", label: "Waiting", field: "waiting_period_days", align: "right" },
  { key: "rules", label: "Rules", render: (_value, row) => [row.allows_standalone ? "Standalone" : "Attached", row.requires_underwriting ? "Underwriting" : "No underwriting"].join(" · ") },
])
const tableColumns: TableColumn<RateTableRecord>[] = commonDateColumns([
  { key: "table_code", label: "Rate table", field: "table_code", sortable: true },
  { key: "name", label: "Name", field: "name", sortable: true },
  { key: "rider", label: "Rider", field: "rider" },
  { key: "rating_basis", label: "Basis", field: "rating_basis" },
  { key: "version", label: "Version", field: "version", render: (value) => <span className="font-bold">v{formatValue(value)}</span> },
])
const rowColumns: TableColumn<RateRowRecord>[] = commonDateColumns([
  { key: "code", label: "Code", field: "code", sortable: true },
  { key: "gender", label: "Gender", field: "gender" },
  { key: "smoker_status", label: "Smoker", field: "smoker_status" },
  { key: "age", label: "Age band", render: (_value, row) => range(row.age_from, row.age_to) },
  { key: "term", label: "Term band", render: (_value, row) => range(row.term_from, row.term_to, " years") },
  { key: "frequency", label: "Frequency", field: "frequency" },
  { key: "rate", label: "Rate", field: "rate", align: "right" },
  { key: "rate_unit", label: "Unit", field: "rate_unit" },
])

const filters: Record<ScreenKey, FilterDefinition[]> = {
  riders: [{ key: "rider_category", label: "Category", type: "select" }, { key: "benefit_type", label: "Benefit", type: "select" }, { key: "is_active", label: "Status", type: "select" }],
  "rate-tables": [{ key: "rider", label: "Rider", type: "text", placeholder: "Rider ID" }, { key: "product", label: "Product", type: "text", placeholder: "Product ID" }, { key: "rating_basis", label: "Rating basis", type: "select" }, { key: "is_active", label: "Status", type: "select" }],
  "rate-rows": [{ key: "table", label: "Rate table", type: "text", placeholder: "Rate table ID" }, { key: "gender", label: "Gender", type: "select" }, { key: "smoker_status", label: "Smoker", type: "select" }, { key: "frequency", label: "Frequency", type: "select" }],
}

function defaults(screen: ScreenKey, parent?: AnyRecord): EditorRecord {
  if (screen === "riders") return { code: "", name: "", description: "", rider_category: "", benefit_type: "", calculation_basis: "", min_age: 18, max_age: 65, min_term: 1, max_term: 30, min_sum_assured: null, max_sum_assured: null, waiting_period_days: 0, allows_standalone: false, requires_underwriting: true, exclusion_rules: {}, product: null, plan: null, effective_from: today(), effective_to: null, is_active: true }
  if (screen === "rate-tables") return { table_code: "", name: "", description: "", rider: parent?.id ?? "", product: null, plan: null, rating_basis: "", version: "1.0", effective_from: today(), effective_to: null, is_active: true }
  return { code: "", name: "", description: "", table: parent?.id ?? "", gender: "", smoker_status: "", age_from: 18, age_to: 65, term_from: 1, term_to: 30, frequency: "", sum_assured_band_from: null, sum_assured_band_to: null, rate: "", rate_unit: "", effective_from: today(), effective_to: null, is_active: true }
}

function validate(screen: ScreenKey, draft: EditorRecord): Record<string, string> {
  const errors: Record<string, string> = {}
  if (!asString(draft.code || draft.table_code).trim()) errors.code = "Code is required."
  if (!asString(draft.name).trim()) errors.name = "Name is required."
  const effectiveFrom = asString(draft.effective_from)
  const effectiveTo = asString(draft.effective_to)
  if (effectiveFrom && effectiveTo && effectiveTo < effectiveFrom) errors.effective_to = "Effective-to cannot be before effective-from."
  if (screen === "riders") {
    if (!asString(draft.rider_category)) errors.rider_category = "Category is required."
    if (!asString(draft.benefit_type)) errors.benefit_type = "Benefit type is required."
    if (!asString(draft.calculation_basis)) errors.calculation_basis = "Calculation basis is required."
    if (asNumber(draft.min_age) < 0 || asNumber(draft.max_age) > 150 || asNumber(draft.max_age) < asNumber(draft.min_age)) errors.max_age = "Age range must be ordered between 0 and 150."
    if (asNumber(draft.min_term) < 1 || asNumber(draft.max_term) < asNumber(draft.min_term)) errors.max_term = "Term range must be ordered and start at one year."
    if (draft.min_sum_assured !== null && draft.min_sum_assured !== "" && asNumber(draft.min_sum_assured) < 0) errors.min_sum_assured = "Minimum sum assured cannot be negative."
    if (draft.max_sum_assured !== null && draft.max_sum_assured !== "" && asNumber(draft.max_sum_assured) < asNumber(draft.min_sum_assured)) errors.max_sum_assured = "Maximum sum assured cannot be below minimum."
  }
  if (screen === "rate-tables" && !asString(draft.rider).trim()) errors.rider = "Rider is required."
  if (screen === "rate-rows") {
    if (!asString(draft.table).trim()) errors.table = "Rate table is required."
    if (!asString(draft.gender)) errors.gender = "Gender is required."
    if (!asString(draft.smoker_status)) errors.smoker_status = "Smoker status is required."
    if (!asString(draft.rate_unit)) errors.rate_unit = "Rate unit is required."
    if (asNumber(draft.age_from) < 0 || asNumber(draft.age_to) > 150 || asNumber(draft.age_to) < asNumber(draft.age_from)) errors.age_to = "Age band must be ordered between 0 and 150."
    if (asNumber(draft.term_from) < 1 || asNumber(draft.term_to) < asNumber(draft.term_from)) errors.term_to = "Term band must be ordered and start at one year."
    if (draft.sum_assured_band_to !== null && draft.sum_assured_band_to !== "" && asNumber(draft.sum_assured_band_to) < asNumber(draft.sum_assured_band_from)) errors.sum_assured_band_to = "Sum-assured band-to cannot be below band-from."
    if (draft.rate === "" || draft.rate === null || asNumber(draft.rate) < 0) errors.rate = "Rate must be a non-negative decimal."
  }
  return errors
}

function editorBody(screen: ScreenKey, draft: EditorRecord) {
  const body = { ...draft }
  if (screen === "riders") body.exclusion_rules = typeof body.exclusion_rules === "object" && body.exclusion_rules !== null && !Array.isArray(body.exclusion_rules) ? body.exclusion_rules : {}
  return body
}

function OptionSelect({ label, value, onChange, options, required, error, placeholder = "Select an option" }: { label: string; value: Primitive | undefined; onChange: (value: string) => void; options: FilterOption[]; required?: boolean; error?: string; placeholder?: string }) {
  return <SelectInput label={label} required={required} error={error} value={asString(value)} onChange={(event) => onChange(event.target.value)}><option value="">{placeholder}</option>{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</SelectInput>
}

function RiderEditor({ screen, draft, setDraft, errors, choices }: { screen: ScreenKey; draft: EditorRecord; setDraft: (key: string, value: Primitive) => void; errors: Record<string, string>; choices: Record<string, FilterOption[]> }) {
  const field = (key: string) => ({ value: draft[key] as string | number | readonly string[] | undefined, onChange: (event: React.ChangeEvent<HTMLInputElement>) => setDraft(key, event.target.type === "number" ? event.target.value : event.target.value) })
  if (screen === "riders") return <div className="space-y-5"><InfoBanner title="Backend-driven rider catalog">Rider category, benefit type, calculation basis, and scope values are loaded from the API metadata and active records.</InfoBanner><FormGrid columns={2}><TextInput label="Code" required error={errors.code} {...field("code")} /><TextInput label="Name" required error={errors.name} {...field("name")} /><OptionSelect label="Rider category" required error={errors.rider_category} value={draft.rider_category} onChange={(value) => setDraft("rider_category", value)} options={choices.rider_category ?? []} /><OptionSelect label="Benefit type" required error={errors.benefit_type} value={draft.benefit_type} onChange={(value) => setDraft("benefit_type", value)} options={choices.benefit_type ?? []} /><OptionSelect label="Calculation basis" required error={errors.calculation_basis} value={draft.calculation_basis} onChange={(value) => setDraft("calculation_basis", value)} options={choices.calculation_basis ?? []} /><DecimalInput label="Waiting period (days)" min={0} {...field("waiting_period_days")} error={errors.waiting_period_days} /><DecimalInput label="Minimum age" min={0} max={150} {...field("min_age")} /><DecimalInput label="Maximum age" min={0} max={150} {...field("max_age")} error={errors.max_age} /><DecimalInput label="Minimum term (years)" min={1} {...field("min_term")} /><DecimalInput label="Maximum term (years)" min={1} {...field("max_term")} error={errors.max_term} /><DecimalInput label="Minimum sum assured" min={0} {...field("min_sum_assured")} error={errors.min_sum_assured} /><DecimalInput label="Maximum sum assured" min={0} {...field("max_sum_assured")} error={errors.max_sum_assured} /></FormGrid><FormGrid columns={2}><Toggle label="Allows standalone attachment" checked={Boolean(draft.allows_standalone)} onChange={(value) => setDraft("allows_standalone", value)} /><Toggle label="Requires underwriting" checked={Boolean(draft.requires_underwriting)} onChange={(value) => setDraft("requires_underwriting", value)} /><DateInput label="Effective from" required error={errors.effective_from} {...field("effective_from")} /><DateInput label="Effective to" error={errors.effective_to} {...field("effective_to")} /></FormGrid><TextareaInput label="Description" value={asString(draft.description)} onChange={(event) => setDraft("description", event.target.value)} /></div>
  if (screen === "rate-tables") return <div className="space-y-5"><FormGrid columns={2}><TextInput label="Table code" required error={errors.code} value={asString(draft.table_code)} onChange={(event) => setDraft("table_code", event.target.value)} /><TextInput label="Name" required error={errors.name} {...field("name")} /><TextInput label="Rider ID" required error={errors.rider} {...field("rider")} /><TextInput label="Product ID" {...field("product")} /><TextInput label="Plan ID" {...field("plan")} /><OptionSelect label="Rating basis" required value={draft.rating_basis} onChange={(value) => setDraft("rating_basis", value)} options={choices.rating_basis ?? []} /><TextInput label="Version" required {...field("version")} /><DateInput label="Effective from" required {...field("effective_from")} /><DateInput label="Effective to" {...field("effective_to")} /></FormGrid><TextareaInput label="Description" value={asString(draft.description)} onChange={(event) => setDraft("description", event.target.value)} /></div>
  return <div className="space-y-5"><InfoBanner title="Rate dimensions">Rows are validated against age, term, sum-assured, frequency, gender, smoker status, and rate-unit dimensions before persistence.</InfoBanner><FormGrid columns={2}><TextInput label="Code" required error={errors.code} {...field("code")} /><TextInput label="Name" required error={errors.name} {...field("name")} /><TextInput label="Rate table ID" required error={errors.table} {...field("table")} /><OptionSelect label="Gender" required error={errors.gender} value={draft.gender} onChange={(value) => setDraft("gender", value)} options={choices.gender ?? []} /><OptionSelect label="Smoker status" required error={errors.smoker_status} value={draft.smoker_status} onChange={(value) => setDraft("smoker_status", value)} options={choices.smoker_status ?? []} /><OptionSelect label="Frequency" value={draft.frequency} onChange={(value) => setDraft("frequency", value)} options={choices.frequency ?? []} /><DecimalInput label="Age from" min={0} {...field("age_from")} /><DecimalInput label="Age to" min={0} error={errors.age_to} {...field("age_to")} /><DecimalInput label="Term from" min={1} {...field("term_from")} /><DecimalInput label="Term to" min={1} error={errors.term_to} {...field("term_to")} /><DecimalInput label="Sum assured from" min={0} {...field("sum_assured_band_from")} /><DecimalInput label="Sum assured to" min={0} error={errors.sum_assured_band_to} {...field("sum_assured_band_to")} /><DecimalInput label="Rate" required min={0} error={errors.rate} {...field("rate")} /><OptionSelect label="Rate unit" required error={errors.rate_unit} value={draft.rate_unit} onChange={(value) => setDraft("rate_unit", value)} options={choices.rate_unit ?? []} /></FormGrid><FormGrid columns={2}><DateInput label="Effective from" required {...field("effective_from")} /><DateInput label="Effective to" {...field("effective_to")} /></FormGrid><TextareaInput label="Description" value={asString(draft.description)} onChange={(event) => setDraft("description", event.target.value)} /></div>
}

export default function OLRiderSetup() {
  const { access, canAccess, isSuperAdmin } = useAccess()
  const { toast } = useToast()
  const [screen, setScreen] = useState<ScreenKey>("riders")
  const [filtersState, setFiltersState] = useState<FilterValues>({})
  const [refreshKey, setRefreshKey] = useState(0)
  const [editor, setEditor] = useState<{ screen: ScreenKey; record: EditorRecord; parent?: AnyRecord } | null>(null)
  const [confirm, setConfirm] = useState<AnyRecord | null>(null)
  const [saving, setSaving] = useState(false)
  const [validation, setValidation] = useState<Record<string, string>>({})
  const [rows, setRows] = useState<AnyRecord[]>([])
  const endpoint = screen === "riders" ? `${API_PREFIX}/rider-setups/` : screen === "rate-tables" ? `${API_PREFIX}/rider-rate-tables/` : `${API_PREFIX}/rider-rate-rows/`
  const metadataEndpoint = endpoint
  const choiceFields = screen === "riders" ? ["rider_category", "benefit_type", "calculation_basis"] : screen === "rate-tables" ? ["rating_basis"] : ["gender", "smoker_status", "frequency", "rate_unit"]
  const { choices, loading: choicesLoading } = useRemoteChoices(metadataEndpoint, choiceFields, rows)
  const permissions = isSuperAdmin ? ["ol_parameters.view", "ol_parameters.create", "ol_parameters.update", "ol_parameters.deactivate"] : access.permissions.map((permission) => `${permission.module}.${permission.action}`)
  const writable = isSuperAdmin || (canAccess("ol_parameters") && (permissions.length === 0 || permissions.some((permission) => permission.includes("write") || permission.includes("create") || permission.includes("update"))))
  const deactivatable = writable

  const fetcher = useCallback(async (query: TableQuery) => {
    const result = await request<unknown>(`${endpoint}${buildTableQuery(query)}`)
    const normalized = normalizeTableResponse<AnyRecord>(result)
    setRows(normalized.results)
    return normalized
  }, [endpoint])

  const openCreate = () => { setValidation({}); setEditor({ screen, record: defaults(screen), parent: undefined }) }
  const openEdit = (record: AnyRecord) => { setValidation({}); setEditor({ screen, record: { ...record }, parent: undefined }) }
  const save = async () => {
    if (!editor) return
    const errors = validate(editor.screen, editor.record)
    setValidation(errors)
    if (Object.keys(errors).length) { toast({ tone: "danger", title: "Review the highlighted fields", message: "The record was not saved." }); return }
    setSaving(true)
    try {
      const id = editor.record.id
      await request(`${editor.screen === "riders" ? `${API_PREFIX}/rider-setups/` : editor.screen === "rate-tables" ? `${API_PREFIX}/rider-rate-tables/` : `${API_PREFIX}/rider-rate-rows/`}${id ? `${id}/` : ""}`, { method: id ? "PATCH" : "POST", body: JSON.stringify(editorBody(editor.screen, editor.record)) })
      toast({ tone: "success", title: id ? "Setup updated" : "Setup created" })
      setEditor(null); setRefreshKey((value) => value + 1)
    } catch (error) { toast({ tone: "danger", title: "Unable to save setup", message: error instanceof Error ? error.message : "The backend rejected this setup." }) } finally { setSaving(false) }
  }
  const deactivate = async () => {
    if (!confirm) return
    try { await request(`${endpoint}${confirm.id}/deactivate/`, { method: "POST" }); toast({ tone: "success", title: "Record deactivated" }); setConfirm(null); setRefreshKey((value) => value + 1) }
    catch (error) { toast({ tone: "danger", title: "Unable to deactivate", message: error instanceof Error ? error.message : "The backend rejected the action." }) }
  }
  const importRows = async (file: File) => {
    const text = await file.text()
    const [headerLine, ...lines] = text.split(/\r?\n/).filter(Boolean)
    const headers = headerLine.split(",").map((header) => header.trim().replace(/^"|"$/g, ""))
    const accepted: EditorRecord[] = []
    const failures: string[] = []
    lines.forEach((line, index) => {
      const values = line.split(",").map((value) => value.trim().replace(/^"|"$/g, ""))
      const record = Object.fromEntries(headers.map((header, headerIndex) => [header, values[headerIndex] ?? ""])) as EditorRecord
      const errors = validate("rate-rows", record)
      if (Object.keys(errors).length) failures.push(`Row ${index + 2}: ${Object.values(errors).join(" ")}`)
      else accepted.push(record)
    })
    if (failures.length) toast({ tone: "danger", title: "CSV import needs attention", message: failures.slice(0, 3).join(" ") })
    if (!accepted.length) return
    try { await Promise.all(accepted.map((record) => request(`${API_PREFIX}/rider-rate-rows/`, { method: "POST", body: JSON.stringify(record) }))); toast({ tone: "success", title: `${accepted.length} rate row${accepted.length === 1 ? "" : "s"} imported` }); setRefreshKey((value) => value + 1) }
    catch (error) { toast({ tone: "danger", title: "Some rate rows could not be imported", message: error instanceof Error ? error.message : "The backend rejected the import." }) }
  }

  const actions: RowAction<AnyRecord>[] = [{ key: "edit", label: "Edit", permission: "ol_parameters.update", onSelect: openEdit }, { key: "deactivate", label: "Deactivate", permission: "ol_parameters.deactivate", tone: "danger", isVisible: (row) => row.is_active, onSelect: (row) => setConfirm(row) }]
  const rateTableActions: RowAction<AnyRecord>[] = [{ key: "edit", label: "Edit", permission: "ol_parameters.update", onSelect: openEdit }, { key: "rows", label: "Open rate rows", permission: "ol_parameters.read", onSelect: (row) => { setFiltersState({ table: String(row.id) }); setScreen("rate-rows") } }, { key: "deactivate", label: "Deactivate", permission: "ol_parameters.deactivate", tone: "danger", isVisible: (row) => row.is_active, onSelect: (row) => setConfirm(row) }]
  const visibleActions = screen === "rate-tables" ? rateTableActions : actions
  const definitions = filters[screen].map((definition) => ({ ...definition, options: definition.key === "is_active" ? [{ label: "Active", value: "true" }, { label: "Inactive", value: "false" }] : choices[definition.key] ?? [] }))
  const metadata: TableMetadata<AnyRecord> = { totalLabel: screen === "riders" ? "OL Riders" : screen === "rate-tables" ? "Rider rate tables" : "Rider rate rows", defaultOrdering: screen === "riders" ? "code" : screen === "rate-tables" ? "table_code" : "code", columns: (screen === "riders" ? riderColumns : screen === "rate-tables" ? tableColumns : rowColumns) as TableColumn<AnyRecord>[] }
  const title = screen === "riders" ? "OL Riders" : screen === "rate-tables" ? "OL Rider Rate Tables" : "OL Rider Rate Rows"
  const description = screen === "riders" ? "Configure reusable rider definitions and underwriting applicability." : screen === "rate-tables" ? "Versioned rider rate tables scoped by rider, product, plan, and effective period." : "Edit multi-dimensional rider premium rows with CSV import and export."

  return <div className="space-y-5 p-4 md:p-6"><header className="flex flex-wrap items-start justify-between gap-4"><div><div className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.14em] text-[var(--muted-foreground)]"><Shield size={15} aria-hidden="true" /> Ordinary Life Parameters</div><h1 className="text-2xl font-black tracking-tight">{title}</h1><p className="mt-1 max-w-3xl text-sm text-[var(--muted-foreground)]">{description}</p></div><button type="button" className="button-primary" onClick={openCreate} disabled={!writable}><Plus size={16} aria-hidden="true" />New setup</button></header><div className="flex flex-wrap gap-2" role="tablist" aria-label="Rider setup screens"><button type="button" role="tab" aria-selected={screen === "riders"} className={screen === "riders" ? "button-primary" : "button-secondary"} onClick={() => { setScreen("riders"); setFiltersState({}) }}><Shield size={15} aria-hidden="true" />Riders</button><button type="button" role="tab" aria-selected={screen === "rate-tables"} className={screen === "rate-tables" ? "button-primary" : "button-secondary"} onClick={() => { setScreen("rate-tables"); setFiltersState({}) }}><Table2 size={15} aria-hidden="true" />Rate tables</button><button type="button" role="tab" aria-selected={screen === "rate-rows"} className={screen === "rate-rows" ? "button-primary" : "button-secondary"} onClick={() => { setScreen("rate-rows"); setFiltersState({}) }}><Table2 size={15} aria-hidden="true" />Rate rows</button></div><FilterBar definitions={definitions} value={filtersState} onChange={(key, value) => setFiltersState((current) => ({ ...current, [key]: value }))} onReset={() => setFiltersState({})} /><DataTable metadata={metadata} fetcher={fetcher} filters={filtersState} refreshKey={refreshKey} actions={writable ? visibleActions : []} permissions={permissions} onImportCsv={screen === "rate-rows" && writable ? importRows : undefined} exportFileName={`ol-${screen}.csv`} caption={metadata.totalLabel} />{choicesLoading && <p className="text-xs text-[var(--muted-foreground)]">Loading backend option metadata…</p>}<FormModal open={Boolean(editor)} title={editor ? `${editor.record.id ? "Edit" : "Create"} ${editor.screen === "riders" ? "rider" : editor.screen === "rate-tables" ? "rider rate table" : "rider rate row"}` : "Editor"} description="All select options are sourced from backend metadata or active records." onClose={() => setEditor(null)} onSave={() => void save()} saving={saving} saveLabel="Save setup">{editor && <RiderEditor screen={editor.screen} draft={editor.record} setDraft={(key, value) => setEditor((current) => current ? { ...current, record: { ...current.record, [key]: value } } : current)} errors={validation} choices={choices} />}</FormModal><ConfirmModal open={Boolean(confirm)} title="Deactivate setup" description="This record will no longer be selectable for new configurations. Existing transactions remain linked to the stored record." confirmLabel="Deactivate" onClose={() => setConfirm(null)} onConfirm={() => void deactivate()} /></div>
}

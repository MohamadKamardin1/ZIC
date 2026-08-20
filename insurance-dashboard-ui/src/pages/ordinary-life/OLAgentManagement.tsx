import { useCallback, useMemo, useState } from "react"
import { BriefcaseBusiness, Plus } from "lucide-react"
import { buildTableQuery, request, type TableQuery } from "../../lib/apiClient"
import { useAccess } from "../../lib/access"
import { DataTable, normalizeTableResponse } from "../../components/ui/DataTable"
import { FilterBar } from "../../components/ui/FilterBar"
import { ConfirmModal, FormModal, InfoBanner } from "../../components/ui/Overlays"
import { DateInput, DecimalInput, FormGrid, SelectInput, TextInput, TextareaInput } from "../../components/ui"
import { StatusBadge } from "../../components/ui/StatusBadge"
import { useToast } from "../../components/ui/Toast"
import type { FilterValues } from "../../components/ui/FilterBar"
import type { FilterOption, RowAction, TableColumn, TableMetadata } from "../../components/ui/types"
import { optionLabel, useRemoteChoices } from "./OLParameterOptions"

const ENDPOINT = "/api/v1/ol-parameters/agent-commission-setups/"
type Primitive = string | number | boolean | null | string[] | Record<string, unknown>
type CommissionRecord = Record<string, Primitive | undefined> & { id: string; code: string; name?: string; intermediary_type?: string; distribution_channel?: string; commission_type?: string; rate_type?: string; rate_value?: string | number; priority?: number; product?: string | null; plan?: string | null; effective_from?: string | null; effective_to?: string | null; is_active: boolean }
const today = () => new Date().toISOString().slice(0, 10)
const text = (value: unknown) => value === null || value === undefined ? "" : String(value)
const num = (value: unknown) => value === null || value === undefined || value === "" ? 0 : Number(value)
const state = (row: CommissionRecord) => !row.is_active ? "Inactive" : row.effective_to && row.effective_to < today() ? "Expired" : row.effective_from && row.effective_from > today() ? "Scheduled" : "Active"
const stateTone = (value: string): "success" | "danger" | "info" | "neutral" => value === "Active" ? "success" : value === "Scheduled" ? "info" : value === "Expired" || value === "Inactive" ? "danger" : "neutral"
const format = (value: unknown) => value === null || value === undefined || value === "" ? "—" : String(value)

const columns: TableColumn<CommissionRecord>[] = [
  { key: "code", label: "Code", field: "code", sortable: true },
  { key: "intermediary_type", label: "Agent / partner", field: "intermediary_type" },
  { key: "product", label: "Product", field: "product" },
  { key: "plan", label: "Plan", field: "plan" },
  { key: "distribution_channel", label: "Channel", field: "distribution_channel" },
  { key: "commission_type", label: "Commission type", field: "commission_type" },
  { key: "rate", label: "Rate", render: (_value, row) => `${format(row.rate_value)} ${optionLabel(row.rate_type, [])}` },
  { key: "priority", label: "Priority", field: "priority", align: "right", sortable: true },
  { key: "effective_from", label: "Effective from", field: "effective_from", sortable: true },
  { key: "effective_to", label: "Effective to", field: "effective_to" },
  { key: "status", label: "Status", render: (_value, row) => <StatusBadge value={state(row)} tone={stateTone(state(row))} /> },
]

const filterDefinitions: Array<{ key: string; label: string; type: "text" | "select"; placeholder?: string }> = [
  { key: "product", label: "Product", type: "select" },
  { key: "plan", label: "Plan", type: "select" },
  { key: "intermediary_type", label: "Agent / partner", type: "select" },
  { key: "commission_type", label: "Commission type", type: "select" },
  { key: "distribution_channel", label: "Channel", type: "select" },
  { key: "is_active", label: "Status", type: "select" },
]

function defaults(): CommissionRecord {
  return { id: "", code: "", name: "", intermediary_type: "", distribution_channel: "", commission_type: "", premium_year_from: 1, premium_year_to: 1, policy_year_from: 1, policy_year_to: 1, rate_type: "", rate_value: "", minimum_commission: 0, maximum_commission: 0, priority: 100, product: null, plan: null, rider: null, currency: "", branch: null, effective_from: today(), effective_to: null, is_active: true, reason: "" }
}

function validate(draft: CommissionRecord) {
  const errors: Record<string, string> = {}
  if (!text(draft.code).trim()) errors.code = "Code is required."
  if (!text(draft.name).trim()) errors.name = "Name is required."
  if (!text(draft.intermediary_type)) errors.intermediary_type = "Intermediary type is required."
  if (!text(draft.distribution_channel)) errors.distribution_channel = "Distribution channel is required."
  if (!text(draft.commission_type)) errors.commission_type = "Commission type is required."
  if (!text(draft.rate_type)) errors.rate_type = "Rate type is required."
  if (draft.rate_value === "" || draft.rate_value === null || num(draft.rate_value) < 0) errors.rate_value = "Rate must be a non-negative decimal."
  if (num(draft.priority) < 0) errors.priority = "Priority cannot be negative."
  if (num(draft.premium_year_to) < num(draft.premium_year_from)) errors.premium_year_to = "Premium year range is not ordered."
  if (num(draft.policy_year_to) < num(draft.policy_year_from)) errors.policy_year_to = "Policy year range is not ordered."
  if (text(draft.effective_to) && text(draft.effective_to) < text(draft.effective_from)) errors.effective_to = "Effective-to cannot be before effective-from."
  return errors
}

function Choice({ label, value, onChange, options, required, error }: { label: string; value: unknown; onChange: (value: string) => void; options: FilterOption[]; required?: boolean; error?: string }) {
  return <SelectInput label={label} required={required} error={error} value={text(value)} onChange={(event) => onChange(event.target.value)}><option value="">Select an option</option>{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</SelectInput>
}

export default function OLAgentManagement() {
  const { access, canAccess, isSuperAdmin } = useAccess()
  const { toast } = useToast()
  const [filters, setFilters] = useState<FilterValues>({})
  const [editor, setEditor] = useState<CommissionRecord | null>(null)
  const [confirm, setConfirm] = useState<CommissionRecord | null>(null)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [overlapWarning, setOverlapWarning] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)
  const [rows, setRows] = useState<CommissionRecord[]>([])
  const { choices } = useRemoteChoices(ENDPOINT, ["intermediary_type", "distribution_channel", "commission_type", "rate_type", "product", "plan", "rider"], rows)
  const permissions = isSuperAdmin ? ["ol_parameters.view", "ol_parameters.create", "ol_parameters.update", "ol_parameters.deactivate"] : access.permissions.map((permission) => `${permission.module}.${permission.action}`)
  const writable = isSuperAdmin || (canAccess("ol_parameters") && (permissions.length === 0 || permissions.some((permission) => /\.create$|\.update$|\.write$/.test(permission))))
  const fetcher = useCallback(async (query: TableQuery) => { const payload = await request<unknown>(`${ENDPOINT}${buildTableQuery(query)}`); const result = normalizeTableResponse<CommissionRecord>(payload); setRows(result.results); return result }, [])
  const definitions = useMemo(() => filterDefinitions.map((definition) => ({ ...definition, options: definition.key === "is_active" ? [{ label: "Active", value: "true" }, { label: "Inactive", value: "false" }] : choices[definition.key] ?? [] })), [choices])
  const update = (key: string, value: Primitive) => setEditor((current) => current ? { ...current, [key]: value } : current)
  const save = async () => {
    if (!editor) return
    const nextErrors = validate(editor)
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length) { toast({ tone: "danger", title: "Review the highlighted fields" }); return }
    setSaving(true); setOverlapWarning(null)
    try { await request(`${ENDPOINT}${editor.id ? `${editor.id}/` : ""}`, { method: editor.id ? "PATCH" : "POST", body: JSON.stringify({ ...editor, id: undefined }) }); toast({ tone: "success", title: editor.id ? "Commission setup updated" : "Commission setup created" }); setEditor(null); setRefreshKey((value) => value + 1) }
    catch (error) { const message = error instanceof Error ? error.message : "The backend rejected the commission setup."; if (/overlap|conflict|duplicate/i.test(message)) setOverlapWarning(message); toast({ tone: "danger", title: "Commission setup was not saved", message }) } finally { setSaving(false) }
  }
  const deactivate = async () => { if (!confirm) return; try { await request(`${ENDPOINT}${confirm.id}/deactivate/`, { method: "POST" }); toast({ tone: "success", title: "Commission setup deactivated" }); setConfirm(null); setRefreshKey((value) => value + 1) } catch (error) { toast({ tone: "danger", title: "Unable to deactivate", message: error instanceof Error ? error.message : "The backend rejected the action." }) } }
  const actions: RowAction<CommissionRecord>[] = [{ key: "edit", label: "Edit", permission: "ol_parameters.update", onSelect: (row) => { setErrors({}); setOverlapWarning(null); setEditor({ ...row }) } }, { key: "deactivate", label: "Deactivate", permission: "ol_parameters.deactivate", tone: "danger", isVisible: (row) => row.is_active, onSelect: setConfirm }]
  const field = (key: string, numeric = false) => ({ value: editor ? editor[key] as string | number | readonly string[] | undefined : "", onChange: (event: React.ChangeEvent<HTMLInputElement>) => update(key, numeric ? event.target.value : event.target.value) })
  return <div className="space-y-5 p-4 md:p-6"><header className="flex flex-wrap items-start justify-between gap-4"><div><div className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.14em] text-[var(--muted-foreground)]"><BriefcaseBusiness size={15} aria-hidden="true" /> Ordinary Life Parameters</div><h1 className="text-2xl font-black tracking-tight">Agent Commission Setup</h1><p className="mt-1 max-w-3xl text-sm text-[var(--muted-foreground)]">Configure effective-dated intermediary commission rules by product, plan, channel, and commission type.</p></div><button type="button" className="button-primary" disabled={!writable} onClick={() => { setErrors({}); setOverlapWarning(null); setEditor(defaults()) }}><Plus size={16} aria-hidden="true" />New commission setup</button></header><FilterBar definitions={definitions} value={filters} onChange={(key, value) => setFilters((current) => ({ ...current, [key]: value }))} onReset={() => setFilters({})} /><DataTable metadata={{ totalLabel: "Agent commission setups", defaultOrdering: "priority", columns } satisfies TableMetadata<CommissionRecord>} fetcher={fetcher} filters={filters} refreshKey={refreshKey} actions={writable ? actions : []} permissions={permissions} exportFileName="ol-agent-commission-setups.csv" /><FormModal open={Boolean(editor)} title={editor?.id ? "Edit agent commission setup" : "Create agent commission setup"} description="Commission type and rate choices are loaded from backend metadata." onClose={() => setEditor(null)} onSave={() => void save()} saving={saving} saveLabel="Save commission setup">{editor && <div className="space-y-5"><InfoBanner title="Overlap protection">Active rules with the same scope and overlapping effective period are rejected by the backend. Resolve any overlap before saving.</InfoBanner>{overlapWarning && <InfoBanner title="Overlap warning" className="border-amber-300 bg-amber-50 text-amber-950">{overlapWarning}</InfoBanner>}<FormGrid columns={2}><TextInput label="Code" required error={errors.code} {...field("code")} /><TextInput label="Name" required error={errors.name} {...field("name")} /><Choice label="Intermediary type" required error={errors.intermediary_type} value={editor.intermediary_type} onChange={(value) => update("intermediary_type", value)} options={choices.intermediary_type ?? []} /><Choice label="Distribution channel" required error={errors.distribution_channel} value={editor.distribution_channel} onChange={(value) => update("distribution_channel", value)} options={choices.distribution_channel ?? []} /><Choice label="Commission type" required error={errors.commission_type} value={editor.commission_type} onChange={(value) => update("commission_type", value)} options={choices.commission_type ?? []} /><Choice label="Rate type" required error={errors.rate_type} value={editor.rate_type} onChange={(value) => update("rate_type", value)} options={choices.rate_type ?? []} /><DecimalInput label="Rate value" required min={0} error={errors.rate_value} {...field("rate_value", true)} /><DecimalInput label="Priority" min={0} error={errors.priority} {...field("priority", true)} /><Choice label="Product" value={editor.product} onChange={(value) => update("product", value)} options={choices.product ?? []} /><Choice label="Plan" value={editor.plan} onChange={(value) => update("plan", value)} options={choices.plan ?? []} /><Choice label="Rider" value={editor.rider} onChange={(value) => update("rider", value)} options={choices.rider ?? []} /><TextInput label="Currency" {...field("currency")} /><DecimalInput label="Premium year from" min={1} {...field("premium_year_from", true)} /><DecimalInput label="Premium year to" min={1} error={errors.premium_year_to} {...field("premium_year_to", true)} /><DecimalInput label="Policy year from" min={1} {...field("policy_year_from", true)} /><DecimalInput label="Policy year to" min={1} error={errors.policy_year_to} {...field("policy_year_to", true)} /><DecimalInput label="Minimum commission" min={0} {...field("minimum_commission", true)} /><DecimalInput label="Maximum commission" min={0} {...field("maximum_commission", true)} /><DateInput label="Effective from" required {...field("effective_from")} /><DateInput label="Effective to" error={errors.effective_to} {...field("effective_to")} /></FormGrid><TextareaInput label="Reason / notes" value={text(editor.reason)} onChange={(event) => update("reason", event.target.value)} /></div>}</FormModal><ConfirmModal open={Boolean(confirm)} title="Deactivate commission setup" description="This rule will no longer be selected for new commission calculations." confirmLabel="Deactivate" onClose={() => setConfirm(null)} onConfirm={() => void deactivate()} /></div>
}

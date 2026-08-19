import { useCallback, useMemo, useState } from "react"
import { Banknote, Plus } from "lucide-react"
import { buildTableQuery, request, type TableQuery } from "../../lib/apiClient"
import { useAccess } from "../../lib/access"
import { DataTable, normalizeTableResponse } from "../../components/ui/DataTable"
import { FilterBar } from "../../components/ui/FilterBar"
import { ConfirmModal, FormModal, InfoBanner } from "../../components/ui/Overlays"
import { DateInput, DecimalInput, FormGrid, SelectInput, TextInput, TextareaInput, Toggle } from "../../components/ui"
import { StatusBadge } from "../../components/ui/StatusBadge"
import { useToast } from "../../components/ui/Toast"
import type { FilterValues } from "../../components/ui/FilterBar"
import type { FilterOption, RowAction, TableColumn, TableMetadata } from "../../components/ui/types"
import { useRemoteChoices } from "./OLParameterOptions"

const API_PREFIX = "/api/v1/ol-parameters"
type ScreenKey = "system" | "interest"
type Primitive = string | number | boolean | null | string[] | Record<string, unknown>
type LoanRecord = Record<string, Primitive | undefined> & { id: string; code: string; name?: string; is_active: boolean; product?: string | null; plan?: string | null; effective_from?: string | null; effective_to?: string | null; loan_basis?: string; max_loan_percentage_of_cash_value?: string | number; min_loan_amount?: string | number; max_loan_amount?: string | number; allow_policy_loans?: boolean; require_approval?: boolean; interest_rate?: string | number; compounding_frequency?: string; interest_calculation_basis?: string; grace_period_days?: number; penalty_interest_rate?: string | number | null; capitalize_interest?: boolean }
const today = () => new Date().toISOString().slice(0, 10)
const text = (value: unknown) => value === null || value === undefined ? "" : String(value)
const num = (value: unknown) => value === null || value === undefined || value === "" ? 0 : Number(value)
const state = (row: LoanRecord) => !row.is_active ? "Inactive" : row.effective_to && row.effective_to < today() ? "Expired" : row.effective_from && row.effective_from > today() ? "Scheduled" : "Active"
const tone = (value: string): "success" | "danger" | "info" | "neutral" => value === "Active" ? "success" : value === "Scheduled" ? "info" : value === "Expired" || value === "Inactive" ? "danger" : "neutral"
const format = (value: unknown) => value === null || value === undefined || value === "" ? "—" : String(value)
const endpointFor = (screen: ScreenKey) => screen === "system" ? `${API_PREFIX}/loan-system-setups/` : `${API_PREFIX}/loan-interest-controls/`

const systemColumns: TableColumn<LoanRecord>[] = [
  { key: "code", label: "Code", field: "code", sortable: true },
  { key: "name", label: "Name", field: "name", sortable: true },
  { key: "loan_basis", label: "Loan basis", field: "loan_basis" },
  { key: "max_loan_percentage_of_cash_value", label: "Max %", field: "max_loan_percentage_of_cash_value", align: "right" },
  { key: "amounts", label: "Min / max amount", render: (_value, row) => `${format(row.min_loan_amount)} / ${format(row.max_loan_amount)}` },
  { key: "allow_policy_loans", label: "Loans", render: (_value, row) => row.allow_policy_loans ? "Allowed" : "Blocked" },
  { key: "require_approval", label: "Approval", render: (_value, row) => row.require_approval ? "Required" : "Not required" },
  { key: "effective_from", label: "Effective from", field: "effective_from", sortable: true },
  { key: "effective_to", label: "Effective to", field: "effective_to" },
  { key: "status", label: "Status", render: (_value, row) => <StatusBadge value={state(row)} tone={tone(state(row))} /> },
]
const interestColumns: TableColumn<LoanRecord>[] = [
  { key: "code", label: "Code", field: "code", sortable: true },
  { key: "name", label: "Name", field: "name", sortable: true },
  { key: "interest_rate", label: "Interest rate", field: "interest_rate", align: "right" },
  { key: "compounding_frequency", label: "Compounding", field: "compounding_frequency" },
  { key: "interest_calculation_basis", label: "Calculation basis", field: "interest_calculation_basis" },
  { key: "grace_period_days", label: "Grace days", field: "grace_period_days", align: "right" },
  { key: "penalty_interest_rate", label: "Penalty rate", field: "penalty_interest_rate", align: "right" },
  { key: "capitalize_interest", label: "Capitalize", render: (_value, row) => row.capitalize_interest ? "Yes" : "No" },
  { key: "effective_from", label: "Effective from", field: "effective_from", sortable: true },
  { key: "effective_to", label: "Effective to", field: "effective_to" },
  { key: "status", label: "Status", render: (_value, row) => <StatusBadge value={state(row)} tone={tone(state(row))} /> },
]

const filters: Record<ScreenKey, Array<{ key: string; label: string; type: "text" | "select"; placeholder?: string }>> = {
  system: [{ key: "product", label: "Product", type: "text", placeholder: "Product ID" }, { key: "plan", label: "Plan", type: "text", placeholder: "Plan ID" }, { key: "loan_basis", label: "Loan basis", type: "select" }, { key: "is_active", label: "Status", type: "select" }],
  interest: [{ key: "product", label: "Product", type: "text", placeholder: "Product ID" }, { key: "plan", label: "Plan", type: "text", placeholder: "Plan ID" }, { key: "compounding_frequency", label: "Compounding", type: "select" }, { key: "interest_calculation_basis", label: "Calculation basis", type: "select" }, { key: "is_active", label: "Status", type: "select" }],
}

function defaults(screen: ScreenKey): LoanRecord {
  if (screen === "system") return { id: "", code: "", name: "", description: "", product: null, plan: null, allow_policy_loans: true, loan_basis: "", max_loan_percentage_of_cash_value: "", min_loan_amount: "", max_loan_amount: "", loan_currency: "", repayment_options: [], auto_deduct_from_benefits: true, effect_on_claim: "", effect_on_surrender: "", effect_on_maturity: "", require_approval: false, effective_from: today(), effective_to: null, is_active: true }
  return { id: "", code: "", name: "", description: "", product: null, plan: null, interest_rate: "", compounding_frequency: "", interest_calculation_basis: "", grace_period_days: 0, penalty_interest_rate: null, interest_suspension_rule: "", capitalize_interest: true, effective_from: today(), effective_to: null, is_active: true }
}

function validate(screen: ScreenKey, draft: LoanRecord) {
  const errors: Record<string, string> = {}
  if (!text(draft.code).trim()) errors.code = "Code is required."
  if (!text(draft.name).trim()) errors.name = "Name is required."
  if (!text(draft.effective_from)) errors.effective_from = "Effective-from is required."
  if (text(draft.effective_to) && text(draft.effective_to) < text(draft.effective_from)) errors.effective_to = "Effective-to cannot be before effective-from."
  if (screen === "system") {
    if (!text(draft.loan_basis)) errors.loan_basis = "Loan basis is required."
    if (num(draft.max_loan_percentage_of_cash_value) < 0 || num(draft.max_loan_percentage_of_cash_value) > 100) errors.max_loan_percentage_of_cash_value = "Maximum loan percentage must be between 0 and 100."
    if (num(draft.min_loan_amount) <= 0) errors.min_loan_amount = "Minimum loan amount must be positive."
    if (num(draft.max_loan_amount) <= 0 || num(draft.max_loan_amount) < num(draft.min_loan_amount)) errors.max_loan_amount = "Maximum loan amount must be positive and at least the minimum."
    if (!text(draft.effect_on_claim)) errors.effect_on_claim = "Claim effect is required."
    if (!text(draft.effect_on_surrender)) errors.effect_on_surrender = "Surrender effect is required."
    if (!text(draft.effect_on_maturity)) errors.effect_on_maturity = "Maturity effect is required."
  } else {
    if (num(draft.interest_rate) < 0 || num(draft.interest_rate) > 100) errors.interest_rate = "Interest rate must be between 0 and 100."
    if (!text(draft.compounding_frequency)) errors.compounding_frequency = "Compounding frequency is required."
    if (!text(draft.interest_calculation_basis)) errors.interest_calculation_basis = "Interest calculation basis is required."
    if (num(draft.grace_period_days) < 0) errors.grace_period_days = "Grace period cannot be negative."
    if (draft.penalty_interest_rate !== null && draft.penalty_interest_rate !== "" && (num(draft.penalty_interest_rate) < 0 || num(draft.penalty_interest_rate) > 100)) errors.penalty_interest_rate = "Penalty interest rate must be between 0 and 100."
  }
  return errors
}

function Choice({ label, value, onChange, options, required, error }: { label: string; value: unknown; onChange: (value: string) => void; options: FilterOption[]; required?: boolean; error?: string }) {
  return <SelectInput label={label} required={required} error={error} value={text(value)} onChange={(event) => onChange(event.target.value)}><option value="">Select an option</option>{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</SelectInput>
}

export default function OLLoanSetup() {
  const { access, canAccess, isSuperAdmin } = useAccess()
  const { toast } = useToast()
  const [screen, setScreen] = useState<ScreenKey>("system")
  const [filtersState, setFiltersState] = useState<FilterValues>({})
  const [editor, setEditor] = useState<LoanRecord | null>(null)
  const [confirm, setConfirm] = useState<LoanRecord | null>(null)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)
  const [rows, setRows] = useState<LoanRecord[]>([])
  const endpoint = endpointFor(screen)
  const choiceFields = screen === "system" ? ["loan_basis", "effect_on_claim", "effect_on_surrender", "effect_on_maturity"] : ["compounding_frequency", "interest_calculation_basis"]
  const { choices } = useRemoteChoices(endpoint, choiceFields, rows)
  const permissions = isSuperAdmin ? ["ol_parameters.view", "ol_parameters.create", "ol_parameters.update", "ol_parameters.deactivate"] : access.permissions.map((permission) => `${permission.module}.${permission.action}`)
  const writable = isSuperAdmin || (canAccess("ol_parameters") && (permissions.length === 0 || permissions.some((permission) => /\.create$|\.update$|\.write$/.test(permission))))
  const fetcher = useCallback(async (query: TableQuery) => { const payload = await request<unknown>(`${endpoint}${buildTableQuery(query)}`); const result = normalizeTableResponse<LoanRecord>(payload); setRows(result.results); return result }, [endpoint])
  const definitions = useMemo(() => filters[screen].map((definition) => ({ ...definition, options: definition.key === "is_active" ? [{ label: "Active", value: "true" }, { label: "Inactive", value: "false" }] : choices[definition.key] ?? [] })), [choices, screen])
  const update = (key: string, value: Primitive) => setEditor((current) => current ? { ...current, [key]: value } : current)
  const save = async () => { if (!editor) return; const nextErrors = validate(screen, editor); setErrors(nextErrors); if (Object.keys(nextErrors).length) { toast({ tone: "danger", title: "Review the highlighted fields" }); return }; setSaving(true); try { const body = { ...editor, id: undefined }; await request(`${endpoint}${editor.id ? `${editor.id}/` : ""}`, { method: editor.id ? "PATCH" : "POST", body: JSON.stringify(body) }); toast({ tone: "success", title: editor.id ? "Loan setup updated" : "Loan setup created" }); setEditor(null); setRefreshKey((value) => value + 1) } catch (error) { toast({ tone: "danger", title: "Unable to save loan setup", message: error instanceof Error ? error.message : "The backend rejected this setup." }) } finally { setSaving(false) } }
  const deactivate = async () => { if (!confirm) return; try { await request(`${endpoint}${confirm.id}/deactivate/`, { method: "POST" }); toast({ tone: "success", title: "Loan setup deactivated" }); setConfirm(null); setRefreshKey((value) => value + 1) } catch (error) { toast({ tone: "danger", title: "Unable to deactivate", message: error instanceof Error ? error.message : "The backend rejected the action." }) } }
  const actions: RowAction<LoanRecord>[] = [{ key: "edit", label: "Edit", permission: "ol_parameters.update", onSelect: (row) => { setErrors({}); setEditor({ ...row }) } }, { key: "deactivate", label: "Deactivate", permission: "ol_parameters.deactivate", tone: "danger", isVisible: (row) => row.is_active, onSelect: setConfirm }]
  const field = (key: string) => ({ value: editor ? editor[key] as string | number | readonly string[] | undefined : "", onChange: (event: React.ChangeEvent<HTMLInputElement>) => update(key, event.target.value) })
  return <div className="space-y-5 p-4 md:p-6"><header className="flex flex-wrap items-start justify-between gap-4"><div><div className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.14em] text-[var(--muted-foreground)]"><Banknote size={15} aria-hidden="true" /> Ordinary Life Parameters</div><h1 className="text-2xl font-black tracking-tight">{screen === "system" ? "OL Loan System Setup" : "OL Loan Interest Control"}</h1><p className="mt-1 max-w-3xl text-sm text-[var(--muted-foreground)]">{screen === "system" ? "Control policy-loan eligibility, limits, repayment behavior, and claim or maturity effects." : "Control effective-dated loan interest rates, compounding, grace periods, penalties, and capitalization."}</p></div><button type="button" className="button-primary" disabled={!writable} onClick={() => { setErrors({}); setEditor(defaults(screen)) }}><Plus size={16} aria-hidden="true" />New setup</button></header><div className="flex flex-wrap gap-2" role="tablist" aria-label="Loan setup screens"><button type="button" role="tab" aria-selected={screen === "system"} className={screen === "system" ? "button-primary" : "button-secondary"} onClick={() => { setScreen("system"); setFiltersState({}) }}>Loan system setup</button><button type="button" role="tab" aria-selected={screen === "interest"} className={screen === "interest" ? "button-primary" : "button-secondary"} onClick={() => { setScreen("interest"); setFiltersState({}) }}>Loan interest control</button></div><FilterBar definitions={definitions} value={filtersState} onChange={(key, value) => setFiltersState((current) => ({ ...current, [key]: value }))} onReset={() => setFiltersState({})} /><DataTable metadata={{ totalLabel: screen === "system" ? "Loan system setups" : "Loan interest controls", defaultOrdering: "code", columns: screen === "system" ? systemColumns : interestColumns } satisfies TableMetadata<LoanRecord>} fetcher={fetcher} filters={filtersState} refreshKey={refreshKey} actions={writable ? actions : []} permissions={permissions} exportFileName={`ol-loan-${screen}.csv`} /><FormModal open={Boolean(editor)} title={editor?.id ? `Edit ${screen === "system" ? "loan system setup" : "loan interest control"}` : `Create ${screen === "system" ? "loan system setup" : "loan interest control"}`} description="Choice lists are loaded from backend serializer metadata and current parameter records." onClose={() => setEditor(null)} onSave={() => void save()} saving={saving} saveLabel="Save setup">{editor && (screen === "system" ? <div className="space-y-5"><InfoBanner title="Loan limits">The maximum loan percentage is validated from 0 to 100. Minimum and maximum amounts must be positive and ordered.</InfoBanner><FormGrid columns={2}><TextInput label="Code" required error={errors.code} {...field("code")} /><TextInput label="Name" required error={errors.name} {...field("name")} /><TextInput label="Product ID" {...field("product")} /><TextInput label="Plan ID" {...field("plan")} /><Choice label="Loan basis" required error={errors.loan_basis} value={editor.loan_basis} onChange={(value) => update("loan_basis", value)} options={choices.loan_basis ?? []} /><DecimalInput label="Maximum % of cash value" required min={0} max={100} error={errors.max_loan_percentage_of_cash_value} value={text(editor.max_loan_percentage_of_cash_value)} onChange={(event) => update("max_loan_percentage_of_cash_value", event.target.value)} /><DecimalInput label="Minimum loan amount" required min={0} error={errors.min_loan_amount} value={text(editor.min_loan_amount)} onChange={(event) => update("min_loan_amount", event.target.value)} /><DecimalInput label="Maximum loan amount" required min={0} error={errors.max_loan_amount} value={text(editor.max_loan_amount)} onChange={(event) => update("max_loan_amount", event.target.value)} /><TextInput label="Loan currency" {...field("loan_currency")} /><Choice label="Effect on claim" required error={errors.effect_on_claim} value={editor.effect_on_claim} onChange={(value) => update("effect_on_claim", value)} options={choices.effect_on_claim ?? []} /><Choice label="Effect on surrender" required error={errors.effect_on_surrender} value={editor.effect_on_surrender} onChange={(value) => update("effect_on_surrender", value)} options={choices.effect_on_surrender ?? []} /><Choice label="Effect on maturity" required error={errors.effect_on_maturity} value={editor.effect_on_maturity} onChange={(value) => update("effect_on_maturity", value)} options={choices.effect_on_maturity ?? []} /><DateInput label="Effective from" required error={errors.effective_from} {...field("effective_from")} /><DateInput label="Effective to" error={errors.effective_to} {...field("effective_to")} /></FormGrid><div className="space-y-4 rounded-[10px] border bg-[var(--muted)]/25 p-4"><Toggle label="Allow policy loans" checked={Boolean(editor.allow_policy_loans)} onChange={(value) => update("allow_policy_loans", value)} /><Toggle label="Auto-deduct from benefits" checked={Boolean(editor.auto_deduct_from_benefits)} onChange={(value) => update("auto_deduct_from_benefits", value)} /><Toggle label="Require approval" checked={Boolean(editor.require_approval)} onChange={(value) => update("require_approval", value)} /></div><TextareaInput label="Description" value={text(editor.description)} onChange={(event) => update("description", event.target.value)} /></div> : <div className="space-y-5"><InfoBanner title="Interest controls">Interest and penalty rates are validated as percentages from 0 to 100. Grace days cannot be negative.</InfoBanner><FormGrid columns={2}><TextInput label="Code" required error={errors.code} {...field("code")} /><TextInput label="Name" required error={errors.name} {...field("name")} /><TextInput label="Product ID" {...field("product")} /><TextInput label="Plan ID" {...field("plan")} /><DecimalInput label="Interest rate" required min={0} max={100} error={errors.interest_rate} value={text(editor.interest_rate)} onChange={(event) => update("interest_rate", event.target.value)} /><Choice label="Compounding frequency" required error={errors.compounding_frequency} value={editor.compounding_frequency} onChange={(value) => update("compounding_frequency", value)} options={choices.compounding_frequency ?? []} /><Choice label="Interest calculation basis" required error={errors.interest_calculation_basis} value={editor.interest_calculation_basis} onChange={(value) => update("interest_calculation_basis", value)} options={choices.interest_calculation_basis ?? []} /><DecimalInput label="Grace period (days)" min={0} error={errors.grace_period_days} value={text(editor.grace_period_days)} onChange={(event) => update("grace_period_days", event.target.value)} /><DecimalInput label="Penalty interest rate" min={0} max={100} error={errors.penalty_interest_rate} value={text(editor.penalty_interest_rate)} onChange={(event) => update("penalty_interest_rate", event.target.value)} /><TextInput label="Interest suspension rule" {...field("interest_suspension_rule")} /><DateInput label="Effective from" required error={errors.effective_from} {...field("effective_from")} /><DateInput label="Effective to" error={errors.effective_to} {...field("effective_to")} /></FormGrid><div className="rounded-[10px] border bg-[var(--muted)]/25 p-4"><Toggle label="Capitalize interest" checked={Boolean(editor.capitalize_interest)} onChange={(value) => update("capitalize_interest", value)} /></div><TextareaInput label="Description" value={text(editor.description)} onChange={(event) => update("description", event.target.value)} /></div>)}</FormModal><ConfirmModal open={Boolean(confirm)} title="Deactivate loan setup" description="This configuration will no longer be used for new loan calculations." confirmLabel="Deactivate" onClose={() => setConfirm(null)} onConfirm={() => void deactivate()} /></div>
}

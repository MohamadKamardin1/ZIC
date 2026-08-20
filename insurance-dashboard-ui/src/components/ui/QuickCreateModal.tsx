import { useQuery } from "@tanstack/react-query"
import { AlertTriangle, Loader2, Plus } from "lucide-react"
import { useEffect, useId, useMemo, useState, type FormEvent, type ReactNode } from "react"
import { useAccess } from "../../lib/access"
import { hasExplicitPermission, OPTION_CREATE_PERMISSIONS, OPTION_MANAGE_HREFS, OPTION_PARAMETER_SCREEN_LABELS, prettifyOptionEntity } from "../../lib/optionMetadata"
import { ApiClientError, request } from "../../lib/apiClient"
import { Modal } from "./Overlays"
import { DateInput, DecimalInput, FieldLabel, SelectInput, TextInput, TextareaInput } from "./FormControls"

export type QuickCreateChoice = { value: string; label: string }

export type QuickCreateField = {
  name: string
  type?: string
  required?: boolean
  choices?: QuickCreateChoice[]
  default?: unknown
  nested_entity?: string
  nestedEntity?: string
  quick_create_entity?: string
  quickCreateEntity?: string
  help_text?: string
  helpText?: string
}

export type QuickCreateSchema = {
  entity: string
  permission?: string
  fields: QuickCreateField[]
  defaults?: Record<string, unknown>
}

export type QuickCreateOption = {
  value: string
  label: string
  meta?: Record<string, unknown>
}

type QuickCreateModalProps = {
  open: boolean
  entity: string
  entityLabel?: string
  permissionCode?: string
  manageHref?: string
  parameterScreenLabel?: string
  onClose: () => void
  onCreated: (option: QuickCreateOption) => void
}

type FieldErrors = Record<string, string[]>

function prettifyField(name: string): string {
  return name.replace(/[-_]/g, " ").replace(/\b\w/g, (character) => character.toUpperCase())
}

function normalizeError(error: unknown): { message: string; fieldErrors: FieldErrors } {
  if (error instanceof ApiClientError) return { message: error.message, fieldErrors: error.fieldErrors }
  if (error && typeof error === "object") {
    const record = error as Record<string, unknown>
    const raw = record.fieldErrors ?? record.field_errors ?? record.errors
    const fieldErrors: FieldErrors = {}
    if (raw && typeof raw === "object" && !Array.isArray(raw)) {
      Object.entries(raw as Record<string, unknown>).forEach(([field, detail]) => {
        fieldErrors[field] = Array.isArray(detail) ? detail.map(String) : [String(detail)]
      })
    }
    if (record.message) return { message: String(record.message), fieldErrors }
  }
  return { message: error instanceof Error ? error.message : "Unable to create this option.", fieldErrors: {} }
}

function normalizeCreatedOption(payload: unknown): QuickCreateOption | null {
  const root = payload && typeof payload === "object" ? payload as Record<string, unknown> : {}
  const candidate = root.option && typeof root.option === "object" ? root.option as Record<string, unknown> : root
  const value = candidate.value ?? candidate.id ?? candidate.code
  const label = candidate.label ?? candidate.name ?? candidate.display_name ?? candidate.displayName
  if (value === null || value === undefined || !label) return null
  return {
    value: String(value),
    label: String(label),
    meta: candidate.meta && typeof candidate.meta === "object" && !Array.isArray(candidate.meta) ? candidate.meta as Record<string, unknown> : undefined,
  }
}

function initialValues(schema: QuickCreateSchema): Record<string, string | number | boolean> {
  const values: Record<string, string | number | boolean> = {}
  schema.fields.forEach((field) => {
    const candidate = schema.defaults?.[field.name] ?? field.default
    if (typeof candidate === "string" || typeof candidate === "number" || typeof candidate === "boolean") {
      values[field.name] = candidate
    } else {
      values[field.name] = field.type === "boolean" ? false : ""
    }
  })
  return values
}

export function QuickCreateModal({ open, entity, entityLabel = entity, permissionCode, manageHref, parameterScreenLabel, onClose, onCreated }: QuickCreateModalProps) {
  const { access } = useAccess()
  const formId = `quick-create-form-${useId().replace(/:/g, "")}`
  const [values, setValues] = useState<Record<string, string | number | boolean>>({})
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [submitError, setSubmitError] = useState("")
  const [saving, setSaving] = useState(false)
  const [nestedField, setNestedField] = useState<QuickCreateField | null>(null)
  const [schemaPermission, setSchemaPermission] = useState<string | undefined>(undefined)
  const resolvedPermission = permissionCode ?? schemaPermission ?? OPTION_CREATE_PERMISSIONS[entity]
  const allowed = hasExplicitPermission(access.permissions, resolvedPermission)
  const resolvedManageHref = manageHref ?? OPTION_MANAGE_HREFS[entity]
  const resolvedParameterScreenLabel = parameterScreenLabel ?? OPTION_PARAMETER_SCREEN_LABELS[entity] ?? prettifyOptionEntity(entity)

  const schemaQuery = useQuery({
    queryKey: ["ol-option-quick-create-schema", entity],
    queryFn: () => request<QuickCreateSchema>(`/api/v1/ol/options/${encodeURIComponent(entity)}/quick-create-schema/`),
    enabled: open,
    staleTime: 5 * 60_000,
  })
  const schema = schemaQuery.data
  const duplicateMessage = useMemo(() => {
    const duplicate = Object.values(fieldErrors).flat().find((message) => /already exists|duplicate|unique/i.test(message))
    return duplicate ? `Duplicate detected: ${duplicate}` : ""
  }, [fieldErrors])

  useEffect(() => {
    if (!open) return
    if (schema) {
      setSchemaPermission(schema.permission)
      setValues(initialValues(schema))
      setFieldErrors({})
      setSubmitError("")
      setNestedField(null)
    }
  }, [open, schema])

  const setValue = (name: string, value: string | number | boolean) => {
    setValues((current) => ({ ...current, [name]: value }))
    setFieldErrors((current) => ({ ...current, [name]: [] }))
    setSubmitError("")
  }

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!schema || !allowed || saving) return
    setSaving(true)
    setFieldErrors({})
    setSubmitError("")
    try {
      const payload = await request<unknown>(`/api/v1/ol/options/${encodeURIComponent(entity)}/quick-create/`, {
        method: "POST",
        body: JSON.stringify(values),
      })
      const option = normalizeCreatedOption(payload)
      if (!option) throw new Error("The server created the record but did not return a selectable value and label.")
      onCreated(option)
    } catch (error) {
      const normalized = normalizeError(error)
      setFieldErrors(normalized.fieldErrors)
      setSubmitError(normalized.message)
    } finally {
      setSaving(false)
    }
  }

  const renderField = (field: QuickCreateField): ReactNode => {
    const fieldError = fieldErrors[field.name]?.join(" ")
    const type = (field.type ?? "string").toLowerCase()
    const label = prettifyField(field.name)
    const help = field.help_text ?? field.helpText
    const nestedEntity = field.nested_entity ?? field.nestedEntity ?? field.quick_create_entity ?? field.quickCreateEntity
    const canCreateNested = Boolean(nestedEntity && hasExplicitPermission(access.permissions, OPTION_CREATE_PERMISSIONS[nestedEntity]))
    if (type === "select" || type === "choice" || type === "relation") {
      return <div key={field.name} className="flex items-end gap-2"><div className="min-w-0 flex-1"><SelectInput label={label} name={field.name} required={field.required} hint={help} error={fieldError} value={String(values[field.name] ?? "")} onChange={(event) => setValue(field.name, event.target.value)}><option value="">Select {label.toLowerCase()}</option>{(field.choices ?? []).map((choice) => <option key={choice.value} value={choice.value}>{choice.label}</option>)}</SelectInput></div>{canCreateNested && <button type="button" className="mb-0.5 inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-[10px] border border-[var(--border)] text-[var(--primary)] outline-none transition hover:bg-[var(--secondary)] focus-visible:border-[var(--ring)] focus-visible:ring-2 focus-visible:ring-[color-mix(in_srgb,var(--ring)_18%,transparent)] active:scale-[0.97]" onClick={() => setNestedField(field)} aria-label={`Add new ${prettifyField(nestedEntity ?? "option")}`} title={`Add new ${prettifyField(nestedEntity ?? "option")}`}><Plus size={16} aria-hidden="true" /></button>}</div>
    }
    if (type === "boolean" || type === "bool" || type === "checkbox") {
      return <label key={field.name} className="flex items-center gap-3 rounded-[10px] border px-3 py-2.5 text-sm"><input type="checkbox" checked={Boolean(values[field.name])} onChange={(event) => setValue(field.name, event.target.checked)} /> <span>{label}{field.required && <span className="ml-1 text-[var(--destructive)]" aria-label="required">*</span>}</span>{help && <span className="ml-auto text-xs text-[var(--muted-foreground)]">{help}</span>}</label>
    }
    if (type === "number" || type === "decimal" || type === "integer") {
      return <DecimalInput key={field.name} label={label} name={field.name} required={field.required} hint={help} error={fieldError} value={String(values[field.name] ?? "")} onChange={(event) => setValue(field.name, event.target.value)} />
    }
    if (type === "date") {
      return <DateInput key={field.name} label={label} name={field.name} required={field.required} hint={help} error={fieldError} value={String(values[field.name] ?? "")} onChange={(event) => setValue(field.name, event.target.value)} />
    }
    if (type === "textarea" || type === "text-area") {
      return <TextareaInput key={field.name} label={label} name={field.name} required={field.required} hint={help} error={fieldError} value={String(values[field.name] ?? "")} onChange={(event) => setValue(field.name, event.target.value)} />
    }
    return <TextInput key={field.name} label={label} name={field.name} required={field.required} hint={help} error={fieldError} type={type === "email" ? "email" : "text"} value={String(values[field.name] ?? "")} onChange={(event) => setValue(field.name, event.target.value)} />
  }

  const title = `Add ${entityLabel}`
  const nestedLabel = nestedField ? prettifyField(nestedField.nested_entity ?? nestedField.nestedEntity ?? nestedField.quick_create_entity ?? nestedField.quickCreateEntity ?? "option") : "option"

  return <>
    <Modal open={open} title={title} description="Create a reference option without leaving the current form." onClose={onClose} size="lg" footer={<><button type="button" className="button-secondary" onClick={onClose} disabled={saving}>Cancel</button><button type="submit" form={formId} className="button-primary" disabled={saving || schemaQuery.isLoading || !schema || !allowed}>{saving ? "Creating…" : "Create option"}</button></>}>
      {!allowed && <div className="rounded-[10px] border border-[var(--destructive)]/30 bg-[var(--destructive)]/10 p-3 text-sm text-[var(--destructive)]" role="alert">You do not have permission to create this option.</div>}
      {allowed && schemaQuery.isLoading && <div className="flex items-center justify-center gap-2 py-8 text-sm text-[var(--muted-foreground)]" role="status"><Loader2 size={16} className="animate-spin" aria-hidden="true" /> Loading quick-create fields…</div>}
      {allowed && schemaQuery.isError && <div className="rounded-[10px] border border-[var(--destructive)]/30 bg-[var(--destructive)]/10 p-3 text-sm text-[var(--destructive)]" role="alert">Unable to load the quick-create schema.</div>}
      {allowed && schema && <form id={formId} onSubmit={submit} className="space-y-4"><div className="flex gap-2 rounded-[10px] border border-[var(--primary)]/25 bg-[var(--primary)]/10 p-3 text-sm text-[var(--foreground)]" role="note"><span className="font-semibold">Info</span><span>This creates a minimal record. Complete full configuration in {resolvedManageHref ? <a href={resolvedManageHref} target="_blank" rel="noreferrer" className="font-semibold text-[var(--primary)] underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]">{resolvedParameterScreenLabel}</a> : resolvedParameterScreenLabel}.</span></div><div className="grid grid-cols-1 gap-4 md:grid-cols-2">{schema.fields.map(renderField)}</div>{duplicateMessage && <div className="flex gap-2 rounded-[10px] border border-[var(--warning)]/35 bg-[var(--warning)]/10 p-3 text-sm text-[var(--foreground)]" role="alert"><AlertTriangle size={16} className="mt-0.5 shrink-0 text-[var(--warning)]" aria-hidden="true" /><span>{duplicateMessage}</span></div>}{submitError && !duplicateMessage && <p className="text-sm text-[var(--destructive)]" role="alert">{submitError}</p>}</form>}
    </Modal>
    {nestedField && (nestedField.nested_entity ?? nestedField.nestedEntity ?? nestedField.quick_create_entity ?? nestedField.quickCreateEntity) && <QuickCreateModal open={Boolean(nestedField)} entity={nestedField.nested_entity ?? nestedField.nestedEntity ?? nestedField.quick_create_entity ?? nestedField.quickCreateEntity ?? ""} entityLabel={nestedLabel} onClose={() => setNestedField(null)} onCreated={(option) => { setValue(nestedField.name, option.value); setNestedField(null) }} />}
  </>
}

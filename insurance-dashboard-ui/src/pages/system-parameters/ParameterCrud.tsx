import { useEffect, useState, useCallback } from "react"
import {
  Plus,
  Pencil,
  Trash2,
  Save,
  X,
  ChevronDown,
  GripVertical,
  AlertCircle,
  Check,
  Loader2,
} from "lucide-react"
import {
  listSystemParameters,
  createSystemParameter,
  updateSystemParameter,
  deleteSystemParameter,
} from "../../lib/api"
import { SkeletonTable } from "../../components/shared/Skeleton"
import { useDataRefresh } from "../../lib/useDataRefresh"
import type { SystemParameter } from "../../lib/types"

interface ParameterCrudProps {
  groupId: string
  title?: string
  description?: string
}

type ValueType = "STRING" | "TEXT" | "INTEGER" | "FLOAT" | "BOOLEAN" | "JSON"

interface ParamForm {
  code: string
  name: string
  description: string
  valueType: ValueType
  stringValue: string | null
  integerValue: number | null
  floatValue: number | null
  booleanValue: boolean | null
  jsonValue: unknown
  sortOrder: number
}

const EMPTY_FORM: ParamForm = {
  code: "",
  name: "",
  description: "",
  valueType: "STRING",
  stringValue: "",
  integerValue: null,
  floatValue: null,
  booleanValue: null,
  jsonValue: null,
  sortOrder: 0,
}

function paramToForm(p: SystemParameter): ParamForm {
  return {
    code: p.code,
    name: p.name,
    description: p.description ?? "",
    valueType: p.valueType as ValueType,
    stringValue: p.stringValue,
    integerValue: p.integerValue,
    floatValue: p.floatValue,
    booleanValue: p.booleanValue,
    jsonValue: p.jsonValue,
    sortOrder: p.sortOrder ?? 0,
  }
}

function formToPayload(
  form: ParamForm,
  groupId: string,
): Record<string, unknown> {
  const value = (() => {
    switch (form.valueType) {
      case "STRING":
      case "TEXT":
        return form.stringValue ?? ""
      case "INTEGER":
        return form.integerValue
      case "FLOAT":
        return form.floatValue
      case "BOOLEAN":
        return form.booleanValue
      case "JSON":
        return form.jsonValue
      default:
        return null
    }
  })()
  return {
    group: groupId,
    code: form.code.trim().toUpperCase(),
    name: form.name,
    description: form.description,
    value_type: form.valueType,
    value,
    sort_order: form.sortOrder,
  }
}

function ValueEditor({
  valueType,
  value,
  onChange,
}: {
  valueType: ValueType
  value: unknown
  onChange: (v: unknown) => void
}) {
  switch (valueType) {
    case "STRING":
      return (
        <input
          type="text"
          value={(value as string) ?? ""}
          onChange={(e) => onChange(e.target.value)}
          className="w-full rounded border border-input bg-background px-2 py-1.5 text-sm"
        />
      )
    case "TEXT":
      return (
        <textarea
          value={(value as string) ?? ""}
          onChange={(e) => onChange(e.target.value)}
          rows={3}
          className="w-full rounded border border-input bg-background px-2 py-1.5 text-sm"
        />
      )
    case "INTEGER":
      return (
        <input
          type="number"
          value={(value as number) ?? ""}
          onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
          className="w-full rounded border border-input bg-background px-2 py-1.5 text-sm"
        />
      )
    case "FLOAT":
      return (
        <input
          type="number"
          step="0.01"
          value={(value as number) ?? ""}
          onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
          className="w-full rounded border border-input bg-background px-2 py-1.5 text-sm"
        />
      )
    case "BOOLEAN":
      return (
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={!!value}
            onChange={(e) => onChange(e.target.checked)}
            className="rounded border-input"
          />
          <span className="text-sm">{value ? "True" : "False"}</span>
        </label>
      )
    case "JSON":
      return (
        <textarea
          value={
            value ? JSON.stringify(value, null, 2) : ""
          }
          onChange={(e) => {
            try {
              onChange(JSON.parse(e.target.value))
            } catch {
              // Keep current value while editing
            }
          }}
          rows={6}
          className="w-full rounded border border-input bg-background px-2 py-1.5 font-mono text-xs"
        />
      )
    default:
      return <span className="text-sm text-muted-foreground">{String(value)}</span>
  }
}

export default function ParameterCrud({
  groupId,
  title,
  description,
}: ParameterCrudProps) {
  const [params, setParams] = useState<SystemParameter[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editForm, setEditForm] = useState<ParamForm>(EMPTY_FORM)
  const [showAdd, setShowAdd] = useState(false)
  const [addForm, setAddForm] = useState<ParamForm>(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const refreshKey = useDataRefresh("system-parameters")

  const load = useCallback(async () => {
    setLoading(true)
    setError("")
    try {
      const data = await listSystemParameters(groupId)
      setParams(data.sort((a, b) => (a.sortOrder ?? 0) - (b.sortOrder ?? 0)))
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load parameters")
    } finally {
      setLoading(false)
    }
  }, [groupId, refreshKey])

  useEffect(() => {
    load()
  }, [load])

  async function handleSave(id: string) {
    setSaving(true)
    try {
      await updateSystemParameter(id, formToPayload(editForm, groupId))
      setEditingId(null)
      await load()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to update")
    } finally {
      setSaving(false)
    }
  }

  async function handleCreate() {
    if (!addForm.code) {
      setError("Code is required")
      return
    }
    setSaving(true)
    setError("")
    try {
      await createSystemParameter(formToPayload(addForm, groupId))
      setShowAdd(false)
      setAddForm(EMPTY_FORM)
      await load()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create")
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id: string) {
    if (!window.confirm("Delete this parameter?")) return
    try {
      await deleteSystemParameter(id)
      await load()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to delete")
    }
  }

  function startEdit(p: SystemParameter) {
    setEditingId(p.id)
    setEditForm(paramToForm(p))
  }

  function cancelEdit() {
    setEditingId(null)
  }

  if (loading) {
    return <SkeletonTable rows={5} cols={6} />
  }

  return (
    <div>
      {title && <h2 className="mb-1 text-base font-semibold">{title}</h2>}
      {description && <p className="mb-4 text-xs text-muted-foreground">{description}</p>}

      {error && (
        <div className="mb-4 flex items-center gap-2 rounded-lg bg-destructive/10 px-4 py-2 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 flex-none" />
          {error}
          <button onClick={() => setError("")} className="ml-auto">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      <div className="mb-4 flex items-center justify-between">
        <span className="text-xs text-muted-foreground">{params.length} parameter{params.length !== 1 ? "s" : ""}</span>
        <button
          onClick={() => {
            setShowAdd(true)
            setAddForm({ ...EMPTY_FORM, sortOrder: params.length * 10 + 10 })
          }}
          className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90"
        >
          <Plus className="h-3.5 w-3.5" />
          Add Parameter
        </button>
      </div>

      {/* Add form */}
      {showAdd && (
        <div className="mb-4 rounded-lg border border-border bg-card p-4">
          <h3 className="mb-3 text-sm font-semibold">New Parameter</h3>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground">Code *</label>
              <input
                type="text"
                value={addForm.code}
                onChange={(e) => setAddForm({ ...addForm, code: e.target.value })}
                className="mt-1 w-full rounded border border-input bg-background px-2 py-1.5 text-sm font-mono"
                placeholder="MY_PARAM"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Name</label>
              <input
                type="text"
                value={addForm.name}
                onChange={(e) => setAddForm({ ...addForm, name: e.target.value })}
                className="mt-1 w-full rounded border border-input bg-background px-2 py-1.5 text-sm"
                placeholder="My Parameter"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Value Type</label>
              <select
                value={addForm.valueType}
                onChange={(e) => setAddForm({ ...addForm, valueType: e.target.value as ValueType })}
                className="mt-1 w-full rounded border border-input bg-background px-2 py-1.5 text-sm"
              >
                <option value="STRING">String</option>
                <option value="TEXT">Text</option>
                <option value="INTEGER">Integer</option>
                <option value="FLOAT">Float</option>
                <option value="BOOLEAN">Boolean</option>
                <option value="JSON">JSON</option>
              </select>
            </div>
            <div className="sm:col-span-2 lg:col-span-3">
              <label className="text-xs font-medium text-muted-foreground">Description</label>
              <input
                type="text"
                value={addForm.description}
                onChange={(e) => setAddForm({ ...addForm, description: e.target.value })}
                className="mt-1 w-full rounded border border-input bg-background px-2 py-1.5 text-sm"
              />
            </div>
            <div className="sm:col-span-2 lg:col-span-3">
              <label className="text-xs font-medium text-muted-foreground">Value</label>
              <ValueEditor
                valueType={addForm.valueType}
                value={
                  addForm.valueType === "STRING" || addForm.valueType === "TEXT"
                    ? addForm.stringValue
                    : addForm.valueType === "INTEGER"
                      ? addForm.integerValue
                      : addForm.valueType === "FLOAT"
                        ? addForm.floatValue
                        : addForm.valueType === "BOOLEAN"
                          ? addForm.booleanValue
                          : addForm.jsonValue
                }
                onChange={(v) => {
                  if (addForm.valueType === "STRING" || addForm.valueType === "TEXT")
                    setAddForm({ ...addForm, stringValue: v as string })
                  else if (addForm.valueType === "INTEGER")
                    setAddForm({ ...addForm, integerValue: v as number })
                  else if (addForm.valueType === "FLOAT")
                    setAddForm({ ...addForm, floatValue: v as number })
                  else if (addForm.valueType === "BOOLEAN")
                    setAddForm({ ...addForm, booleanValue: v as boolean })
                  else
                    setAddForm({ ...addForm, jsonValue: v as Record<string, unknown> })
                }}
              />
            </div>
          </div>
          <div className="mt-3 flex justify-end gap-2">
            <button
              onClick={() => { setShowAdd(false); setError("") }}
              className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium hover:bg-secondary"
            >
              Cancel
            </button>
            <button
              onClick={handleCreate}
              disabled={saving || !addForm.code}
              className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
              Create
            </button>
          </div>
        </div>
      )}

      {/* Parameters list */}
      <div className="overflow-hidden rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-secondary/50">
              <th className="w-8 px-2 py-2.5"></th>
              <th className="px-3 py-2.5 text-left text-xs font-medium text-muted-foreground">Code</th>
              <th className="px-3 py-2.5 text-left text-xs font-medium text-muted-foreground">Name</th>
              <th className="px-3 py-2.5 text-left text-xs font-medium text-muted-foreground">Type</th>
              <th className="px-3 py-2.5 text-left text-xs font-medium text-muted-foreground">Value</th>
              <th className="w-20 px-3 py-2.5 text-right text-xs font-medium text-muted-foreground">Actions</th>
            </tr>
          </thead>
          <tbody>
            {params.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-sm text-muted-foreground">
                  No parameters found in this group.
                </td>
              </tr>
            )}
            {params.map((p) => {
              const editing = editingId === p.id
              return (
                <tr key={p.id} className="border-b border-border last:border-0 hover:bg-secondary/20">
                  <td className="px-2 py-2">
                    <GripVertical className="h-3.5 w-3.5 text-muted-foreground/40" />
                  </td>
                  <td className="px-3 py-2">
                    {editing ? (
                      <input
                        type="text"
                        value={editForm.code}
                        onChange={(e) => setEditForm({ ...editForm, code: e.target.value })}
                        className="w-32 rounded border border-input bg-background px-2 py-1 font-mono text-xs"
                      />
                    ) : (
                      <span className="font-mono text-xs text-muted-foreground">{p.code}</span>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    {editing ? (
                      <input
                        type="text"
                        value={editForm.name}
                        onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                        className="w-40 rounded border border-input bg-background px-2 py-1 text-sm"
                      />
                    ) : (
                      <span className="text-sm font-medium">{p.name}</span>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    {editing ? (
                      <select
                        value={editForm.valueType}
                        onChange={(e) => setEditForm({ ...editForm, valueType: e.target.value as ValueType })}
                        className="w-24 rounded border border-input bg-background px-2 py-1 text-xs"
                      >
                        <option value="STRING">String</option>
                        <option value="TEXT">Text</option>
                        <option value="INTEGER">Integer</option>
                        <option value="FLOAT">Float</option>
                        <option value="BOOLEAN">Boolean</option>
                        <option value="JSON">JSON</option>
                      </select>
                    ) : (
                      <span className="rounded bg-secondary px-2 py-0.5 text-xs">{p.valueType}</span>
                    )}
                  </td>
                  <td className="max-w-[300px] px-3 py-2">
                    {editing ? (
                      <ValueEditor
                        valueType={editForm.valueType}
                        value={
                          editForm.valueType === "STRING" || editForm.valueType === "TEXT"
                            ? editForm.stringValue
                            : editForm.valueType === "INTEGER"
                              ? editForm.integerValue
                              : editForm.valueType === "FLOAT"
                                ? editForm.floatValue
                                : editForm.valueType === "BOOLEAN"
                                  ? editForm.booleanValue
                                  : editForm.jsonValue
                        }
                        onChange={(v) => {
                          if (editForm.valueType === "STRING" || editForm.valueType === "TEXT")
                            setEditForm({ ...editForm, stringValue: v as string })
                          else if (editForm.valueType === "INTEGER")
                            setEditForm({ ...editForm, integerValue: v as number })
                          else if (editForm.valueType === "FLOAT")
                            setEditForm({ ...editForm, floatValue: v as number })
                          else if (editForm.valueType === "BOOLEAN")
                            setEditForm({ ...editForm, booleanValue: v as boolean })
                          else
                            setEditForm({ ...editForm, jsonValue: v as Record<string, unknown> })
                        }}
                      />
                    ) : (
                      <div className="truncate text-xs">
                        {p.valueType === "JSON" ? (
                          <span className="font-mono text-muted-foreground">
                            {p.value ? JSON.stringify(p.value).substring(0, 80) + (JSON.stringify(p.value).length > 80 ? "…" : "") : "—"}
                          </span>
                        ) : (
                          <span>{p.value != null ? String(p.value) : "—"}</span>
                        )}
                      </div>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {editing ? (
                      <div className="inline-flex gap-1">
                        <button
                          onClick={() => handleSave(p.id)}
                          disabled={saving}
                          className="rounded p-1 text-primary hover:bg-primary/10"
                        >
                          {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
                        </button>
                        <button
                          onClick={cancelEdit}
                          className="rounded p-1 text-muted-foreground hover:bg-secondary"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    ) : (
                      <div className="inline-flex gap-1">
                        <button
                          onClick={() => startEdit(p)}
                          className="rounded p-1 text-muted-foreground hover:text-foreground"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={() => handleDelete(p.id)}
                          className="rounded p-1 text-muted-foreground hover:text-destructive"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

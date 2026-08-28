import { useEffect, useState } from "react"
import { Plus, Pencil, Trash2, X, Check, Loader2 } from "lucide-react"
import { PageHeader } from "./SharedComponents"
import {
  fetchAllDocumentRequirements,
  createDocumentRequirement,
  updateDocumentRequirement,
  deleteDocumentRequirement,
  fetchPartnerTypes,
} from "../../lib/api"
import type { PartnerTypeDocumentRequirement, PartnerTypeRecord } from "../../lib/types"

interface FormState {
  partnerType: string
  code: string
  description: string
  isRequired: boolean
  isMandatory: boolean
  sortOrder: number
  isActive: boolean
}

const emptyForm: FormState = {
  partnerType: "",
  code: "",
  description: "",
  isRequired: true,
  isMandatory: false,
  sortOrder: 0,
  isActive: true,
}

export default function PartnerDocumentRequirements() {
  const [items, setItems] = useState<PartnerTypeDocumentRequirement[]>([])
  const [partnerTypes, setPartnerTypes] = useState<PartnerTypeRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [adding, setAdding] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState<FormState>(emptyForm)

  useEffect(() => {
    Promise.all([
      fetchAllDocumentRequirements(),
      fetchPartnerTypes(),
    ]).then(([docs, types]) => {
      setItems(docs)
      setPartnerTypes(types.filter((t) => t.isActive))
    }).finally(() => setLoading(false))
  }, [])

  function resetForm() {
    setForm(emptyForm)
    setAdding(false)
    setEditingId(null)
  }

  function startAdd() {
    resetForm()
    setAdding(true)
  }

  function startEdit(item: PartnerTypeDocumentRequirement) {
    setForm({
      partnerType: item.partnerType,
      code: item.code,
      description: item.description,
      isRequired: item.isRequired,
      isMandatory: item.isMandatory,
      sortOrder: item.sortOrder,
      isActive: item.isActive,
    })
    setEditingId(item.id)
    setAdding(false)
  }

  async function handleAdd() {
    if (!form.partnerType || !form.code.trim()) return
    setSaving(true)
    try {
      // Use the flat endpoint for create — POST to /documents/
      // But the flat endpoint might not have partner_type in validated_data correctly
      // Let's use the nested endpoint approach
      const created = await createDocumentRequirement(form.partnerType, form)
      setItems((prev) => [...prev, created])
      resetForm()
    } catch {
      // error handled by api
    } finally {
      setSaving(false)
    }
  }

  async function handleSave(id: string) {
    if (!form.code.trim()) return
    setSaving(true)
    try {
      const updated = await updateDocumentRequirement(form.partnerType, id, form)
      setItems((prev) => prev.map((i) => (i.id === id ? updated : i)))
      resetForm()
    } catch {
      // error handled by api
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id: string, partnerTypeId: string) {
    try {
      await deleteDocumentRequirement(partnerTypeId, id)
      setItems((prev) => prev.filter((i) => i.id !== id))
    } catch {
      // error handled by api
    }
  }

  // Group documents by partner type
  const grouped = items.reduce<Record<string, PartnerTypeDocumentRequirement[]>>((acc, item) => {
    const key = item.partnerTypeName || "Unknown"
    if (!acc[key]) acc[key] = []
    acc[key].push(item)
    return acc
  }, {})

  const sortedGroups = Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b))

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12 text-muted-foreground">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
        Loading...
      </div>
    )
  }

  const ptOptions = partnerTypes.map((pt) => (
    <option key={pt.id} value={pt.id}>{pt.name} ({pt.code})</option>
  ))

  return (
    <div>
      <PageHeader title="Document Requirements" description="All document requirements defined per partner type">
        <button onClick={startAdd} disabled={adding} className="flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
          <Plus className="h-4 w-4" />
          Add Document
        </button>
      </PageHeader>

      {/* Add form */}
      {adding && (
        <div className="mb-6 rounded-lg border border-border bg-card p-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-muted-foreground">Partner Type</label>
              <select
                value={form.partnerType}
                onChange={(e) => setForm({ ...form, partnerType: e.target.value })}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="">-- Select --</option>
                {ptOptions}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-muted-foreground">Code</label>
              <input
                value={form.code}
                onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase().replace(/[^A-Z0-9_]/g, "") })}
                placeholder="e.g. NID"
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              />
            </div>
            <div className="sm:col-span-2">
              <label className="mb-1 block text-xs font-medium text-muted-foreground">Description</label>
              <input
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="Document description"
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-muted-foreground">Required</label>
              <select
                value={form.isRequired ? "yes" : "no"}
                onChange={(e) => setForm({ ...form, isRequired: e.target.value === "yes" })}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="yes">Yes</option>
                <option value="no">No</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-muted-foreground">Mandatory</label>
              <select
                value={form.isMandatory ? "yes" : "no"}
                onChange={(e) => setForm({ ...form, isMandatory: e.target.value === "yes" })}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="yes">Yes</option>
                <option value="no">No</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-muted-foreground">Sort Order</label>
              <input
                type="number"
                value={form.sortOrder}
                onChange={(e) => setForm({ ...form, sortOrder: parseInt(e.target.value) || 0 })}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-muted-foreground">Active</label>
              <select
                value={form.isActive ? "yes" : "no"}
                onChange={(e) => setForm({ ...form, isActive: e.target.value === "yes" })}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="yes">Yes</option>
                <option value="no">No</option>
              </select>
            </div>
          </div>
          <div className="mt-3 flex gap-2">
            <button
              onClick={handleAdd}
              disabled={saving || !form.code.trim() || !form.partnerType}
              className="flex items-center gap-1 rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {saving && <Loader2 className="h-3 w-3 animate-spin" />}
              Save
            </button>
            <button onClick={resetForm} disabled={saving} className="rounded-lg border border-border bg-card px-3 py-1.5 text-xs hover:bg-accent">
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Grouped tables */}
      {sortedGroups.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted-foreground">No document requirements configured yet.</p>
      ) : (
        <div className="space-y-8">
          {sortedGroups.map(([groupName, docs]) => (
            <div key={groupName}>
              <h2 className="mb-3 text-lg font-semibold">{groupName}</h2>
              <div className="overflow-hidden rounded-lg border border-border">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-muted/50 text-left text-xs font-medium text-muted-foreground">
                      <th className="px-4 py-3">Code</th>
                      <th className="px-4 py-3">Description</th>
                      <th className="px-4 py-3">Required</th>
                      <th className="px-4 py-3">Mandatory</th>
                      <th className="px-4 py-3">Order</th>
                      <th className="px-4 py-3">Active</th>
                      <th className="px-4 py-3">Last Updated</th>
                      <th className="px-4 py-3 w-20">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {docs.map((item) => (
                      editingId === item.id ? (
                        <tr key={item.id} className="border-t bg-accent/30">
                          <td className="px-4 py-2">
                            <input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase().replace(/[^A-Z0-9_]/g, "") })} className="w-full rounded border border-input bg-background px-2 py-1 text-xs" />
                          </td>
                          <td className="px-4 py-2">
                            <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="w-full rounded border border-input bg-background px-2 py-1 text-xs" />
                          </td>
                          <td className="px-4 py-2">
                            <select value={form.isRequired ? "yes" : "no"} onChange={(e) => setForm({ ...form, isRequired: e.target.value === "yes" })} className="rounded border border-input bg-background px-2 py-1 text-xs">
                              <option value="yes">Yes</option>
                              <option value="no">No</option>
                            </select>
                          </td>
                          <td className="px-4 py-2">
                            <select value={form.isMandatory ? "yes" : "no"} onChange={(e) => setForm({ ...form, isMandatory: e.target.value === "yes" })} className="rounded border border-input bg-background px-2 py-1 text-xs">
                              <option value="yes">Yes</option>
                              <option value="no">No</option>
                            </select>
                          </td>
                          <td className="px-4 py-2">
                            <input type="number" value={form.sortOrder} onChange={(e) => setForm({ ...form, sortOrder: parseInt(e.target.value) || 0 })} className="w-16 rounded border border-input bg-background px-2 py-1 text-xs" />
                          </td>
                          <td className="px-4 py-2">
                            <select value={form.isActive ? "yes" : "no"} onChange={(e) => setForm({ ...form, isActive: e.target.value === "yes" })} className="rounded border border-input bg-background px-2 py-1 text-xs">
                              <option value="yes">Yes</option>
                              <option value="no">No</option>
                            </select>
                          </td>
                          <td className="px-4 py-2 text-xs text-muted-foreground">—</td>
                          <td className="px-4 py-2">
                            <div className="flex gap-1">
                              <button onClick={() => handleSave(item.id)} disabled={saving || !form.code.trim()} className="rounded p-1 text-[var(--color-text-success-soft)] hover:bg-[var(--color-bg-success-soft)] disabled:opacity-50" title="Save">
                                <Check className="h-4 w-4" />
                              </button>
                              <button onClick={resetForm} disabled={saving} className="rounded p-1 text-muted-foreground hover:bg-accent" title="Cancel">
                                <X className="h-4 w-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ) : (
                        <tr key={item.id} className="border-t hover:bg-muted/20">
                          <td className="px-4 py-3 font-medium">{item.code}</td>
                          <td className="px-4 py-3 text-muted-foreground">{item.description || "—"}</td>
                          <td className="px-4 py-3">
                            <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${item.isRequired ? "bg-[var(--color-bg-success-soft)] text-[var(--color-text-success-soft)]" : "bg-muted text-muted-foreground"}`}>
                              {item.isRequired ? "Yes" : "No"}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${item.isMandatory ? "bg-[var(--color-bg-warning-soft)] text-[var(--color-text-warning-soft)]" : "bg-muted text-muted-foreground"}`}>
                              {item.isMandatory ? "Yes" : "No"}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-muted-foreground">{item.sortOrder}</td>
                          <td className="px-4 py-3">
                            <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${item.isActive ? "bg-[var(--color-bg-success-soft)] text-[var(--color-text-success-soft)]" : "bg-[var(--color-bg-destructive-soft)] text-[var(--color-text-destructive-soft)]"}`}>
                              {item.isActive ? "Active" : "Inactive"}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-xs text-muted-foreground">
                            {item.updatedAt ? new Date(item.updatedAt).toLocaleDateString() : "—"}
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex gap-1">
                              <button onClick={() => startEdit(item)} className="rounded p-1 text-primary hover:bg-accent" title="Edit">
                                <Pencil className="h-4 w-4" />
                              </button>
                              <button onClick={() => handleDelete(item.id, item.partnerType)} className="rounded p-1 text-[var(--color-text-destructive-soft)] hover:bg-[var(--color-bg-destructive-soft)]" title="Delete">
                                <Trash2 className="h-4 w-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      )
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

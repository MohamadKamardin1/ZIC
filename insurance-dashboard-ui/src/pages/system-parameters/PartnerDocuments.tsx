import { useEffect, useState } from "react"
import { Plus, Pencil, Trash2, X, Check, Loader2, ChevronDown, ChevronRight } from "lucide-react"
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

export default function PartnerDocuments() {
  const [items, setItems] = useState<PartnerTypeDocumentRequirement[]>([])
  const [partnerTypes, setPartnerTypes] = useState<PartnerTypeRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [adding, setAdding] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [expandedTypes, setExpandedTypes] = useState<Set<string>>(new Set())
  const [form, setForm] = useState<FormState>(emptyForm)
  const [editForm, setEditForm] = useState<Partial<PartnerTypeDocumentRequirement>>({})

  useEffect(() => {
    Promise.all([
      fetchAllDocumentRequirements(),
      fetchPartnerTypes(),
    ])
      .then(([docs, types]) => {
        setItems(docs)
        const active = types.filter((t) => t.isActive)
        setPartnerTypes(active)
        setExpandedTypes(new Set(active.map((t) => t.id)))
      })
      .finally(() => setLoading(false))
  }, [])

  function resetForm() {
    setForm(emptyForm)
    setAdding(false)
  }

  function startAdd() {
    resetForm()
    setAdding(true)
  }

  function startEdit(item: PartnerTypeDocumentRequirement) {
    setEditingId(item.id)
    setEditForm({ ...item })
  }

  async function handleAdd() {
    if (!form.partnerType || !form.code) return
    setSaving(true)
    try {
      const created = await createDocumentRequirement(form.partnerType, {
        code: form.code,
        description: form.description,
        is_required: form.isRequired,
        is_mandatory: form.isMandatory,
        sort_order: form.sortOrder,
        is_active: form.isActive,
      } as unknown as Partial<PartnerTypeDocumentRequirement>)
      setItems((prev) => [...prev, created])
      resetForm()
    } catch (e) {
      console.error(e)
    } finally {
      setSaving(false)
    }
  }

  async function handleSave(id: string) {
    const ptId = items.find((i) => i.id === id)?.partnerType
    if (!ptId) return
    setSaving(true)
    try {
      const updated = await updateDocumentRequirement(ptId, id, editForm)
      setItems((prev) => prev.map((i) => (i.id === id ? updated : i)))
      setEditingId(null)
    } catch (e) {
      console.error(e)
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id: string) {
    const ptId = items.find((i) => i.id === id)?.partnerType
    if (!ptId) return
    if (!window.confirm("Delete this document requirement?")) return
    try {
      await deleteDocumentRequirement(ptId, id)
      setItems((prev) => prev.filter((i) => i.id !== id))
    } catch (e) {
      console.error(e)
    }
  }

  const grouped = items.reduce<Record<string, PartnerTypeDocumentRequirement[]>>((acc, item) => {
    const key = item.partnerType
    if (!acc[key]) acc[key] = []
    acc[key].push(item)
    return acc
  }, {})

  function toggleType(id: string) {
    setExpandedTypes((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12 text-muted-foreground">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
        Loading...
      </div>
    )
  }

  return (
    <div>
      <PageHeader title="Document Config per Partner Type" description="Configure required and optional documents for each partner type">
        <button
          onClick={startAdd}
          disabled={adding}
          className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          <Plus className="h-4 w-4" />
          Add Document
        </button>
      </PageHeader>

      {adding && (
        <div className="mb-6 rounded-xl border border-border bg-card p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-foreground">New Document Requirement</h3>
            <button onClick={resetForm} className="rounded p-1 text-muted-foreground hover:bg-accent">
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-foreground">Partner Type *</label>
              <select
                value={form.partnerType}
                onChange={(e) => setForm((f) => ({ ...f, partnerType: e.target.value }))}
                className="w-full rounded-lg border border-input bg-background px-2.5 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
              >
                <option value="">Select type...</option>
                {partnerTypes.map((t) => (
                  <option key={t.id} value={t.id}>{t.name} ({t.code})</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-foreground">Document Code *</label>
              <input
                value={form.code}
                onChange={(e) => setForm((f) => ({ ...f, code: e.target.value }))}
                placeholder="e.g. TIN_CERT"
                className="w-full rounded-lg border border-input bg-background px-2.5 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-foreground">Description</label>
              <input
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                placeholder="e.g. TIN Certificate"
                className="w-full rounded-lg border border-input bg-background px-2.5 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-foreground">Sort Order</label>
              <input
                type="number"
                value={form.sortOrder}
                onChange={(e) => setForm((f) => ({ ...f, sortOrder: Number(e.target.value) }))}
                className="w-full rounded-lg border border-input bg-background px-2.5 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-foreground">Required</label>
              <select
                value={form.isRequired ? "yes" : "no"}
                onChange={(e) => setForm((f) => ({ ...f, isRequired: e.target.value === "yes" }))}
                className="w-full rounded-lg border border-input bg-background px-2.5 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
              >
                <option value="yes">Yes</option>
                <option value="no">No</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-foreground">Mandatory</label>
              <select
                value={form.isMandatory ? "yes" : "no"}
                onChange={(e) => setForm((f) => ({ ...f, isMandatory: e.target.value === "yes" }))}
                className="w-full rounded-lg border border-input bg-background px-2.5 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
              >
                <option value="yes">Yes</option>
                <option value="no">No</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-foreground">Active</label>
              <select
                value={form.isActive ? "yes" : "no"}
                onChange={(e) => setForm((f) => ({ ...f, isActive: e.target.value === "yes" }))}
                className="w-full rounded-lg border border-input bg-background px-2.5 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
              >
                <option value="yes">Yes</option>
                <option value="no">No</option>
              </select>
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button onClick={resetForm} className="rounded-lg border border-input px-3 py-1.5 text-xs font-medium text-foreground hover:bg-accent">
              Cancel
            </button>
            <button
              onClick={handleAdd}
              disabled={saving || !form.partnerType || !form.code}
              className="inline-flex items-center gap-1 rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Plus className="h-3 w-3" />}
              Save
            </button>
          </div>
        </div>
      )}

      {partnerTypes.length === 0 ? (
        <p className="text-sm text-muted-foreground text-center py-8">No active partner types found.</p>
      ) : (
        <div className="space-y-3">
          {partnerTypes.map((pt) => {
            const docs = grouped[pt.id] || []
            const isExpanded = expandedTypes.has(pt.id)
            return (
              <div key={pt.id} className="rounded-xl border border-border bg-card overflow-hidden">
                <div
                  onClick={() => toggleType(pt.id)}
                  className="flex items-center justify-between px-5 py-3.5 cursor-pointer hover:bg-muted/30 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    {isExpanded ? <ChevronDown className="h-4 w-4 text-muted-foreground" /> : <ChevronRight className="h-4 w-4 text-muted-foreground" />}
                    <span className="text-sm font-medium text-foreground">{pt.name}</span>
                    <span className="text-xs text-muted-foreground">({pt.code})</span>
                  </div>
                  <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary">
                    {docs.length} doc{docs.length !== 1 ? "s" : ""}
                  </span>
                </div>
                {isExpanded && (
                  <div className="border-t border-border">
                    {docs.length === 0 ? (
                      <p className="px-5 py-4 text-sm text-muted-foreground">No document requirements defined for this partner type.</p>
                    ) : (
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-border bg-muted/20 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                              <th className="px-4 py-2.5">Code</th>
                              <th className="px-4 py-2.5">Description</th>
                              <th className="px-4 py-2.5">Required</th>
                              <th className="px-4 py-2.5">Mandatory</th>
                              <th className="px-4 py-2.5">Order</th>
                              <th className="px-4 py-2.5">Active</th>
                              <th className="px-4 py-2.5">Last Updated</th>
                              <th className="w-20 px-4 py-2.5 text-right">Actions</th>
                            </tr>
                          </thead>
                          <tbody>
                            {docs.map((doc) => {
                              const isEditing = editingId === doc.id
                              return (
                                <tr key={doc.id} className="border-b border-border/50 last:border-b-0">
                                  {isEditing ? (
                                    <>
                                      <td className="px-4 py-2">
                                        <input
                                          value={editForm.code ?? ""}
                                          onChange={(e) => setEditForm((f) => ({ ...f, code: e.target.value }))}
                                          className="w-28 rounded border border-input bg-background px-2 py-1 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
                                        />
                                      </td>
                                      <td className="px-4 py-2">
                                        <input
                                          value={editForm.description ?? ""}
                                          onChange={(e) => setEditForm((f) => ({ ...f, description: e.target.value }))}
                                          className="w-full rounded border border-input bg-background px-2 py-1 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
                                        />
                                      </td>
                                      <td className="px-4 py-2">
                                        <select
                                          value={editForm.isRequired ? "yes" : "no"}
                                          onChange={(e) => setEditForm((f) => ({ ...f, isRequired: e.target.value === "yes" }))}
                                          className="w-20 rounded border border-input bg-background px-2 py-1 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
                                        >
                                          <option value="yes">Yes</option>
                                          <option value="no">No</option>
                                        </select>
                                      </td>
                                      <td className="px-4 py-2">
                                        <select
                                          value={editForm.isMandatory ? "yes" : "no"}
                                          onChange={(e) => setEditForm((f) => ({ ...f, isMandatory: e.target.value === "yes" }))}
                                          className="w-20 rounded border border-input bg-background px-2 py-1 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
                                        >
                                          <option value="yes">Yes</option>
                                          <option value="no">No</option>
                                        </select>
                                      </td>
                                      <td className="px-4 py-2">
                                        <input
                                          type="number"
                                          value={editForm.sortOrder ?? 0}
                                          onChange={(e) => setEditForm((f) => ({ ...f, sortOrder: Number(e.target.value) }))}
                                          className="w-16 rounded border border-input bg-background px-2 py-1 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
                                        />
                                      </td>
                                      <td className="px-4 py-2">
                                        <select
                                          value={editForm.isActive ? "yes" : "no"}
                                          onChange={(e) => setEditForm((f) => ({ ...f, isActive: e.target.value === "yes" }))}
                                          className="w-20 rounded border border-input bg-background px-2 py-1 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
                                        >
                                          <option value="yes">Yes</option>
                                          <option value="no">No</option>
                                        </select>
                                      </td>
                                      <td className="px-4 py-2 text-xs text-muted-foreground">
                                        {doc.updatedAt ? new Date(doc.updatedAt).toLocaleDateString() : "—"}
                                      </td>
                                      <td className="px-4 py-2 text-right">
                                        <div className="flex items-center justify-end gap-1">
                                          <button
                                            onClick={() => handleSave(doc.id)}
                                            disabled={saving}
                                            className="rounded p-1 text-[var(--color-feedback-success)] hover:bg-[var(--color-bg-success-soft)]"
                                            title="Save"
                                          >
                                            <Check className="h-3.5 w-3.5" />
                                          </button>
                                          <button
                                            onClick={() => setEditingId(null)}
                                            className="rounded p-1 text-muted-foreground hover:bg-accent"
                                            title="Cancel"
                                          >
                                            <X className="h-3.5 w-3.5" />
                                          </button>
                                        </div>
                                      </td>
                                    </>
                                  ) : (
                                    <>
                                      <td className="px-4 py-2.5 font-medium text-foreground">{doc.code}</td>
                                      <td className="px-4 py-2.5 text-muted-foreground">{doc.description || "—"}</td>
                                      <td className="px-4 py-2.5">
                                        <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${
                                          doc.isRequired ? "bg-[var(--color-bg-success-soft)] text-[var(--color-text-success-soft)]" : "bg-[var(--color-bg-warning-soft)] text-[var(--color-text-warning-soft)]"
                                        }`}>
                                          {doc.isRequired ? "Required" : "Optional"}
                                        </span>
                                      </td>
                                      <td className="px-4 py-2.5">
                                        <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${
                                          doc.isMandatory ? "bg-[var(--color-bg-destructive-soft)] text-[var(--color-text-destructive-soft)]" : "bg-[var(--color-bg-warning-soft)] text-[var(--color-text-warning-soft)]"
                                        }`}>
                                          {doc.isMandatory ? "Mandatory" : "Optional"}
                                        </span>
                                      </td>
                                      <td className="px-4 py-2.5 text-xs text-muted-foreground">{doc.sortOrder}</td>
                                      <td className="px-4 py-2.5">
                                        <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${
                                          doc.isActive ? "bg-[var(--color-bg-success-soft)] text-[var(--color-text-success-soft)]" : "bg-[var(--color-bg-destructive-soft)] text-[var(--color-text-destructive-soft)]"
                                        }`}>
                                          {doc.isActive ? "Active" : "Inactive"}
                                        </span>
                                      </td>
                                      <td className="px-4 py-2.5 text-xs text-muted-foreground">
                                        {doc.updatedAt ? new Date(doc.updatedAt).toLocaleDateString() : "—"}
                                      </td>
                                      <td className="px-4 py-2.5 text-right">
                                        <div className="flex items-center justify-end gap-1">
                                          <button onClick={() => startEdit(doc)} className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-accent" title="Edit">
                                            <Pencil className="h-3.5 w-3.5" />
                                          </button>
                                          <button onClick={() => handleDelete(doc.id)} className="rounded p-1 text-muted-foreground hover:text-destructive hover:bg-destructive/10" title="Delete">
                                            <Trash2 className="h-3.5 w-3.5" />
                                          </button>
                                        </div>
                                      </td>
                                    </>
                                  )}
                                </tr>
                              )
                            })}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

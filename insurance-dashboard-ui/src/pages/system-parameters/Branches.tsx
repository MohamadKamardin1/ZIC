import { useEffect, useState, useCallback, useMemo } from "react"
import { Plus, Pencil, Trash2, Check, X, Loader2, Search as SearchIcon } from "lucide-react"
import { PageHeader } from "./SharedComponents"
import { fetchBranches, createBranchRecord, updateBranchRecord, deleteBranchRecord } from "../../lib/api"
import { SkeletonTable } from "../../components/shared/Skeleton"
import { emitDataChange, useDataRefresh } from "../../lib/useDataRefresh"
import type { BranchRecord } from "../../lib/types"

export default function Branches() {
  const [items, setItems] = useState<BranchRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState({ code: "", name: "", isActive: true })
  const [adding, setAdding] = useState(false)
  const [saving, setSaving] = useState(false)
  const [search, setSearch] = useState("")
  const refreshKey = useDataRefresh("branches")

  const filtered = useMemo(
    () => items.filter(
      (b) => !search || b.code.toLowerCase().includes(search.toLowerCase()) || b.name.toLowerCase().includes(search.toLowerCase()),
    ),
    [items, search],
  )

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setItems(await fetchBranches())
    } finally {
      setLoading(false)
    }
  }, [refreshKey])

  useEffect(() => { load() }, [load])

  async function handleSave(id?: string) {
    setSaving(true)
    try {
      if (id) {
        await updateBranchRecord(id, form)
      } else {
        await createBranchRecord(form)
      }
      setEditingId(null)
      setAdding(false)
      setForm({ code: "", name: "", isActive: true })
      emitDataChange("branches")
      await load()
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id: string) {
    if (!window.confirm("Delete this branch?")) return
    await deleteBranchRecord(id)
    emitDataChange("branches")
    await load()
  }

  function startEdit(item: BranchRecord) {
    setEditingId(item.id)
    setForm({ code: item.code, name: item.name, isActive: item.isActive })
    setAdding(false)
  }

  function startAdd() {
    setAdding(true)
    setEditingId(null)
    setForm({ code: "", name: "", isActive: true })
  }

  function cancel() {
    setEditingId(null)
    setAdding(false)
  }

  if (loading) {
    return <SkeletonTable rows={5} cols={4} />
  }

  return (
    <div>
      <PageHeader title="Branches" description="Manage branch offices">
        <button onClick={startAdd} className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition">
          <Plus className="h-4 w-4" />
          Add Branch
        </button>
      </PageHeader>

      {adding && (
        <div className="mb-4 rounded-lg border border-border bg-card p-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-muted-foreground">Code *</label>
              <input
                className="w-full rounded border border-input bg-background px-2 py-1.5 text-sm font-mono"
                value={form.code}
                onChange={e => setForm({ ...form, code: e.target.value.toUpperCase() })}
                placeholder="HQ"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-muted-foreground">Name *</label>
              <input
                className="w-full rounded border border-input bg-background px-2 py-1.5 text-sm"
                value={form.name}
                onChange={e => setForm({ ...form, name: e.target.value })}
                placeholder="Head Office"
              />
            </div>
            <div className="flex items-end gap-4">
              <label className="flex items-center gap-1.5 text-sm pb-1.5">
                <input type="checkbox" checked={form.isActive} onChange={e => setForm({ ...form, isActive: e.target.checked })} />
                Active
              </label>
            </div>
          </div>
          <div className="mt-3 flex justify-end gap-2">
            <button onClick={cancel} className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium hover:bg-secondary">
              Cancel
            </button>
            <button
              onClick={() => handleSave()}
              disabled={saving || !form.code || !form.name}
              className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
              Save
            </button>
          </div>
        </div>
      )}

      {/* Search */}
      {!adding && items.length > 0 && (
        <div className="mb-3">
          <div className="relative max-w-xs">
            <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search branches..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full rounded-lg border border-input bg-card py-1.5 pl-9 pr-3 text-sm text-foreground outline-none placeholder:text-muted-foreground focus:ring-2 focus:ring-ring/40"
            />
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {filtered.length} of {items.length} branches
          </p>
        </div>
      )}

      <div className="overflow-hidden rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/50 text-left">
              <th className="px-4 py-2.5 text-xs font-medium text-muted-foreground">Code</th>
              <th className="px-4 py-2.5 text-xs font-medium text-muted-foreground">Name</th>
              <th className="px-4 py-2.5 text-xs font-medium text-muted-foreground">Active</th>
              <th className="w-20 px-4 py-2.5 text-right text-xs font-medium text-muted-foreground">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-sm text-muted-foreground">
                  {search ? "No branches match your search." : "No branches defined."}
                </td>
              </tr>
            )}
            {filtered.map(item =>
              editingId === item.id ? (
                <tr key={item.id} className="border-b border-border/50">
                  <td className="px-4 py-2">
                    <input className="w-24 rounded border border-input bg-background px-2 py-1 font-mono text-xs" value={form.code} onChange={e => setForm({ ...form, code: e.target.value.toUpperCase() })} />
                  </td>
                  <td className="px-4 py-2">
                    <input className="w-56 rounded border border-input bg-background px-2 py-1 text-sm" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
                  </td>
                  <td className="px-4 py-2">
                    <input type="checkbox" checked={form.isActive} onChange={e => setForm({ ...form, isActive: e.target.checked })} />
                  </td>
                  <td className="px-4 py-2 text-right">
                    <button onClick={() => handleSave(item.id)} disabled={saving} className="mr-1 rounded p-1 text-success hover:bg-success/10"><Check className="h-4 w-4" /></button>
                    <button onClick={cancel} className="rounded p-1 text-muted-foreground hover:bg-secondary"><X className="h-4 w-4" /></button>
                  </td>
                </tr>
              ) : (
                <tr key={item.id} className="border-b border-border/50 hover:bg-muted/30">
                  <td className="px-4 py-2 font-mono text-xs text-muted-foreground">{item.code}</td>
                  <td className="px-4 py-2 font-medium">{item.name}</td>
                  <td className="px-4 py-2">{item.isActive ? <span className="text-success">Yes</span> : <span className="text-muted-foreground">No</span>}</td>
                  <td className="px-4 py-2 text-right">
                    <button onClick={() => startEdit(item)} className="mr-1 rounded p-1 text-muted-foreground hover:bg-secondary"><Pencil className="h-4 w-4" /></button>
                    <button onClick={() => handleDelete(item.id)} className="rounded p-1 text-destructive hover:bg-destructive/10"><Trash2 className="h-4 w-4" /></button>
                  </td>
                </tr>
              )
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

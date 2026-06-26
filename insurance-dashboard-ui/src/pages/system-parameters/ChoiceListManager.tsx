import { useEffect, useState, useCallback } from "react"
import {
  Plus,
  Pencil,
  Trash2,
  Save,
  X,
  AlertCircle,
  Check,
  Loader2,
} from "lucide-react"
import {
  listChoiceLists,
  createChoiceList,
  updateChoiceList,
  deleteChoiceList,
  listChoiceOptions,
  createChoiceOption,
  updateChoiceOption,
  deleteChoiceOption,
  clearGroupCache,
} from "../../lib/api"
import { SkeletonTable } from "../../components/shared/Skeleton"
import { useDataRefresh } from "../../lib/useDataRefresh"
import type { ChoiceList, ChoiceOption } from "../../lib/types"

interface ChoiceListManagerProps {
  title?: string
  description?: string
}

export default function ChoiceListManager({ title, description }: ChoiceListManagerProps) {
  const [lists, setLists] = useState<ChoiceList[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [selectedListId, setSelectedListId] = useState<string | null>(null)
  const [options, setOptions] = useState<ChoiceOption[]>([])
  const [optionsLoading, setOptionsLoading] = useState(false)

  // New list form
  const [showNewList, setShowNewList] = useState(false)
  const [newListCode, setNewListCode] = useState("")
  const [newListName, setNewListName] = useState("")

  // Edit list
  const [editingListId, setEditingListId] = useState<string | null>(null)
  const [editListCode, setEditListCode] = useState("")
  const [editListName, setEditListName] = useState("")

  // New option
  const [showNewOption, setShowNewOption] = useState(false)
  const [newOptCode, setNewOptCode] = useState("")
  const [newOptLabel, setNewOptLabel] = useState("")

  // Edit option
  const [editingOptId, setEditingOptId] = useState<string | null>(null)
  const [editOptCode, setEditOptCode] = useState("")
  const [editOptLabel, setEditOptLabel] = useState("")

  const [saving, setSaving] = useState(false)
  const refreshKey = useDataRefresh("choice-lists")

  const loadLists = useCallback(async () => {
    setLoading(true)
    setError("")
    try {
      const data = await listChoiceLists()
      setLists(data)
      if (!selectedListId && data.length > 0) {
        setSelectedListId(data[0].id)
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load choice lists")
    } finally {
      setLoading(false)
    }
  }, [selectedListId, refreshKey])

  useEffect(() => {
    loadLists()
  }, [loadLists])

  const loadOptions = useCallback(async (listId: string) => {
    setOptionsLoading(true)
    try {
      const data = await listChoiceOptions(listId)
      setOptions(data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load options")
    } finally {
      setOptionsLoading(false)
    }
  }, [])

  useEffect(() => {
    if (selectedListId) {
      loadOptions(selectedListId)
    }
  }, [selectedListId, loadOptions])

  const selectedList = lists.find((l) => l.id === selectedListId)

  // --- List CRUD ---

  async function handleCreateList() {
    if (!newListCode) { setError("Code is required"); return }
    setSaving(true)
    setError("")
    try {
      await createChoiceList({ code: newListCode, name: newListName || newListCode } as Record<string, unknown>)
      setShowNewList(false)
      setNewListCode("")
      setNewListName("")
      clearGroupCache()
      await loadLists()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create")
    } finally {
      setSaving(false)
    }
  }

  async function handleUpdateList(id: string) {
    setSaving(true)
    setError("")
    try {
      await updateChoiceList(id, { code: editListCode, name: editListName } as Record<string, unknown>)
      setEditingListId(null)
      clearGroupCache()
      await loadLists()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to update")
    } finally {
      setSaving(false)
    }
  }

  async function handleDeleteList(id: string) {
    if (!window.confirm("Delete this choice list and all its options?")) return
    try {
      await deleteChoiceList(id)
      if (selectedListId === id) {
        setSelectedListId(null)
        setOptions([])
      }
      clearGroupCache()
      await loadLists()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to delete")
    }
  }

  // --- Option CRUD ---

  async function handleCreateOption() {
    if (!newOptCode || !selectedListId) { setError("Code is required"); return }
    setSaving(true)
    setError("")
    try {
      await createChoiceOption({
        choice_list: selectedListId,
        code: newOptCode,
        label: newOptLabel || newOptCode,
        sort_order: (options.length + 1) * 10,
      } as Record<string, unknown>)
      setShowNewOption(false)
      setNewOptCode("")
      setNewOptLabel("")
      await loadOptions(selectedListId)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create option")
    } finally {
      setSaving(false)
    }
  }

  async function handleUpdateOption(id: string) {
    setSaving(true)
    setError("")
    try {
      await updateChoiceOption(id, { code: editOptCode, label: editOptLabel } as Record<string, unknown>)
      setEditingOptId(null)
      if (selectedListId) await loadOptions(selectedListId)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to update option")
    } finally {
      setSaving(false)
    }
  }

  async function handleDeleteOption(id: string) {
    if (!window.confirm("Delete this option?")) return
    try {
      await deleteChoiceOption(id)
      if (selectedListId) await loadOptions(selectedListId)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to delete option")
    }
  }

  if (loading) {
    return (
      <div className="grid gap-5 lg:grid-cols-[280px_1fr]">
        <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
          <div className="mb-3 flex items-center justify-between">
            <div className="h-3 w-16 animate-pulse rounded bg-muted-foreground/15" />
            <div className="h-7 w-14 animate-pulse rounded-lg bg-muted-foreground/15" />
          </div>
          <div className="space-y-1">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-9 animate-pulse rounded-md bg-muted-foreground/15" />
            ))}
          </div>
        </div>
        <SkeletonTable rows={5} cols={3} />
      </div>
    )
  }

  return (
    <div>
      {title && <h2 className="mb-1 text-base font-semibold">{title}</h2>}
      {description && <p className="mb-4 text-xs text-muted-foreground">{description}</p>}

      {error && (
        <div className="mb-4 flex items-center gap-2 rounded-lg bg-destructive/10 px-4 py-2 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 flex-none" />
          {error}
          <button onClick={() => setError("")} className="ml-auto"><X className="h-4 w-4" /></button>
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-[280px_1fr]">
        {/* Left panel: list of choice lists */}
        <div>
          <div className="mb-3 flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground">{lists.length} lists</span>
            <button
              onClick={() => setShowNewList(true)}
              className="inline-flex items-center gap-1 rounded-lg bg-primary px-2.5 py-1 text-xs font-medium text-primary-foreground hover:bg-primary/90"
            >
              <Plus className="h-3 w-3" /> New
            </button>
          </div>

          {/* New list form */}
          {showNewList && (
            <div className="mb-3 rounded-lg border border-border bg-card p-3">
              <input
                type="text"
                value={newListCode}
                onChange={(e) => setNewListCode(e.target.value)}
                placeholder="Code"
                className="mb-2 w-full rounded border border-input bg-background px-2 py-1.5 text-xs font-mono"
              />
              <input
                type="text"
                value={newListName}
                onChange={(e) => setNewListName(e.target.value)}
                placeholder="Name (optional)"
                className="mb-2 w-full rounded border border-input bg-background px-2 py-1.5 text-xs"
              />
              <div className="flex justify-end gap-1.5">
                <button onClick={() => setShowNewList(false)} className="rounded px-2 py-1 text-xs hover:bg-secondary">Cancel</button>
                <button onClick={handleCreateList} disabled={saving || !newListCode} className="rounded bg-primary px-2 py-1 text-xs text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
                  {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : "Create"}
                </button>
              </div>
            </div>
          )}

          <div className="space-y-1">
            {lists.map((list) => {
              const editing = editingListId === list.id
              return (
                <div key={list.id}>
                  <button
                    onClick={() => setSelectedListId(list.id)}
                    className={`w-full rounded-lg px-3 py-2 text-left text-sm transition ${
                      selectedListId === list.id
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:bg-secondary"
                    }`}
                  >
                    {editing ? (
                      <div className="space-y-1" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="text"
                          value={editListCode}
                          onChange={(e) => setEditListCode(e.target.value)}
                          className="w-full rounded border border-input bg-background px-2 py-1 text-xs font-mono text-foreground"
                        />
                        <input
                          type="text"
                          value={editListName}
                          onChange={(e) => setEditListName(e.target.value)}
                          className="w-full rounded border border-input bg-background px-2 py-1 text-xs text-foreground"
                        />
                        <div className="flex justify-end gap-1 pt-1">
                          <button onClick={() => setEditingListId(null)} className="rounded px-1.5 py-0.5 text-xs hover:bg-secondary/50">
                            <X className="h-3 w-3" />
                          </button>
                          <button onClick={() => handleUpdateList(list.id)} disabled={saving} className="rounded px-1.5 py-0.5 text-xs hover:bg-secondary/50">
                            {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="text-sm font-medium truncate">{list.code}</div>
                          <div className={`text-xs ${selectedListId === list.id ? "text-primary-foreground/70" : "text-muted-foreground"}`}>
                            {list.options?.length ?? "—"} options
                          </div>
                        </div>
                        <div className="flex gap-0.5" onClick={(e) => e.stopPropagation()}>
                          <button
                            onClick={() => {
                              setEditingListId(list.id)
                              setEditListCode(list.code)
                              setEditListName(list.name)
                            }}
                            className={`rounded p-0.5 ${selectedListId === list.id ? "hover:bg-primary-foreground/20" : "hover:bg-secondary"}`}
                          >
                            <Pencil className="h-3 w-3" />
                          </button>
                          <button
                            onClick={() => handleDeleteList(list.id)}
                            className={`rounded p-0.5 ${selectedListId === list.id ? "hover:bg-primary-foreground/20" : "hover:bg-secondary"}`}
                          >
                            <Trash2 className="h-3 w-3" />
                          </button>
                        </div>
                      </div>
                    )}
                  </button>
                </div>
              )
            })}
            {lists.length === 0 && (
              <p className="py-4 text-center text-xs text-muted-foreground">No choice lists yet.</p>
            )}
          </div>
        </div>

        {/* Right panel: options for selected list */}
        <div>
          {selectedList ? (
            <div>
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-base font-semibold">{selectedList.code} — Options</h3>
                <button
                  onClick={() => { setShowNewOption(true); setNewOptCode(""); setNewOptLabel("") }}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90"
                >
                  <Plus className="h-3.5 w-3.5" />
                  Add Option
                </button>
              </div>

              {showNewOption && (
                <div className="mb-3 rounded-lg border border-border bg-card p-3">
                  <div className="grid gap-2 sm:grid-cols-2">
                    <input
                      type="text"
                      value={newOptCode}
                      onChange={(e) => setNewOptCode(e.target.value)}
                      placeholder="Code"
                      className="rounded border border-input bg-background px-2 py-1.5 text-xs font-mono"
                    />
                    <input
                      type="text"
                      value={newOptLabel}
                      onChange={(e) => setNewOptLabel(e.target.value)}
                      placeholder="Label"
                      className="rounded border border-input bg-background px-2 py-1.5 text-xs"
                    />
                  </div>
                  <div className="mt-2 flex justify-end gap-1.5">
                    <button onClick={() => setShowNewOption(false)} className="rounded px-2 py-1 text-xs hover:bg-secondary">Cancel</button>
                    <button onClick={handleCreateOption} disabled={saving || !newOptCode} className="rounded bg-primary px-2 py-1 text-xs text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
                      {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : "Add"}
                    </button>
                  </div>
                </div>
              )}

              {optionsLoading ? (
                <SkeletonTable rows={4} cols={3} />
              ) : (
                <div className="overflow-hidden rounded-lg border border-border">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border bg-secondary/50">
                        <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Code</th>
                        <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Label</th>
                        <th className="w-16 px-3 py-2 text-right text-xs font-medium text-muted-foreground">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {options.length === 0 && (
                        <tr>
                          <td colSpan={3} className="px-4 py-8 text-center text-sm text-muted-foreground">
                            No options yet. Click "Add Option".
                          </td>
                        </tr>
                      )}
                      {options.map((opt) => {
                        const editing = editingOptId === opt.id
                        return (
                          <tr key={opt.id} className="border-b border-border last:border-0 hover:bg-secondary/20">
                            <td className="px-3 py-2">
                              {editing ? (
                                <input
                                  type="text"
                                  value={editOptCode}
                                  onChange={(e) => setEditOptCode(e.target.value)}
                                  className="w-32 rounded border border-input bg-background px-2 py-1 font-mono text-xs"
                                />
                              ) : (
                                <span className="font-mono text-xs text-muted-foreground">{opt.code}</span>
                              )}
                            </td>
                            <td className="px-3 py-2">
                              {editing ? (
                                <input
                                  type="text"
                                  value={editOptLabel}
                                  onChange={(e) => setEditOptLabel(e.target.value)}
                                  className="w-full rounded border border-input bg-background px-2 py-1 text-sm"
                                />
                              ) : (
                                <span>{opt.label}</span>
                              )}
                            </td>
                            <td className="px-3 py-2 text-right">
                              {editing ? (
                                <div className="inline-flex gap-1">
                                  <button onClick={() => handleUpdateOption(opt.id)} disabled={saving} className="rounded p-1 text-primary hover:bg-primary/10">
                                    {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
                                  </button>
                                  <button onClick={() => setEditingOptId(null)} className="rounded p-1 text-muted-foreground hover:bg-secondary">
                                    <X className="h-3.5 w-3.5" />
                                  </button>
                                </div>
                              ) : (
                                <div className="inline-flex gap-1">
                                  <button
                                    onClick={() => { setEditingOptId(opt.id); setEditOptCode(opt.code); setEditOptLabel(opt.label) }}
                                    className="rounded p-1 text-muted-foreground hover:text-foreground"
                                  >
                                    <Pencil className="h-3.5 w-3.5" />
                                  </button>
                                  <button onClick={() => handleDeleteOption(opt.id)} className="rounded p-1 text-muted-foreground hover:text-destructive">
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
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">
              Select a choice list to manage its options
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

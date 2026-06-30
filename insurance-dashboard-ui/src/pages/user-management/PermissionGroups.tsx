import { useEffect, useState } from "react"
import { Loader2, Plus, Edit2, Trash2, Shield, FolderGit2, Search, X } from "lucide-react"
import { listPermissionGroups, createPermissionGroup, updatePermissionGroup, deletePermissionGroup } from "../../lib/api"

interface PermissionGroupRecord {
  id: string
  name: string
  module_code: string
  description: string
}

export default function PermissionGroups() {
  const [groups, setGroups] = useState<PermissionGroupRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")

  // Modals state
  const [showAddModal, setShowAddModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [selectedGroup, setSelectedGroup] = useState<PermissionGroupRecord | null>(null)

  // Form state
  const [formData, setFormData] = useState({ name: "", module_code: "", description: "" })
  const [submitting, setSubmitting] = useState(false)

  const fetchGroups = async () => {
    try {
      setLoading(true)
      const data = await listPermissionGroups()
      setGroups(data)
      setError(null)
    } catch (err: any) {
      setError(err.message ?? "Failed to fetch permission groups")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchGroups()
  }, [])

  const handleOpenAdd = () => {
    setFormData({ name: "", module_code: "", description: "" })
    setShowAddModal(true)
  }

  const handleOpenEdit = (group: PermissionGroupRecord) => {
    setSelectedGroup(group)
    setFormData({
      name: group.name,
      module_code: group.module_code,
      description: group.description || "",
    })
    setShowEditModal(true)
  }

  const handleAddGroup = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.name || !formData.module_code) return
    try {
      setSubmitting(true)
      await createPermissionGroup({
        name: formData.name,
        module_code: formData.module_code.toUpperCase(),
        description: formData.description,
      })
      setShowAddModal(false)
      fetchGroups()
    } catch (err: any) {
      alert(err.message ?? "Failed to create permission group")
    } finally {
      setSubmitting(false)
    }
  }

  const handleEditGroup = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedGroup || !formData.name || !formData.module_code) return
    try {
      setSubmitting(true)
      await updatePermissionGroup(selectedGroup.id, {
        name: formData.name,
        module_code: formData.module_code.toUpperCase(),
        description: formData.description,
      })
      setShowEditModal(false)
      fetchGroups()
    } catch (err: any) {
      alert(err.message ?? "Failed to update permission group")
    } finally {
      setSubmitting(false)
    }
  }

  const handleDeleteGroup = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to delete the permission group "${name}"?`)) return
    try {
      await deletePermissionGroup(id)
      fetchGroups()
    } catch (err: any) {
      alert(err.message ?? "Failed to delete permission group")
    }
  }

  const filteredGroups = groups.filter(g =>
    g.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    g.module_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
    g.description?.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <FolderGit2 className="h-6 w-6 text-primary" /> Permission Groups
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Configure logical permission groups and module boundaries in the system.
          </p>
        </div>
        <button
          onClick={handleOpenAdd}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-sm hover:bg-primary/90 transition-all cursor-pointer"
        >
          <Plus className="h-4 w-4" /> Add Group
        </button>
      </div>

      {/* Stats / Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border border-border bg-card/50 backdrop-blur-md flex items-center gap-4">
          <div className="p-3 rounded-lg bg-primary/10 text-primary">
            <FolderGit2 className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Total Groups</p>
            <p className="text-2xl font-bold text-foreground">{groups.length}</p>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="rounded-xl border border-border bg-card shadow-sm overflow-hidden">
        {/* Toolbar */}
        <div className="p-4 border-b border-border bg-card/50 flex flex-col sm:flex-row items-center gap-4">
          <div className="relative flex-1 w-full">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search groups by name, module code, or description..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
            />
          </div>
        </div>

        {/* Loading / Error States */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 text-muted-foreground gap-3">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="text-sm">Fetching permission groups...</p>
          </div>
        ) : error ? (
          <div className="p-6 text-center">
            <p className="text-sm text-destructive font-medium">{error}</p>
            <button onClick={fetchGroups} className="mt-4 text-xs font-semibold text-primary underline">Try Again</button>
          </div>
        ) : filteredGroups.length === 0 ? (
          <div className="py-20 text-center text-muted-foreground">
            <Shield className="h-10 w-10 mx-auto text-muted-foreground/50 mb-3" />
            <p className="text-sm font-medium">No permission groups found</p>
            <p className="text-xs mt-1">Try resetting your search query or add a new group.</p>
          </div>
        ) : (
          /* Table */
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-muted/40 border-b border-border text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  <th className="p-4 font-semibold">Group Name</th>
                  <th className="p-4 font-semibold">Module Code</th>
                  <th className="p-4 font-semibold">Description</th>
                  <th className="p-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border text-sm">
                {filteredGroups.map((group) => (
                  <tr key={group.id} className="hover:bg-muted/20 transition-colors">
                    <td className="p-4 font-medium text-foreground">{group.name}</td>
                    <td className="p-4">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-primary/10 text-primary uppercase">
                        {group.module_code}
                      </span>
                    </td>
                    <td className="p-4 text-muted-foreground max-w-xs truncate">{group.description || "—"}</td>
                    <td className="p-4 text-right space-x-2">
                      <button
                        onClick={() => handleOpenEdit(group)}
                        className="inline-flex items-center justify-center p-2 rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground transition-all cursor-pointer"
                        title="Edit Group"
                      >
                        <Edit2 className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDeleteGroup(group.id, group.name)}
                        className="inline-flex items-center justify-center p-2 rounded-lg text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-all cursor-pointer"
                        title="Delete Group"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="bg-card border border-border w-full max-w-md rounded-2xl shadow-xl overflow-hidden animate-in fade-in zoom-in duration-200">
            <div className="p-6 border-b border-border flex items-center justify-between">
              <h2 className="text-lg font-bold text-foreground">Add Permission Group</h2>
              <button onClick={() => setShowAddModal(false)} className="text-muted-foreground hover:text-foreground p-1 rounded-lg hover:bg-muted cursor-pointer">
                <X className="h-5 w-5" />
              </button>
            </div>
            <form onSubmit={handleAddGroup} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1">Group Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Partner Management"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all text-foreground"
                />
              </div>
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1">Module Code</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. PARTNERS"
                  value={formData.module_code}
                  onChange={(e) => setFormData({ ...formData, module_code: e.target.value })}
                  className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all text-foreground uppercase"
                />
              </div>
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1">Description</label>
                <textarea
                  placeholder="Describe the scope of this module boundary..."
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all text-foreground h-24 resize-none"
                />
              </div>
              <div className="flex items-center justify-end gap-3 pt-2 border-t border-border mt-4">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 text-sm font-semibold rounded-lg border border-border hover:bg-muted text-foreground transition-all cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-all cursor-pointer"
                >
                  {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
                  Save Group
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {showEditModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="bg-card border border-border w-full max-w-md rounded-2xl shadow-xl overflow-hidden animate-in fade-in zoom-in duration-200">
            <div className="p-6 border-b border-border flex items-center justify-between">
              <h2 className="text-lg font-bold text-foreground">Edit Permission Group</h2>
              <button onClick={() => setShowEditModal(false)} className="text-muted-foreground hover:text-foreground p-1 rounded-lg hover:bg-muted cursor-pointer">
                <X className="h-5 w-5" />
              </button>
            </div>
            <form onSubmit={handleEditGroup} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1">Group Name</label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all text-foreground"
                />
              </div>
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1">Module Code</label>
                <input
                  type="text"
                  required
                  value={formData.module_code}
                  onChange={(e) => setFormData({ ...formData, module_code: e.target.value })}
                  className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all text-foreground uppercase"
                />
              </div>
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1">Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all text-foreground h-24 resize-none"
                />
              </div>
              <div className="flex items-center justify-end gap-3 pt-2 border-t border-border mt-4">
                <button
                  type="button"
                  onClick={() => setShowEditModal(false)}
                  className="px-4 py-2 text-sm font-semibold rounded-lg border border-border hover:bg-muted text-foreground transition-all cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-all cursor-pointer"
                >
                  {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

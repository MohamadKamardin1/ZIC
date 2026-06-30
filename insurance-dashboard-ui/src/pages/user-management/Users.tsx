import { useEffect, useState } from "react"
import { 
  Loader2, User, Plus, Edit2, Trash2, Search, Filter, 
  X, Check, AlertCircle, ShieldAlert, UserCheck, UserX 
} from "lucide-react"
import { 
  listUsers, createUser, updateUser, deleteUser, 
  activateUser, deactivateUser, listUserGroups 
} from "../../lib/api"

interface UserRecord {
  id: string
  username: string
  email: string
  firstName: string
  lastName: string
  fullName: string
  phoneNumber: string
  userType: string
  isActive: boolean
  isApproved: boolean
  department: string
  jobTitle: string
  employeeId: string
  groups: string[] | any[]
}

interface GroupRecord {
  id: string
  name: string
  code: string
  description: string
}

export default function Users() {
  const [users, setUsers] = useState<UserRecord[]>([])
  const [groups, setGroups] = useState<GroupRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Search & Filters
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedGroup, setSelectedGroup] = useState("")
  const [selectedStatus, setSelectedStatus] = useState("")
  const [page, setPage] = useState(1)
  const [totalCount, setTotalCount] = useState(0)

  // Modals state
  const [showAddModal, setShowAddModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [selectedUser, setSelectedUser] = useState<UserRecord | null>(null)

  // Form states (internal UI states can be snake_case or camelCase, we keep them simple and map them when posting)
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    firstName: "",
    lastName: "",
    password: "",
    passwordConfirm: "",
    phoneNumber: "",
    userType: "PORTAL_USER",
    department: "",
    jobTitle: "",
    employeeId: "",
    groupIds: [] as string[]
  })
  
  const [submitting, setSubmitting] = useState(false)

  const fetchUsers = async () => {
    try {
      setLoading(true)
      const isActiveFilter = selectedStatus === "active" ? true : selectedStatus === "inactive" ? false : undefined
      const data = await listUsers({
        page,
        pageSize: 10,
        search: searchQuery || undefined,
        group: selectedGroup || undefined,
        is_active: isActiveFilter
      })
      setUsers(data.results)
      setTotalCount(data.count)
      setError(null)
    } catch (err: any) {
      setError(err.message ?? "Failed to fetch users list")
    } finally {
      setLoading(false)
    }
  }

  const fetchGroups = async () => {
    try {
      const data = await listUserGroups()
      setGroups(data)
    } catch (err) {
      console.error("Failed to fetch user groups:", err)
    }
  }

  useEffect(() => {
    fetchUsers()
  }, [page, selectedGroup, selectedStatus])

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
    fetchUsers()
  }

  useEffect(() => {
    fetchGroups()
  }, [])

  const handleOpenAdd = () => {
    setFormData({
      username: "",
      email: "",
      firstName: "",
      lastName: "",
      password: "",
      passwordConfirm: "",
      phoneNumber: "",
      userType: "PORTAL_USER",
      department: "",
      jobTitle: "",
      employeeId: "",
      groupIds: []
    })
    setShowAddModal(true)
  }

  const handleOpenEdit = (user: UserRecord) => {
    setSelectedUser(user)
    
    // Resolve group IDs from groups list matching names
    const userGroupNames = Array.isArray(user.groups) 
      ? user.groups.map(g => typeof g === "object" ? g.name : g)
      : []

    const matchedGroupIds = groups
      .filter(g => userGroupNames.includes(g.name))
      .map(g => g.id)

    setFormData({
      username: user.username,
      email: user.email,
      firstName: user.firstName || "",
      lastName: user.lastName || "",
      password: "",
      passwordConfirm: "",
      phoneNumber: user.phoneNumber || "",
      userType: user.userType || "PORTAL_USER",
      department: user.department || "",
      jobTitle: user.jobTitle || "",
      employeeId: user.employeeId || "",
      groupIds: matchedGroupIds
    })
    setShowEditModal(true)
  }

  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault()
    if (formData.password !== formData.passwordConfirm) {
      alert("Passwords do not match!")
      return
    }
    try {
      setSubmitting(true)
      await createUser({
        username: formData.username,
        email: formData.email,
        password: formData.password,
        passwordConfirm: formData.passwordConfirm,
        firstName: formData.firstName,
        lastName: formData.lastName,
        phoneNumber: formData.phoneNumber,
        userType: formData.userType,
        department: formData.department,
        jobTitle: formData.jobTitle,
        employeeId: formData.employeeId,
        groupIds: formData.groupIds
      })
      setShowAddModal(false)
      fetchUsers()
    } catch (err: any) {
      alert(err.message ?? "Failed to create user")
    } finally {
      setSubmitting(false)
    }
  }

  const handleEditUser = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedUser) return
    try {
      setSubmitting(true)
      await updateUser(selectedUser.id, {
        firstName: formData.firstName,
        lastName: formData.lastName,
        phoneNumber: formData.phoneNumber,
        userType: formData.userType,
        department: formData.department,
        jobTitle: formData.jobTitle,
        employeeId: formData.employeeId,
        groupIds: formData.groupIds
      })
      setShowEditModal(false)
      fetchUsers()
    } catch (err: any) {
      alert(err.message ?? "Failed to update user")
    } finally {
      setSubmitting(false)
    }
  }

  const handleDeleteUser = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to delete user "${name}"?`)) return
    try {
      await deleteUser(id)
      fetchUsers()
    } catch (err: any) {
      alert(err.message ?? "Failed to delete user")
    }
  }

  const handleToggleActiveStatus = async (user: UserRecord) => {
    const action = user.isActive ? "deactivate" : "activate"
    if (!confirm(`Are you sure you want to ${action} user "${user.fullName || user.username}"?`)) return
    try {
      if (user.isActive) {
        await deactivateUser(user.id)
      } else {
        await activateUser(user.id)
      }
      fetchUsers()
    } catch (err: any) {
      alert(err.message ?? `Failed to ${action} user`)
    }
  }

  const handleGroupSelectToggle = (groupId: string) => {
    setFormData(prev => {
      const selected = prev.groupIds.includes(groupId)
        ? prev.groupIds.filter(id => id !== groupId)
        : [...prev.groupIds, groupId]
      return { ...prev, groupIds: selected }
    })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <User className="h-6 w-6 text-primary" /> Users Directory
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage system operators, Portal users, Quotations clerks, and Underwriter accounts.
          </p>
        </div>
        <button
          onClick={handleOpenAdd}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-sm hover:bg-primary/90 transition-all cursor-pointer"
        >
          <Plus className="h-4 w-4" /> Add User
        </button>
      </div>

      {/* Main List Box */}
      <div className="rounded-xl border border-border bg-card shadow-sm overflow-hidden">
        {/* Filters */}
        <form onSubmit={handleSearchSubmit} className="p-4 border-b border-border bg-card/50 flex flex-col md:flex-row items-center gap-4">
          <div className="relative flex-1 w-full">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search by username, email, name, or phone..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all text-foreground"
            />
          </div>

          <div className="flex flex-wrap items-center gap-4 w-full md:w-auto">
            {/* Group Filter */}
            <select
              value={selectedGroup}
              onChange={(e) => { setSelectedGroup(e.target.value); setPage(1); }}
              className="px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary text-foreground"
            >
              <option value="">All Roles</option>
              {groups.map(g => (
                <option key={g.id} value={g.name}>{g.name}</option>
              ))}
            </select>

            {/* Status Filter */}
            <select
              value={selectedStatus}
              onChange={(e) => { setSelectedStatus(e.target.value); setPage(1); }}
              className="px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary text-foreground"
            >
              <option value="">All Statuses</option>
              <option value="active">Active Only</option>
              <option value="inactive">Inactive Only</option>
            </select>

            <button
              type="submit"
              className="px-4 py-2 text-sm font-semibold rounded-lg bg-secondary text-secondary-foreground hover:bg-secondary/80 transition-all cursor-pointer"
            >
              Search
            </button>
          </div>
        </form>

        {/* Loading / Error States */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 text-muted-foreground gap-3">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="text-sm">Fetching users directory...</p>
          </div>
        ) : error ? (
          <div className="p-6 text-center">
            <p className="text-sm text-destructive font-medium">{error}</p>
            <button onClick={fetchUsers} className="mt-4 text-xs font-semibold text-primary underline">Try Again</button>
          </div>
        ) : users.length === 0 ? (
          <div className="py-20 text-center text-muted-foreground">
            <User className="h-10 w-10 mx-auto text-muted-foreground/50 mb-3" />
            <p className="text-sm font-medium">No users found</p>
            <p className="text-xs mt-1 font-normal">No user records matched your criteria.</p>
          </div>
        ) : (
          /* Table */
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-muted/40 border-b border-border text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  <th className="p-4 font-semibold">Username / Email</th>
                  <th className="p-4 font-semibold">Full Name</th>
                  <th className="p-4 font-semibold">User Type</th>
                  <th className="p-4 font-semibold">Roles / Groups</th>
                  <th className="p-4 font-semibold">Status</th>
                  <th className="p-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border text-sm">
                {users.map((user) => (
                  <tr key={user.id} className="hover:bg-muted/20 transition-colors">
                    <td className="p-4">
                      <div className="flex flex-col">
                        <span className="font-semibold text-foreground">{user.username}</span>
                        <span className="text-xs text-muted-foreground">{user.email}</span>
                      </div>
                    </td>
                    <td className="p-4">
                      <div className="flex flex-col">
                        <span className="font-medium text-foreground">{user.fullName || "—"}</span>
                        <span className="text-xs text-muted-foreground">{user.phoneNumber || "No Phone"}</span>
                      </div>
                    </td>
                    <td className="p-4">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-secondary text-secondary-foreground">
                        {user.userType}
                      </span>
                    </td>
                    <td className="p-4 max-w-[200px]">
                      <div className="flex flex-wrap gap-1">
                        {Array.isArray(user.groups) && user.groups.length > 0 ? (
                          user.groups.map((g: any, i) => {
                            const name = typeof g === "object" ? g.name : g
                            return (
                              <span key={i} className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-primary/10 text-primary uppercase">
                                {name}
                              </span>
                            )
                          })
                        ) : (
                          <span className="text-xs text-muted-foreground">None</span>
                        )}
                      </div>
                    </td>
                    <td className="p-4">
                      <button
                        onClick={() => handleToggleActiveStatus(user)}
                        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold cursor-pointer ${
                          user.isActive 
                            ? "bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20" 
                            : "bg-red-500/10 text-red-500 hover:bg-red-500/20"
                        }`}
                        title={user.isActive ? "Click to Deactivate" : "Click to Activate"}
                      >
                        {user.isActive ? (
                          <>
                            <UserCheck className="h-3 w-3" /> Active
                          </>
                        ) : (
                          <>
                            <UserX className="h-3 w-3" /> Inactive
                          </>
                        )}
                      </button>
                    </td>
                    <td className="p-4 text-right space-x-1">
                      <button
                        onClick={() => handleOpenEdit(user)}
                        className="inline-flex items-center justify-center p-2 rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground transition-all cursor-pointer"
                        title="Edit User"
                      >
                        <Edit2 className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDeleteUser(user.id, user.username)}
                        className="inline-flex items-center justify-center p-2 rounded-lg text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-all cursor-pointer"
                        title="Delete User"
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

        {/* Pagination Footer */}
        {totalCount > 10 && (
          <div className="p-4 border-t border-border flex items-center justify-between bg-card/30">
            <span className="text-xs text-muted-foreground">
              Showing page {page} of {Math.ceil(totalCount / 10)} ({totalCount} total users)
            </span>
            <div className="flex gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
                className="px-3 py-1.5 text-xs font-semibold rounded border border-border bg-background hover:bg-muted disabled:opacity-50 transition-all cursor-pointer"
              >
                Previous
              </button>
              <button
                disabled={page * 10 >= totalCount}
                onClick={() => setPage(page + 1)}
                className="px-3 py-1.5 text-xs font-semibold rounded border border-border bg-background hover:bg-muted disabled:opacity-50 transition-all cursor-pointer"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm overflow-y-auto">
          <div className="bg-card border border-border w-full max-w-2xl rounded-2xl shadow-xl overflow-hidden my-8 animate-in fade-in zoom-in duration-200">
            <div className="p-6 border-b border-border flex items-center justify-between">
              <h2 className="text-lg font-bold text-foreground">Create User Account</h2>
              <button onClick={() => setShowAddModal(false)} className="text-muted-foreground hover:text-foreground p-1 rounded-lg hover:bg-muted cursor-pointer">
                <X className="h-5 w-5" />
              </button>
            </div>
            <form onSubmit={handleAddUser} className="p-6 space-y-4 max-h-[75vh] overflow-y-auto">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1">Username *</label>
                  <input
                    type="text"
                    required
                    value={formData.username}
                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                    className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 text-foreground"
                    placeholder="e.g. jdoe"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1">Email *</label>
                  <input
                    type="email"
                    required
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 text-foreground"
                    placeholder="e.g. john.doe@zic.co.tz"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1">First Name</label>
                  <input
                    type="text"
                    value={formData.firstName}
                    onChange={(e) => setFormData({ ...formData, firstName: e.target.value })}
                    className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 text-foreground"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1">Last Name</label>
                  <input
                    type="text"
                    value={formData.lastName}
                    onChange={(e) => setFormData({ ...formData, lastName: e.target.value })}
                    className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 text-foreground"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1">Password *</label>
                  <input
                    type="password"
                    required
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 text-foreground"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1">Confirm Password *</label>
                  <input
                    type="password"
                    required
                    value={formData.passwordConfirm}
                    onChange={(e) => setFormData({ ...formData, passwordConfirm: e.target.value })}
                    className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 text-foreground"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1">Phone Number</label>
                  <input
                    type="text"
                    value={formData.phoneNumber}
                    onChange={(e) => setFormData({ ...formData, phoneNumber: e.target.value })}
                    className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 text-foreground"
                    placeholder="+255700000000"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1">User Type</label>
                  <select
                    value={formData.userType}
                    onChange={(e) => setFormData({ ...formData, userType: e.target.value })}
                    className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 text-foreground"
                  >
                    <option value="PORTAL_USER">Portal User</option>
                    <option value="ZIC_GROUP">ZIC Group User</option>
                    <option value="PARTNER_USER">Partner User</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1">Department</label>
                  <input
                    type="text"
                    value={formData.department}
                    onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                    className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 text-foreground"
                    placeholder="e.g. Underwriting"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1">Job Title</label>
                  <input
                    type="text"
                    value={formData.jobTitle}
                    onChange={(e) => setFormData({ ...formData, jobTitle: e.target.value })}
                    className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 text-foreground"
                    placeholder="e.g. Senior Underwriter"
                  />
                </div>
              </div>

              {/* Group / Role Selection */}
              <div className="space-y-2 pt-2">
                <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground">Assign Roles / User Groups</label>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {groups.map(group => {
                    const selected = formData.groupIds.includes(group.id)
                    return (
                      <div
                        key={group.id}
                        onClick={() => handleGroupSelectToggle(group.id)}
                        className={`p-3 rounded-lg border flex items-center justify-between cursor-pointer select-none transition-all ${
                          selected 
                            ? "bg-primary/5 border-primary text-primary" 
                            : "bg-background border-border hover:bg-muted/10 text-foreground"
                        }`}
                      >
                        <div className="flex flex-col gap-0.5">
                          <span className="text-xs font-semibold">{group.name}</span>
                          <span className="text-[10px] text-muted-foreground line-clamp-1">{group.description}</span>
                        </div>
                        {selected && <Check className="h-4 w-4" />}
                      </div>
                    )
                  })}
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-border mt-6">
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
                  Create User
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {showEditModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm overflow-y-auto">
          <div className="bg-card border border-border w-full max-w-2xl rounded-2xl shadow-xl overflow-hidden my-8 animate-in fade-in zoom-in duration-200">
            <div className="p-6 border-b border-border flex items-center justify-between">
              <h2 className="text-lg font-bold text-foreground">Edit User Profile</h2>
              <button onClick={() => setShowEditModal(false)} className="text-muted-foreground hover:text-foreground p-1 rounded-lg hover:bg-muted cursor-pointer">
                <X className="h-5 w-5" />
              </button>
            </div>
            <form onSubmit={handleEditUser} className="p-6 space-y-4 max-h-[75vh] overflow-y-auto">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1">Username (Read-only)</label>
                  <input
                    type="text"
                    disabled
                    value={formData.username}
                    className="w-full px-3 py-2 text-sm bg-muted border border-border rounded-lg text-muted-foreground focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1">Email (Read-only)</label>
                  <input
                    type="email"
                    disabled
                    value={formData.email}
                    className="w-full px-3 py-2 text-sm bg-muted border border-border rounded-lg text-muted-foreground focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1">First Name</label>
                  <input
                    type="text"
                    value={formData.firstName}
                    onChange={(e) => setFormData({ ...formData, firstName: e.target.value })}
                    className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 text-foreground"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1">Last Name</label>
                  <input
                    type="text"
                    value={formData.lastName}
                    onChange={(e) => setFormData({ ...formData, lastName: e.target.value })}
                    className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 text-foreground"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1">Phone Number</label>
                  <input
                    type="text"
                    value={formData.phoneNumber}
                    onChange={(e) => setFormData({ ...formData, phoneNumber: e.target.value })}
                    className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 text-foreground"
                    placeholder="+255700000000"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1">User Type</label>
                  <select
                    value={formData.userType}
                    onChange={(e) => setFormData({ ...formData, userType: e.target.value })}
                    className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 text-foreground"
                  >
                    <option value="PORTAL_USER">Portal User</option>
                    <option value="ZIC_GROUP">ZIC Group User</option>
                    <option value="PARTNER_USER">Partner User</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1">Department</label>
                  <input
                    type="text"
                    value={formData.department}
                    onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                    className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 text-foreground"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1">Job Title</label>
                  <input
                    type="text"
                    value={formData.jobTitle}
                    onChange={(e) => setFormData({ ...formData, jobTitle: e.target.value })}
                    className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 text-foreground"
                  />
                </div>
              </div>

              {/* Group / Role Selection */}
              <div className="space-y-2 pt-2">
                <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground">Assign Roles / User Groups</label>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {groups.map(group => {
                    const selected = formData.groupIds.includes(group.id)
                    return (
                      <div
                        key={group.id}
                        onClick={() => handleGroupSelectToggle(group.id)}
                        className={`p-3 rounded-lg border flex items-center justify-between cursor-pointer select-none transition-all ${
                          selected 
                            ? "bg-primary/5 border-primary text-primary" 
                            : "bg-background border-border hover:bg-muted/10 text-foreground"
                        }`}
                      >
                        <div className="flex flex-col gap-0.5">
                          <span className="text-xs font-semibold">{group.name}</span>
                          <span className="text-[10px] text-muted-foreground line-clamp-1">{group.description}</span>
                        </div>
                        {selected && <Check className="h-4 w-4" />}
                      </div>
                    )
                  })}
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-border mt-6">
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

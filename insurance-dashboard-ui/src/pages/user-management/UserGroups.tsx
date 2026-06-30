import { useEffect, useState } from "react"
import { Loader2, Users, ShieldAlert, Check, Shield, Lock, Search } from "lucide-react"
import { 
  listUserGroups, 
  listPermissions, 
  assignPermissionsToGroup, 
  removePermissionsFromGroup,
  getUserGroup
} from "../../lib/api"

interface UserGroupRecord {
  id: string
  name: string
  code: string
  description: string
  permissions: { id: string; codename: string; name: string; module: string }[]
}

interface PermissionRecord {
  id: string
  name: string
  codename: string
  module: string
  action: string
  description: string
}

export default function UserGroups() {
  const [groups, setGroups] = useState<UserGroupRecord[]>([])
  const [permissions, setPermissions] = useState<PermissionRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Selection
  const [selectedGroupId, setSelectedGroupId] = useState<string>("")
  const [groupPermIds, setGroupPermIds] = useState<string[]>([])
  const [loadingDetails, setLoadingDetails] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")

  // State to prevent multiple quick clicks
  const [updatingPermId, setUpdatingPermId] = useState<string | null>(null)

  const fetchData = async () => {
    try {
      setLoading(true)
      setError(null)
      const [groupsData, permsData] = await Promise.all([
        listUserGroups(),
        listPermissions()
      ])
      setGroups(groupsData)
      setPermissions(permsData)
      
      // Default selection to first group if not set
      if (groupsData.length > 0 && !selectedGroupId) {
        setSelectedGroupId(groupsData[0].id)
      }
    } catch (err: any) {
      setError(err.message ?? "Failed to load user groups and permissions")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  // Load group details (permissions) when selected group changes
  useEffect(() => {
    if (!selectedGroupId) return

    const fetchDetails = async () => {
      try {
        setLoadingDetails(true)
        const details = await getUserGroup(selectedGroupId)
        if (details && Array.isArray(details.permissions)) {
          setGroupPermIds(details.permissions.map((p: any) => p.id))
        } else {
          setGroupPermIds([])
        }
      } catch (err) {
        console.error("Failed to fetch group details:", err)
      } finally {
        setLoadingDetails(false)
      }
    }

    fetchDetails()
  }, [selectedGroupId])

  const selectedGroup = groups.find(g => g.id === selectedGroupId)
  const isSuperAdmin = selectedGroup?.code === "SUPER_ADMIN"
  const isZicGroup = selectedGroup?.code === "ZIC_GROUP"

  // Check if group has a specific permission
  const hasPermission = (permId: string) => {
    if (isSuperAdmin) return true // Superadmin always has all permissions
    return groupPermIds.includes(permId)
  }

  // Handle toggling permission
  const handleTogglePermission = async (permId: string) => {
    if (!selectedGroup || isSuperAdmin || updatingPermId) return

    setUpdatingPermId(permId)
    const active = hasPermission(permId)

    try {
      if (active) {
        // Remove permission
        await removePermissionsFromGroup(selectedGroup.id, [permId])
        // Update local state
        setGroupPermIds(prev => prev.filter(id => id !== permId))
      } else {
        // Add permission
        await assignPermissionsToGroup(selectedGroup.id, [permId])
        // Update local state
        setGroupPermIds(prev => [...prev, permId])
      }
    } catch (err: any) {
      alert(err.message ?? "Failed to update permission mapping")
    } finally {
      setUpdatingPermId(null)
    }
  }

  // Group permissions by module (normalize module name to lowercase and trimmed)
  const permissionsByModule = permissions.reduce((acc, p) => {
    const modKey = (p.module || "general").trim().toLowerCase()
    acc[modKey] = acc[modKey] || []
    acc[modKey].push(p)
    return acc
  }, {} as Record<string, PermissionRecord[]>)

  // Filter modules/permissions based on search query
  const filteredModules = Object.entries(permissionsByModule).reduce((acc, [moduleName, perms]) => {
    const matchedPerms = perms.filter(p => 
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.codename.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      moduleName.toLowerCase().includes(searchQuery.toLowerCase())
    )
    if (matchedPerms.length > 0) {
      acc[moduleName] = matchedPerms
    }
    return acc
  }, {} as Record<string, PermissionRecord[]>)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
          <Users className="h-6 w-6 text-primary" /> Role Access Control
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Assign and configure role permission scopes for Portal users, Underwriters, and top-tier Managers.
        </p>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 text-muted-foreground gap-3 bg-card border border-border rounded-xl shadow-sm">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm">Loading user roles & permission matrices...</p>
        </div>
      ) : error ? (
        <div className="p-6 text-center bg-card border border-border rounded-xl shadow-sm">
          <p className="text-sm text-destructive font-medium">{error}</p>
          <button onClick={fetchData} className="mt-4 text-xs font-semibold text-primary underline">Try Again</button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Roles Navigation Sidebar (col-4) */}
          <div className="lg:col-span-4 space-y-4">
            <div className="rounded-xl border border-border bg-card shadow-sm p-4 space-y-3">
              <h2 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">User Groups / Roles</h2>
              <div className="space-y-1.5">
                {groups.map((group) => {
                  const isSelected = group.id === selectedGroupId
                  return (
                    <button
                      key={group.id}
                      onClick={() => setSelectedGroupId(group.id)}
                      className={`w-full text-left p-3.5 rounded-xl border transition-all cursor-pointer flex flex-col gap-1 ${
                        isSelected
                          ? "bg-primary/10 border-primary text-primary shadow-sm"
                          : "bg-card border-border hover:bg-muted/30 text-foreground"
                      }`}
                    >
                      <div className="flex items-center justify-between w-full">
                        <span className="font-semibold text-sm">{group.name}</span>
                        {group.code === "SUPER_ADMIN" || group.code === "ZIC_GROUP" ? (
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-500 uppercase tracking-wider">
                            Top Tier
                          </span>
                        ) : null}
                      </div>
                      <span className={`text-xs ${isSelected ? "text-primary/80" : "text-muted-foreground"}`}>
                        {group.description || "No description provided."}
                      </span>
                    </button>
                  )
                })}
              </div>
            </div>
          </div>

          {/* Permissions Matrix Panel (col-8) */}
          <div className="lg:col-span-8">
            {selectedGroup && (
              <div className="rounded-xl border border-border bg-card shadow-sm overflow-hidden space-y-6">
                {/* Panel Info */}
                <div className="p-6 border-b border-border bg-muted/20 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                  <div>
                    <h2 className="text-lg font-bold text-foreground flex items-center gap-2">
                      <Shield className="h-5 w-5 text-primary" /> {selectedGroup.name} Permissions
                    </h2>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {isSuperAdmin 
                        ? "Bypasses all guards automatically. All permissions granted."
                        : isZicGroup
                        ? "Full admin access group. Typically has all permissions."
                        : "Toggle fine-grained permissions to configure scope for this group."}
                    </p>
                  </div>
                  
                  {/* Search Permissions */}
                  <div className="relative w-full md:w-64">
                    <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                    <input
                      type="text"
                      placeholder="Search permissions..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-full pl-8 pr-3 py-1.5 text-xs bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary text-foreground"
                    />
                  </div>
                </div>

                {/* Permissions Toggles List */}
                <div className="p-6 pt-0 space-y-6 max-h-[600px] overflow-y-auto">
                  {loadingDetails ? (
                    <div className="flex flex-col items-center justify-center py-20 text-muted-foreground gap-3">
                      <Loader2 className="h-8 w-8 animate-spin text-primary" />
                      <p className="text-sm">Loading group permissions...</p>
                    </div>
                  ) : (
                    <>
                      {isSuperAdmin && (
                        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-start gap-3">
                          <Lock className="h-5 w-5 text-amber-500 shrink-0 mt-0.5" />
                          <div>
                            <h4 className="text-sm font-semibold text-amber-600">Permissions are Locked</h4>
                            <p className="text-xs text-amber-600/80 mt-0.5">
                              Superadmins always bypass all module guards and have full system scope. Individual permission overrides are not necessary.
                            </p>
                          </div>
                        </div>
                      )}

                      {Object.entries(filteredModules).map(([moduleName, perms]) => (
                        <div key={`module-${selectedGroupId}-${moduleName}`} className="space-y-3">
                          <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wider border-b border-border pb-1">
                            {moduleName.toUpperCase()} MODULE
                          </h3>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            {perms.map((perm) => {
                              const active = hasPermission(perm.id)
                              const updating = updatingPermId === perm.id
                              return (
                                <div 
                                  key={`perm-${selectedGroupId}-${perm.id}`} 
                                  onClick={() => !isSuperAdmin && handleTogglePermission(perm.id)}
                                  className={`p-3.5 rounded-xl border flex items-center justify-between transition-all select-none ${
                                    isSuperAdmin 
                                      ? "bg-muted/30 border-muted text-muted-foreground cursor-not-allowed"
                                      : active
                                      ? "bg-primary/5 border-primary/30 hover:border-primary/50 cursor-pointer"
                                      : "bg-background border-border hover:bg-muted/10 cursor-pointer"
                                  }`}
                                >
                                  <div className="space-y-0.5 max-w-[80%]">
                                    <p className="text-xs font-semibold text-foreground">{perm.name}</p>
                                    <p className="text-[10px] font-mono text-muted-foreground">{perm.codename}</p>
                                  </div>

                                  {/* Toggle Checkbox/Indicator */}
                                  <div className="flex items-center justify-center">
                                    {updating ? (
                                      <Loader2 className="h-4 w-4 animate-spin text-primary" />
                                    ) : active ? (
                                      <div className="h-5 w-5 rounded bg-primary text-primary-foreground flex items-center justify-center shadow-sm">
                                        <Check className="h-3.5 w-3.5 stroke-[3]" />
                                      </div>
                                    ) : (
                                      <div className="h-5 w-5 rounded border border-border bg-background" />
                                    )}
                                  </div>
                                </div>
                              )
                            })}
                          </div>
                        </div>
                      ))}

                      {Object.keys(filteredModules).length === 0 && (
                        <div className="text-center py-10 text-muted-foreground">
                          <ShieldAlert className="h-8 w-8 mx-auto mb-2 text-muted-foreground/50" />
                          <p className="text-xs">No permissions matched your search query.</p>
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

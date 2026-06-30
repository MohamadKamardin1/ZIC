import { useEffect, useState } from "react"
import { Loader2, ShieldCheck, Search, Filter, RefreshCw } from "lucide-react"
import { listPermissions, listPermissionModules } from "../../lib/api"

interface PermissionRecord {
  id: string
  name: string
  codename: string
  module: string
  action: string
  resource_type: string
  description: string
}

export default function Permissions() {
  const [permissions, setPermissions] = useState<PermissionRecord[]>([])
  const [modules, setModules] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedModule, setSelectedModule] = useState("")

  const fetchData = async () => {
    try {
      setLoading(true)
      setError(null)
      const [permsData, modulesData] = await Promise.all([
        listPermissions(),
        listPermissionModules(),
      ])
      setPermissions(permsData)
      setModules(modulesData)
    } catch (err: any) {
      setError(err.message ?? "Failed to fetch permissions")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const filteredPermissions = permissions.filter(p => {
    const matchesSearch = p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.codename.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.description?.toLowerCase().includes(searchQuery.toLowerCase())
    
    const matchesModule = selectedModule === "" || p.module === selectedModule
    return matchesSearch && matchesModule
  })

  // Group by module for display stats
  const moduleCounts = permissions.reduce((acc, p) => {
    acc[p.module] = (acc[p.module] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <ShieldCheck className="h-6 w-6 text-primary" /> Permissions Directory
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Browse and search all fine-grained system access controls and permission definitions.
          </p>
        </div>
        <button
          onClick={fetchData}
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-border bg-card px-4 py-2 text-sm font-semibold text-foreground hover:bg-muted transition-all cursor-pointer"
        >
          <RefreshCw className="h-4 w-4" /> Refresh
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border border-border bg-card/50 backdrop-blur-md flex items-center gap-4">
          <div className="p-3 rounded-lg bg-primary/10 text-primary">
            <ShieldCheck className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Total Permissions</p>
            <p className="text-2xl font-bold text-foreground">{permissions.length}</p>
          </div>
        </div>

        <div className="p-4 rounded-xl border border-border bg-card/50 backdrop-blur-md flex items-center gap-4">
          <div className="p-3 rounded-lg bg-emerald-500/10 text-emerald-500">
            <Filter className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Active Modules</p>
            <p className="text-2xl font-bold text-foreground">{modules.length}</p>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="rounded-xl border border-border bg-card shadow-sm overflow-hidden">
        {/* Toolbar */}
        <div className="p-4 border-b border-border bg-card/50 flex flex-col sm:flex-row items-center gap-4">
          {/* Search */}
          <div className="relative flex-1 w-full">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search permissions by name, codename, or description..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all text-foreground"
            />
          </div>

          {/* Module Selector */}
          <div className="w-full sm:w-64 flex items-center gap-2">
            <Filter className="h-4 w-4 text-muted-foreground shrink-0" />
            <select
              value={selectedModule}
              onChange={(e) => setSelectedModule(e.target.value)}
              className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all text-foreground"
            >
              <option value="">All Modules ({permissions.length})</option>
              {modules.map((mod) => (
                <option key={mod} value={mod}>
                  {mod.toUpperCase()} ({moduleCounts[mod] || 0})
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Loading / Error States */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 text-muted-foreground gap-3">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="text-sm">Loading permissions directory...</p>
          </div>
        ) : error ? (
          <div className="p-6 text-center">
            <p className="text-sm text-destructive font-medium">{error}</p>
            <button onClick={fetchData} className="mt-4 text-xs font-semibold text-primary underline">Try Again</button>
          </div>
        ) : filteredPermissions.length === 0 ? (
          <div className="py-20 text-center text-muted-foreground">
            <ShieldCheck className="h-10 w-10 mx-auto text-muted-foreground/50 mb-3" />
            <p className="text-sm font-medium">No permissions match your filters</p>
            <p className="text-xs mt-1">Try clearing your search query or choosing another module.</p>
          </div>
        ) : (
          /* Table */
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-muted/40 border-b border-border text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  <th className="p-4 font-semibold">Permission Name</th>
                  <th className="p-4 font-semibold">Codename</th>
                  <th className="p-4 font-semibold">Module</th>
                  <th className="p-4 font-semibold">Scope / Action</th>
                  <th className="p-4 font-semibold">Description</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border text-sm">
                {filteredPermissions.map((perm) => (
                  <tr key={perm.id} className="hover:bg-muted/20 transition-colors">
                    <td className="p-4 font-medium text-foreground">{perm.name}</td>
                    <td className="p-4 font-mono text-xs text-muted-foreground">{perm.codename}</td>
                    <td className="p-4">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-secondary text-secondary-foreground uppercase">
                        {perm.module}
                      </span>
                    </td>
                    <td className="p-4">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                        perm.action === "MANAGE" 
                          ? "bg-red-500/10 text-red-500" 
                          : perm.action === "READ" 
                          ? "bg-blue-500/10 text-blue-500"
                          : "bg-amber-500/10 text-amber-500"
                      }`}>
                        {perm.action}
                      </span>
                    </td>
                    <td className="p-4 text-muted-foreground max-w-sm truncate" title={perm.description}>
                      {perm.description || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

import { useState, useEffect, useCallback } from "react"
import {
  Users, Search, Eye, Loader2, Plus, X,
  AlertTriangle, UserCheck, UserX, Heart
} from "lucide-react"
import { gcMembers } from "../../lib/gc-api"

function formatCurrency(val: any) {
  if (!val) return "—"
  return new Intl.NumberFormat("en-US", { style: "decimal", minimumFractionDigits: 0 }).format(Number(val))
}

const UW_STATUS_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  NOT_REQUIRED: { bg: "bg-slate-500/10", text: "text-slate-400", label: "N/A" },
  PENDING: { bg: "bg-amber-500/10", text: "text-amber-400", label: "Pending UW" },
  STANDARD: { bg: "bg-emerald-500/10", text: "text-emerald-400", label: "Standard" },
  LOADED: { bg: "bg-orange-500/10", text: "text-orange-400", label: "Loaded" },
  EXCLUDED: { bg: "bg-red-500/10", text: "text-red-400", label: "Exclusion" },
  DECLINED: { bg: "bg-red-500/10", text: "text-red-500", label: "Declined" },
}

export default function GCBorrowers() {
  const [members, setMembers] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [uwFilter, setUwFilter] = useState("")
  const [selectedMember, setSelectedMember] = useState<any>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  const loadMembers = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string> = {}
      if (search) params.search = search
      if (uwFilter) params.uw_status = uwFilter
      const res = await gcMembers.list(params)
      setMembers(res?.results ?? res?.data ?? res ?? [])
    } catch (err: any) { console.error(err) }
    finally { setLoading(false) }
  }, [search, uwFilter])

  useEffect(() => { loadMembers() }, [loadMembers])

  async function viewDetail(id: string) {
    setDetailLoading(true)
    try {
      const detail = await gcMembers.get(id)
      setSelectedMember(detail)
    } catch (err: any) { alert(err.message) }
    finally { setDetailLoading(false) }
  }

  const total = members.length
  const withUW = members.filter((m: any) => m.requiresMedicalUw).length
  const pending = members.filter((m: any) => m.uwStatus === "PENDING").length

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground flex items-center gap-3">
          <div className="p-2 rounded-xl" style={{ background: "linear-gradient(135deg, #8b5cf6, #a855f7)" }}>
            <Users className="h-6 w-6 text-white" />
          </div>
          Members
        </h1>
        <p className="text-muted-foreground mt-1">Scheme member enrollment & underwriting management</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[
          { label: "Total Members", value: total, icon: Users, color: "#8b5cf6" },
          { label: "Requires UW", value: withUW, icon: Heart, color: "#f59e0b" },
          { label: "Pending UW", value: pending, icon: AlertTriangle, color: "#ef4444" },
          { label: "Standard", value: members.filter((m: any) => m.uwStatus === "STANDARD" || m.uwStatus === "NOT_REQUIRED").length, icon: UserCheck, color: "#10b981" },
        ].map((s) => (
          <div key={s.label} className="rounded-2xl border border-border bg-card p-4 flex items-center gap-3">
            <div className="rounded-xl p-2.5" style={{ backgroundColor: `${s.color}15` }}>
              <s.icon className="h-5 w-5" style={{ color: s.color }} />
            </div>
            <div>
              <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">{s.label}</p>
              <p className="text-xl font-bold text-foreground">{s.value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search members..."
            className="h-10 w-full rounded-xl border border-border bg-card pl-10 pr-4 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40" />
        </div>
        <select value={uwFilter} onChange={(e) => setUwFilter(e.target.value)}
          className="h-10 rounded-xl border border-border bg-card px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40">
          <option value="">All UW Status</option>
          {Object.entries(UW_STATUS_STYLES).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
        </select>
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
        {loading ? (
          <div className="flex items-center justify-center p-16"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>
        ) : members.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-16 text-muted-foreground">
            <Users className="h-12 w-12 mb-3 opacity-40" />
            <p className="text-lg font-medium">No members found</p>
            <p className="text-sm">Members are enrolled through the Scheme detail page.</p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-border bg-secondary/30">
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Member #</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Name</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Scheme</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Category</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-muted-foreground">Sum Assured</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">UW Status</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-muted-foreground">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {members.map((m: any) => {
                const uwStyle = UW_STATUS_STYLES[m.uwStatus] ?? UW_STATUS_STYLES.NOT_REQUIRED
                return (
                  <tr key={m.id} className="group transition hover:bg-secondary/20 cursor-pointer" onClick={() => viewDetail(m.id)}>
                    <td className="px-4 py-3.5">
                      <span className="text-sm font-mono font-semibold text-primary">{m.memberNumber}</span>
                    </td>
                    <td className="px-4 py-3.5">
                      <p className="text-sm font-medium text-foreground">{m.fullName ?? `${m.firstName ?? ""} ${m.surname ?? ""}`}</p>
                      <p className="text-xs text-muted-foreground">{m.employeeNumber ?? ""}</p>
                    </td>
                    <td className="px-4 py-3.5 text-sm text-foreground font-mono">{m.schemeNumber ?? "—"}</td>
                    <td className="px-4 py-3.5 text-sm text-foreground">{m.categoryName ?? "—"}</td>
                    <td className="px-4 py-3.5 text-sm text-foreground text-right font-mono">{formatCurrency(m.sumAssured)}</td>
                    <td className="px-4 py-3.5">
                      <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${uwStyle.bg} ${uwStyle.text}`}>
                        {m.requiresMedicalUw && <Heart className="h-3 w-3" />}
                        {uwStyle.label}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-right">
                      <button className="p-1.5 rounded-lg hover:bg-secondary text-muted-foreground hover:text-foreground transition">
                        <Eye className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Member Detail Slide-over */}
      {selectedMember && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/50 backdrop-blur-sm" onClick={() => setSelectedMember(null)}>
          <div className="w-full max-w-2xl overflow-y-auto bg-card border-l border-border shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="sticky top-0 z-10 border-b border-border bg-card/95 backdrop-blur-sm px-6 py-4 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-foreground">{selectedMember.memberNumber}</h2>
                <p className="text-sm text-muted-foreground">{selectedMember.fullName}</p>
              </div>
              <button onClick={() => setSelectedMember(null)} className="p-2 rounded-lg hover:bg-secondary"><X className="h-5 w-5 text-foreground" /></button>
            </div>
            {detailLoading ? (
              <div className="flex items-center justify-center p-16"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>
            ) : (
              <div className="p-6 space-y-6">
                {/* Personal Info */}
                <div>
                  <h3 className="text-sm font-semibold text-foreground mb-3">Personal Information</h3>
                  <div className="grid grid-cols-2 gap-4">
                    {[
                      { label: "First Name", value: selectedMember.firstName },
                      { label: "Surname", value: selectedMember.surname },
                      { label: "Gender", value: selectedMember.gender },
                      { label: "Date of Birth", value: selectedMember.dateOfBirth },
                      { label: "Age", value: selectedMember.age },
                      { label: "Nationality", value: selectedMember.nationality },
                      { label: "ID Type", value: selectedMember.identificationType },
                      { label: "ID Number", value: selectedMember.identificationNumber },
                      { label: "Email", value: selectedMember.email },
                      { label: "Mobile", value: selectedMember.mobileNumber },
                    ].map((f) => (
                      <div key={f.label}>
                        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{f.label}</p>
                        <p className="text-sm font-medium text-foreground mt-0.5">{f.value ?? "—"}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Employment */}
                <div>
                  <h3 className="text-sm font-semibold text-foreground mb-3">Employment</h3>
                  <div className="grid grid-cols-2 gap-4">
                    {[
                      { label: "Employee #", value: selectedMember.employeeNumber },
                      { label: "Job Title", value: selectedMember.jobTitle },
                      { label: "Start Date", value: selectedMember.dateOfEmployment },
                      { label: "Annual Salary", value: formatCurrency(selectedMember.annualSalary) },
                    ].map((f) => (
                      <div key={f.label}>
                        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{f.label}</p>
                        <p className="text-sm font-medium text-foreground mt-0.5">{f.value ?? "—"}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Cover Details */}
                <div className="rounded-xl border border-border bg-secondary/20 p-4">
                  <h3 className="text-sm font-semibold text-foreground mb-3">Cover Details</h3>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <p className="text-xs text-muted-foreground">Sum Assured</p>
                      <p className="text-lg font-bold text-foreground">{formatCurrency(selectedMember.sumAssured)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Premium</p>
                      <p className="text-lg font-bold text-primary">{formatCurrency(selectedMember.premiumAmount)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">UW Status</p>
                      <p className="text-lg font-bold text-foreground">{selectedMember.uwStatusDisplay ?? selectedMember.uwStatus}</p>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4 mt-3">
                    <div>
                      <p className="text-xs text-muted-foreground">Cover Start</p>
                      <p className="text-sm font-medium text-foreground">{selectedMember.coverStartDate ?? "—"}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Cover End</p>
                      <p className="text-sm font-medium text-foreground">{selectedMember.coverEndDate ?? "—"}</p>
                    </div>
                  </div>
                </div>

                {/* Dependents */}
                {selectedMember.dependents?.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-foreground mb-3">Dependents ({selectedMember.dependents.length})</h3>
                    <div className="space-y-2">
                      {selectedMember.dependents.map((dep: any) => (
                        <div key={dep.id} className="rounded-xl border border-border p-3 flex items-center justify-between">
                          <div>
                            <p className="text-sm font-medium text-foreground">{dep.firstName} {dep.surname}</p>
                            <p className="text-xs text-muted-foreground">{dep.relationshipDisplay ?? dep.relationship} • {dep.dateOfBirth}</p>
                          </div>
                          <div className="text-right">
                            <p className="text-sm font-mono text-foreground">{formatCurrency(dep.sumAssured)}</p>
                            <span className={`text-xs ${dep.isActive ? "text-emerald-400" : "text-red-400"}`}>{dep.isActive ? "Active" : "Inactive"}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

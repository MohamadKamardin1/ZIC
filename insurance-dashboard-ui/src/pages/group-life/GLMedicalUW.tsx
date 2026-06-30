import { useState, useEffect, useCallback } from "react"
import {
  Heart, Search, Loader2, X, Eye,
  CheckCircle, AlertTriangle, FileText, Stethoscope
} from "lucide-react"
import { glMedicalCases, glSetup } from "../../lib/gl-api"

const CASE_STATUS_STYLES: Record<string, { bg: string; text: string }> = {
  OPEN: { bg: "bg-blue-500/10", text: "text-blue-400" },
  IN_PROGRESS: { bg: "bg-amber-500/10", text: "text-amber-400" },
  COMPLETED: { bg: "bg-emerald-500/10", text: "text-emerald-400" },
  CANCELLED: { bg: "bg-slate-500/10", text: "text-slate-400" },
}

export default function GLMedicalUW() {
  const [cases, setCases] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState("")
  const [selectedCase, setSelectedCase] = useState<any>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [decisions, setDecisions] = useState<any[]>([])
  const [decisionForm, setDecisionForm] = useState({ decision: "", decisionNotes: "", premiumLoadingPercent: 0 })
  const [saving, setSaving] = useState(false)

  const loadCases = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string> = {}
      if (search) params.search = search
      if (statusFilter) params.status = statusFilter
      const res = await glMedicalCases.list(params)
      setCases(res?.results ?? res?.data ?? res ?? [])
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }, [search, statusFilter])

  useEffect(() => { loadCases() }, [loadCases])

  useEffect(() => {
    glSetup.listUWDecisions().then((res: any) => setDecisions(res?.results ?? res?.data ?? res ?? [])).catch(() => {})
  }, [])

  async function viewDetail(id: string) {
    setDetailLoading(true)
    try {
      const detail = await glMedicalCases.get(id)
      setSelectedCase(detail)
      setDecisionForm({ decision: detail.decision ?? "", decisionNotes: detail.decisionNotes ?? "", premiumLoadingPercent: detail.premiumLoadingPercent ?? 0 })
    } catch (err: any) { alert(err.message) }
    finally { setDetailLoading(false) }
  }

  async function handleDecision() {
    if (!selectedCase || !decisionForm.decision) return
    setSaving(true)
    try {
      await glMedicalCases.makeDecision(selectedCase.id, decisionForm)
      await viewDetail(selectedCase.id)
      await loadCases()
    } catch (err: any) { alert(err.message) }
    finally { setSaving(false) }
  }

  const total = cases.length
  const open = cases.filter((c: any) => c.status === "OPEN" || c.status === "IN_PROGRESS").length
  const completed = cases.filter((c: any) => c.status === "COMPLETED").length

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground flex items-center gap-3">
          <div className="p-2 rounded-xl" style={{ background: "linear-gradient(135deg, #ec4899, #f43f5e)" }}>
            <Heart className="h-6 w-6 text-white" />
          </div>
          Medical Underwriting
        </h1>
        <p className="text-muted-foreground mt-1">Review and process medical underwriting cases</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {[
          { label: "Total Cases", value: total, icon: FileText, color: "#ec4899" },
          { label: "Open / In Progress", value: open, icon: AlertTriangle, color: "#f59e0b" },
          { label: "Completed", value: completed, icon: CheckCircle, color: "#10b981" },
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
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search cases..."
            className="h-10 w-full rounded-xl border border-border bg-card pl-10 pr-4 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40" />
        </div>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
          className="h-10 rounded-xl border border-border bg-card px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40">
          <option value="">All Statuses</option>
          {Object.keys(CASE_STATUS_STYLES).map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
        </select>
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
        {loading ? (
          <div className="flex items-center justify-center p-16"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>
        ) : cases.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-16 text-muted-foreground">
            <Heart className="h-12 w-12 mb-3 opacity-40" />
            <p className="text-lg font-medium">No medical cases</p>
            <p className="text-sm">Cases are created when members exceed the Free Cover Limit.</p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-border bg-secondary/30">
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Case #</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Member</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Facility</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Status</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Decision</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Exam Date</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-muted-foreground">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {cases.map((c: any) => {
                const statusStyle = CASE_STATUS_STYLES[c.status] ?? CASE_STATUS_STYLES.OPEN
                return (
                  <tr key={c.id} className="group transition hover:bg-secondary/20 cursor-pointer" onClick={() => viewDetail(c.id)}>
                    <td className="px-4 py-3.5 text-sm font-mono font-semibold text-primary">{c.caseNumber}</td>
                    <td className="px-4 py-3.5">
                      <p className="text-sm font-medium text-foreground">{c.memberName ?? "—"}</p>
                      <p className="text-xs text-muted-foreground font-mono">{c.memberNumber}</p>
                    </td>
                    <td className="px-4 py-3.5 text-sm text-foreground">{c.facilityName ?? "—"}</td>
                    <td className="px-4 py-3.5">
                      <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${statusStyle.bg} ${statusStyle.text}`}>
                        {c.statusDisplay ?? c.status?.replace(/_/g, " ")}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-sm text-foreground">{c.decisionName ?? "—"}</td>
                    <td className="px-4 py-3.5 text-sm text-foreground">{c.examinationDate ?? "—"}</td>
                    <td className="px-4 py-3.5 text-right">
                      <button className="p-1.5 rounded-lg hover:bg-secondary text-muted-foreground hover:text-foreground transition"><Eye className="h-4 w-4" /></button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Detail Slide-over */}
      {selectedCase && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/50 backdrop-blur-sm" onClick={() => setSelectedCase(null)}>
          <div className="w-full max-w-2xl overflow-y-auto bg-card border-l border-border shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="sticky top-0 z-10 border-b border-border bg-card/95 backdrop-blur-sm px-6 py-4 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-foreground">{selectedCase.caseNumber}</h2>
                <p className="text-sm text-muted-foreground">{selectedCase.memberName}</p>
              </div>
              <button onClick={() => setSelectedCase(null)} className="p-2 rounded-lg hover:bg-secondary"><X className="h-5 w-5 text-foreground" /></button>
            </div>
            {detailLoading ? (
              <div className="flex items-center justify-center p-16"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>
            ) : (
              <div className="p-6 space-y-6">
                <div className="grid grid-cols-2 gap-4">
                  {[
                    { label: "Member", value: selectedCase.memberName },
                    { label: "Member #", value: selectedCase.memberNumber },
                    { label: "Facility", value: selectedCase.facilityName },
                    { label: "Practitioner", value: selectedCase.practitionerName },
                    { label: "Exam Date", value: selectedCase.examinationDate },
                    { label: "Status", value: selectedCase.statusDisplay },
                  ].map((f) => (
                    <div key={f.label}>
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{f.label}</p>
                      <p className="text-sm font-medium text-foreground mt-0.5">{f.value ?? "—"}</p>
                    </div>
                  ))}
                </div>

                {/* Diagnosis */}
                {selectedCase.diagnosisCodes?.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-foreground mb-2">Diagnosis Codes</h3>
                    <div className="flex flex-wrap gap-2">
                      {selectedCase.diagnosisCodes.map((d: any) => (
                        <span key={d.id} className="rounded-lg bg-secondary px-3 py-1.5 text-xs font-medium text-foreground">
                          {d.code} — {d.name}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Personal Habits */}
                {selectedCase.personalHabits?.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-foreground mb-2">Personal Habits</h3>
                    <div className="flex flex-wrap gap-2">
                      {selectedCase.personalHabits.map((h: any) => (
                        <span key={h.id} className={`rounded-lg px-3 py-1.5 text-xs font-medium ${
                          h.riskLevel === "HIGH" ? "bg-red-500/10 text-red-400" :
                          h.riskLevel === "MEDIUM" ? "bg-amber-500/10 text-amber-400" : "bg-slate-500/10 text-slate-400"
                        }`}>{h.name}</span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Decision Form (for open cases) */}
                {selectedCase.status !== "COMPLETED" && (
                  <div className="rounded-xl border border-primary/20 bg-primary/5 p-4">
                    <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                      <Stethoscope className="h-4 w-4 text-primary" />
                      Make Underwriting Decision
                    </h3>
                    <div className="space-y-3">
                      <div>
                        <label className="mb-1 block text-sm font-medium text-foreground">Decision</label>
                        <select value={decisionForm.decision} onChange={(e) => setDecisionForm({ ...decisionForm, decision: e.target.value })}
                          className="h-10 w-full rounded-xl border border-border bg-card px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40">
                          <option value="">Select decision...</option>
                          {decisions.map((d: any) => <option key={d.id} value={d.id}>{d.name}</option>)}
                        </select>
                      </div>
                      <div>
                        <label className="mb-1 block text-sm font-medium text-foreground">Premium Loading %</label>
                        <input type="number" value={decisionForm.premiumLoadingPercent} onChange={(e) => setDecisionForm({ ...decisionForm, premiumLoadingPercent: Number(e.target.value) })}
                          className="h-10 w-full rounded-xl border border-border bg-card px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40" />
                      </div>
                      <div>
                        <label className="mb-1 block text-sm font-medium text-foreground">Decision Notes</label>
                        <textarea value={decisionForm.decisionNotes} onChange={(e) => setDecisionForm({ ...decisionForm, decisionNotes: e.target.value })} rows={2}
                          className="w-full rounded-xl border border-border bg-card px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40" />
                      </div>
                      <button onClick={handleDecision} disabled={saving || !decisionForm.decision}
                        className="flex items-center gap-2 rounded-xl px-5 py-2 text-sm font-medium text-white shadow-lg transition hover:opacity-90 disabled:opacity-50"
                        style={{ background: "linear-gradient(135deg, #ec4899, #f43f5e)" }}>
                        {saving && <Loader2 className="h-4 w-4 animate-spin" />} Submit Decision
                      </button>
                    </div>
                  </div>
                )}

                {/* Completed Decision */}
                {selectedCase.status === "COMPLETED" && selectedCase.decisionName && (
                  <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
                    <h3 className="text-sm font-semibold text-foreground mb-2 flex items-center gap-2">
                      <CheckCircle className="h-4 w-4 text-emerald-400" /> Decision: {selectedCase.decisionName}
                    </h3>
                    {selectedCase.premiumLoadingPercent > 0 && (
                      <p className="text-sm text-foreground">Premium Loading: <strong>{selectedCase.premiumLoadingPercent}%</strong></p>
                    )}
                    {selectedCase.decisionNotes && (
                      <p className="text-sm text-muted-foreground mt-1">{selectedCase.decisionNotes}</p>
                    )}
                    <p className="text-xs text-muted-foreground mt-2">Decided by {selectedCase.decidedByName} on {selectedCase.decidedAt}</p>
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

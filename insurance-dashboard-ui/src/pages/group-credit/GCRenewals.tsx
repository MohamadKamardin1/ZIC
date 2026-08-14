import { useState, useEffect, useCallback } from "react"
import {
  RefreshCw, Search, Eye, Loader2, Plus, X,
  CheckCircle, Calendar, DollarSign, AlertTriangle
} from "lucide-react"
import { gcRenewals, gcSchemes } from "../../lib/gc-api"

function formatCurrency(val: any) {
  if (!val) return "—"
  return new Intl.NumberFormat("en-US", { style: "decimal", minimumFractionDigits: 0 }).format(Number(val))
}

const STATUS_STYLES: Record<string, { bg: string; text: string }> = {
  PENDING: { bg: "bg-amber-500/10", text: "text-amber-400" },
  APPROVED: { bg: "bg-emerald-500/10", text: "text-emerald-400" },
  RENEWED: { bg: "bg-blue-500/10", text: "text-blue-400" },
  DECLINED: { bg: "bg-red-500/10", text: "text-red-400" },
  EXPIRED: { bg: "bg-gray-500/10", text: "text-gray-400" },
}

export default function GCRenewals() {
  const [renewals, setRenewals] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [selectedRenewal, setSelectedRenewal] = useState<any>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState("")

  const loadRenewals = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string> = {}
      if (search) params.search = search
      const res = await gcRenewals.list(params)
      setRenewals(res?.results ?? res?.data ?? res ?? [])
    } catch (err: any) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [search])

  useEffect(() => { loadRenewals() }, [loadRenewals])

  async function viewDetail(id: string) {
    setDetailLoading(true)
    try {
      const detail = await gcRenewals.get(id)
      setSelectedRenewal(detail)
    } catch (err: any) {
      alert(err.message)
    } finally {
      setDetailLoading(false)
    }
  }

  async function handleApprove(id: string) {
    setActionLoading("approve")
    try {
      await gcRenewals.approve(id)
      await viewDetail(id)
      await loadRenewals()
    } catch (err: any) {
      alert(err.message)
    } finally {
      setActionLoading("")
    }
  }

  const total = renewals.length
  const pending = renewals.filter((r: any) => r.renewal_status_code === "PENDING").length
  const renewed = renewals.filter((r: any) => r.renewal_status_code === "RENEWED").length

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-3">
            <div className="p-2 rounded-xl" style={{ background: "linear-gradient(135deg, #f59e0b, #f97316)" }}>
              <RefreshCw className="h-6 w-6 text-white" />
            </div>
            Schemes Due For Renewal
          </h1>
          <p className="text-muted-foreground mt-1">Manage Group Credit scheme renewals and re-rating</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {[
          { label: "Total Renewals", value: total, icon: RefreshCw, color: "#6366f1" },
          { label: "Pending", value: pending, icon: AlertTriangle, color: "#f59e0b" },
          { label: "Renewed", value: renewed, icon: CheckCircle, color: "#10b981" },
        ].map((s) => (
          <div key={s.label} className="rounded-2xl border border-border bg-card p-4 flex items-center gap-4">
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
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search renewals..."
            className="h-10 w-full rounded-xl border border-border bg-card pl-10 pr-4 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
          />
        </div>
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
        {loading ? (
          <div className="flex items-center justify-center p-16"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>
        ) : renewals.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-16 text-muted-foreground">
            <RefreshCw className="h-12 w-12 mb-3 opacity-40" />
            <p className="text-lg font-medium">No renewals found</p>
            <p className="text-sm">Scheme renewals will appear here when schemes approach expiry.</p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-border bg-secondary/30">
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Renewal #</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Scheme</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Status</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Expiry Date</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Proposed Date</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-muted-foreground">Proposed Premium</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-muted-foreground">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {renewals.map((r: any) => {
                const st = STATUS_STYLES[r.renewal_status_code] ?? STATUS_STYLES.PENDING
                return (
                  <tr key={r.id} className="group transition hover:bg-secondary/20 cursor-pointer" onClick={() => viewDetail(r.id)}>
                    <td className="px-4 py-3.5">
                      <span className="text-sm font-mono font-semibold text-primary">{r.renewal_number}</span>
                    </td>
                    <td className="px-4 py-3.5 text-sm text-foreground">{r.scheme_number ?? "—"}</td>
                    <td className="px-4 py-3.5">
                      <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${st.bg} ${st.text}`}>
                        {r.renewal_status_name ?? r.renewal_status_code}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-sm text-foreground">{r.current_expiry_date ?? "—"}</td>
                    <td className="px-4 py-3.5 text-sm text-foreground">{r.proposed_renewal_date ?? "—"}</td>
                    <td className="px-4 py-3.5 text-sm text-foreground text-right font-mono">{formatCurrency(r.proposed_premium)}</td>
                    <td className="px-4 py-3.5 text-right">
                      <button onClick={(e) => { e.stopPropagation(); viewDetail(r.id) }} className="p-1.5 rounded-lg hover:bg-secondary text-muted-foreground hover:text-foreground transition">
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

      {/* Detail Slide-over */}
      {selectedRenewal && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/50 backdrop-blur-sm" onClick={() => setSelectedRenewal(null)}>
          <div className="w-full max-w-2xl overflow-y-auto bg-card border-l border-border shadow-2xl animate-in slide-in-from-right" onClick={(e) => e.stopPropagation()}>
            <div className="sticky top-0 z-10 border-b border-border bg-card/95 backdrop-blur-sm px-6 py-4 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-foreground">{selectedRenewal.renewal_number}</h2>
                <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${(STATUS_STYLES[selectedRenewal.renewal_status_code] ?? STATUS_STYLES.PENDING).bg} ${(STATUS_STYLES[selectedRenewal.renewal_status_code] ?? STATUS_STYLES.PENDING).text}`}>
                  {selectedRenewal.renewal_status_name}
                </span>
              </div>
              <button onClick={() => setSelectedRenewal(null)} className="p-2 rounded-lg hover:bg-secondary"><X className="h-5 w-5 text-foreground" /></button>
            </div>

            {detailLoading ? (
              <div className="flex items-center justify-center p-16"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>
            ) : (
              <div className="p-6 space-y-6">
                <div className="grid grid-cols-2 gap-4">
                  {[
                    { label: "Scheme", value: selectedRenewal.scheme_number },
                    { label: "Current Expiry", value: selectedRenewal.current_expiry_date },
                    { label: "Proposed Renewal Date", value: selectedRenewal.proposed_renewal_date },
                    { label: "Previous Premium", value: formatCurrency(selectedRenewal.previous_premium) },
                    { label: "Proposed Premium", value: formatCurrency(selectedRenewal.proposed_premium) },
                    { label: "Claims Experience Ratio", value: selectedRenewal.claims_experience_ratio ?? "—" },
                  ].map((f) => (
                    <div key={f.label}>
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{f.label}</p>
                      <p className="text-sm font-medium text-foreground mt-0.5">{f.value ?? "—"}</p>
                    </div>
                  ))}
                </div>

                {selectedRenewal.notes && (
                  <div className="rounded-xl border border-border bg-secondary/20 p-4">
                    <h3 className="text-sm font-semibold text-foreground mb-2">Notes</h3>
                    <p className="text-sm text-muted-foreground">{selectedRenewal.notes}</p>
                  </div>
                )}

                {selectedRenewal.renewal_status_code !== "RENEWED" && (
                  <div className="flex items-center gap-3 pt-2">
                    <button
                      onClick={() => handleApprove(selectedRenewal.id)}
                      disabled={!!actionLoading}
                      className="flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 transition disabled:opacity-50"
                    >
                      {actionLoading === "approve" ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle className="h-4 w-4" />}
                      Approve Renewal
                    </button>
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

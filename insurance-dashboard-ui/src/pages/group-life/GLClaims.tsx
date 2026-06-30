import { useState, useEffect, useCallback } from "react"
import {
  AlertCircle, Search, Eye, Loader2, Plus, X,
  CheckCircle, XCircle, DollarSign, FileWarning, Banknote
} from "lucide-react"
import { glClaims } from "../../lib/gl-api"

function formatCurrency(val: any) {
  if (!val) return "—"
  return new Intl.NumberFormat("en-US", { style: "decimal", minimumFractionDigits: 0 }).format(Number(val))
}

const CLAIM_STATUS_STYLES: Record<string, { bg: string; text: string }> = {
  REGISTERED: { bg: "bg-blue-500/10", text: "text-blue-400" },
  ASSESSED: { bg: "bg-amber-500/10", text: "text-amber-400" },
  APPROVED: { bg: "bg-emerald-500/10", text: "text-emerald-400" },
  PAID: { bg: "bg-green-500/10", text: "text-green-400" },
  REJECTED: { bg: "bg-red-500/10", text: "text-red-400" },
  CLOSED: { bg: "bg-slate-500/10", text: "text-slate-400" },
}

export default function GLClaims() {
  const [claims, setClaims] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [selectedClaim, setSelectedClaim] = useState<any>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState("")

  const loadClaims = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string> = {}
      if (search) params.search = search
      const res = await glClaims.list(params)
      setClaims(res?.results ?? res?.data ?? res ?? [])
    } catch (err: any) { console.error(err) }
    finally { setLoading(false) }
  }, [search])

  useEffect(() => { loadClaims() }, [loadClaims])

  async function viewDetail(id: string) {
    setDetailLoading(true)
    try {
      const detail = await glClaims.get(id)
      setSelectedClaim(detail)
    } catch (err: any) { alert(err.message) }
    finally { setDetailLoading(false) }
  }

  async function handleAction(action: string, id: string) {
    setActionLoading(action)
    try {
      if (action === "assess") await glClaims.assess(id, {})
      else if (action === "approve") await glClaims.approve(id, {})
      else if (action === "reject") await glClaims.reject(id, "Rejected by claims officer")
      else if (action === "pay") await glClaims.pay(id, selectedClaim?.approvedAmount || 0)
      await viewDetail(id)
      await loadClaims()
    } catch (err: any) { alert(err.message) }
    finally { setActionLoading("") }
  }

  const total = claims.length
  const pending = claims.filter((c: any) => ["REGISTERED", "ASSESSED"].includes(c.statusCode)).length
  const approved = claims.filter((c: any) => c.statusCode === "APPROVED").length
  const totalPaid = claims.reduce((sum: number, c: any) => sum + Number(c.paidAmount || 0), 0)

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground flex items-center gap-3">
          <div className="p-2 rounded-xl" style={{ background: "linear-gradient(135deg, #ef4444, #f97316)" }}>
            <AlertCircle className="h-6 w-6 text-white" />
          </div>
          Claims
        </h1>
        <p className="text-muted-foreground mt-1">Group Life claims registration & processing</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[
          { label: "Total Claims", value: total, icon: AlertCircle, color: "#ef4444" },
          { label: "Pending", value: pending, icon: FileWarning, color: "#f59e0b" },
          { label: "Approved", value: approved, icon: CheckCircle, color: "#10b981" },
          { label: "Total Paid", value: formatCurrency(totalPaid), icon: Banknote, color: "#3b82f6" },
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

      {/* Search */}
      <div className="flex items-center gap-3 mb-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search claims..."
            className="h-10 w-full rounded-xl border border-border bg-card pl-10 pr-4 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40" />
        </div>
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
        {loading ? (
          <div className="flex items-center justify-center p-16"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>
        ) : claims.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-16 text-muted-foreground">
            <AlertCircle className="h-12 w-12 mb-3 opacity-40" />
            <p className="text-lg font-medium">No claims found</p>
            <p className="text-sm">Claims are registered against active scheme members.</p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-border bg-secondary/30">
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Claim #</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Member</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Scheme</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Type</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Status</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-muted-foreground">Claimed</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-muted-foreground">Paid</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-muted-foreground">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {claims.map((c: any) => {
                const statusStyle = CLAIM_STATUS_STYLES[c.statusCode] ?? CLAIM_STATUS_STYLES.REGISTERED
                return (
                  <tr key={c.id} className="group transition hover:bg-secondary/20 cursor-pointer" onClick={() => viewDetail(c.id)}>
                    <td className="px-4 py-3.5">
                      <span className="text-sm font-mono font-semibold text-primary">{c.claimNumber}</span>
                      <p className="text-xs text-muted-foreground mt-0.5">{c.incidentDate}</p>
                    </td>
                    <td className="px-4 py-3.5">
                      <p className="text-sm font-medium text-foreground">{c.memberName ?? "—"}</p>
                      <p className="text-xs text-muted-foreground font-mono">{c.memberNumber ?? ""}</p>
                    </td>
                    <td className="px-4 py-3.5 text-sm font-mono text-foreground">{c.schemeNumber ?? "—"}</td>
                    <td className="px-4 py-3.5 text-sm text-foreground">{c.claimTypeName ?? "—"}</td>
                    <td className="px-4 py-3.5">
                      <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${statusStyle.bg} ${statusStyle.text}`}>
                        {c.statusName ?? c.statusCode}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-sm text-foreground text-right font-mono">{formatCurrency(c.claimAmount)}</td>
                    <td className="px-4 py-3.5 text-sm text-foreground text-right font-mono">{formatCurrency(c.paidAmount)}</td>
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

      {/* Claim Detail Slide-over */}
      {selectedClaim && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/50 backdrop-blur-sm" onClick={() => setSelectedClaim(null)}>
          <div className="w-full max-w-2xl overflow-y-auto bg-card border-l border-border shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="sticky top-0 z-10 border-b border-border bg-card/95 backdrop-blur-sm px-6 py-4 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-foreground">{selectedClaim.claimNumber}</h2>
                {(() => {
                  const style = CLAIM_STATUS_STYLES[selectedClaim.statusCode] ?? CLAIM_STATUS_STYLES.REGISTERED
                  return <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${style.bg} ${style.text}`}>{selectedClaim.statusName ?? selectedClaim.statusCode}</span>
                })()}
              </div>
              <button onClick={() => setSelectedClaim(null)} className="p-2 rounded-lg hover:bg-secondary"><X className="h-5 w-5 text-foreground" /></button>
            </div>
            {detailLoading ? (
              <div className="flex items-center justify-center p-16"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>
            ) : (
              <div className="p-6 space-y-6">
                <div className="grid grid-cols-2 gap-4">
                  {[
                    { label: "Member", value: selectedClaim.memberName },
                    { label: "Scheme", value: selectedClaim.schemeNumber },
                    { label: "Claim Type", value: selectedClaim.claimTypeName },
                    { label: "Reason", value: selectedClaim.claimReasonName },
                    { label: "Incident Date", value: selectedClaim.incidentDate },
                    { label: "Notification Date", value: selectedClaim.notificationDate },
                    { label: "Claimant", value: selectedClaim.claimantName },
                    { label: "Claimant Phone", value: selectedClaim.claimantPhone },
                  ].map((f) => (
                    <div key={f.label}>
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{f.label}</p>
                      <p className="text-sm font-medium text-foreground mt-0.5">{f.value ?? "—"}</p>
                    </div>
                  ))}
                </div>

                {/* Financial */}
                <div className="rounded-xl border border-border bg-secondary/20 p-4">
                  <h3 className="text-sm font-semibold text-foreground mb-3">Financial Summary</h3>
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    <div>
                      <p className="text-xs text-muted-foreground">Sum at Claim</p>
                      <p className="text-lg font-bold text-foreground">{formatCurrency(selectedClaim.sumAssuredAtClaim)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Claimed</p>
                      <p className="text-lg font-bold text-amber-400">{formatCurrency(selectedClaim.claimAmount)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Approved</p>
                      <p className="text-lg font-bold text-emerald-400">{formatCurrency(selectedClaim.approvedAmount)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Paid</p>
                      <p className="text-lg font-bold text-primary">{formatCurrency(selectedClaim.paidAmount)}</p>
                    </div>
                  </div>
                </div>

                {/* Installments */}
                {selectedClaim.installments?.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-foreground mb-3">Payment Installments ({selectedClaim.installments.length})</h3>
                    <div className="space-y-2">
                      {selectedClaim.installments.map((inst: any) => (
                        <div key={inst.id} className="rounded-xl border border-border p-3 flex items-center justify-between">
                          <div>
                            <p className="text-sm font-medium text-foreground">Installment #{inst.installmentNumber}</p>
                            <p className="text-xs text-muted-foreground">Due: {inst.dueDate}</p>
                          </div>
                          <div className="text-right">
                            <p className="text-sm font-mono text-foreground">{formatCurrency(inst.amount)}</p>
                            <p className="text-xs text-muted-foreground">{inst.statusDisplay ?? inst.status}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex items-center gap-3 pt-2 flex-wrap">
                  {selectedClaim.statusCode === "REGISTERED" && (
                    <button onClick={() => handleAction("assess", selectedClaim.id)} disabled={!!actionLoading}
                      className="flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium text-white bg-amber-600 hover:bg-amber-700 transition disabled:opacity-50">
                      {actionLoading === "assess" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Eye className="h-4 w-4" />} Assess
                    </button>
                  )}
                  {selectedClaim.statusCode === "ASSESSED" && (
                    <>
                      <button onClick={() => handleAction("approve", selectedClaim.id)} disabled={!!actionLoading}
                        className="flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 transition disabled:opacity-50">
                        {actionLoading === "approve" ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle className="h-4 w-4" />} Approve
                      </button>
                      <button onClick={() => handleAction("reject", selectedClaim.id)} disabled={!!actionLoading}
                        className="flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 transition disabled:opacity-50">
                        {actionLoading === "reject" ? <Loader2 className="h-4 w-4 animate-spin" /> : <XCircle className="h-4 w-4" />} Reject
                      </button>
                    </>
                  )}
                  {selectedClaim.statusCode === "APPROVED" && (
                    <button onClick={() => handleAction("pay", selectedClaim.id)} disabled={!!actionLoading}
                      className="flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium text-white transition disabled:opacity-50"
                      style={{ background: "linear-gradient(135deg, #3b82f6, #6366f1)" }}>
                      {actionLoading === "pay" ? <Loader2 className="h-4 w-4 animate-spin" /> : <DollarSign className="h-4 w-4" />} Record Payment
                    </button>
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

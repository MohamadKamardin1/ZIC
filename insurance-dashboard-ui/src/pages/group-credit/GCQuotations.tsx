import { useState, useEffect, useCallback } from "react"
import {
  FileText, Plus, Search, Eye, CheckCircle, XCircle, ArrowRightCircle,
  Loader2, Filter, Calendar, DollarSign, Users, ChevronDown, X
} from "lucide-react"
import { gcQuotations, gcSetup } from "../../lib/gc-api"

const STATUS_STYLES: Record<string, { bg: string; text: string }> = {
  DRAFT: { bg: "bg-slate-500/10", text: "text-slate-400" },
  SUBMITTED: { bg: "bg-blue-500/10", text: "text-blue-400" },
  UNDER_REVIEW: { bg: "bg-amber-500/10", text: "text-amber-400" },
  APPROVED: { bg: "bg-emerald-500/10", text: "text-emerald-400" },
  DECLINED: { bg: "bg-red-500/10", text: "text-red-400" },
  CONVERTED: { bg: "bg-purple-500/10", text: "text-purple-400" },
  EXPIRED: { bg: "bg-gray-500/10", text: "text-gray-400" },
}

function StatusBadge({ status, label }: { status: string; label?: string }) {
  const style = STATUS_STYLES[status] ?? STATUS_STYLES.DRAFT
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${style.bg} ${style.text}`}>
      {label ?? status.replace(/_/g, " ")}
    </span>
  )
}

function formatCurrency(val: any) {
  if (!val) return "—"
  return new Intl.NumberFormat("en-US", { style: "decimal", minimumFractionDigits: 0 }).format(Number(val))
}

export default function GCQuotations() {
  const [quotations, setQuotations] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState("")
  const [selectedQuotation, setSelectedQuotation] = useState<any>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [products, setProducts] = useState<any[]>([])
  const [schemeTypes, setSchemeTypes] = useState<any[]>([])
  const [formData, setFormData] = useState<Record<string, any>>({})
  const [saving, setSaving] = useState(false)
  const [actionLoading, setActionLoading] = useState("")

  const loadQuotations = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string> = {}
      if (search) params.search = search
      if (statusFilter) params.status = statusFilter
      const res = await gcQuotations.list(params)
      setQuotations(res?.results ?? res?.data ?? res ?? [])
    } catch (err: any) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [search, statusFilter])

  useEffect(() => { loadQuotations() }, [loadQuotations])

  useEffect(() => {
    Promise.all([
      gcSetup.listProducts().then((r: any) => setProducts(r?.results ?? r?.data ?? r ?? [])),
      gcSetup.listSchemeTypes().then((r: any) => setSchemeTypes(r?.results ?? r?.data ?? r ?? [])),
    ]).catch(() => {})
  }, [])

  async function viewDetail(id: string) {
    setDetailLoading(true)
    try {
      const detail = await gcQuotations.get(id)
      setSelectedQuotation(detail)
    } catch (err: any) {
      alert(err.message)
    } finally {
      setDetailLoading(false)
    }
  }

  async function handleCreate() {
    setSaving(true)
    try {
      await gcQuotations.create(formData)
      setShowCreateModal(false)
      setFormData({})
      await loadQuotations()
    } catch (err: any) {
      alert(err.message)
    } finally {
      setSaving(false)
    }
  }

  async function handleAction(action: string, id: string) {
    setActionLoading(action)
    try {
      if (action === "approve") await gcQuotations.approve(id)
      else if (action === "decline") await gcQuotations.decline(id, "Declined by user")
      else if (action === "convert") await gcQuotations.convertToScheme(id, {})
      await viewDetail(id)
      await loadQuotations()
    } catch (err: any) {
      alert(err.message)
    } finally {
      setActionLoading("")
    }
  }

  // Stats
  const total = quotations.length
  const approved = quotations.filter((q: any) => q.status === "APPROVED").length
  const pending = quotations.filter((q: any) => ["DRAFT", "SUBMITTED", "UNDER_REVIEW"].includes(q.status)).length
  const totalPremium = quotations.reduce((sum: number, q: any) => sum + Number(q.totalAnnualPremium || 0), 0)

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-3">
            <div className="p-2 rounded-xl" style={{ background: "linear-gradient(135deg, #3b82f6, #6366f1)" }}>
              <FileText className="h-6 w-6 text-white" />
            </div>
            Quotations
          </h1>
          <p className="text-muted-foreground mt-1">Manage Group Credit insurance quotations</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-medium text-white shadow-lg transition hover:opacity-90"
          style={{ background: "linear-gradient(135deg, #3b82f6, #6366f1)" }}
        >
          <Plus className="h-4 w-4" /> New Quotation
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[
          { label: "Total", value: total, icon: FileText, color: "#6366f1" },
          { label: "Pending", value: pending, icon: Filter, color: "#f59e0b" },
          { label: "Approved", value: approved, icon: CheckCircle, color: "#10b981" },
          { label: "Total Premium", value: formatCurrency(totalPremium), icon: DollarSign, color: "#3b82f6" },
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
            placeholder="Search quotations..."
            className="h-10 w-full rounded-xl border border-border bg-card pl-10 pr-4 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="h-10 rounded-xl border border-border bg-card px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
        >
          <option value="">All Statuses</option>
          {Object.keys(STATUS_STYLES).map((s) => (
            <option key={s} value={s}>{s.replace(/_/g, " ")}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
        {loading ? (
          <div className="flex items-center justify-center p-16"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>
        ) : quotations.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-16 text-muted-foreground">
            <FileText className="h-12 w-12 mb-3 opacity-40" />
            <p className="text-lg font-medium">No quotations found</p>
            <p className="text-sm">Create your first quotation to get started.</p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-border bg-secondary/30">
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Quotation #</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Partner</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Product</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Status</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Members</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-muted-foreground">Premium</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-muted-foreground">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {quotations.map((q: any) => (
                <tr key={q.id} className="group transition hover:bg-secondary/20 cursor-pointer" onClick={() => viewDetail(q.id)}>
                  <td className="px-4 py-3.5">
                    <span className="text-sm font-mono font-semibold text-primary">{q.quotationNumber}</span>
                    <p className="text-xs text-muted-foreground mt-0.5">{q.quotationDate}</p>
                  </td>
                  <td className="px-4 py-3.5 text-sm text-foreground">{q.partnerName ?? "—"}</td>
                  <td className="px-4 py-3.5 text-sm text-foreground">{q.productName ?? "—"}</td>
                  <td className="px-4 py-3.5"><StatusBadge status={q.status} label={q.statusDisplay} /></td>
                  <td className="px-4 py-3.5 text-sm text-foreground">{q.totalMembers ?? 0}</td>
                  <td className="px-4 py-3.5 text-sm text-foreground text-right font-mono">{formatCurrency(q.totalAnnualPremium)}</td>
                  <td className="px-4 py-3.5 text-right">
                    <button onClick={(e) => { e.stopPropagation(); viewDetail(q.id) }} className="p-1.5 rounded-lg hover:bg-secondary text-muted-foreground hover:text-foreground transition">
                      <Eye className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Detail Slide-over */}
      {selectedQuotation && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/50 backdrop-blur-sm" onClick={() => setSelectedQuotation(null)}>
          <div className="w-full max-w-2xl overflow-y-auto bg-card border-l border-border shadow-2xl animate-in slide-in-from-right" onClick={(e) => e.stopPropagation()}>
            <div className="sticky top-0 z-10 border-b border-border bg-card/95 backdrop-blur-sm px-6 py-4 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-foreground">{selectedQuotation.quotationNumber}</h2>
                <StatusBadge status={selectedQuotation.status} label={selectedQuotation.statusDisplay} />
              </div>
              <button onClick={() => setSelectedQuotation(null)} className="p-2 rounded-lg hover:bg-secondary"><X className="h-5 w-5 text-foreground" /></button>
            </div>

            {detailLoading ? (
              <div className="flex items-center justify-center p-16"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>
            ) : (
              <div className="p-6 space-y-6">
                {/* Key Info */}
                <div className="grid grid-cols-2 gap-4">
                  {[
                    { label: "Partner", value: selectedQuotation.partnerName },
                    { label: "Product", value: selectedQuotation.productName },
                    { label: "Scheme Type", value: selectedQuotation.schemeTypeName },
                    { label: "Date", value: selectedQuotation.quotationDate },
                    { label: "Valid Until", value: selectedQuotation.validUntil ?? "—" },
                    { label: "Prepared By", value: selectedQuotation.preparedByName ?? "—" },
                  ].map((f) => (
                    <div key={f.label}>
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{f.label}</p>
                      <p className="text-sm font-medium text-foreground mt-0.5">{f.value ?? "—"}</p>
                    </div>
                  ))}
                </div>

                {/* Financials */}
                <div className="rounded-xl border border-border bg-secondary/20 p-4">
                  <h3 className="text-sm font-semibold text-foreground mb-3">Financial Summary</h3>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <p className="text-xs text-muted-foreground">Total Members</p>
                      <p className="text-lg font-bold text-foreground">{selectedQuotation.totalMembers ?? 0}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Total Sum Assured</p>
                      <p className="text-lg font-bold text-foreground">{formatCurrency(selectedQuotation.totalSumAssured)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Annual Premium</p>
                      <p className="text-lg font-bold text-primary">{formatCurrency(selectedQuotation.totalAnnualPremium)}</p>
                    </div>
                  </div>
                </div>

                {/* Categories */}
                {selectedQuotation.categories?.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-foreground mb-3">Categories</h3>
                    <div className="space-y-2">
                      {selectedQuotation.categories.map((cat: any) => (
                        <div key={cat.id} className="rounded-xl border border-border p-3 flex items-center justify-between">
                          <div>
                            <p className="text-sm font-medium text-foreground">{cat.categoryName}</p>
                            <p className="text-xs text-muted-foreground">{cat.memberCount ?? 0} members</p>
                          </div>
                          <p className="text-sm font-mono font-semibold text-foreground">{formatCurrency(cat.annualPremium)}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex items-center gap-3 pt-2">
                  {["DRAFT", "SUBMITTED", "UNDER_REVIEW"].includes(selectedQuotation.status) && (
                    <button
                      onClick={() => handleAction("approve", selectedQuotation.id)}
                      disabled={!!actionLoading}
                      className="flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 transition disabled:opacity-50"
                    >
                      {actionLoading === "approve" ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle className="h-4 w-4" />}
                      Approve
                    </button>
                  )}
                  {!["CONVERTED", "EXPIRED", "DECLINED"].includes(selectedQuotation.status) && (
                    <button
                      onClick={() => handleAction("decline", selectedQuotation.id)}
                      disabled={!!actionLoading}
                      className="flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 transition disabled:opacity-50"
                    >
                      {actionLoading === "decline" ? <Loader2 className="h-4 w-4 animate-spin" /> : <XCircle className="h-4 w-4" />}
                      Decline
                    </button>
                  )}
                  {selectedQuotation.status === "APPROVED" && (
                    <button
                      onClick={() => handleAction("convert", selectedQuotation.id)}
                      disabled={!!actionLoading}
                      className="flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium text-white shadow-lg transition hover:opacity-90 disabled:opacity-50"
                      style={{ background: "linear-gradient(135deg, #8b5cf6, #6366f1)" }}
                    >
                      {actionLoading === "convert" ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRightCircle className="h-4 w-4" />}
                      Convert to Scheme
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={() => setShowCreateModal(false)}>
          <div className="w-full max-w-lg rounded-2xl border border-border bg-card p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-bold text-foreground">New Quotation</h2>
              <button onClick={() => setShowCreateModal(false)} className="p-1.5 rounded-lg hover:bg-secondary"><X className="h-5 w-5 text-foreground" /></button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium text-foreground">Product <span className="text-red-400">*</span></label>
                <select
                  value={formData.product ?? ""}
                  onChange={(e) => setFormData({ ...formData, product: e.target.value })}
                  className="h-10 w-full rounded-xl border border-border bg-secondary/30 px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                >
                  <option value="">Select product...</option>
                  {products.map((p: any) => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium text-foreground">Scheme Type</label>
                <select
                  value={formData.schemeType ?? ""}
                  onChange={(e) => setFormData({ ...formData, schemeType: e.target.value })}
                  className="h-10 w-full rounded-xl border border-border bg-secondary/30 px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                >
                  <option value="">Select type...</option>
                  {schemeTypes.map((t: any) => <option key={t.id} value={t.id}>{t.name}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-foreground">Total Members</label>
                  <input type="number" value={formData.totalMembers ?? ""} onChange={(e) => setFormData({ ...formData, totalMembers: Number(e.target.value) })}
                    className="h-10 w-full rounded-xl border border-border bg-secondary/30 px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40" />
                </div>
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-foreground">Annual Premium</label>
                  <input type="number" value={formData.totalAnnualPremium ?? ""} onChange={(e) => setFormData({ ...formData, totalAnnualPremium: Number(e.target.value) })}
                    className="h-10 w-full rounded-xl border border-border bg-secondary/30 px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40" />
                </div>
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium text-foreground">Notes</label>
                <textarea value={formData.notes ?? ""} onChange={(e) => setFormData({ ...formData, notes: e.target.value })} rows={3}
                  className="w-full rounded-xl border border-border bg-secondary/30 px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40" />
              </div>
            </div>
            <div className="mt-6 flex items-center justify-end gap-3">
              <button onClick={() => setShowCreateModal(false)} className="rounded-xl border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-secondary transition">Cancel</button>
              <button onClick={handleCreate} disabled={saving}
                className="flex items-center gap-2 rounded-xl px-5 py-2 text-sm font-medium text-white shadow-lg transition hover:opacity-90 disabled:opacity-50"
                style={{ background: "linear-gradient(135deg, #3b82f6, #6366f1)" }}
              >
                {saving && <Loader2 className="h-4 w-4 animate-spin" />} Create Quotation
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

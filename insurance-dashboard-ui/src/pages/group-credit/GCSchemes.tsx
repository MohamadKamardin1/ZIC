import { useState, useEffect, useCallback } from "react"
import {
  Shield, Search, Eye, Loader2, Calendar, AlertTriangle,
  Users, DollarSign, X, Plus
} from "lucide-react"
import { gcSchemes } from "../../lib/gc-api"

function formatCurrency(val: any) {
  if (!val) return "—"
  return new Intl.NumberFormat("en-US", { style: "decimal", minimumFractionDigits: 0 }).format(Number(val))
}

function StatusBadge({ code, name }: { code: string; name: string }) {
  const colors: Record<string, string> = {
    ACTIVE: "bg-emerald-500/10 text-emerald-400",
    INACTIVE: "bg-slate-500/10 text-slate-400",
    SUSPENDED: "bg-red-500/10 text-red-400",
    LAPSED: "bg-orange-500/10 text-orange-400",
    CANCELLED: "bg-red-500/10 text-red-400",
  }
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${colors[code] ?? "bg-blue-500/10 text-blue-400"}`}>
      {name || code}
    </span>
  )
}

export default function GCSchemes() {
  const [schemes, setSchemes] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [selectedScheme, setSelectedScheme] = useState<any>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [summary, setSummary] = useState<any>(null)

  const loadSchemes = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string> = {}
      if (search) params.search = search
      const res = await gcSchemes.list(params)
      setSchemes(res?.results ?? res?.data ?? res ?? [])
    } catch (err: any) { console.error(err) }
    finally { setLoading(false) }
  }, [search])

  useEffect(() => { loadSchemes() }, [loadSchemes])

  useEffect(() => {
    gcSchemes.dashboardSummary().then(setSummary).catch(() => {})
  }, [])

  async function viewDetail(id: string) {
    setDetailLoading(true)
    try {
      const detail = await gcSchemes.get(id)
      setSelectedScheme(detail)
    } catch (err: any) { alert(err.message) }
    finally { setDetailLoading(false) }
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground flex items-center gap-3">
          <div className="p-2 rounded-xl" style={{ background: "linear-gradient(135deg, #10b981, #059669)" }}>
            <Shield className="h-6 w-6 text-white" />
          </div>
          Schemes
        </h1>
        <p className="text-muted-foreground mt-1">Group Credit policy management</p>
      </div>

      {/* Dashboard Stats */}
      {summary && (
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
          {[
            { label: "Total Schemes", value: summary.totalSchemes, icon: Shield, color: "#10b981" },
            { label: "Active", value: summary.activeSchemes, icon: Shield, color: "#3b82f6" },
            { label: "Total Members", value: formatCurrency(summary.totalMembers), icon: Users, color: "#8b5cf6" },
            { label: "Total Premium", value: formatCurrency(summary.totalPremium), icon: DollarSign, color: "#6366f1" },
            { label: "Expiring Soon", value: summary.expiringSoon, icon: AlertTriangle, color: summary.expiringSoon > 0 ? "#ef4444" : "#6b7280" },
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
      )}

      {/* Search */}
      <div className="flex items-center gap-3 mb-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search schemes..."
            className="h-10 w-full rounded-xl border border-border bg-card pl-10 pr-4 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40" />
        </div>
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
        {loading ? (
          <div className="flex items-center justify-center p-16"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>
        ) : schemes.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-16 text-muted-foreground">
            <Shield className="h-12 w-12 mb-3 opacity-40" />
            <p className="text-lg font-medium">No schemes found</p>
            <p className="text-sm">Schemes are created by converting approved quotations.</p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-border bg-secondary/30">
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Scheme #</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Partner</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Product</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Status</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Period</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-muted-foreground">Members</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-muted-foreground">Premium</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-muted-foreground">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {schemes.map((s: any) => (
                <tr key={s.id} className="group transition hover:bg-secondary/20 cursor-pointer" onClick={() => viewDetail(s.id)}>
                  <td className="px-4 py-3.5">
                    <span className="text-sm font-mono font-semibold text-primary">{s.schemeNumber}</span>
                  </td>
                  <td className="px-4 py-3.5 text-sm text-foreground">{s.partnerName ?? "—"}</td>
                  <td className="px-4 py-3.5 text-sm text-foreground">{s.productName ?? "—"}</td>
                  <td className="px-4 py-3.5"><StatusBadge code={s.statusCode ?? ""} name={s.statusName ?? s.status} /></td>
                  <td className="px-4 py-3.5">
                    <p className="text-sm text-foreground">{s.inceptionDate} → {s.expiryDate ?? "—"}</p>
                    {s.isExpired && <span className="text-xs text-red-400 font-medium">Expired</span>}
                    {!s.isExpired && s.daysUntilExpiry != null && s.daysUntilExpiry <= 30 && (
                      <span className="text-xs text-amber-400 font-medium flex items-center gap-1"><AlertTriangle className="h-3 w-3" />{s.daysUntilExpiry}d left</span>
                    )}
                  </td>
                  <td className="px-4 py-3.5 text-sm text-foreground text-right">{s.totalMembers ?? 0}</td>
                  <td className="px-4 py-3.5 text-sm text-foreground text-right font-mono">{formatCurrency(s.totalAnnualPremium)}</td>
                  <td className="px-4 py-3.5 text-right">
                    <button className="p-1.5 rounded-lg hover:bg-secondary text-muted-foreground hover:text-foreground transition">
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
      {selectedScheme && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/50 backdrop-blur-sm" onClick={() => setSelectedScheme(null)}>
          <div className="w-full max-w-2xl overflow-y-auto bg-card border-l border-border shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="sticky top-0 z-10 border-b border-border bg-card/95 backdrop-blur-sm px-6 py-4 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-foreground">{selectedScheme.schemeNumber}</h2>
                <StatusBadge code={selectedScheme.statusCode ?? ""} name={selectedScheme.statusName ?? ""} />
              </div>
              <button onClick={() => setSelectedScheme(null)} className="p-2 rounded-lg hover:bg-secondary"><X className="h-5 w-5 text-foreground" /></button>
            </div>
            {detailLoading ? (
              <div className="flex items-center justify-center p-16"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>
            ) : (
              <div className="p-6 space-y-6">
                <div className="grid grid-cols-2 gap-4">
                  {[
                    { label: "Partner", value: selectedScheme.partnerName },
                    { label: "Product", value: selectedScheme.productName },
                    { label: "Scheme Type", value: selectedScheme.schemeTypeName },
                    { label: "Inception", value: selectedScheme.inceptionDate },
                    { label: "Expiry", value: selectedScheme.expiryDate },
                    { label: "FCL", value: formatCurrency(selectedScheme.freeCoverLimit) },
                    { label: "Currency", value: selectedScheme.currency },
                    { label: "Source Quotation", value: selectedScheme.convertedFromQuotationNumber ?? "—" },
                  ].map((f) => (
                    <div key={f.label}>
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{f.label}</p>
                      <p className="text-sm font-medium text-foreground mt-0.5">{f.value ?? "—"}</p>
                    </div>
                  ))}
                </div>

                <div className="rounded-xl border border-border bg-secondary/20 p-4">
                  <h3 className="text-sm font-semibold text-foreground mb-3">Financial Summary</h3>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <p className="text-xs text-muted-foreground">Total Members</p>
                      <p className="text-lg font-bold text-foreground">{selectedScheme.totalMembers ?? 0}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Sum Assured</p>
                      <p className="text-lg font-bold text-foreground">{formatCurrency(selectedScheme.totalSumAssured)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Annual Premium</p>
                      <p className="text-lg font-bold text-primary">{formatCurrency(selectedScheme.totalAnnualPremium)}</p>
                    </div>
                  </div>
                </div>

                {/* Categories */}
                {selectedScheme.categories?.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-foreground mb-3">Categories ({selectedScheme.categories.length})</h3>
                    <div className="space-y-2">
                      {selectedScheme.categories.map((cat: any) => (
                        <div key={cat.id} className="rounded-xl border border-border p-3">
                          <p className="text-sm font-medium text-foreground">{cat.categoryName}</p>
                          <p className="text-xs text-muted-foreground mt-1">{cat.description ?? ""}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Riders */}
                {selectedScheme.riders?.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-foreground mb-3">Riders ({selectedScheme.riders.length})</h3>
                    <div className="space-y-2">
                      {selectedScheme.riders.map((r: any) => (
                        <div key={r.id} className="rounded-xl border border-border p-3 flex items-center justify-between">
                          <div>
                            <p className="text-sm font-medium text-foreground">{r.riderName}</p>
                            <p className="text-xs text-muted-foreground">{r.riderType}</p>
                          </div>
                          <span className="text-sm font-mono text-foreground">{r.ratePerMille}‰</span>
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

import { useEffect, useState, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { Search, ChevronLeft, ChevronRight, Loader2, Eye, Pencil } from "lucide-react"
import { SkeletonTable } from "../../components/shared/Skeleton"
import { listPartners } from "../../lib/api"
import { useDataRefresh } from "../../lib/useDataRefresh"
import type { PartnerListItem } from "../../lib/types"

export default function PartnerList() {
  const navigate = useNavigate()
  const [items, setItems] = useState<PartnerListItem[]>([])
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [search, setSearch] = useState("")
  const [page, setPage] = useState(1)
  const pageSize = 20

  const refreshKey = useDataRefresh("partners")

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError("")
    try {
      const result = await listPartners({
        page,
        per_page: pageSize,
        search: search || undefined,
      })
      setItems(result.results)
      setCount(result.count)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load partners")
    } finally {
      setLoading(false)
    }
  }, [page, search])

  useEffect(() => {
    fetchData()
  }, [fetchData, refreshKey])

  const totalPages = Math.max(1, Math.ceil(count / pageSize))

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-foreground">Partners</h1>
        <span className="text-sm text-muted-foreground">{count} total</span>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <input
          type="text"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}
          placeholder="Search partners..."
          className="w-full pl-10 pr-4 py-2 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
        />
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-[var(--color-bg-destructive-soft)] text-[var(--color-text-destructive-soft)] text-sm">
          {error}
        </div>
      )}

      <div className="rounded-xl border border-border bg-card overflow-hidden">
        {loading ? (
          <SkeletonTable rows={8} cols={7} />
        ) : items.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            <h3 className="text-lg font-semibold text-foreground">No Partners Found</h3>
            <p className="mt-1 text-sm">
              {search ? "Try a different search term." : "No partners have been created yet."}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border bg-muted/50">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Partner #</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Name</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Type</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Email</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Mobile</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Status</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {items.map((partner) => (
                  <tr key={partner.id} className="hover:bg-muted/30 transition-colors">
                    <td className="px-4 py-3 text-sm font-medium text-foreground">{partner.partnerNumber}</td>
                    <td className="px-4 py-3 text-sm text-foreground">{partner.displayName}</td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">{partner.partnerCategory || partner.partnerType}</td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">{partner.email}</td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">{partner.mobileNumber}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        partner.status === "ACTIVE"
                          ? "bg-[var(--color-bg-success-soft)] text-[var(--color-text-success-soft)]"
                          : partner.status === "INACTIVE"
                          ? "bg-[var(--color-bg-destructive-soft)] text-[var(--color-text-destructive-soft)]"
                          : "bg-[var(--color-bg-warning-soft)] text-[var(--color-text-warning-soft)]"
                      }`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${
                          partner.status === "ACTIVE"
                            ? "bg-[var(--color-feedback-success)]"
                            : partner.status === "INACTIVE"
                            ? "bg-[var(--color-feedback-destructive)]"
                            : "bg-[var(--color-feedback-warning)]"
                        }`} />
                        {partner.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => navigate(`/partners/${partner.id}/edit`)}
                          className="p-2 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                          title="Edit Partner"
                        >
                          <Pencil className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => navigate(`/partners/${partner.id}`)}
                          className="p-2 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                          title="View Partner"
                        >
                          <Eye className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="p-2 rounded-lg hover:bg-muted disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="text-sm text-muted-foreground">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="p-2 rounded-lg hover:bg-muted disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  )
}

import { useEffect, useState, useCallback, useMemo } from "react"
import { useNavigate } from "react-router-dom"
import {
  Search,
  Plus,
  Upload,
  ChevronLeft,
  ChevronRight,
  Eye,
  Pencil,
  Trash2,
  Loader2,
  Filter,
  X,
  Users,
} from "lucide-react"
import BulkUploadModal from "../../components/onboarding/BulkUploadModal"
import ConfirmDialog from "../../components/shared/ConfirmDialog"
import { SkeletonTable } from "../../components/shared/Skeleton"
import {
  listApplications,
  deleteApplication,
  listPartners,
} from "../../lib/api"
import { useDataRefresh } from "../../lib/useDataRefresh"
import type { PartnerApplicationList, ApplicationStatus, PartnerListItem } from "../../lib/types"
import { useWorkflowConfig } from "../../config/ConfigurationHooks"

const STATUSES: { value: ApplicationStatus | ""; label: string }[] = [
  { value: "", label: "All Statuses" },
  { value: "DRAFT", label: "Draft" },
  { value: "SUBMITTED", label: "Submitted" },
  { value: "UNDER_REVIEW", label: "Under Review" },
  { value: "PENDING_DOCUMENTS", label: "Pending Docs" },
  { value: "COMPLIANCE_CHECK", label: "Compliance" },
  { value: "APPROVED", label: "Approved" },
  { value: "CONVERTED", label: "Converted" },
  { value: "REJECTED", label: "Rejected" },
  { value: "SUSPENDED", label: "Suspended" },
]

const PARTNER_TYPES = [
  { value: "", label: "All Types" },
  { value: "INDIVIDUAL", label: "Individual" },
  { value: "CORPORATE", label: "Corporate" },
]

function statusVariant(status: ApplicationStatus): { bg: string; text: string; dot: string } {
  const active = { bg: "bg-[var(--color-bg-success-soft)]", text: "text-[var(--color-text-success-soft)]", dot: "bg-[var(--color-feedback-success)]" }
  const pending = { bg: "bg-[var(--color-bg-warning-soft)]", text: "text-[var(--color-text-warning-soft)]", dot: "bg-[var(--color-feedback-warning)]" }
  const inactive = { bg: "bg-[var(--color-bg-destructive-soft)]", text: "text-[var(--color-text-destructive-soft)]", dot: "bg-[var(--color-feedback-destructive)]" }
  switch (status) {
    case "ACTIVE":
    case "APPROVED":
    case "CONVERTED":
      return active
    case "REJECTED":
    case "SUSPENDED":
      return inactive
    default:
      return pending
  }
}

function getPageNumbers(current: number, total: number): (number | "...")[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
  const pages: (number | "...")[] = [1]
  if (current > 3) pages.push("...")
  const start = Math.max(2, current - 1)
  const end = Math.min(total - 1, current + 1)
  for (let i = start; i <= end; i++) pages.push(i)
  if (current < total - 2) pages.push("...")
  pages.push(total)
  return pages
}

export default function OnboardingList() {
  const navigate = useNavigate()
  const [items, setItems] = useState<PartnerApplicationList[]>([])
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState<ApplicationStatus | "">("")
  const [typeFilter, setTypeFilter] = useState("")
  const workflowConfig = useWorkflowConfig()
  const statusLabels = workflowConfig?.status_labels ?? {
    ACTIVE: "Active", DRAFT: "Draft", SUBMITTED: "Submitted",
    UNDER_REVIEW: "Under Review", PENDING_DOCUMENTS: "Pending Docs",
    COMPLIANCE_CHECK: "Compliance", APPROVED: "Approved",
    CONVERTED: "Converted", REJECTED: "Rejected", SUSPENDED: "Suspended",
  }
  const [deleting, setDeleting] = useState<string | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [searchValue, setSearchValue] = useState("")
  const [showBulkUpload, setShowBulkUpload] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const refreshKey = useDataRefresh("partners")

  const [viewMode, setViewMode] = useState<"applications" | "partners">("applications")
  const [partnerItems, setPartnerItems] = useState<PartnerListItem[]>([])
  const [partnerCount, setPartnerCount] = useState(0)
  const [partnerPage, setPartnerPage] = useState(1)
  const partnerPageSize = 20

  const load = useCallback(async () => {
    setLoading(true)
    setError("")
    try {
      const result = await listApplications({
        page,
        pageSize,
        search: search || undefined,
        status: statusFilter || undefined,
        partnerType: typeFilter || undefined,
        ordering: "-created_at",
      })
      setItems(result.results ?? [])
      setCount(result.count ?? 0)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load applications")
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, search, statusFilter, typeFilter, refreshKey])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (viewMode !== "partners") return
    let cancelled = false
    ;(async () => {
      setLoading(true)
      setError("")
      try {
        const result = await listPartners({ page: partnerPage, per_page: partnerPageSize, search: search || undefined })
        if (!cancelled) {
          setPartnerItems(result.results ?? [])
          setPartnerCount(result.count ?? 0)
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load partners")
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [viewMode, partnerPage, search, refreshKey])

  function handleSearchKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      setSearch(searchValue)
      setPage(1)
    }
  }

  function handleClearSearch() {
    setSearchValue("")
    setSearch("")
    setPage(1)
  }

  function hasActiveFilters() {
    return statusFilter !== "" || typeFilter !== "" || search !== ""
  }

  function clearAllFilters() {
    setStatusFilter("")
    setTypeFilter("")
    setSearch("")
    setSearchValue("")
    setPage(1)
  }

  function handleDeleteClick(id: string, e: React.MouseEvent) {
    e.stopPropagation()
    setDeleteTarget(id)
  }

  async function handleDeleteConfirm() {
    if (!deleteTarget) return
    setDeleting(deleteTarget)
    try {
      await deleteApplication(deleteTarget)
      load()
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete")
    } finally {
      setDeleting(null)
      setDeleteTarget(null)
    }
  }

  const totalPages = Math.ceil(count / pageSize)
  const pageNumbers = useMemo(() => getPageNumbers(page, totalPages), [page, totalPages])

  return (
    <div className="flex flex-col gap-4">
      {/* View Toggle */}
      <div className="flex gap-1 border-b border-border">
        <button
          onClick={() => { setViewMode("applications"); setPage(1) }}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            viewMode === "applications"
              ? "border-primary text-foreground"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          Applications
        </button>
        <button
          onClick={() => { setViewMode("partners"); setPartnerPage(1) }}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            viewMode === "partners"
              ? "border-primary text-foreground"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Users className="h-3.5 w-3.5 inline mr-1.5" />
          Partners
        </button>
      </div>

      {/* Page header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-foreground">Partner Onboarding</h1>
          <p className="text-sm text-muted-foreground">
            {viewMode === "applications"
              ? `${count} application${count !== 1 ? "s" : ""} · ${items.length} shown${hasActiveFilters() ? " (filtered)" : ""}`
              : `${partnerCount} partner${partnerCount !== 1 ? "s" : ""} · ${partnerItems.length} shown`
            }
          </p>
        </div>
        <div className="flex items-center gap-2">
          {viewMode === "applications" && (
            <button
              onClick={() => setShowBulkUpload(true)}
              className="inline-flex items-center gap-2 rounded-lg border border-input bg-card px-3 py-2 text-sm font-medium text-foreground transition hover:bg-secondary"
            >
              <Upload className="h-4 w-4" />
              <span className="hidden sm:inline">Bulk Upload</span>
            </button>
          )}
          <button
            onClick={() => viewMode === "applications" ? navigate("/onboarding/new") : navigate("/partners/new")}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90 active:scale-[0.98]"
          >
            <Plus className="h-4 w-4" />
            {viewMode === "applications" ? "Add Partner" : "New Partner"}
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm font-medium text-destructive">
          {error}
        </div>
      )}

      {viewMode === "partners" ? (
        /* ---- Partners Table ---- */
        <div className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
          <div className="flex flex-col gap-3 border-b border-border p-3 sm:flex-row sm:items-center sm:justify-between">
            <div />
            <div className="relative flex-1 sm:flex-none sm:w-60">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search partners..."
                value={searchValue}
                onChange={(e) => setSearchValue(e.target.value)}
                onKeyDown={handleSearchKeyDown}
                className="w-full rounded-lg border border-input bg-card py-1.5 pl-9 pr-8 text-sm text-foreground outline-none transition placeholder:text-muted-foreground focus:ring-2 focus:ring-ring/40"
              />
              {searchValue && (
                <button
                  onClick={handleClearSearch}
                  className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-0.5 text-muted-foreground hover:text-foreground"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          </div>

          {loading ? (
            <SkeletonTable rows={6} cols={7} />
          ) : partnerItems.length === 0 ? (
            <div className="flex flex-col items-center justify-center px-6 py-16 text-center">
              <h3 className="text-lg font-semibold text-foreground">No Partners Found</h3>
              <p className="mt-1 text-sm text-muted-foreground">{search ? "Try a different search." : "No partners yet."}</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-muted/30">
                    <th className="whitespace-nowrap px-3 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Partner #</th>
                    <th className="whitespace-nowrap px-3 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Name</th>
                    <th className="whitespace-nowrap px-3 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Type</th>
                    <th className="whitespace-nowrap px-3 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Email</th>
                    <th className="whitespace-nowrap px-3 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Mobile</th>
                    <th className="whitespace-nowrap px-3 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Status</th>
                    <th className="w-24 px-2 py-3 text-right text-xs font-semibold uppercase tracking-wider text-muted-foreground">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {partnerItems.map((partner) => (
                    <tr key={partner.id} className="border-b border-border/50 transition last:border-b-0 hover:bg-secondary/40">
                      <td className="whitespace-nowrap px-3 py-3 font-medium text-foreground">{partner.partnerNumber}</td>
                      <td className="whitespace-nowrap px-3 py-3 text-foreground">{partner.displayName}</td>
                      <td className="whitespace-nowrap px-3 py-3 text-muted-foreground">{partner.partnerCategory || partner.partnerType}</td>
                      <td className="px-3 py-3 text-muted-foreground">{partner.email}</td>
                      <td className="whitespace-nowrap px-3 py-3 text-muted-foreground">{partner.mobileNumber}</td>
                      <td className="whitespace-nowrap px-3 py-3">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          partner.status === "ACTIVE"
                            ? "bg-[var(--color-bg-success-soft)] text-[var(--color-text-success-soft)]"
                            : "bg-[var(--color-bg-destructive-soft)] text-[var(--color-text-destructive-soft)]"
                        }`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${
                            partner.status === "ACTIVE" ? "bg-[var(--color-feedback-success)]" : "bg-[var(--color-feedback-destructive)]"
                          }`} />
                          {partner.status}
                        </span>
                      </td>
                      <td className="px-2 py-3 text-right">
                        <div className="flex items-center justify-end gap-0.5">
                          <button
                            onClick={() => navigate(`/partners/${partner.id}/edit?from=onboarding`)}
                            className="rounded p-1.5 text-muted-foreground transition hover:bg-secondary hover:text-foreground"
                            title="Edit"
                          >
                            <Pencil className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => navigate(`/partners/${partner.id}?from=onboarding`)}
                            className="rounded p-1.5 text-muted-foreground transition hover:bg-secondary hover:text-foreground"
                            title="View"
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

          {Math.ceil(partnerCount / partnerPageSize) > 1 && (
            <div className="flex items-center justify-center gap-2 border-t border-border px-3 py-3">
              <button
                onClick={() => setPartnerPage((p) => Math.max(1, p - 1))}
                disabled={partnerPage <= 1}
                className="p-2 rounded-lg hover:bg-muted disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <span className="text-sm text-muted-foreground">Page {partnerPage} of {Math.ceil(partnerCount / partnerPageSize)}</span>
              <button
                onClick={() => setPartnerPage((p) => Math.min(Math.ceil(partnerCount / partnerPageSize), p + 1))}
                disabled={partnerPage >= Math.ceil(partnerCount / partnerPageSize)}
                className="p-2 rounded-lg hover:bg-muted disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>
      ) : (
      /* ---- Applications Table ---- */
      <div className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
        {/* Toolbar */}
        <div className="flex flex-col gap-3 border-b border-border p-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            {/* Entries */}
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value))
                setPage(1)
              }}
              className="rounded-lg border border-input bg-card px-2.5 py-1.5 text-sm text-foreground outline-none focus:ring-2 focus:ring-ring/40"
            >
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>

            {/* Filter toggle button (mobile) */}
            <button
              onClick={() => setShowFilters((s) => !s)}
              className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm font-medium transition sm:hidden ${
                showFilters
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-input bg-card text-muted-foreground hover:bg-secondary"
              }`}
            >
              <Filter className="h-3.5 w-3.5" />
              Filters
              {hasActiveFilters() && (
                <span className="ml-1 flex h-4 w-4 items-center justify-center rounded-full bg-primary text-[10px] font-bold text-primary-foreground">
                  {[statusFilter, typeFilter, search].filter(Boolean).length}
                </span>
              )}
            </button>

            {/* Inline filters (desktop always shown, mobile toggled) */}
            <div
              className={`flex w-full flex-wrap items-center gap-2 sm:w-auto sm:flex-nowrap ${
                showFilters ? "flex" : "hidden sm:flex"
              }`}
            >
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value as ApplicationStatus | "")
                  setPage(1)
                }}
                className="rounded-lg border border-input bg-card px-2.5 py-1.5 text-sm text-foreground outline-none focus:ring-2 focus:ring-ring/40"
              >
                {STATUSES.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>

              <select
                value={typeFilter}
                onChange={(e) => {
                  setTypeFilter(e.target.value)
                  setPage(1)
                }}
                className="rounded-lg border border-input bg-card px-2.5 py-1.5 text-sm text-foreground outline-none focus:ring-2 focus:ring-ring/40"
              >
                {PARTNER_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>

              {hasActiveFilters() && (
                <button
                  onClick={clearAllFilters}
                  className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-muted-foreground transition hover:text-destructive"
                >
                  <X className="h-3 w-3" />
                  Clear all
                </button>
              )}
            </div>
          </div>

          {/* Search */}
          <div className="relative flex-1 sm:flex-none sm:w-60">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search partners..."
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              onKeyDown={handleSearchKeyDown}
              className="w-full rounded-lg border border-input bg-card py-1.5 pl-9 pr-8 text-sm text-foreground outline-none transition placeholder:text-muted-foreground focus:ring-2 focus:ring-ring/40"
            />
            {searchValue && (
              <button
                onClick={handleClearSearch}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-0.5 text-muted-foreground hover:text-foreground"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Table / loading / empty */}
        {loading ? (
          <SkeletonTable rows={6} cols={14} />
        ) : items.length === 0 ? (
          <div className="flex flex-col items-center justify-center px-6 py-16 text-center">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
              <svg
                className="h-8 w-8 text-primary"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                <circle cx="9" cy="7" r="4" />
                <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                <path d="M16 3.13a4 4 0 0 1 0 7.75" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-foreground">No Partners Found</h3>
            <p className="mt-1 max-w-sm text-sm text-muted-foreground">
              {hasActiveFilters()
                ? "No applications match your current filters. Try adjusting your search."
                : "There are no partner applications yet. Add your first one to get started."}
            </p>
            <div className="mt-5 flex items-center gap-2">
              <button
                onClick={() => navigate("/onboarding/new")}
                className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90"
              >
                <Plus className="h-4 w-4" />
                Add Partner
              </button>
              {hasActiveFilters() && (
                <button
                  onClick={clearAllFilters}
                  className="rounded-lg border border-input px-4 py-2 text-sm font-medium text-foreground transition hover:bg-secondary"
                >
                  Clear Filters
                </button>
              )}
            </div>
          </div>
        ) : (
          <>
            {/* Desktop table (≥768px) */}
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-muted/30">
                    <th className="whitespace-nowrap px-3 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      #
                    </th>
                    <th className="whitespace-nowrap px-3 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      App Number
                    </th>
                    <th className="whitespace-nowrap px-3 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Title
                    </th>
                    <th className="whitespace-nowrap px-3 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Surname
                    </th>
                    <th className="whitespace-nowrap px-3 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Type
                    </th>
                    <th className="whitespace-nowrap px-3 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Mobile
                    </th>
                    <th className="whitespace-nowrap px-3 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Nationality
                    </th>
                    <th className="whitespace-nowrap px-3 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      ID Type
                    </th>
                    <th className="whitespace-nowrap px-3 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Email
                    </th>
                    <th className="whitespace-nowrap px-3 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Status
                    </th>
                    <th className="whitespace-nowrap px-3 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Created By
                    </th>
                    <th className="whitespace-nowrap px-3 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Updated By
                    </th>
                    <th className="whitespace-nowrap px-3 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Created
                    </th>
                    <th className="w-28 px-2 py-3 text-right text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((app, idx) => {
                    const sv = statusVariant(app.status)
                    return (
                      <tr
                        key={app.id}
                        className="cursor-pointer border-b border-border/50 transition last:border-b-0 hover:bg-secondary/40"
                        onClick={() => navigate(`/onboarding/${app.id}`)}
                      >
                        <td className="whitespace-nowrap px-3 py-3 text-muted-foreground">
                          {idx + 1 + (page - 1) * pageSize}
                        </td>
                        <td className="whitespace-nowrap px-3 py-3 font-medium text-foreground">
                          {app.applicationNumber}
                        </td>
                        <td className="whitespace-nowrap px-3 py-3 text-muted-foreground">
                          {app.title || "—"}
                        </td>
                        <td className="whitespace-nowrap px-3 py-3 text-foreground">
                          {app.surname || "—"}
                        </td>
                        <td className="whitespace-nowrap px-3 py-3 text-muted-foreground">
                          {app.partnerType === "INDIVIDUAL" ? "Individual" : "Corporate"}
                        </td>
                        <td className="whitespace-nowrap px-3 py-3 text-muted-foreground">
                          {app.mobileNumber || "—"}
                        </td>
                        <td className="whitespace-nowrap px-3 py-3 text-muted-foreground">
                          {app.nationality || "—"}
                        </td>
                        <td className="whitespace-nowrap px-3 py-3 text-muted-foreground">
                          {app.identificationType || "—"}
                        </td>
                        <td className="max-w-[180px] px-3 py-3">
                          <div className="truncate text-muted-foreground">{app.email}</div>
                        </td>
                        <td className="whitespace-nowrap px-3 py-3">
                          <span
                            className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ${sv.bg} ${sv.text}`}
                          >
                            <span
                              className={`h-1.5 w-1.5 shrink-0 rounded-full ${sv.dot}`}
                            />
                            {statusLabels[app.status]}
                          </span>
                        </td>
                        <td className="whitespace-nowrap px-3 py-3 text-muted-foreground">
                          {app.createdByName || "—"}
                        </td>
                        <td className="whitespace-nowrap px-3 py-3 text-muted-foreground">
                          {app.updatedByName || "—"}
                        </td>
                        <td className="whitespace-nowrap px-3 py-3 text-muted-foreground">
                          {new Date(app.createdAt).toLocaleDateString()}
                        </td>
                        <td className="px-2 py-3 text-right">
                          <div className="flex items-center justify-end gap-0.5">
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                navigate(`/onboarding/${app.id}/edit`)
                              }}
                              className="rounded p-1.5 text-muted-foreground transition hover:bg-secondary hover:text-foreground"
                              title="Edit"
                            >
                              <Pencil className="h-4 w-4" />
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                navigate(`/onboarding/${app.id}`)
                              }}
                              className="rounded p-1.5 text-muted-foreground transition hover:bg-secondary hover:text-foreground"
                              title="View"
                            >
                              <Eye className="h-4 w-4" />
                            </button>
                            {(app.status === "DRAFT" || app.status === "ACTIVE") && (
                              <button
                                onClick={(e) => handleDeleteClick(app.id, e)}
                                disabled={deleting === app.id}
                                className="rounded p-1.5 text-muted-foreground transition hover:bg-destructive/10 hover:text-destructive disabled:opacity-50"
                                title="Delete"
                              >
                                {deleting === app.id ? (
                                  <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                  <Trash2 className="h-4 w-4" />
                                )}
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            {/* Mobile cards (<768px) */}
            <div className="divide-y divide-border md:hidden">
              {items.map((app, idx) => {
                const sv = statusVariant(app.status)
                return (
                  <div
                    key={app.id}
                    className="cursor-pointer px-4 py-3 transition active:bg-secondary/60"
                    onClick={() => navigate(`/onboarding/${app.id}`)}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-medium text-muted-foreground">
                            {idx + 1 + (page - 1) * pageSize}
                          </span>
                          <span className="truncate font-medium text-foreground">
                            {app.surname ? `${app.title ? app.title + " " : ""}${app.surname}` : app.displayName}
                          </span>
                          <span
                            className={`inline-flex items-center gap-1 rounded-full px-2 py-0 text-[10px] font-semibold ${sv.bg} ${sv.text}`}
                          >
                            {statusLabels[app.status]}
                          </span>
                        </div>
                        <div className="mt-0.5 text-xs text-muted-foreground">
                          {app.applicationNumber}
                        </div>
                        <div className="mt-1 grid grid-cols-2 gap-x-4 gap-y-0.5 text-xs">
                          <span className="text-muted-foreground">Type</span>
                          <span className="text-foreground">
                            {app.partnerType === "INDIVIDUAL" ? "Individual" : "Corporate"}
                          </span>
                          <span className="text-muted-foreground">Mobile</span>
                          <span className="truncate text-foreground">
                            {app.mobileNumber || "—"}
                          </span>
                          <span className="text-muted-foreground">Nationality</span>
                          <span className="text-foreground">
                            {app.nationality || "—"}
                          </span>
                          <span className="text-muted-foreground">ID Type</span>
                          <span className="text-foreground">
                            {app.identificationType || "—"}
                          </span>
                          <span className="text-muted-foreground">Email</span>
                          <span className="truncate text-foreground">{app.email}</span>
                          <span className="text-muted-foreground">Created By</span>
                          <span className="text-foreground">
                            {app.createdByName || "—"}
                          </span>
                          <span className="text-muted-foreground">Updated By</span>
                          <span className="text-foreground">
                            {app.updatedByName || "—"}
                          </span>
                        </div>
                      </div>
                      <div className="flex flex-col items-end gap-1">
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            navigate(`/onboarding/${app.id}/edit`)
                          }}
                          className="rounded p-1 text-muted-foreground transition hover:bg-secondary hover:text-foreground"
                          title="Edit"
                        >
                          <Pencil className="h-4 w-4" />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            navigate(`/onboarding/${app.id}`)
                          }}
                          className="rounded p-1 text-muted-foreground transition hover:bg-secondary hover:text-foreground"
                          title="View"
                        >
                          <Eye className="h-4 w-4" />
                        </button>
                        {(app.status === "DRAFT" || app.status === "ACTIVE") && (
                          <button
                            onClick={(e) => handleDeleteClick(app.id, e)}
                            disabled={deleting === app.id}
                            className="rounded p-1 text-muted-foreground transition hover:bg-destructive/10 hover:text-destructive disabled:opacity-50"
                            title="Delete"
                          >
                            {deleting === app.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Trash2 className="h-4 w-4" />
                            )}
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border px-4 py-3">
            <span className="text-sm text-muted-foreground">
              Page{" "}
              <span className="font-semibold text-foreground">{page}</span> of{" "}
              <span className="font-semibold text-foreground">{totalPages}</span>
              {" · "}{count} total
            </span>

            {/* Mobile: prev/next only */}
            <div className="flex items-center gap-2 sm:hidden">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="inline-flex items-center gap-1 rounded-lg border border-input px-3 py-1.5 text-sm font-medium text-foreground transition hover:bg-secondary disabled:opacity-40"
              >
                <ChevronLeft className="h-4 w-4" />
                Prev
              </button>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="inline-flex items-center gap-1 rounded-lg border border-input px-3 py-1.5 text-sm font-medium text-foreground transition hover:bg-secondary disabled:opacity-40"
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>

            {/* Desktop: full page numbers */}
            <div className="hidden items-center gap-1 sm:flex">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="inline-flex items-center gap-1 rounded-lg border border-input px-3 py-1.5 text-sm font-medium text-foreground transition hover:bg-secondary disabled:opacity-40"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              {pageNumbers.map((p, i) =>
                p === "..." ? (
                  <span
                    key={`ellipsis-${i}`}
                    className="flex h-8 w-8 items-center justify-center text-sm text-muted-foreground"
                  >
                    …
                  </span>
                ) : (
                  <button
                    key={p}
                    onClick={() => setPage(p)}
                    className={`flex h-8 w-8 items-center justify-center rounded-lg border text-sm font-medium transition ${
                      p === page
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-input text-foreground hover:bg-secondary"
                    }`}
                  >
                    {p}
                  </button>
                ),
              )}
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="inline-flex items-center gap-1 rounded-lg border border-input px-3 py-1.5 text-sm font-medium text-foreground transition hover:bg-secondary disabled:opacity-40"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}
      </div>
      )}

      <BulkUploadModal
        open={showBulkUpload}
        onClose={() => setShowBulkUpload(false)}
        onSuccess={load}
      />

      <ConfirmDialog
        open={deleteTarget !== null}
        title="Delete Application"
        message="Delete this draft application? This cannot be undone."
        loading={deleting !== null}
        onConfirm={handleDeleteConfirm}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  )
}

import { useEffect, useState, useCallback, useMemo } from "react"
import type { KeyboardEvent, MouseEvent, ReactNode } from "react"
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
  SlidersHorizontal,
  ArrowUpDown,
  UserRound,
  Building2,
  RefreshCw,
} from "lucide-react"
import BulkUploadModal from "../../components/onboarding/BulkUploadModal"
import ConfirmDialog from "../../components/shared/ConfirmDialog"
import { SkeletonTable } from "../../components/shared/Skeleton"
import { listUnifiedRecords, deleteApplication } from "../../lib/api"
import { useDataRefresh } from "../../lib/useDataRefresh"
import type { UnifiedOnboardingRecord, ApplicationStatus, KycStatus } from "../../lib/types"
import { useWorkflowConfig } from "../../config/ConfigurationHooks"
import { useChoices } from "../../hooks/useChoices"
import { useLitProps } from "../../lib/useLitProps"

const STATUSES: { value: ApplicationStatus | ""; label: string }[] = [
  { value: "", label: "All statuses" },
  { value: "DRAFT", label: "Draft" },
  { value: "SUBMITTED", label: "Submitted" },
  { value: "UNDER_REVIEW", label: "Under review" },
  { value: "PENDING_DOCUMENTS", label: "Pending documents" },
  { value: "COMPLIANCE_CHECK", label: "Compliance" },
  { value: "APPROVED", label: "Approved" },
  { value: "CONVERTED", label: "Converted" },
  { value: "REJECTED", label: "Rejected" },
  { value: "SUSPENDED", label: "Suspended" },
]

const PARTNER_TYPES = [
  { value: "", label: "All partner types" },
  { value: "INDIVIDUAL", label: "Individual" },
  { value: "CORPORATE", label: "Corporate" },
]

function statusVariant(status: ApplicationStatus): { bg: string; text: string; dot: string } {
  if (["APPROVED", "CONVERTED", "ACTIVE"].includes(status)) {
    return { bg: "bg-[#f1f5f4]", text: "text-[#1c3b34]", dot: "bg-[#1c3b34]" }
  }
  if (["REJECTED", "SUSPENDED"].includes(status)) {
    return { bg: "bg-[#f4f4f4]", text: "text-[#242424]", dot: "bg-[#242424]" }
  }
  return { bg: "bg-[#f6f6f6]", text: "text-[#585858]", dot: "bg-[#8a8a8a]" }
}

function getPageNumbers(current: number, total: number): (number | "...")[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
  const pages: (number | "...")[] = [1]
  if (current > 3) pages.push("...")
  const start = Math.max(2, current - 1)
  const end = Math.min(total - 1, current + 1)
  for (let i = start; i <= end; i += 1) pages.push(i)
  if (current < total - 2) pages.push("...")
  pages.push(total)
  return pages
}

function formatDate(value: string | null | undefined) {
  if (!value) return "—"
  return new Intl.DateTimeFormat(undefined, { day: "2-digit", month: "short", year: "numeric" }).format(new Date(value))
}

function RecordTypeMark({ type }: { type: UnifiedOnboardingRecord["recordType"] }) {
  const corporate = type === "PARTNER" ? false : type === "APPLICATION"
  return corporate ? <Building2 className="h-3.5 w-3.5" /> : <UserRound className="h-3.5 w-3.5" />
}

export default function OnboardingList() {
  const navigate = useNavigate()
  const { data: kycOptions } = useChoices("KYC_STATUS_CHOICES")
  const [items, setItems] = useState<UnifiedOnboardingRecord[]>([])
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [search, setSearch] = useState("")
  const [searchValue, setSearchValue] = useState("")
  const [statusFilter, setStatusFilter] = useState<ApplicationStatus | "">("")
  const [kycFilter, setKycFilter] = useState<KycStatus | "">("")
  const [typeFilter, setTypeFilter] = useState("")
  const [showFilters, setShowFilters] = useState(false)
  const [showBulkUpload, setShowBulkUpload] = useState(false)
  const [deleting, setDeleting] = useState<string | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const refreshKey = useDataRefresh("partners")
  const workflowConfig = useWorkflowConfig()
  const statusLabels = workflowConfig?.status_labels ?? {
    ACTIVE: "Active", DRAFT: "Draft", SUBMITTED: "Submitted", UNDER_REVIEW: "Under review",
    PENDING_DOCUMENTS: "Pending documents", COMPLIANCE_CHECK: "Compliance", APPROVED: "Approved",
    CONVERTED: "Converted", REJECTED: "Rejected", SUSPENDED: "Suspended",
  }

  const load = useCallback(async () => {
    setLoading(true)
    setError("")
    try {
      const result = await listUnifiedRecords({
        page,
        pageSize,
        search: search || undefined,
        application_status: statusFilter || undefined,
        kyc_status: kycFilter || undefined,
        partner_type: typeFilter || undefined,
        ordering: "-created_at",
      })
      setItems(result.results ?? [])
      setCount(result.count ?? 0)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load the onboarding register")
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, search, statusFilter, kycFilter, typeFilter, refreshKey])

  useEffect(() => { load() }, [load])

  function applySearch() {
    setSearch(searchValue.trim())
    setPage(1)
  }

  function handleSearchKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") applySearch()
  }

  function clearAllFilters() {
    setStatusFilter("")
    setKycFilter("")
    setTypeFilter("")
    setSearch("")
    setSearchValue("")
    setPage(1)
  }

  const hasActiveFilters = Boolean(statusFilter || typeFilter || kycFilter || search)
  const totalPages = Math.max(1, Math.ceil(count / pageSize))
  const pageNumbers = useMemo(() => getPageNumbers(page, totalPages), [page, totalPages])
  const activeOnPage = items.filter((item) => ["DRAFT", "ACTIVE", "SUBMITTED", "UNDER_REVIEW", "PENDING_DOCUMENTS", "COMPLIANCE_CHECK"].includes(item.applicationStatus || "")).length
  const approvedOnPage = items.filter((item) => item.applicationStatus === "APPROVED").length
  const convertedOnPage = items.filter((item) => item.recordType === "PARTNER" || item.applicationStatus === "CONVERTED").length
  const totalStatsRef = useLitProps<HTMLElement>({ label: "Total records", value: String(count), caption: "Across the onboarding register", tone: "blue" })
  const activeStatsRef = useLitProps<HTMLElement>({ label: "Active pipeline", value: String(activeOnPage), caption: "Current page", tone: "amber" })
  const approvedStatsRef = useLitProps<HTMLElement>({ label: "Approved", value: String(approvedOnPage), caption: "Current page", tone: "green" })
  const convertedStatsRef = useLitProps<HTMLElement>({ label: "Converted partners", value: String(convertedOnPage), caption: "Current page", tone: "violet" })

  function navigateTo(record: UnifiedOnboardingRecord) {
    navigate(record.recordType === "APPLICATION" ? `/onboarding/${record.applicationId}` : `/partners/${record.partnerId}?from=onboarding`)
  }

  function navigateEdit(record: UnifiedOnboardingRecord) {
    navigate(record.recordType === "APPLICATION" ? `/onboarding/${record.applicationId}/edit` : `/partners/${record.partnerId}/edit?from=onboarding`)
  }

  function handleDeleteClick(id: string, event: MouseEvent) {
    event.stopPropagation()
    setDeleteTarget(id)
  }

  async function handleDeleteConfirm() {
    if (!deleteTarget) return
    setDeleting(deleteTarget)
    try {
      await deleteApplication(deleteTarget)
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete the draft")
    } finally {
      setDeleting(null)
      setDeleteTarget(null)
    }
  }

  return (
    <div className="min-w-0 space-y-5 text-[#1b1b1b]">
      <div className="flex flex-col gap-4 border-b border-[#e7e7e7] pb-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs font-medium text-[#777]">
            <button onClick={() => navigate("/")} className="transition hover:text-[#111]">Home</button>
            <span>/</span>
            <span className="text-[#222]">Partner onboarding</span>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-[#dedede] bg-white">
              <UsersMark />
            </div>
            <div>
              <h1 className="text-2xl font-semibold tracking-[-0.03em] text-[#111]">Partner onboarding</h1>
              <p className="mt-1 text-sm text-[#737373]">Manage applications, conversion status, and partner records in one register.</p>
            </div>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button onClick={() => setShowBulkUpload(true)} className="inline-flex items-center gap-2 rounded-lg border border-[#d8d8d8] bg-white px-3.5 py-2.5 text-sm font-semibold text-[#303030] transition hover:border-[#111] hover:bg-[#fafafa]">
            <Upload className="h-4 w-4" />
            Bulk upload
          </button>
          <button onClick={() => navigate("/onboarding/new")} className="inline-flex items-center gap-2 rounded-lg bg-[#111] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#2b2b2b] active:scale-[0.99]">
            <Plus className="h-4 w-4" />
            Add partner
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <onboarding-stats-card ref={totalStatsRef} />
        <onboarding-stats-card ref={activeStatsRef} />
        <onboarding-stats-card ref={approvedStatsRef} />
        <onboarding-stats-card ref={convertedStatsRef} />
      </div>

      {error && <div role="alert" className="flex items-center justify-between gap-3 rounded-lg border border-[#d5d5d5] bg-[#f7f7f7] px-4 py-3 text-sm text-[#222]"><span>{error}</span><button onClick={load} className="inline-flex items-center gap-1.5 font-semibold underline underline-offset-4"><RefreshCw className="h-3.5 w-3.5" /> Retry</button></div>}

      <section className="overflow-hidden rounded-xl border border-[#dedede] bg-white shadow-[0_8px_30px_rgba(0,0,0,0.035)]">
        <div className="flex flex-col gap-3 border-b border-[#e5e5e5] p-4 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            <label className="flex items-center gap-2 text-sm text-[#666]">
              <span>Show</span>
              <select aria-label="Rows per page" value={pageSize} onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1) }} className="rounded-md border border-[#d9d9d9] bg-white px-2.5 py-2 text-sm font-semibold text-[#222] outline-none focus:border-[#111] focus:ring-2 focus:ring-[#111]/10">
                {[10, 25, 50, 100].map((size) => <option key={size} value={size}>{size}</option>)}
              </select>
              <span>entries</span>
            </label>
            <button onClick={() => setShowFilters((value) => !value)} className={`inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm font-semibold transition ${showFilters || hasActiveFilters ? "border-[#111] bg-[#111] text-white" : "border-[#d9d9d9] bg-white text-[#444] hover:border-[#111]"}`}>
              <SlidersHorizontal className="h-3.5 w-3.5" /> Filters
              {hasActiveFilters && <span className="rounded-full bg-white px-1.5 text-[10px] text-[#111]">{[statusFilter, kycFilter, typeFilter, search].filter(Boolean).length}</span>}
            </button>
            <button onClick={load} className="inline-flex items-center gap-2 rounded-md border border-[#d9d9d9] bg-white px-3 py-2 text-sm font-semibold text-[#444] transition hover:border-[#111]" title="Refresh register"><RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} /> Refresh</button>
          </div>
          <div className="relative w-full xl:w-[300px]">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#8a8a8a]" />
            <input aria-label="Search partner onboarding" value={searchValue} onChange={(e) => setSearchValue(e.target.value)} onKeyDown={handleSearchKeyDown} placeholder="Search name, reference, email..." className="w-full rounded-md border border-[#d9d9d9] bg-white py-2.5 pl-9 pr-20 text-sm text-[#1c1c1c] outline-none transition placeholder:text-[#999] focus:border-[#111] focus:ring-2 focus:ring-[#111]/10" />
            <div className="absolute right-2 top-1/2 flex -translate-y-1/2 items-center gap-1">
              {searchValue && <button onClick={() => { setSearchValue(""); setSearch(""); setPage(1) }} className="rounded p-1 text-[#777] hover:bg-[#f2f2f2]" aria-label="Clear search"><X className="h-3.5 w-3.5" /></button>}
              <button onClick={applySearch} className="rounded bg-[#111] px-2 py-1 text-[11px] font-bold text-white">Search</button>
            </div>
          </div>
        </div>

        {showFilters && <div className="grid gap-3 border-b border-[#e5e5e5] bg-[#fafafa] p-4 sm:grid-cols-3 lg:grid-cols-4">
          <FilterSelect label="Application status" value={statusFilter} onChange={(value) => { setStatusFilter(value as ApplicationStatus | ""); setPage(1) }} options={STATUSES} />
          <FilterSelect label="KYC status" value={kycFilter} onChange={(value) => { setKycFilter(value as KycStatus | ""); setPage(1) }} options={[{ value: "", label: "All KYC statuses" }, ...(kycOptions ?? [])]} />
          <FilterSelect label="Partner type" value={typeFilter} onChange={(value) => { setTypeFilter(value); setPage(1) }} options={PARTNER_TYPES} />
          <div className="flex items-end"><button onClick={clearAllFilters} disabled={!hasActiveFilters} className="inline-flex h-10 items-center gap-2 rounded-md border border-[#d9d9d9] bg-white px-3 text-sm font-semibold text-[#555] transition hover:border-[#111] disabled:cursor-not-allowed disabled:opacity-40"><X className="h-3.5 w-3.5" /> Clear filters</button></div>
        </div>}

        {loading ? <div className="p-4"><SkeletonTable rows={7} cols={11} /></div> : items.length === 0 ? <EmptyState filtered={hasActiveFilters} onAdd={() => navigate("/onboarding/new")} onClear={clearAllFilters} /> : <>
          <div className="overflow-x-auto">
            <table className="min-w-[1180px] w-full text-left text-sm">
              <thead className="bg-[#fafafa] text-[11px] uppercase tracking-[0.08em] text-[#777]">
                <tr className="border-b border-[#e5e5e5]">
                  {['No.', 'Reference', 'Partner', 'Record', 'Client type', 'Contact', 'Telephone', 'Status', 'Created', 'Updated', ''].map((heading, index) => <th key={heading || index} className="whitespace-nowrap px-4 py-3.5 font-bold">{heading || <span className="sr-only">Actions</span>}{index > 0 && index < 10 && heading && <ArrowUpDown className="ml-1 inline h-3 w-3 text-[#b0b0b0]" />}</th>)}
                </tr>
              </thead>
              <tbody>
                {items.map((record, index) => {
                  const status = record.applicationStatus ? statusVariant(record.applicationStatus) : null
                  const canDelete = record.recordType === "APPLICATION" && record.applicationStatus && ["DRAFT", "ACTIVE"].includes(record.applicationStatus)
                  return <tr key={record.id} tabIndex={0} onClick={() => navigateTo(record)} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); navigateTo(record) } }} className="group cursor-pointer border-b border-[#eeeeee] outline-none transition last:border-0 hover:bg-[#fafafa] focus:bg-[#fafafa] focus:ring-2 focus:ring-inset focus:ring-[#111]">
                    <td className="px-4 py-4 text-[#888]">{index + 1 + (page - 1) * pageSize}</td>
                    <td className="whitespace-nowrap px-4 py-4 font-semibold text-[#222]">{record.referenceNumber}</td>
                    <td className="max-w-[235px] px-4 py-4"><div className="truncate font-semibold text-[#202020]">{record.displayName}</div><div className="mt-1 truncate text-xs text-[#888]">{record.email || "No email recorded"}</div></td>
                    <td className="whitespace-nowrap px-4 py-4"><span className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#666]"><RecordTypeMark type={record.recordType} /> {record.recordType === "APPLICATION" ? "Application" : "Partner"}</span></td>
                    <td className="whitespace-nowrap px-4 py-4 text-[#555]">{record.partnerType === "INDIVIDUAL" ? "Individual" : "Corporate"}</td>
                    <td className="whitespace-nowrap px-4 py-4 text-[#555]">{record.email || "—"}</td>
                    <td className="whitespace-nowrap px-4 py-4 text-[#555]">{record.mobileNumber || "—"}</td>
                    <td className="whitespace-nowrap px-4 py-4">{status ? <span className={`inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-xs font-bold ${status.bg} ${status.text}`}><span className={`h-1.5 w-1.5 rounded-full ${status.dot}`} />{statusLabels[record.applicationStatus!] || record.applicationStatus}</span> : <span className="text-[#999]">—</span>}</td>
                    <td className="whitespace-nowrap px-4 py-4 text-[#555]">{formatDate(record.createdAt)}</td>
                    <td className="whitespace-nowrap px-4 py-4 text-[#777]">{formatDate(record.createdAt)}</td>
                    <td className="px-4 py-4"><div className="flex justify-end gap-1 opacity-70 transition group-hover:opacity-100"><IconButton label="Edit" onClick={(e) => { e.stopPropagation(); navigateEdit(record) }}><Pencil className="h-4 w-4" /></IconButton><IconButton label="View" onClick={(e) => { e.stopPropagation(); navigateTo(record) }}><Eye className="h-4 w-4" /></IconButton>{canDelete && <IconButton label="Delete draft" onClick={(e) => handleDeleteClick(record.applicationId!, e)} disabled={deleting === record.applicationId}>{deleting === record.applicationId ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}</IconButton>}</div></td>
                  </tr>
                })}
              </tbody>
            </table>
          </div>
          <div className="flex flex-col gap-3 border-t border-[#e5e5e5] px-4 py-4 text-sm text-[#777] sm:flex-row sm:items-center sm:justify-between"><span>Showing <strong className="text-[#222]">{count === 0 ? 0 : (page - 1) * pageSize + 1}–{Math.min(page * pageSize, count)}</strong> of <strong className="text-[#222]">{count}</strong> records</span><div className="flex items-center gap-1"><button aria-label="Previous page" disabled={page <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))} className="inline-flex h-8 items-center gap-1 rounded-md border border-[#d9d9d9] px-2.5 font-semibold text-[#555] transition hover:border-[#111] disabled:cursor-not-allowed disabled:opacity-35"><ChevronLeft className="h-3.5 w-3.5" /> Previous</button>{pageNumbers.map((pageNumber, index) => pageNumber === "..." ? <span key={`ellipsis-${index}`} className="px-2">…</span> : <button key={pageNumber} aria-label={`Page ${pageNumber}`} onClick={() => setPage(pageNumber)} className={`h-8 min-w-8 rounded-md border px-2 font-semibold transition ${pageNumber === page ? "border-[#111] bg-[#111] text-white" : "border-[#d9d9d9] bg-white text-[#555] hover:border-[#111]"}`}>{pageNumber}</button>)}<button aria-label="Next page" disabled={page >= totalPages} onClick={() => setPage((value) => Math.min(totalPages, value + 1))} className="inline-flex h-8 items-center gap-1 rounded-md border border-[#d9d9d9] px-2.5 font-semibold text-[#555] transition hover:border-[#111] disabled:cursor-not-allowed disabled:opacity-35">Next <ChevronRight className="h-3.5 w-3.5" /></button></div></div>
        </>}
      </section>

      <BulkUploadModal open={showBulkUpload} onClose={() => setShowBulkUpload(false)} onSuccess={load} />
      <ConfirmDialog open={!!deleteTarget} title="Delete draft application?" message="This draft will be permanently removed from the onboarding register." confirmLabel="Delete draft" onConfirm={handleDeleteConfirm} onCancel={() => setDeleteTarget(null)} />
    </div>
  )
}

function UsersMark() { return <svg viewBox="0 0 24 24" aria-hidden="true" className="h-5 w-5"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg> }

function FilterSelect({ label, value, onChange, options }: { label: string; value: string; onChange: (value: string) => void; options: { value: string; label: string }[] }) { return <label className="text-xs font-bold uppercase tracking-[0.06em] text-[#777]"><span className="mb-1.5 block">{label}</span><select value={value} onChange={(e) => onChange(e.target.value)} className="h-10 w-full rounded-md border border-[#d9d9d9] bg-white px-3 text-sm font-medium normal-case tracking-normal text-[#222] outline-none focus:border-[#111] focus:ring-2 focus:ring-[#111]/10">{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label> }

function IconButton({ label, onClick, disabled, children }: { label: string; onClick: (event: MouseEvent<HTMLButtonElement>) => void; disabled?: boolean; children: ReactNode }) { return <button aria-label={label} title={label} onClick={onClick} disabled={disabled} className="rounded-md p-2 text-[#777] transition hover:bg-[#eeeeee] hover:text-[#111] disabled:cursor-wait disabled:opacity-40">{children}</button> }

function EmptyState({ filtered, onAdd, onClear }: { filtered: boolean; onAdd: () => void; onClear: () => void }) { return <div className="flex flex-col items-center justify-center px-6 py-16 text-center"><div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full border border-[#dedede] bg-[#fafafa] text-[#555]"><UsersMark /></div><h3 className="text-lg font-semibold text-[#111]">No partner records found</h3><p className="mt-1 max-w-sm text-sm text-[#777]">{filtered ? "No records match the current search and filters." : "Create your first partner application to begin the onboarding register."}</p><div className="mt-5 flex gap-2">{filtered && <button onClick={onClear} className="rounded-md border border-[#d7d7d7] px-4 py-2 text-sm font-semibold text-[#444] hover:border-[#111]">Clear filters</button>}<button onClick={onAdd} className="inline-flex items-center gap-2 rounded-md bg-[#111] px-4 py-2 text-sm font-semibold text-white hover:bg-[#303030]"><Plus className="h-4 w-4" /> Add partner</button></div></div> }

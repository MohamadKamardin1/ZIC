import { useCallback, useEffect, useState, useRef } from "react"
import { useNavigate, useParams, useSearchParams } from "react-router-dom"
import {
  ArrowLeft, User, Building2, Shield, FileText, Loader2, Pencil,
  FileSpreadsheet, Contact, Landmark, CheckCircle, XCircle, Plus, Trash2, Upload,
  ChevronDown, Search, X, Save, MapPin, CalendarDays, Mail, Phone, Eye,
} from "lucide-react"
import {
  getPartner,
  activatePartner,
  deactivatePartner,
  getAssignmentHistory,
  activateAssignment,
  deactivateAssignment,
  getAssignmentSetupSummary,
  getAssignmentDocuments,
  uploadAssignmentDocumentFile,
  updateAssignmentDocument,
  getAssignmentFieldValues,
  updateAssignmentFieldValues,
  getAssignmentContacts,
  createAssignmentContact,
  deleteAssignmentContact,
  getAssignmentBankAccounts,
  createAssignmentBankAccount,
  deleteAssignmentBankAccount,
  getAssignmentKYC,
  updateAssignmentKYC,
  fetchDocumentRequirements,
  fetchPartnerTypes,
  fetchBranches,
  fetchLocations,
  assignPartnerType,
  updatePartnerTypeAssignment,
} from "../../lib/api"
import type {
  PartnerDetail as PartnerDetailType,
  PartnerTypeAssignment,
  SetupSummary,
  PartnerDocument,
  PartnerDynamicFieldValue,
  PartnerAssignmentContact,
  PartnerAssignmentBankAccount,
  PartnerKYCProfile,
  PartnerTypeDocumentRequirement,
  PartnerTypeFieldConfiguration,
  PartnerTypeContactRequirement,
  PartnerTypeBankRequirement,
  PartnerTypeAssignmentHistory,
  PartnerTypeRecord,
  BranchRecord,
  LocationRecord,
} from "../../lib/types"

type SetupTab = "documents" | "fields" | "contacts" | "banks" | "kyc"



export default function PartnerDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const fromOnboarding = searchParams.get("from") === "onboarding"

  const [partner, setPartner] = useState<PartnerDetailType | null>(null)
  const [summaries, setSummaries] = useState<Record<string, SetupSummary>>({})
  const [histories, setHistories] = useState<Record<string, PartnerTypeAssignmentHistory[]>>({})
  const [loading, setLoading] = useState(true)
  const [actionBusy, setActionBusy] = useState(false)
  const [error, setError] = useState("")
  const [expandedAssign, setExpandedAssign] = useState<string | null>(null)
  const [detailTab, setDetailTab] = useState<"types" | "contacts" | "banks">("types")
  const [assignmentSearch, setAssignmentSearch] = useState("")
  const [typeModalOpen, setTypeModalOpen] = useState(false)
  const [editingAssignment, setEditingAssignment] = useState<PartnerTypeAssignment | null>(null)

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError("")
    try {
      const data = await getPartner(id)
      setPartner(data)
      const summaryMap: Record<string, SetupSummary> = {}
      const historyMap: Record<string, PartnerTypeAssignmentHistory[]> = {}
      if (data.typeAssignments?.length) {
        const results = await Promise.allSettled(
          data.typeAssignments.map(async (a) => ({
            id: a.id,
            summary: await getAssignmentSetupSummary(a.id),
            history: await getAssignmentHistory(a.id),
          })),
        )
        for (const result of results) {
          if (result.status === "fulfilled") {
            summaryMap[result.value.id] = result.value.summary
            historyMap[result.value.id] = result.value.history
          }
        }
      }
      setSummaries(summaryMap)
      setHistories(historyMap)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load partner")
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    const handlePartnerAction = async (event: Event) => {
      const detail = (event as CustomEvent<{ action?: string; entityId?: string }>).detail
      if (!detail?.action || !detail.entityId) return
      const isPartner = detail.entityId === id
      const assignment = partner?.typeAssignments?.find((item) => item.id === detail.entityId)
      if (!isPartner && !assignment) return
      const reason = detail.action === "deactivate"
        ? window.prompt("Enter the reason for deactivation:", "")
        : ""
      if (detail.action === "deactivate" && reason === null) return
      setActionBusy(true)
      try {
        if (isPartner) {
          if (detail.action === "deactivate") await deactivatePartner(detail.entityId, reason || "")
          else await activatePartner(detail.entityId)
        } else if (assignment) {
          if (detail.action === "deactivate") await deactivateAssignment(detail.entityId, reason || "")
          else await activateAssignment(detail.entityId)
        }
        await load()
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Lifecycle action failed")
      } finally {
        setActionBusy(false)
      }
    }
    document.addEventListener("partner-action", handlePartnerAction)
    return () => document.removeEventListener("partner-action", handlePartnerAction)
  }, [id, load, partner])

  async function handleAssignmentLifecycle(assignment: PartnerTypeAssignment) {
    const isDeactivation = assignment.status === "ACTIVE"
    const reason = isDeactivation ? window.prompt("Enter the reason for deactivation:", "") : ""
    if (isDeactivation && reason === null) return
    setActionBusy(true)
    setError("")
    try {
      if (isDeactivation) await deactivateAssignment(assignment.id, reason || "")
      else await activateAssignment(assignment.id)
      await load()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Assignment lifecycle action failed")
    } finally {
      setActionBusy(false)
    }
  }

  function openTypeModal(assignment: PartnerTypeAssignment | null = null) {
    setEditingAssignment(assignment)
    setTypeModalOpen(true)
  }

  function openAssignmentSetup(assignmentId: string) {
    setDetailTab("types")
    setExpandedAssign(assignmentId)
    window.setTimeout(() => {
      document.getElementById(`assignment-${assignmentId}`)?.scrollIntoView({ behavior: "smooth", block: "center" })
    }, 80)
  }

  if (loading) {
    return <div className="flex min-h-[420px] items-center justify-center"><Loader2 className="h-7 w-7 animate-spin text-[#777]" /></div>
  }

  if (error) {
    return (
      <div className="space-y-4">
        <button onClick={() => navigate(fromOnboarding ? "/onboarding" : "/partners")} className="inline-flex items-center gap-2 text-sm text-[#666] hover:text-[#111]"><ArrowLeft className="h-4 w-4" />Back</button>
        <div className="rounded-xl border border-[#d9d9d9] bg-white p-5 text-sm text-[#333]">{error}</div>
        <button onClick={load} className="rounded-lg bg-[#111] px-4 py-2 text-sm font-semibold text-white">Retry</button>
      </div>
    )
  }

  if (!partner) return null

  const assignments = partner.typeAssignments ?? []
  const visibleAssignments = assignments.filter((assignment) => {
    const query = assignmentSearch.trim().toLowerCase()
    if (!query) return true
    return [assignment.partnerTypeName, assignment.partnerTypeCode, assignment.branchName, assignment.locationName, assignment.status]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(query))
  })
  const expandedAssignment = assignments.find((assignment) => assignment.id === expandedAssign)
  const activeAssignments = assignments.filter((assignment) => assignment.status === "ACTIVE").length

  return (
    <div className="space-y-5 pb-8 text-[#222]">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm text-[#777]">
          <button onClick={() => navigate(fromOnboarding ? "/onboarding" : "/partners")} className="hover:text-[#111]">{fromOnboarding ? "Onboarding" : "Partners"}</button>
          <span>/</span>
          <span className="text-[#222]">View Partner</span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button onClick={() => navigate(`/partners/${id}/edit`)} className="inline-flex items-center gap-2 rounded-lg border border-[#d6d6d6] bg-white px-3.5 py-2 text-sm font-semibold text-[#333] hover:bg-[#f5f5f5]"><Pencil className="h-4 w-4" />Edit Partner</button>
          <partner-lifecycle-actions status={partner.status} entityId={partner.id} busy={actionBusy}></partner-lifecycle-actions>
        </div>
      </div>

      <section className="overflow-hidden rounded-xl border border-[#dedede] bg-white shadow-[0_8px_24px_rgba(0,0,0,0.04)]">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#e8e8e8] px-5 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#111] text-white"><User className="h-5 w-5" /></div>
            <div><h1 className="text-xl font-bold tracking-tight text-[#111]">{partner.displayName}</h1><p className="mt-0.5 text-xs text-[#777]">{partner.partnerNumber} · {partner.partnerCategory || partner.partnerType}</p></div>
          </div>
          <div className="flex items-center gap-3 text-right"><div><p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[#999]">Status</p><p className="mt-1 text-sm font-semibold text-[#222]">{partner.status}</p></div><span className="h-8 w-px bg-[#e4e4e4]" /><div><p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[#999]">Active Types</p><p className="mt-1 text-sm font-semibold text-[#222]">{activeAssignments}</p></div></div>
        </div>
        <div className="grid grid-cols-1 divide-y divide-[#ededed] md:grid-cols-3 md:divide-x md:divide-y-0">
          <InfoColumn rows={[
            ["Partner Number", partner.partnerNumber],
            ["Client Type", partner.partnerCategory || partner.partnerType],
            ["Name", partner.displayName],
            ["Email", partner.email],
            ["Telephone", partner.telephoneNumber],
            ["Mobile Number", partner.mobileNumber],
          ]} />
          <InfoColumn rows={[
            ["Nationality", partner.nationality],
            ["Identification Type", partner.identificationType],
            ["Identification Number", partner.identificationNumber],
            ["Date of Birth", partner.dateOfBirth],
            ["Occupation", partner.occupation],
            ["Gender", partner.gender],
          ]} />
          <InfoColumn rows={[
            ["Marital Status", partner.maritalStatus],
            ["Status", partner.status],
            ["Created", formatDate(partner.createdAt)],
            ["Updated", formatDate(partner.updatedAt)],
            ["AML Risk", partner.amlRisk],
            ["Political Risk", partner.politicalRisk],
          ]} />
        </div>
      </section>

      <section className="overflow-hidden rounded-xl border border-[#dedede] bg-white shadow-[0_8px_24px_rgba(0,0,0,0.04)]">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#e6e6e6] px-5 pt-4">
          <div className="flex items-center gap-1 overflow-x-auto">
            {(["types", "contacts", "banks"] as const).map((tab) => (
              <button key={tab} onClick={() => setDetailTab(tab)} className={`border-b-2 px-4 pb-3 text-sm font-semibold capitalize transition-colors ${detailTab === tab ? "border-[#111] text-[#111]" : "border-transparent text-[#999] hover:text-[#333]"}`}>{tab === "types" ? "Partner Types" : tab === "contacts" ? "Partner Contacts" : "Partner Banks"}</button>
            ))}
          </div>
          {detailTab === "types" && <button onClick={() => openTypeModal()} className="mb-2 inline-flex items-center gap-2 rounded-lg bg-[#111] px-3.5 py-2 text-sm font-semibold text-white hover:bg-[#2c2c2c]"><Plus className="h-4 w-4" />Add Partner Type</button>}
        </div>

        {detailTab === "types" && (
          <>
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#efefef] px-5 py-4">
              <div className="flex items-center gap-2 text-sm text-[#777]"><span>Showing</span><span className="font-semibold text-[#222]">{visibleAssignments.length}</span><span>of {assignments.length}</span></div>
              <label className="relative block w-full sm:w-64"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#aaa]" /><input value={assignmentSearch} onChange={(event) => setAssignmentSearch(event.target.value)} placeholder="Search partner types..." className="w-full rounded-lg border border-[#d7d7d7] bg-white py-2 pl-9 pr-3 text-sm text-[#222] outline-none focus:border-[#111] focus:ring-2 focus:ring-[#111]/10" /></label>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-[980px] w-full text-left text-sm">
                <thead className="bg-[#fafafa] text-[11px] font-bold uppercase tracking-[0.08em] text-[#777]"><tr><th className="px-5 py-3">No.</th><th className="px-4 py-3">Partner Type</th><th className="px-4 py-3">Location</th><th className="px-4 py-3">Active</th><th className="px-4 py-3">KYC Compliance</th><th className="px-4 py-3">Created</th><th className="px-4 py-3">Updated</th><th className="px-5 py-3 text-right">Actions</th></tr></thead>
                <tbody className="divide-y divide-[#efefef]">
                  {visibleAssignments.map((assignment, index) => {
                    const summary = summaries[assignment.id]
                    const kycReady = summary?.kyc.status === "APPROVED" || summary?.kyc.status === "COMPLIANT"
                    return <tr key={assignment.id} id={`assignment-${assignment.id}`} className="hover:bg-[#fcfcfc]">
                      <td className="px-5 py-4 text-[#999]">{index + 1}</td>
                      <td className="px-4 py-4"><div className="font-semibold text-[#222]">{assignment.partnerTypeName}</div><div className="mt-0.5 text-xs text-[#999]">{assignment.partnerTypeCode}</div></td>
                      <td className="px-4 py-4"><div className="flex items-center gap-1.5 text-[#555]"><MapPin className="h-3.5 w-3.5 text-[#999]" />{assignment.locationName || assignment.branchName || "Not set"}</div></td>
                      <td className="px-4 py-4"><span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${assignment.status === "ACTIVE" ? "bg-[#f0f0f0] text-[#222]" : "bg-[#fafafa] text-[#999]"}`}><span className={`h-1.5 w-1.5 rounded-full ${assignment.status === "ACTIVE" ? "bg-[#111]" : "bg-[#aaa]"}`} />{assignment.status === "ACTIVE" ? "Active" : "Inactive"}</span></td>
                      <td className="px-4 py-4"><span className={`font-semibold ${kycReady ? "text-[#222]" : "text-[#999]"}`}>{summary ? (kycReady ? "Compliant" : summary.kyc.status || "Not Set") : "Not Set"}</span></td>
                      <td className="px-4 py-4 text-[#666]">{formatDate(assignment.createdAt)}</td>
                      <td className="px-4 py-4 text-[#666]">{formatDate(assignment.updatedAt)}</td>
                      <td className="px-5 py-4"><div className="flex items-center justify-end gap-1.5"><button title="View setup" onClick={() => openAssignmentSetup(assignment.id)} className="inline-flex items-center gap-1 rounded-md border border-[#d7d7d7] px-2.5 py-1.5 text-xs font-semibold text-[#333] hover:bg-[#f4f4f4]"><Eye className="h-3.5 w-3.5" />View</button><button title="Edit assignment" onClick={() => openTypeModal(assignment)} className="inline-flex items-center gap-1 rounded-md border border-[#d7d7d7] px-2.5 py-1.5 text-xs font-semibold text-[#333] hover:bg-[#f4f4f4]"><Pencil className="h-3.5 w-3.5" />Edit</button><button title={assignment.status === "ACTIVE" ? "Deactivate assignment" : "Activate assignment"} disabled={actionBusy} onClick={() => handleAssignmentLifecycle(assignment)} className="rounded-md border border-[#d7d7d7] px-2.5 py-1.5 text-xs font-semibold text-[#333] hover:bg-[#f4f4f4] disabled:opacity-50">{assignment.status === "ACTIVE" ? "Deactivate" : "Activate"}</button></div></td>
                    </tr>
                  })}
                </tbody>
              </table>
            </div>
            {visibleAssignments.length === 0 && <div className="px-5 py-14 text-center"><Shield className="mx-auto h-8 w-8 text-[#bbb]" /><p className="mt-3 text-sm font-semibold text-[#444]">No partner types found</p><p className="mt-1 text-sm text-[#999]">Assign a partner type or change the search term.</p></div>}
            {expandedAssignment && <div className="border-t border-[#e8e8e8] bg-[#fafafa]"><div className="flex items-center justify-between px-5 py-4"><div><p className="text-sm font-bold text-[#222]">Setup workspace · {expandedAssignment.partnerTypeName}</p><p className="mt-0.5 text-xs text-[#777]">Manage documents, fields, contacts, banks, and KYC for this assignment.</p></div><button onClick={() => setExpandedAssign(null)} className="rounded-md p-1.5 text-[#777] hover:bg-[#eee] hover:text-[#111]"><X className="h-4 w-4" /></button></div><SetupManager assignment={expandedAssignment} summary={summaries[expandedAssignment.id]} onRefresh={load} /><partner-assignment-history history={histories[expandedAssignment.id] ?? []}></partner-assignment-history></div>}
          </>
        )}

        {detailTab !== "types" && <RelatedAssignmentTab tab={detailTab} assignments={assignments} summaries={summaries} onManage={openAssignmentSetup} />}
      </section>

      <PartnerTypeModal open={typeModalOpen} partnerId={partner.id} assignment={editingAssignment} onClose={() => { setTypeModalOpen(false); setEditingAssignment(null) }} onSaved={async () => { setTypeModalOpen(false); setEditingAssignment(null); await load() }} />
    </div>
  )
}

function InfoColumn({ rows }: { rows: [string, string | null | undefined][] }) {
  return <div className="px-5 py-3">{rows.map(([label, value]) => <div key={label} className="grid grid-cols-[minmax(130px,0.9fr)_minmax(0,1.1fr)] gap-3 border-b border-[#f0f0f0] py-2.5 last:border-b-0"><span className="text-xs font-bold text-[#333]">{label}:</span><span className="truncate text-sm text-[#666]">{value || "—"}</span></div>)}</div>
}

function RelatedAssignmentTab({ tab, assignments, summaries, onManage }: { tab: "contacts" | "banks"; assignments: PartnerTypeAssignment[]; summaries: Record<string, SetupSummary>; onManage: (id: string) => void }) {
  const label = tab === "contacts" ? "contacts" : "bank accounts"
  return <div className="p-5"><div className="mb-4 flex items-center justify-between"><div><h2 className="text-base font-bold text-[#222]">Partner {tab === "contacts" ? "Contacts" : "Banks"}</h2><p className="mt-1 text-sm text-[#777]">Manage assignment-specific {label} from the setup workspace.</p></div><span className="rounded-full bg-[#f3f3f3] px-3 py-1 text-xs font-semibold text-[#555]">{assignments.length} assignment{assignments.length === 1 ? "" : "s"}</span></div><div className="overflow-x-auto rounded-lg border border-[#e3e3e3]"><table className="min-w-[720px] w-full text-left text-sm"><thead className="bg-[#fafafa] text-[11px] font-bold uppercase tracking-[0.08em] text-[#777]"><tr><th className="px-4 py-3">Partner Type</th><th className="px-4 py-3">Location</th><th className="px-4 py-3">Required</th><th className="px-4 py-3">Submitted</th><th className="px-4 py-3 text-right">Action</th></tr></thead><tbody className="divide-y divide-[#efefef]">{assignments.map((assignment) => { const summary = summaries[assignment.id]; const metrics = tab === "contacts" ? summary?.contacts : summary?.banks; return <tr key={assignment.id}><td className="px-4 py-3 font-semibold text-[#222]">{assignment.partnerTypeName}</td><td className="px-4 py-3 text-[#666]">{assignment.locationName || assignment.branchName || "Not set"}</td><td className="px-4 py-3 text-[#666]">{metrics?.total ?? "—"}</td><td className="px-4 py-3 text-[#666]">{metrics?.submitted ?? "—"}</td><td className="px-4 py-3 text-right"><button onClick={() => onManage(assignment.id)} className="inline-flex items-center gap-1.5 rounded-md border border-[#d7d7d7] px-2.5 py-1.5 text-xs font-semibold text-[#333] hover:bg-[#f4f4f4]"><Eye className="h-3.5 w-3.5" />Manage</button></td></tr> })}</tbody></table>{assignments.length === 0 && <div className="p-12 text-center text-sm text-[#999]">No partner type assignments are available yet.</div>}</div></div>
}

function PartnerTypeModal({ open, partnerId, assignment, onClose, onSaved }: { open: boolean; partnerId: string; assignment: PartnerTypeAssignment | null; onClose: () => void; onSaved: () => Promise<void> }) {
  const [partnerTypes, setPartnerTypes] = useState<PartnerTypeRecord[]>([])
  const [branches, setBranches] = useState<BranchRecord[]>([])
  const [locations, setLocations] = useState<LocationRecord[]>([])
  const [selectedType, setSelectedType] = useState("")
  const [selectedBranch, setSelectedBranch] = useState("")
  const [selectedLocation, setSelectedLocation] = useState("")
  const [shareData, setShareData] = useState(false)
  const [effectiveDate, setEffectiveDate] = useState("")
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    if (!open) return
    setLoading(true)
    setError("")
    Promise.all([fetchPartnerTypes(), fetchBranches(), fetchLocations()]).then(([types, branchRows, locationRows]) => {
      setPartnerTypes(types.filter((type) => type.isActive))
      setBranches(branchRows.filter((branch) => branch.isActive))
      setLocations(locationRows.filter((location) => location.isActive))
      setSelectedType(assignment?.partnerType || "")
      setSelectedBranch(assignment?.branch || "")
      setSelectedLocation(assignment?.location || "")
      setShareData(assignment?.shareDataExternally ?? false)
      setEffectiveDate(assignment?.effectiveDate || "")
    }).catch((e: unknown) => setError(e instanceof Error ? e.message : "Failed to load partner type options")).finally(() => setLoading(false))
  }, [open, assignment])

  if (!open) return null

  async function submit() {
    if (!selectedType) { setError("Select a partner type before saving."); return }
    setSaving(true)
    setError("")
    try {
      const payload = { partner_type: selectedType, branches: selectedBranch ? [selectedBranch] : [], location: selectedLocation || null, share_data_externally: shareData, effective_date: effectiveDate || null }
      if (assignment) await updatePartnerTypeAssignment(partnerId, assignment.id, payload)
      else await assignPartnerType(partnerId, payload)
      await onSaved()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unable to save partner type")
    } finally { setSaving(false) }
  }

  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4" role="dialog" aria-modal="true" aria-labelledby="partner-type-modal-title"><div className="w-full max-w-2xl overflow-hidden rounded-xl border border-[#d7d7d7] bg-white shadow-2xl"><div className="flex items-center justify-between border-b border-[#e7e7e7] px-5 py-4"><div><h2 id="partner-type-modal-title" className="text-lg font-bold text-[#222]">{assignment ? "Edit Partner Type" : "Add Partner Type"}</h2><p className="mt-1 text-xs text-[#777]">Configure type, branch, location, and data-sharing rules.</p></div><button onClick={onClose} className="rounded-md p-2 text-[#777] hover:bg-[#f2f2f2] hover:text-[#111]" aria-label="Close"><X className="h-5 w-5" /></button></div>{loading ? <div className="flex h-56 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-[#777]" /></div> : <><div className="grid gap-5 px-5 py-5 md:grid-cols-2"><SelectField label="Partner Type" value={selectedType} onChange={setSelectedType} options={partnerTypes.map((type) => ({ value: type.id, label: `${type.name} · ${type.code}` }))} placeholder="Select partner type" /><SelectField label="Branch" value={selectedBranch} onChange={(value) => { setSelectedBranch(value); if (!value) setSelectedLocation("") }} options={branches.map((branch) => ({ value: branch.id, label: `${branch.name} · ${branch.code}` }))} placeholder="Select branch" /><SelectField label="Location" value={selectedLocation} onChange={setSelectedLocation} options={locations.filter((location) => !selectedBranch || location.branchId === selectedBranch).map((location) => ({ value: location.id, label: `${location.name} · ${location.code}` }))} placeholder={selectedBranch ? "Select location" : "Select branch first"} disabled={!selectedBranch} /><label className="block"><span className="mb-1.5 block text-xs font-bold text-[#333]">Effective Date</span><div className="relative"><CalendarDays className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#999]" /><input type="date" value={effectiveDate} onChange={(event) => setEffectiveDate(event.target.value)} className="w-full rounded-lg border border-[#d7d7d7] bg-white py-2.5 pl-9 pr-3 text-sm text-[#222] outline-none focus:border-[#111] focus:ring-2 focus:ring-[#111]/10" /></div></label><label className="flex items-center gap-3 rounded-lg border border-[#e1e1e1] bg-[#fafafa] px-3 py-3 md:col-span-2"><input type="checkbox" checked={shareData} onChange={(event) => setShareData(event.target.checked)} className="h-4 w-4 accent-[#111]" /><span><span className="block text-sm font-semibold text-[#333]">Share data externally</span><span className="mt-0.5 block text-xs text-[#777]">Allow this partner type to share approved information with configured external systems.</span></span></label></div>{error && <div className="mx-5 mb-4 rounded-lg border border-[#d7d7d7] bg-[#f7f7f7] px-3 py-2 text-sm text-[#333]">{error}</div>}<div className="flex items-center justify-end gap-2 border-t border-[#e7e7e7] px-5 py-4"><button onClick={onClose} className="rounded-lg border border-[#d7d7d7] px-4 py-2 text-sm font-semibold text-[#555] hover:bg-[#f4f4f4]">Cancel</button><button onClick={submit} disabled={saving} className="inline-flex items-center gap-2 rounded-lg bg-[#111] px-4 py-2 text-sm font-semibold text-white hover:bg-[#2c2c2c] disabled:opacity-50">{saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}{saving ? "Saving..." : "Save"}</button></div></>}</div></div>
}

function SelectField({ label, value, onChange, options, placeholder, disabled = false }: { label: string; value: string; onChange: (value: string) => void; options: { value: string; label: string }[]; placeholder: string; disabled?: boolean }) {
  return <label className="block"><span className="mb-1.5 block text-xs font-bold text-[#333]">{label}</span><div className="relative"><select value={value} onChange={(event) => onChange(event.target.value)} disabled={disabled} className="w-full appearance-none rounded-lg border border-[#d7d7d7] bg-white px-3 py-2.5 pr-9 text-sm text-[#222] outline-none focus:border-[#111] focus:ring-2 focus:ring-[#111]/10 disabled:bg-[#f7f7f7] disabled:text-[#aaa]"><option value="">{placeholder}</option>{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select><ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#999]" /></div></label>
}

function SetupManager({
  assignment,
  summary,
  onRefresh,
}: {
  assignment: PartnerTypeAssignment
  summary?: SetupSummary
  onRefresh: () => void
}) {
  const [tab, setTab] = useState<SetupTab>("documents")

  const tabs: { key: SetupTab; label: string; icon: React.ReactNode }[] = [
    { key: "documents", label: "Documents", icon: <FileText className="h-3.5 w-3.5" /> },
    { key: "fields", label: "Fields", icon: <FileSpreadsheet className="h-3.5 w-3.5" /> },
    { key: "contacts", label: "Contacts", icon: <Contact className="h-3.5 w-3.5" /> },
    { key: "banks", label: "Banks", icon: <Landmark className="h-3.5 w-3.5" /> },
    { key: "kyc", label: "KYC", icon: <CheckCircle className="h-3.5 w-3.5" /> },
  ]

  return (
    <div className="border-t border-border">
      <div className="flex gap-1 px-4 pt-3 border-b border-border bg-muted/20">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
              tab === t.key
                ? "border-primary text-foreground bg-card"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>
      <div className="p-4">
        {tab === "documents" && <DocumentsTab assignmentId={assignment.id} partnerTypeId={assignment.partnerType} onRefresh={onRefresh} />}
        {tab === "fields" && <FieldsTab assignmentId={assignment.id} onRefresh={onRefresh} />}
        {tab === "contacts" && <ContactsTab assignmentId={assignment.id} onRefresh={onRefresh} />}
        {tab === "banks" && <BanksTab assignmentId={assignment.id} onRefresh={onRefresh} />}
        {tab === "kyc" && <KYCTab assignmentId={assignment.id} onRefresh={onRefresh} />}
      </div>
    </div>
  )
}

function DocumentsTab({ assignmentId, partnerTypeId, onRefresh }: { assignmentId: string; partnerTypeId: string; onRefresh: () => void }) {
  const [requirements, setRequirements] = useState<PartnerTypeDocumentRequirement[]>([])
  const [docs, setDocs] = useState<PartnerDocument[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState("")
  const [uploading, setUploading] = useState<string | null>(null)
  const fileRefs = useRef<Record<string, HTMLInputElement | null>>({})

  const [manualMode, setManualMode] = useState(false)
  const [manualReqId, setManualReqId] = useState("")
  const manualFileRef = useRef<HTMLInputElement | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setLoadError("")
    try {
      const [reqs, existing] = await Promise.all([
        fetchDocumentRequirements(partnerTypeId),
        getAssignmentDocuments(assignmentId),
      ])
      setRequirements(reqs.filter((r) => r.isActive))
      setDocs(existing)
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "Failed to load")
      setManualMode(true)
    }
    setLoading(false)
  }, [assignmentId, partnerTypeId])
  useEffect(() => { load() }, [load])

  function getDocForRequirement(reqId: string): PartnerDocument | undefined {
    return docs.find((d) => d.documentRequirement === reqId)
  }

  async function handleFilePick(reqId: string, file: File) {
    setUploading(reqId)
    try {
      await uploadAssignmentDocumentFile(assignmentId, reqId, file)
      load()
      onRefresh()
    } catch {}
    setUploading(null)
  }

  async function handleManualUpload() {
    if (!manualReqId || !manualFileRef.current?.files?.[0]) return
    setUploading("manual")
    try {
      await uploadAssignmentDocumentFile(assignmentId, manualReqId, manualFileRef.current.files[0])
      setManualReqId("")
      if (manualFileRef.current) manualFileRef.current.value = ""
      load()
      onRefresh()
    } catch {}
    setUploading(null)
  }

  async function handleVerify(docId: string) {
    try {
      await updateAssignmentDocument(assignmentId, docId, { status: "APPROVED" })
      load()
      onRefresh()
    } catch {}
  }

  async function handleReject(docId: string) {
    try {
      await updateAssignmentDocument(assignmentId, docId, { status: "REJECTED" })
      load()
      onRefresh()
    } catch {}
  }

  if (loading) return <Loader2 className="h-5 w-5 animate-spin text-muted-foreground mx-auto" />

  const activeReqs = requirements.filter((r) => r.isActive)

  return (
    <div className="space-y-3">
      {loadError && (
        <div className="p-2 rounded bg-[var(--color-bg-warning-soft)] text-xs text-[var(--color-text-warning-soft)]">
          {loadError}
        </div>
      )}

      {activeReqs.length > 0 ? (
        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Required Documents</p>
          {activeReqs.map((req) => {
            const doc = getDocForRequirement(req.id)
            return (
              <div key={req.id} className="flex items-center justify-between rounded-lg border border-border px-4 py-3">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground">{req.description || req.code}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">{req.code}{req.isMandatory ? " · Required" : " · Optional"}</p>
                </div>
                <div className="flex items-center gap-3 flex-none ml-4">
                  {doc ? (
                    <>
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium ${
                        doc.status === "APPROVED" ? "bg-[var(--color-bg-success-soft)] text-[var(--color-text-success-soft)]" :
                        doc.status === "REJECTED" || doc.status === "EXPIRED" ? "bg-[var(--color-bg-destructive-soft)] text-[var(--color-text-destructive-soft)]" :
                        "bg-[var(--color-bg-warning-soft)] text-[var(--color-text-warning-soft)]"
                      }`}>{doc.status}</span>
                      {doc.status === "UPLOADED" || doc.status === "NOT_SUBMITTED" ? (
                        <>
                          <button onClick={() => handleVerify(doc.id)} className="p-1 text-[var(--color-feedback-success)] hover:bg-[var(--color-bg-success-soft)] rounded" title="Approve"><CheckCircle className="h-4 w-4" /></button>
                          <button onClick={() => handleReject(doc.id)} className="p-1 text-[var(--color-feedback-destructive)] hover:bg-[var(--color-bg-destructive-soft)] rounded" title="Reject"><XCircle className="h-4 w-4" /></button>
                        </>
                      ) : null}
                    </>
                  ) : (
                    <>
                      <input type="file" ref={(el) => { fileRefs.current[req.id] = el }} onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFilePick(req.id, f) }} className="hidden" accept=".pdf,.jpg,.jpeg,.png" />
                      <button onClick={() => fileRefs.current[req.id]?.click()} disabled={uploading === req.id} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors">
                        {uploading === req.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Upload className="h-3.5 w-3.5" />}
                        Upload
                      </button>
                    </>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      ) : !loadError ? (
        <p className="text-sm text-muted-foreground text-center py-4">No document requirements configured for this partner type.</p>
      ) : null}

      {manualMode && (
        <div className="border-t border-border pt-3 mt-3">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">Upload by Document ID</p>
          <div className="flex items-center gap-2">
            <input value={manualReqId} onChange={(e) => setManualReqId(e.target.value)} placeholder="Document Requirement UUID" className="flex-1 rounded border border-input bg-card px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50" />
            <input type="file" ref={manualFileRef} className="hidden" accept=".pdf,.jpg,.jpeg,.png" />
            <button onClick={() => manualFileRef.current?.click()} className="px-2 py-1.5 rounded border border-input text-xs text-foreground hover:bg-muted">Choose File</button>
            <button onClick={handleManualUpload} disabled={uploading === "manual" || !manualReqId} className="flex items-center gap-1 px-3 py-1.5 rounded bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 disabled:opacity-50">
              {uploading === "manual" ? <Loader2 className="h-3 w-3 animate-spin" /> : <Upload className="h-3 w-3" />}
              Upload
            </button>
          </div>
        </div>
      )}

      {docs.length > 0 && (
        <div className="border-t border-border pt-3 mt-3">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">All Uploaded Documents ({docs.length})</p>
          <div className="space-y-1">
            {docs.map((doc) => (
              <div key={doc.id} className="flex items-center justify-between rounded border border-border px-3 py-2 text-xs">
                <span className="text-foreground truncate">{doc.documentRequirementName || doc.documentRequirementCode || doc.id}</span>
                <span className={`ml-2 px-1.5 py-0.5 rounded text-[10px] font-medium flex-none ${
                  doc.status === "APPROVED" ? "bg-[var(--color-bg-success-soft)] text-[var(--color-text-success-soft)]" :
                  doc.status === "REJECTED" || doc.status === "EXPIRED" ? "bg-[var(--color-bg-destructive-soft)] text-[var(--color-text-destructive-soft)]" :
                  "bg-[var(--color-bg-warning-soft)] text-[var(--color-text-warning-soft)]"
                }`}>{doc.status}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function FieldsTab({ assignmentId, onRefresh }: { assignmentId: string; onRefresh: () => void }) {
  const [fields, setFields] = useState<PartnerDynamicFieldValue[]>([])
  const [loading, setLoading] = useState(true)
  const load = useCallback(async () => {
    setLoading(true)
    try { setFields(await getAssignmentFieldValues(assignmentId)) } catch {}
    setLoading(false)
  }, [assignmentId])
  useEffect(() => { load() }, [load])

  const [editValues, setEditValues] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const ev: Record<string, string> = {}
    for (const f of fields) {
      const v = f.valueJson
      ev[f.id] = typeof v === "object" && v !== null ? String((v as Record<string, unknown>).value ?? "") : String(v ?? "")
    }
    setEditValues(ev)
  }, [fields])

  async function handleSave() {
    setSaving(true)
    try {
      const payload = fields.map((f) => ({
        field_config: f.fieldConfig,
        value_json: { value: editValues[f.id] ?? "" },
      }))
      await updateAssignmentFieldValues(assignmentId, payload)
      load()
      onRefresh()
    } catch {}
    setSaving(false)
  }

  if (loading) return <Loader2 className="h-5 w-5 animate-spin text-muted-foreground mx-auto" />

  return (
    <div className="space-y-3">
      {fields.map((f) => (
        <div key={f.id} className="flex items-center gap-3">
          <span className="text-sm text-foreground w-40 flex-none">{f.fieldName || f.fieldCode}</span>
          <input
            type={f.fieldType === "DATE" ? "date" : "text"}
            value={editValues[f.id] ?? ""}
            onChange={(e) => setEditValues((ev) => ({ ...ev, [f.id]: e.target.value }))}
            className="flex-1 rounded border border-input bg-card px-2 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
          />
          <span className="text-[10px] text-muted-foreground w-16 text-right">{f.fieldType}</span>
        </div>
      ))}
      {fields.length === 0 && <p className="text-sm text-muted-foreground text-center py-4">No dynamic fields configured.</p>}
      {fields.length > 0 && (
        <div className="flex justify-end pt-2">
          <button onClick={handleSave} disabled={saving} className="flex items-center gap-1 px-3 py-1.5 rounded bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 disabled:opacity-50">
            {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : <CheckCircle className="h-3 w-3" />}
            Save Fields
          </button>
        </div>
      )}
    </div>
  )
}

function ContactsTab({ assignmentId, onRefresh }: { assignmentId: string; onRefresh: () => void }) {
  const [contacts, setContacts] = useState<PartnerAssignmentContact[]>([])
  const [loading, setLoading] = useState(true)
  const load = useCallback(async () => {
    setLoading(true)
    try { setContacts(await getAssignmentContacts(assignmentId)) } catch {}
    setLoading(false)
  }, [assignmentId])
  useEffect(() => { load() }, [load])

  const [newContact, setNewContact] = useState({ contact_requirement: "", contact_type: "OTHER", first_name: "", last_name: "", email: "", phone: "", mobile: "", designation: "", is_primary: false, notes: "" })
  const [saving, setSaving] = useState(false)
  const [showForm, setShowForm] = useState(false)

  async function handleAdd() {
    if (!newContact.first_name) return
    setSaving(true)
    try {
      await createAssignmentContact(assignmentId, newContact)
      setNewContact({ contact_requirement: "", contact_type: "OTHER", first_name: "", last_name: "", email: "", phone: "", mobile: "", designation: "", is_primary: false, notes: "" })
      setShowForm(false)
      load()
      onRefresh()
    } catch {}
    setSaving(false)
  }

  async function handleDelete(contactId: string) {
    try { await deleteAssignmentContact(assignmentId, contactId); load(); onRefresh() } catch {}
  }

  if (loading) return <Loader2 className="h-5 w-5 animate-spin text-muted-foreground mx-auto" />

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <button onClick={() => setShowForm(!showForm)} className="flex items-center gap-1 px-3 py-1.5 rounded bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90">
          <Plus className="h-3 w-3" />
          Add Contact
        </button>
      </div>

      {showForm && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 p-3 rounded-lg border border-border bg-muted/20">
          <input placeholder="First Name *" value={newContact.first_name} onChange={(e) => setNewContact((d) => ({ ...d, first_name: e.target.value }))} className="rounded border border-input bg-card px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50" />
          <input placeholder="Last Name" value={newContact.last_name} onChange={(e) => setNewContact((d) => ({ ...d, last_name: e.target.value }))} className="rounded border border-input bg-card px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50" />
          <input placeholder="Email" value={newContact.email} onChange={(e) => setNewContact((d) => ({ ...d, email: e.target.value }))} className="rounded border border-input bg-card px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50" />
          <input placeholder="Phone" value={newContact.phone} onChange={(e) => setNewContact((d) => ({ ...d, phone: e.target.value }))} className="rounded border border-input bg-card px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50" />
          <input placeholder="Mobile" value={newContact.mobile} onChange={(e) => setNewContact((d) => ({ ...d, mobile: e.target.value }))} className="rounded border border-input bg-card px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50" />
          <input placeholder="Designation" value={newContact.designation} onChange={(e) => setNewContact((d) => ({ ...d, designation: e.target.value }))} className="rounded border border-input bg-card px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50" />
          <div className="flex items-center gap-2">
            <input type="checkbox" id="isPrimary" checked={newContact.is_primary} onChange={(e) => setNewContact((d) => ({ ...d, is_primary: e.target.checked }))} className="rounded border-border" />
            <label htmlFor="isPrimary" className="text-xs text-foreground">Is Primary</label>
          </div>
          <button onClick={handleAdd} disabled={saving || !newContact.first_name} className="flex items-center gap-1 px-3 py-1.5 rounded bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 disabled:opacity-50">
            {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Plus className="h-3 w-3" />}
            Save Contact
          </button>
        </div>
      )}

      <div className="space-y-2">
        {contacts.map((c) => (
          <div key={c.id} className="flex items-center justify-between rounded-lg border border-border px-3 py-2 text-sm">
            <div className="flex-1 min-w-0">
              <p className="font-medium text-foreground">{c.firstName} {c.lastName}</p>
              <p className="text-xs text-muted-foreground">{c.email} · {c.phone || c.mobile || "—"}{c.isPrimary ? " · PRIMARY" : ""}</p>
              <p className="text-xs text-muted-foreground">{c.contactType}{c.designation ? ` · ${c.designation}` : ""}</p>
            </div>
            <button onClick={() => handleDelete(c.id)} className="p-1 text-muted-foreground hover:text-destructive rounded flex-none ml-2" title="Delete">
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
        {contacts.length === 0 && <p className="text-sm text-muted-foreground text-center py-4">No contacts added yet.</p>}
      </div>
    </div>
  )
}

function BanksTab({ assignmentId, onRefresh }: { assignmentId: string; onRefresh: () => void }) {
  const [banks, setBanks] = useState<PartnerAssignmentBankAccount[]>([])
  const [loading, setLoading] = useState(true)
  const load = useCallback(async () => {
    setLoading(true)
    try { setBanks(await getAssignmentBankAccounts(assignmentId)) } catch {}
    setLoading(false)
  }, [assignmentId])
  useEffect(() => { load() }, [load])

  const [newBank, setNewBank] = useState({ bank_requirement: "", bank_type: "SAVINGS", bank_name: "", branch_name: "", account_name: "", account_number: "", swift_code: "", currency: "TZS", is_primary: false, notes: "" })
  const [saving, setSaving] = useState(false)
  const [showForm, setShowForm] = useState(false)

  async function handleAdd() {
    if (!newBank.bank_name || !newBank.account_name) return
    setSaving(true)
    try {
      await createAssignmentBankAccount(assignmentId, newBank)
      setNewBank({ bank_requirement: "", bank_type: "SAVINGS", bank_name: "", branch_name: "", account_name: "", account_number: "", swift_code: "", currency: "TZS", is_primary: false, notes: "" })
      setShowForm(false)
      load()
      onRefresh()
    } catch {}
    setSaving(false)
  }

  async function handleDelete(bankId: string) {
    try { await deleteAssignmentBankAccount(assignmentId, bankId); load(); onRefresh() } catch {}
  }

  if (loading) return <Loader2 className="h-5 w-5 animate-spin text-muted-foreground mx-auto" />

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <button onClick={() => setShowForm(!showForm)} className="flex items-center gap-1 px-3 py-1.5 rounded bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90">
          <Plus className="h-3 w-3" />
          Add Bank Account
        </button>
      </div>

      {showForm && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 p-3 rounded-lg border border-border bg-muted/20">
          <input placeholder="Bank Name *" value={newBank.bank_name} onChange={(e) => setNewBank((d) => ({ ...d, bank_name: e.target.value }))} className="rounded border border-input bg-card px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50" />
          <input placeholder="Branch" value={newBank.branch_name} onChange={(e) => setNewBank((d) => ({ ...d, branch_name: e.target.value }))} className="rounded border border-input bg-card px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50" />
          <input placeholder="Account Name *" value={newBank.account_name} onChange={(e) => setNewBank((d) => ({ ...d, account_name: e.target.value }))} className="rounded border border-input bg-card px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50" />
          <input placeholder="Account Number" value={newBank.account_number} onChange={(e) => setNewBank((d) => ({ ...d, account_number: e.target.value }))} className="rounded border border-input bg-card px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50" />
          <input placeholder="SWIFT Code" value={newBank.swift_code} onChange={(e) => setNewBank((d) => ({ ...d, swift_code: e.target.value }))} className="rounded border border-input bg-card px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50" />
          <input placeholder="Currency" value={newBank.currency} onChange={(e) => setNewBank((d) => ({ ...d, currency: e.target.value }))} className="rounded border border-input bg-card px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50" />
          <div className="flex items-center gap-2">
            <input type="checkbox" id="isPrimaryBank" checked={newBank.is_primary} onChange={(e) => setNewBank((d) => ({ ...d, is_primary: e.target.checked }))} className="rounded border-border" />
            <label htmlFor="isPrimaryBank" className="text-xs text-foreground">Is Primary</label>
          </div>
          <button onClick={handleAdd} disabled={saving || !newBank.bank_name || !newBank.account_name} className="flex items-center gap-1 px-3 py-1.5 rounded bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 disabled:opacity-50">
            {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Plus className="h-3 w-3" />}
            Save Bank
          </button>
        </div>
      )}

      <div className="space-y-2">
        {banks.map((b) => (
          <div key={b.id} className="flex items-center justify-between rounded-lg border border-border px-3 py-2 text-sm">
            <div className="flex-1 min-w-0">
              <p className="font-medium text-foreground">{b.bankName} · {b.accountName}</p>
              <p className="text-xs text-muted-foreground">{b.accountNumber}{b.swiftCode ? ` · SWIFT ${b.swiftCode}` : ""} · {b.currency}{b.isPrimary ? " · PRIMARY" : ""}</p>
              {b.branchName && <p className="text-xs text-muted-foreground">{b.branchName}</p>}
            </div>
            <button onClick={() => handleDelete(b.id)} className="p-1 text-muted-foreground hover:text-destructive rounded flex-none ml-2" title="Delete">
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
        {banks.length === 0 && <p className="text-sm text-muted-foreground text-center py-4">No bank accounts added yet.</p>}
      </div>
    </div>
  )
}

function KYCTab({ assignmentId, onRefresh }: { assignmentId: string; onRefresh: () => void }) {
  const [kyc, setKYC] = useState<PartnerKYCProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const load = useCallback(async () => {
    setLoading(true)
    try { setKYC(await getAssignmentKYC(assignmentId)) } catch {}
    setLoading(false)
  }, [assignmentId])
  useEffect(() => { load() }, [load])

  const [kycStatus, setKycStatus] = useState("NOT_SET")
  const [notes, setNotes] = useState("")
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (kyc) {
      setKycStatus(kyc.kycStatus)
      setNotes(kyc.notes ?? "")
    }
  }, [kyc])

  async function handleSave() {
    setSaving(true)
    try {
      await updateAssignmentKYC(assignmentId, {
        kyc_status: kycStatus,
        last_review_date: new Date().toISOString(),
        notes,
      })
      load()
      onRefresh()
    } catch {}
    setSaving(false)
  }

  if (loading) return <Loader2 className="h-5 w-5 animate-spin text-muted-foreground mx-auto" />

  return (
    <div className="space-y-4">
      {kyc && (
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className="text-center p-3 rounded-lg border border-border">
            <p className="text-2xl font-bold text-foreground">{kyc.riskScore ?? "—"}</p>
            <p className="text-xs text-muted-foreground">Risk Score</p>
          </div>
          <div className="text-center p-3 rounded-lg border border-border">
            <p className="text-2xl font-bold text-foreground">{kyc.riskLevel || "—"}</p>
            <p className="text-xs text-muted-foreground">Risk Level</p>
          </div>
          <div className="text-center p-3 rounded-lg border border-border">
            <p className="text-lg font-bold text-foreground">{kyc.lastReviewDate ? new Date(kyc.lastReviewDate).toLocaleDateString() : "—"}</p>
            <p className="text-xs text-muted-foreground">Last Review</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium text-foreground mb-1">KYC Status</label>
          <select
            value={kycStatus}
            onChange={(e) => setKycStatus(e.target.value)}
            className="w-full rounded-lg border border-input bg-card px-2.5 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
          >
            <option value="NOT_SET">Not Set</option>
            <option value="PENDING">Pending</option>
            <option value="CLEARED">Cleared</option>
            <option value="REJECTED">Rejected</option>
            <option value="ESCALATED">Escalated</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-foreground mb-1">Notes</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            className="w-full rounded-lg border border-input bg-card px-2.5 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
          />
        </div>
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-1 px-3 py-1.5 rounded bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 disabled:opacity-50"
        >
          {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : <CheckCircle className="h-3 w-3" />}
          Update KYC
        </button>
      </div>
    </div>
  )
}

function Field({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="text-sm">
      <span className="text-muted-foreground">{label}</span>
      <p className="text-foreground mt-0.5">{value || "-"}</p>
    </div>
  )
}

function MiniProgress({ label, pct }: { label: string; pct: number }) {
  return (
    <div className="text-center">
      <p className="text-xs font-medium text-foreground">{pct}%</p>
      <div className="mt-0.5 h-1 w-full rounded-full bg-[var(--color-bg-muted)] overflow-hidden">
        <div
          className="h-full rounded-full"
          style={{
            width: `${pct}%`,
            backgroundColor: pct >= 80
              ? "var(--color-feedback-success)"
              : pct >= 50
                ? "var(--color-feedback-warning)"
                : "var(--color-feedback-info)",
          }}
        />
      </div>
      <p className="text-[10px] text-muted-foreground mt-0.5">{label}</p>
    </div>
  )
}

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "-"
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric", month: "short", day: "numeric",
    hour: "2-digit", minute: "2-digit",
  })
}

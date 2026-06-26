import { useCallback, useEffect, useRef, useState } from "react"
import { useNavigate, useParams, useSearchParams } from "react-router-dom"
import { ArrowLeft, Loader2, Save, Plus, Trash2, Check, X, Search, ChevronDown } from "lucide-react"
import {
  getPartner,
  updatePartner,
  updateIndividualProfile,
  updateCorporateProfile,
  assignPartnerType,
  fetchPartnerTypes,
  fetchBranches,
  fetchLocations,
} from "../../lib/api"
import type {
  PartnerDetail as PartnerDetailType,
  PartnerTypeRecord,
  BranchRecord,
  LocationRecord,
} from "../../lib/types"

export default function PartnerEdit() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const fromOnboarding = searchParams.get("from") === "onboarding"

  const [partner, setPartner] = useState<PartnerDetailType | null>(null)
  const [partnerTypes, setPartnerTypes] = useState<PartnerTypeRecord[]>([])
  const [branches, setBranches] = useState<BranchRecord[]>([])
  const [allLocations, setAllLocations] = useState<LocationRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")
  const [tab, setTab] = useState<"core" | "profile" | "assign">("core")

  const [form, setForm] = useState<Record<string, string>>({})
  const [profileForm, setProfileForm] = useState<Record<string, string>>({})

  const [selectedType, setSelectedType] = useState("")
  const [selectedBranches, setSelectedBranches] = useState<BranchRecord[]>([])
  const [branchQuery, setBranchQuery] = useState("")
  const [branchOpen, setBranchOpen] = useState(false)
  const branchRef = useRef<HTMLDivElement>(null)
  const [selectedLocation, setSelectedLocation] = useState("")
  const [shareData, setShareData] = useState(false)
  const [effectiveDate, setEffectiveDate] = useState("")

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError("")
    try {
      const [p, types, brs, locs] = await Promise.all([
        getPartner(id),
        fetchPartnerTypes(),
        fetchBranches(),
        fetchLocations(),
      ])
      setPartner(p)
      setPartnerTypes(types)
      setBranches(brs)
      setAllLocations(locs)

      const f: Record<string, string> = {}
      for (const key of UPDATE_FIELDS) {
        const val = (p as unknown as Record<string, string>)[key]
        f[key] = val ?? ""
      }
      setForm(f)

      const pf: Record<string, string> = {}
      if (p.individualProfile) {
        for (const key of INDIVIDUAL_FIELDS) {
          const val = (p.individualProfile as unknown as Record<string, string>)[key]
          pf[key] = val ?? ""
        }
      } else if (p.corporateProfile) {
        for (const key of CORPORATE_FIELDS) {
          const val = (p.corporateProfile as unknown as Record<string, string>)[key]
          pf[key] = val ?? ""
        }
      }
      setProfileForm(pf)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load partner")
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => { load() }, [load])

  async function handleSaveCore() {
    if (!id) return
    setSaving(true)
    setError("")
    setSuccess("")
    try {
      const body: Record<string, unknown> = {}
      for (const key of UPDATE_FIELDS) {
        body[key] = form[key] || null
      }
      await updatePartner(id, body)
      setSuccess("Core information saved.")
      load()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Save failed")
    } finally {
      setSaving(false)
    }
  }

  async function handleSaveProfile() {
    if (!id || !partner) return
    setSaving(true)
    setError("")
    setSuccess("")
    try {
      if (partner.partnerCategory === "INDIVIDUAL" || partner.individualProfile) {
        await updateIndividualProfile(id, profileForm)
      } else {
        await updateCorporateProfile(id, profileForm)
      }
      setSuccess("Profile saved.")
      load()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Save failed")
    } finally {
      setSaving(false)
    }
  }

  async function handleAssignType() {
    if (!id || !selectedType) return
    setSaving(true)
    setError("")
    setSuccess("")
    try {
      await assignPartnerType(id, {
        partner_type: selectedType,
        branches: selectedBranches.map((b) => b.id),
        location: selectedLocation || null,
        share_data_externally: shareData,
        effective_date: effectiveDate || null,
      })
      setSuccess("Partner type assigned.")
      setSelectedType("")
      setSelectedBranches([])
      setSelectedLocation("")
      setShareData(false)
      setEffectiveDate("")
      load()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Assignment failed")
    } finally {
      setSaving(false)
    }
  }

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (branchRef.current && !branchRef.current.contains(e.target as Node)) {
        setBranchOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClick)
    return () => document.removeEventListener("mousedown", handleClick)
  }, [])

  const filteredBranches = branches.filter(
    (b) => !selectedBranches.some((sb) => sb.id === b.id),
  )
  const branchSearchResults = branchQuery
    ? filteredBranches.filter((b) => b.name.toLowerCase().includes(branchQuery.toLowerCase()))
    : filteredBranches

  function handleBranchToggle(b: BranchRecord) {
    setSelectedBranches((prev) => {
      const exists = prev.find((sb) => sb.id === b.id)
      return exists ? prev.filter((sb) => sb.id !== b.id) : [...prev, b]
    })
    setBranchQuery("")
    setBranchOpen(false)
  }

  const branchIds = selectedBranches.map((b) => b.id)
  const locationOptions = branchIds.length > 0
    ? allLocations.filter((l) => branchIds.includes(l.branchId))
    : allLocations

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!partner) return null

  const isCorporate = partner.partnerCategory === "CORPORATE" || !!partner.corporateProfile

  return (
    <div className="space-y-6">
      <button
        onClick={() => navigate(`/partners/${id}${fromOnboarding ? "?from=onboarding" : ""}`)}
        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Partner Detail
      </button>

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Edit {partner.displayName}</h1>
          <p className="text-sm text-muted-foreground mt-1">{partner.partnerNumber}</p>
        </div>
        <span className="text-sm text-muted-foreground">{partner.partnerCategory || partner.partnerType}</span>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-[var(--color-bg-destructive-soft)] text-[var(--color-text-destructive-soft)] text-sm">
          {error}
        </div>
      )}
      {success && (
        <div className="p-4 rounded-lg bg-[var(--color-bg-success-soft)] text-[var(--color-text-success-soft)] text-sm flex items-center gap-2">
          <Check className="h-4 w-4" />
          {success}
        </div>
      )}

      <div className="flex gap-1 border-b border-border">
        {[
          { key: "core", label: "Core Info" },
          { key: "profile", label: "Profile" },
          { key: "assign", label: "Assign Type" },
        ].map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key as typeof tab)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t.key
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "core" && (
        <div className="rounded-xl border border-border bg-card p-5">
          <h2 className="text-base font-semibold text-foreground mb-4">Core Information</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <FormField label="First Name" value={form.firstName ?? ""} onChange={(v) => setForm((f) => ({ ...f, firstName: v }))} />
            <FormField label="Other Name" value={form.otherName ?? ""} onChange={(v) => setForm((f) => ({ ...f, otherName: v }))} />
            <FormField label="Surname" value={form.surname ?? ""} onChange={(v) => setForm((f) => ({ ...f, surname: v }))} />
            <FormField label="Email" value={form.email ?? ""} onChange={(v) => setForm((f) => ({ ...f, email: v }))} />
            <FormField label="Mobile Number" value={form.mobileNumber ?? ""} onChange={(v) => setForm((f) => ({ ...f, mobileNumber: v }))} />
            <FormField label="Telephone" value={form.telephoneNumber ?? ""} onChange={(v) => setForm((f) => ({ ...f, telephoneNumber: v }))} />
            <FormField label="Physical Address" value={form.physicalAddress ?? ""} onChange={(v) => setForm((f) => ({ ...f, physicalAddress: v }))} />
            <FormField label="Postal Address" value={form.postalAddress ?? ""} onChange={(v) => setForm((f) => ({ ...f, postalAddress: v }))} />
            <FormField label="TIN Number" value={form.tinNumber ?? ""} onChange={(v) => setForm((f) => ({ ...f, tinNumber: v }))} />
            <FormField label="Company Name" value={form.companyName ?? ""} onChange={(v) => setForm((f) => ({ ...f, companyName: v }))} />
            <FormField label="Contact Person" value={form.contactPerson ?? ""} onChange={(v) => setForm((f) => ({ ...f, contactPerson: v }))} />
            <FormField label="Contact Phone" value={form.contactPersonPhone ?? ""} onChange={(v) => setForm((f) => ({ ...f, contactPersonPhone: v }))} />
            <FormField label="Contact Email" value={form.contactPersonEmail ?? ""} onChange={(v) => setForm((f) => ({ ...f, contactPersonEmail: v }))} />
            <FormField label="Occupation" value={form.occupation ?? ""} onChange={(v) => setForm((f) => ({ ...f, occupation: v }))} />
            <FormField label="Nationality" value={form.nationality ?? ""} onChange={(v) => setForm((f) => ({ ...f, nationality: v }))} />
            <FormField label="Political Risk" value={form.politicalRisk ?? ""} onChange={(v) => setForm((f) => ({ ...f, politicalRisk: v }))} />
            <FormField label="AML Risk" value={form.amlRisk ?? ""} onChange={(v) => setForm((f) => ({ ...f, amlRisk: v }))} />
          </div>
          <div className="mt-6 flex justify-end">
            <button
              onClick={handleSaveCore}
              disabled={saving}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              Save Core Info
            </button>
          </div>
        </div>
      )}

      {tab === "profile" && (
        <div className="rounded-xl border border-border bg-card p-5">
          <h2 className="text-base font-semibold text-foreground mb-4">
            {isCorporate ? "Corporate Profile" : "Individual Profile"}
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {isCorporate ? (
              <>
                <FormField label="Company Name" value={profileForm.companyName ?? ""} onChange={(v) => setProfileForm((f) => ({ ...f, companyName: v }))} />
                <FormField label="TIN Number" value={profileForm.tinNumber ?? ""} onChange={(v) => setProfileForm((f) => ({ ...f, tinNumber: v }))} />
                <FormField label="Incorporation Date" value={profileForm.incorporationDate ?? ""} onChange={(v) => setProfileForm((f) => ({ ...f, incorporationDate: v }))} />
                <FormField label="Industry" value={profileForm.industry ?? ""} onChange={(v) => setProfileForm((f) => ({ ...f, industry: v }))} />
                <FormField label="Contact Person" value={profileForm.contactPerson ?? ""} onChange={(v) => setProfileForm((f) => ({ ...f, contactPerson: v }))} />
                <FormField label="Contact Person Phone" value={profileForm.contactPersonPhone ?? ""} onChange={(v) => setProfileForm((f) => ({ ...f, contactPersonPhone: v }))} />
                <FormField label="Contact Person Email" value={profileForm.contactPersonEmail ?? ""} onChange={(v) => setProfileForm((f) => ({ ...f, contactPersonEmail: v }))} />
              </>
            ) : (
              <>
                <FormField label="Title" value={profileForm.title ?? ""} onChange={(v) => setProfileForm((f) => ({ ...f, title: v }))} />
                <FormField label="First Name" value={profileForm.firstName ?? ""} onChange={(v) => setProfileForm((f) => ({ ...f, firstName: v }))} />
                <FormField label="Other Name" value={profileForm.otherName ?? ""} onChange={(v) => setProfileForm((f) => ({ ...f, otherName: v }))} />
                <FormField label="Surname" value={profileForm.surname ?? ""} onChange={(v) => setProfileForm((f) => ({ ...f, surname: v }))} />
                <FormField label="Gender" value={profileForm.gender ?? ""} onChange={(v) => setProfileForm((f) => ({ ...f, gender: v }))} />
                <FormField label="Date of Birth" value={profileForm.dateOfBirth ?? ""} onChange={(v) => setProfileForm((f) => ({ ...f, dateOfBirth: v }))} />
                <FormField label="Marital Status" value={profileForm.maritalStatus ?? ""} onChange={(v) => setProfileForm((f) => ({ ...f, maritalStatus: v }))} />
                <FormField label="Occupation" value={profileForm.occupation ?? ""} onChange={(v) => setProfileForm((f) => ({ ...f, occupation: v }))} />
                <FormField label="Nationality" value={profileForm.nationality ?? ""} onChange={(v) => setProfileForm((f) => ({ ...f, nationality: v }))} />
                <FormField label="ID Type" value={profileForm.identificationType ?? ""} onChange={(v) => setProfileForm((f) => ({ ...f, identificationType: v }))} />
                <FormField label="ID Number" value={profileForm.identificationNumber ?? ""} onChange={(v) => setProfileForm((f) => ({ ...f, identificationNumber: v }))} />
              </>
            )}
          </div>
          <div className="mt-6 flex justify-end">
            <button
              onClick={handleSaveProfile}
              disabled={saving}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              Save Profile
            </button>
          </div>
        </div>
      )}

      {tab === "assign" && (
        <div className="space-y-6">
          <div className="rounded-xl border border-border bg-card p-5">
            <h2 className="text-base font-semibold text-foreground mb-4">Assign New Partner Type</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Partner Type *</label>
                <select
                  value={selectedType}
                  onChange={(e) => setSelectedType(e.target.value)}
                  className="w-full rounded-lg border border-border bg-background text-foreground px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                >
                  <option value="">Select type...</option>
                  {partnerTypes.map((t) => (
                    <option key={t.id} value={t.id}>{t.name} ({t.code})</option>
                  ))}
                </select>
              </div>
              <div ref={branchRef} className="relative">
                <label className="block text-sm font-medium text-foreground mb-1">Branches</label>
                {selectedBranches.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mb-1.5">
                    {selectedBranches.map((b) => (
                      <span key={b.id} className="inline-flex items-center gap-1 rounded-full bg-primary/10 text-primary px-2.5 py-0.5 text-xs font-medium">
                        {b.name}
                        <button onClick={() => handleBranchToggle(b)} className="hover:text-destructive">
                          <X className="h-3 w-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                )}
                <div className="relative">
                  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <input
                    type="text"
                    placeholder="Search branches..."
                    value={branchQuery}
                    onChange={(e) => { setBranchQuery(e.target.value); setBranchOpen(true) }}
                    onFocus={() => setBranchOpen(true)}
                    className="w-full rounded-lg border border-border bg-background text-foreground pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                  />
                </div>
                {branchOpen && branchSearchResults.length > 0 && (
                  <div className="absolute z-20 mt-1 w-full rounded-lg border border-border bg-card shadow-lg max-h-48 overflow-y-auto">
                    {branchSearchResults.map((b) => (
                      <button
                        key={b.id}
                        onClick={() => handleBranchToggle(b)}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-accent transition-colors"
                      >
                        {b.name} <span className="text-muted-foreground text-xs ml-1">({b.code})</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <div className="relative">
                <label className="block text-sm font-medium text-foreground mb-1">Location</label>
                <select
                  value={selectedLocation}
                  onChange={(e) => setSelectedLocation(e.target.value)}
                  className="w-full rounded-lg border border-border bg-background text-foreground px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                >
                  <option value="">{selectedBranches.length === 0 ? "Select a branch first" : "No location..."}</option>
                  {locationOptions.map((l) => (
                    <option key={l.id} value={l.id}>{l.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Effective Date</label>
                <input
                  type="date"
                  value={effectiveDate}
                  onChange={(e) => setEffectiveDate(e.target.value)}
                  className="w-full rounded-lg border border-border bg-background text-foreground px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="shareData"
                  checked={shareData}
                  onChange={(e) => setShareData(e.target.checked)}
                  className="rounded border-border"
                />
                <label htmlFor="shareData" className="text-sm text-foreground">Share Data Externally</label>
              </div>
            </div>
            <div className="mt-6 flex justify-end">
              <button
                onClick={handleAssignType}
                disabled={saving || !selectedType}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
              >
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                Assign Type
              </button>
            </div>
          </div>

          {partner.typeAssignments?.length > 0 && (
            <div className="rounded-xl border border-border bg-card p-5">
              <h2 className="text-base font-semibold text-foreground mb-4">Current Assignments ({partner.typeAssignments.length})</h2>
              <div className="space-y-2">
                {partner.typeAssignments.map((ta) => (
                  <div key={ta.id} className="flex items-center justify-between rounded-lg border border-border px-4 py-3">
                    <div>
                      <span className="font-medium text-foreground">{ta.partnerTypeName}</span>
                      <span className="text-sm text-muted-foreground ml-2">({ta.partnerTypeCode})</span>
                      {ta.branchName && (
                        <span className="text-sm text-muted-foreground ml-3">{ta.branchName}{ta.locationName ? ` / ${ta.locationName}` : ""}</span>
                      )}
                    </div>
                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      ta.status === "ACTIVE"
                        ? "bg-[var(--color-bg-success-soft)] text-[var(--color-text-success-soft)]"
                        : "bg-[var(--color-bg-destructive-soft)] text-[var(--color-text-destructive-soft)]"
                    }`}>
                      {ta.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

const UPDATE_FIELDS = [
  "firstName", "otherName", "surname", "email", "mobileNumber",
  "telephoneNumber", "physicalAddress", "postalAddress",
  "tinNumber", "companyName", "contactPerson", "contactPersonPhone",
  "contactPersonEmail", "occupation", "nationality",
  "politicalRisk", "amlRisk",
]

const INDIVIDUAL_FIELDS = [
  "title", "firstName", "otherName", "surname", "gender",
  "dateOfBirth", "maritalStatus", "occupation", "nationality",
  "identificationType", "identificationNumber",
]

const CORPORATE_FIELDS = [
  "companyName", "tinNumber", "incorporationDate", "industry",
  "contactPerson", "contactPersonPhone", "contactPersonEmail",
]

function FormField({
  label,
  value,
  onChange,
}: {
  label: string
  value: string
  onChange: (v: string) => void
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-foreground mb-1">{label}</label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-border bg-background text-foreground px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
      />
    </div>
  )
}

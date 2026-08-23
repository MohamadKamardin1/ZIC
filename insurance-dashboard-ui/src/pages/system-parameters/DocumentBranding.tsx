import { useEffect, useState } from "react"
import { Palette, Save, UploadCloud } from "lucide-react"
import { ApiClientError, request } from "../../lib/apiClient"
import { ErrorCoach } from "../../components/ErrorCoach"
import { InfoBanner } from "../../components/ui/Overlays"
import { useToast } from "../../components/ui/Toast"

type BrandingVersion = {
  code: string
  version: number
  logo_url?: string | null
  company_name: string
  address: string
  phone: string
  email: string
  registration_number: string
  footer_legal_text: string
  accent_colors: Record<string, string>
  is_active: boolean
  created_at?: string | null
}

type BrandingPayload = BrandingVersion & { history?: BrandingVersion[] }

type BrandingForm = Omit<BrandingVersion, "code" | "version" | "logo_url" | "is_active" | "created_at"> & { logo_file?: File }

const initialForm: BrandingForm = {
  company_name: "",
  address: "",
  phone: "",
  email: "",
  registration_number: "",
  footer_legal_text: "",
  accent_colors: { primary: "#183a91", accent: "#d94754", table_header: "#edf1f4" },
}

function formatDate(value?: string | null) {
  if (!value) return "—"
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

export default function DocumentBranding() {
  const { toast } = useToast()
  const [form, setForm] = useState<BrandingForm>(initialForm)
  const [current, setCurrent] = useState<BrandingPayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<unknown>(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const payload = await request<BrandingPayload>("/api/v1/documents/branding/")
      setCurrent(payload)
      setForm({
        company_name: payload.company_name ?? "",
        address: payload.address ?? "",
        phone: payload.phone ?? "",
        email: payload.email ?? "",
        registration_number: payload.registration_number ?? "",
        footer_legal_text: payload.footer_legal_text ?? "",
        accent_colors: { ...initialForm.accent_colors, ...(payload.accent_colors ?? {}) },
      })
    } catch (caught) {
      setError(caught)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  const setField = (field: keyof BrandingForm, value: string) => setForm((previous) => ({ ...previous, [field]: value }))

  const save = async (event: React.FormEvent) => {
    event.preventDefault()
    setSaving(true)
    setError(null)
    const body = new FormData()
    body.append("company_name", form.company_name)
    body.append("address", form.address)
    body.append("phone", form.phone)
    body.append("email", form.email)
    body.append("registration_number", form.registration_number)
    body.append("footer_legal_text", form.footer_legal_text)
    body.append("accent_colors", JSON.stringify(form.accent_colors))
    if (form.logo_file) body.append("logo_file", form.logo_file)
    try {
      const payload = await request<BrandingPayload>("/api/v1/documents/branding/", { method: "POST", body })
      setCurrent(payload)
      setForm((previous) => ({ ...previous, logo_file: undefined }))
      toast({ tone: "success", title: `Branding version ${payload.version} created`, message: "Future documents will use this active branding." })
      await load()
    } catch (caught) {
      setError(caught)
    } finally {
      setSaving(false)
    }
  }

  const errorMessage = error instanceof ApiClientError && error.code === "AUTHENTICATION_REQUIRED"
    ? "Your session expired. Sign in again to manage document branding."
    : error instanceof Error ? error.message : "Document branding could not be loaded."

  if (loading) return <div className="flex min-h-64 items-center justify-center text-sm text-[var(--muted-foreground)]" role="status">Loading document branding…</div>

  return (
    <div className="space-y-5 p-4 md:p-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div><p className="text-xs font-bold uppercase tracking-[0.16em] text-[var(--muted-foreground)]">System Parameters / Documents</p><h1 className="mt-1 text-2xl font-bold tracking-tight">Document Branding</h1><p className="mt-1 max-w-2xl text-sm leading-6 text-[var(--muted-foreground)]">Manage the versioned company identity used by the shared quotation, proposal, and commitment document engine.</p></div>
        <div className="rounded-[10px] border bg-[var(--card)] px-4 py-3 text-right shadow-sm"><p className="text-xs text-[var(--muted-foreground)]">Active version</p><p className="text-xl font-bold text-[var(--primary)]">v{current?.version ?? 0}</p></div>
      </header>
      {error ? <ErrorCoach message={errorMessage} loginUrl={error instanceof ApiClientError && error.code === "AUTHENTICATION_REQUIRED" ? "/login" : undefined} /> : null}
      <InfoBanner title="Authoritative document branding">This versioned screen is the authoritative administration surface for generated documents. Legacy System Parameter branding values remain supported as a fallback when no versioned configuration exists.</InfoBanner>
      <form onSubmit={(event) => void save(event)} className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
        <section className="surface-card p-5"><div className="mb-5 flex items-center gap-2"><Palette size={18} className="text-[var(--primary)]" aria-hidden="true" /><div><h2 className="font-bold">Company details</h2><p className="text-sm text-[var(--muted-foreground)]">Saving creates a new immutable version and retires the previous active version.</p></div></div><div className="grid gap-4 sm:grid-cols-2"><label className="space-y-1.5 sm:col-span-2"><span className="text-sm font-semibold">Company name <b className="text-red-600">*</b></span><input required value={form.company_name} onChange={(event) => setField("company_name", event.target.value)} className="h-10 w-full rounded-[8px] border bg-[var(--card)] px-3 text-sm outline-none focus:border-[var(--ring)]" /></label><label className="space-y-1.5 sm:col-span-2"><span className="text-sm font-semibold">Address</span><textarea rows={3} value={form.address} onChange={(event) => setField("address", event.target.value)} className="w-full rounded-[8px] border bg-[var(--card)] px-3 py-2 text-sm outline-none focus:border-[var(--ring)]" /></label>{(["phone", "email", "registration_number"] as const).map((field) => <label key={field} className="space-y-1.5"><span className="text-sm font-semibold">{field.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase())}</span><input type={field === "email" ? "email" : "text"} value={form[field]} onChange={(event) => setField(field, event.target.value)} className="h-10 w-full rounded-[8px] border bg-[var(--card)] px-3 text-sm outline-none focus:border-[var(--ring)]" /></label>)}<label className="space-y-1.5 sm:col-span-2"><span className="text-sm font-semibold">Footer legal text</span><textarea rows={3} value={form.footer_legal_text} onChange={(event) => setField("footer_legal_text", event.target.value)} className="w-full rounded-[8px] border bg-[var(--card)] px-3 py-2 text-sm outline-none focus:border-[var(--ring)]" /></label></div><div className="mt-5 flex justify-end"><button type="submit" className="button-primary inline-flex items-center gap-2" disabled={saving || !form.company_name.trim()}><Save size={15} aria-hidden="true" />{saving ? "Creating version…" : "Create branding version"}</button></div></section>
        <aside className="space-y-5"><section className="surface-card p-5"><h2 className="font-bold">Logo and colors</h2><label className="mt-4 flex cursor-pointer items-center gap-3 rounded-[10px] border border-dashed p-4 text-sm hover:border-[var(--primary)]"><UploadCloud size={18} className="text-[var(--primary)]" aria-hidden="true" /><span className="min-w-0 flex-1"><span className="block font-semibold">Upload company logo</span><span className="block truncate text-xs text-[var(--muted-foreground)]">{form.logo_file?.name ?? "PNG, JPEG, or SVG"}</span></span><input type="file" accept="image/png,image/jpeg,image/svg+xml" className="sr-only" onChange={(event) => setForm((previous) => ({ ...previous, logo_file: event.target.files?.[0] }))} /></label>{current?.logo_url && <img src={current.logo_url} alt="Current company logo" className="mt-4 max-h-20 max-w-full rounded border bg-white p-2" />}<div className="mt-5 space-y-3">{(["primary", "accent", "table_header"] as const).map((color) => <label key={color} className="flex items-center justify-between gap-3 text-sm"><span className="font-semibold">{color.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase())}</span><span className="flex items-center gap-2"><input type="color" value={form.accent_colors[color] ?? "#183a91"} onChange={(event) => setForm((previous) => ({ ...previous, accent_colors: { ...previous.accent_colors, [color]: event.target.value } }))} className="h-8 w-10 cursor-pointer rounded border p-0.5" /><code className="text-xs text-[var(--muted-foreground)]">{form.accent_colors[color]}</code></span></label>)}</div></section><section className="surface-card p-5"><h2 className="font-bold">Version history</h2><div className="mt-3 space-y-2">{(current?.history ?? []).length === 0 ? <p className="text-sm text-[var(--muted-foreground)]">No versioned changes yet.</p> : current?.history?.map((version) => <div key={`${version.code}-${version.version}`} className="flex items-start justify-between gap-3 rounded-[8px] border px-3 py-2 text-sm"><div><p className="font-semibold">Version {version.version}{version.is_active && <span className="ml-2 text-xs text-emerald-700">Active</span>}</p><p className="text-xs text-[var(--muted-foreground)]">{version.company_name} · {formatDate(version.created_at)}</p></div></div>)}</div></section></aside>
      </form>
    </div>
  )
}

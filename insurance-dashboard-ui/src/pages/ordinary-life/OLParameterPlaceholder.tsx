import { Link } from "react-router-dom"
import { ArrowLeft, Settings2 } from "lucide-react"
import { InfoBanner } from "../../components/ui/Overlays"

export default function OLParameterPlaceholder({ title }: { title: string }) {
  return (
    <section className="space-y-5">
      <div className="surface-card overflow-hidden">
        <div className="bg-[linear-gradient(135deg,#232238,#4d4b79)] px-6 py-7 text-white">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-white/70">Ordinary Life Parameters</p>
          <h1 className="mt-2 text-2xl font-semibold">{title}</h1>
          <p className="mt-2 max-w-2xl text-sm text-white/75">This parameter group is reserved in the navigation and will be connected to its table-first API screen in a subsequent delivery.</p>
        </div>
        <div className="p-6">
          <InfoBanner title="Configuration screen pending">
            The navigation contract is ready. No business options are hardcoded here; the production screen will read its catalogs and effective-dated setup records from the backend.
          </InfoBanner>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <Link to="/ordinary-life/parameters" className="button-secondary"><ArrowLeft size={16} aria-hidden="true" /> Default Setup</Link>
            <span className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm text-muted-foreground"><Settings2 size={16} aria-hidden="true" /> Parameter-driven module</span>
          </div>
        </div>
      </div>
    </section>
  )
}

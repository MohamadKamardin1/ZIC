import { Link } from "react-router-dom"
import {
  ArrowRight,
  BookOpen,
  Building2,
  CheckSquare,
  Clock3,
  FileCheck2,
  Hash,
  Landmark,
  ListFilter,
  Loader2,
  RefreshCw,
  Scale,
  Settings2,
  ShieldCheck,
  Users,
  type LucideIcon,
} from "lucide-react"
import { PageHeader } from "./SharedComponents"
import { usePartnerOnboardingConfiguration } from "../../config/ConfigurationAPI"

const CONFIGURATION_SECTIONS = [
  {
    label: "Workflow & lifecycle",
    description: "Statuses, transitions, terminal states, and workflow controls.",
    icon: Scale,
    path: "/system-parameters/partner/workflow",
    key: "workflow",
  },
  {
    label: "Choice catalogues",
    description: "Controlled values used by every onboarding dropdown and validation rule.",
    icon: ListFilter,
    path: "/system-parameters/partner/choices",
    key: "choices",
  },
  {
    label: "Numbering & schedules",
    description: "Application numbers, partner numbers, sequence formats, and scheduled jobs.",
    icon: Hash,
    path: "/system-parameters/partner/numbering",
    key: "numbering",
  },
  {
    label: "Documents by partner type",
    description: "Required evidence, mandatory status, upload multiplicity, and document rules.",
    icon: FileCheck2,
    path: "/system-parameters/partner/documents",
    key: "documents",
  },
  {
    label: "Attributes by partner type",
    description: "Dynamic fields, defaults, visibility, data types, and validation rules.",
    icon: Settings2,
    path: "/system-parameters/partner/fields",
    key: "attributes",
  },
  {
    label: "Contacts by partner type",
    description: "Contact roles, requiredness, multiplicity, and display order.",
    icon: Users,
    path: "/system-parameters/partner/contact-types",
    key: "contacts",
  },
  {
    label: "Banks by partner type",
    description: "Bank account roles and type-specific validation requirements.",
    icon: Landmark,
    path: "/system-parameters/partner/bank-types",
    key: "banks",
  },
  {
    label: "Compliance & risk",
    description: "Risk weights, thresholds, high-risk industries, and screening rules.",
    icon: ShieldCheck,
    path: "/system-parameters/partner/compliance",
    key: "compliance",
  },
  {
    label: "Field validation",
    description: "Required base fields, age rules, uniqueness rules, and validation policies.",
    icon: BookOpen,
    path: "/system-parameters/partner/validation",
    key: "validation",
  },
  {
    label: "Scheduled tasks",
    description: "Draft cleanup, reminders, and compliance reporting windows.",
    icon: Clock3,
    path: "/system-parameters/partner/schedules",
    key: "schedules",
  },
]

function countParameters(groups: Array<{ parameters: unknown[]; children: Array<{ parameters: unknown[]; children: unknown[] }> }>): number {
  return groups.reduce((total, group) => (
    total + group.parameters.length + group.children.reduce((childTotal, child) => childTotal + child.parameters.length, 0)
  ), 0)
}

export default function PartnerParameters() {
  const { configuration, loading, error } = usePartnerOnboardingConfiguration()
  const partnerTypes = configuration?.partnerTypes ?? []
  const choiceLists = configuration?.choiceLists ?? []
  const scalarParameterCount = countParameters(configuration?.groups ?? [])
  const requirementCounts = partnerTypes.reduce((total, type) => total + type.documents.length + type.attributes.length + type.contacts.length + type.banks.length, 0)

  return (
    <div className="space-y-6 text-[#1b1b1b]">
      <PageHeader
        title="Partner Onboarding Parameters"
        description="One governed configuration workspace for every dynamic onboarding field, rule, and requirement."
      />

      <section className="rounded-xl border border-[#dedede] bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#737373]">Configuration control centre</p>
            <h2 className="mt-1 text-xl font-semibold tracking-tight">Everything onboarding reads is managed here</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-[#666]">
              Changes are stored by the backend, audited, and reflected in new and existing onboarding forms after the configuration cache refreshes.
            </p>
          </div>
          <div className="inline-flex items-center gap-2 rounded-lg border border-[#dedede] px-3 py-2 text-xs font-medium text-[#555]">
            <RefreshCw className="h-3.5 w-3.5" />
            <span>{configuration?.version ?? "partner-onboarding.v1"}</span>
          </div>
        </div>

        {loading ? (
          <div className="mt-6 flex items-center gap-2 border-t border-[#eeeeee] pt-5 text-sm text-[#666]">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading live configuration summary…
          </div>
        ) : error ? (
          <div className="mt-6 border-t border-[#eeeeee] pt-5 text-sm text-[#555]">
            The configuration summary could not be loaded. The domain editors remain available and use their protected CRUD endpoints.
          </div>
        ) : (
          <div className="mt-6 grid gap-3 border-t border-[#eeeeee] pt-5 sm:grid-cols-2 xl:grid-cols-4">
            {([
              { label: "Partner types", value: partnerTypes.length, Icon: Building2 },
              { label: "Choice catalogues", value: choiceLists.length, Icon: ListFilter },
              { label: "Dynamic requirements", value: requirementCounts, Icon: CheckSquare },
              { label: "Scalar parameters", value: scalarParameterCount, Icon: Settings2 },
            ] as Array<{ label: string; value: number; Icon: LucideIcon }>).map(({ label, value, Icon: SummaryIcon }) => {
              return (
                <div key={String(label)} className="rounded-lg border border-[#e5e5e5] bg-[#fafafa] px-4 py-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium uppercase tracking-[0.12em] text-[#777]">{label}</span>
                    <SummaryIcon className="h-4 w-4 text-[#555]" />
                  </div>
                  <p className="mt-2 text-2xl font-semibold tabular-nums">{String(value)}</p>
                </div>
              )
            })}
          </div>
        )}
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {CONFIGURATION_SECTIONS.map((section) => {
          const Icon = section.icon
          let count: number | null = null
          if (section.key === "choices") count = choiceLists.length
          if (section.key === "documents") count = partnerTypes.reduce((total, type) => total + type.documents.length, 0)
          if (section.key === "attributes") count = partnerTypes.reduce((total, type) => total + type.attributes.length, 0)
          if (section.key === "contacts") count = partnerTypes.reduce((total, type) => total + type.contacts.length, 0)
          if (section.key === "banks") count = partnerTypes.reduce((total, type) => total + type.banks.length, 0)
          return (
            <Link
              key={section.path}
              to={section.path}
              className="group rounded-xl border border-[#dedede] bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-[#999] hover:shadow-md"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-[#dedede] bg-[#fafafa] text-[#333]">
                  <Icon className="h-5 w-5" />
                </div>
                <ArrowRight className="h-4 w-4 text-[#999] transition group-hover:translate-x-1 group-hover:text-[#222]" />
              </div>
              <div className="mt-5 flex items-end justify-between gap-4">
                <div>
                  <h2 className="text-base font-semibold">{section.label}</h2>
                  <p className="mt-1 text-sm leading-5 text-[#666]">{section.description}</p>
                </div>
                {count !== null && <span className="text-2xl font-semibold tabular-nums text-[#333]">{count}</span>}
              </div>
            </Link>
          )
        })}
      </section>
    </div>
  )
}

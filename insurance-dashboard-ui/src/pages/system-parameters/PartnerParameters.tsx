import { Link } from "react-router-dom"
import {
  Scale,
  Grip,
  FileCheck,
  ShieldCheck,
  Columns,
  Users,
  Landmark,
  BookOpen,
  Hash,
  Clock,
  ChevronRight,
} from "lucide-react"
import { PageHeader } from "./SharedComponents"

const PARTNER_GROUPS = [
  {
    label: "Workflow & Statuses",
    description: "State machine transitions, allowed statuses, and permission rules",
    icon: Scale,
    path: "/system-parameters/partner/workflow",
    items: ["Status transition rules", "Permission-controlled actions", "Terminal statuses"],
  },
  {
    label: "Dropdown Choices",
    description: "All selectable options: ID types, titles, genders, industries, nationalities, etc.",
    icon: Grip,
    path: "/system-parameters/partner/choices",
    items: [
      "Identification types",
      "Titles, Genders, Marital statuses",
      "Industries, Nationalities",
      "Document types, Task types/statuses/priorities",
      "Contact types, Political/AML risk levels",
    ],
  },
  {
    label: "Numbering Formats",
    description: "Application and partner number prefixes, formats, and sequences",
    icon: Hash,
    path: "/system-parameters/partner/numbering",
    items: [
      "Individual app prefix (PA)",
      "Corporate app prefix (CO)",
      "Partner number prefix (PN)",
      "Year format inclusion",
      "Sequence digit padding",
    ],
  },
  {
    label: "Doc Config per Type",
    description: "Required documents per partner type with file type, size, and upload rules",
    icon: FileCheck,
    path: "/system-parameters/partner/documents",
    items: [
      "AGENT: TIRA license, commission agreement, ID, proof of address",
      "AGENCY: Agency license, corporate registration, TIRA agreement",
      "BANCASSURANCE: Bancassurance license, MoU, board resolution",
      "TAKAFUL: Shariah compliance cert, Takaful license, fund guarantee",
    ],
  },
  {
    label: "Field Config per Type",
    description: "Custom form fields, validation rules, and data types per partner type",
    icon: Columns,
    path: "/system-parameters/partner/fields",
    items: [
      "AGENT: License number, commission rate, territory, tax ID",
      "AGENCY: Registration number, override rate, agent count, contract dates",
      "BANCASSURANCE: License number, MoU dates, product lines, revenue share",
      "TAKAFUL: Shariah board info, fund details, Wakaful fee",
    ],
  },
  {
    label: "Contact Config per Type",
    description: "Required contact types and multiplicity per partner type",
    icon: Users,
    path: "/system-parameters/partner/contact-types",
    items: [
      "AGENT: PRIMARY, SECONDARY",
      "AGENCY: PRIMARY, TECHNICAL, BILLING, COMPLIANCE",
      "BANCASSURANCE: PRIMARY, TECHNICAL, BILLING, LEGAL",
      "TAKAFUL: PRIMARY, SHARIAH, BILLING",
    ],
  },
  {
    label: "Bank Config per Type",
    description: "Required bank account types and validation rules per partner type",
    icon: Landmark,
    path: "/system-parameters/partner/bank-types",
    items: [
      "AGENT: COMMISSION account",
      "AGENCY: OPERATIONS + COMMISSION accounts",
      "BANCASSURANCE: OPERATIONS + COMMISSION (with SWIFT)",
      "TAKAFUL: OPERATIONS + TAKAFUL_FUND (segregated)",
    ],
  },
  {
    label: "Compliance Rules",
    description: "Risk scoring weights, thresholds, and high-risk industry flags",
    icon: ShieldCheck,
    path: "/system-parameters/partner/compliance",
    items: [
      "Political/AML risk weights",
      "High-risk thresholds per partner type",
      "High-risk industries list",
      "PEP bonus score",
    ],
  },
  {
    label: "Field Validation",
    description: "Required fields per partner type, age validation, and data rules",
    icon: BookOpen,
    path: "/system-parameters/partner/validation",
    items: [
      "Individual required fields",
      "Corporate required fields",
      "Minimum age requirement",
      "Email uniqueness rules",
    ],
  },
  {
    label: "Scheduled Tasks",
    description: "Intervals for automated jobs: draft cleanup, reminders, reports",
    icon: Clock,
    path: "/system-parameters/partner/schedules",
    items: [
      "Expired draft cleanup period (days)",
      "Pending document reminder interval (days)",
      "Compliance report window (days)",
    ],
  },
]

export default function PartnerParameters() {
  return (
    <div>
      <PageHeader title="Partner Parameters" description="All configurable settings for partner onboarding" />
      <div className="grid gap-5 md:grid-cols-2">
        {PARTNER_GROUPS.map((group) => {
          const Icon = group.icon
          return (
            <Link
              key={group.path}
              to={group.path}
              className="group rounded-lg border border-border bg-card p-5 transition hover:border-primary/30 hover:shadow-sm"
            >
              <div className="flex items-start gap-4">
                <div className="flex h-10 w-10 flex-none items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Icon className="h-5 w-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <h2 className="text-base font-semibold">{group.label}</h2>
                    <ChevronRight className="h-4 w-4 text-muted-foreground transition group-hover:translate-x-0.5" />
                  </div>
                  <p className="mt-0.5 text-xs text-muted-foreground">{group.description}</p>
                  <ul className="mt-3 space-y-1">
                    {group.items.map((item) => (
                      <li key={item} className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span className="h-1 w-1 flex-none rounded-full bg-primary/40" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </Link>
          )
        })}
      </div>
    </div>
  )
}

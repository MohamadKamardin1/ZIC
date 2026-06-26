import { useState } from "react"
import { Link } from "react-router-dom"
import { Settings, Sliders, Users, UserCog, ShieldCheck, ChevronRight } from "lucide-react"

const SECTIONS = [
  {
    title: "General Parameters",
    description: "System-wide settings, application defaults, and global configuration",
    icon: Sliders,
    path: "/system-parameters/general",
    items: [
      "System name & branding",
      "Date & time formats",
      "Default language & locale",
      "Pagination defaults",
      "Notification settings",
    ],
  },
  {
    title: "Partner Parameters",
    description: "Workflow, choices, compliance rules, validation, and numbering for partner onboarding",
    icon: Users,
    path: "/system-parameters/partner",
    items: [
      "Workflow state machine & statuses",
      "Dropdown choice lists (ID types, titles, industries, etc.)",
      "Document upload rules (MIME types, size limits)",
      "Compliance risk weights & thresholds",
      "Required fields & age validation",
      "Number formats for applications & partners",
      "Scheduled task intervals",
    ],
  },
  {
    title: "User Parameters",
    description: "User account settings, session policies, and authentication rules",
    icon: UserCog,
    path: "/system-parameters/users",
    items: [
      "Password policies & complexity rules",
      "Session timeout duration",
      "2FA enforcement settings",
      "Account lockout thresholds",
      "User role & permission defaults",
    ],
  },
  {
    title: "Reinsurance Parameters",
    description: "Reinsurance treaties, limits, and cession rules",
    icon: ShieldCheck,
    path: "/system-parameters/reinsurance",
    items: [
      "Treaty types & limits",
      "Automatic cession percentages",
      "Facultative thresholds",
      "Reinsurer approval workflows",
      "Retention limits",
    ],
  },
]

export default function SystemParameters() {
  return (
    <div>
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Settings className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold">System Parameters</h1>
            <p className="text-sm text-muted-foreground">Configure all system settings</p>
          </div>
        </div>
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        {SECTIONS.map((section) => {
          const Icon = section.icon
          return (
            <Link
              key={section.path}
              to={section.path}
              className="group rounded-lg border border-border bg-card p-5 transition hover:border-primary/30 hover:shadow-sm"
            >
              <div className="flex items-start gap-4">
                <div className="flex h-10 w-10 flex-none items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Icon className="h-5 w-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <h2 className="text-base font-semibold">{section.title}</h2>
                    <ChevronRight className="h-4 w-4 text-muted-foreground transition group-hover:translate-x-0.5" />
                  </div>
                  <p className="mt-0.5 text-xs text-muted-foreground">{section.description}</p>
                  <ul className="mt-3 space-y-1">
                    {section.items.map((item) => (
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

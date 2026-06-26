import { useEffect, useState } from "react"
import { Loader2 } from "lucide-react"
import { PageHeader } from "./SharedComponents"
import { resolveGroupId } from "../../lib/api"
import ParameterCrud from "./ParameterCrud"

export default function PasswordPolicy() {
  const [groupId, setGroupId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    resolveGroupId("PASSWORD_POLICY")
      .then(setGroupId)
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12 text-muted-foreground">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
        Loading...
      </div>
    )
  }

  if (!groupId) {
    return (
      <div>
        <PageHeader title="Password Policy" description="Password complexity rules, expiry, history, and lockout settings" />
        <p className="text-sm text-muted-foreground">Parameter group not found. Run data migration.</p>
      </div>
    )
  }

  return (
    <div>
      <PageHeader title="Password Policy" description="Define password complexity requirements, expiration, history rules, and change notifications" />
      <ParameterCrud
        groupId={groupId}
        title="Password Policy Configuration"
        description="Configure minimum/maximum length, required character types (uppercase, lowercase, digits, special characters), expiry days, history count, minimum age, and change notifications. Enable REQUIRE_SPECIAL_CHAR and the password must include at least one character from the SPECIAL_CHARACTER_SET."
      />
    </div>
  )
}

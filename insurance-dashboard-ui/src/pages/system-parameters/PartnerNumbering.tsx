import { useEffect, useState } from "react"
import { Loader2 } from "lucide-react"
import { PageHeader } from "./SharedComponents"
import { resolveGroupId } from "../../lib/api"
import ParameterCrud from "./ParameterCrud"

export default function PartnerNumbering() {
  const [groupId, setGroupId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    resolveGroupId("PARTNER_NUMBERING")
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
        <PageHeader title="Numbering Formats" description="Application and partner number prefixes, formats, and sequences" />
        <p className="text-sm text-muted-foreground">Parameter group not found. Run data migration.</p>
      </div>
    )
  }

  return (
    <div>
      <PageHeader title="Numbering Formats" description="Application and partner number prefixes, formats, and sequences" />
      <ParameterCrud
        groupId={groupId}
        title="Number Format Configuration"
        description="Configure prefixes (INDIVIDUAL_APP_PREFIX, CORPORATE_APP_PREFIX, PARTNER_PREFIX), SEQUENCE_PADDING (integer), and INCLUDE_YEAR (boolean)."
      />
    </div>
  )
}

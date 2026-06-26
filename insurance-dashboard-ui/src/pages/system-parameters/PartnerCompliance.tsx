import { useEffect, useState } from "react"
import { Loader2 } from "lucide-react"
import { PageHeader } from "./SharedComponents"
import { resolveGroupId } from "../../lib/api"
import ParameterCrud from "./ParameterCrud"

export default function PartnerCompliance() {
  const [groupId, setGroupId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    resolveGroupId("PARTNER_COMPLIANCE")
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
        <PageHeader title="Compliance Rules" description="Risk scoring weights, thresholds, and high-risk industry flags" />
        <p className="text-sm text-muted-foreground">Parameter group not found. Run data migration.</p>
      </div>
    )
  }

  return (
    <div>
      <PageHeader title="Compliance Rules" description="Risk scoring weights, thresholds, and high-risk industry flags" />
      <ParameterCrud
        groupId={groupId}
        title="Compliance Configuration"
        description="Edit risk weights (JSON), high-risk thresholds (JSON), high-risk industries list (JSON), and bonus/incentive scores (integer)."
      />
    </div>
  )
}

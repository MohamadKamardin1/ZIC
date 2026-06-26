import { useEffect, useState } from "react"
import { Loader2 } from "lucide-react"
import { PageHeader } from "./SharedComponents"
import { resolveGroupId } from "../../lib/api"
import ParameterCrud from "./ParameterCrud"

export default function PartnerTypeDocuments() {
  const [groupId, setGroupId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    resolveGroupId("PARTNER_TYPE_CONFIG")
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
        <PageHeader title="Document Requirements" description="Required and optional document types per partner type" />
        <p className="text-sm text-muted-foreground">Parameter group not found. Run data migration.</p>
      </div>
    )
  }

  return (
    <div>
      <PageHeader title="Document Requirements per Partner Type" description="Configure which document types each partner type must provide, split by registration type (INDIVIDUAL / CORPORATE)" />
      <ParameterCrud
        groupId={groupId}
        title="Documents Configuration"
        description="Edit the DOCUMENTS_CONFIG JSON. Structure: { PARTNER_TYPE_CODE: { INDIVIDUAL|CORPORATE: { required: [...], optional: [...] } } }. Document type codes: NID, PASSPORT, TIN_CERTIFICATE, INCORPORATION_CERT, MEMORANDUM, BOARD_RESOLUTION, DRIVING_LICENSE, VOTER_ID, RESIDENT_PERMIT."
      />
    </div>
  )
}

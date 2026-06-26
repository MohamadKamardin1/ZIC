import { useEffect, useState } from "react"
import { Loader2 } from "lucide-react"
import { PageHeader } from "./SharedComponents"
import { resolveGroupId } from "../../lib/api"
import ParameterCrud from "./ParameterCrud"

export default function PartnerTypeContacts() {
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
        <PageHeader title="Contact Configuration" description="Contact types and fields per partner type" />
        <p className="text-sm text-muted-foreground">Parameter group not found. Run data migration.</p>
      </div>
    )
  }

  return (
    <div>
      <PageHeader title="Contact Configuration per Partner Type" description="Configure allowed contact types, required/optional contact fields, and min/max contacts for each partner type" />
      <ParameterCrud
        groupId={groupId}
        title="Contacts Configuration"
        description="Edit the CONTACTS_CONFIG JSON. Structure: { PARTNER_TYPE_CODE: { allowed_contact_types: [...], required_fields: [...], optional_fields: [...], min_contacts: N, max_contacts: N } }. Contact types: PRIMARY, SECONDARY, BILLING, TECHNICAL, OTHER."
      />
    </div>
  )
}

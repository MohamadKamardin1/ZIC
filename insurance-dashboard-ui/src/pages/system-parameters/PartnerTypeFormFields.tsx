import { useEffect, useState } from "react"
import { Loader2 } from "lucide-react"
import { PageHeader } from "./SharedComponents"
import { resolveGroupId } from "../../lib/api"
import ParameterCrud from "./ParameterCrud"

export default function PartnerTypeFormFields() {
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
        <PageHeader title="Form Fields" description="Attribution form fields per partner type" />
        <p className="text-sm text-muted-foreground">Parameter group not found. Run data migration.</p>
      </div>
    )
  }

  return (
    <div>
      <PageHeader title="Form Fields per Partner Type" description="Configure which attribution form fields are collected for each partner type and registration type" />
      <ParameterCrud
        groupId={groupId}
        title="Form Fields Configuration"
        description="Edit the FORM_FIELDS_CONFIG JSON. Structure: { PARTNER_TYPE_CODE: { INDIVIDUAL|CORPORATE: [field_name, ...] } }. Available fields include: first_name, surname, email, mobile_number, date_of_birth, nationality, company_name, tin_number, license_number, specialization, etc."
      />
    </div>
  )
}

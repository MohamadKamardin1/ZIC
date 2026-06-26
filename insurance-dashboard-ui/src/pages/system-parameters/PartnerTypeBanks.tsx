import { useEffect, useState } from "react"
import { Loader2 } from "lucide-react"
import { PageHeader } from "./SharedComponents"
import { resolveGroupId } from "../../lib/api"
import ParameterCrud from "./ParameterCrud"

export default function PartnerTypeBanks() {
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
        <PageHeader title="Bank Configuration" description="Bank account requirements per partner type" />
        <p className="text-sm text-muted-foreground">Parameter group not found. Run data migration.</p>
      </div>
    )
  }

  return (
    <div>
      <PageHeader title="Bank Configuration per Partner Type" description="Configure required/optional bank fields and min/max bank accounts for each partner type" />
      <ParameterCrud
        groupId={groupId}
        title="Banks Configuration"
        description="Edit the BANKS_CONFIG JSON. Structure: { PARTNER_TYPE_CODE: { required_fields: [...], optional_fields: [...], min_accounts: N, max_accounts: N } }. Bank fields: bank_name, branch_name, account_name, account_number, swift_code, iban."
      />
    </div>
  )
}

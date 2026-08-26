import { useMemo, useState } from "react"
import { ErrorCoach } from "../../components/commitments/ErrorCoach"
import { DateInput, FormGrid, SelectInput, TextInput, TextareaInput } from "../../components/ui/FormControls"
import { InfoBanner, Modal } from "../../components/ui/Overlays"
import { useToast } from "../../components/ui/Toast"
import { useCreatePolicyEndorsementMutation, usePolicyOptions } from "../../lib/policiesHooks"
import type { PolicyDetail, PolicyOption } from "../../lib/policies"

function today() {
  return new Date().toISOString().slice(0, 10)
}

function optionType(option: PolicyOption): string {
  return option.value.toUpperCase()
}

function isPremiumChange(type: string) {
  return type.includes("PREMIUM")
}

function isMemberAdd(type: string) {
  return type.includes("MEMBER") && type.includes("ADD")
}

export default function PolicyEndorsementModal({ open, policy, onClose }: { open: boolean; policy: PolicyDetail; onClose: () => void }) {
  const { toast } = useToast()
  const [endorsementType, setEndorsementType] = useState("")
  const [effectiveDate, setEffectiveDate] = useState(today())
  const [description, setDescription] = useState("")
  const [newPremium, setNewPremium] = useState("")
  const [memberName, setMemberName] = useState("")
  const [memberRelation, setMemberRelation] = useState("")
  const [errors, setErrors] = useState<Record<string, string>>({})
  const typeOptions = usePolicyOptions("endorsement_types", {}, open)
  const createEndorsement = useCreatePolicyEndorsementMutation()
  const selectedOption = useMemo(() => (typeOptions.data ?? []).find((option) => option.value === endorsementType), [endorsementType, typeOptions.data])
  const selectedType = optionType(selectedOption ?? { value: endorsementType, label: "" })
  const premiumChange = isPremiumChange(selectedType)
  const memberAdd = isMemberAdd(selectedType)
  const maxChangePercent = Number(selectedOption?.meta?.max_premium_change_percent ?? selectedOption?.meta?.max_change_percent)
  const currentPremium = Number(policy.premiumAmount)

  const close = () => {
    setErrors({})
    createEndorsement.reset()
    onClose()
  }

  const submit = () => {
    const nextErrors: Record<string, string> = {}
    if (!endorsementType) nextErrors.endorsement_type = "Choose the type of policy change to apply."
    if (!effectiveDate) nextErrors.effective_date = "Choose when the endorsement should take effect."
    if (!description.trim()) nextErrors.description = "Explain why this endorsement is being requested."
    if (premiumChange) {
      const amount = Number(newPremium)
      if (!newPremium || !Number.isFinite(amount) || amount <= 0) nextErrors.new_premium_amount = "Enter a new premium amount greater than zero."
      else if (Number.isFinite(maxChangePercent) && currentPremium > 0 && Math.abs(amount - currentPremium) / currentPremium * 100 > maxChangePercent) nextErrors.new_premium_amount = `The premium change cannot exceed ${maxChangePercent}% for this policy. Enter an amount within the configured limit.`
    }
    if (memberAdd) {
      if (!memberName.trim()) nextErrors.member_name = "Enter the covered member’s full name."
      if (!memberRelation.trim()) nextErrors.member_relation = "Enter the member relationship."
    }
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) return

    const changes: Record<string, unknown> = {}
    if (premiumChange) changes.new_premium_amount = newPremium
    if (memberAdd) {
      changes.member_name = memberName.trim()
      changes.member_relation = memberRelation.trim()
    }
    createEndorsement.mutate({ id: policy.id, payload: { endorsement_type: endorsementType, effective_date: effectiveDate, description: description.trim(), changes } }, {
      onSuccess: () => {
        toast({ title: "Endorsement submitted", message: "The request was appended to the policy history for review.", tone: "success" })
        close()
      },
    })
  }

  return <Modal open={open} title="Create endorsement" description="Add a pending policy change without overwriting the issued contract history." onClose={close} size="lg" footer={<><button type="button" className="button-secondary" onClick={close} disabled={createEndorsement.isPending}>Cancel</button><button type="button" className="button-primary" onClick={submit} disabled={createEndorsement.isPending}>{createEndorsement.isPending ? "Submitting…" : "Submit endorsement"}</button></>}>
    <div className="space-y-4">
      <InfoBanner title="Append-only policy history">An endorsement creates a new before/after record. The existing issued snapshot remains preserved.</InfoBanner>
      {createEndorsement.error ? <ErrorCoach error={createEndorsement.error} title="Endorsement could not be submitted" compact onRetry={submit} /> : null}
      <FormGrid columns={2}>
        <SelectInput label="Endorsement type" name="endorsement_type" required value={endorsementType} error={errors.endorsement_type} onChange={(event) => { setEndorsementType(event.target.value); setErrors((current) => ({ ...current, endorsement_type: "" })) }}>
          <option value="">Select endorsement type</option>
          {(typeOptions.data ?? []).map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
        </SelectInput>
        <DateInput label="Effective date" name="effective_date" required value={effectiveDate} error={errors.effective_date} onChange={(event) => setEffectiveDate(event.target.value)} />
      </FormGrid>
      {typeOptions.isError ? <ErrorCoach error={typeOptions.error} title="Endorsement types could not be loaded" compact onRetry={() => void typeOptions.refetch()} /> : null}
      {premiumChange && <TextInput label="New premium amount" name="new_premium_amount" type="number" min="0" step="0.01" required value={newPremium} hint={Number.isFinite(maxChangePercent) ? `Configured maximum change: ${maxChangePercent}%` : "Validated against the product setup when submitted"} error={errors.new_premium_amount} onChange={(event) => setNewPremium(event.target.value)} />}
      {memberAdd && <FormGrid columns={2}><TextInput label="Member name" name="member_name" required value={memberName} error={errors.member_name} onChange={(event) => setMemberName(event.target.value)} /><TextInput label="Member relation" name="member_relation" required value={memberRelation} error={errors.member_relation} onChange={(event) => setMemberRelation(event.target.value)} /></FormGrid>}
      <TextareaInput label="Reason / description" name="description" required value={description} error={errors.description} hint="Give the reviewer enough context to approve or reject the change." onChange={(event) => setDescription(event.target.value)} placeholder="Describe the requested policy change" />
    </div>
  </Modal>
}

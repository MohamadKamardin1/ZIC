/**
 * OL Beneficiaries — management tab over the beneficiaries endpoints.
 *
 * Share math is always visible: the panel header shows a live
 * ShareTotalIndicator over the saved rows, and the add/edit form shows one
 * over the projected set. Client-side rules mirror the backend exactly so the
 * operator learns the same lesson before submitting: shares must total 100%,
 * at least one beneficiary must be primary, and minors need a guardian.
 */

import { useEffect, useMemo, useState } from "react"
import { Pencil, Plus, Star, Trash2 } from "lucide-react"
import { ErrorCoach } from "../../components/commitments/ErrorCoach"
import { ConfirmModal, Modal } from "../../components/ui/Overlays"
import { DecimalInput, FormGrid, TextInput, Toggle } from "../../components/ui/FormControls"
import { SmartSelect } from "../../components/ui/SmartSelect"
import { type BeneficiaryRecord, type ProposalDetail } from "../../lib/proposals"
import { ApiClientError } from "../../lib/apiClient"
import {
  useAddBeneficiaryMutation,
  useDeleteBeneficiaryMutation,
  useUpdateBeneficiaryMutation,
} from "../../lib/proposalsHooks"
import { useToast } from "../../components/ui/Toast"
import { ShareTotalIndicator, shareTotal } from "../../components/proposals/ShareTotalIndicator"

const IDENTITY_TYPES_URL = "/api/v1/ol/options/identity-types/"

interface FormState {
  personName: string
  identityType: string
  identityNumber: string
  beneficialType: string
  sharePercent: string
  isPrimary: boolean
  isMinor: boolean
  guardianName: string
  guardianIdentityType: string
  guardianIdentityNumber: string
  guardianRelationship: string
}

function emptyForm(): FormState {
  return {
    personName: "",
    identityType: "",
    identityNumber: "",
    beneficialType: "",
    sharePercent: "",
    isPrimary: false,
    isMinor: false,
    guardianName: "",
    guardianIdentityType: "",
    guardianIdentityNumber: "",
    guardianRelationship: "",
  }
}

function formFromRecord(record: BeneficiaryRecord): FormState {
  return {
    personName: record.personName === "—" ? "" : record.personName,
    identityType: record.identityType ?? "",
    identityNumber: record.identityNumber ?? "",
    beneficialType: "",
    sharePercent: String(record.sharePercent ?? ""),
    isPrimary: Boolean(record.isPrimary),
    isMinor: Boolean(record.isMinor),
    guardianName: record.guardianName ?? "",
    guardianIdentityType: "",
    guardianIdentityNumber: "",
    guardianRelationship: record.guardianRelationship ?? "",
  }
}

/** Exact fix steps mirrored from the backend error factory. */
const SHARE_STEPS = [
  "Adjust each beneficiary share so the total is exactly 100%.",
  "Mark one beneficiary as primary.",
]
const PRIMARY_STEPS = ["Mark one beneficiary as primary."]
const GUARDIAN_STEPS = ["Record the guardian name and relationship."]

export interface OLBeneficiariesPanelProps {
  detail: ProposalDetail
  canEnrich: boolean
}

export function OLBeneficiariesPanel({ detail, canEnrich }: OLBeneficiariesPanelProps) {
  const { toast } = useToast()
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<BeneficiaryRecord | null>(null)
  const [removing, setRemoving] = useState<BeneficiaryRecord | null>(null)
  const [error, setError] = useState<unknown>(null)

  const remove = useDeleteBeneficiaryMutation()

  const beneficiaries = detail.beneficiaries

  const openAdd = () => {
    setEditing(null)
    setError(null)
    setModalOpen(true)
  }

  const openEdit = (record: BeneficiaryRecord) => {
    setEditing(record)
    setError(null)
    setModalOpen(true)
  }

  const confirmRemove = () => {
    if (!removing) return
    setError(null)
    remove.mutate(
      { id: String(detail.id), beneficiaryId: removing.id },
      {
        onSuccess: () => {
          toast({
            title: "Beneficiary removed",
            message: `${removing.personName} was removed. Check that the remaining shares still total 100%.`,
            tone: "success",
          })
          setRemoving(null)
        },
        onError: (mutationError) => setError(mutationError),
      },
    )
  }

  return (
    <div className="space-y-4" data-testid="tab-beneficiaries">
      <section className="surface-card p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-bold">Beneficiaries</h2>
          <ShareTotalIndicator shares={beneficiaries.map((row) => row.sharePercent)} />
        </div>
        {beneficiaries.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm" data-testid="beneficiaries-table">
              <thead>
                <tr className="border-b text-xs font-bold uppercase tracking-wide text-[var(--muted-foreground)]">
                  <th className="py-2 pr-3">Name</th>
                  <th className="py-2 pr-3">Identity</th>
                  <th className="py-2 pr-3">Beneficial type</th>
                  <th className="py-2 pr-3 text-right">Share</th>
                  <th className="py-2 pr-3">Primary</th>
                  <th className="py-2 pr-3">Minor</th>
                  {canEnrich && <th className="py-2 text-right">Actions</th>}
                </tr>
              </thead>
              <tbody>
                {beneficiaries.map((row) => (
                  <tr key={row.id || row.personName} data-testid="beneficiary-row" className="border-b last:border-0">
                    <td className="py-2 pr-3 font-semibold">{row.personName}</td>
                    <td className="py-2 pr-3 text-[var(--muted-foreground)]">
                      {[row.identityType, row.identityNumber].filter(Boolean).join(" · ") || "—"}
                    </td>
                    <td className="py-2 pr-3">
                      {row.beneficialTypeName ? (
                        <span className="rounded-full bg-[var(--secondary)] px-2 py-0.5 text-xs font-bold">{row.beneficialTypeName}</span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="py-2 pr-3 text-right font-bold tabular-nums">{Number(row.sharePercent).toFixed(2)}%</td>
                    <td className="py-2 pr-3" aria-label={row.isPrimary ? "Primary beneficiary" : "Not primary"}>
                      {row.isPrimary ? (
                        <Star size={15} aria-label="Primary star" className="fill-[var(--warning)] text-[var(--warning)]" />
                      ) : (
                        <span className="text-[var(--muted-foreground)]">—</span>
                      )}
                    </td>
                    <td className="py-2 pr-3">
                      {row.isMinor ? (
                        <span className="text-xs font-semibold" title={[row.guardianName, row.guardianRelationship].filter(Boolean).join(" · ")}>
                          Minor{row.guardianName ? ` · Guardian: ${row.guardianName}` : " · No guardian recorded"}
                        </span>
                      ) : (
                        <span className="text-[var(--muted-foreground)]">—</span>
                      )}
                    </td>
                    {canEnrich && (
                      <td className="py-2 text-right">
                        <span className="inline-flex justify-end gap-1">
                          <button type="button" className="button-secondary !px-2 !py-1" aria-label={`Edit ${row.personName}`} onClick={() => openEdit(row)}>
                            <Pencil size={14} aria-hidden="true" />
                          </button>
                          <button type="button" className="button-secondary !px-2 !py-1" aria-label={`Remove ${row.personName}`} onClick={() => setRemoving(row)}>
                            <Trash2 size={14} aria-hidden="true" />
                          </button>
                        </span>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-[var(--muted-foreground)]">
            No beneficiaries recorded yet. Add at least one primary beneficiary whose shares total exactly 100%.
          </p>
        )}

        {canEnrich && (
          <div className="mt-4 flex justify-end">
            <button type="button" className="button-primary" data-testid="add-beneficiary" onClick={openAdd}>
              <Plus size={15} aria-hidden="true" />
              Add beneficiary
            </button>
          </div>
        )}

        {Boolean(error) && (
          <div className="mt-4">
            <ErrorCoach error={error} title="The beneficiary could not be removed" compact onRetry={() => setError(null)} />
          </div>
        )}
      </section>

      <OLBeneficiaryFormModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        detail={detail}
        editing={editing}
      />

      <ConfirmModal
        open={Boolean(removing)}
        title={`Remove ${removing?.personName ?? "beneficiary"}?`}
        description={`This removes ${removing?.personName ?? "the beneficiary"} and their share from the proposal. The remaining shares must still total 100% with at least one primary beneficiary.`}
        confirmLabel="Remove"
        onClose={() => setRemoving(null)}
        onConfirm={confirmRemove}
      />
    </div>
  )
}

export interface OLBeneficiaryFormModalProps {
  open: boolean
  onClose: () => void
  detail: ProposalDetail
  editing: BeneficiaryRecord | null
}

export function OLBeneficiaryFormModal({ open, onClose, detail, editing }: OLBeneficiaryFormModalProps) {
  const { toast } = useToast()
  const add = useAddBeneficiaryMutation()
  const update = useUpdateBeneficiaryMutation()

  const [form, setForm] = useState<FormState>(emptyForm())
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [coachError, setCoachError] = useState<ApiClientError | null>(null)

  useEffect(() => {
    if (!open) return
    setForm(editing ? formFromRecord(editing) : emptyForm())
    setFieldErrors({})
    setCoachError(null)
    add.reset()
    update.reset()
  }, [open, editing])

  const set = (patch: Partial<FormState>) => setForm((current) => ({ ...current, ...patch }))

  /** Shares of the OTHER saved rows — the live indicator projects this row on top. */
  const contextShares = useMemo(
    () => detail.beneficiaries.filter((row) => row.id !== editing?.id).map((row) => row.sharePercent),
    [detail.beneficiaries, editing],
  )

  const liveShare = Number.parseFloat(form.sharePercent) || 0
  const projectedShares = [...contextShares, liveShare]
  const projectedTotal = projectedShares.reduce((sum, value) => sum + value, 0)

  const mutationPending = add.isPending || update.isPending

  const buildPayload = (): Record<string, unknown> => ({
    person_name: form.personName.trim(),
    identity_type: form.identityType,
    identity_number: form.identityNumber.trim(),
    ...(form.beneficialType ? { beneficial_type: form.beneficialType } : {}),
    share_percent: String(liveShare),
    is_primary: form.isPrimary,
    is_minor: form.isMinor,
    guardian_name: form.guardianName.trim(),
    guardian_identity_type: form.guardianIdentityType,
    guardian_identity_number: form.guardianIdentityNumber.trim(),
    guardian_relationship: form.guardianRelationship.trim(),
  })

  const submit = () => {
    setCoachError(null)
    const errors: Record<string, string> = {}
    if (!form.personName.trim()) errors.personName = "Full name is required."
    if (!form.identityType) errors.identityType = "Choose an identity document type."
    if (!form.identityNumber.trim()) errors.identityNumber = "Identity number is required."

    const duplicate = detail.beneficiaries.some(
      (row) =>
        row.id !== editing?.id &&
        row.identityNumber &&
        row.identityNumber.toUpperCase() === form.identityNumber.trim().toUpperCase() &&
        (row.identityType ?? "").toUpperCase() === form.identityType.toUpperCase(),
    )
    if (duplicate) errors.identityNumber = `A beneficiary with this ${form.identityType} number already exists on this proposal.`

    if (shareTotal(projectedTotal) !== "valid") {
      setCoachError(
        new ApiClientError({
          status: 422,
          code: "PROPOSAL_BENEFICIARY_SHARES_INVALID",
          message: `Beneficiary shares must total 100%, currently ${projectedTotal.toFixed(2)}%.`,
          fieldErrors: {},
          details: { resolution_steps: SHARE_STEPS },
        }),
      )
      setFieldErrors(errors)
      return
    }
    if (form.isMinor && !form.guardianName.trim()) {
      errors.guardianName = "A guardian is required for a minor beneficiary."
      setFieldErrors(errors)
      return
    }
    const noPrimaryRemains = !form.isPrimary && !detail.beneficiaries.some((row) => row.id !== editing?.id && row.isPrimary)
    if (noPrimaryRemains) {
      setCoachError(
        new ApiClientError({
          status: 422,
          code: "PROPOSAL_BENEFICIARY_SHARES_INVALID",
          message: "At least one beneficiary must be marked as primary.",
          fieldErrors: {},
          details: { resolution_steps: PRIMARY_STEPS },
        }),
      )
      setFieldErrors(errors)
      return
    }
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors)
      return
    }

    const payload = buildPayload()
    const onSuccess = () => {
      toast({
        title: editing ? "Beneficiary updated" : "Beneficiary added",
        message: `${form.personName.trim()} now holds ${liveShare.toFixed(2)}% of this proposal.`,
        tone: "success",
      })
      onClose()
    }
    const onError = (mutationError: unknown) => setCoachError(toApiClientError(mutationError))

    if (editing) update.mutate({ id: String(detail.id), beneficiaryId: editing.id, data: payload }, { onSuccess, onError })
    else add.mutate({ id: String(detail.id), data: payload }, { onSuccess, onError })
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="lg"
      title={editing ? `Edit beneficiary · ${editing.personName}` : "Add beneficiary"}
      description="Shares across all beneficiaries must total exactly 100%, one beneficiary must be primary, and minors require a guardian."
    >
      <div className="space-y-5" data-testid="beneficiary-form">
        <FormGrid columns={2}>
          <TextInput
            label="Full name"
            name="beneficiary_person_name"
            required
            value={form.personName}
            error={fieldErrors.personName}
            onChange={(event) => set({ personName: event.target.value })}
          />
          <DecimalInput
            label="Share percent"
            name="beneficiary_share_percent"
            required
            inputMode="decimal"
            value={form.sharePercent}
            onChange={(event) => set({ sharePercent: event.target.value })}
            hint="e.g. 40 or 33.33"
          />
          <SmartSelect
            entity="identity-types"
            label="Identity type"
            name="beneficiary_identity_type"
            value={form.identityType}
            error={fieldErrors.identityType}
            rememberLastUsed={false}
            onChange={(value) => set({ identityType: value })}
            placeholder="Select identity type"
          />
          <TextInput
            label="Identity number"
            name="beneficiary_identity_number"
            required
            value={form.identityNumber}
            error={fieldErrors.identityNumber}
            onChange={(event) => set({ identityNumber: event.target.value })}
          />
          <SmartSelect
            entity="benefit-types"
            label="Beneficial type"
            name="beneficiary_beneficial_type"
            rememberLastUsed={false}
            value={form.beneficialType}
            onChange={(value) => set({ beneficialType: value })}
            placeholder="Select beneficial type"
            className="sm:col-span-2"
          />
        </FormGrid>

        <div className="grid gap-3 sm:grid-cols-2">
          <Toggle
            label="Primary beneficiary"
            checked={form.isPrimary}
            onChange={(checked) => set({ isPrimary: checked })}
            hint="At least one beneficiary must be primary."
          />
          <Toggle
            label="Minor (under 18)"
            checked={form.isMinor}
            onChange={(checked) => set({ isMinor: checked })}
            hint="Minors require a named guardian."
          />
        </div>

        {form.isMinor && (
          <div className="rounded-md border bg-[var(--muted)]/30 p-3" data-testid="guardian-fields">
            <p className="mb-3 text-xs font-bold uppercase tracking-[0.08em] text-[var(--muted-foreground)]">Guardian details</p>
            <FormGrid columns={2}>
              <TextInput
                label="Guardian full name"
                name="guardian_person_name"
                required
                value={form.guardianName}
                error={fieldErrors.guardianName}
                onChange={(event) => set({ guardianName: event.target.value })}
              />
              <TextInput
                label="Guardian relationship"
                name="guardian_relationship"
                value={form.guardianRelationship}
                onChange={(event) => set({ guardianRelationship: event.target.value })}
                placeholder="e.g. Mother"
              />
              <SmartSelect
                entity="identity-types"
                label="Guardian identity type"
                name="guardian_identity_type"
                rememberLastUsed={false}
                value={form.guardianIdentityType}
                onChange={(value) => set({ guardianIdentityType: value })}
                placeholder="Select identity type"
              />
              <TextInput
                label="Guardian identity number"
                name="guardian_identity_number"
                value={form.guardianIdentityNumber}
                onChange={(event) => set({ guardianIdentityNumber: event.target.value })}
              />
            </FormGrid>
          </div>
        )}

        {/* Live share math for the projected beneficiary set. */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-t pt-3">
          <ShareTotalIndicator shares={projectedShares} />
          <span className="text-xs font-semibold text-[var(--muted-foreground)]" data-testid="projected-share-note">
            {editing ? `Replaces current ${Number(editing.sharePercent).toFixed(2)}% share` : `Existing beneficiaries hold ${contextShares.reduce((sum, value) => sum + value, 0).toFixed(2)}%`}
          </span>
        </div>

        {coachError && (
          <ErrorCoach
            error={coachError}
            title={
              coachError.code === "PROPOSAL_BENEFICIARY_GUARDIAN_REQUIRED"
                ? "Guardian details are missing"
                : coachError.code === "PROPOSAL_DUPLICATE_BENEFICIARY"
                  ? "Duplicate beneficiary identity"
                  : "Beneficiary shares are invalid"
            }
            compact
            onRetry={() => setCoachError(null)}
          />
        )}

        <div className="flex justify-end gap-2">
          <button type="button" className="button-secondary" onClick={onClose} disabled={mutationPending}>
            Cancel
          </button>
          <button type="button" className="button-primary" data-testid="save-beneficiary" disabled={mutationPending} onClick={submit}>
            {mutationPending ? "Saving…" : editing ? "Save changes" : "Add beneficiary"}
          </button>
        </div>
      </div>
    </Modal>
  )
}

function toApiClientError(error: unknown): ApiClientError {
  if (error instanceof ApiClientError) return error
  const message = error instanceof Error ? error.message : "The beneficiary could not be saved."
  return new ApiClientError({ status: 0, code: "BENEFICIARY_SAVE_FAILED", message, fieldErrors: {}, details: {} })
}

export { GUARDIAN_STEPS, PRIMARY_STEPS, SHARE_STEPS }

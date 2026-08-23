/**
 * OL Enrichment Modal — sectioned workspace over PATCH /enrich/.
 *
 * Four sections (Employer, Intermediary, Declarations, Bank details), each
 * with its own Save and Clear actions hitting the shared endpoint. The bank
 * account number arrives masked from the API, so it is only included in a
 * save payload when the operator types a replacement value. Errors render
 * through ErrorCoach; payloads carry names — never UUIDs.
 */

import { useEffect, useState } from "react"
import { ErrorCoach } from "../../components/commitments/ErrorCoach"
import { Modal } from "../../components/ui/Overlays"
import { FormGrid, ReadOnlyField, SelectInput, TextareaInput, TextInput } from "../../components/ui/FormControls"
import { SmartSelect } from "../../components/ui/SmartSelect"
import { type ProposalDetail } from "../../lib/proposals"
import { ApiClientError } from "../../lib/apiClient"
import { useEnrichSectionMutation } from "../../lib/proposalsHooks"
import { useToast } from "../../components/ui/Toast"

const OPTIONS_BASE = "/api/v1/ol-proposals/options"

function ChoiceSelect({ label, name, value, options, required, error, onChange, placeholder = "Select an option" }: { label: string; name: string; value: string; options: Array<{ value: string; label: string }>; required?: boolean; error?: string; onChange: (value: string) => void; placeholder?: string }) {
  return (
    <SelectInput label={label} name={name} required={required} error={error} value={value} onChange={(event) => onChange(event.target.value)}>
      <option value="">{placeholder}</option>
      {options.map((option) => (
        <option key={option.value} value={option.value}>{option.label}</option>
      ))}
    </SelectInput>
  )
}

const SECTION_LABELS: Record<SectionKey, string> = {
  employer: "Employer details",
  intermediary: "Intermediary details",
  declarations: "Declarations",
  bank_details: "Bank details",
}

const YES_NO = [
  { value: "yes", label: "Yes" },
  { value: "no", label: "No" },
]

function triToChoice(value: boolean | null | undefined): string {
  if (value === true) return "yes"
  if (value === false) return "no"
  return ""
}

function choiceToTri(value: string): boolean | null {
  if (value === "yes") return true
  if (value === "no") return false
  return null
}

type SectionKey = "employer" | "intermediary" | "declarations" | "bank_details"

interface SectionProps {
  detail: ProposalDetail
  onSave: (section: string, data: Record<string, unknown>, label: string) => void
  onClear: (section: SectionKey, data: Record<string, unknown>) => void
}

function EmployerSection({ detail, onSave, onClear }: SectionProps) {
  const [employerPartnerId, setEmployerPartnerId] = useState(detail.employerPartnerId ?? "")
  const [employmentReference, setEmploymentReference] = useState(detail.employmentReference ?? "")
  const [payrollDeduction, setPayrollDeduction] = useState(triToChoice(detail.payrollDeduction))

  return (
    <div className="space-y-4" data-testid="enrich-section-employer">
      <FormGrid columns={2}>
        <SmartSelect
          entity="employers"
          label="Employer (corporate partner)"
          name="enrich_employer_partner"
          optionsUrl={`${OPTIONS_BASE}/employers/`}
          rememberLastUsed={false}
          value={employerPartnerId}
          onChange={setEmployerPartnerId}
          placeholder={detail.employerName && detail.employerName !== "-" ? `Current: ${detail.employerName}` : "Select employer"}
        />
        <TextInput
          label="Employment reference"
          name="enrich_employment_reference"
          value={employmentReference}
          onChange={(event) => setEmploymentReference(event.target.value)}
          placeholder="e.g. Payroll number or staff ID"
        />
        <ChoiceSelect
          label="Payroll deduction"
          name="enrich_payroll_deduction"
          options={YES_NO}
          value={payrollDeduction}
          onChange={setPayrollDeduction}
          placeholder="Not declared"
        />
      </FormGrid>
      <div className="flex flex-wrap justify-end gap-2">
        <button
          type="button"
          className="button-secondary"
          data-testid="enrich-clear-employer"
          onClick={() =>
            onClear("employer", { employer_partner: null, employment_reference: "", payroll_deduction: false })
          }
        >
          Clear section
        </button>
        <button
          type="button"
          className="button-primary"
          data-testid="enrich-save-employer"
          onClick={() => {
            const payload: Record<string, unknown> = {
              employer_partner: employerPartnerId || null,
              employment_reference: employmentReference.trim(),
              payroll_deduction: payrollDeduction === "yes",
            }
            onSave("employer", payload, "Employer details")
          }}
        >
          Save employer
        </button>
      </div>
    </div>
  )
}

function IntermediarySection({ detail, onSave, onClear }: SectionProps) {
  const [agentPartnerId, setAgentPartnerId] = useState(detail.agentPartnerId ?? "")

  return (
    <div className="space-y-4" data-testid="enrich-section-intermediary">
      <FormGrid columns={2}>
        <SmartSelect
          entity="intermediaries"
          label="Intermediary / agent partner"
          name="enrich_agent_partner"
          optionsUrl={`${OPTIONS_BASE}/intermediaries/`}
          rememberLastUsed={false}
          createPermission="partners.create"
          value={agentPartnerId}
          onChange={setAgentPartnerId}
          placeholder={detail.agentName ? `Current: ${detail.agentName}` : "Select intermediary"}
        />
        <ReadOnlyField
          label="Distribution channel"
          value={detail.intermediaryChannel || "—"}
          hint="Channel is carried from the source quotation and cannot be edited here."
        />
      </FormGrid>
      <div className="flex flex-wrap justify-end gap-2">
        <button
          type="button"
          className="button-secondary"
          data-testid="enrich-clear-intermediary"
          onClick={() => onClear("intermediary", { agent_partner: null })}
        >
          Clear section
        </button>
        <button
          type="button"
          className="button-primary"
          data-testid="enrich-save-intermediary"
          onClick={() => onSave("intermediary", { agent_partner: agentPartnerId || null }, "Intermediary details")}
        >
          Save intermediary
        </button>
      </div>
    </div>
  )
}

function DeclarationsSection({ detail, onSave, onClear }: SectionProps) {
  const [pep, setPep] = useState(triToChoice(detail.declarationPep))
  const [aml, setAml] = useState(triToChoice(detail.declarationAml))
  const [existingPolicies, setExistingPolicies] = useState(
    detail.existingPoliciesCount === null || detail.existingPoliciesCount === undefined ? "" : String(detail.existingPoliciesCount),
  )
  const [occupationNote, setOccupationNote] = useState(detail.occupationRiskNote ?? "")

  let freeTextInitial = "{}"
  if (detail.declarationsFreeText) {
    try {
      freeTextInitial = JSON.stringify(JSON.parse(detail.declarationsFreeText), null, 2)
    } catch {
      freeTextInitial = detail.declarationsFreeText
    }
  }
  const [freeText, setFreeText] = useState(freeTextInitial)

  const buildPayload = (): Record<string, unknown> | { error: string } => {
    let parsed: unknown = {}
    if (freeText.trim()) {
      try {
        parsed = JSON.parse(freeText)
      } catch {
        return { error: "Declarations note must be valid JSON." }
      }
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        return { error: "Declarations note must be a JSON object." }
      }
    }
    const policiesRaw = existingPolicies.trim()
    return {
      declaration_pep_flag: choiceToTri(pep),
      declaration_aml_flag: choiceToTri(aml),
      existing_policies_count: policiesRaw === "" ? null : Number(policiesRaw),
      occupation_risk_note: occupationNote,
      declarations_free_text: parsed,
    }
  }

  return (
    <div className="space-y-4" data-testid="enrich-section-declarations">
      <FormGrid columns={2}>
        <ChoiceSelect label="PEP declaration" name="enrich_declaration_pep" options={YES_NO} value={pep} onChange={setPep} placeholder="Not declared" />
        <ChoiceSelect label="AML declaration" name="enrich_declaration_aml" options={YES_NO} value={aml} onChange={setAml} placeholder="Not declared" />
        <TextInput
          label="Existing policies count"
          name="enrich_existing_policies"
          inputMode="numeric"
          value={existingPolicies}
          onChange={(event) => setExistingPolicies(event.target.value)}
        />
        <TextInput
          label="Occupation risk note"
          name="enrich_occupation_note"
          value={occupationNote}
          onChange={(event) => setOccupationNote(event.target.value)}
        />
      </FormGrid>
      <TextareaInput
        label="Declarations note (JSON)"
        name="enrich_declarations_free_text"
        rows={4}
        value={freeText}
        onChange={(event) => setFreeText(event.target.value)}
        hint='Free-form JSON object, e.g. {"smoker": false}'
      />
      <div className="flex flex-wrap justify-end gap-2">
        <button
          type="button"
          className="button-secondary"
          data-testid="enrich-clear-declarations"
          onClick={() =>
            onClear("declarations", {
              declaration_pep_flag: null,
              declaration_aml_flag: null,
              existing_policies_count: null,
              occupation_risk_note: "",
              declarations_free_text: {},
            })
          }
        >
          Clear section
        </button>
        <button
          type="button"
          className="button-primary"
          data-testid="enrich-save-declarations"
          onClick={() => {
            const payload = buildPayload()
            if ("error" in payload) {
              onSave("__invalid__", { validationMessage: payload.error }, "Declarations")
              return
            }
            onSave("declarations", payload, "Declarations")
          }}
        >
          Save declarations
        </button>
      </div>
    </div>
  )
}

function BankSection({ detail, onSave, onClear }: SectionProps) {
  const [bankName, setBankName] = useState(detail.bankName ?? "")
  const [accountName, setAccountName] = useState(detail.bankAccountName ?? "")
  const [accountNumber, setAccountNumber] = useState("")
  const accountNumberDirty = accountNumber.trim().length > 0

  return (
    <div className="space-y-4" data-testid="enrich-section-bank">
      <FormGrid columns={2}>
        <SmartSelect
          entity="banks"
          label="Bank"
          name="enrich_bank_name"
          optionsUrl={`${OPTIONS_BASE}/banks/`}
          rememberLastUsed={false}
          value={bankName}
          onChange={setBankName}
          placeholder={detail.bankName ? `Current: ${detail.bankName}` : "Select bank"}
        />
        <TextInput
          label="Account name"
          name="enrich_bank_account_name"
          value={accountName}
          onChange={(event) => setAccountName(event.target.value)}
        />
        <TextInput
          label="Account number"
          name="enrich_bank_account_number"
          value={accountNumber}
          onChange={(event) => setAccountNumber(event.target.value)}
          placeholder={detail.bankAccountNumberMasked || "Enter new account number"}
          hint="Stored masked — type only to replace the existing number."
        />
      </FormGrid>
      <div className="flex flex-wrap justify-end gap-2">
        <button
          type="button"
          className="button-secondary"
          data-testid="enrich-clear-bank_details"
          onClick={() => onClear("bank_details", { bank_name: "", bank_account_name: "", bank_account_number: "" })}
        >
          Clear section
        </button>
        <button
          type="button"
          className="button-primary"
          data-testid="enrich-save-bank_details"
          onClick={() => {
            const payload: Record<string, unknown> = { bank_name: bankName, bank_account_name: accountName }
            if (accountNumberDirty) payload.bank_account_number = accountNumber.trim()
            onSave("bank_details", payload, "Bank details")
          }}
        >
          Save bank details
        </button>
      </div>
    </div>
  )
}

export interface OLEnrichmentModalProps {
  open: boolean
  onClose: () => void
  detail: ProposalDetail
}

export default function OLEnrichmentModal({ open, onClose, detail }: OLEnrichmentModalProps) {
  const { toast } = useToast()
  const enrich = useEnrichSectionMutation()
  const [error, setError] = useState<Error | null>(null)
  const [validationMessage, setValidationMessage] = useState<string | null>(null)

  useEffect(() => {
    if (open) {
      setError(null)
      setValidationMessage(null)
      enrich.reset()
    }
  }, [open, detail.id])

  const submit = (section: SectionKey, data: Record<string, unknown>, label: string) => {
    setError(null)
    setValidationMessage(null)
    enrich.mutate(
      { id: String(detail.id), section, data },
      {
        onSuccess: () => {
          toast({ title: `${label} saved`, message: `The ${label.toLowerCase()} section was applied to this proposal.`, tone: "success" })
        },
        onError: (mutationError) => setError(mutationError),
      },
    )
  }

  const clearSection = (section: SectionKey, data: Record<string, unknown>) => {
    submit(section, data, SECTION_LABELS[section])
  }

  const handleSave = (section: string, data: Record<string, unknown>, label: string) => {
    if (section === "__invalid__") {
      setValidationMessage(String(data.validationMessage))
      return
    }
    submit(section as SectionKey, data, label)
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="lg"
      title={`Enrich proposal · ${detail.proposalNumber}`}
      description="Complete each section and save. Sections are independent — saving one does not affect the others."
    >
      <div className="space-y-6" data-testid="enrichment-workspace">
        <section className="surface-card p-4">
          <h3 className="mb-3 font-bold">Employer</h3>
          <EmployerSection detail={detail} onSave={handleSave} onClear={clearSection} />
        </section>

        <section className="surface-card p-4">
          <h3 className="mb-3 font-bold">Intermediary</h3>
          <IntermediarySection detail={detail} onSave={handleSave} onClear={clearSection} />
        </section>

        <section className="surface-card p-4">
          <h3 className="mb-3 font-bold">Declarations</h3>
          {validationMessage && (
            <p className="mb-3 text-sm font-semibold text-[var(--destructive)]" role="alert" data-testid="enrich-validation-error">
              {validationMessage}
            </p>
          )}
          <DeclarationsSection detail={detail} onSave={handleSave} onClear={clearSection} />
        </section>

        <section className="surface-card p-4">
          <h3 className="mb-3 font-bold">Bank details</h3>
          <BankSection detail={detail} onSave={handleSave} onClear={clearSection} />
        </section>

        {error && (
          <ErrorCoach
            error={error}
            title={
              error instanceof ApiClientError && error.code === "VALIDATION_ERROR"
                ? "Some fields were rejected"
                : "The enrichment change could not be saved"
            }
            compact
            onRetry={() => {
              setError(null)
              enrich.reset()
            }}
          />
        )}

        {enrich.isPending && (
          <p className="text-right text-xs font-semibold text-[var(--muted-foreground)]" role="status">
            Saving…
          </p>
        )}
      </div>
    </Modal>
  )
}

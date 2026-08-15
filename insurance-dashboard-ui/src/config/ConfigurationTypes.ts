export interface ChoiceOption {
  value: string
  label: string
  description?: string
  metadata?: Record<string, unknown> | null
}

export interface ChoicesResponse {
  partnerTypes: ChoiceOption[]
  identificationTypes: ChoiceOption[]
  titles: ChoiceOption[]
  genders: ChoiceOption[]
  maritalStatuses: ChoiceOption[]
  politicalRisks: ChoiceOption[]
  amlRisks: ChoiceOption[]
  industries: ChoiceOption[]
  nationalities: ChoiceOption[]
  applicationStatuses: ChoiceOption[]
  documentTypes: ChoiceOption[]
  taskTypes: ChoiceOption[]
  taskStatuses: ChoiceOption[]
  taskPriorities: ChoiceOption[]
  systemPartnerTypes?: ChoiceOption[]
  branches?: ChoiceOption[]
  locations?: { value: string; label: string; branchId: string }[]
  regions?: ChoiceOption[]
}

export interface WorkflowConfig {
  state_machine: Record<string, string[]>
  terminal_statuses: string[]
  all_statuses: string[]
  status_labels: Record<string, string>
}

export interface PartnerOnboardingParameter {
  id: string
  code: string
  name: string
  description: string
  valueType: "STRING" | "TEXT" | "INTEGER" | "FLOAT" | "BOOLEAN" | "JSON" | "FILE" | string
  value: unknown
  isActive: boolean
  isEncrypted: boolean
  sortOrder: number
}

export interface PartnerOnboardingParameterGroup {
  id: string
  code: string
  name: string
  description: string
  parameters: PartnerOnboardingParameter[]
  children: PartnerOnboardingParameterGroup[]
}

export interface PartnerOnboardingChoiceOption {
  id: string
  code: string
  label: string
  isDefault: boolean
  isActive: boolean
  sortOrder: number
  metadata: Record<string, unknown> | null
}

export interface PartnerOnboardingChoiceList {
  id: string
  code: string
  name: string
  description: string
  isActive: boolean
  options: PartnerOnboardingChoiceOption[]
}

export interface PartnerOnboardingConfiguration {
  version: string
  groups: PartnerOnboardingParameterGroup[]
  choiceLists: PartnerOnboardingChoiceList[]
  partnerTypes: Array<{
    id: string
    code: string
    name: string
    description: string
    isActive: boolean
    documents: Array<{
      id: string
      code: string
      description: string
      isRequired: boolean
      isMandatory: boolean
      allowMultipleUploads: boolean
      sortOrder: number
      isActive: boolean
    }>
    attributes: Array<{
      id: string
      fieldName: string
      fieldCode: string
      fieldType: string
      defaultValue: string
      isRequired: boolean
      validationRules: Record<string, unknown>
      displayOrder: number
      visibilityRules: Record<string, unknown>
      isActive: boolean
    }>
    contacts: Array<{
      id: string
      contactType: string
      isRequired: boolean
      multipleAllowed: boolean
      displayOrder: number
      isActive: boolean
    }>
    banks: Array<{
      id: string
      bankType: string
      isRequired: boolean
      multipleAllowed: boolean
      validationRules: Record<string, unknown>
      displayOrder: number
      isActive: boolean
    }>
  }>
}

export interface ContactTypeLabel {
  value: string
  label: string
}

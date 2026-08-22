import { useCallback, useEffect, useRef, useState, type Dispatch, type SetStateAction } from "react"
import { useLocation, useNavigate, useParams } from "react-router-dom"
import {
  ArrowLeft, ArrowRight, Loader2, Save, Send, Upload, Trash2,
  FileText, CheckCircle2, Building2, User, AlertCircle, FileCheck,
  Eye, Plus, X, Search,
} from "lucide-react"
import {
  createApplication,
  updateApplication,
  getApplication,
  submitApplication,
  uploadDocument,
  deleteDocument,
  listDocuments,
  createApplicationPartnerType,
  listApplicationPartnerTypes,
  deleteApplicationPartnerType,
  listFieldValues,
  batchUpdateFieldValues,
  fetchFieldConfigurations,
  fetchDocumentRequirements,
  fetchContactRequirements,
  fetchBankRequirements,
  listContacts,
  createContact,
  listBankAccounts,
  createBankAccount,
  verifyDocument,
  getChoices,
} from "../../lib/api"
import type {
  PartnerApplicationDetail,
  ApplicationDocument,
  PartnerTypeFieldConfiguration,
  PartnerTypeDocumentRequirement,
  PartnerTypeContactRequirement,
  PartnerTypeBankRequirement,
  ApplicationContact,
  ApplicationBankAccount,
  ChoicesResponse,
} from "../../lib/types"
import { useChoiceList, usePartnerOnboardingConfiguration } from "../../config/ConfigurationAPI"
import type { PartnerOnboardingConfiguration } from "../../config/ConfigurationTypes"
import type { Step } from "../../components/shared/Stepper"

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */
interface PartnerRoleConfig {
  branches: string[]
  region: string
  shareDataExternally: boolean
}

interface ContactDraft {
  id?: string
  contactType: string
  firstName: string
  lastName: string
  email: string
  phone: string
  mobile: string
  designation: string
  isPrimary: boolean
  notes: string
}

interface BankDraft {
  id?: string
  bankName: string
  branchName: string
  accountName: string
  accountNumber: string
  swiftCode: string
  iban: string
  currency: string
  isPrimary: boolean
  notes: string
}

interface FormState {
  partnerType: "INDIVIDUAL" | "CORPORATE" | ""
  identificationType: string
  identificationNumber: string
  title: string
  firstName: string
  otherName: string
  surname: string
  gender: string
  dateOfBirth: string
  maritalStatus: string
  occupation: string
  nationality: string
  companyName: string
  tinNumber: string
  incorporationDate: string
  companyIncorporation: string
  industry: string
  contactPerson: string
  contactPersonPhone: string
  contactPersonEmail: string
  email: string
  telephoneNumber: string
  mobileNumber: string
  physicalAddress: string
  postalAddress: string
  politicalRisk: string
  amlRisk: string
}

const INITIAL: FormState = {
  partnerType: "",
  identificationType: "",
  identificationNumber: "",
  title: "Mr",
  firstName: "",
  otherName: "",
  surname: "",
  gender: "",
  dateOfBirth: "",
  maritalStatus: "",
  occupation: "",
  nationality: "",
  companyName: "",
  tinNumber: "",
  incorporationDate: "",
  companyIncorporation: "",
  industry: "",
  contactPerson: "",
  contactPersonPhone: "",
  contactPersonEmail: "",
  email: "",
  telephoneNumber: "",
  mobileNumber: "",
  physicalAddress: "",
  postalAddress: "",
  politicalRisk: "LOW",
  amlRisk: "LOW",
}

const STEPS: Step[] = [
  { title: "Client Type", description: "Individual or Corporate" },
  { title: "Information", description: "Personal or Company details" },
  { title: "Partner Roles", description: "Select roles & fields" },
  { title: "Contact & Risk", description: "Contact info & assessment" },
  { title: "Documents", description: "Upload required docs" },
  { title: "Review & Submit", description: "Final review" },
]

function toPayload(f: FormState): Record<string, unknown> {
  const payload: Record<string, unknown> = {
    partner_type: f.partnerType,
    email: f.email,
    telephone_number: f.telephoneNumber,
    mobile_number: f.mobileNumber,
    physical_address: f.physicalAddress,
    postal_address: f.postalAddress,
    political_risk: f.politicalRisk,
    aml_risk: f.amlRisk,
  }

  if (f.partnerType === "INDIVIDUAL") {
    payload.identification_type = f.identificationType
    payload.identification_number = f.identificationNumber
    payload.title = f.title
    payload.first_name = f.firstName
    payload.other_name = f.otherName
    payload.surname = f.surname
    payload.gender = f.gender
    payload.date_of_birth = f.dateOfBirth || null
    payload.marital_status = f.maritalStatus
    payload.occupation = f.occupation
    payload.nationality = f.nationality
  } else {
    payload.company_name = f.companyName
    payload.tin_number = f.tinNumber
    payload.incorporation_date = f.incorporationDate || null
    payload.company_incorporation = f.companyIncorporation
    payload.industry = f.industry
    payload.contact_person = f.contactPerson
    payload.contact_person_phone = f.contactPersonPhone
    payload.contact_person_email = f.contactPersonEmail
  }

  return payload
}

function configuredOptions(
  configuration: PartnerOnboardingConfiguration | null,
  codes: string[],
  fallback: { value: string; label: string }[],
) {
  const list = configuration?.choiceLists.find((item) => codes.includes(item.code))
  if (!list) return fallback
  return list.options.filter((option) => option.isActive).sort((a, b) => a.sortOrder - b.sortOrder).map((option) => ({ value: option.code, label: option.label }))
}

function configuredDefault(
  configuration: PartnerOnboardingConfiguration | null,
  codes: string[],
  fallback: string,
) {
  const list = configuration?.choiceLists.find((item) => codes.includes(item.code))
  return list?.options.find((option) => option.isActive && option.isDefault)?.code ?? fallback
}

function configuredParameter(configuration: PartnerOnboardingConfiguration | null, code: string): unknown {
  for (const group of configuration?.groups ?? []) {
    const direct = group.parameters.find((parameter) => parameter.code === code)
    if (direct) return direct.value
    for (const child of group.children) {
      const nested = child.parameters.find((parameter) => parameter.code === code)
      if (nested) return nested.value
    }
  }
  return undefined
}

function requiredFieldList(configuration: PartnerOnboardingConfiguration | null, partnerType: string) {
  const code = partnerType === "INDIVIDUAL" ? "INDIVIDUAL_REQUIRED_FIELDS" : "CORPORATE_REQUIRED_FIELDS"
  const value = configuredParameter(configuration, code)
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : []
}

function formValueForParameter(form: FormState, code: string): unknown {
  const fields: Record<string, keyof FormState> = {
    identification_type: "identificationType",
    identification_number: "identificationNumber",
    first_name: "firstName",
    other_name: "otherName",
    surname: "surname",
    title: "title",
    gender: "gender",
    date_of_birth: "dateOfBirth",
    marital_status: "maritalStatus",
    occupation: "occupation",
    nationality: "nationality",
    company_name: "companyName",
    tin_number: "tinNumber",
    incorporation_date: "incorporationDate",
    company_incorporation: "companyIncorporation",
    industry: "industry",
    contact_person: "contactPerson",
    contact_person_phone: "contactPersonPhone",
    contact_person_email: "contactPersonEmail",
    email: "email",
    telephone_number: "telephoneNumber",
    mobile_number: "mobileNumber",
    physical_address: "physicalAddress",
    postal_address: "postalAddress",
    political_risk: "politicalRisk",
    aml_risk: "amlRisk",
  }
  const field = fields[code]
  return field ? form[field] : undefined
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */
export default function ApplicationForm() {
  const { id } = useParams<{ id: string }>()
  const isEdit = !!id
  const location = useLocation()
  const navigate = useNavigate()

  const [form, setForm] = useState<FormState>(INITIAL)
  const [step, setStep] = useState(() => {
    const requestedStep = Number((location.state as { step?: number } | null)?.step ?? 0)
    return Number.isInteger(requestedStep) ? Math.max(0, Math.min(requestedStep, STEPS.length - 1)) : 0
  })
  const [saving, setSaving] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState("")
  const [docs, setDocs] = useState<ApplicationDocument[]>([])
  const [documentRequirements, setDocumentRequirements] = useState<PartnerTypeDocumentRequirement[]>([])
  const [contactRequirements, setContactRequirements] = useState<PartnerTypeContactRequirement[]>([])
  const [bankRequirements, setBankRequirements] = useState<PartnerTypeBankRequirement[]>([])
  const [contacts, setContacts] = useState<ContactDraft[]>([])
  const [bankAccounts, setBankAccounts] = useState<BankDraft[]>([])

  const [selectedPartnerTypes, setSelectedPartnerTypes] = useState<string[]>([])
  const [dynamicFieldsConfig, setDynamicFieldsConfig] = useState<PartnerTypeFieldConfiguration[]>([])
  const [dynamicFieldValues, setDynamicFieldValues] = useState<Record<string, unknown>>({})
  const [choices, setChoices] = useState<ChoicesResponse | null>(null)
  const [roleConfigs, setRoleConfigs] = useState<Record<string, PartnerRoleConfig>>({})
  const { configuration: onboardingConfiguration } = usePartnerOnboardingConfiguration()

  /* ------------------ Choice Lists ------------------ */
  const titleList = useChoiceList("TITLE_CHOICES")
  const genderList = useChoiceList("GENDER_CHOICES")
  const idTypeList = useChoiceList("IDENTIFICATION_TYPE_CHOICES")
  const maritalStatusList = useChoiceList("MARITAL_STATUS_CHOICES")
  const nationalityList = useChoiceList("NATIONALITY_CHOICES")
  const industryList = useChoiceList("INDUSTRY_CHOICES")
  const politicalRiskList = useChoiceList("POLITICAL_RISK_CHOICES")
  const amlRiskList = useChoiceList("AML_RISK_CHOICES")
  const documentTypeList = useChoiceList("DOCUMENT_TYPE_CHOICES")
  const systemPartnerTypeList = useChoiceList("system_partner_types")

  const titleOptions = configuredOptions(onboardingConfiguration, ["TITLE_CHOICES"], titleList.options)
  const idTypeOptions = configuredOptions(onboardingConfiguration, ["IDENTIFICATION_TYPE_CHOICES"], idTypeList.options)
  const genderOptions = configuredOptions(onboardingConfiguration, ["GENDER_CHOICES"], genderList.options)
  const maritalStatusOptions = configuredOptions(onboardingConfiguration, ["MARITAL_STATUS_CHOICES"], maritalStatusList.options)
  const nationalityOptions = configuredOptions(onboardingConfiguration, ["NATIONALITY_CHOICES"], nationalityList.options)
  const industryOptions = configuredOptions(onboardingConfiguration, ["INDUSTRY_CHOICES"], industryList.options)
  const politicalRiskOptions = configuredOptions(onboardingConfiguration, ["POLITICAL_RISK_CHOICES"], politicalRiskList.options)
  const amlRiskOptions = configuredOptions(onboardingConfiguration, ["AML_RISK_CHOICES"], amlRiskList.options)
  const documentTypeOptions = configuredOptions(onboardingConfiguration, ["DOCUMENT_TYPE_CHOICES"], documentTypeList.options)
  // Partner roles are foreign keys to partners.PartnerType. Do not use the
  // configurable PARTNER_TYPE_CHOICES catalog here: its values are business
  // codes (for example CORPORATE), while onboarding assignment/configuration
  // endpoints require the PartnerType UUID.
  const systemPartnerTypeOptions = choices?.systemPartnerTypes ?? []
  const defaultCurrency = String(configuredParameter(onboardingConfiguration, "DEFAULT_CURRENCY") ?? "TZS")

  /* ------------------ Effects ------------------ */
  useEffect(() => {
    if (isEdit || !onboardingConfiguration) return
    setForm((current) => ({
      ...current,
      title: current.title === INITIAL.title ? configuredDefault(onboardingConfiguration, ["TITLE_CHOICES"], INITIAL.title) : current.title,
      politicalRisk: current.politicalRisk === INITIAL.politicalRisk ? configuredDefault(onboardingConfiguration, ["POLITICAL_RISK_CHOICES"], INITIAL.politicalRisk) : current.politicalRisk,
      amlRisk: current.amlRisk === INITIAL.amlRisk ? configuredDefault(onboardingConfiguration, ["AML_RISK_CHOICES"], INITIAL.amlRisk) : current.amlRisk,
    }))
  }, [isEdit, onboardingConfiguration])

  useEffect(() => {
    if (!isEdit) return
    let active = true
    getApplication(id!).then((d) => {
      if (!active) return
      setForm({
        partnerType: d.partnerType,
        identificationType: d.identificationType || "",
        identificationNumber: d.identificationNumber || "",
        title: d.title || "Mr",
        firstName: d.firstName || "",
        otherName: d.otherName || "",
        surname: d.surname || "",
        gender: d.gender || "",
        dateOfBirth: d.dateOfBirth || "",
        maritalStatus: d.maritalStatus || "",
        occupation: d.occupation || "",
        nationality: d.nationality || "",
        companyName: d.companyName || "",
        tinNumber: d.tinNumber || "",
        incorporationDate: d.incorporationDate || "",
        companyIncorporation: d.companyIncorporation || "",
        industry: d.industry || "",
        contactPerson: d.contactPerson || "",
        contactPersonPhone: d.contactPersonPhone || "",
        contactPersonEmail: d.contactPersonEmail || "",
        email: d.email || "",
        telephoneNumber: d.telephoneNumber || "",
        mobileNumber: d.mobileNumber || "",
        physicalAddress: d.physicalAddress || "",
        postalAddress: d.postalAddress || "",
        politicalRisk: d.politicalRisk || "LOW",
        amlRisk: d.amlRisk || "LOW",
      })
      setDocs(d.documents || [])
    })
    return () => { active = false }
  }, [id, isEdit, defaultCurrency])

  useEffect(() => {
    if (!isEdit || !id) return
    let active = true
    listDocuments(id)
      .then((d) => { if (active) setDocs(d) })
      .catch(() => {})
    return () => { active = false }
  }, [id, isEdit])

  useEffect(() => {
    let active = true
    const fetchConfigs = async () => {
      const configs: PartnerTypeFieldConfiguration[] = []
      for (const pt of selectedPartnerTypes) {
        try {
          const fc = await fetchFieldConfigurations(pt)
          configs.push(...fc)
        } catch {}
      }
      if (active) setDynamicFieldsConfig(configs)
    }
    fetchConfigs()
    return () => { active = false }
  }, [selectedPartnerTypes, choices])

  useEffect(() => {
    getChoices().then(setChoices).catch(() => {})
  }, [])

  useEffect(() => {
    if (!isEdit || !id) return
    let active = true
    Promise.all([
      listApplicationPartnerTypes(id),
      listFieldValues(id),
      listContacts(id),
      listBankAccounts(id),
      getChoices(),
    ]).then(([ptypes, fvalues, existingContacts, existingBanks, chs]) => {
      if (!active) return
      setSelectedPartnerTypes(ptypes.map(pt => pt.partnerType))
      const rc: Record<string, PartnerRoleConfig> = {}
      ptypes.forEach(pt => {
        rc[pt.partnerType] = {
          branches: pt.branch ? [pt.branch] : [],
          region: pt.region || "",
          shareDataExternally: pt.shareDataExternally,
        }
      })
      setRoleConfigs(rc)
      setChoices(chs)
      setContacts(existingContacts.map((contact) => ({
        id: contact.id,
        contactType: contact.contactType || "SECONDARY",
        firstName: contact.firstName || "",
        lastName: contact.lastName || "",
        email: contact.email || "",
        phone: contact.phone || "",
        mobile: contact.mobile || "",
        designation: contact.designation || "",
        isPrimary: contact.isPrimary,
        notes: contact.notes || "",
      })))
      setBankAccounts(existingBanks.map((account) => ({
        id: account.id,
        bankName: account.bankName || "",
        branchName: account.branchName || "",
        accountName: account.accountName || "",
        accountNumber: account.accountNumber || "",
        swiftCode: account.swiftCode || "",
        iban: account.iban || "",
        currency: account.currency || defaultCurrency,
        isPrimary: account.isPrimary,
        notes: account.notes || "",
      })))
      const fvMap: Record<string, unknown> = {}
      fvalues.forEach(fv => { fvMap[fv.fieldConfig] = fv.valueJson })
      setDynamicFieldValues(fvMap)
    }).catch(() => {})
    return () => { active = false }
  }, [id, isEdit])

  useEffect(() => {
    let active = true
    const loadRequirements = async () => {
      if (selectedPartnerTypes.length === 0) {
        setDocumentRequirements([])
        setContactRequirements([])
        setBankRequirements([])
        return
      }
      const results = await Promise.all(selectedPartnerTypes.map(async (partnerTypeId) => {
        const [documents, contactReqs, bankReqs] = await Promise.all([
          fetchDocumentRequirements(partnerTypeId).catch(() => [] as PartnerTypeDocumentRequirement[]),
          fetchContactRequirements(partnerTypeId).catch(() => [] as PartnerTypeContactRequirement[]),
          fetchBankRequirements(partnerTypeId).catch(() => [] as PartnerTypeBankRequirement[]),
        ])
        return { documents, contactReqs, bankReqs }
      }))
      if (!active) return
      setDocumentRequirements(results.flatMap((result) => result.documents.filter((item) => item.isActive)))
      setContactRequirements(results.flatMap((result) => result.contactReqs.filter((item) => item.isActive)))
      setBankRequirements(results.flatMap((result) => result.bankReqs.filter((item) => item.isActive)))
    }
    loadRequirements().catch(() => {})
    return () => { active = false }
  }, [selectedPartnerTypes])

  /* ------------------ Helpers ------------------ */
  const update = useCallback(
    <K extends keyof FormState>(k: K, v: FormState[K]) =>
      setForm((f) => ({ ...f, [k]: v })),
    []
  )

  function validateStep(s: number): string | null {
    switch (s) {
      case 0:
        if (!form.partnerType) return "Select a client type"
        break
      case 1: {
        const configuredFields = requiredFieldList(onboardingConfiguration, form.partnerType)
        const informationFields = form.partnerType === "INDIVIDUAL"
          ? new Set(["identification_type", "identification_number", "first_name", "other_name", "surname", "title", "gender", "date_of_birth", "marital_status", "occupation", "nationality"])
          : new Set(["company_name", "tin_number", "incorporation_date", "company_incorporation", "industry", "contact_person"])
        const requiredFields = configuredFields.length > 0
          ? configuredFields.filter((field) => informationFields.has(field))
          : form.partnerType === "INDIVIDUAL" ? ["first_name", "surname"] : ["company_name", "tin_number", "contact_person"]
        const missingField = requiredFields.find((field) => {
          const value = formValueForParameter(form, field)
          return value === undefined || value === null || String(value).trim() === ""
        })
        if (missingField) return `Complete the required field: ${missingField.replace(/_/g, " ")}`
        break
      }
      case 2: {
        const missingDynamicField = dynamicFieldsConfig.find((field) => {
          if (!field.isRequired) return false
          const value = dynamicFieldValues[field.id]
          return value === undefined || value === null || (Array.isArray(value) ? value.length === 0 : String(value).trim() === "")
        })
        if (missingDynamicField) return `Complete the required partner attribute: ${missingDynamicField.fieldName}`
        break
      }
      case 3: {
        const configuredFields = requiredFieldList(onboardingConfiguration, form.partnerType)
        const contactFields = new Set(["email", "telephone_number", "mobile_number", "physical_address", "postal_address", "contact_person_phone", "contact_person_email"])
        const requiredContactFields = configuredFields.length > 0
          ? configuredFields.filter((field) => contactFields.has(field))
          : ["email", "mobile_number"]
        const missingContactField = requiredContactFields.find((field) => {
          const value = formValueForParameter(form, field)
          return value === undefined || value === null || String(value).trim() === ""
        })
        if (missingContactField) return `Complete the required field: ${missingContactField.replace(/_/g, " ")}`
        const requiredContactTypes = contactRequirements.filter((item) => item.isRequired).map((item) => item.contactType)
        const presentContactTypes = new Set(contacts.map((contact) => contact.contactType))
        const missingContacts = requiredContactTypes.filter((type) => !presentContactTypes.has(type))
        if (missingContacts.length > 0) return `Add the required contact(s): ${missingContacts.join(", ")}`
        const incompleteContact = contacts.find((contact) => !contact.firstName.trim() || !contact.lastName.trim())
        if (incompleteContact) return "Complete the first and last name for every added contact"
        const requiredBanks = bankRequirements.filter((item) => item.isRequired)
        if (requiredBanks.length > 0 && bankAccounts.length === 0) return "Add at least one required bank account"
        const incompleteBank = bankAccounts.find((account) => !account.bankName.trim() || !account.accountName.trim() || !account.accountNumber.trim() || !account.currency.trim())
        if (incompleteBank) return "Complete the bank name, account name, account number, and currency for every added account"
        break
      }
      case 4: {
        const requiredDocumentTypes = documentRequirements.filter((item) => item.isRequired).map((item) => item.code)
        if (requiredDocumentTypes.length > 0 && !isEdit) return "Save the application draft before uploading required documents"
        const presentDocumentTypes = new Set(docs.map((doc) => doc.documentType))
        const missingDocuments = requiredDocumentTypes.filter((code) => !presentDocumentTypes.has(code))
        if (missingDocuments.length > 0) return `Upload the required document(s): ${missingDocuments.join(", ")}`
        break
      }
      case 5: {
        const requiredDocumentTypes = documentRequirements.filter((item) => item.isRequired).map((item) => item.code)
        const verifiedDocumentTypes = new Set(docs.filter((doc) => doc.isVerified).map((doc) => doc.documentType))
        const unverifiedDocuments = requiredDocumentTypes.filter((code) => !verifiedDocumentTypes.has(code))
        if (unverifiedDocuments.length > 0) return `Verify the required document(s) before submitting: ${unverifiedDocuments.join(", ")}`
        break
      }
    }
    return null
  }

  function canAdvance(s: number): boolean {
    return validateStep(s) === null
  }

  async function handleNext() {
    const err = validateStep(step)
    if (err) { setError(err); return }
    setError("")
    setSaving(true)
    try {
      if (!isEdit && step >= 2) {
        const appId = await ensureDraft()
        navigate(`/onboarding/${appId}/edit`, { state: { step: Math.min(step + 1, STEPS.length - 1) }, replace: true })
        return
      }
      setStep((s) => Math.min(s + 1, STEPS.length - 1))
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save this phase")
    } finally {
      setSaving(false)
    }
  }

  function handleBack() {
    setError("")
    setStep((s) => Math.max(s - 1, 0))
  }

  async function savePartnerTypesAndFields(appId: string) {
    const existingPts = isEdit ? await listApplicationPartnerTypes(appId) : []
    const existingIds = existingPts.map(pt => pt.partnerType)

    const toAdd = selectedPartnerTypes.filter(pid => !existingIds.includes(pid))
    const toRemove = existingPts.filter(pt => !selectedPartnerTypes.includes(pt.partnerType))

    for (const pt of toRemove) {
      await deleteApplicationPartnerType(appId, pt.id)
    }
    for (const ptId of toAdd) {
      const cfg = roleConfigs[ptId] ?? { branches: [], region: "", shareDataExternally: false }
      await createApplicationPartnerType(appId, {
        partner_type: ptId,
        branches: cfg.branches.length > 0 ? cfg.branches : undefined,
        region: cfg.region,
        share_data_externally: cfg.shareDataExternally,
      })
    }

    const batchData = Object.entries(dynamicFieldValues).map(([configId, val]) => ({
      field_config: configId,
      value_json: val as Record<string, unknown>
    }))
    if (batchData.length > 0) {
      await batchUpdateFieldValues(appId, batchData)
    }
  }

  async function saveNestedRecords(appId: string) {
    const unsavedContacts = contacts.filter((contact) => !contact.id)
    for (const contact of unsavedContacts) {
      const created = await createContact(appId, {
        contact_type: contact.contactType,
        first_name: contact.firstName,
        last_name: contact.lastName,
        email: contact.email,
        phone: contact.phone,
        mobile: contact.mobile,
        designation: contact.designation,
        is_primary: contact.isPrimary,
        notes: contact.notes,
      } as unknown as Partial<ApplicationContact>)
      setContacts((current) => current.map((item) => item === contact ? { ...item, id: created.id } : item))
    }

    const unsavedBanks = bankAccounts.filter((account) => !account.id)
    for (const account of unsavedBanks) {
      const created = await createBankAccount(appId, {
        bank_name: account.bankName,
        branch_name: account.branchName,
        account_name: account.accountName,
        account_number: account.accountNumber,
        swift_code: account.swiftCode,
        iban: account.iban,
        currency: account.currency,
        is_primary: account.isPrimary,
        notes: account.notes,
      } as unknown as Partial<ApplicationBankAccount>)
      setBankAccounts((current) => current.map((item) => item === account ? { ...item, id: created.id } : item))
    }
  }

  async function ensureDraft(): Promise<string> {
    if (isEdit && id) return id
    const created = await createApplication(toPayload(form))
    const appId = (created as PartnerApplicationDetail).id
    await savePartnerTypesAndFields(appId)
    await saveNestedRecords(appId)
    return appId
  }

  async function handleSave() {
    const err = validateStep(step)
    if (err) { setError(err); return }
    setError("")
    setSaving(true)
    try {
      if (isEdit) {
        await updateApplication(id!, toPayload(form))
        await savePartnerTypesAndFields(id!)
        await saveNestedRecords(id!)
      } else {
        const appId = await ensureDraft()
        navigate(`/onboarding/${appId}/edit`, { state: { step }, replace: true })
        return
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save")
    } finally {
      setSaving(false)
    }
  }

  async function handleSaveAndSubmit() {
    const err = validateStep(step)
    if (err) { setError(err); return }
    setError("")
    setSubmitting(true)
    try {
      if (!isEdit) {
        const appId = await ensureDraft()
        setError("Draft created. Continue through the Documents phase, upload and verify the required evidence, then submit.")
        navigate(`/onboarding/${appId}/edit`, { state: { step: 4 }, replace: true })
        return
      }
      const appId = id!
      await updateApplication(appId, toPayload(form))
      await savePartnerTypesAndFields(appId)
      await saveNestedRecords(appId)
      await submitApplication(appId)
      navigate(`/onboarding/${appId}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to submit")
    } finally {
      setSubmitting(false)
    }
  }

  async function handleUpload(file: File, docType: string) {
    if (!isEdit) return
    try {
      const doc = await uploadDocument(id!, file, docType)
      setDocs((d) => [...d, doc])
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed")
    }
  }

  async function handleDeleteDoc(docId: string) {
    if (!isEdit) return
    try {
      await deleteDocument(id!, docId)
      setDocs((d) => d.filter((x) => x.id !== docId))
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed")
    }
  }

  async function handleVerifyDoc(docId: string) {
    if (!isEdit) return
    try {
      const verified = await verifyDocument(id!, docId)
      setDocs((current) => current.map((document) => document.id === docId ? verified : document))
    } catch (e) {
      setError(e instanceof Error ? e.message : "Verification failed")
    }
  }

  const isCorporate = form.partnerType === "CORPORATE"
  const busy = saving || submitting
  const isLastStep = step === STEPS.length - 1
  const isFirstStep = step === 0

  function handleStepClick(index: number) {
    if (index < step) {
      setStep(index)
      return
    }
    for (let i = step; i < index; i++) {
      if (!canAdvance(i)) {
        const err = validateStep(i)
        setError(err || "Complete the current step first")
        return
      }
    }
    setError("")
    setStep(index)
  }

  /* ------------------------------------------------------------------ */
  /*  Render                                                             */
  /* ------------------------------------------------------------------ */
  return (
    <div className="mx-auto w-full max-w-6xl space-y-5 text-[#1b1b1b]">
      {/* Header */}
      <div className="flex flex-col gap-4 border-b border-[#e7e7e7] pb-5 sm:flex-row sm:items-end sm:justify-between">
        <button
          onClick={() => navigate(isEdit ? `/onboarding/${id}` : "/onboarding")}
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-[#d9d9d9] bg-white text-[#555] transition hover:border-[#111] hover:text-[#111]"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <h1 className="text-2xl font-semibold tracking-[-0.03em] text-[#111]">
          {isEdit ? "Edit Application" : "Add Partner"}
        </h1>
      </div>

      {/* Progress navigation */}
      <div className="overflow-x-auto rounded-xl border border-[#dedede] bg-white p-2">
        <div className="grid min-w-[720px] grid-cols-6 gap-1">
          {STEPS.map((item, index) => (
            <button key={item.title} type="button" onClick={() => handleStepClick(index)} className={`relative rounded-lg px-3 py-3 text-left transition ${index === step ? "bg-[#111] text-white" : index < step ? "bg-[#f1f1f1] text-[#222]" : "text-[#777] hover:bg-[#f7f7f7]"}`}>
              <span className="flex items-center gap-2"><span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-xs font-bold ${index === step ? "border-white bg-white text-[#111]" : index < step ? "border-[#111] bg-[#111] text-white" : "border-[#cfcfcf]"}`}>{index < step ? "✓" : index + 1}</span><span className="truncate text-xs font-bold">{item.title}</span></span>
              <span className={`mt-1 block truncate pl-8 text-[10px] ${index === step ? "text-[#d7d7d7]" : "text-[#999]"}`}>{item.description}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="mb-4 flex items-center gap-2 rounded-lg border border-[#d4d4d4] bg-[#f6f6f6] px-4 py-3 text-sm text-[#333]">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Step Content */}
      <div className="overflow-hidden rounded-xl border border-[#dedede] bg-white shadow-[0_10px_35px_rgba(0,0,0,0.04)]">
        {step === 0 && (
          <StepClientType
            partnerType={form.partnerType}
            isEdit={isEdit}
            onSelect={(v) => setForm((f) => ({ ...f, partnerType: v }))}
          />
        )}

        {step === 1 && (
          <StepInformation
            form={form}
            isCorporate={isCorporate}
            update={update}
            titleList={{ ...titleList, options: titleOptions }}
            idTypeList={{ ...idTypeList, options: idTypeOptions }}
            genderList={{ ...genderList, options: genderOptions }}
            maritalStatusList={{ ...maritalStatusList, options: maritalStatusOptions }}
            nationalityList={{ ...nationalityList, options: nationalityOptions }}
            industryList={{ ...industryList, options: industryOptions }}
          />
        )}

        {step === 2 && (
          <StepPartnerRoles
            selectedPartnerTypes={selectedPartnerTypes}
            setSelectedPartnerTypes={setSelectedPartnerTypes}
            roleConfigs={roleConfigs}
            setRoleConfigs={setRoleConfigs}
            dynamicFieldsConfig={dynamicFieldsConfig}
            dynamicFieldValues={dynamicFieldValues}
            setDynamicFieldValues={setDynamicFieldValues}
            systemPartnerTypeList={{ ...systemPartnerTypeList, options: systemPartnerTypeOptions }}
            choices={choices}
          />
        )}

        {step === 3 && (
          <StepContactRisk
            form={form}
            update={update}
            politicalRiskList={{ ...politicalRiskList, options: politicalRiskOptions }}
            amlRiskList={{ ...amlRiskList, options: amlRiskOptions }}
            contacts={contacts}
            setContacts={setContacts}
            bankAccounts={bankAccounts}
            setBankAccounts={setBankAccounts}
            contactRequirements={contactRequirements}
            bankRequirements={bankRequirements}
            defaultCurrency={defaultCurrency}
          />
        )}

        {step === 4 && (
          <StepDocuments
            isEdit={isEdit}
            docs={docs}
            documentRequirements={documentRequirements}
            documentTypeList={{ ...documentTypeList, options: documentTypeOptions }}
            onUpload={handleUpload}
            onDelete={handleDeleteDoc}
            onVerify={handleVerifyDoc}
          />
        )}

        {step === 5 && (
          <StepReview
            form={form}
            isCorporate={isCorporate}
            selectedPartnerTypes={selectedPartnerTypes}
            systemPartnerTypeList={{ ...systemPartnerTypeList, options: systemPartnerTypeOptions }}
            docs={docs}
            isEdit={isEdit}
          />
        )}
      </div>

      {/* Navigation */}
      <div className="flex flex-col-reverse gap-3 border-t border-[#e7e7e7] pt-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          {!isFirstStep && (
            <button
              onClick={handleBack}
              disabled={busy}
              className="inline-flex items-center gap-2 rounded-lg border border-[#d6d6d6] bg-white px-5 py-2.5 text-sm font-semibold text-[#444] transition hover:border-[#111] hover:text-[#111] disabled:opacity-50"
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </button>
          )}
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleSave}
            disabled={busy}
            className="inline-flex items-center gap-2 rounded-lg border border-[#d9d9d9] px-5 py-2.5 text-sm font-semibold text-[#222] transition hover:bg-[#f3f3f3] disabled:opacity-50"
          >
            {saving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            Save as Draft
          </button>

          {isLastStep ? (
            <button
              onClick={handleSaveAndSubmit}
              disabled={busy}
              className="inline-flex items-center gap-2 rounded-lg bg-[#111] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#2b2b2b] disabled:opacity-50"
            >
              {submitting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
              Submit Application
            </button>
          ) : (
            <button
              onClick={handleNext}
              disabled={busy}
              className="inline-flex items-center gap-2 rounded-lg bg-[#111] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#2b2b2b] disabled:opacity-50"
            >
              Next
              <ArrowRight className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

/* ================================================================== */
/*  Step Components                                                    */
/* ================================================================== */

function StepClientType({
  partnerType,
  isEdit,
  onSelect,
}: {
  partnerType: string
  isEdit: boolean
  onSelect: (v: "INDIVIDUAL" | "CORPORATE") => void
}) {
  return (
    <div className="p-6">
      <div className="mb-6 text-center">
        <h2 className="text-lg font-bold text-[#222]">Choose Client Type</h2>
        <p className="mt-1 text-sm text-[#777]">Select whether this partner is an individual person or a company</p>
      </div>
      <div className="mx-auto grid max-w-2xl grid-cols-2 gap-6">
        {[
          { value: "INDIVIDUAL", label: "Individual", icon: User, description: "Individual person", detail: "For sole proprietors, freelancers, and individual partners" },
          { value: "CORPORATE", label: "Corporate", icon: Building2, description: "Company/Organization", detail: "For registered companies, LLCs, corporations, and organizations" },
        ].map((type) => {
          const Icon = type.icon
          const isSelected = partnerType === type.value
          return (
            <button
              key={type.value}
              type="button"
              disabled={isEdit}
              onClick={() => onSelect(type.value as "INDIVIDUAL" | "CORPORATE")}
              className={`relative flex flex-col items-center rounded-xl border-2 p-8 text-center transition-all duration-200 ${
                isSelected
                  ? "border-[#111] bg-[#111] text-white shadow-md scale-[1.02]"
                  : "border-[#d9d9d9] bg-white text-[#777] hover:border-[#777] hover:bg-[#fafafa] hover:shadow-sm"
              } ${isEdit ? "cursor-not-allowed opacity-60" : "cursor-pointer"}`}
            >
              <Icon className={`mb-3 h-10 w-10 ${isSelected ? "text-white" : "text-[#777]"}`} />
              <span className={`text-base font-bold ${isSelected ? "text-white" : "text-[#222]"}`}>
                {type.label}
              </span>
              <span className="mt-1 text-xs text-[#777]">{type.description}</span>
              <span className="mt-2 text-[11px] leading-tight text-[#777]/70">{type.detail}</span>
              {isSelected && (
                    <div className="absolute right-3 top-3 flex h-6 w-6 items-center justify-center rounded-full bg-white text-[#111]">
                  <CheckCircle2 className="h-4 w-4" />
                </div>
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}

function StepInformation({
  form,
  isCorporate,
  update,
  titleList,
  idTypeList,
  genderList,
  maritalStatusList,
  nationalityList,
  industryList,
}: {
  form: FormState
  isCorporate: boolean
  update: <K extends keyof FormState>(k: K, v: FormState[K]) => void
  titleList: { options: { value: string; label: string }[] }
  idTypeList: { options: { value: string; label: string }[] }
  genderList: { options: { value: string; label: string }[] }
  maritalStatusList: { options: { value: string; label: string }[] }
  nationalityList: { options: { value: string; label: string }[] }
  industryList: { options: { value: string; label: string }[] }
}) {
  return (
    <>
      <div className="border-b border-[#d9d9d9] px-6 py-4">
        <h2 className="text-base font-semibold text-[#222]">
          {isCorporate ? "Company Information" : "Personal Information"}
        </h2>
        <p className="mt-0.5 text-xs text-[#777]">
          {isCorporate
            ? "Enter the company details below. Fields marked with * are required."
            : "Enter the personal details below. Fields marked with * are required."}
        </p>
      </div>
      <div className="grid grid-cols-1 gap-x-6 gap-y-4 p-6 sm:grid-cols-2 lg:grid-cols-3">
        {isCorporate ? (
          <>
            <InputField label="Company Name *" value={form.companyName} onChange={(v) => update("companyName", v)} colSpan={3} />
            <InputField label="TIN Number *" value={form.tinNumber} onChange={(v) => update("tinNumber", v)} />
            <InputField type="date" label="Incorporation Date" value={form.incorporationDate} onChange={(v) => update("incorporationDate", v)} />
            <InputField label="Company Incorporation Number *" value={form.companyIncorporation} onChange={(v) => update("companyIncorporation", v)} colSpan={3} />
            <SelectField label="Industry" value={form.industry} onChange={(v) => update("industry", v)} options={industryList.options} placeholder="Select industry" colSpan={3} />
            <InputField label="Contact Person *" value={form.contactPerson} onChange={(v) => update("contactPerson", v)} />
            <InputField label="Contact Phone" value={form.contactPersonPhone} onChange={(v) => update("contactPersonPhone", v)} />
            <InputField label="Contact Email" type="email" value={form.contactPersonEmail} onChange={(v) => update("contactPersonEmail", v)} />
          </>
        ) : (
          <>
            <SelectField label="Title" value={form.title} onChange={(v) => update("title", v)} options={titleList.options} />
            <InputField label="First Name *" value={form.firstName} onChange={(v) => update("firstName", v)} />
            <InputField label="Other Name" value={form.otherName} onChange={(v) => update("otherName", v)} />
            <InputField label="Surname *" value={form.surname} onChange={(v) => update("surname", v)} />
            <SelectField label="ID Type" value={form.identificationType} onChange={(v) => update("identificationType", v)} options={idTypeList.options} placeholder="Select ID type" />
            <InputField label="ID Number" value={form.identificationNumber} onChange={(v) => update("identificationNumber", v)} />
            <SelectField label="Gender" value={form.gender} onChange={(v) => update("gender", v)} options={genderList.options} placeholder="Select gender" />
            <InputField type="date" label="Date of Birth" value={form.dateOfBirth} onChange={(v) => update("dateOfBirth", v)} />
            <SelectField label="Marital Status" value={form.maritalStatus} onChange={(v) => update("maritalStatus", v)} options={maritalStatusList.options} placeholder="Select" />
            <InputField label="Occupation" value={form.occupation} onChange={(v) => update("occupation", v)} />
            <SelectField label="Nationality" value={form.nationality} onChange={(v) => update("nationality", v)} options={nationalityList.options} placeholder="Select nationality" colSpan={3} />
          </>
        )}
      </div>
    </>
  )
}

function StepPartnerRoles({
  selectedPartnerTypes,
  setSelectedPartnerTypes,
  roleConfigs,
  setRoleConfigs,
  dynamicFieldsConfig,
  dynamicFieldValues,
  setDynamicFieldValues,
  systemPartnerTypeList,
  choices,
}: {
  selectedPartnerTypes: string[]
  setSelectedPartnerTypes: (v: string[]) => void
  roleConfigs: Record<string, PartnerRoleConfig>
  setRoleConfigs: (v: Record<string, PartnerRoleConfig>) => void
  dynamicFieldsConfig: PartnerTypeFieldConfiguration[]
  dynamicFieldValues: Record<string, unknown>
  setDynamicFieldValues: (v: Record<string, unknown>) => void
  systemPartnerTypeList: { options: { value: string; label: string }[] }
  choices: ChoicesResponse | null
}) {
  function togglePartnerType(value: string) {
    const isSelected = selectedPartnerTypes.includes(value)
    if (isSelected) {
      setSelectedPartnerTypes(selectedPartnerTypes.filter((id) => id !== value))
      const next = { ...roleConfigs }
      delete next[value]
      setRoleConfigs(next)
    } else {
      setSelectedPartnerTypes([...selectedPartnerTypes, value])
      setRoleConfigs({
        ...roleConfigs,
        [value]: { branches: [], region: "", shareDataExternally: false },
      })
    }
  }

  function updateConfig(ptId: string, patch: Partial<PartnerRoleConfig>) {
    setRoleConfigs({
      ...roleConfigs,
      [ptId]: { ...roleConfigs[ptId], ...patch },
    })
  }

  const ptLabel = (id: string) => systemPartnerTypeList.options.find((o) => o.value === id)?.label ?? id

  const branchOptions = choices?.branches ?? []

  return (
    <>
      <div className="border-b border-[#d9d9d9] px-6 py-4">
        <h2 className="text-base font-semibold text-[#222]">Assign Partner Roles</h2>
        <p className="mt-0.5 text-xs text-[#777]">
          Select one or more partner roles for this application. Each role may require additional information.
        </p>
      </div>

      <div className="p-6">
        {/* Partner type chips */}
        <div className="flex flex-wrap gap-2 mb-6">
          {systemPartnerTypeList.options.map((pt) => {
            const isSelected = selectedPartnerTypes.includes(pt.value)
            return (
              <button
                key={pt.value}
                type="button"
                onClick={() => togglePartnerType(pt.value)}
                className={`rounded-full border px-4 py-1.5 text-sm font-medium transition ${
                  isSelected
                    ? "border-[#111] bg-[#111] text-white shadow-sm"
                    : "border-[#d9d9d9] bg-white text-[#777] hover:border-[#111]/50 hover:text-[#222]"
                }`}
              >
                {pt.label}
              </button>
            )
          })}
        </div>

        {/* Config cards for selected partner types */}
        {selectedPartnerTypes.length > 0 && (
          <div className="space-y-4 mb-6">
            {selectedPartnerTypes.map((ptId) => {
              const cfg = roleConfigs[ptId] ?? { branches: [], region: "", shareDataExternally: false }
              return (
                <div key={ptId} className="rounded-lg border border-[#d9d9d9] bg-white p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-[#222]">{ptLabel(ptId)}</h3>
                    <button
                      type="button"
                      onClick={() => togglePartnerType(ptId)}
                      className="rounded p-1 text-[#777] hover:text-[#111] transition-colors"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                  <div className="grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-2 lg:grid-cols-3">
                    {/* Branches */}
                    <BranchSelect
                      selected={cfg.branches}
                      options={branchOptions}
                      onChange={(vals) => updateConfig(ptId, { branches: vals })}
                    />
                    {/* Region */}
                    <SelectField
                      label="Region"
                      value={cfg.region}
                      onChange={(v) => updateConfig(ptId, { region: v })}
                      options={choices?.regions ?? []}
                      placeholder="Select region"
                    />
                    {/* Share Data */}
                    <SelectField
                      label="Share Data Externally"
                      value={cfg.shareDataExternally ? "yes" : "no"}
                      onChange={(v) => updateConfig(ptId, { shareDataExternally: v === "yes" })}
                      options={[
                        { value: "no", label: "No" },
                        { value: "yes", label: "Yes" },
                      ]}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {selectedPartnerTypes.length === 0 && (
          <p className="py-6 text-center text-sm text-[#777]">
            Click a partner role above to configure it.
          </p>
        )}
      </div>

      {dynamicFieldsConfig.length > 0 && (
        <>
          <div className="border-t border-[#d9d9d9] px-6 py-4">
            <h3 className="text-sm font-semibold text-[#222]">Additional Information</h3>
            <p className="mt-0.5 text-xs text-[#777]">
              Fill in the additional fields required for the selected partner roles.
            </p>
          </div>
          <div className="grid grid-cols-1 gap-x-6 gap-y-4 p-6 pt-2 sm:grid-cols-2 lg:grid-cols-3">
            {dynamicFieldsConfig.map((config) => (
              <InputField
                key={config.id}
                label={config.fieldName + (config.isRequired ? " *" : "")}
                value={(dynamicFieldValues[config.id] as string) || ""}
                onChange={(v) => {
                  const next = { ...dynamicFieldValues, [config.id]: v }
                  setDynamicFieldValues(next)
                }}
                type={config.fieldType === "DATE" ? "date" : config.fieldType === "NUMBER" ? "number" : "text"}
              />
            ))}
          </div>
        </>
      )}
    </>
  )
}

/* ── Branch multi-select with search ── */
function BranchSelect({
  selected,
  options,
  onChange,
}: {
  selected: string[]
  options: { value: string; label: string }[]
  onChange: (vals: string[]) => void
}) {
  const [query, setQuery] = useState("")
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener("mousedown", handleClick)
    return () => document.removeEventListener("mousedown", handleClick)
  }, [])

  const filtered = query
    ? options.filter((b) => !selected.includes(b.value) && b.label.toLowerCase().includes(query.toLowerCase()))
    : options.filter((b) => !selected.includes(b.value))

  return (
    <div ref={ref} className="relative">
      <label className="mb-1 block text-sm font-medium text-[#222]">Branches</label>
      {selected.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-1.5">
          {selected.map((id) => {
            const b = options.find((o) => o.value === id)
            return (
              <span key={id} className="inline-flex items-center gap-1 rounded-full bg-[#111]/10 text-[#222] px-2.5 py-0.5 text-xs font-medium">
                {b?.label ?? id}
                <button
                  type="button"
                  onClick={() => onChange(selected.filter((v) => v !== id))}
                  className="hover:text-[#111]"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            )
          })}
        </div>
      )}
      <div className="relative">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-[#777] pointer-events-none" />
        <input
          type="text"
          placeholder="Search branches..."
          value={query}
          onChange={(e) => { setQuery(e.target.value); setOpen(true) }}
          onFocus={() => setOpen(true)}
          className="w-full rounded-lg border border-[#d7d7d7] bg-white text-[#222] pl-9 pr-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#111]/10"
        />
      </div>
      {open && filtered.length > 0 && (
        <div className="absolute z-20 mt-1 w-full rounded-lg border border-[#d9d9d9] bg-white shadow-lg max-h-48 overflow-y-auto">
          {filtered.map((b) => (
            <button
              key={b.value}
              type="button"
              onClick={() => { onChange([...selected, b.value]); setQuery(""); setOpen(false) }}
              className="w-full text-left px-3 py-2 text-sm hover:bg-[#f7f7f7] transition-colors"
            >
              {b.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function StepContactRisk({
  form,
  update,
  politicalRiskList,
  amlRiskList,
  contacts,
  setContacts,
  bankAccounts,
  setBankAccounts,
  contactRequirements,
  bankRequirements,
  defaultCurrency,
}: {
  form: FormState
  update: <K extends keyof FormState>(k: K, v: FormState[K]) => void
  politicalRiskList: { options: { value: string; label: string }[] }
  amlRiskList: { options: { value: string; label: string }[] }
  contacts: ContactDraft[]
  setContacts: Dispatch<SetStateAction<ContactDraft[]>>
  bankAccounts: BankDraft[]
  setBankAccounts: Dispatch<SetStateAction<BankDraft[]>>
  contactRequirements: PartnerTypeContactRequirement[]
  bankRequirements: PartnerTypeBankRequirement[]
  defaultCurrency: string
}) {
  const addContact = (contactType = contactRequirements[0]?.contactType || "SECONDARY") => {
    setContacts((current) => [...current, {
      contactType,
      firstName: "",
      lastName: "",
      email: "",
      phone: "",
      mobile: "",
      designation: "",
      isPrimary: current.length === 0,
      notes: "",
    }])
  }
  const addBankAccount = () => {
    setBankAccounts((current) => [...current, {
      bankName: "",
      branchName: "",
      accountName: "",
      accountNumber: "",
      swiftCode: "",
      iban: "",
      currency: defaultCurrency,
      isPrimary: current.length === 0,
      notes: "",
    }])
  }
  return (
    <>
      <div className="border-b border-[#d9d9d9] px-6 py-4">
        <h2 className="text-base font-semibold text-[#222]">Contact Information</h2>
        <p className="mt-0.5 text-xs text-[#777]">Provide the primary contact details, configured contacts, bank accounts, and risk assessment information.</p>
      </div>
      <div className="grid grid-cols-1 gap-x-6 gap-y-4 p-6 sm:grid-cols-2 lg:grid-cols-3">
        <InputField label="Email *" type="email" value={form.email} onChange={(v) => update("email", v)} />
        <InputField label="Mobile Number *" value={form.mobileNumber} onChange={(v) => update("mobileNumber", v)} />
        <InputField label="Telephone" value={form.telephoneNumber} onChange={(v) => update("telephoneNumber", v)} />
        <TextAreaField label="Physical Address" value={form.physicalAddress} onChange={(v) => update("physicalAddress", v)} colSpan={3} />
        <TextAreaField label="Postal Address" value={form.postalAddress} onChange={(v) => update("postalAddress", v)} colSpan={3} />
      </div>

      <div className="border-t border-[#d9d9d9] px-6 py-4 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-[#222]">Required contacts</h3>
          <p className="mt-0.5 text-xs text-[#777]">Add one contact for every configured required contact type.</p>
        </div>
        <button type="button" onClick={() => addContact()} className="inline-flex items-center gap-2 rounded-lg border border-[#cfcfcf] px-3 py-2 text-xs font-semibold text-[#222] hover:bg-[#f5f5f5]"><Plus className="h-3.5 w-3.5" /> Add contact</button>
      </div>
      <div className="space-y-4 p-6 pt-3">
        {contacts.map((contact, index) => (
          <div key={contact.id || index} className="rounded-lg border border-[#e0e0e0] p-4">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-[0.12em] text-[#666]">Contact {index + 1}</span>
              {!contact.id && <button type="button" onClick={() => setContacts((current) => current.filter((_, itemIndex) => itemIndex !== index))} className="text-[#666] hover:text-[#111]" aria-label="Remove contact"><Trash2 className="h-4 w-4" /></button>}
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <SelectField label="Contact type" value={contact.contactType} onChange={(value) => setContacts((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, contactType: value } : item))} options={contactRequirements.length > 0 ? contactRequirements.map((item) => ({ value: item.contactType, label: item.contactType })) : [{ value: "SECONDARY", label: "Secondary" }, { value: "BILLING", label: "Billing" }, { value: "TECHNICAL", label: "Technical" }, { value: "OTHER", label: "Other" }]} />
              <InputField label="First name" value={contact.firstName} onChange={(value) => setContacts((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, firstName: value } : item))} />
              <InputField label="Last name" value={contact.lastName} onChange={(value) => setContacts((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, lastName: value } : item))} />
              <InputField label="Designation" value={contact.designation} onChange={(value) => setContacts((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, designation: value } : item))} />
              <InputField label="Email" type="email" value={contact.email} onChange={(value) => setContacts((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, email: value } : item))} />
              <InputField label="Phone" value={contact.phone} onChange={(value) => setContacts((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, phone: value } : item))} />
              <InputField label="Mobile" value={contact.mobile} onChange={(value) => setContacts((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, mobile: value } : item))} />
              <label className="flex items-center gap-2 self-end pb-2 text-xs text-[#555]"><input type="checkbox" checked={contact.isPrimary} onChange={(event) => setContacts((current) => current.map((item, itemIndex) => ({ ...item, isPrimary: itemIndex === index ? event.target.checked : event.target.checked ? false : item.isPrimary })))} /> Primary contact</label>
            </div>
          </div>
        ))}
        {contacts.length === 0 && <p className="rounded-lg border border-dashed border-[#d8d8d8] px-4 py-5 text-center text-xs text-[#777]">No additional contacts added yet.</p>}
      </div>

      <div className="border-t border-[#d9d9d9] px-6 py-4 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-[#222]">Bank accounts</h3>
          <p className="mt-0.5 text-xs text-[#777]">{bankRequirements.length > 0 ? "Add the account required by the selected partner role." : "Add settlement details when applicable."}</p>
        </div>
        <button type="button" onClick={addBankAccount} className="inline-flex items-center gap-2 rounded-lg border border-[#cfcfcf] px-3 py-2 text-xs font-semibold text-[#222] hover:bg-[#f5f5f5]"><Plus className="h-3.5 w-3.5" /> Add bank account</button>
      </div>
      <div className="space-y-4 p-6 pt-3">
        {bankAccounts.map((account, index) => (
          <div key={account.id || index} className="rounded-lg border border-[#e0e0e0] p-4">
            <div className="mb-3 flex items-center justify-between"><span className="text-xs font-semibold uppercase tracking-[0.12em] text-[#666]">Bank account {index + 1}</span>{!account.id && <button type="button" onClick={() => setBankAccounts((current) => current.filter((_, itemIndex) => itemIndex !== index))} className="text-[#666] hover:text-[#111]" aria-label="Remove bank account"><Trash2 className="h-4 w-4" /></button>}</div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <InputField label="Bank name" value={account.bankName} onChange={(value) => setBankAccounts((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, bankName: value } : item))} />
              <InputField label="Branch" value={account.branchName} onChange={(value) => setBankAccounts((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, branchName: value } : item))} />
              <InputField label="Account name" value={account.accountName} onChange={(value) => setBankAccounts((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, accountName: value } : item))} />
              <InputField label="Account number" value={account.accountNumber} onChange={(value) => setBankAccounts((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, accountNumber: value } : item))} />
              <InputField label="Currency" value={account.currency} onChange={(value) => setBankAccounts((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, currency: value.toUpperCase() } : item))} />
              <InputField label="SWIFT code" value={account.swiftCode} onChange={(value) => setBankAccounts((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, swiftCode: value } : item))} />
              <InputField label="IBAN" value={account.iban} onChange={(value) => setBankAccounts((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, iban: value } : item))} />
              <label className="flex items-center gap-2 self-end pb-2 text-xs text-[#555]"><input type="checkbox" checked={account.isPrimary} onChange={(event) => setBankAccounts((current) => current.map((item, itemIndex) => ({ ...item, isPrimary: itemIndex === index ? event.target.checked : item.isPrimary })))} /> Primary account</label>
            </div>
          </div>
        ))}
      </div>

      <div className="border-t border-[#d9d9d9] px-6 py-4"><h3 className="text-sm font-semibold text-[#222]">Risk Assessment</h3></div>
      <div className="grid grid-cols-1 gap-x-6 gap-y-4 p-6 pt-2 sm:grid-cols-2">
        <SelectField label="Political Risk" value={form.politicalRisk} onChange={(v) => update("politicalRisk", v)} options={politicalRiskList.options} />
        <SelectField label="AML Risk" value={form.amlRisk} onChange={(v) => update("amlRisk", v)} options={amlRiskList.options} />
      </div>
    </>
  )
}

function StepDocuments({
  isEdit,
  docs,
  documentRequirements,
  documentTypeList,
  onUpload,
  onDelete,
  onVerify,
}: {
  isEdit: boolean
  docs: ApplicationDocument[]
  documentRequirements: PartnerTypeDocumentRequirement[]
  documentTypeList: { options: { value: string; label: string }[] }
  onUpload: (file: File, docType: string) => Promise<void>
  onDelete: (docId: string) => Promise<void>
  onVerify: (docId: string) => Promise<void>
}) {
  return (
    <>
      <div className="border-b border-[#d9d9d9] px-6 py-4">
        <h2 className="flex items-center gap-2 text-base font-semibold text-[#222]">
          <FileCheck className="h-5 w-5 text-[#222]" />
          Documents
        </h2>
        <p className="mt-0.5 text-xs text-[#777]">
          {isEdit
            ? documentRequirements.length > 0
              ? `Upload and verify: ${documentRequirements.filter((item) => item.isRequired).map((item) => item.code).join(", ") || "configured evidence"}.`
              : "Upload required documents for this application. You can upload multiple documents."
            : "Documents can be uploaded after saving the application draft."}
        </p>
      </div>
      <div className="p-6">
        {isEdit ? (
          <>
            <div className="mb-4 flex gap-3">
              <select
                id="docType"
                className="rounded-lg border border-[#d7d7d7] bg-white px-3 py-2 text-sm text-[#222]"
              >
                {(documentRequirements.length > 0
                  ? documentRequirements.map((requirement) => ({ value: requirement.code, label: requirement.description ? `${requirement.code} — ${requirement.description}` : requirement.code }))
                  : (documentTypeList.options ?? [])
                ).map((d) => (
                  <option key={d.value} value={d.value}>{d.label}</option>
                ))}
              </select>
              <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-[#d7d7d7] bg-white px-4 py-2 text-sm font-medium text-[#222] transition hover:bg-[#f3f3f3]">
                <Upload className="h-4 w-4" />
                Upload
                <input
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0]
                    const sel = document.getElementById("docType") as HTMLSelectElement | null
                    if (file && sel) {
                      onUpload(file, sel.value)
                      e.target.value = ""
                    }
                  }}
                />
              </label>
            </div>

            {docs.length > 0 ? (
              <ul className="divide-y divide-border">
                {docs.map((d) => (
                  <li key={d.id} className="flex items-center gap-3 py-3">
                    <FileText className="h-4 w-4 shrink-0 text-[#777]" />
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-medium text-[#222]">{d.documentName}</div>
                      <div className="text-xs text-[#777]">
                        {d.fileSize ? ` · ${(d.fileSize / 1024).toFixed(0)} KB` : ""}
                      </div>
                    </div>
                    {d.isVerified ? (
                      <span className="inline-flex items-center gap-1 text-xs font-semibold text-[#222]"><CheckCircle2 className="h-4 w-4 shrink-0" /> Verified</span>
                    ) : (
                      <button type="button" onClick={() => onVerify(d.id)} className="rounded-md border border-[#cfcfcf] px-2 py-1 text-xs font-semibold text-[#222] hover:bg-[#f3f3f3]">Verify</button>
                    )}
                    <button type="button" onClick={() => onDelete(d.id)} className="rounded p-1 text-[#777] hover:text-[#111]">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="py-8 text-center">
                <FileText className="mx-auto mb-2 h-8 w-8 text-[#777]/40" />
                <p className="text-sm text-[#777]">No documents uploaded yet.</p>
              </div>
            )}
          </>
        ) : (
          <div className="py-8 text-center">
            <FileCheck className="mx-auto mb-2 h-8 w-8 text-[#777]/40" />
            <p className="text-sm font-medium text-[#222]">Save the application first</p>
            <p className="mt-1 text-xs text-[#777]">
              Documents can be uploaded after saving this application as a draft.
            </p>
          </div>
        )}
      </div>
    </>
  )
}

function StepReview({
  form,
  isCorporate,
  selectedPartnerTypes,
  systemPartnerTypeList,
  docs,
  isEdit,
}: {
  form: FormState
  isCorporate: boolean
  selectedPartnerTypes: string[]
  systemPartnerTypeList: { options: { value: string; label: string }[] }
  docs: ApplicationDocument[]
  isEdit: boolean
}) {
  const ptLabels = selectedPartnerTypes.map((id) => {
    const found = systemPartnerTypeList.options.find((o) => o.value === id)
    return found?.label || id
  })

  return (
    <>
      <div className="border-b border-[#d9d9d9] px-6 py-4">
        <h2 className="flex items-center gap-2 text-base font-semibold text-[#222]">
          <Eye className="h-5 w-5 text-[#222]" />
          Review & Submit
        </h2>
        <p className="mt-0.5 text-xs text-[#777]">
          Please review all information before submitting. Once submitted, changes will require a new review cycle.
        </p>
      </div>
      <div className="p-6 space-y-6">
        {/* Client Type */}
        <div>
          <h3 className="text-sm font-semibold text-[#222] mb-2">Client Type</h3>
          <div className="rounded-lg border border-[#d9d9d9] bg-[#fafafa] px-4 py-3">
            <div className="flex items-center gap-2">
              {isCorporate ? <Building2 className="h-4 w-4 text-[#777]" /> : <User className="h-4 w-4 text-[#777]" />}
              <span className="text-sm font-medium text-[#222]">{isCorporate ? "Corporate" : "Individual"}</span>
            </div>
          </div>
        </div>

        {/* Info Summary */}
        <div>
          <h3 className="text-sm font-semibold text-[#222] mb-2">
            {isCorporate ? "Company Information" : "Personal Information"}
          </h3>
          <div className="grid grid-cols-2 gap-x-6 gap-y-2 rounded-lg border border-[#d9d9d9] bg-[#fafafa] px-4 py-3">
            {isCorporate ? (
              <>
                <ReviewField label="Company Name" value={form.companyName} />
                <ReviewField label="TIN" value={form.tinNumber} />
                <ReviewField label="Incorporation Date" value={form.incorporationDate} />
                <ReviewField label="Industry" value={form.industry} />
                <ReviewField label="Contact Person" value={form.contactPerson} />
                <ReviewField label="Contact Phone" value={form.contactPersonPhone} />
                <ReviewField label="Contact Email" value={form.contactPersonEmail} />
              </>
            ) : (
              <>
                <ReviewField label="Title" value={form.title} />
                <ReviewField label="First Name" value={form.firstName} />
                <ReviewField label="Other Name" value={form.otherName} />
                <ReviewField label="Surname" value={form.surname} />
                <ReviewField label="ID Type" value={form.identificationType} />
                <ReviewField label="ID Number" value={form.identificationNumber} />
                <ReviewField label="Gender" value={form.gender} />
                <ReviewField label="Date of Birth" value={form.dateOfBirth} />
                <ReviewField label="Marital Status" value={form.maritalStatus} />
                <ReviewField label="Occupation" value={form.occupation} />
                <ReviewField label="Nationality" value={form.nationality} />
              </>
            )}
          </div>
        </div>

        {/* Partner Roles */}
        <div>
          <h3 className="text-sm font-semibold text-[#222] mb-2">Partner Roles</h3>
          <div className="rounded-lg border border-[#d9d9d9] bg-[#fafafa] px-4 py-3">
            {ptLabels.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {ptLabels.map((label) => (
                  <span key={label} className="rounded-full bg-[#111]/10 px-3 py-1 text-xs font-medium text-[#222]">
                    {label}
                  </span>
                ))}
              </div>
            ) : (
              <span className="text-sm text-[#777]">None selected</span>
            )}
          </div>
        </div>

        {/* Contact */}
        <div>
          <h3 className="text-sm font-semibold text-[#222] mb-2">Contact & Risk</h3>
          <div className="grid grid-cols-2 gap-x-6 gap-y-2 rounded-lg border border-[#d9d9d9] bg-[#fafafa] px-4 py-3">
            <ReviewField label="Email" value={form.email} />
            <ReviewField label="Mobile" value={form.mobileNumber} />
            <ReviewField label="Telephone" value={form.telephoneNumber} />
            <ReviewField label="Political Risk" value={form.politicalRisk} />
            <ReviewField label="AML Risk" value={form.amlRisk} />
            <ReviewField label="Physical Address" value={form.physicalAddress} colSpan={2} />
            <ReviewField label="Postal Address" value={form.postalAddress} colSpan={2} />
          </div>
        </div>

        {/* Documents */}
        <div>
          <h3 className="text-sm font-semibold text-[#222] mb-2">Documents</h3>
          <div className="rounded-lg border border-[#d9d9d9] bg-[#fafafa] px-4 py-3">
            {isEdit && docs.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {docs.map((d) => (
                  <span key={d.id} className="inline-flex items-center gap-1 rounded-full bg-muted px-3 py-1 text-xs text-[#222]">
                    <FileText className="h-3 w-3" />
                    {d.documentName}
                    {d.isVerified && <CheckCircle2 className="h-3 w-3 text-success" />}
                  </span>
                ))}
              </div>
            ) : (
              <span className="text-sm text-[#777]">No documents uploaded</span>
            )}
          </div>
        </div>
      </div>
    </>
  )
}

function ReviewField({ label, value, colSpan }: { label: string; value?: string; colSpan?: number }) {
  return (
    <div className={colSpan === 2 ? "col-span-2" : ""}>
      <span className="text-xs text-[#777]">{label}</span>
      <p className="text-sm font-medium text-[#222]">{value || "—"}</p>
    </div>
  )
}

/* ================================================================== */
/*  Field helpers                                                      */
/* ================================================================== */

function InputField({ label, value, onChange, type = "text", colSpan }: {
  label: string; value: string; onChange: (v: string) => void; type?: string; colSpan?: number
}) {
  return (
    <div className={colSpan === 3 ? "sm:col-span-2 lg:col-span-3" : ""}>
      <label className="mb-1.5 block text-sm font-medium text-[#222]">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-[#d7d7d7] bg-white px-3 py-2.5 text-sm text-[#222] outline-none transition placeholder:text-[#999] focus:border-[#111] focus:ring-2 focus:ring-[#111]/10"
      />
    </div>
  )
}

function SelectField({ label, value, onChange, options, placeholder, colSpan }: {
  label: string; value: string; onChange: (v: string) => void
  options: { value: string; label: string }[]; placeholder?: string; colSpan?: number
}) {
  return (
    <div className={colSpan === 3 ? "sm:col-span-2 lg:col-span-3" : ""}>
      <label className="mb-1.5 block text-sm font-medium text-[#222]">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-[#d7d7d7] bg-white px-3 py-2.5 text-sm text-[#222] outline-none transition focus:border-[#111] focus:ring-2 focus:ring-[#111]/10"
      >
        {placeholder && <option value="">{placeholder}</option>}
        {options?.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </div>
  )
}

function TextAreaField({ label, value, onChange, colSpan }: {
  label: string; value: string; onChange: (v: string) => void; colSpan?: number
}) {
  return (
    <div className={colSpan === 3 ? "sm:col-span-2 lg:col-span-3" : ""}>
      <label className="mb-1.5 block text-sm font-medium text-[#222]">{label}</label>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={2}
        className="w-full rounded-lg border border-[#d7d7d7] bg-white px-3 py-2.5 text-sm text-[#222] outline-none transition placeholder:text-[#999] focus:border-[#111] focus:ring-2 focus:ring-[#111]/10"
      />
    </div>
  )
}

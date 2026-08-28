import { http, HttpResponse } from "msw"

const CLAIMS_BASE = "/api/v1/ol/claims"
const POLICY_CLAIMS_BASE = "/api/v1/ol/policies"

export type ClaimMockItem = {
  id: string
  benefit_type: string
  sum_assured: string
  calculated_amount: string
  approved_amount: string | null
  adjustment_reason: string
}

export type ClaimMockDocument = {
  id: string
  document_type: string
  file_reference: string
  mandatory: boolean
  uploaded_by_display: string
  uploaded_at: string | null
}

export type ClaimMockNote = {
  id: string
  note_text: string
  author_display: string
  source_channel: string
  created_at: string
}

export type ClaimMockRequisition = {
  id: string
  requisition_number: string
  amount: string
  bank_details: Record<string, unknown>
  payment_requisition_number: string | null
  approval_request_status: string | null
  approval_required: boolean
  narration: string
  status: string
  status_display: string
  created_at: string
  updated_at: string
}

export type ClaimMockRow = {
  id: string
  claim_number: string
  policy_id: string
  policy_number: string
  policyholder_name: string
  policyholder_display: string
  product_display: string
  branch_display: string
  currency: string
  claim_type: string
  claim_date: string
  admitted_date: string | null
  status: string
  status_display: string
  fraud_flag: boolean
  fraud_flag_reason: string
  amount: string
  cause_of_claim: string
  description: string
  medical_status: string
  medical_result: string
  medical_reason: string
  medical_loading_factor: string | null
  claimant: {
    id: string
    claimant_type: string
    relationship: string
    name: string
    identity_number: string
    age: number | null
    gender: string
  } | null
  items: ClaimMockItem[]
  documents: ClaimMockDocument[]
  file_notes: ClaimMockNote[]
  requisition: ClaimMockRequisition | null
  loan_offset: {
    gross_amount: string
    offset_amount: string
    net_payout: string
    status: string
  } | null
  allowed_actions: string[]
  created_at: string
  updated_at: string
}

const initialClaims: ClaimMockRow[] = [
  {
    id: "claim-registered-1",
    claim_number: "OL-CLM-2026-000001",
    policy_id: "policy-aman-1",
    policy_number: "ZIC-OL-2026-000001",
    policyholder_name: "Amani Salum",
    policyholder_display: "P-000001 — Amani Salum",
    product_display: "OL_EDU_GROWTH — Elimu Bora Growth Plan",
    branch_display: "ZNZ-MAIN — Zanzibar Main Branch",
    currency: "TZS",
    claim_type: "MATERNITY",
    claim_date: "2026-08-18",
    admitted_date: null,
    status: "REGISTERED",
    status_display: "Registered",
    fraud_flag: false,
    fraud_flag_reason: "",
    amount: "250000.00",
    cause_of_claim: "Maternity hospitalisation",
    description: "Admitted for delivery and postnatal care at Mnazi Mmoja Hospital.",
    medical_status: "NOT_REQUIRED",
    medical_result: "",
    medical_reason: "",
    medical_loading_factor: null,
    claimant: { id: "claimant-aman-1", claimant_type: "POLICYHOLDER", relationship: "Self", name: "Amani Salum", identity_number: "19850102-54321-00001-9", age: 41, gender: "M" },
    items: [{ id: "claim-item-1", benefit_type: "MATERNITY_BENEFIT", sum_assured: "250000.00", calculated_amount: "250000.00", approved_amount: null, adjustment_reason: "" }],
    documents: [],
    file_notes: [{ id: "note-reg-1", note_text: "Claim admitted from policy claim history. Awaiting supporting documents.", author_display: "Claims Officer — Neema K.", source_channel: "API", created_at: "2026-08-18T09:00:00Z" }],
    requisition: null,
    loan_offset: null,
    allowed_actions: ["view", "assess", "cancel", "print"],
    created_at: "2026-08-18T09:00:00Z",
    updated_at: "2026-08-18T09:00:00Z",
  },
  {
    id: "claim-pending-medical-1",
    claim_number: "OL-CLM-2026-000002",
    policy_id: "policy-fatma-1",
    policy_number: "ZIC-OL-2025-000021",
    policyholder_name: "Fatma Ali",
    policyholder_display: "P-000021 — Fatma Ali",
    product_display: "OL_TERM_FAMILY — ZIC Term Assurance Family",
    branch_display: "ZNZ-NORTH — North Region Branch",
    currency: "TZS",
    claim_type: "CRITICAL_ILLNESS",
    claim_date: "2026-08-12",
    admitted_date: "2026-08-12",
    status: "PENDING_MEDICAL",
    status_display: "Pending Medical",
    fraud_flag: false,
    fraud_flag_reason: "",
    amount: "1500000.00",
    cause_of_claim: "Diagnosed critical illness",
    description: "Myocardial infarction confirmed by cardiologist report.",
    medical_status: "REQUESTED",
    medical_result: "",
    medical_reason: "",
    medical_loading_factor: null,
    claimant: { id: "claimant-fatma-1", claimant_type: "INSURED", relationship: "Insured", name: "Fatma Ali", identity_number: "19920311-87654-00004-2", age: 34, gender: "F" },
    items: [{ id: "claim-item-2", benefit_type: "CI_BENEFIT", sum_assured: "1500000.00", calculated_amount: "1500000.00", approved_amount: null, adjustment_reason: "" }],
    documents: [{ id: "doc-ci-1", document_type: "MEDICAL_REPORT", file_reference: "DR-MR-2026-008812", mandatory: true, uploaded_by_display: "Claims Officer — Neema K.", uploaded_at: "2026-08-12T10:00:00Z" }],
    file_notes: [{ id: "note-med-1", note_text: "Medical review requested pending specialist report.", author_display: "Claims Officer — Neema K.", source_channel: "API", created_at: "2026-08-12T10:00:00Z" }],
    requisition: null,
    loan_offset: null,
    allowed_actions: ["view", "cancel", "print"],
    created_at: "2026-08-12T09:00:00Z",
    updated_at: "2026-08-12T10:00:00Z",
  },
  {
    id: "claim-assessed-1",
    claim_number: "OL-CLM-2026-000003",
    policy_id: "policy-juma-1",
    policy_number: "ZIC-OL-2024-000044",
    policyholder_name: "Juma Hassan",
    policyholder_display: "P-000044 — Juma Hassan",
    product_display: "OL_LIFE_WHOLE — ZIC Whole Life Plan",
    branch_display: "DSM-CENTRAL — Dar es Salaam Central Branch",
    currency: "TZS",
    claim_type: "HOSPITAL_CASH",
    claim_date: "2026-07-20",
    admitted_date: "2026-07-20",
    status: "ASSESSED",
    status_display: "Assessed",
    fraud_flag: false,
    fraud_flag_reason: "",
    amount: "800000.00",
    cause_of_claim: "Hospitalisation benefit",
    description: "Five-day hospital admission for malaria treatment.",
    medical_status: "COMPLETED",
    medical_result: "CLEARED",
    medical_reason: "Specialist report confirms the diagnosis.",
    medical_loading_factor: null,
    claimant: { id: "claimant-juma-1", claimant_type: "POLICYHOLDER", relationship: "Self", name: "Juma Hassan", identity_number: "19881222-11223-00009-7", age: 37, gender: "M" },
    items: [{ id: "claim-item-3", benefit_type: "HOSPITAL_CASH", sum_assured: "800000.00", calculated_amount: "800000.00", approved_amount: "760000.00", adjustment_reason: "Admitted for 5 days; benefit applied at full rate." }],
    documents: [{ id: "doc-hc-1", document_type: "HOSPITAL_DISCHARGE", file_reference: "DR-DC-2026-003301", mandatory: true, uploaded_by_display: "Claims Officer — Neema K.", uploaded_at: "2026-07-20T12:00:00Z" }],
    file_notes: [{ id: "note-as-1", note_text: "Benefit approved after medical clearance.", author_display: "Claims Assessor — Baraka M.", source_channel: "API", created_at: "2026-07-21T09:00:00Z" }],
    requisition: null,
    loan_offset: null,
    allowed_actions: ["view", "raise-requisition", "cancel", "print"],
    created_at: "2026-07-20T09:00:00Z",
    updated_at: "2026-07-21T09:00:00Z",
  },
  {
    id: "claim-requisitioned-1",
    claim_number: "OL-CLM-2026-000004",
    policy_id: "policy-zekia-1",
    policy_number: "ZIC-OL-2024-000056",
    policyholder_name: "Zekia Mwinyi",
    policyholder_display: "P-000056 — Zekia Mwinyi",
    product_display: "OL_TERM_FAMILY — ZIC Term Assurance Family",
    branch_display: "DSM-CENTRAL — Dar es Salaam Central Branch",
    currency: "TZS",
    claim_type: "HOSPITAL_CASH",
    claim_date: "2026-07-10",
    admitted_date: "2026-07-10",
    status: "REQUISITIONED",
    status_display: "Requisitioned",
    fraud_flag: false,
    fraud_flag_reason: "",
    amount: "1200000.00",
    cause_of_claim: "Surgical procedure",
    description: "Emergency appendectomy with post-operative care.",
    medical_status: "COMPLETED",
    medical_result: "CLEARED",
    medical_reason: "Surgical notes confirm the procedure.",
    medical_loading_factor: null,
    claimant: { id: "claimant-zekia-1", claimant_type: "POLICYHOLDER", relationship: "Self", name: "Zekia Mwinyi", identity_number: "19750708-44556-00012-3", age: 51, gender: "F" },
    items: [{ id: "claim-item-4", benefit_type: "HOSPITAL_CASH", sum_assured: "1200000.00", calculated_amount: "1200000.00", approved_amount: "1140000.00", adjustment_reason: "Approved per 10-day admission at day rate." }],
    documents: [{ id: "doc-surg-1", document_type: "HOSPITAL_DISCHARGE", file_reference: "DR-DC-2026-002890", mandatory: true, uploaded_by_display: "Claims Officer — Neema K.", uploaded_at: "2026-07-10T11:00:00Z" }],
    file_notes: [{ id: "note-rq-1", note_text: "Requisition raised; awaiting finance approval.", author_display: "Claims Officer — Neema K.", source_channel: "API", created_at: "2026-07-11T08:00:00Z" }],
    requisition: { id: "req-claim-4", requisition_number: "REQ-OL-2026-000101", amount: "1140000.00", bank_details: { account_holder: "Zekia Mwinyi", account_number: "0150-0123-4567", bank_name: "CRDB Bank" }, payment_requisition_number: "PR-2026-000221", approval_request_status: "PENDING", approval_required: true, narration: "Claim settlement payment", status: "PENDING", status_display: "Pending", created_at: "2026-07-11T08:00:00Z", updated_at: "2026-07-11T08:00:00Z" },
    loan_offset: null,
    allowed_actions: ["view", "settle", "print"],
    created_at: "2026-07-10T09:00:00Z",
    updated_at: "2026-07-11T08:00:00Z",
  },
  {
    id: "claim-approved-1",
    claim_number: "OL-CLM-2026-000005",
    policy_id: "policy-mariam-1",
    policy_number: "ZIC-OL-2023-000078",
    policyholder_name: "Mariam Juma",
    policyholder_display: "P-000078 — Mariam Juma",
    product_display: "OL_LIFE_WHOLE — ZIC Whole Life Plan",
    branch_display: "ZNZ-MAIN — Zanzibar Main Branch",
    currency: "TZS",
    claim_type: "CRITICAL_ILLNESS",
    claim_date: "2026-06-25",
    admitted_date: "2026-06-25",
    status: "APPROVED",
    status_display: "Approved",
    fraud_flag: false,
    fraud_flag_reason: "",
    amount: "5000000.00",
    cause_of_claim: "Cancer diagnosis",
    description: "Breast cancer confirmed; treatment plan initiated.",
    medical_status: "COMPLETED",
    medical_result: "LOADING",
    medical_reason: "Pre-existing condition loading of 25%.",
    medical_loading_factor: "1.25",
    claimant: { id: "claimant-mariam-1", claimant_type: "POLICYHOLDER", relationship: "Self", name: "Mariam Juma", identity_number: "19800315-77889-00007-1", age: 46, gender: "F" },
    items: [{ id: "claim-item-5", benefit_type: "CI_BENEFIT", sum_assured: "5000000.00", calculated_amount: "5000000.00", approved_amount: "4000000.00", adjustment_reason: "Loading factor 1.25 applied to sum assured." }],
    documents: [{ id: "doc-ci-2", document_type: "MEDICAL_REPORT", file_reference: "DR-MR-2026-006611", mandatory: true, uploaded_by_display: "Claims Officer — Neema K.", uploaded_at: "2026-06-25T13:00:00Z" }, { id: "doc-ci-3", document_type: "HOSPITAL_DISCHARGE", file_reference: "DR-DC-2026-002101", mandatory: true, uploaded_by_display: "Claims Officer — Neema K.", uploaded_at: "2026-06-26T09:00:00Z" }],
    file_notes: [{ id: "note-ap-1", note_text: "Finance approval granted; awaiting settlement.", author_display: "Finance Manager — Yusuf A.", source_channel: "API", created_at: "2026-06-27T10:00:00Z" }],
    requisition: { id: "req-claim-5", requisition_number: "REQ-OL-2026-000098", amount: "4000000.00", bank_details: { account_holder: "Mariam Juma", account_number: "2050-0777-8899", bank_name: "NMB Bank" }, payment_requisition_number: "PR-2026-000210", approval_request_status: "APPROVED", approval_required: true, narration: "Claim settlement payment", status: "APPROVED", status_display: "Approved", created_at: "2026-06-26T12:00:00Z", updated_at: "2026-06-27T10:00:00Z" },
    loan_offset: null,
    allowed_actions: ["view", "settle", "print"],
    created_at: "2026-06-25T09:00:00Z",
    updated_at: "2026-06-27T10:00:00Z",
  },
  {
    id: "claim-settled-1",
    claim_number: "OL-CLM-2026-000006",
    policy_id: "policy-said-1",
    policy_number: "ZIC-OL-2023-000090",
    policyholder_name: "Said Omar",
    policyholder_display: "P-000090 — Said Omar",
    product_display: "OL_TERM_FAMILY — ZIC Term Assurance Family",
    branch_display: "ZNZ-NORTH — North Region Branch",
    currency: "TZS",
    claim_type: "HOSPITAL_CASH",
    claim_date: "2026-05-02",
    admitted_date: "2026-05-02",
    status: "SETTLED",
    status_display: "Settled",
    fraud_flag: false,
    fraud_flag_reason: "",
    amount: "600000.00",
    cause_of_claim: "Hospitalisation benefit",
    description: "Four-day admission for dengue fever.",
    medical_status: "COMPLETED",
    medical_result: "CLEARED",
    medical_reason: "Laboratory results confirm dengue.",
    medical_loading_factor: null,
    claimant: { id: "claimant-said-1", claimant_type: "POLICYHOLDER", relationship: "Self", name: "Said Omar", identity_number: "19770210-33445-00005-5", age: 49, gender: "M" },
    items: [{ id: "claim-item-6", benefit_type: "HOSPITAL_CASH", sum_assured: "600000.00", calculated_amount: "600000.00", approved_amount: "570000.00", adjustment_reason: "Approved per 4-day admission at day rate." }],
    documents: [{ id: "doc-hc-2", document_type: "HOSPITAL_DISCHARGE", file_reference: "DR-DC-2026-001009", mandatory: true, uploaded_by_display: "Claims Officer — Neema K.", uploaded_at: "2026-05-02T14:00:00Z" }],
    file_notes: [{ id: "note-st-1", note_text: "Settlement confirmed; discharge voucher printed.", author_display: "Finance Officer — Rehema S.", source_channel: "API", created_at: "2026-05-03T09:00:00Z" }],
    requisition: { id: "req-claim-6", requisition_number: "REQ-OL-2026-000088", amount: "570000.00", bank_details: { account_holder: "Said Omar", account_number: "0150-0555-1200", bank_name: "CRDB Bank" }, payment_requisition_number: "PR-2026-000180", approval_request_status: "APPROVED", approval_required: false, narration: "Claim settlement payment", status: "APPROVED", status_display: "Approved", created_at: "2026-05-02T15:00:00Z", updated_at: "2026-05-03T09:00:00Z" },
    loan_offset: { gross_amount: "570000.00", offset_amount: "120000.00", net_payout: "450000.00", status: "APPLIED" },
    allowed_actions: ["view", "print"],
    created_at: "2026-05-02T09:00:00Z",
    updated_at: "2026-05-03T09:00:00Z",
  },
  {
    id: "claim-rejected-1",
    claim_number: "OL-CLM-2026-000007",
    policy_id: "policy-aman-1",
    policy_number: "ZIC-OL-2026-000001",
    policyholder_name: "Amani Salum",
    policyholder_display: "P-000001 — Amani Salum",
    product_display: "OL_EDU_GROWTH — Elimu Bora Growth Plan",
    branch_display: "ZNZ-MAIN — Zanzibar Main Branch",
    currency: "TZS",
    claim_type: "HOSPITAL_CASH",
    claim_date: "2026-04-11",
    admitted_date: null,
    status: "REJECTED",
    status_display: "Rejected",
    fraud_flag: true,
    fraud_flag_reason: "Claim duplicates previously settled hospitalisation benefit.",
    amount: "400000.00",
    cause_of_claim: "Hospitalisation benefit",
    description: "Submitted without a matching hospital admission record.",
    medical_status: "COMPLETED",
    medical_result: "REJECTED",
    medical_reason: "Benefit not covered at date of admission.",
    medical_loading_factor: null,
    claimant: { id: "claimant-aman-2", claimant_type: "DEPENDENT", relationship: "Spouse", name: "Rehema Salum", identity_number: "19881104-11223-00008-8", age: 38, gender: "F" },
    items: [{ id: "claim-item-7", benefit_type: "HOSPITAL_CASH", sum_assured: "400000.00", calculated_amount: "400000.00", approved_amount: null, adjustment_reason: "" }],
    documents: [],
    file_notes: [{ id: "note-rj-1", note_text: "Claim rejected; beneficiary can appeal through the approved governance channel.", author_display: "Claims Assessor — Baraka M.", source_channel: "API", created_at: "2026-04-12T09:00:00Z" }],
    requisition: null,
    loan_offset: null,
    allowed_actions: ["view", "print"],
    created_at: "2026-04-11T09:00:00Z",
    updated_at: "2026-04-12T09:00:00Z",
  },
  {
    id: "claim-cancelled-1",
    claim_number: "OL-CLM-2026-000008",
    policy_id: "policy-aman-1",
    policy_number: "ZIC-OL-2026-000001",
    policyholder_name: "Amani Salum",
    policyholder_display: "P-000001 — Amani Salum",
    product_display: "OL_EDU_GROWTH — Elimu Bora Growth Plan",
    branch_display: "ZNZ-MAIN — Zanzibar Main Branch",
    currency: "TZS",
    claim_type: "HOSPITAL_CASH",
    claim_date: "2026-03-02",
    admitted_date: null,
    status: "CANCELLED",
    status_display: "Cancelled",
    fraud_flag: false,
    fraud_flag_reason: "",
    amount: "350000.00",
    cause_of_claim: "Hospitalisation benefit",
    description: "Cancelled at the policyholder's request before assessment.",
    medical_status: "NOT_REQUIRED",
    medical_result: "",
    medical_reason: "",
    medical_loading_factor: null,
    claimant: { id: "claimant-aman-3", claimant_type: "INSURED", relationship: "Insured", name: "Amani Salum", identity_number: "19850102-54321-00001-9", age: 41, gender: "M" },
    items: [{ id: "claim-item-8", benefit_type: "HOSPITAL_CASH", sum_assured: "350000.00", calculated_amount: "350000.00", approved_amount: null, adjustment_reason: "" }],
    documents: [],
    file_notes: [{ id: "note-cn-1", note_text: "Claim cancelled before any benefit was assessed.", author_display: "Claims Officer — Neema K.", source_channel: "API", created_at: "2026-03-02T10:00:00Z" }],
    requisition: null,
    loan_offset: null,
    allowed_actions: ["view", "print"],
    created_at: "2026-03-02T09:00:00Z",
    updated_at: "2026-03-02T10:00:00Z",
  },
]

const policyOptions = [
  { value: "policy-aman-1", label: "ZIC-OL-2026-000001 — Amani Salum", meta: { policy_number: "ZIC-OL-2026-000001", policyholder_name: "Amani Salum", policyholder_display: "P-000001 — Amani Salum", status: "ACTIVE", currency: "TZS", product_display: "OL_EDU_GROWTH — Elimu Bora Growth Plan" } },
  { value: "policy-fatma-1", label: "ZIC-OL-2025-000021 — Fatma Ali", meta: { policy_number: "ZIC-OL-2025-000021", policyholder_name: "Fatma Ali", policyholder_display: "P-000021 — Fatma Ali", status: "ACTIVE", currency: "TZS", product_display: "OL_TERM_FAMILY — ZIC Term Assurance Family" } },
  { value: "policy-juma-1", label: "ZIC-OL-2024-000044 — Juma Hassan", meta: { policy_number: "ZIC-OL-2024-000044", policyholder_name: "Juma Hassan", policyholder_display: "P-000044 — Juma Hassan", status: "ACTIVE", currency: "TZS", product_display: "OL_LIFE_WHOLE — ZIC Whole Life Plan" } },
  { value: "policy-lapsed-1", label: "ZIC-OL-2023-000011 — Lapsed Policyholder", meta: { policy_number: "ZIC-OL-2023-000011", policyholder_name: "Lapsed Policyholder", policyholder_display: "P-000011 — Lapsed Policyholder", status: "LAPSED", currency: "TZS", product_display: "OL_TERM_FAMILY — ZIC Term Assurance Family" } },
]

const claimTypeOptions = [
  { value: "HOSPITAL_CASH", label: "Hospital Cash", meta: { active: true } },
  { value: "MATERNITY", label: "Maternity Benefit", meta: { active: true } },
  { value: "CRITICAL_ILLNESS", label: "Critical Illness", meta: { active: true } },
  { value: "ACCIDENT", label: "Accident", meta: { active: true } },
  { value: "DEATH", label: "Death", meta: { active: true } },
  { value: "DISABILITY", label: "Disability", meta: { active: true } },
]

const claimReasonOptions = [
  { value: "HOSPITALISATION", label: "Hospitalisation", meta: { active: true } },
  { value: "SURGERY", label: "Surgical procedure", meta: { active: true } },
  { value: "MATERNITY", label: "Maternity / delivery", meta: { active: true } },
  { value: "ILLNESS", label: "Critical illness diagnosis", meta: { active: true } },
  { value: "ACCIDENT", label: "Accidental injury", meta: { active: true } },
]

const benefitOptions: Record<string, { value: string; label: string; meta: Record<string, unknown> }[]> = {
  "policy-aman-1": [{ value: "MATERNITY_BENEFIT", label: "Maternity Benefit — sum assured 250,000.00", meta: { sum_assured: "250000.00", covered: true } }, { value: "HOSPITAL_CASH", label: "Hospital Cash — daily rate", meta: { sum_assured: "100000.00", covered: true } }],
  "policy-fatma-1": [{ value: "CI_BENEFIT", label: "Critical Illness Benefit — sum assured 1,500,000.00", meta: { sum_assured: "1500000.00", covered: true } }],
  "policy-juma-1": [{ value: "HOSPITAL_CASH", label: "Hospital Cash — daily rate", meta: { sum_assured: "160000.00", covered: true } }],
  "policy-mariam-1": [{ value: "CI_BENEFIT", label: "Critical Illness Benefit — sum assured 5,000,000.00", meta: { sum_assured: "5000000.00", covered: true } }],
  "policy-said-1": [{ value: "HOSPITAL_CASH", label: "Hospital Cash — daily rate", meta: { sum_assured: "150000.00", covered: true } }],
  "policy-zekia-1": [{ value: "HOSPITAL_CASH", label: "Hospital Cash — daily rate", meta: { sum_assured: "120000.00", covered: true } }],
}

const memberOptions: Record<string, { value: string; label: string; meta: Record<string, unknown> }[]> = {
  "policy-aman-1": [{ value: "claimant-aman-1", label: "Amani Salum — Policyholder", meta: { claimant_type: "POLICYHOLDER", relationship: "Self", identity_number: "19850102-54321-00001-9" } }, { value: "claimant-aman-2", label: "Rehema Salum — Spouse", meta: { claimant_type: "DEPENDENT", relationship: "Spouse", identity_number: "19881104-11223-00008-8" } }],
  "policy-fatma-1": [{ value: "claimant-fatma-1", label: "Fatma Ali — Insured", meta: { claimant_type: "INSURED", relationship: "Insured", identity_number: "19920311-87654-00004-2" } }],
  "policy-juma-1": [{ value: "claimant-juma-1", label: "Juma Hassan — Policyholder", meta: { claimant_type: "POLICYHOLDER", relationship: "Self", identity_number: "19881222-11223-00009-7" } }],
}

const requiredDocuments = [
  { document_type: "MEDICAL_REPORT", mandatory: true },
  { document_type: "HOSPITAL_DISCHARGE", mandatory: true },
  { document_type: "IDENTITY_DOCUMENT", mandatory: true },
  { document_type: "POLICE_REPORT", mandatory: false },
  { document_type: "DEATH_CERTIFICATE", mandatory: false },
]

let claims = cloneRows(initialClaims)

function cloneRows(rows: ClaimMockRow[]): ClaimMockRow[] {
  return rows.map((row) => ({
    ...row,
    allowed_actions: [...row.allowed_actions],
    items: row.items.map((item) => ({ ...item })),
    documents: row.documents.map((doc) => ({ ...doc })),
    file_notes: row.file_notes.map((note) => ({ ...note })),
    requisition: row.requisition ? { ...row.requisition, bank_details: { ...row.requisition.bank_details } } : null,
    claimant: row.claimant ? { ...row.claimant } : null,
    loan_offset: row.loan_offset ? { ...row.loan_offset } : null,
  }))
}

export function resetClaimMockState() {
  claims = cloneRows(initialClaims)
}

function data<T>(payload: T, status = 200) {
  return HttpResponse.json({ data: payload }, { status })
}

function error(status: number, code: string, message: string, resolutionSteps: string[], fieldErrors: Record<string, string[]> = {}) {
  return HttpResponse.json({ success: false, errorCode: code, message, resolutionSteps, fieldErrors, error: { code, message, details: { resolutionSteps, fieldErrors } } }, { status })
}

function page<T>(rows: T[], url: URL) {
  const pageSize = Math.max(1, Number(url.searchParams.get("page_size") ?? 20))
  const pageNumber = Math.max(1, Number(url.searchParams.get("page") ?? 1))
  const start = (pageNumber - 1) * pageSize
  return { results: rows.slice(start, start + pageSize), count: rows.length, page: pageNumber, page_size: pageSize, next: start + pageSize < rows.length, previous: pageNumber > 1 }
}

function findClaim(id: string) {
  return claims.find((row) => row.id === id)
}

function listFor(row: ClaimMockRow) {
  return {
    id: row.id,
    claim_number: row.claim_number,
    policy_id: row.policy_id,
    policy_number: row.policy_number,
    policyholder_name: row.policyholder_name,
    policyholder_display: row.policyholder_display,
    product_display: row.product_display,
    branch_display: row.branch_display,
    currency: row.currency,
    claim_type: row.claim_type,
    claim_date: row.claim_date,
    admitted_date: row.admitted_date,
    amount: row.amount,
    status: row.status,
    status_display: row.status_display,
    fraud_flag: row.fraud_flag,
    allowed_actions: row.allowed_actions,
    created_at: row.created_at,
    updated_at: row.updated_at,
  }
}

function itemWithApproved(item: ClaimMockItem) {
  return {
    ...item,
    calculated_amount: item.calculated_amount,
    approved_amount: item.approved_amount ?? item.calculated_amount,
    adjustment_reason: item.adjustment_reason,
  }
}

function detailFor(row: ClaimMockRow) {
  const approvedTotal = row.items.reduce((sum, item) => sum + Number(item.approved_amount ?? item.calculated_amount), 0).toFixed(2)
  const netPayout = row.loan_offset ? row.loan_offset.net_payout : approvedTotal
  return {
    ...listFor(row),
    cause_of_claim: row.cause_of_claim,
    description: row.description,
    fraud_flag_reason: row.fraud_flag_reason,
    assessment_notes: row.status === "ASSESSED" || row.status === "REQUISITIONED" || row.status === "APPROVED" || row.status === "SETTLED" ? "Benefit verified against policy schedule and medical evidence." : "",
    waiver_of_premium_days: 0,
    waiver_of_premium_until: null,
    waiver_of_premium_applied: false,
    settled_date: row.status === "SETTLED" ? row.updated_at : null,
    settlement_amount: row.status === "SETTLED" ? netPayout : null,
    payment_reference: row.status === "SETTLED" ? "FO-PAY-2026-000041" : "",
    source_channel: "API",
    source_channel_display: "Claims Console",
    medical_status: row.medical_status,
    medical_status_display: row.medical_status === "COMPLETED" ? "Completed" : row.medical_status === "REQUESTED" ? "Requested" : "Not required",
    medical_result: row.medical_result,
    medical_reason: row.medical_reason,
    medical_loading_factor: row.medical_loading_factor,
    medical_requested_at: row.medical_status === "REQUESTED" || row.medical_status === "COMPLETED" ? row.created_at : null,
    medical_reviewed_by_display: row.medical_status === "COMPLETED" ? "Medical Officer — Dr. Khalfan S." : null,
    medical_reviewed_at: row.medical_status === "COMPLETED" ? row.updated_at : null,
    registered_by_display: "Claims Officer — Neema K.",
    admitted_by_display: row.admitted_date ? "Claims Officer — Neema K." : null,
    claimant: row.claimant ? { ...row.claimant, claimant_type_display: row.claimant.claimant_type.charAt(0) + row.claimant.claimant_type.slice(1).toLowerCase() } : null,
    items: row.items.map(itemWithApproved),
    documents: row.documents.map((doc) => ({ ...doc, mandatory_flag: doc.mandatory })),
    file_notes: row.file_notes.map((note) => ({ ...note })),
    requisition: row.requisition ? { ...row.requisition, bank_details_json: row.requisition.bank_details } : null,
    loan_offset: row.loan_offset,
    policy_context: { policy_number: row.policy_number, policyholder_display: row.policyholder_display, product_display: row.product_display, branch_display: row.branch_display, currency: row.currency },
    financial_summary: {
      claim_number: row.claim_number,
      policy_number: row.policy_number,
      currency: row.currency,
      gross_amount: approvedTotal,
      loan_offset: row.loan_offset ? row.loan_offset.offset_amount : "0.00",
      net_payout: netPayout,
      loan_offset_applied: Boolean(row.loan_offset),
      loan_breakdown: row.loan_offset ? [{ loan_id: "loan-said-1", outstanding_principal: "120000.00", interest: "0.00", offset_amount: "120000.00" }] : [],
    },
    audit_timeline: [
      { id: `${row.id}-event-1`, action: "REGISTERED", actor_display: "Claims Officer — Neema K.", source_channel: "API", reason: "Claim registered and admitted.", created_at: row.created_at },
      ...(row.medical_status === "REQUESTED" || row.medical_status === "COMPLETED" ? [{ id: `${row.id}-event-2`, action: "MEDICAL_REVIEW_REQUESTED", actor_display: "Claims Officer — Neema K.", source_channel: "API", reason: "Medical evidence requested.", created_at: row.created_at }] : []),
      ...(row.medical_status === "COMPLETED" ? [{ id: `${row.id}-event-3`, action: "MEDICAL_REVIEW_COMPLETED", actor_display: "Medical Officer — Dr. Khalfan S.", source_channel: "API", reason: row.medical_result === "CLEARED" ? "Medical clearance granted." : row.medical_reason, created_at: row.updated_at }] : []),
      ...(row.status === "ASSESSED" || row.status === "REQUISITIONED" || row.status === "APPROVED" || row.status === "SETTLED" ? [{ id: `${row.id}-event-4`, action: "ASSESSED", actor_display: "Claims Assessor — Baraka M.", source_channel: "API", reason: "Benefit amount approved.", created_at: row.updated_at }] : []),
      ...(row.requisition ? [{ id: `${row.id}-event-5`, action: "REQUISITIONED", actor_display: "Claims Officer — Neema K.", source_channel: "API", reason: "Payment requisition raised.", created_at: row.requisition.created_at }] : []),
      ...(row.status === "APPROVED" ? [{ id: `${row.id}-event-6`, action: "APPROVED", actor_display: "Finance Manager — Yusuf A.", source_channel: "API", reason: "Payment approval granted.", created_at: row.updated_at }] : []),
      ...(row.status === "SETTLED" ? [{ id: `${row.id}-event-7`, action: "SETTLED", actor_display: "Finance Officer — Rehema S.", source_channel: "API", reason: "Settlement confirmed and paid.", created_at: row.updated_at }] : []),
      ...(row.status === "REJECTED" ? [{ id: `${row.id}-event-8`, action: "REJECTED", actor_display: "Claims Assessor — Baraka M.", source_channel: "API", reason: row.fraud_flag_reason || "Claim rejected.", created_at: row.updated_at }] : []),
      ...(row.status === "CANCELLED" ? [{ id: `${row.id}-event-9`, action: "CANCELLED", actor_display: "Claims Officer — Neema K.", source_channel: "API", reason: "Claim cancelled.", created_at: row.updated_at }] : []),
    ],
  }
}

function documentsFor(row: ClaimMockRow) {
  const uploadedTypes = row.documents.map((doc) => doc.document_type)
  const requirements = requiredDocuments.map((req) => ({ ...req, uploaded: uploadedTypes.includes(req.document_type) }))
  const missing = requirements.filter((req) => req.mandatory && !req.uploaded).map((req) => req.document_type)
  return {
    claim_number: row.claim_number,
    results: row.documents.map((doc) => ({ ...doc, mandatory_flag: doc.mandatory })),
    documents: row.documents.map((doc) => ({ ...doc, mandatory_flag: doc.mandatory })),
    required_document_types: requiredDocuments.map((req) => req.document_type),
    missing_document_types: missing,
    all_mandatory_uploaded: missing.length === 0,
    mandatory: requiredDocuments.filter((req) => req.mandatory).length,
    uploaded: row.documents.length,
    requirements,
  }
}

function statusAfterAssess(row: ClaimMockRow) {
  return ["ASSESSED", "REQUISITIONED", "APPROVED", "SETTLED", "REJECTED", "CANCELLED"].includes(row.status) ? row.status : "ASSESSED"
}

export const claimsHandlers = [
  http.get(`*${CLAIMS_BASE}/kpis/`, ({ request }) => {
    const url = new URL(request.url)
    const q = (url.searchParams.get("q") ?? "").toLowerCase()
    const status = url.searchParams.get("status")
    const filtered = claims.filter((row) => (!q || `${row.claim_number} ${row.policy_number} ${row.policyholder_display}`.toLowerCase().includes(q)) && (!status || row.status === status))
    const settledRows = filtered.filter((row) => row.status === "SETTLED")
    const pendingAssessment = filtered.filter((row) => ["REGISTERED", "PENDING_MEDICAL", "ASSESSMENT"].includes(row.status))
    const outstanding = filtered.filter((row) => row.status !== "SETTLED").reduce((sum, row) => sum + Number(row.amount), 0).toFixed(2)
    const settledAmount = settledRows.reduce((sum, row) => sum + Number(row.amount), 0).toFixed(2)
    const currencyTotals: Record<string, { outstanding_amount: string; settled_amount: string }> = { TZS: { outstanding_amount: outstanding, settled_amount: settledAmount } }
    return data({
      total_claims: filtered.length,
      outstanding_amount: outstanding,
      settled_amount_period: settledAmount,
      pending_assessment_count: pendingAssessment.length,
      currency: "TZS",
      currency_totals: currencyTotals,
      filters_applied: { q: url.searchParams.get("q") ?? undefined, status: url.searchParams.get("status") ?? undefined },
      timestamp: "2026-08-27T08:00:00Z",
    })
  }),
  http.get(`*${CLAIMS_BASE}/options/types/`, ({ request }) => {
    const url = new URL(request.url)
    const q = (url.searchParams.get("q") ?? "").toLowerCase()
    return data(page(claimTypeOptions.filter((option) => !q || `${option.value} ${option.label}`.toLowerCase().includes(q)), url))
  }),
  http.get(`*${CLAIMS_BASE}/options/reasons/`, ({ request }) => {
    const url = new URL(request.url)
    const q = (url.searchParams.get("q") ?? "").toLowerCase()
    return data(page(claimReasonOptions.filter((option) => !q || `${option.value} ${option.label}`.toLowerCase().includes(q)), url))
  }),
  http.get(`*${CLAIMS_BASE}/options/policies/`, ({ request }) => {
    const url = new URL(request.url)
    const q = (url.searchParams.get("q") ?? "").toLowerCase()
    const rows = policyOptions.map((option) => ({ value: option.value, label: option.label, meta: option.meta }))
    return data(page(rows.filter((option) => !q || `${option.value} ${option.label}`.toLowerCase().includes(q)), url))
  }),
  http.get(`*${CLAIMS_BASE}/options/benefits/`, ({ params, request }) => {
    const url = new URL(request.url)
    const policyId = url.searchParams.get("policy_id")
    if (!policyId) return error(400, "CLAIM_POLICY_REQUIRED", "A policy is required to load claim-specific options.", ["Select a policy before loading covered benefits.", "Retry the options request with the policy_id query parameter."])
    const q = (url.searchParams.get("q") ?? "").toLowerCase()
    const options = benefitOptions[policyId] ?? []
    return data(page(options.filter((option) => !q || `${option.value} ${option.label}`.toLowerCase().includes(q)), url))
  }),
  http.get(`*${CLAIMS_BASE}/options/members/`, ({ request }) => {
    const url = new URL(request.url)
    const policyId = url.searchParams.get("policy_id")
    if (!policyId) return error(400, "CLAIM_POLICY_REQUIRED", "A policy is required to load claim-specific options.", ["Select a policy before loading members.", "Retry the options request with the policy_id query parameter."])
    const q = (url.searchParams.get("q") ?? "").toLowerCase()
    const options = memberOptions[policyId] ?? []
    return data(page(options.filter((option) => !q || `${option.value} ${option.label}`.toLowerCase().includes(q)), url))
  }),
  http.get(`*${CLAIMS_BASE}/export/`, () => new HttpResponse("claim_number,policy_number,status\nOL-CLM-2026-000001,ZIC-OL-2026-000001,REGISTERED\n", { status: 200, headers: { "Content-Type": "text/csv" } })),
  http.get(`*${CLAIMS_BASE}/:claimId/assessment-readiness/`, ({ params }) => {
    const row = findClaim(String(params.claimId))
    if (!row) return error(404, "CLAIM_NOT_FOUND", "The requested claim could not be found.", ["Return to the Claims register and search by claim number.", "Contact Claims Administration if the claim was recently migrated or archived."])
    const uploaded = row.documents.map((doc) => doc.document_type)
    const missing = requiredDocuments.filter((req) => req.mandatory && !uploaded.includes(req.document_type)).map((req) => req.document_type)
    const medicalReady = row.medical_status === "COMPLETED"
    return data({ claim_id: row.id, claim_number: row.claim_number, all_mandatory_documents_uploaded: missing.length === 0, missing_document_types: missing, medical_review_completed: medicalReady, medical_status: row.medical_status, ready: missing.length === 0 && medicalReady })
  }),
  http.get(`*${CLAIMS_BASE}/:claimId/documents/`, ({ params }) => {
    const row = findClaim(String(params.claimId))
    return row ? data(documentsFor(row)) : error(404, "CLAIM_NOT_FOUND", "The requested claim could not be found.", ["Return to the Claims register and search by claim number."])
  }),
  http.post(`*${CLAIMS_BASE}/:claimId/documents/`, async ({ params, request }) => {
    const row = findClaim(String(params.claimId))
    if (!row) return error(404, "CLAIM_NOT_FOUND", "The requested claim could not be found.", ["Return to the Claims register and search by claim number."])
    const text = await request.text()
    const documentType = (text.match(/name="document_type"[\s\S]*?\r\n\r\n([^\r\n]+)/) ?? [])[1]?.trim() ?? ""
    if (!documentType) return error(400, "CLAIM_DOCUMENT_REQUIRED", "A document type and file are required before the claim can progress.", ["Select the document type that matches the claim requirement.", "Attach the file or provide a managed storage reference, then retry."], { document_type: ["Choose a document type."] })
    const fileName = (text.match(/name="file"; filename="([^"]*)"/) ?? [])[1] ?? ""
    if (!fileName) return error(400, "CLAIM_DOCUMENT_REQUIRED", "A document type and file are required before the claim can progress.", ["Attach the file before uploading.", "Retry the upload from the claim Documents section."], { file: ["Choose a file to upload."] })
    if (text.length > 20 * 1024 * 1024) return error(400, "CLAIM_DOCUMENT_TOO_LARGE", "The claim document is larger than the supported 20 MB limit.", ["Reduce the file size to 20 MB or less without removing required evidence.", "Upload the smaller file again from the claim Documents section."])
    const uploaded: ClaimMockDocument = { id: `doc-${row.id}-${documentType}-${row.documents.length + 1}`, document_type: documentType, file_reference: `MOCK-FILE-${documentType}-${row.documents.length + 1}`, mandatory: requiredDocuments.some((req) => req.document_type === documentType && req.mandatory), uploaded_by_display: "Claims Officer — Neema K.", uploaded_at: "2026-08-27T09:00:00Z" }
    row.documents = [...row.documents, uploaded]
    row.updated_at = "2026-08-27T09:00:00Z"
    return data(documentsFor(row), 201)
  }),
  http.get(`*${CLAIMS_BASE}/:claimId/notes/`, ({ params }) => {
    const row = findClaim(String(params.claimId))
    return row ? data(row.file_notes) : error(404, "CLAIM_NOT_FOUND", "The requested claim could not be found.", ["Return to the Claims register and search by claim number."])
  }),
  http.post(`*${CLAIMS_BASE}/:claimId/notes/`, async ({ params, request }) => {
    const row = findClaim(String(params.claimId))
    if (!row) return error(404, "CLAIM_NOT_FOUND", "The requested claim could not be found.", ["Return to the Claims register and search by claim number."])
    const body = await request.json().catch(() => ({})) as { note_text?: string }
    const noteText = String(body.note_text ?? "").trim()
    if (!noteText) return error(400, "CLAIM_NOTE_REQUIRED", "An internal claim note cannot be empty.", ["Enter the operational observation or decision that should be retained in the claim file.", "Do not include sensitive credentials or unrelated personal information."], { note_text: ["Enter a note."] })
    const note: ClaimMockNote = { id: `note-${row.id}-${row.file_notes.length + 1}`, note_text: noteText, author_display: "Claims Officer — Neema K.", source_channel: "API", created_at: "2026-08-27T09:00:00Z" }
    row.file_notes = [...row.file_notes, note]
    row.updated_at = "2026-08-27T09:00:00Z"
    return data(note, 201)
  }),
  http.get(`*${CLAIMS_BASE}/:claimId/financial-summary/`, ({ params }) => {
    const row = findClaim(String(params.claimId))
    if (!row) return error(404, "CLAIM_NOT_FOUND", "The requested claim could not be found.", ["Return to the Claims register and search by claim number."])
    const approvedTotal = row.items.reduce((sum, item) => sum + Number(item.approved_amount ?? item.calculated_amount), 0)
    if (approvedTotal <= 0) return error(422, "CLAIM_FINANCIAL_SUMMARY_UNAVAILABLE", "A financial summary cannot be calculated until the claim has a positive approved amount.", ["Complete claim assessment and approve a positive benefit amount.", "Refresh the Financial Summary section and retry the calculation."])
    return data(detailFor(row).financial_summary)
  }),
  http.post(`*${CLAIMS_BASE}/:claimId/medical/require/`, async ({ params, request }) => {
    const row = findClaim(String(params.claimId))
    if (!row) return error(404, "CLAIM_NOT_FOUND", "The requested claim could not be found.", ["Return to the Claims register and search by claim number."])
    if (row.medical_status === "REQUESTED") return error(422, "CLAIM_INVALID_MEDICAL_STATUS", "A medical result cannot be recorded from the claim's current medical status.", ["Request medical review first, then record one outcome exactly once.", "Refresh the claim to confirm the current medical status before retrying."])
    const body = await request.json().catch(() => ({})) as { reason?: string }
    row.medical_status = "REQUESTED"
    row.medical_reason = String(body.reason ?? "")
    row.allowed_actions = ["view", "cancel", "print"]
    row.updated_at = "2026-08-27T09:00:00Z"
    return data(detailFor(row), 201)
  }),
  http.post(`*${CLAIMS_BASE}/:claimId/medical/result/`, async ({ params, request }) => {
    const row = findClaim(String(params.claimId))
    if (!row) return error(404, "CLAIM_NOT_FOUND", "The requested claim could not be found.", ["Return to the Claims register and search by claim number."])
    if (row.medical_status !== "REQUESTED") return error(422, "CLAIM_INVALID_MEDICAL_STATUS", "A medical result cannot be recorded from the claim's current medical status.", ["Request medical review first, then record one outcome exactly once.", "Refresh the claim to confirm the current medical status before retrying."])
    const body = await request.json().catch(() => ({})) as { result?: string; reason?: string; loading_factor?: string | number }
    const result = String(body.result ?? "").toUpperCase()
    if (!["CLEARED", "REJECTED", "LOADING"].includes(result)) return error(400, "CLAIM_INVALID_MEDICAL_RESULT", "The medical result is incomplete or unsupported.", ["Choose Cleared, Rejected, or Loading.", "Provide a reason when rejecting and a valid loading factor when applying loading."], { result: ["Choose Cleared, Rejected, or Loading."] })
    if (result === "REJECTED" && !String(body.reason ?? "").trim()) return error(400, "CLAIM_INVALID_MEDICAL_RESULT", "The medical result is incomplete or unsupported.", ["Provide a reason when rejecting the claim."], { reason: ["A rejection reason is required."] })
    if (result === "LOADING") {
      const factor = Number(body.loading_factor ?? 0)
      if (!Number.isFinite(factor) || factor <= 1 || factor > 10) return error(400, "CLAIM_LOADING_FACTOR_INVALID", "The medical loading factor is invalid.", ["Enter a loading factor greater than zero and no greater than 10.", "Alternatively provide a loading percentage that produces a factor in the supported range."], { loading_factor: ["Loading factor must be greater than 1 and no greater than 10."] })
      row.medical_loading_factor = factor.toFixed(2)
    } else {
      row.medical_loading_factor = null
    }
    row.medical_status = "COMPLETED"
    row.medical_result = result
    row.medical_reason = String(body.reason ?? "")
    row.allowed_actions = ["view", "assess", "cancel", "print"]
    row.updated_at = "2026-08-27T09:00:00Z"
    return data(detailFor(row), 201)
  }),
  http.post(`*${CLAIMS_BASE}/:claimId/assess/`, async ({ params, request }) => {
    const row = findClaim(String(params.claimId))
    if (!row) return error(404, "CLAIM_NOT_FOUND", "The requested claim could not be found.", ["Return to the Claims register and search by claim number."])
    const body = await request.json().catch(() => ({})) as { assessed_amount?: string | number; assessment_notes?: string; fraud_flag?: boolean; fraud_flag_reason?: string }
    const assessedAmount = Number(body.assessed_amount ?? 0)
    if (!Number.isFinite(assessedAmount) || assessedAmount < 0) return error(400, "CLAIM_ASSESSMENT_AMOUNT_INVALID", "The assessed amount is invalid or exceeds the calculated claim limit.", ["Enter a non-negative assessed amount no greater than the calculated maximum.", "Open the claim benefit breakdown to review the authoritative calculated amount."], { assessed_amount: ["Enter a valid amount."] })
    const calculatedTotal = row.items.reduce((sum, item) => sum + Number(item.calculated_amount), 0)
    if (assessedAmount > calculatedTotal) return error(422, "CLAIM_AMOUNT_EXCEEDS_LIMIT", "The requested claim amount exceeds the calculated benefit limit.", ["Review the calculated amount for each claim item.", "Enter an assessed amount at or below the calculated maximum, or document an approved adjustment."], { assessed_amount: [`The maximum assessed amount is ${calculatedTotal.toFixed(2)}.`] })
    if (row.medical_status !== "COMPLETED") return error(422, "CLAIM_MEDICAL_REVIEW_REQUIRED", "Medical review must be completed before claim assessment can proceed.", ["Open the Medical Review section and record a Cleared or Loading outcome.", "If the medical evidence is insufficient, obtain the required report and retry the review."])
    if (row.medical_result === "REJECTED") return error(422, "CLAIM_MEDICAL_REJECTED", "Medical review rejected this claim and assessment cannot proceed.", ["Review the medical decision and recorded reason in the claim timeline.", "Escalate or reopen the claim only through the approved Claims governance process."])
    const uploaded = row.documents.map((doc) => doc.document_type)
    const missingMandatory = requiredDocuments.some((req) => req.mandatory && !uploaded.includes(req.document_type))
    if (missingMandatory) return error(422, "CLAIM_MANDATORY_DOC_MISSING", "One or more mandatory claim documents are missing.", ["Open the claim Documents section and upload every required document.", "Verify that each uploaded file is linked to the correct document type before continuing."])
    if (body.fraud_flag && !String(body.fraud_flag_reason ?? "").trim()) return error(400, "CLAIM_FRAUD_REASON_REQUIRED", "A fraud flag reason is required when a claim is marked for fraud review.", ["Describe the evidence or control exception that triggered the fraud flag.", "Leave the fraud flag off when no fraud concern has been identified."], { fraud_flag_reason: ["Enter a fraud flag reason."] })
    row.status = statusAfterAssess(row)
    row.status_display = row.status.charAt(0) + row.status.slice(1).toLowerCase()
    row.items = row.items.map((item) => ({ ...item, approved_amount: assessedAmount.toFixed(2), adjustment_reason: item.approved_amount ? item.adjustment_reason : "Approved at assessed amount." }))
    row.fraud_flag = Boolean(body.fraud_flag)
    row.fraud_flag_reason = body.fraud_flag ? String(body.fraud_flag_reason ?? "") : ""
    row.allowed_actions = ["view", "raise-requisition", "cancel", "print"]
    row.updated_at = "2026-08-27T09:00:00Z"
    return data(detailFor(row), 201)
  }),
  http.post(`*${CLAIMS_BASE}/:claimId/raise-requisition/`, async ({ params, request }) => {
    const row = findClaim(String(params.claimId))
    if (!row) return error(404, "CLAIM_NOT_FOUND", "The requested claim could not be found.", ["Return to the Claims register and search by claim number."])
    if (!["ASSESSED", "REQUISITIONED", "APPROVED"].includes(row.status)) return error(422, "CLAIM_REQUISITION_REQUIRED", "The claim must be assessed before a payment requisition can be raised.", ["Complete mandatory documents and medical review in the claim file.", "Assess the covered benefit and approve the payable claim amount, then retry."])
    if (row.requisition) return error(409, "CLAIM_REQUISITION_ALREADY_EXISTS", "A payment requisition already exists for this claim.", ["Open the existing requisition to review its status and payment link.", "Do not create a second requisition for the same claim."])
    const body = await request.json().catch(() => ({})) as { bank_details?: Record<string, unknown>; narration?: string }
    const bankDetails = (body.bank_details && typeof body.bank_details === "object" && !Array.isArray(body.bank_details) ? body.bank_details : {}) as Record<string, unknown>
    const approvedTotal = row.items.reduce((sum, item) => sum + Number(item.approved_amount ?? item.calculated_amount), 0)
    if (approvedTotal <= 0) return error(422, "CLAIM_REQUISITION_NET_ZERO", "A payment requisition cannot be raised because the claim net payout is zero.", ["Review the approved claim amount and any policy loan offset in Financial Summary.", "Raise a requisition only when a positive amount remains payable."])
    if (!String(bankDetails.account_number ?? "").trim() || !String(bankDetails.account_holder ?? "").trim()) return error(400, "CLAIM_REQUISITION_BANK_DETAILS_REQUIRED", "Payment bank details are required before the claim requisition can be submitted.", ["Provide the approved claimant or partner bank details in the payment form.", "Confirm the account holder and account number before submitting the requisition."], { bank_details: ["Enter the account holder and account number."] })
    row.requisition = { id: `req-${row.id}`, requisition_number: `REQ-OL-2026-0002${row.items.length}`, amount: approvedTotal.toFixed(2), bank_details: bankDetails, payment_requisition_number: null, approval_request_status: "PENDING", approval_required: true, narration: String(body.narration ?? "Claim settlement payment"), status: "PENDING", status_display: "Pending", created_at: "2026-08-27T09:00:00Z", updated_at: "2026-08-27T09:00:00Z" }
    row.status = "REQUISITIONED"
    row.status_display = "Requisitioned"
    row.allowed_actions = ["view", "settle", "print"]
    row.updated_at = "2026-08-27T09:00:00Z"
    return data({ requisition: row.requisition }, 201)
  }),
  http.post(`*${CLAIMS_BASE}/:claimId/settle/`, async ({ params, request }) => {
    const row = findClaim(String(params.claimId))
    if (!row) return error(404, "CLAIM_NOT_FOUND", "The requested claim could not be found.", ["Return to the Claims register and search by claim number."])
    if (!["REQUISITIONED", "APPROVED"].includes(row.status)) return error(422, "CLAIM_SETTLEMENT_NOT_READY", "This claim is not ready to be settled in its current status.", ["Confirm that the claim payment has been approved and the claim is awaiting settlement.", "Complete any outstanding assessment, requisition, or approval step before retrying."])
    if (!row.requisition) return error(422, "CLAIM_SETTLEMENT_REQUISITION_REQUIRED", "A payment requisition is required before this claim can be settled.", ["Raise a payment requisition from the assessed claim.", "Confirm that the Front Office payment request is linked, then retry settlement."])
    const body = await request.json().catch(() => ({})) as { payment_reference?: string; payment_status?: string }
    const reference = String(body.payment_reference ?? "").trim()
    if (!reference) return error(400, "CLAIM_SETTLEMENT_PAYMENT_REFERENCE_REQUIRED", "A Front Office payment reference is required before settlement.", ["Enter the payment reference generated by Front Office.", "Verify that the reference belongs to this claim requisition before retrying."], { payment_reference: ["Enter the Front Office payment reference."] })
    row.status = "SETTLED"
    row.status_display = "Settled"
    row.requisition.payment_requisition_number = reference
    row.requisition.approval_request_status = "APPROVED"
    row.requisition.status = "APPROVED"
    row.requisition.status_display = "Approved"
    row.allowed_actions = ["view", "print"]
    row.updated_at = "2026-08-27T09:00:00Z"
    return data({ claim: detailFor(row) }, 201)
  }),
  http.post(`*${CLAIMS_BASE}/:claimId/print-discharge-voucher/`, ({ params }) => {
    const row = findClaim(String(params.claimId))
    return row ? data({ instance: { id: `${row.id}-voucher`, document_type: "OL_CLAIM_DISCHARGE_VOUCHER", template_version: 1, generated_by_display: "Sultan Admin" }, preview_url: `/api/v1/documents/instances/${row.id}-voucher/preview/`, signed_download_url: `/api/v1/documents/instances/${row.id}-voucher/download/?ticket=mock-voucher-${row.id}` }, 201) : error(404, "CLAIM_NOT_FOUND", "The requested claim could not be found.", ["Return to the Claims register and search by claim number."])
  }),
  http.post(`*${CLAIMS_BASE}/:claimId/medical/evaluate/`, ({ params }) => {
    const row = findClaim(String(params.claimId))
    return row ? data({ claim_id: row.id, claim_number: row.claim_number, evaluation: "ADMITTED", next_action: "upload-documents" }) : error(404, "CLAIM_NOT_FOUND", "The requested claim could not be found.", ["Return to the Claims register and search by claim number."])
  }),
  http.get(`*${CLAIMS_BASE}/:claimId/`, ({ params }) => {
    const row = findClaim(String(params.claimId))
    return row ? data(detailFor(row)) : error(404, "CLAIM_NOT_FOUND", "The requested claim could not be found.", ["Return to the Claims register and search by claim number.", "Contact Claims Administration if the claim was recently migrated or archived."])
  }),
  http.post(`*${POLICY_CLAIMS_BASE}/:policyId/claims/`, async ({ params, request }) => {
    const policy = policyOptions.find((item) => item.value === String(params.policyId))
    if (!policy) return error(404, "CLAIM_POLICY_NOT_FOUND", "The requested policy could not be found for claim options.", ["Select an existing policy from the policy search results.", "Ask Policy Administration to verify the policy reference if it was recently migrated."])
    if (policy.meta.status === "LAPSED") return error(422, "CLAIM_POLICY_INACTIVE", "This policy is not active and cannot receive a new claim.", ["Review the policy status and effective dates.", "Reinstate or correct the policy before registering a claim if the contract permits it."])
    const idempotencyKey = request.headers.get("X-Idempotency-Key")
    if (!idempotencyKey) return error(400, "CLAIM_IDEMPOTENCY_REQUIRED", "An idempotency key is required to register a claim safely.", ["Retry the request with a unique X-Idempotency-Key header.", "Reuse the same key when retrying the same submission so the original claim is returned."])
    const body = await request.json().catch(() => ({})) as { claim_type?: string; claim_date?: string; cause_of_claim?: string; description?: string; member_id?: string; claimant_details?: Record<string, unknown>; benefit_type?: string }
    if (!String(body.claim_type ?? "").trim()) return error(400, "CLAIM_INVALID_REGISTRATION", "The claim registration form needs correction before it can be submitted.", ["Correct each highlighted claim field.", "Select a configured claim type and provide claimant information before retrying."], { claim_type: ["Choose a claim type."] })
    if (!claimTypeOptions.some((option) => option.value === String(body.claim_type))) return error(422, "CLAIM_TYPE_NOT_CONFIGURED", "The selected claim type is not configured for current use.", ["Choose an active claim type from the Claims parameters catalog.", "Ask Claims Configuration to activate or effective-date the required claim type."])
    const claimDate = String(body.claim_date ?? "")
    if (!/^\d{4}-\d{2}-\d{2}$/.test(claimDate)) return error(400, "CLAIM_INVALID_DATE", "The claim date is invalid.", ["Enter a real calendar date in the policy service period.", "Use the date format YYYY-MM-DD when calling the API."], { claim_date: ["Use the date format YYYY-MM-DD."] })
    if (!String(body.member_id ?? "").trim() && (!body.claimant_details || !String(body.claimant_details.name ?? "").trim())) return error(400, "CLAIM_CLAIMANT_REQUIRED", "Claimant information is required before the claim can be registered.", ["Select an issued policy member or provide claimant_details with a name and claimant_type.", "Verify the claimant relationship and identity information before retrying."])
    const seq = (claims.length + 1).toString().padStart(6, "0")
    const row: ClaimMockRow = {
      id: `claim-registered-${Date.now()}`,
      claim_number: `OL-CLM-2026-${seq}`,
      policy_id: String(params.policyId),
      policy_number: String(policy.meta.policy_number),
      policyholder_name: String(policy.meta.policyholder_name),
      policyholder_display: String(policy.meta.policyholder_display ?? policy.label),
      product_display: String(policy.meta.product_display),
      branch_display: "DSM-CENTRAL — Dar es Salaam Central Branch",
      currency: String(policy.meta.currency ?? "TZS"),
      claim_type: String(body.claim_type),
      claim_date: claimDate,
      admitted_date: claimDate,
      status: "REGISTERED",
      status_display: "Registered",
      fraud_flag: false,
      fraud_flag_reason: "",
      amount: "0.00",
      cause_of_claim: String(body.cause_of_claim ?? ""),
      description: String(body.description ?? ""),
      medical_status: "NOT_REQUIRED",
      medical_result: "",
      medical_reason: "",
      medical_loading_factor: null,
      claimant: { id: String(body.member_id ?? `claimant-${Date.now()}`), claimant_type: String(body.claimant_details?.claimant_type ?? "POLICYHOLDER"), relationship: String(body.claimant_details?.relationship ?? "Self"), name: String(body.claimant_details?.name ?? String(policy.meta.policyholder_name)), identity_number: String(body.claimant_details?.identity_number ?? ""), age: Number(body.claimant_details?.age ?? null) || null, gender: String(body.claimant_details?.gender ?? "") },
      items: [{ id: `claim-item-${Date.now()}`, benefit_type: String(body.benefit_type ?? "GENERAL_BENEFIT"), sum_assured: "0.00", calculated_amount: "0.00", approved_amount: null, adjustment_reason: "" }],
      documents: [],
      file_notes: [{ id: `note-${Date.now()}`, note_text: "Claim registered from the Claims console.", author_display: "Claims Officer — Neema K.", source_channel: "API", created_at: "2026-08-27T09:00:00Z" }],
      requisition: null,
      loan_offset: null,
      allowed_actions: ["view", "assess", "cancel", "print"],
      created_at: "2026-08-27T09:00:00Z",
      updated_at: "2026-08-27T09:00:00Z",
    }
    claims = [row, ...claims]
    return data({ claim: detailFor(row) }, 201)
  }),
  http.get(`*${CLAIMS_BASE}/`, ({ request }) => {
    const url = new URL(request.url)
    const q = (url.searchParams.get("q") ?? "").toLowerCase()
    const status = url.searchParams.get("status")
    const claimType = url.searchParams.get("claim_type")
    const fraudFlag = url.searchParams.get("fraud_flag")
    const filtered = claims.filter((row) => (!q || `${row.claim_number} ${row.policy_number} ${row.policyholder_name} ${row.policyholder_display}`.toLowerCase().includes(q)) && (!status || row.status === status) && (!claimType || row.claim_type === claimType) && (!fraudFlag || String(row.fraud_flag) === fraudFlag))
    return data(page(filtered.map((row) => listFor(row)), url))
  }),
]

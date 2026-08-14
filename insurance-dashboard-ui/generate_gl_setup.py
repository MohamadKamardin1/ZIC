import re

# We will read GCSetup.tsx, rip out the SETUP_CATEGORIES array, and replace it with GL_CATEGORIES.
# Then we will replace all gcSetup with glSetup.

with open("src/pages/group-credit/GCSetup.tsx", "r") as f:
    gc_content = f.read()

# GL SETUP CATEGORIES DEFINITION
GL_CATS_STRING = """const SETUP_CATEGORIES: SetupCategory[] = [
  // ── System Setup ──────────────────────────────────────────────
  {
    key: "lookupValues", label: "Dropdown Configuration", group: "System Setup", icon: Database,
    color: "#64748b", gradient: "linear-gradient(135deg, #64748b, #94a3b8)",
    fetchFn: () => glSetup.listLookupValues(), createFn: (d) => glSetup.createLookupValue(d),
    updateFn: (id, d) => glSetup.updateLookupValue(id, d), deleteFn: (id) => glSetup.deleteLookupValue(id),
    fields: [
      { key: "category", label: "Category Key", required: true, type: "select", choices: [
        { value: "RATE_TYPE", label: "RATE_TYPE" },
        { value: "GENDER", label: "GENDER" },
        { value: "QUESTION_TYPE", label: "QUESTION_TYPE" },
        { value: "HEALTH_QUESTION_CATEGORY", label: "HEALTH_QUESTION_CATEGORY" },
        { value: "RIDER_TYPE", label: "RIDER_TYPE" },
        { value: "STATUS", label: "STATUS" },
        { value: "UW_STATUS", label: "UW_STATUS" },
        { value: "RELATIONSHIP", label: "RELATIONSHIP" },
        { value: "PERSONAL_HABIT_CATEGORY", label: "PERSONAL_HABIT_CATEGORY" },
        { value: "RISK_LEVEL", label: "RISK_LEVEL" },
        { value: "MEDICAL_HISTORY_CATEGORY", label: "MEDICAL_HISTORY_CATEGORY" },
        { value: "RISK_IMPACT", label: "RISK_IMPACT" },
        { value: "FACILITY_TYPE", label: "FACILITY_TYPE" },
        { value: "MEDICAL_CASE_STATUS", label: "MEDICAL_CASE_STATUS" },
        { value: "CLAIM_INSTALLMENT_STATUS", label: "CLAIM_INSTALLMENT_STATUS" },
        { value: "INVOICE_STATUS", label: "INVOICE_STATUS" },
      ] },
      { key: "value", label: "Stored Value", required: true },
      { key: "label", label: "Display Label", required: true },
      { key: "sort_order", label: "Sort Order", type: "number" },
    ],
  },
  
  // ── GL Scheme Setup ──────────────────────────────────────────────
  {
    key: "schemeTypes", label: "GL Scheme Types", group: "GL Scheme Setup", icon: FileText,
    color: "#f59e0b", gradient: "linear-gradient(135deg, #f59e0b, #fbbf24)",
    fetchFn: glSetup.listSchemeTypes, createFn: (d) => glSetup.createSchemeType(d),
    updateFn: (id, d) => glSetup.updateSchemeType(id, d), deleteFn: (id) => glSetup.deleteSchemeType(id),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "description", label: "Description", type: "textarea" },
    ],
  },
  {
    key: "premiumRates", label: "Premium Rates", group: "GL Scheme Setup", icon: DollarSign,
    color: "#f59e0b", gradient: "linear-gradient(135deg, #f59e0b, #fbbf24)",
    fetchFn: glSetup.listPremiumRates, createFn: (d) => glSetup.createPremiumRate(d),
    updateFn: (id, d) => glSetup.updatePremiumRate(id, d), deleteFn: (id) => glSetup.deletePremiumRate(id),
    fields: [
      { key: "name", label: "Name", required: true },
      { key: "rate_type", label: "Rate Type", type: "select", lookupCategory: "RATE_TYPE", required: true },
      { key: "age_band_start", label: "Age Start", type: "number" },
      { key: "age_band_end", label: "Age End", type: "number" },
      { key: "gender", label: "Gender", type: "select", lookupCategory: "GENDER" },
      { key: "rate_per_mille", label: "Rate Per Mille", type: "number" },
      { key: "effective_date", label: "Effective Date", type: "date", required: true },
    ],
  },
  {
    key: "memberStatuses", label: "Member Statuses", group: "GL Scheme Setup", icon: Users,
    color: "#f59e0b", gradient: "linear-gradient(135deg, #f59e0b, #fbbf24)",
    fetchFn: glSetup.listMemberStatuses, createFn: (d) => glSetup.createMemberStatus(d),
    updateFn: (id, d) => glSetup.updateMemberStatus(id, d), deleteFn: (id) => glSetup.deleteMemberStatus(id),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "description", label: "Description" },
    ],
  },
  {
    key: "schemeStatuses", label: "Scheme Statuses", group: "GL Scheme Setup", icon: Activity,
    color: "#f59e0b", gradient: "linear-gradient(135deg, #f59e0b, #fbbf24)",
    fetchFn: glSetup.listSchemeStatuses, createFn: (d) => glSetup.createSchemeStatus(d),
    updateFn: (id, d) => glSetup.updateSchemeStatus(id, d), deleteFn: (id) => glSetup.deleteSchemeStatus(id),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "sort_order", label: "Sort Order", type: "number" },
      { key: "is_terminal", label: "Is Terminal", type: "boolean" },
    ],
  },
  {
    key: "renewalStatuses", label: "Renewal Statuses", group: "GL Scheme Setup", icon: Repeat,
    color: "#f59e0b", gradient: "linear-gradient(135deg, #f59e0b, #fbbf24)",
    fetchFn: glSetup.listRenewalStatuses, createFn: (d) => glSetup.createRenewalStatus(d),
    updateFn: (id, d) => glSetup.updateRenewalStatus(id, d), deleteFn: (id) => glSetup.deleteRenewalStatus(id),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
    ],
  },
  {
    key: "healthQuestions", label: "Health Questions", group: "GL Scheme Setup", icon: HelpCircle,
    color: "#f59e0b", gradient: "linear-gradient(135deg, #f59e0b, #fbbf24)",
    fetchFn: glSetup.listHealthQuestions, createFn: (d) => glSetup.createHealthQuestion(d),
    updateFn: (id, d) => glSetup.updateHealthQuestion(id, d), deleteFn: (id) => glSetup.deleteHealthQuestion(id),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "question_text", label: "Question", type: "textarea", required: true },
      { key: "question_type", label: "Type", type: "select", lookupCategory: "QUESTION_TYPE", required: true },
      { key: "category", label: "Category", type: "select", lookupCategory: "HEALTH_QUESTION_CATEGORY", required: true },
    ],
  },
  {
    key: "healthQuestionnaires", label: "Health Questionnaires", group: "GL Scheme Setup", icon: FileText,
    color: "#f59e0b", gradient: "linear-gradient(135deg, #f59e0b, #fbbf24)",
    fetchFn: glSetup.listHealthQuestionnaires, createFn: (d) => glSetup.createHealthQuestionnaire(d),
    updateFn: (id, d) => glSetup.updateHealthQuestionnaire(id, d), deleteFn: (id) => glSetup.deleteHealthQuestionnaire(id),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "version", label: "Version" },
      { key: "effective_date", label: "Effective Date", type: "date", required: true },
    ],
  },
  
  // ── GL Product Setup ──────────────────────────────────────────────
  {
    key: "subProducts", label: "Sub Products", group: "GL Product Setup", icon: Package,
    color: "#6366f1", gradient: "linear-gradient(135deg, #6366f1, #8b5cf6)",
    fetchFn: glSetup.listSubProducts, createFn: (d) => glSetup.createSubProduct(d),
    updateFn: (id, d) => glSetup.updateSubProduct(id, d), deleteFn: (id) => glSetup.deleteSubProduct(id),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "description", label: "Description", type: "textarea" },
    ],
  },
  {
    key: "products", label: "GL Products", group: "GL Product Setup", icon: PackageCheck,
    color: "#6366f1", gradient: "linear-gradient(135deg, #6366f1, #8b5cf6)",
    fetchFn: glSetup.listProducts, createFn: (d) => glSetup.createProduct(d),
    updateFn: (id, d) => glSetup.updateProduct(id, d), deleteFn: (id) => glSetup.deleteProduct(id),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "sub_product", label: "Sub Product", type: "select", optionsFn: glSetup.listSubProducts, displayKey: "sub_product_name", required: true },
      { key: "min_members", label: "Min Members", type: "number" },
      { key: "max_members", label: "Max Members", type: "number" },
      { key: "free_cover_limit", label: "FCL", type: "number" },
    ],
  },

  // ── GL Rider Setup ──────────────────────────────────────────────
  {
    key: "riders", label: "GL Riders", group: "GL Rider Setup", icon: Shield,
    color: "#10b981", gradient: "linear-gradient(135deg, #10b981, #34d399)",
    fetchFn: glSetup.listRiders, createFn: (d) => glSetup.createRider(d),
    updateFn: (id, d) => glSetup.updateRider(id, d), deleteFn: (id) => glSetup.deleteRider(id),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "rider_type", label: "Type", type: "select", lookupCategory: "RIDER_TYPE", required: true },
      { key: "is_mandatory", label: "Mandatory", type: "boolean" },
    ],
  },
  {
    key: "riderRates", label: "Rider Rates", group: "GL Rider Setup", icon: Percent,
    color: "#10b981", gradient: "linear-gradient(135deg, #10b981, #34d399)",
    fetchFn: glSetup.listRiderRates, createFn: (d) => glSetup.createRiderRate(d),
    updateFn: (id, d) => glSetup.updateRiderRate(id, d), deleteFn: (id) => glSetup.deleteRiderRate(id),
    fields: [
      { key: "rider", label: "Rider", type: "select", optionsFn: glSetup.listRiders, displayKey: "rider_name", required: true },
      { key: "age_band_start", label: "Age Start", type: "number" },
      { key: "age_band_end", label: "Age End", type: "number" },
      { key: "gender", label: "Gender", type: "select", lookupCategory: "GENDER" },
      { key: "rate_per_mille", label: "Rate Per Mille", type: "number" },
      { key: "effective_date", label: "Effective Date", type: "date", required: true },
    ],
  },

  // ── GL Medical U/w ──────────────────────────────────────────────
  {
    key: "medicalCodes", label: "Medical Codes", group: "GL Medical U/w", icon: Activity,
    color: "#ec4899", gradient: "linear-gradient(135deg, #ec4899, #f472b6)",
    fetchFn: glSetup.listMedicalCodes, createFn: (d) => glSetup.createMedicalCode(d),
    updateFn: (id, d) => glSetup.updateMedicalCode(id, d), deleteFn: (id) => glSetup.deleteMedicalCode(id),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "description", label: "Description", type: "textarea" },
    ],
  },
  {
    key: "medicalLimits", label: "Medical Limits", group: "GL Medical U/w", icon: AlertTriangle,
    color: "#ec4899", gradient: "linear-gradient(135deg, #ec4899, #f472b6)",
    fetchFn: glSetup.listMedicalLimits, createFn: (d) => glSetup.createMedicalLimit(d),
    updateFn: (id, d) => glSetup.updateMedicalLimit(id, d), deleteFn: (id) => glSetup.deleteMedicalLimit(id),
    fields: [
      { key: "age_min", label: "Age Min", type: "number", required: true },
      { key: "age_max", label: "Age Max", type: "number", required: true },
      { key: "sum_assured_min", label: "SA Min", type: "number" },
      { key: "sum_assured_max", label: "SA Max", type: "number" },
      { key: "required_codes", label: "Requirements", type: "textarea" },
    ],
  },
  {
    key: "uwDecisions", label: "UW Decisions", group: "GL Medical U/w", icon: CheckSquare,
    color: "#ec4899", gradient: "linear-gradient(135deg, #ec4899, #f472b6)",
    fetchFn: glSetup.listUnderwritingDecisions, createFn: (d) => glSetup.createUnderwritingDecision(d),
    updateFn: (id, d) => glSetup.updateUnderwritingDecision(id, d), deleteFn: (id) => glSetup.deleteUnderwritingDecision(id),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "decision_name", label: "Name", required: true },
      { key: "loading_percentage", label: "Loading %", type: "number" },
    ],
  },
  {
    key: "personalHabits", label: "Personal Habits", group: "GL Medical U/w", icon: Cigarette,
    color: "#ec4899", gradient: "linear-gradient(135deg, #ec4899, #f472b6)",
    fetchFn: glSetup.listPersonalHabits, createFn: (d) => glSetup.createPersonalHabit(d),
    updateFn: (id, d) => glSetup.updatePersonalHabit(id, d), deleteFn: (id) => glSetup.deletePersonalHabit(id),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "category", label: "Category", type: "select", lookupCategory: "PERSONAL_HABIT_CATEGORY", required: true },
      { key: "description", label: "Description", type: "textarea" },
      { key: "risk_level", label: "Risk Level", type: "select", lookupCategory: "RISK_LEVEL", required: true },
    ],
  },
  {
    key: "medicalHistories", label: "Medical Histories", group: "GL Medical U/w", icon: HeartPulse,
    color: "#ec4899", gradient: "linear-gradient(135deg, #ec4899, #f472b6)",
    fetchFn: glSetup.listMedicalHistories, createFn: (d) => glSetup.createMedicalHistory(d),
    updateFn: (id, d) => glSetup.updateMedicalHistory(id, d), deleteFn: (id) => glSetup.deleteMedicalHistory(id),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "category", label: "Category", type: "select", lookupCategory: "MEDICAL_HISTORY_CATEGORY", required: true },
      { key: "condition_name", label: "Condition", required: true },
      { key: "risk_impact", label: "Risk Impact", type: "select", lookupCategory: "RISK_IMPACT", required: true },
    ],
  },
  {
    key: "medicalFacilities", label: "Medical Facilities", group: "GL Medical U/w", icon: Heart,
    color: "#ec4899", gradient: "linear-gradient(135deg, #ec4899, #f472b6)",
    fetchFn: glSetup.listMedicalFacilities, createFn: (d) => glSetup.createMedicalFacility(d),
    updateFn: (id, d) => glSetup.updateMedicalFacility(id, d), deleteFn: (id) => glSetup.deleteMedicalFacility(id),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "facility_type", label: "Type", type: "select", lookupCategory: "FACILITY_TYPE", required: true },
      { key: "city", label: "City" },
      { key: "region", label: "Region" },
      { key: "phone", label: "Phone" },
    ],
  },
  {
    key: "medicalPractitioners", label: "Medical Practitioners", group: "GL Medical U/w", icon: Stethoscope,
    color: "#ec4899", gradient: "linear-gradient(135deg, #ec4899, #f472b6)",
    fetchFn: glSetup.listMedicalPractitioners, createFn: (d) => glSetup.createMedicalPractitioner(d),
    updateFn: (id, d) => glSetup.updateMedicalPractitioner(id, d), deleteFn: (id) => glSetup.deleteMedicalPractitioner(id),
    fields: [
      { key: "license_number", label: "License", required: true },
      { key: "name", label: "Name", required: true },
      { key: "specialty", label: "Specialty", required: true },
      { key: "facility", label: "Facility", type: "select", optionsFn: glSetup.listMedicalFacilities, displayKey: "facility_name" },
    ],
  },

  // ── GL Claim Setup ──────────────────────────────────────────────
  {
    key: "claimTypes", label: "Claim Types", group: "GL Claim Setup", icon: AlertCircle,
    color: "#ef4444", gradient: "linear-gradient(135deg, #ef4444, #f87171)",
    fetchFn: glSetup.listClaimTypes, createFn: (d) => glSetup.createClaimType(d),
    updateFn: (id, d) => glSetup.updateClaimType(id, d), deleteFn: (id) => glSetup.deleteClaimType(id),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "requires_medical_report", label: "Req. Medical", type: "boolean" },
    ],
  },
  {
    key: "claimReasons", label: "Claim Reasons", group: "GL Claim Setup", icon: HelpCircle,
    color: "#ef4444", gradient: "linear-gradient(135deg, #ef4444, #f87171)",
    fetchFn: glSetup.listClaimReasons, createFn: (d) => glSetup.createClaimReason(d),
    updateFn: (id, d) => glSetup.updateClaimReason(id, d), deleteFn: (id) => glSetup.deleteClaimReason(id),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
    ],
  },
  {
    key: "claimStatuses", label: "Claim Statuses", group: "GL Claim Setup", icon: Activity,
    color: "#ef4444", gradient: "linear-gradient(135deg, #ef4444, #f87171)",
    fetchFn: glSetup.listClaimStatuses, createFn: (d) => glSetup.createClaimStatus(d),
    updateFn: (id, d) => glSetup.updateClaimStatus(id, d), deleteFn: (id) => glSetup.deleteClaimStatus(id),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "sort_order", label: "Sort Order", type: "number" },
      { key: "is_terminal", label: "Is Terminal", type: "boolean" },
    ],
  },
  {
    key: "dischargeTypes", label: "Discharge Types", group: "GL Claim Setup", icon: FileCheck,
    color: "#ef4444", gradient: "linear-gradient(135deg, #ef4444, #f87171)",
    fetchFn: glSetup.listDischargeTypes, createFn: (d) => glSetup.createDischargeType(d),
    updateFn: (id, d) => glSetup.updateDischargeType(id, d), deleteFn: (id) => glSetup.deleteDischargeType(id),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
    ],
  },
  {
    key: "correspondentTypes", label: "Correspondent Types", group: "GL Claim Setup", icon: Users,
    color: "#ef4444", gradient: "linear-gradient(135deg, #ef4444, #f87171)",
    fetchFn: glSetup.listCorrespondentTypes, createFn: (d) => glSetup.createCorrespondentType(d),
    updateFn: (id, d) => glSetup.updateCorrespondentType(id, d), deleteFn: (id) => glSetup.deleteCorrespondentType(id),
    fields: [
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
    ],
  },

  // ── GL Invoicing ──────────────────────────────────────────────
  {
    key: "medicalInvoices", label: "Medical Invoices", group: "GL Invoicing", icon: Receipt,
    color: "#8b5cf6", gradient: "linear-gradient(135deg, #8b5cf6, #d946ef)",
    fetchFn: glSetup.listMedicalInvoices, createFn: (d) => glSetup.createMedicalInvoice(d),
    updateFn: (id, d) => glSetup.updateMedicalInvoice(id, d), deleteFn: (id) => glSetup.deleteMedicalInvoice(id),
    fields: [
      { key: "invoice_number", label: "Invoice No.", required: true },
      { key: "facility", label: "Facility", type: "select", optionsFn: glSetup.listMedicalFacilities, displayKey: "facility_name", required: true },
      { key: "amount", label: "Amount", type: "number", required: true },
      { key: "status", label: "Status", type: "select", lookupCategory: "INVOICE_STATUS", required: true },
    ],
  },
]
"""

# We need to add the extra icon imports: 
# DollarSign, Users, Repeat, HelpCircle, PackageCheck, Percent, AlertTriangle, CheckSquare, Cigarette, HeartPulse, Stethoscope, FileCheck, Receipt
extra_icons = "DollarSign, Users, Repeat, HelpCircle, PackageCheck, Percent, AlertTriangle, CheckSquare, Cigarette, HeartPulse, Stethoscope, FileCheck, Receipt"

# Replace SETUP_CATEGORIES
pattern = re.compile(r"const SETUP_CATEGORIES: SetupCategory\[\] = \[.*?\]\n", re.DOTALL)
new_content = pattern.sub(GL_CATS_STRING, gc_content)

# Replace gcSetup with glSetup globally
new_content = new_content.replace("gcSetup", "glSetup")
new_content = new_content.replace("gc-api", "gl-api")
new_content = new_content.replace("Group Credit Setup", "Group Life Setup")
new_content = new_content.replace("Group Credit insurance", "Group Life insurance")

# Add the extra icons to the import statement
# We'll just replace `AlertCircle` with `AlertCircle, ` + extra_icons
new_content = new_content.replace("AlertCircle", "AlertCircle, " + extra_icons)

with open("src/pages/group-life/GLSetup.tsx", "w") as f:
    f.write(new_content)


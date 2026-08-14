import os
import re

with open("src/pages/group-life/GLSetup.tsx", "r") as f:
    gl_setup_content = f.read()

# Replace GL to OL
ol_setup_content = gl_setup_content.replace("GLSetup", "OLSetup")
ol_setup_content = ol_setup_content.replace("Group Life Parameters", "Ordinary Life Parameters")
ol_setup_content = ol_setup_content.replace("group-life", "ordinary-life")
ol_setup_content = ol_setup_content.replace("glSetup", "olSetup")
ol_setup_content = ol_setup_content.replace("gl-api", "ol-api")

# We will need to fully replace the `SETUP_CATEGORIES` array because OL has different parameter tables.
setup_categories = """const SETUP_CATEGORIES: SetupCategory[] = [
  // ── OL Lookup Values ──────────────────────────────────────────────
  {
    key: "lookupValues", label: "Dropdown Configuration", group: "General Configuration", icon: Settings,
    color: "#a855f7", gradient: "linear-gradient(135deg, #a855f7, #d946ef)",
    fetchFn: olSetup.listLookupValues, createFn: (d) => olSetup.createLookupValue(d),
    updateFn: (id, d) => olSetup.updateLookupValue(id, d), deleteFn: (id) => olSetup.deleteLookupValue(id),
    fields: [
      { key: "category", label: "Category Key (e.g. POLICY_STATUS)", type: "text", required: true },
      { key: "value", label: "Stored Value", type: "text", required: true },
      { key: "label", label: "Display Label", type: "text", required: true },
      { key: "sort_order", label: "Sort Order", type: "number", required: false },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  
  // ── OL Default Setups ──────────────────────────────────────────────
  {
    key: "defaultSystemParameters", label: "Default System Parameters", group: "OL Default Setups", icon: Sliders,
    color: "#3b82f6", gradient: "linear-gradient(135deg, #3b82f6, #60a5fa)",
    fetchFn: olSetup.listDefaultSystemParameters, createFn: (d) => olSetup.createDefaultSystemParameter(d),
    updateFn: (id, d) => olSetup.updateDefaultSystemParameter(id, d), deleteFn: (id) => olSetup.deleteDefaultSystemParameter(id),
    fields: [
      { key: "code", label: "Parameter Code", type: "text", required: true },
      { key: "name", label: "Parameter Name", type: "text", required: true },
      { key: "value", label: "Parameter Value", type: "text", required: true },
      { key: "description", label: "Description", type: "text", required: false },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  {
    key: "overrideCommissionSetup", label: "Override Commission Setup", group: "OL Default Setups", icon: Percent,
    color: "#f59e0b", gradient: "linear-gradient(135deg, #f59e0b, #fbbf24)",
    fetchFn: olSetup.listOverrideCommissionSetups, createFn: (d) => olSetup.createOverrideCommissionSetup(d),
    updateFn: (id, d) => olSetup.updateOverrideCommissionSetup(id, d), deleteFn: (id) => olSetup.deleteOverrideCommissionSetup(id),
    fields: [
      { key: "role_name", label: "Role Name", type: "text", required: true },
      { key: "override_percentage", label: "Override %", type: "number", required: true },
      { key: "effective_date", label: "Effective Date", type: "date", required: true },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  {
    key: "computationApproaches", label: "Computation Approach", group: "OL Default Setups", icon: Calculator,
    color: "#10b981", gradient: "linear-gradient(135deg, #10b981, #34d399)",
    fetchFn: olSetup.listComputationApproaches, createFn: (d) => olSetup.createComputationApproach(d),
    updateFn: (id, d) => olSetup.updateComputationApproach(id, d), deleteFn: (id) => olSetup.deleteComputationApproach(id),
    fields: [
      { key: "code", label: "Code", type: "text", required: true },
      { key: "name", label: "Name", type: "text", required: true },
      { key: "description", label: "Description", type: "text", required: false },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  {
    key: "maturityClaimSetup", label: "Maturity Claims Setup", group: "OL Default Setups", icon: CheckSquare,
    color: "#6366f1", gradient: "linear-gradient(135deg, #6366f1, #818cf8)",
    fetchFn: olSetup.listMaturityClaimSetups, createFn: (d) => olSetup.createMaturityClaimSetup(d),
    updateFn: (id, d) => olSetup.updateMaturityClaimSetup(id, d), deleteFn: (id) => olSetup.deleteMaturityClaimSetup(id),
    fields: [
      { key: "code", label: "Code", type: "text", required: true },
      { key: "name", label: "Name", type: "text", required: true },
      { key: "notification_days_prior", label: "Notification Days Prior", type: "number", required: true },
      { key: "requires_discharge_voucher", label: "Requires Discharge Voucher", type: "boolean", required: false },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },

  // ── OL Policy Setup ──────────────────────────────────────────────
  {
    key: "anticipatedEndowmentRates", label: "Anticipated Endowment Rates", group: "OL Policy Setup", icon: TrendingUp,
    color: "#ec4899", gradient: "linear-gradient(135deg, #ec4899, #f472b6)",
    fetchFn: olSetup.listAnticipatedEndowmentInstallmentRates, createFn: (d) => olSetup.createAnticipatedEndowmentInstallmentRate(d),
    updateFn: (id, d) => olSetup.updateAnticipatedEndowmentInstallmentRate(id, d), deleteFn: (id) => olSetup.deleteAnticipatedEndowmentInstallmentRate(id),
    fields: [
      { key: "policy_year", label: "Policy Year", type: "number", required: true },
      { key: "percentage_payout", label: "Percentage Payout", type: "number", required: true },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  {
    key: "gracePeriods", label: "Grace Period", group: "OL Policy Setup", icon: Clock,
    color: "#8b5cf6", gradient: "linear-gradient(135deg, #8b5cf6, #a78bfa)",
    fetchFn: olSetup.listGracePeriods, createFn: (d) => olSetup.createGracePeriod(d),
    updateFn: (id, d) => olSetup.updateGracePeriod(id, d), deleteFn: (id) => olSetup.deleteGracePeriod(id),
    fields: [
      { key: "code", label: "Code", type: "text", required: true },
      { key: "days", label: "Days", type: "number", required: true },
      { key: "description", label: "Description", type: "text", required: false },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  {
    key: "policyStatuses", label: "Policy Statuses", group: "OL Policy Setup", icon: Activity,
    color: "#14b8a6", gradient: "linear-gradient(135deg, #14b8a6, #2dd4bf)",
    fetchFn: olSetup.listPolicyStatuses, createFn: (d) => olSetup.createPolicyStatus(d),
    updateFn: (id, d) => olSetup.updatePolicyStatus(id, d), deleteFn: (id) => olSetup.deletePolicyStatus(id),
    fields: [
      { key: "code", label: "Code", type: "text", required: true },
      { key: "name", label: "Name", type: "text", required: true },
      { key: "is_terminal", label: "Is Terminal", type: "boolean", required: false },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  {
    key: "policyRenewalStatuses", label: "Policy Renewal Status", group: "OL Policy Setup", icon: RefreshCw,
    color: "#0ea5e9", gradient: "linear-gradient(135deg, #0ea5e9, #38bdf8)",
    fetchFn: olSetup.listPolicyRenewalStatuses, createFn: (d) => olSetup.createPolicyRenewalStatus(d),
    updateFn: (id, d) => olSetup.updatePolicyRenewalStatus(id, d), deleteFn: (id) => olSetup.deletePolicyRenewalStatus(id),
    fields: [
      { key: "code", label: "Code", type: "text", required: true },
      { key: "name", label: "Name", type: "text", required: true },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  {
    key: "beneficiaryTypes", label: "Beneficiary Types", group: "OL Policy Setup", icon: Users,
    color: "#ef4444", gradient: "linear-gradient(135deg, #ef4444, #f87171)",
    fetchFn: olSetup.listBeneficiaryTypes, createFn: (d) => olSetup.createBeneficiaryType(d),
    updateFn: (id, d) => olSetup.updateBeneficiaryType(id, d), deleteFn: (id) => olSetup.deleteBeneficiaryType(id),
    fields: [
      { key: "code", label: "Code", type: "text", required: true },
      { key: "name", label: "Name", type: "text", required: true },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  {
    key: "memberCoverConfigurations", label: "Member Cover Configuration", group: "OL Policy Setup", icon: Shield,
    color: "#eab308", gradient: "linear-gradient(135deg, #eab308, #facc15)",
    fetchFn: olSetup.listMemberCoverConfigurations, createFn: (d) => olSetup.createMemberCoverConfiguration(d),
    updateFn: (id, d) => olSetup.updateMemberCoverConfiguration(id, d), deleteFn: (id) => olSetup.deleteMemberCoverConfiguration(id),
    fields: [
      { key: "code", label: "Code", type: "text", required: true },
      { key: "name", label: "Name", type: "text", required: true },
      { key: "max_dependents", label: "Max Dependents", type: "number", required: false },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  {
    key: "surrenderSetup", label: "Surrender Setup", group: "OL Policy Setup", icon: HandCoins,
    color: "#f43f5e", gradient: "linear-gradient(135deg, #f43f5e, #fb7185)",
    fetchFn: olSetup.listSurrenderSetups, createFn: (d) => olSetup.createSurrenderSetup(d),
    updateFn: (id, d) => olSetup.updateSurrenderSetup(id, d), deleteFn: (id) => olSetup.deleteSurrenderSetup(id),
    fields: [
      { key: "code", label: "Code", type: "text", required: true },
      { key: "min_years_in_force", label: "Min Years in Force", type: "number", required: true },
      { key: "penalty_percentage", label: "Penalty %", type: "number", required: true },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  {
    key: "paidUpSetup", label: "Paid Up Setup", group: "OL Policy Setup", icon: Wallet,
    color: "#22c55e", gradient: "linear-gradient(135deg, #22c55e, #4ade80)",
    fetchFn: olSetup.listPaidUpSetups, createFn: (d) => olSetup.createPaidUpSetup(d),
    updateFn: (id, d) => olSetup.updatePaidUpSetup(id, d), deleteFn: (id) => olSetup.deletePaidUpSetup(id),
    fields: [
      { key: "code", label: "Code", type: "text", required: true },
      { key: "min_years_in_force", label: "Min Years in Force", type: "number", required: true },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  {
    key: "surrenderValueRates", label: "Surrender Value Rates", group: "OL Policy Setup", icon: TrendingDown,
    color: "#d946ef", gradient: "linear-gradient(135deg, #d946ef, #e879f9)",
    fetchFn: olSetup.listSurrenderValueRates, createFn: (d) => olSetup.createSurrenderValueRate(d),
    updateFn: (id, d) => olSetup.updateSurrenderValueRate(id, d), deleteFn: (id) => olSetup.deleteSurrenderValueRate(id),
    fields: [
      { key: "policy_year", label: "Policy Year", type: "number", required: true },
      { key: "rate_factor", label: "Rate Factor", type: "number", required: true },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  {
    key: "paidUpRates", label: "Paid Up Rates", group: "OL Policy Setup", icon: Banknote,
    color: "#64748b", gradient: "linear-gradient(135deg, #64748b, #94a3b8)",
    fetchFn: olSetup.listPaidUpRates, createFn: (d) => olSetup.createPaidUpRate(d),
    updateFn: (id, d) => olSetup.updatePaidUpRate(id, d), deleteFn: (id) => olSetup.deletePaidUpRate(id),
    fields: [
      { key: "policy_year", label: "Policy Year", type: "number", required: true },
      { key: "rate_factor", label: "Rate Factor", type: "number", required: true },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  {
    key: "commitmentStatuses", label: "Commitment Statuses", group: "OL Policy Setup", icon: CheckCircle,
    color: "#0284c7", gradient: "linear-gradient(135deg, #0284c7, #38bdf8)",
    fetchFn: olSetup.listCommitmentStatuses, createFn: (d) => olSetup.createCommitmentStatus(d),
    updateFn: (id, d) => olSetup.updateCommitmentStatus(id, d), deleteFn: (id) => olSetup.deleteCommitmentStatus(id),
    fields: [
      { key: "code", label: "Code", type: "text", required: true },
      { key: "name", label: "Name", type: "text", required: true },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  {
    key: "healthQuestions", label: "Health Questions", group: "OL Policy Setup", icon: HeartPulse,
    color: "#f43f5e", gradient: "linear-gradient(135deg, #f43f5e, #fb7185)",
    fetchFn: olSetup.listHealthQuestions, createFn: (d) => olSetup.createHealthQuestion(d),
    updateFn: (id, d) => olSetup.updateHealthQuestion(id, d), deleteFn: (id) => olSetup.deleteHealthQuestion(id),
    fields: [
      { key: "code", label: "Question Code", type: "text", required: true },
      { key: "question_text", label: "Question Text", type: "text", required: true },
      { key: "category", label: "Category", type: "text", required: false },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  {
    key: "healthQuestionnaires", label: "Health Questionnaires", group: "OL Policy Setup", icon: FileText,
    color: "#3b82f6", gradient: "linear-gradient(135deg, #3b82f6, #60a5fa)",
    fetchFn: olSetup.listHealthQuestionnaires, createFn: (d) => olSetup.createHealthQuestionnaire(d),
    updateFn: (id, d) => olSetup.updateHealthQuestionnaire(id, d), deleteFn: (id) => olSetup.deleteHealthQuestionnaire(id),
    fields: [
      { key: "code", label: "Questionnaire Code", type: "text", required: true },
      { key: "name", label: "Name", type: "text", required: true },
      { key: "version", label: "Version", type: "text", required: false },
      { key: "effective_date", label: "Effective Date", type: "date", required: true },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  {
    key: "gracePeriodNotificationSchedules", label: "Grace Period Notification Schedule", group: "OL Policy Setup", icon: Bell,
    color: "#f59e0b", gradient: "linear-gradient(135deg, #f59e0b, #fbbf24)",
    fetchFn: olSetup.listGracePeriodNotificationSchedules, createFn: (d) => olSetup.createGracePeriodNotificationSchedule(d),
    updateFn: (id, d) => olSetup.updateGracePeriodNotificationSchedule(id, d), deleteFn: (id) => olSetup.deleteGracePeriodNotificationSchedule(id),
    fields: [
      { key: "days_past_due", label: "Days Past Due", type: "number", required: true },
      { key: "notification_type", label: "Notification Type", type: "text", required: true },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
  {
    key: "reinstatementWindows", label: "Reinstatement Window", group: "OL Policy Setup", icon: Undo2,
    color: "#10b981", gradient: "linear-gradient(135deg, #10b981, #34d399)",
    fetchFn: olSetup.listReinstatementWindows, createFn: (d) => olSetup.createReinstatementWindow(d),
    updateFn: (id, d) => olSetup.updateReinstatementWindow(id, d), deleteFn: (id) => olSetup.deleteReinstatementWindow(id),
    fields: [
      { key: "max_months", label: "Max Months", type: "number", required: true },
      { key: "requires_medical", label: "Requires Medical", type: "boolean", required: false },
      { key: "is_active", label: "Is Active", type: "boolean", required: false },
    ],
  },
]
"""

pattern = r"const SETUP_CATEGORIES: SetupCategory\[\] = \[\s*.*?\n\]"
ol_setup_content = re.sub(pattern, setup_categories, ol_setup_content, flags=re.DOTALL)

icons_used = set(re.findall(r"icon:\s*([A-Z][a-zA-Z0-9]+)", setup_categories))
import_icons_str = "import { " + ", ".join(icons_used) + ", Plus, Edit2, Trash2, X, Search, ChevronRight, AlertCircle, Filter, Loader2, PlayCircle } from 'lucide-react'"

import_idx = ol_setup_content.find("import {")
import_end_idx = ol_setup_content.find("from \"lucide-react\"", import_idx) + 19
if import_idx != -1 and import_end_idx > import_idx:
    ol_setup_content = ol_setup_content[:import_idx] + import_icons_str + ol_setup_content[import_end_idx:]

os.makedirs("src/pages/ordinary-life", exist_ok=True)
with open("src/pages/ordinary-life/OLSetup.tsx", "w") as f:
    f.write(ol_setup_content)

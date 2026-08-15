/**
 * Auth types matching the Django backend response shape.
 *
 * Backend uses djangorestframework-camel-case renderer, so all snake_case
 * fields are converted to camelCase in JSON responses.
 *
 * Login response envelope:
 *   { success, statusCode, message, data: { accessToken, refreshToken, ... }, meta }
 * 2FA required:
 *   { success, statusCode, message, data: { requires2FA, userId }, meta }
 */

export interface Permission {
  module: string
  action: string
}

export interface AuthUser {
  id: string
  username: string
  email: string
  firstName: string
  lastName: string
  fullName: string
  phoneNumber: string | null
  userType: string
  isActive: boolean
  isApproved: boolean
  is2faEnabled: boolean
  emailVerified: boolean
  phoneVerified: boolean
  department: string | null
  jobTitle: string | null
  employeeId: string | null
  avatar: string | null
  lastLogin: string | null
  dateJoined: string
  permissions: Permission[]
  groups: string[]
}

export interface LoginTokens {
  accessToken: string
  refreshToken: string
  accessExpiresIn: number
  refreshExpiresIn: number
}

export interface LoginSuccessData extends LoginTokens {
  user: AuthUser
}

export interface Login2FARequiredData {
  requires2FA: true
  userId: string
}

export interface LoginResult {
  success: boolean
  statusCode: number
  message: string
  data: LoginSuccessData | Login2FARequiredData
  meta: { timestamp: string; version: string }
}

export interface Setup2FAResult {
  qrCodeUrl: string
  secret: string
  backupCodes: string[]
}

// ---- Dashboard types (existing) ----

export interface HeroStat {
  label: string
  value: string
  icon: "growth" | "users" | "revenue"
}

export interface PolicyBreakdown {
  label: string
  count: number
  delta: number
  up: boolean
}

export interface PoliciesIssued {
  total: number
  delta: number
  up: boolean
  breakdown: PolicyBreakdown[]
}

export interface ClaimGauge {
  label: string
  percent: number
  claims: number
  color: string
}

export interface PartnerBar {
  label: string
  left: number
  right: number
}

export interface PartnersOnboarded {
  total: number
  bars: PartnerBar[]
}

export interface DebitedSegment {
  label: string
  value: string
  color: string
}

export interface DebitedAmount {
  total: string
  segments: DebitedSegment[]
  gaugePercent: number
}

export interface QuotationSeries {
  name: string
  color: string
  points: number[]
}

export interface Quotations {
  total: number
  labels: string[]
  series: QuotationSeries[]
  legend: { label: string; color: string; percent: number; count: number }[]
}

export interface NotificationStatus {
  label: string
  count: number
  tone: "warning" | "success" | "destructive" | "muted"
}

export interface NotificationItem {
  id: string
  tag?: string
  title: string
  status: string
  time: string
  amount?: string
}

export interface NotificationsData {
  unread: number
  statuses: NotificationStatus[]
  items: NotificationItem[]
}

export interface TodoItem {
  id: string
  title: string
  date: string
}

export interface LeadItem {
  rank: number
  place: string
  name: string
  amount: string
}

export interface DashboardData {
  hero: HeroStat[]
  policies: PoliciesIssued
  claims: ClaimGauge[]
  partners: PartnersOnboarded
  debited: DebitedAmount
  quotations: Quotations
  notifications: NotificationsData
  todos: TodoItem[]
  leads: LeadItem[]
}

export type DashboardTaskStatus = "TODO" | "IN_PROGRESS" | "DONE" | "ARCHIVED"
export type DashboardTaskPriority = "LOW" | "MEDIUM" | "HIGH" | "URGENT"

export interface DashboardTaskRecord {
  id: number
  title: string
  description: string
  status: DashboardTaskStatus
  priority: DashboardTaskPriority
  dueAt: string | null
  route: string
  entityType: string
  entityId: string
  completedAt: string | null
  createdAt: string
  updatedAt: string
}

export type DashboardAlertSeverity = "INFO" | "WARNING" | "CRITICAL"
export type DashboardAlertStatus = "OPEN" | "ACKNOWLEDGED" | "DISMISSED"

export interface DashboardAlertRecord {
  id: number
  title: string
  message: string
  severity: DashboardAlertSeverity
  status: DashboardAlertStatus
  route: string
  entityType: string
  entityId: string
  acknowledgedAt: string | null
  createdAt: string
  updatedAt: string
}

export interface DashboardNotificationRecord {
  id: number
  kind: string
  title: string
  message: string
  status: string
  route: string
  entityType: string
  entityId: string
  isRead: boolean
  createdAt: string
}

export interface GlobalSearchResult {
  id: string
  type: string
  kind: string
  label: string
  subtitle: string
  route: string
}

export interface CurrencyPairRecord {
  id: number
  baseCurrency: string
  quoteCurrency: string
  isActive: boolean
  targetRate: string | null
  latestRate: string | null
  latestAsOf: string | null
  isStale: boolean
  createdAt: string
  updatedAt: string
}

// ============================================================================
// Partner Onboarding types (camelCase — backend uses camelCase renderer)
// ============================================================================

export type PartnerType = "INDIVIDUAL" | "CORPORATE"
export type KycStatus = "NOT_SET" | "CLEARED" | "PENDING" | "REJECTED" | "REQUIRE_MORE_INFO"

export interface UnifiedOnboardingRecord {
  id: string
  recordType: "APPLICATION" | "PARTNER"
  applicationId: string | null
  partnerId: string | null
  referenceNumber: string
  displayName: string
  partnerType: PartnerType
  email: string
  mobileNumber: string
  applicationStatus: ApplicationStatus | null
  kycStatus: KycStatus | null
  createdAt: string
}

export type ApplicationStatus =

  | "ACTIVE"
  | "DRAFT"
  | "SUBMITTED"
  | "UNDER_REVIEW"
  | "PENDING_DOCUMENTS"
  | "COMPLIANCE_CHECK"
  | "APPROVED"
  | "CONVERTED"
  | "REJECTED"
  | "SUSPENDED"

export interface PartnerApplicationList {
  id: string
  applicationNumber: string
  partnerType: PartnerType
  displayName: string
  title: string
  surname: string
  mobileNumber: string
  nationality: string
  identificationType: string
  email: string
  status: ApplicationStatus
  politicalRisk: string
  amlRisk: string
  submittedAt: string | null
  createdAt: string
  updatedAt: string
  createdByName: string | null
  updatedByName: string | null
}

export interface ApplicationDocument {
  id: string
  applicationPartnerType?: string | null
  documentType: string
  documentName: string
  file: string
  fileSize: number | null
  mimeType: string
  isVerified: boolean
  verifiedBy: string | null
  verifiedAt: string | null
  verificationNotes: string
  uploadedBy: string | null
  createdAt: string
}

export interface ApplicationTask {
  id: string
  taskType: string
  title: string
  description: string
  assignedTo: string | null
  status: "PENDING" | "IN_PROGRESS" | "COMPLETED" | "CANCELLED"
  priority: "LOW" | "MEDIUM" | "HIGH" | "URGENT"
  dueDate: string | null
  completedAt: string | null
  completedBy: string | null
  notes: string
  createdAt: string
  updatedAt: string
}

export interface PartnerApplicationEvent {
  id: string
  eventType: string
  fromStatus: string
  toStatus: string
  actor: string | null
  actorName: string | null
  notes: string
  metadata: Record<string, unknown>
  createdAt: string
}

export interface PartnerApplicationDetail {
  id: string
  applicationNumber: string
  partnerType: PartnerType
  status: ApplicationStatus
  identificationType: string
  identificationNumber: string
  title: string
  firstName: string
  otherName: string
  surname: string
  gender: string
  dateOfBirth: string | null
  maritalStatus: string
  occupation: string
  nationality: string
  companyName: string
  tinNumber: string
  incorporationDate: string | null
  companyIncorporation: string
  industry: string
  contactPerson: string
  contactPersonPhone: string
  contactPersonEmail: string
  physicalAddress: string
  postalAddress: string
  email: string
  telephoneNumber: string
  mobileNumber: string
  politicalRisk: string
  amlRisk: string
  submittedBy: string | null
  reviewedBy: string | null
  approvedBy: string | null
  rejectionReason: string
  complianceNotes: string
  submittedAt: string | null
  reviewedAt: string | null
  approvedAt: string | null
  convertedAt: string | null
  createdAt: string
  updatedAt: string
  documents: ApplicationDocument[]
  tasks: ApplicationTask[]
  events: PartnerApplicationEvent[]
}

export interface ChoicesResponse {
  partnerTypes: { value: string; label: string }[]
  partnerCategories: { value: string; label: string }[]
  identificationTypes: { value: string; label: string }[]
  titles: { value: string; label: string }[]
  genders: { value: string; label: string }[]
  maritalStatuses: { value: string; label: string }[]
  politicalRisks: { value: string; label: string }[]
  amlRisks: { value: string; label: string }[]
  industries: { value: string; label: string }[]
  nationalities: { value: string; label: string }[]
  applicationStatuses: { value: string; label: string }[]
  documentTypes: { value: string; label: string }[]
  taskTypes: { value: string; label: string }[]
  taskStatuses: { value: string; label: string }[]
  taskPriorities: { value: string; label: string }[]
  systemPartnerTypes: { value: string; label: string }[]
  branches: { value: string; label: string }[]
  locations: { value: string; label: string; branchId: string }[]
  regions: { value: string; label: string }[]
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface ApiEnvelope<T> {
  success: boolean
  statusCode: number
  message: string
  data: T
  meta: { timestamp: string; version: string }
}

export interface BulkUploadResult {
  imported: number
  skipped: number
  errors: { row: number; message: string }[]
}

export interface ApplicationPartnerType {
  id: string
  application: string
  partnerType: string
  partnerTypeName: string
  branch: string | null
  branchName: string | null
  location: string | null
  locationName: string | null
  region: string
  shareDataExternally: boolean
  createdAt: string
}

export interface ApplicationContact {
  id: string
  contactType: string
  firstName: string
  lastName: string
  email: string
  phone: string
  mobile: string
  designation: string
  isPrimary: boolean
  notes: string
  createdAt: string
  updatedAt: string
}

export interface ApplicationBankAccount {
  id: string
  bankName: string
  branchName: string
  accountName: string
  accountNumber: string
  swiftCode: string
  iban: string
  currency: string
  isPrimary: boolean
  isVerified: boolean
  notes: string
  createdAt: string
  updatedAt: string
}

export interface BranchOption {
  value: string
  label: string
}

export interface LocationOption {
  value: string
  label: string
  branch_id: string
}

// ============================================================================
// System Parameters types
// ============================================================================

export interface ParameterGroup {
  id: string
  parent: string | null
  name: string
  code: string
  description: string
  sortOrder: number
  isActive: boolean
  children?: ParameterGroup[]
  parameterCount?: number
  createdAt: string
  updatedAt: string
}

export interface SystemParameter {
  id: string
  group: string
  groupName: string
  name: string
  code: string
  description: string
  valueType: "STRING" | "TEXT" | "INTEGER" | "FLOAT" | "BOOLEAN" | "JSON" | "FILE"
  value: string | number | boolean | Record<string, unknown> | null
  stringValue: string | null
  integerValue: number | null
  floatValue: number | null
  booleanValue: boolean | null
  jsonValue: Record<string, unknown> | null
  fileValue: string | null
  isActive: boolean
  isEncrypted: boolean
  sortOrder: number
  createdAt: string
  updatedAt: string
}

export interface ChoiceList {
  id: string
  group: string | null
  code: string
  name: string
  description: string
  isActive: boolean
  options: ChoiceOption[]
  createdAt: string
  updatedAt: string
}

export interface ChoiceOption {
  id: string
  choiceList: string
  code: string
  label: string
  isDefault: boolean
  isActive: boolean
  sortOrder: number
  metadata: Record<string, unknown> | null
  createdAt: string
  updatedAt: string
}

// ============================================================================
// Partner Master Domain types (Phase 2 - new normalized structure)
// ============================================================================

export interface IndividualProfile {
  id: string
  identificationType: string
  identificationNumber: string
  title: string
  firstName: string
  otherName: string
  surname: string
  gender: string
  dateOfBirth: string | null
  maritalStatus: string
  occupation: string
  nationality: string
}

export interface CorporateProfile {
  id: string
  companyName: string
  tinNumber: string
  incorporationDate: string | null
  industry: string
  contactPerson: string
  contactPersonPhone: string
  contactPersonEmail: string
}

export interface PartnerTypeAssignment {
  id: string
  partner: string
  partnerType: string
  partnerTypeName: string
  partnerTypeCode: string
  branch: string | null
  branchName: string | null
  location: string | null
  locationName: string | null
  shareDataExternally: boolean
  status: "ACTIVE" | "INACTIVE"
  effectiveDate: string | null
  createdAt: string
  updatedAt: string
}

export interface PartnerDetail {
  id: string
  partnerNumber: string
  partnerType: PartnerType
  partnerCategory: PartnerType
  status: string
  displayName: string
  identificationType: string
  identificationNumber: string
  title: string
  firstName: string
  otherName: string
  surname: string
  gender: string
  dateOfBirth: string | null
  maritalStatus: string
  occupation: string
  nationality: string
  companyName: string
  tinNumber: string
  incorporationDate: string | null
  industry: string
  contactPerson: string
  contactPersonPhone: string
  contactPersonEmail: string
  physicalAddress: string
  postalAddress: string
  email: string
  telephoneNumber: string
  mobileNumber: string
  politicalRisk: string
  amlRisk: string
  createdFromApplication: string | null
  individualProfile: IndividualProfile | null
  corporateProfile: CorporateProfile | null
  typeAssignments: PartnerTypeAssignment[]
  activatedAt: string | null
  deactivatedAt: string | null
  deactivationReason: string
  createdAt: string
  updatedAt: string
}

// ============================================================================
// Partner Type / Branch / Location (DB-driven CRUD models)
// ============================================================================

export interface PartnerTypeDocumentRequirement {
  id: string
  partnerType: string
  partnerTypeName: string
  code: string
  description: string
  isRequired: boolean
  isMandatory: boolean
  sortOrder: number
  isActive: boolean
  createdBy: string | null
  createdByName: string | null
  updatedBy: string | null
  updatedByName: string | null
  createdAt: string
  updatedAt: string
}

export interface PartnerTypeRecord {
  id: string
  code: string
  name: string
  description: string
  branchId: string | null
  branchName: string | null
  locationId: string | null
  locationName: string | null
  isActive: boolean
  createdAt: string
  updatedAt: string
}

export interface BranchRecord {
  id: string
  code: string
  name: string
  isActive: boolean
}

export interface LocationRecord {
  id: string
  branchId: string
  code: string
  name: string
  isActive: boolean
}

// ============================================================================
// Partner Type Setup Configuration (Phase 3 - PartnerType Setup Engine)
// ============================================================================

export interface PartnerTypeFieldConfiguration {
  id: string
  partnerType: string
  partnerTypeName: string
  fieldName: string
  fieldCode: string
  fieldType: "TEXT" | "NUMBER" | "DATE" | "BOOLEAN" | "DROPDOWN" | "MULTI_SELECT" | "FILE" | "CURRENCY" | "PERCENTAGE"
  defaultValue: string
  isRequired: boolean
  validationRules: Record<string, unknown>
  displayOrder: number
  visibilityRules: Record<string, unknown>
  isActive: boolean
  createdAt: string
  updatedAt: string
}

export interface PartnerTypeContactRequirement {
  id: string
  partnerType: string
  partnerTypeName: string
  contactType: string
  isRequired: boolean
  multipleAllowed: boolean
  displayOrder: number
  isActive: boolean
  createdAt: string
  updatedAt: string
}

export interface PartnerTypeBankRequirement {
  id: string
  partnerType: string
  partnerTypeName: string
  bankType: string
  isRequired: boolean
  multipleAllowed: boolean
  validationRules: Record<string, unknown>
  displayOrder: number
  isActive: boolean
  createdAt: string
  updatedAt: string
}

// ============================================================================
// Partner Type Assignment Setup Data (Phase 3 - transaction/instance data)
// ============================================================================

export interface PartnerDocument {
  id: string
  assignment: string
  documentRequirement: string
  documentRequirementCode: string
  documentRequirementName: string
  allowMultipleUploads: boolean
  file: string
  documentNumber: string
  issueDate: string | null
  expiryDate: string | null
  uploadedBy: string | null
  uploadedAt: string | null
  status: "NOT_SUBMITTED" | "UPLOADED" | "UNDER_REVIEW" | "APPROVED" | "REJECTED" | "EXPIRED"
  verificationNotes: string
  createdAt: string
  updatedAt: string
}

export interface PartnerDynamicFieldValue {
  id: string
  assignment: string
  fieldConfig: string
  fieldCode: string
  fieldName: string
  fieldType: string
  valueJson: unknown
  createdAt: string
  updatedAt: string
}

export interface ApplicationFieldValue {
  id: string
  application: string
  fieldConfig: string
  fieldCode: string
  fieldName: string
  fieldType: string
  valueJson: unknown
  createdAt: string
  updatedAt: string
}

export interface PartnerAssignmentContact {
  id: string
  assignment: string
  contactRequirement: string
  configContactType: string
  contactType: string
  firstName: string
  lastName: string
  email: string
  phone: string
  mobile: string
  designation: string
  isPrimary: boolean
  notes: string
  createdAt: string
  updatedAt: string
}

export interface PartnerAssignmentBankAccount {
  id: string
  assignment: string
  bankRequirement: string
  configBankType: string
  bankType: string
  bankName: string
  branchName: string
  accountName: string
  accountNumber: string
  swiftCode: string
  currency: string
  isPrimary: boolean
  notes: string
  createdAt: string
  updatedAt: string
}

export interface PartnerKYCProfile {
  id: string
  assignment: string
  kycStatus: "NOT_SET" | "PENDING" | "CLEARED" | "REJECTED" | "ESCALATED"
  riskScore: number | null
  riskLevel: string
  lastReviewDate: string | null
  reviewedBy: string | null
  notes: string
  createdAt: string
  updatedAt: string
}

export interface SetupSummary {
  documents: {
    total: number
    submitted: number
    required: number
    requiredSubmitted: number
    progressPct: number
  }
  fields: {
    total: number
    filled: number
    required: number
    requiredFilled: number
    progressPct: number
  }
  contacts: {
    total: number
    submitted: number
    progressPct: number
  }
  banks: {
    total: number
    submitted: number
    progressPct: number
  }
  kyc: {
    status: string
    riskScore: number | null
    riskLevel: string
  }
}

export interface PartnerTypeAssignmentSetup {
  id: string
  partner: string
  partnerType: string
  setupSummary: SetupSummary
  documents: PartnerDocument[]
  fieldValues: PartnerDynamicFieldValue[]
  assignmentContacts: PartnerAssignmentContact[]
  assignmentBankAccounts: PartnerAssignmentBankAccount[]
  kycProfile: PartnerKYCProfile | null
}

// ============================================================================
// Partner List (from /api/v1/partners/)
// ============================================================================

export interface PartnerListItem {
  id: string
  partnerNumber: string
  partnerType: string
  partnerCategory: string | null
  displayName: string
  email: string
  mobileNumber: string
  status: string
  politicalRisk: string
  amlRisk: string
  createdAt: string
}

// ============================================================================
// Phase 4 — Enterprise Governance types
// ============================================================================

export interface AuditLog {
  id: string
  user: string | null
  userEmail: string | null
  userName: string
  actionType: string
  entityType: string
  entityId: string
  entityRepr: string
  beforeState: Record<string, unknown> | null
  afterState: Record<string, unknown> | null
  description: string
  ipAddress: string | null
  userAgent: string
  requestId: string
  timestamp: string
}

export type ApprovalStatus = "PENDING" | "APPROVED" | "REJECTED" | "CANCELLED"

export interface ApprovalRequest {
  id: string
  module: string
  entityType: string
  entityId: string
  entityRepr: string
  action: string
  requestedData: Record<string, unknown> | null
  currentData: Record<string, unknown> | null
  status: ApprovalStatus
  submittedBy: string | null
  submittedByEmail: string | null
  submittedByName: string | null
  submittedAt: string
  reviewedBy: string | null
  reviewedByEmail: string | null
  reviewedByName: string | null
  reviewedAt: string | null
  comments: string
  createdAt: string
  updatedAt: string
}

export interface ConfigurationVersion {
  id: string
  module: string
  versionNumber: number
  effectiveFrom: string
  effectiveTo: string | null
  status: "DRAFT" | "ACTIVE" | "RETIRED"
  configurationData: Record<string, unknown>
  changeSummary: string
  createdBy: string | null
  createdByEmail: string | null
  createdByName: string | null
  createdAt: string
  notes: string
}

export interface DocumentVersion {
  id: string
  document: string
  versionNumber: number
  file: string
  fileName: string
  fileSize: number | null
  mimeType: string
  status: string
  notes: string
  uploadedBy: string | null
  uploadedByEmail: string | null
  uploadedAt: string
  verificationStatus: string
  verifiedBy: string | null
  verifiedByEmail: string | null
  verifiedAt: string | null
  verificationNotes: string
}

export interface KYCReviewHistory {
  id: string
  kycProfile: string
  reviewType: "INITIAL" | "PERIODIC" | "ENHANCED_DUE_DILIGENCE" | "HIGH_RISK_ESCALATION" | "REVIEW"
  previousKycStatus: string
  newKycStatus: string
  previousRiskScore: number | null
  newRiskScore: number | null
  previousRiskLevel: string
  newRiskLevel: string
  reviewedBy: string | null
  reviewedByEmail: string | null
  reviewedByName: string | null
  decisionDate: string
  comments: string
  createdAt: string
}

export interface PartnerTypeAssignmentHistory {
  id: string
  assignment: string
  previousStatus: string
  newStatus: string
  reason: string
  changedBy: string | null
  changedByEmail: string | null
  changedByName: string | null
  changedAt: string
  eventType?: "STATUS" | "AUDIT"
  action?: string
  description?: string
  actorName?: string | null
  createdAt?: string
  entityType?: string
  objectId?: string
  changedFields?: string[]
  beforeState?: Record<string, unknown> | null
  afterState?: Record<string, unknown> | null
  sourceChannel?: string
}

export interface ComplianceOverview {
  totalPartners: number
  activePartners: number
  kycPending: number
  kycCleared: number
  kycRejected: number
  kycEscalated: number
  documentsPending: number
  documentsExpired: number
  highRiskPartners: number
}

export interface AuditStats {
  total: number
  days: number
  byAction: Record<string, number>
  byEntity: Record<string, number>
}

export interface ApprovalStats {
  total: number
  pending: number
  approved: number
  rejected: number
  cancelled: number
}

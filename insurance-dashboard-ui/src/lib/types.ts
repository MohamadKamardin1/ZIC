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

// ============================================================================
// Partner Onboarding types (camelCase — backend uses camelCase renderer)
// ============================================================================

export type PartnerType = "INDIVIDUAL" | "CORPORATE"
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

export const STATUS_LABELS: Record<ApplicationStatus, string> = {
  ACTIVE: "Active",
  DRAFT: "Draft",
  SUBMITTED: "Submitted",
  UNDER_REVIEW: "Under Review",
  PENDING_DOCUMENTS: "Pending Docs",
  COMPLIANCE_CHECK: "Compliance",
  APPROVED: "Approved",
  CONVERTED: "Converted",
  REJECTED: "Rejected",
  SUSPENDED: "Suspended",
}

export const STATUS_COLORS: Record<ApplicationStatus, string> = {
  ACTIVE: "bg-green-100 text-green-700",
  DRAFT: "bg-gray-100 text-gray-700",
  SUBMITTED: "bg-blue-100 text-blue-700",
  UNDER_REVIEW: "bg-purple-100 text-purple-700",
  PENDING_DOCUMENTS: "bg-amber-100 text-amber-700",
  COMPLIANCE_CHECK: "bg-orange-100 text-orange-700",
  APPROVED: "bg-green-100 text-green-700",
  CONVERTED: "bg-emerald-100 text-emerald-700",
  REJECTED: "bg-red-100 text-red-700",
  SUSPENDED: "bg-yellow-100 text-yellow-700",
}

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
}

export interface ChoicesResponse {
  partnerTypes: { value: string; label: string }[]
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

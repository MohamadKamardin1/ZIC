import { Navigate, Route, Routes } from "react-router-dom"
import { lazy, Suspense, type ReactNode } from "react"
import { useAuth } from "./lib/auth"
import { RequirePermission, AccessGate } from "./lib/access"
import Login from "./pages/Login"
import Dashboard from "./pages/Dashboard"
import DashboardLayout from "./components/layout/DashboardLayout"
import OnboardingList from "./pages/onboarding/OnboardingList"
import ApplicationForm from "./pages/onboarding/ApplicationForm"
import ApplicationDetail from "./pages/onboarding/ApplicationDetail"
import GeneralParameters from "./pages/system-parameters/GeneralParameters"
import PartnerParameters from "./pages/system-parameters/PartnerParameters"
import PartnerWorkflow from "./pages/system-parameters/PartnerWorkflow"
import PartnerChoices from "./pages/system-parameters/PartnerChoices"
import PartnerTypeList from "./pages/system-parameters/PartnerTypeList"
import PartnerTypeSetup from "./pages/system-parameters/PartnerTypeSetup"
import PartnerList from "./pages/partners/PartnerList"
import PartnerDetail from "./pages/partners/PartnerDetail"
import PartnerEdit from "./pages/partners/PartnerEdit"
import Branches from "./pages/system-parameters/Branches"
import Locations from "./pages/system-parameters/Locations"
import PartnerTypeDocuments from "./pages/system-parameters/PartnerTypeDocuments"
import PartnerTypeFormFields from "./pages/system-parameters/PartnerTypeFormFields"
import PartnerTypeContacts from "./pages/system-parameters/PartnerTypeContacts"
import PartnerTypeBanks from "./pages/system-parameters/PartnerTypeBanks"
import PartnerDocuments from "./pages/system-parameters/PartnerDocuments"
import PartnerFields from "./pages/system-parameters/PartnerFields"
import PartnerContactTypes from "./pages/system-parameters/PartnerContactTypes"
import PartnerBankTypes from "./pages/system-parameters/PartnerBankTypes"
import PartnerCompliance from "./pages/system-parameters/PartnerCompliance"
import PartnerValidation from "./pages/system-parameters/PartnerValidation"
import PartnerNumbering from "./pages/system-parameters/PartnerNumbering"
import PartnerSchedules from "./pages/system-parameters/PartnerSchedules"
import UserParameters from "./pages/system-parameters/UserParameters"
import PasswordPolicy from "./pages/system-parameters/PasswordPolicy"
import ReinsuranceParameters from "./pages/system-parameters/ReinsuranceParameters"
import PermissionGroups from "./pages/user-management/PermissionGroups"
import Permissions from "./pages/user-management/Permissions"
import UserGroups from "./pages/user-management/UserGroups"
import Users from "./pages/user-management/Users"
import GLSetup from "./pages/group-life/GLSetup"
import OLSetup from "./pages/ordinary-life/OLSetup"
import OLDefaultSetup from "./pages/ordinary-life/OLDefaultSetup"
import OLPolicySetup from "./pages/ordinary-life/OLPolicySetup"
import OLProductSetup from "./pages/ordinary-life/OLProductSetup"
import OLProductRating from "./pages/ordinary-life/OLProductRating"
import OLRiderSetup from "./pages/ordinary-life/OLRiderSetup"
import OLAgentManagement from "./pages/ordinary-life/OLAgentManagement"
import OLLoanSetup from "./pages/ordinary-life/OLLoanSetup"
import OLParameterPlaceholder from "./pages/ordinary-life/OLParameterPlaceholder"
import OLDropdownConfiguration from "./pages/ordinary-life/OLDropdownConfiguration"
import OLMOrbClaimSetup from "./pages/ordinary-life/OLMedicalClaimSetup"
import OLApplications from "./pages/ordinary-life/OLApplications"
import OLDocuments from "./pages/ordinary-life/OLDocuments"
import OLNotes from "./pages/ordinary-life/OLNotes"
import OLApprovals from "./pages/ordinary-life/OLApprovals"
import OLAuditHistory from "./pages/ordinary-life/OLAuditHistory"
const OLQuotations = lazy(() => import("./pages/ordinary-life/OLQuotations"))
const OLQuotationDetail = lazy(() => import("./pages/ordinary-life/OLQuotationDetail"))
const OLQuotationWizard = lazy(() => import("./pages/ordinary-life/OLQuotationWizard"))
import OLCommitments from "./pages/ordinary-life/OLCommitments"
import CommitmentDetailPage from "./pages/ordinary-life/CommitmentDetail"
import OLProposals from "./pages/ordinary-life/OLProposals"
import OLPolicies from "./pages/ordinary-life/OLPolicies"
import OLLoans from "./pages/ordinary-life/OLLoans"
import OLWithdrawals from "./pages/ordinary-life/OLWithdrawals"
import OLClaims from "./pages/ordinary-life/OLClaims"
import OLMaturityInstallments from "./pages/ordinary-life/OLMaturityInstallments"
import GLQuotations from "./pages/group-life/GLQuotations"
import GLSchemes from "./pages/group-life/GLSchemes"
import GLMembers from "./pages/group-life/GLMembers"
import GLClaims from "./pages/group-life/GLClaims"
import GLMedicalUW from "./pages/group-life/GLMedicalUW"
import GCSetup from "./pages/group-credit/GCSetup"
import GCQuotations from "./pages/group-credit/GCQuotations"
import GCSchemes from "./pages/group-credit/GCSchemes"
import GCBorrowers from "./pages/group-credit/GCBorrowers"
import GCClaims from "./pages/group-credit/GCClaims"
import GCMedicalUW from "./pages/group-credit/GCMedicalUW"
import GCRenewals from "./pages/group-credit/GCRenewals"
import FOReceipts from "./pages/front-office/FOReceipts"
import FOCommissions from "./pages/front-office/FOCommissions"
import FOCommissionStatements from "./pages/front-office/FOCommissionStatements"
import FORequisitions from "./pages/front-office/FORequisitions"
import FOPayments from "./pages/front-office/FOPayments"
import FOParameters from "./pages/front-office/FOParameters"
import WorkspacePage from "./pages/dashboard/WorkspacePage"
import UiKitSandbox from "./pages/UiKitSandbox"

function RequireAuth({ children }: { children: ReactNode }) {
  const { accessToken } = useAuth()
  return accessToken ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  const { accessToken } = useAuth()
  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center bg-[var(--background)] p-6 text-sm font-semibold text-[var(--muted-foreground)]" role="status" aria-live="polite">Loading workspace…</div>}>
      <Routes>
      <Route path="/login" element={accessToken ? <Navigate to="/" replace /> : <Login />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <DashboardLayout />
          </RequireAuth>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="tasks" element={<WorkspacePage section="tasks" />} />
        <Route path="alerts" element={<WorkspacePage section="alerts" />} />
        <Route path="notifications" element={<WorkspacePage section="notifications" />} />
        <Route path="currencies" element={<WorkspacePage section="currencies" />} />
        <Route path="reports" element={<WorkspacePage section="reports" />} />
        <Route path="approvals" element={<WorkspacePage section="approvals" />} />
        <Route path="help" element={<WorkspacePage section="help" />} />
        <Route path="ui-kit" element={<UiKitSandbox />} />
        <Route path="onboarding" element={<OnboardingList />} />
        <Route path="onboarding/new" element={<ApplicationForm />} />
        <Route path="onboarding/:id" element={<ApplicationDetail />} />
        <Route path="onboarding/:id/edit" element={<ApplicationForm />} />
        <Route path="partners" element={<PartnerList />} />
        <Route path="partners/:id" element={<PartnerDetail />} />
        <Route path="partners/:id/edit" element={<PartnerEdit />} />
        <Route path="system-parameters/general" element={<GeneralParameters />} />
        <Route path="system-parameters/partner" element={<PartnerParameters />} />
        <Route path="system-parameters/partner/workflow" element={<PartnerWorkflow />} />
        <Route path="system-parameters/partner/choices" element={<PartnerChoices />} />
        <Route path="system-parameters/partner/documents" element={<PartnerDocuments />} />
        <Route path="system-parameters/partner/fields" element={<PartnerFields />} />
        <Route path="system-parameters/partner/contact-types" element={<PartnerContactTypes />} />
        <Route path="system-parameters/partner/bank-types" element={<PartnerBankTypes />} />
        <Route path="system-parameters/partner/compliance" element={<PartnerCompliance />} />
        <Route path="system-parameters/partner/validation" element={<PartnerValidation />} />
        <Route path="system-parameters/partner/numbering" element={<PartnerNumbering />} />
        <Route path="system-parameters/partner/schedules" element={<PartnerSchedules />} />
        <Route path="system-parameters/partner/partner-types" element={<PartnerTypeList />} />
        <Route path="system-parameters/partner/partner-types/:id/setup" element={<PartnerTypeSetup />} />
        <Route path="system-parameters/partner/branches" element={<Branches />} />
        <Route path="system-parameters/partner/locations" element={<Locations />} />
        <Route path="system-parameters/partner/partner-type-documents" element={<PartnerTypeDocuments />} />
        <Route path="system-parameters/partner/partner-type-form-fields" element={<PartnerTypeFormFields />} />
        <Route path="system-parameters/partner/partner-type-contacts" element={<PartnerTypeContacts />} />
        <Route path="system-parameters/partner/partner-type-banks" element={<PartnerTypeBanks />} />
        <Route path="system-parameters/users" element={<UserParameters />} />
        <Route path="system-parameters/users/password-policy" element={<PasswordPolicy />} />
        <Route path="system-parameters/reinsurance" element={<ReinsuranceParameters />} />
        <Route path="user-management/permission-groups" element={<PermissionGroups />} />
        <Route path="user-management/permissions" element={<Permissions />} />
        <Route path="user-management/user-groups" element={<UserGroups />} />
        <Route path="user-management/users" element={<Users />} />
        <Route path="group-life/setup" element={<GLSetup />} />

        {/* Ordinary Life */}
        <Route path="ordinary-life/setup" element={<OLSetup />} />
        <Route path="ordinary-life/parameters" element={<OLDefaultSetup />} />
        <Route path="ordinary-life/parameters/default-setup" element={<OLDefaultSetup />} />
        <Route path="ordinary-life/parameters/dropdown-configuration" element={<OLDropdownConfiguration />} />
        <Route path="ordinary-life/parameters/:screen" element={<OLDefaultSetup />} />
        <Route path="ordinary-life/parameters/policy-setup" element={<OLPolicySetup />} />
        <Route path="ordinary-life/parameters/product-setup" element={<OLProductSetup />} />
        <Route path="ordinary-life/parameters/product-rating" element={<OLProductRating />} />
        <Route path="ordinary-life/parameters/rider-setup" element={<OLRiderSetup />} />
        <Route path="ordinary-life/parameters/agent-management" element={<OLAgentManagement />} />
        <Route path="ordinary-life/parameters/loan-setup" element={<OLLoanSetup />} />
        <Route path="ordinary-life/parameters/medical-uw" element={<OLMOrbClaimSetup section="medical" />} />
        <Route path="ordinary-life/parameters/claim-setup" element={<OLMOrbClaimSetup section="claims" />} />
        <Route path="ordinary-life/applications" element={<OLApplications />} />
        <Route path="ordinary-life/quotations" element={<OLQuotations />} />
        <Route path="ordinary-life/quotations/new" element={<OLQuotationWizard />} />
        <Route path="ordinary-life/quotations/:id/edit" element={<OLQuotationDetail />} />
        <Route path="ordinary-life/quotations/:id" element={<OLQuotationDetail />} />
        <Route
          path="ordinary-life/commitments"
          element={
            <RequirePermission permission="ol_commitments.view">
              <AccessGate>
                <OLCommitments />
              </AccessGate>
            </RequirePermission>
          }
        />
        <Route
          path="ordinary-life/commitments/:id"
          element={
            <RequirePermission permission="ol_commitments.view">
              <AccessGate>
                <CommitmentDetailPage />
              </AccessGate>
            </RequirePermission>
          }
        />
        <Route path="ordinary-life/proposals" element={<OLProposals />} />
        <Route path="ordinary-life/policies" element={<OLPolicies />} />
        <Route path="ordinary-life/loans" element={<OLLoans />} />
        <Route path="ordinary-life/withdrawals" element={<OLWithdrawals />} />
        <Route path="ordinary-life/claims" element={<OLClaims />} />
        <Route path="ordinary-life/maturity-installments" element={<OLMaturityInstallments />} />
        <Route path="ordinary-life/documents" element={<OLDocuments />} />
        <Route path="ordinary-life/notes" element={<OLNotes />} />
        <Route path="ordinary-life/approvals" element={<OLApprovals />} />
        <Route path="ordinary-life/audit-history" element={<OLAuditHistory />} />
        <Route path="group-life/quotations" element={<GLQuotations />} />
        <Route path="group-life/schemes" element={<GLSchemes />} />
        <Route path="group-life/members" element={<GLMembers />} />
        <Route path="group-life/claims" element={<GLClaims />} />
        <Route path="group-life/medical-uw" element={<GLMedicalUW />} />
        <Route path="group-credit/setup" element={<GCSetup />} />
        <Route path="group-credit/quotations" element={<GCQuotations />} />
        <Route path="group-credit/schemes" element={<GCSchemes />} />
        <Route path="group-credit/renewals" element={<GCRenewals />} />
        <Route path="group-credit/borrowers" element={<GCBorrowers />} />
        <Route path="group-credit/claims" element={<GCClaims />} />
        <Route path="group-credit/medical-uw" element={<GCMedicalUW />} />
        <Route path="front-office/receipts" element={<FOReceipts />} />
        <Route path="front-office/commissions" element={<FOCommissions />} />
        <Route path="front-office/commission-statements" element={<FOCommissionStatements />} />
        <Route path="front-office/requisitions" element={<FORequisitions />} />
        <Route path="front-office/payments" element={<FOPayments />} />
        <Route path="front-office/parameters" element={<FOParameters />} />
      </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}

import { Navigate, Route, Routes } from "react-router-dom"
import { useAuth } from "./lib/auth"
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
import GLQuotations from "./pages/group-life/GLQuotations"
import GLSchemes from "./pages/group-life/GLSchemes"
import GLMembers from "./pages/group-life/GLMembers"
import GLClaims from "./pages/group-life/GLClaims"
import GLMedicalUW from "./pages/group-life/GLMedicalUW"
import type { ReactNode } from "react"

function RequireAuth({ children }: { children: ReactNode }) {
  const { accessToken } = useAuth()
  return accessToken ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  const { accessToken } = useAuth()
  return (
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
        <Route path="group-life/quotations" element={<GLQuotations />} />
        <Route path="group-life/schemes" element={<GLSchemes />} />
        <Route path="group-life/members" element={<GLMembers />} />
        <Route path="group-life/claims" element={<GLClaims />} />
        <Route path="group-life/medical-uw" element={<GLMedicalUW />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

import { Navigate, Route, Routes } from "react-router-dom"
import { useAuth } from "./lib/auth"
import Login from "./pages/Login"
import Dashboard from "./pages/Dashboard"
import DashboardLayout from "./components/layout/DashboardLayout"
import OnboardingList from "./pages/onboarding/OnboardingList"
import ApplicationForm from "./pages/onboarding/ApplicationForm"
import ApplicationDetail from "./pages/onboarding/ApplicationDetail"
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
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

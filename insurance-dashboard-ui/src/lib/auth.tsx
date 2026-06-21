import { createContext, useContext, useState, useCallback, type ReactNode } from "react"
import { login as apiLogin, logout as apiLogout, loadStoredTokens, dropTokens } from "./api"
import type { AuthUser } from "./types"

interface AuthContextValue {
  user: AuthUser | null
  accessToken: string | null
  signIn: (email: string, password: string) => Promise<boolean>
  complete2FA: (otpCode: string) => Promise<void>
  cancel2FA: () => void
  signOut: () => Promise<void>
  requires2FA: boolean
  pendingEmail: string | null
}

const AuthContext = createContext<AuthContextValue | null>(null)

const STORAGE_KEY = "aims_user"

function readStoredUser(): AuthUser | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as AuthUser) : null
  } catch {
    return null
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => readStoredUser())
  const [tokens, setTokens] = useState(() => loadStoredTokens())
  const [requires2FA, setRequires2FA] = useState(false)
  const [pendingCreds, setPendingCreds] = useState<{ email: string; password: string } | null>(null)

  const signIn = useCallback(async (email: string, password: string): Promise<boolean> => {
    const result = await apiLogin({ email, password })
    const data = result.data as Record<string, unknown>

    // Support both camelCase (with renderer) and snake_case (without)
    const requires2FA = (data.requires2FA ?? data.requires_2fa) === true
    if (requires2FA) {
      setRequires2FA(true)
      setPendingCreds({ email, password })
      return true
    }

    const userObj = data.user as AuthUser | undefined
    if (userObj) {
      setUser(userObj)
      setTokens({
        accessToken: (data.accessToken as string) ?? (data.access_token as string) ?? "",
        refreshToken: (data.refreshToken as string) ?? (data.refresh_token as string) ?? "",
        accessExpiresIn: Number((data.accessExpiresIn ?? data.access_expires_in) ?? 0),
        refreshExpiresIn: Number((data.refreshExpiresIn ?? data.refresh_expires_in) ?? 0),
      })
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(userObj))
    }
    return false
  }, [])

  const complete2FA = useCallback(async (otpCode: string) => {
    if (!pendingCreds) return
    const result = await apiLogin(pendingCreds, otpCode)
    const data = result.data as Record<string, unknown>

    const userObj = data.user as AuthUser | undefined
    if (userObj) {
      setUser(userObj)
      setTokens({
        accessToken: (data.accessToken as string) ?? (data.access_token as string) ?? "",
        refreshToken: (data.refreshToken as string) ?? (data.refresh_token as string) ?? "",
        accessExpiresIn: Number((data.accessExpiresIn ?? data.access_expires_in) ?? 0),
        refreshExpiresIn: Number((data.refreshExpiresIn ?? data.refresh_expires_in) ?? 0),
      })
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(userObj))
    }

    setRequires2FA(false)
    setPendingCreds(null)
  }, [pendingCreds])

  const cancel2FA = useCallback(() => {
    setRequires2FA(false)
    setPendingCreds(null)
  }, [])

  const signOut = useCallback(async () => {
    await apiLogout()
    setUser(null)
    setTokens(null)
    setRequires2FA(false)
    setPendingCreds(null)
    sessionStorage.removeItem(STORAGE_KEY)
  }, [])

  return (
    <AuthContext.Provider
      value={{
        user,
        accessToken: tokens?.accessToken ?? null,
        signIn,
        complete2FA,
        cancel2FA,
        signOut,
        requires2FA,
        pendingEmail: pendingCreds?.email ?? null,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within AuthProvider")
  return ctx
}

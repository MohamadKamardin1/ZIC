import { useState, type FormEvent, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { Eye, EyeOff, Lock, User, ShieldCheck, ArrowLeft, KeyRound } from "lucide-react"
import { useAuth } from "../lib/auth"
import { ZicLogo } from "../components/ZicLogo"

export default function Login() {
  const { signIn, complete2FA, cancel2FA, requires2FA, pendingEmail } = useAuth()
  const navigate = useNavigate()

  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [show, setShow] = useState(false)
  const [otpCode, setOtpCode] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  // If already in a 2FA flow and user navigates away/back, reset
  useEffect(() => {
    if (!requires2FA) {
      setOtpCode("")
      setError("")
    }
  }, [requires2FA])

  async function onCredentialsSubmit(e: FormEvent) {
    e.preventDefault()
    setError("")
    setLoading(true)
    try {
      const needs2FA = await signIn(email, password)
      if (!needs2FA) navigate("/", { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to sign in.")
    } finally {
      setLoading(false)
    }
  }

  async function onOTPSubmit(e: FormEvent) {
    e.preventDefault()
    setError("")
    setLoading(true)
    try {
      await complete2FA(otpCode)
      navigate("/", { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid verification code.")
    } finally {
      setLoading(false)
    }
  }

  function handleBack() {
    cancel2FA()
    setError("")
  }

  // ---- 2FA OTP step ----
  if (requires2FA) {
    return (
      <main
        className="min-h-screen w-full bg-cover bg-center flex items-center justify-center p-4"
        style={{ backgroundImage: "url(/login-bg.png)" }}
      >
        <div className="flex w-full max-w-md flex-col items-center justify-center rounded-2xl bg-card px-8 py-12" style={{ boxShadow: "var(--shadow-card)" }}>
          <ZicLogo size={42} />

          <div className="mt-6 flex h-14 w-14 items-center justify-center rounded-full bg-primary/10">
            <ShieldCheck className="h-7 w-7 text-primary" />
          </div>

          <h1 className="mt-4 text-xl font-bold text-foreground">Two-Step Verification</h1>
          <p className="mt-1 text-center text-sm text-muted-foreground">
            Enter the 6-digit code from your authenticator app
          </p>
          {pendingEmail && (
            <p className="mt-1 text-xs text-muted-foreground">
              Signing in as <span className="font-medium text-foreground">{pendingEmail}</span>
            </p>
          )}

          <form onSubmit={onOTPSubmit} className="mt-6 w-full">
            <div className="flex items-center gap-3 rounded-lg border border-input bg-secondary/60 px-3 focus-within:ring-2 focus-within:ring-ring/40">
              <KeyRound className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
              <input
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={6}
                value={otpCode}
                onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ""))}
                placeholder="Enter 6-digit code"
                autoComplete="one-time-code"
                className="w-full bg-transparent py-3 text-sm tracking-[0.3em] text-center font-mono text-foreground outline-none placeholder:text-muted-foreground placeholder:tracking-normal placeholder:font-sans"
                autoFocus
              />
            </div>

            {error && <p className="mt-3 text-sm font-medium text-destructive">{error}</p>}

            <button
              type="submit"
              disabled={loading || otpCode.length < 6}
              className="mt-6 w-full rounded-lg bg-primary py-3 text-sm font-semibold text-primary-foreground transition hover:brightness-110 disabled:opacity-60"
            >
              {loading ? "Verifying..." : "Verify & Sign In"}
            </button>

            <button
              type="button"
              onClick={handleBack}
              className="mt-3 flex w-full items-center justify-center gap-1 text-sm text-muted-foreground transition hover:text-foreground"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Back to login
            </button>
          </form>
        </div>
      </main>
    )
  }

  // ---- Credentials step ----
  return (
    <main
      className="min-h-screen w-full bg-cover bg-center flex items-center justify-center p-4"
      style={{ backgroundImage: "url(/login-bg.png)" }}
    >
      <div className="flex w-full max-w-4xl overflow-hidden rounded-2xl bg-card" style={{ boxShadow: "var(--shadow-card-elevated)" }}>
        {/* Illustration panel */}
        <div className="hidden md:flex w-1/2 items-center justify-center p-8" style={{ backgroundColor: "var(--color-bg-accent)" }}>
          <img
            src="/insurance-illustration.png"
            alt="Insurance policy review illustration"
            className="max-h-80 w-full object-contain"
          />
        </div>

        {/* Form panel */}
        <div className="flex w-full md:w-1/2 flex-col items-center justify-center px-8 py-12 sm:px-12">
          <ZicLogo size={42} />
          <h1 className="mt-6 text-2xl font-bold text-foreground">AIMS Life Login</h1>
          <p className="mt-1 text-sm text-muted-foreground">Sign In to your account</p>

          <form onSubmit={onCredentialsSubmit} className="mt-8 w-full max-w-sm">
            <div className="flex items-center gap-3 rounded-lg border border-input bg-secondary/60 px-3 focus-within:ring-2 focus-within:ring-ring/40">
              <User className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Email"
                autoComplete="email"
                className="w-full bg-transparent py-3 text-sm text-foreground outline-none placeholder:text-muted-foreground"
              />
            </div>

            <div className="mt-4 flex items-center gap-3 rounded-lg border border-input bg-secondary/60 px-3 focus-within:ring-2 focus-within:ring-ring/40">
              <Lock className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
              <input
                type={show ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                autoComplete="current-password"
                className="w-full bg-transparent py-3 text-sm text-foreground outline-none placeholder:text-muted-foreground"
              />
              <button
                type="button"
                onClick={() => setShow((s) => !s)}
                className="text-muted-foreground hover:text-foreground"
                aria-label={show ? "Hide password" : "Show password"}
              >
                {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>

            <p className="mt-3 text-sm text-foreground">
              Forgot Your Password?{" "}
              <a href="#" className="font-semibold text-primary hover:underline">
                reset password
              </a>
            </p>

            {error && <p className="mt-3 text-sm font-medium text-destructive">{error}</p>}

            <button
              type="submit"
              disabled={loading}
              className="mt-6 w-full rounded-lg bg-primary py-3 text-sm font-semibold text-primary-foreground transition hover:brightness-110 disabled:opacity-60"
            >
              {loading ? "Signing in..." : "Login"}
            </button>
          </form>
        </div>
      </div>
    </main>
  )
}

import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from "react"

export type ThemeMode = "light" | "dark" | "system"
export type ResolvedTheme = "light" | "dark"

export interface BrandColors {
  primary: string
  secondary: string
}

interface ThemeContextValue {
  theme: ThemeMode
  resolvedTheme: ResolvedTheme
  setTheme: (theme: ThemeMode) => void
  brandColors: BrandColors
  setBrandColors: (colors: BrandColors) => void
}

const STORAGE_KEY_THEME = "zic-theme-mode"
const STORAGE_KEY_BRAND = "zic-brand-colors"

const DEFAULT_BRAND: BrandColors = {
  primary: "#2563eb",
  secondary: "#f1f5f9",
}

function readStoredTheme(): ThemeMode {
  try {
    const v = localStorage.getItem(STORAGE_KEY_THEME)
    if (v === "light" || v === "dark" || v === "system") return v
  } catch {}
  return "system"
}

function readStoredBrand(): BrandColors {
  try {
    const v = localStorage.getItem(STORAGE_KEY_BRAND)
    if (v) {
      const p = JSON.parse(v) as Partial<BrandColors>
      if (p.primary && p.secondary) return p as BrandColors
    }
  } catch {}
  return DEFAULT_BRAND
}

function resolveMode(theme: ThemeMode): ResolvedTheme {
  if (theme === "system") {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"
  }
  return theme
}

function applyThemeToDOM(resolved: ResolvedTheme) {
  document.documentElement.setAttribute("data-theme", resolved)
}

function applyBrandToDOM(colors: BrandColors) {
  const root = document.documentElement
  root.style.setProperty("--color-brand-primary", colors.primary)
  root.style.setProperty("--color-brand-secondary", colors.secondary)
  root.style.setProperty("--color-brand-accent", colors.primary)
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<ThemeMode>(readStoredTheme)
  const [brandColors, setBrandColorsState] = useState<BrandColors>(readStoredBrand)

  const resolvedTheme = resolveMode(theme)

  const setTheme = useCallback((t: ThemeMode) => {
    setThemeState(t)
    try {
      localStorage.setItem(STORAGE_KEY_THEME, t)
    } catch {}
  }, [])

  const setBrandColors = useCallback((colors: BrandColors) => {
    setBrandColorsState(colors)
    try {
      localStorage.setItem(STORAGE_KEY_BRAND, JSON.stringify(colors))
    } catch {}
  }, [])

  useEffect(() => {
    applyThemeToDOM(resolvedTheme)
  }, [resolvedTheme])

  useEffect(() => {
    applyBrandToDOM(brandColors)
  }, [brandColors])

  useEffect(() => {
    if (theme !== "system") return
    const mq = window.matchMedia("(prefers-color-scheme: dark)")
    const handler = () => applyThemeToDOM(mq.matches ? "dark" : "light")
    mq.addEventListener("change", handler)
    return () => mq.removeEventListener("change", handler)
  }, [theme])

  return (
    <ThemeContext.Provider value={{ theme, resolvedTheme, setTheme, brandColors, setBrandColors }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider")
  return ctx
}

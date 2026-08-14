import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react"

export type DashboardLanguage = "en" | "sw" | "ar"

type TranslationKey =
  | "dashboard" | "search" | "notifications" | "tasks" | "alerts" | "currencies"
  | "reports" | "approvals" | "help" | "openAssistant" | "markAllRead" | "noNotifications"
  | "workspace" | "signOut" | "language" | "viewAll" | "createTask" | "refresh"

const dictionary: Record<DashboardLanguage, Record<TranslationKey, string>> = {
  en: {
    dashboard: "Dashboard", search: "Search", notifications: "Notifications", tasks: "Tasks",
    alerts: "Alerts", currencies: "Currencies", reports: "Reports", approvals: "Approvals",
    help: "Help centre", openAssistant: "Open AI assistant", markAllRead: "Mark all read",
    noNotifications: "You are all caught up.", workspace: "Workspace", signOut: "Sign out",
    language: "Language", viewAll: "View all", createTask: "Create task", refresh: "Refresh",
  },
  sw: {
    dashboard: "Dashibodi", search: "Tafuta", notifications: "Arifa", tasks: "Kazi",
    alerts: "Tahadhari", currencies: "Sarafu", reports: "Ripoti", approvals: "Idhini",
    help: "Kituo cha msaada", openAssistant: "Fungua msaidizi wa AI", markAllRead: "Soma zote",
    noNotifications: "Hakuna arifa mpya.", workspace: "Eneo la kazi", signOut: "Toka",
    language: "Lugha", viewAll: "Tazama zote", createTask: "Unda kazi", refresh: "Onyesha upya",
  },
  ar: {
    dashboard: "لوحة التحكم", search: "بحث", notifications: "الإشعارات", tasks: "المهام",
    alerts: "التنبيهات", currencies: "العملات", reports: "التقارير", approvals: "الموافقات",
    help: "مركز المساعدة", openAssistant: "فتح مساعد الذكاء الاصطناعي", markAllRead: "تحديد الكل كمقروء",
    noNotifications: "لا توجد إشعارات جديدة.", workspace: "مساحة العمل", signOut: "تسجيل الخروج",
    language: "اللغة", viewAll: "عرض الكل", createTask: "إنشاء مهمة", refresh: "تحديث",
  },
}

interface LanguageContextValue {
  language: DashboardLanguage
  setLanguage: (language: DashboardLanguage) => void
  t: (key: TranslationKey) => string
}

const LanguageContext = createContext<LanguageContextValue | null>(null)

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<DashboardLanguage>(() => {
    const stored = window.localStorage.getItem("zic-dashboard-language") as DashboardLanguage | null
    return stored && stored in dictionary ? stored : "en"
  })

  useEffect(() => {
    window.localStorage.setItem("zic-dashboard-language", language)
    document.documentElement.lang = language
    document.documentElement.dir = language === "ar" ? "rtl" : "ltr"
  }, [language])

  const value = useMemo(() => ({ language, setLanguage, t: (key: TranslationKey) => dictionary[language][key] }), [language])
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}

export function useLanguage() {
  const context = useContext(LanguageContext)
  if (!context) throw new Error("useLanguage must be used within LanguageProvider")
  return context
}

export const languageOptions: { value: DashboardLanguage; label: string; nativeLabel: string }[] = [
  { value: "en", label: "English", nativeLabel: "English" },
  { value: "sw", label: "Swahili", nativeLabel: "Kiswahili" },
  { value: "ar", label: "Arabic", nativeLabel: "العربية" },
]

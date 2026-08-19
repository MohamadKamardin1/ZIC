import { useEffect, useState } from "react"
import { Outlet } from "react-router-dom"
import { Sidebar } from "./Sidebar"
import { Topbar } from "./Topbar"
import { Footer } from "./Footer"
import { AIAssistantPanel } from "../ai/AIAssistantPanel"
import { aiAnalyzePrompt, aiExecutePartnerCreation, aiClarify } from "../../lib/api"
import { AccessGate } from "../../lib/access"

export default function DashboardLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(true)

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)")
    const handler = (e: MediaQueryListEvent | MediaQueryList) => {
      setSidebarOpen(!e.matches)
    }
    handler(mq)
    mq.addEventListener("change", handler)
    return () => mq.removeEventListener("change", handler)
  }, [])

  return (
    <div className="h-screen overflow-hidden bg-background">
      <Sidebar open={sidebarOpen} />

      {sidebarOpen && (
        <div
          className="fixed inset-0 z-20 md:hidden" style={{ backgroundColor: "var(--color-bg-overlay)" }}
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <div className={`flex h-full flex-col transition-[margin] duration-200 ease-out ${sidebarOpen ? "md:ml-64" : "md:ml-0"}`}>
        <div className="flex-none">
          <Topbar onToggleSidebar={() => setSidebarOpen((o) => !o)} />
        </div>

          <main className="flex-1 overflow-y-auto overflow-x-hidden px-4 py-5 md:px-6">
            <AccessGate>
              <Outlet />
            </AccessGate>
          </main>

        <div className="flex-none">
          <Footer />
        </div>
      </div>

      <AIAssistantPanel
        onAnalyze={async (prompt) => {
          const result = await aiAnalyzePrompt(prompt)
          const apiData = result.data as Record<string, unknown>
          return {
            success: result.success,
            message: result.message,
            data: {
              status: apiData.status as "ready" | "needs_clarification",
              partnerType: apiData.partnerType as string | undefined,
              partnerData: apiData.partnerData as Record<string, unknown> | undefined,
              missingRequired: apiData.missingRequired as string[] | undefined,
              missingOptional: apiData.missingOptional as string[] | undefined,
              explanation: apiData.explanation as string | undefined,
            },
          }
        }}
        onCreate={async (partnerType, partnerData) => {
          return (await aiExecutePartnerCreation(
            partnerType as "INDIVIDUAL" | "CORPORATE",
            partnerData,
          )) as Record<string, unknown>
        }}
        onClarify={async (prompt, missingFields, partialData) => {
          const result = await aiClarify(prompt, missingFields, partialData)
          const data = result.data as Record<string, unknown>
          return {
            success: true,
            data: {
              status: data.status as "ready" | "needs_clarification",
              partnerType: data.partnerType as string | undefined,
              partnerData: data.partnerData as Record<string, unknown> | undefined,
              missingRequired: data.missingRequired as string[] | undefined,
              missingOptional: data.missingOptional as string[] | undefined,
              explanation: data.explanation as string | undefined,
            },
          }
        }}
      />
    </div>
  )
}

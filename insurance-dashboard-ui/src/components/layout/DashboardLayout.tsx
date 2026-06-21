import { useEffect, useState } from "react"
import { Outlet } from "react-router-dom"
import { Sidebar } from "./Sidebar"
import { Topbar } from "./Topbar"
import { Footer } from "./Footer"

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
          className="fixed inset-0 z-20 bg-black/40 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <div className={`flex h-full flex-col transition-[margin] duration-200 ease-out ${sidebarOpen ? "md:ml-64" : "md:ml-0"}`}>
        <div className="flex-none">
          <Topbar onToggleSidebar={() => setSidebarOpen((o) => !o)} />
        </div>

        <main className="flex-1 overflow-y-auto overflow-x-hidden px-4 py-5 md:px-6">
          <Outlet />
        </main>

        <div className="flex-none">
          <Footer />
        </div>
      </div>
    </div>
  )
}

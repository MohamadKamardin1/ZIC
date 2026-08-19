import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { BrowserRouter } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import "./index.css"
import "./lit/index"
import App from "./App"
import { AuthProvider } from "./lib/auth"
import { AccessProvider } from "./lib/access"
import { AIProvider } from "./components/ai/AIContext"
import { ThemeProvider } from "./theme/ThemeProvider"
import { LanguageProvider } from "./lib/language"
import { ToastProvider } from "./components/ui/Toast"

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ThemeProvider>
          <LanguageProvider>
            <AuthProvider>
              <AccessProvider>
                <AIProvider>
                  <ToastProvider>
                    <App />
                  </ToastProvider>
                </AIProvider>
              </AccessProvider>
            </AuthProvider>
          </LanguageProvider>
        </ThemeProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)

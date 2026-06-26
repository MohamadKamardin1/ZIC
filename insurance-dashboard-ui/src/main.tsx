import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { BrowserRouter } from "react-router-dom"
import "./index.css"
import "./lit/index"
import App from "./App"
import { AuthProvider } from "./lib/auth"
import { AIProvider } from "./components/ai/AIContext"
import { ThemeProvider } from "./theme/ThemeProvider"

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <AIProvider>
            <App />
          </AIProvider>
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  </StrictMode>,
)

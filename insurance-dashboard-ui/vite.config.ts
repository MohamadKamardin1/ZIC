import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"
import path from "node:path"

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: true,
    port: 3000,
    allowedHosts: true,
    proxy: {
      "/api": {
        target: process.env.VITE_BACKEND_PROXY_TARGET ?? "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
})

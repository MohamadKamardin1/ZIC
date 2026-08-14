import os

pages = {
    "OLQuotations.tsx": "Quotations",
    "OLPolicies.tsx": "Policies",
    "OLClients.tsx": "Clients",
    "OLClaims.tsx": "Claims",
    "OLMedicalUW.tsx": "Medical U/W",
}

for filename, title in pages.items():
    content = f"""import {{ FileText }} from "lucide-react"

export default function {filename.replace('.tsx', '')}() {{
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Ordinary Life {title}</h1>
          <p className="text-sm text-slate-400 mt-1">Manage Ordinary Life {title}</p>
        </div>
      </div>
      <div className="p-8 text-center text-slate-400 bg-slate-900/50 rounded-xl border border-slate-800">
        <FileText className="w-12 h-12 mx-auto mb-4 text-slate-600" />
        <h2 className="text-lg font-medium text-white mb-2">{title} Module</h2>
        <p>This module is currently under development.</p>
      </div>
    </div>
  )
}}
"""
    with open(f"src/pages/ordinary-life/{filename}", "w") as f:
        f.write(content)

import os
import re

# 1. Create/Update Placeholders
pages = {
    "OLQuotations.tsx": "Quotations",
    "OLCommitments.tsx": "Commitments",
    "OLProposals.tsx": "Proposals",
    "OLPolicies.tsx": "Policies",
    "OLLoans.tsx": "Loans",
    "OLWithdrawals.tsx": "Withdrawals",
    "OLClaims.tsx": "Claims",
    "OLMaturityInstallments.tsx": "Maturity Installments",
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

# Remove unused ones
for filename in ["OLClients.tsx", "OLMedicalUW.tsx"]:
    try:
        os.remove(f"src/pages/ordinary-life/{filename}")
    except OSError:
        pass

# 2. Update App.tsx
with open("src/App.tsx", "r") as f:
    app_content = f.read()

# Replace the imports
app_content = re.sub(
    r"import OLQuotations.*?import OLMedicalUW from \"./pages/ordinary-life/OLMedicalUW\"",
    """import OLQuotations from "./pages/ordinary-life/OLQuotations"
import OLCommitments from "./pages/ordinary-life/OLCommitments"
import OLProposals from "./pages/ordinary-life/OLProposals"
import OLPolicies from "./pages/ordinary-life/OLPolicies"
import OLLoans from "./pages/ordinary-life/OLLoans"
import OLWithdrawals from "./pages/ordinary-life/OLWithdrawals"
import OLClaims from "./pages/ordinary-life/OLClaims"
import OLMaturityInstallments from "./pages/ordinary-life/OLMaturityInstallments\"""",
    app_content, flags=re.DOTALL
)

# Replace the routes
app_content = re.sub(
    r"<Route path=\"ordinary-life/quotations\".*?<Route path=\"ordinary-life/medical-uw\" element={<OLMedicalUW />} />",
    """<Route path="ordinary-life/quotations" element={<OLQuotations />} />
        <Route path="ordinary-life/commitments" element={<OLCommitments />} />
        <Route path="ordinary-life/proposals" element={<OLProposals />} />
        <Route path="ordinary-life/policies" element={<OLPolicies />} />
        <Route path="ordinary-life/loans" element={<OLLoans />} />
        <Route path="ordinary-life/withdrawals" element={<OLWithdrawals />} />
        <Route path="ordinary-life/claims" element={<OLClaims />} />
        <Route path="ordinary-life/maturity-installments" element={<OLMaturityInstallments />} />""",
    app_content, flags=re.DOTALL
)

with open("src/App.tsx", "w") as f:
    f.write(app_content)

# 3. Update Sidebar.tsx
with open("src/components/layout/Sidebar.tsx", "r") as f:
    sidebar_content = f.read()

# Replace the Ordinary Life children
sidebar_content = re.sub(
    r"\{ label: \"Ordinary Life\".*?\] \},",
    """{ label: "Ordinary Life", icon: Users, expandable: true, children: [
    { label: "Quotations", icon: FileText, path: "/ordinary-life/quotations" },
    { label: "Commitments", icon: FileText, path: "/ordinary-life/commitments" },
    { label: "Proposals", icon: FileText, path: "/ordinary-life/proposals" },
    { label: "Policies", icon: ShieldCheck, path: "/ordinary-life/policies" },
    { label: "Loans", icon: FileText, path: "/ordinary-life/loans" },
    { label: "Withdrawals", icon: FileText, path: "/ordinary-life/withdrawals" },
    { label: "Claims", icon: FileText, path: "/ordinary-life/claims" },
    { label: "Maturity Installments", icon: FileText, path: "/ordinary-life/maturity-installments" },
    { label: "Setup", icon: Settings, path: "/ordinary-life/setup" },
  ] },""",
    sidebar_content, flags=re.DOTALL
)

with open("src/components/layout/Sidebar.tsx", "w") as f:
    f.write(sidebar_content)

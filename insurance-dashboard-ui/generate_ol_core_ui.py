import os

components = [
    {
        "name": "OLQuotations",
        "title": "Quotations",
        "icon": "FileText",
        "endpoint": "olCore.listQuotations",
        "create_endpoint": "olCore.createQuotation",
        "update_endpoint": "olCore.updateQuotation",
        "delete_endpoint": "olCore.deleteQuotation",
        "fields": [
            {"key": "quotation_number", "label": "Quotation No.", "type": "text"},
            {"key": "client", "label": "Client ID", "type": "text"},
            {"key": "product", "label": "Product ID", "type": "text"},
            {"key": "sum_assured", "label": "Sum Assured", "type": "number"},
            {"key": "premium_amount", "label": "Premium Amount", "type": "number"},
            {"key": "status", "label": "Status", "type": "select", "options": ["DRAFT", "SUBMITTED", "EXPIRED", "CONVERTED"]},
        ]
    },
    {
        "name": "OLProposals",
        "title": "Proposals",
        "icon": "FileText",
        "endpoint": "olCore.listProposals",
        "create_endpoint": "olCore.createProposal",
        "update_endpoint": "olCore.updateProposal",
        "delete_endpoint": "olCore.deleteProposal",
        "fields": [
            {"key": "proposal_number", "label": "Proposal No.", "type": "text"},
            {"key": "quotation", "label": "Quotation ID", "type": "text"},
            {"key": "underwriting_status", "label": "UW Status", "type": "select", "options": ["PENDING", "REVIEW", "APPROVED"]},
            {"key": "medical_required", "label": "Medical Required", "type": "boolean"},
            {"key": "status", "label": "Status", "type": "select", "options": ["PENDING", "APPROVED", "DECLINED"]},
        ]
    },
    {
        "name": "OLCommitments",
        "title": "Commitments",
        "icon": "FileText",
        "endpoint": "olCore.listCommitments",
        "create_endpoint": "olCore.createCommitment",
        "update_endpoint": "olCore.updateCommitment",
        "delete_endpoint": "olCore.deleteCommitment",
        "fields": [
            {"key": "commitment_number", "label": "Commitment No.", "type": "text"},
            {"key": "proposal", "label": "Proposal ID", "type": "text"},
            {"key": "amount_paid", "label": "Amount Paid", "type": "number"},
            {"key": "payment_method", "label": "Payment Method", "type": "text"},
            {"key": "status", "label": "Status", "type": "select", "options": ["PENDING", "PAID", "FAILED"]},
        ]
    },
    {
        "name": "OLPolicies",
        "title": "Policies",
        "icon": "ShieldCheck",
        "endpoint": "olCore.listPolicies",
        "create_endpoint": "olCore.createPolicy",
        "update_endpoint": "olCore.updatePolicy",
        "delete_endpoint": "olCore.deletePolicy",
        "fields": [
            {"key": "policy_number", "label": "Policy No.", "type": "text"},
            {"key": "proposal", "label": "Proposal ID", "type": "text"},
            {"key": "start_date", "label": "Start Date", "type": "date"},
            {"key": "end_date", "label": "End Date", "type": "date"},
            {"key": "status", "label": "Status", "type": "select", "options": ["ACTIVE", "LAPSED", "SURRENDERED", "MATURED", "CANCELLED"]},
        ]
    },
    {
        "name": "OLLoans",
        "title": "Loans",
        "icon": "FileText",
        "endpoint": "olCore.listLoans",
        "create_endpoint": "olCore.createLoan",
        "update_endpoint": "olCore.updateLoan",
        "delete_endpoint": "olCore.deleteLoan",
        "fields": [
            {"key": "loan_number", "label": "Loan No.", "type": "text"},
            {"key": "policy", "label": "Policy ID", "type": "text"},
            {"key": "loan_amount", "label": "Loan Amount", "type": "number"},
            {"key": "interest_rate", "label": "Interest Rate %", "type": "number"},
            {"key": "outstanding_balance", "label": "Outstanding Balance", "type": "number"},
            {"key": "status", "label": "Status", "type": "select", "options": ["PENDING", "APPROVED", "REPAID"]},
        ]
    },
    {
        "name": "OLWithdrawals",
        "title": "Withdrawals",
        "icon": "FileText",
        "endpoint": "olCore.listWithdrawals",
        "create_endpoint": "olCore.createWithdrawal",
        "update_endpoint": "olCore.updateWithdrawal",
        "delete_endpoint": "olCore.deleteWithdrawal",
        "fields": [
            {"key": "withdrawal_number", "label": "Withdrawal No.", "type": "text"},
            {"key": "policy", "label": "Policy ID", "type": "text"},
            {"key": "amount", "label": "Amount", "type": "number"},
            {"key": "withdrawal_type", "label": "Type", "type": "select", "options": ["PARTIAL", "FULL_SURRENDER"]},
            {"key": "status", "label": "Status", "type": "select", "options": ["PENDING", "PAID"]},
        ]
    },
    {
        "name": "OLClaims",
        "title": "Claims",
        "icon": "FileText",
        "endpoint": "olCore.listClaims",
        "create_endpoint": "olCore.createClaim",
        "update_endpoint": "olCore.updateClaim",
        "delete_endpoint": "olCore.deleteClaim",
        "fields": [
            {"key": "claim_number", "label": "Claim No.", "type": "text"},
            {"key": "policy", "label": "Policy ID", "type": "text"},
            {"key": "date_of_event", "label": "Date of Event", "type": "date"},
            {"key": "cause", "label": "Cause", "type": "text"},
            {"key": "claim_amount", "label": "Claim Amount", "type": "number"},
            {"key": "status", "label": "Status", "type": "select", "options": ["REPORTED", "INVESTIGATING", "APPROVED", "PAID", "REJECTED"]},
        ]
    },
    {
        "name": "OLMaturityInstallments",
        "title": "Maturity Installments",
        "icon": "FileText",
        "endpoint": "olCore.listMaturityInstallments",
        "create_endpoint": "olCore.createMaturityInstallment",
        "update_endpoint": "olCore.updateMaturityInstallment",
        "delete_endpoint": "olCore.deleteMaturityInstallment",
        "fields": [
            {"key": "installment_number", "label": "Installment No.", "type": "text"},
            {"key": "policy", "label": "Policy ID", "type": "text"},
            {"key": "due_date", "label": "Due Date", "type": "date"},
            {"key": "amount", "label": "Amount", "type": "number"},
            {"key": "status", "label": "Status", "type": "select", "options": ["PENDING", "PAID"]},
        ]
    }
]

template = """import {{ useState, useEffect }} from "react";
import {{ {icon}, Plus, Search, Edit2, Trash2, X, Loader2, AlertCircle, ShieldCheck }} from "lucide-react";
import {{ olCore }} from "../../lib/ol-api";

export default function {name}() {{
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [editingItem, setEditingItem] = useState<any>(null);
  const [formData, setFormData] = useState<any>({{}});

  const fetchItems = async () => {{
    try {{
      setLoading(true);
      const data = await {endpoint}();
      setItems(data);
    }} catch (err: any) {{
      setError(err.message || "Failed to load data.");
    }} finally {{
      setLoading(false);
    }}
  }};

  useEffect(() => {{
    fetchItems();
  }}, []);

  const openModal = (item?: any) => {{
    setEditingItem(item || null);
    setFormData(item || {{}});
    setIsModalOpen(true);
  }};

  const closeModal = () => {{
    setIsModalOpen(false);
    setFormData({{}});
    setEditingItem(null);
  }};

  const handleSubmit = async (e: React.FormEvent) => {{
    e.preventDefault();
    try {{
      setIsSubmitting(true);
      if (editingItem) {{
        await {update_endpoint}(editingItem.id, formData);
      }} else {{
        await {create_endpoint}(formData);
      }}
      closeModal();
      fetchItems();
    }} catch (err: any) {{
      alert(err.message || "Failed to save record.");
    }} finally {{
      setIsSubmitting(false);
    }}
  }};

  const handleDelete = async (id: string) => {{
    if (!confirm("Are you sure you want to delete this record?")) return;
    try {{
      await {delete_endpoint}(id);
      fetchItems();
    }} catch (err: any) {{
      alert(err.message || "Failed to delete record.");
    }}
  }};

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="mb-6 flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-3">
            <div className="p-2 rounded-xl" style={{{{ background: "linear-gradient(135deg, #3b82f6, #6366f1)" }}}}>
              <{icon} className="h-6 w-6 text-white" />
            </div>
            {title}
          </h1>
          <p className="text-muted-foreground mt-1">Manage Ordinary Life {title}</p>
        </div>
        <button
          onClick={{() => openModal()}}
          className="flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-medium text-white shadow-lg transition hover:opacity-90"
          style={{{{ background: "linear-gradient(135deg, #3b82f6, #6366f1)" }}}}
        >
          <Plus className="h-4 w-4" /> Add {title}
        </button>
      </div>

      {{error && (
        <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-xl flex items-center text-destructive">
          <AlertCircle className="w-5 h-5 mr-3" />
          {{error}}
        </div>
      )}}

      <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
        <div className="p-4 border-b border-border flex justify-between items-center bg-secondary/30">
          <div className="relative w-64 max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search..."
              className="h-10 w-full rounded-xl border border-border bg-card pl-10 pr-4 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-foreground">
            <thead className="bg-secondary/30 text-muted-foreground border-b border-border">
              <tr>
                {table_headers}
                <th className="px-6 py-4 font-semibold uppercase tracking-wider text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {{loading ? (
                <tr>
                  <td colSpan={{10}} className="px-6 py-8 text-center text-muted-foreground">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-primary" />
                    Loading...
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={{10}} className="px-6 py-8 text-center text-muted-foreground">
                    No records found.
                  </td>
                </tr>
              ) : (
                items.map((item) => (
                  <tr key={{item.id}} className="hover:bg-secondary/20 transition-colors">
                    {table_cells}
                    <td className="px-6 py-4 text-right">
                      <button onClick={{() => openModal(item)}} className="text-muted-foreground hover:text-primary p-1.5 rounded-lg hover:bg-secondary mr-2 transition-colors">
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button onClick={{() => handleDelete(item.id)}} className="text-muted-foreground hover:text-destructive p-1.5 rounded-lg hover:bg-secondary transition-colors">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}}
            </tbody>
          </table>
        </div>
      </div>

      {{/* Modal */}}
      {{isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <div className="bg-card border border-border rounded-2xl w-full max-w-md overflow-hidden shadow-2xl flex flex-col max-h-[90vh] animate-in fade-in zoom-in-95">
            <div className="px-6 py-4 border-b border-border flex justify-between items-center bg-card">
              <h3 className="text-lg font-bold text-foreground">
                {{editingItem ? 'Edit' : 'Add'}} {title}
              </h3>
              <button onClick={{closeModal}} className="text-muted-foreground hover:text-foreground p-2 rounded-lg hover:bg-secondary transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-6 overflow-y-auto">
              <form id="record-form" onSubmit={{handleSubmit}} className="space-y-4">
                {form_inputs}
              </form>
            </div>

            <div className="px-6 py-4 border-t border-border bg-secondary/30 flex justify-end space-x-3">
              <button
                type="button"
                onClick={{closeModal}}
                className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                form="record-form"
                disabled={{isSubmitting}}
                className="bg-primary hover:bg-primary/90 text-primary-foreground px-6 py-2 rounded-xl text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
              >
                {{isSubmitting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}}
                Save
              </button>
            </div>
          </div>
        </div>
      )}}
    </div>
  );
}}
"""

for comp in components:
    table_headers = "\n                ".join([f'<th className="px-6 py-4 font-semibold uppercase tracking-wider text-xs">{f["label"]}</th>' for f in comp["fields"]])
    table_cells = "\n                    ".join([f'<td className="px-6 py-4">{{item.{f["key"]}}}</td>' for f in comp["fields"]])
    
    form_inputs = ""
    for f in comp["fields"]:
        if f["type"] == "select":
            opts = "\n                    ".join([f'<option value="{opt}">{opt}</option>' for opt in f["options"]])
            form_inputs += f"""
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">{f['label']}</label>
                  <select
                    required
                    value={{formData.{f['key']} || ''}}
                    onChange={{e => setFormData({{ ...formData, {f['key']}: e.target.value }})}}
                    className="w-full h-10 bg-card border border-border rounded-xl px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                  >
                    <option value="">Select...</option>
                    {opts}
                  </select>
                </div>"""
        else:
            input_type = f["type"]
            form_inputs += f"""
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">{f['label']}</label>
                  <input
                    type="{input_type}"
                    required
                    value={{formData.{f['key']} || ''}}
                    onChange={{e => setFormData({{ ...formData, {f['key']}: { 'Number(e.target.value)' if input_type=='number' else 'e.target.value' } }})}}
                    className="w-full h-10 bg-card border border-border rounded-xl px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                  />
                </div>"""

    content = template.format(
        name=comp["name"],
        title=comp["title"],
        icon=comp["icon"],
        endpoint=comp["endpoint"],
        create_endpoint=comp["create_endpoint"],
        update_endpoint=comp["update_endpoint"],
        delete_endpoint=comp["delete_endpoint"],
        table_headers=table_headers,
        table_cells=table_cells,
        form_inputs=form_inputs
    )
    
    with open(f"src/pages/ordinary-life/{comp['name']}.tsx", "w") as f:
        f.write(content)

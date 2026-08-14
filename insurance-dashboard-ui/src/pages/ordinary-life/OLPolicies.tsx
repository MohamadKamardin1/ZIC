import { useState, useEffect } from "react";
import { ShieldCheck, Plus, Search, Edit2, Trash2, X, Loader2, AlertCircle } from "lucide-react";
import { olCore } from "../../lib/ol-api";

export default function OLPolicies() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [editingItem, setEditingItem] = useState<any>(null);
  const [formData, setFormData] = useState<any>({});

  const fetchItems = async () => {
    try {
      setLoading(true);
      const data = await olCore.listPolicies();
      setItems(data);
    } catch (err: any) {
      setError(err.message || "Failed to load data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchItems();
  }, []);

  const openModal = (item?: any) => {
    setEditingItem(item || null);
    setFormData(item || {});
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setFormData({});
    setEditingItem(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsSubmitting(true);
      if (editingItem) {
        await olCore.updatePolicy(editingItem.id, formData);
      } else {
        await olCore.createPolicy(formData);
      }
      closeModal();
      fetchItems();
    } catch (err: any) {
      alert(err.message || "Failed to save record.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this record?")) return;
    try {
      await olCore.deletePolicy(id);
      fetchItems();
    } catch (err: any) {
      alert(err.message || "Failed to delete record.");
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="mb-6 flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-3">
            <div className="p-2 rounded-xl" style={{ background: "linear-gradient(135deg, #3b82f6, #6366f1)" }}>
              <ShieldCheck className="h-6 w-6 text-white" />
            </div>
            Policies
          </h1>
          <p className="text-muted-foreground mt-1">Manage Ordinary Life Policies</p>
        </div>
        <button
          onClick={() => openModal()}
          className="flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-medium text-white shadow-lg transition hover:opacity-90"
          style={{ background: "linear-gradient(135deg, #3b82f6, #6366f1)" }}
        >
          <Plus className="h-4 w-4" /> Add Policies
        </button>
      </div>

      {error && (
        <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-xl flex items-center text-destructive">
          <AlertCircle className="w-5 h-5 mr-3" />
          {error}
        </div>
      )}

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
                <th className="px-6 py-4 font-semibold uppercase tracking-wider text-xs">Policy No.</th>
                <th className="px-6 py-4 font-semibold uppercase tracking-wider text-xs">Proposal ID</th>
                <th className="px-6 py-4 font-semibold uppercase tracking-wider text-xs">Start Date</th>
                <th className="px-6 py-4 font-semibold uppercase tracking-wider text-xs">End Date</th>
                <th className="px-6 py-4 font-semibold uppercase tracking-wider text-xs">Status</th>
                <th className="px-6 py-4 font-semibold uppercase tracking-wider text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {loading ? (
                <tr>
                  <td colSpan={10} className="px-6 py-8 text-center text-muted-foreground">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-primary" />
                    Loading...
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={10} className="px-6 py-8 text-center text-muted-foreground">
                    No records found.
                  </td>
                </tr>
              ) : (
                items.map((item) => (
                  <tr key={item.id} className="hover:bg-secondary/20 transition-colors">
                    <td className="px-6 py-4">{item.policy_number}</td>
                    <td className="px-6 py-4">{item.proposal}</td>
                    <td className="px-6 py-4">{item.start_date}</td>
                    <td className="px-6 py-4">{item.end_date}</td>
                    <td className="px-6 py-4">{item.status}</td>
                    <td className="px-6 py-4 text-right">
                      <button onClick={() => openModal(item)} className="text-muted-foreground hover:text-primary p-1.5 rounded-lg hover:bg-secondary mr-2 transition-colors">
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button onClick={() => handleDelete(item.id)} className="text-muted-foreground hover:text-destructive p-1.5 rounded-lg hover:bg-secondary transition-colors">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <div className="bg-card border border-border rounded-2xl w-full max-w-md overflow-hidden shadow-2xl flex flex-col max-h-[90vh] animate-in fade-in zoom-in-95">
            <div className="px-6 py-4 border-b border-border flex justify-between items-center bg-card">
              <h3 className="text-lg font-bold text-foreground">
                {editingItem ? 'Edit' : 'Add'} Policies
              </h3>
              <button onClick={closeModal} className="text-muted-foreground hover:text-foreground p-2 rounded-lg hover:bg-secondary transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-6 overflow-y-auto">
              <form id="record-form" onSubmit={handleSubmit} className="space-y-4">
                
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Policy No.</label>
                  <input
                    type="text"
                    required
                    value={formData.policy_number || ''}
                    onChange={e => setFormData({ ...formData, policy_number: e.target.value })}
                    className="w-full h-10 bg-card border border-border rounded-xl px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Proposal ID</label>
                  <input
                    type="text"
                    required
                    value={formData.proposal || ''}
                    onChange={e => setFormData({ ...formData, proposal: e.target.value })}
                    className="w-full h-10 bg-card border border-border rounded-xl px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Start Date</label>
                  <input
                    type="date"
                    required
                    value={formData.start_date || ''}
                    onChange={e => setFormData({ ...formData, start_date: e.target.value })}
                    className="w-full h-10 bg-card border border-border rounded-xl px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">End Date</label>
                  <input
                    type="date"
                    required
                    value={formData.end_date || ''}
                    onChange={e => setFormData({ ...formData, end_date: e.target.value })}
                    className="w-full h-10 bg-card border border-border rounded-xl px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Status</label>
                  <select
                    required
                    value={formData.status || ''}
                    onChange={e => setFormData({ ...formData, status: e.target.value })}
                    className="w-full h-10 bg-card border border-border rounded-xl px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40"
                  >
                    <option value="">Select...</option>
                    <option value="ACTIVE">ACTIVE</option>
                    <option value="LAPSED">LAPSED</option>
                    <option value="SURRENDERED">SURRENDERED</option>
                    <option value="MATURED">MATURED</option>
                    <option value="CANCELLED">CANCELLED</option>
                  </select>
                </div>
              </form>
            </div>

            <div className="px-6 py-4 border-t border-border bg-secondary/30 flex justify-end space-x-3">
              <button
                type="button"
                onClick={closeModal}
                className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                form="record-form"
                disabled={isSubmitting}
                className="bg-primary hover:bg-primary/90 text-primary-foreground px-6 py-2 rounded-xl text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
              >
                {isSubmitting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

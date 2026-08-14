import { LitElement, css, html } from "lit"
import { customElement, property, state } from "lit/decorators.js"

interface OnboardingDocumentRecord {
  id?: string
  documentType?: string
  documentName?: string
  file?: string
  fileSize?: number | null
  mimeType?: string
  isVerified?: boolean
  verifiedAt?: string | null
  verificationNotes?: string
  createdAt?: string
}

function titleize(value: string) { return value.replace(/_/g, " ").toLowerCase().replace(/(^|\s)\S/g, (letter: string) => letter.toUpperCase()) }

@customElement("onboarding-document-panel")
export class OnboardingDocumentPanel extends LitElement {
  @property({ attribute: false }) documents: OnboardingDocumentRecord[] = []
  @property({ attribute: false }) documentTypes: Array<{ value: string; label: string }> = []
  @property({ type: Boolean }) canUpload = true
  @property({ type: Boolean }) canVerify = false
  @property({ type: Boolean }) uploading = false
  @property({ type: String }) emptyLabel = "No documents have been uploaded."
  @state() private selectedType = ""

  static styles = css`
    :host { display: block; font-family: var(--font-sans, Inter, sans-serif); color: var(--foreground, #0f172a); }
    .shell { background: var(--card, #fff); border: 1px solid var(--border, #e2e8f0); border-radius: var(--radius, 12px); padding: 20px; box-shadow: 0 1px 3px rgba(15,23,42,.05); }
    .header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 16px; }
    h3 { margin: 0; font-size: 15px; font-weight: 700; }
    .sub { margin: 4px 0 0; color: var(--muted-foreground, #64748b); font-size: 12px; }
    .upload { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; padding: 12px; margin-bottom: 14px; border: 1px dashed var(--border, #cbd5e1); border-radius: 10px; background: var(--muted, #f8fafc); }
    select, .choose, button { height: 34px; border-radius: 7px; border: 1px solid var(--border, #cbd5e1); background: var(--card, #fff); color: var(--foreground, #0f172a); font: 600 12px Inter, sans-serif; }
    select { padding: 0 9px; min-width: 180px; }
    .choose, button { display: inline-flex; align-items: center; justify-content: center; padding: 0 11px; cursor: pointer; }
    .choose { color: var(--primary, #2563eb); border-color: color-mix(in srgb, var(--primary, #2563eb) 30%, var(--border, #cbd5e1)); }
    button { font-weight: 700; }
    button:hover, .choose:hover { background: var(--accent, #f1f5f9); }
    button.danger { color: var(--color-feedback-danger, #b91c1c); }
    button.verify { color: var(--color-feedback-success, #15803d); }
    input[type=file] { display: none; }
    .row { display: grid; grid-template-columns: minmax(0, 1fr) auto auto; gap: 12px; align-items: center; padding: 13px 0; border-bottom: 1px solid var(--border, #eef2f7); }
    .row:last-child { border-bottom: 0; padding-bottom: 0; }
    .name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; font-weight: 700; }
    .meta { display: flex; gap: 7px; flex-wrap: wrap; margin-top: 4px; color: var(--muted-foreground, #64748b); font-size: 11px; }
    .badge { display: inline-flex; align-items: center; padding: 3px 7px; border-radius: 999px; background: var(--color-bg-warning-soft, #fffbeb); color: var(--color-feedback-warning, #b45309); font-weight: 700; }
    .badge.ok { background: var(--color-bg-success-soft, #f0fdf4); color: var(--color-feedback-success, #15803d); }
    .actions { display: flex; gap: 6px; }
    .empty { padding: 24px 0; text-align: center; color: var(--muted-foreground, #64748b); font-size: 12px; }
    @media (max-width: 640px) { .row { grid-template-columns: 1fr; gap: 8px; } .actions { justify-content: flex-start; } }
  `

  private dispatch(name: string, detail: Record<string, unknown>) {
    this.dispatchEvent(new CustomEvent(name, { detail, bubbles: true, composed: true }))
  }

  private onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement
    const file = input.files?.[0]
    if (!file) return
    if (!this.selectedType) { this.dispatch("onboarding-document-error", { message: "Select a document type before uploading." }); input.value = ""; return }
    this.dispatch("onboarding-document-upload", { file, documentType: this.selectedType })
    input.value = ""
  }

  render() {
    return html`
      <section class="shell" aria-label="Application documents">
        <div class="header"><div><h3>Required documents</h3><p class="sub">Keep identity, registration, and compliance evidence current.</p></div><strong>${this.documents.length}</strong></div>
        ${this.canUpload ? html`<div class="upload">
          <select aria-label="Document type" .value=${this.selectedType} @change=${(event: Event) => { this.selectedType = (event.target as HTMLSelectElement).value }}>
            <option value="">Select document type</option>
            ${this.documentTypes.map((type) => html`<option value=${type.value}>${type.label}</option>`)}
          </select>
          <label class="choose">${this.uploading ? "Uploading…" : "Choose file"}<input type="file" accept=".pdf,.jpg,.jpeg,.png,.doc,.docx" ?disabled=${this.uploading} @change=${this.onFileSelected}></label>
          <span class="sub">PDF, image, or office document</span>
        </div>` : ""}
        ${this.documents.length === 0 ? html`<div class="empty">${this.emptyLabel}</div>` : this.documents.map((document) => html`
          <div class="row">
            <div><div class="name" title=${document.documentName || "Document"}>${document.documentName || "Untitled document"}</div><div class="meta"><span>${titleize(document.documentType || "Document")}</span><span>·</span><span>${document.mimeType || "File"}</span><span class="badge ${document.isVerified ? "ok" : ""}">${document.isVerified ? "Verified" : "Pending verification"}</span></div></div>
            <div class="actions">${document.file ? html`<a class="choose" href=${document.file} target="_blank" rel="noreferrer">View</a>` : ""}${this.canVerify && !document.isVerified ? html`<button class="verify" @click=${() => this.dispatch("onboarding-document-action", { action: "verify", document })}>Verify</button>` : ""}<button class="danger" @click=${() => this.dispatch("onboarding-document-action", { action: "delete", document })}>Remove</button></div>
          </div>
        `)}
      </section>
    `
  }
}

declare global { interface HTMLElementTagNameMap { "onboarding-document-panel": OnboardingDocumentPanel } }

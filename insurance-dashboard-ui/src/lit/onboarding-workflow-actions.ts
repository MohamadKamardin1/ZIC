import { LitElement, css, html } from "lit"
import { customElement, property } from "lit/decorators.js"

const LABELS: Record<string, string> = {
  submit: "Submit application",
  review: "Start review",
  request_documents: "Request documents",
  send_to_compliance: "Send to compliance",
  run_compliance: "Run compliance",
  approve: "Approve application",
  reject: "Reject",
  suspend: "Suspend",
  resume: "Resume application",
  convert: "Convert to partner",
}

@customElement("onboarding-workflow-actions")
export class OnboardingWorkflowActions extends LitElement {
  @property({ type: String }) status = "DRAFT"
  @property({ attribute: false }) allowedActions: string[] = []
  @property({ type: Boolean }) busy = false
  @property({ type: Boolean }) canEdit = false

  static styles = css`
    :host { display: block; font-family: var(--font-sans, Inter, sans-serif); }
    .shell { display: flex; align-items: center; justify-content: flex-end; gap: 8px; flex-wrap: wrap; }
    button { min-height: 36px; display: inline-flex; align-items: center; justify-content: center; gap: 7px; padding: 0 13px; border: 1px solid var(--border, #cbd5e1); border-radius: 8px; background: var(--card, #fff); color: var(--foreground, #0f172a); cursor: pointer; font: 700 12px Inter, sans-serif; transition: .16s ease; }
    button:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 3px 8px rgba(15,23,42,.1); }
    button:disabled { cursor: not-allowed; opacity: .55; }
    button.primary { border-color: var(--primary, #2563eb); background: var(--primary, #2563eb); color: var(--primary-foreground, #fff); }
    button.success { border-color: var(--color-feedback-success, #16a34a); background: var(--color-feedback-success, #16a34a); color: #fff; }
    button.danger { color: var(--color-feedback-danger, #b91c1c); border-color: color-mix(in srgb, var(--color-feedback-danger, #b91c1c) 30%, var(--border, #cbd5e1)); }
    .busy { width: 12px; height: 12px; border: 2px solid currentColor; border-right-color: transparent; border-radius: 999px; animation: spin .7s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
  `

  private defaults() {
    if (this.allowedActions.length) return this.allowedActions
    const map: Record<string, string[]> = {
      DRAFT: ["submit"],
      SUBMITTED: ["review"],
      UNDER_REVIEW: ["request_documents", "send_to_compliance", "reject"],
      PENDING_DOCUMENTS: ["send_to_compliance", "reject"],
      COMPLIANCE_CHECK: ["run_compliance", "approve", "reject", "suspend"],
      APPROVED: ["convert"],
      SUSPENDED: ["resume"],
    }
    return map[this.status] || []
  }

  private actionClass(action: string) {
    if (["approve", "convert", "submit", "review", "resume"].includes(action)) return action === "approve" || action === "convert" ? "success" : "primary"
    if (["reject", "suspend"].includes(action)) return "danger"
    return ""
  }

  private run(action: string) { if (!this.busy) this.dispatchEvent(new CustomEvent("onboarding-workflow-action", { detail: { action }, bubbles: true, composed: true })) }

  render() {
    return html`<div class="shell" aria-label="Workflow actions">
      ${this.canEdit && this.status === "DRAFT" ? html`<button @click=${() => this.run("edit")}>Edit draft</button>` : ""}
      ${this.defaults().map((action) => html`<button class=${this.actionClass(action)} ?disabled=${this.busy} @click=${() => this.run(action)}>${this.busy ? html`<span class="busy"></span>` : ""}${LABELS[action] || action}</button>`)}
    </div>`
  }
}

declare global { interface HTMLElementTagNameMap { "onboarding-workflow-actions": OnboardingWorkflowActions } }

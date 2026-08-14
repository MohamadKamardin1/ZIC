import { LitElement, css, html } from "lit"
import { customElement, property } from "lit/decorators.js"
import { cardStyles } from "./shared"

export type PartnerLifecycleAction = "activate" | "deactivate"

@customElement("partner-lifecycle-actions")
export class PartnerLifecycleActions extends LitElement {
  static styles = [
    cardStyles,
    css`
      .actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
      button { border: 1px solid var(--border); border-radius: 9px; padding: 8px 13px; font: inherit; font-size: 12px; font-weight: 700; cursor: pointer; background: var(--card); color: var(--foreground); }
      button:hover { background: var(--muted); }
      button:disabled { cursor: wait; opacity: .55; }
      .activate { border-color: color-mix(in srgb, var(--color-feedback-success) 45%, var(--border)); color: var(--color-feedback-success); }
      .deactivate { border-color: color-mix(in srgb, var(--color-feedback-destructive) 45%, var(--border)); color: var(--color-feedback-destructive); }
      .hint { color: var(--muted-foreground); font-size: 12px; }
    `,
  ]

  @property({ type: String }) status = ""
  @property({ type: String }) entityId = ""
  @property({ type: Boolean }) busy = false
  @property({ type: Boolean }) compact = false

  private emit(action: PartnerLifecycleAction) {
    this.dispatchEvent(new CustomEvent("partner-action", {
      detail: { action, entityId: this.entityId }, bubbles: true, composed: true,
    }))
  }

  render() {
    const active = this.status === "ACTIVE"
    return html`
      <div class="actions">
        ${active
          ? html`<button class="deactivate" ?disabled=${this.busy} @click=${() => this.emit("deactivate")}>
              ${this.busy ? "Working…" : "Deactivate partner"}
            </button>`
          : html`<button class="activate" ?disabled=${this.busy} @click=${() => this.emit("activate")}>
              ${this.busy ? "Working…" : "Activate partner"}
            </button>`}
        ${!this.compact ? html`<span class="hint">Lifecycle changes are recorded in governance audit history.</span>` : html``}
      </div>
    `
  }
}

import { LitElement, css, html } from "lit"
import { customElement, property } from "lit/decorators.js"
import { cardStyles } from "./shared"

export type PartnerStatsTone = "neutral" | "success" | "warning" | "danger" | "info"

@customElement("partner-stats-card")
export class PartnerStatsCard extends LitElement {
  static styles = [
    cardStyles,
    css`
      .card { min-height: 112px; background: var(--card); border-color: var(--border); }
      .value { font-size: 30px; font-weight: 800; line-height: 1; color: var(--foreground); margin-top: 4px; }
      .label { font-size: 12px; color: var(--muted-foreground); font-weight: 600; text-transform: uppercase; letter-spacing: .05em; }
      .meta { margin-top: 10px; font-size: 12px; color: var(--muted-foreground); }
      .accent { width: 36px; height: 4px; border-radius: 999px; margin-bottom: 14px; background: var(--primary); }
      .success { background: var(--color-feedback-success); }
      .warning { background: var(--color-feedback-warning); }
      .danger { background: var(--color-feedback-destructive); }
      .info { background: var(--color-feedback-info); }
    `,
  ]

  @property({ type: String }) label = ""
  @property({ type: String }) value: string | number = 0
  @property({ type: String }) meta = ""
  @property({ type: String }) tone: PartnerStatsTone = "neutral"

  render() {
    return html`
      <div class="card" aria-label="${this.label}">
        <div class="accent ${this.tone}"></div>
        <div class="label">${this.label}</div>
        <div class="value">${this.value}</div>
        ${this.meta ? html`<div class="meta">${this.meta}</div>` : html``}
      </div>
    `
  }
}

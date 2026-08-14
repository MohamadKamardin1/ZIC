import { LitElement, css, html } from "lit"
import { customElement, property } from "lit/decorators.js"
import { cardStyles } from "./shared"
import type { PartnerTypeAssignmentHistory } from "../lib/types"

@customElement("partner-assignment-history")
export class PartnerAssignmentHistory extends LitElement {
  static styles = [
    cardStyles,
    css`
      .card { background: var(--card); border-color: var(--border); }
      .list { display: flex; flex-direction: column; gap: 16px; }
      .item { position: relative; padding-left: 22px; }
      .item:not(:last-child)::before { content: ""; position: absolute; left: 5px; top: 15px; bottom: -18px; width: 1px; background: var(--border); }
      .dot { position: absolute; left: 0; top: 4px; width: 11px; height: 11px; border-radius: 50%; background: var(--color-feedback-info); box-shadow: 0 0 0 3px var(--accent); }
      .dot.inactive { background: var(--color-feedback-destructive); }
      .dot.active { background: var(--color-feedback-success); }
      .top { display: flex; justify-content: space-between; gap: 12px; }
      .change { color: var(--foreground); font-size: 13px; font-weight: 700; }
      .date { color: var(--muted-foreground); font-size: 11px; white-space: nowrap; }
      .reason, .actor { color: var(--muted-foreground); font-size: 12px; margin-top: 3px; }
      .empty { color: var(--muted-foreground); font-size: 12px; }
    `,
  ]

  @property({ attribute: false }) history: PartnerTypeAssignmentHistory[] = []
  @property({ type: String }) title = "Assignment history"

  private format(value: string) {
    if (!value) return "—"
    const date = new Date(value)
    return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date)
  }

  render() {
    return html`
      <div class="card">
        <div class="head"><h3 class="title">${this.title}</h3></div>
        ${this.history.length === 0
          ? html`<div class="empty">No status changes have been recorded.</div>`
          : html`<div class="list">
              ${this.history.map((event) => html`
                <div class="item">
                  <span class="dot ${event.newStatus.toLowerCase()}" aria-hidden="true"></span>
                  <div class="top">
                    <span class="change">${event.previousStatus || "Created"} → ${event.newStatus}</span>
                    <span class="date">${this.format(event.changedAt)}</span>
                  </div>
                  ${event.reason ? html`<div class="reason">${event.reason}</div>` : html``}
                  ${event.changedByName ? html`<div class="actor">Changed by ${event.changedByName}</div>` : html``}
                </div>
              `)}
            </div>`}
      </div>
    `
  }
}

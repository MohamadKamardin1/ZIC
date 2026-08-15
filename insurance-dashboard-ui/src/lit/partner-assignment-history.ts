import { LitElement, css, html } from "lit"
import { customElement, property } from "lit/decorators.js"
import { cardStyles } from "./shared"
import type { PartnerTypeAssignmentHistory } from "../lib/types"

@customElement("partner-assignment-history")
export class PartnerAssignmentHistory extends LitElement {
  static styles = [
    cardStyles,
    css`
      :host { display: block; }
      .card { background: var(--card); border-color: var(--border); }
      .head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
      .count { color: var(--muted-foreground); font-size: 11px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
      .list { display: flex; flex-direction: column; gap: 18px; margin-top: 18px; }
      .item { position: relative; padding-left: 24px; }
      .item:not(:last-child)::before { content: ""; position: absolute; left: 5px; top: 16px; bottom: -22px; width: 1px; background: var(--border); }
      .dot { position: absolute; left: 0; top: 4px; width: 11px; height: 11px; border: 2px solid var(--card); border-radius: 50%; background: var(--foreground); box-shadow: 0 0 0 1px var(--border); }
      .dot.audit { background: var(--muted-foreground); }
      .top { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
      .change { color: var(--foreground); font-size: 13px; font-weight: 750; }
      .date { color: var(--muted-foreground); font-size: 11px; white-space: nowrap; }
      .description, .reason, .actor { color: var(--muted-foreground); font-size: 12px; line-height: 1.45; margin-top: 4px; }
      .badges { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
      .badge { border: 1px solid var(--border); border-radius: 999px; color: var(--muted-foreground); font-size: 10px; font-weight: 700; padding: 3px 7px; text-transform: uppercase; letter-spacing: .05em; }
      .details { margin-top: 9px; border: 1px solid var(--border); border-radius: 7px; overflow: hidden; }
      .details summary { cursor: pointer; color: var(--foreground); font-size: 11px; font-weight: 700; list-style: none; padding: 7px 9px; }
      .details summary::-webkit-details-marker { display: none; }
      .details summary::after { content: "+"; float: right; color: var(--muted-foreground); }
      .details[open] summary::after { content: "−"; }
      .state-grid { display: grid; grid-template-columns: 1fr 1fr; border-top: 1px solid var(--border); }
      .state { min-width: 0; padding: 8px; }
      .state + .state { border-left: 1px solid var(--border); }
      .state-label { color: var(--muted-foreground); font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; }
      pre { overflow: auto; margin: 5px 0 0; color: var(--foreground); font: 10px/1.45 ui-monospace, SFMono-Regular, Menlo, monospace; white-space: pre-wrap; word-break: break-word; }
      .empty { color: var(--muted-foreground); font-size: 12px; padding: 4px 0; }
      @media (max-width: 620px) { .top { display: block; } .date { display: block; margin-top: 4px; } .state-grid { grid-template-columns: 1fr; } .state + .state { border-left: 0; border-top: 1px solid var(--border); } }
    `,
  ]

  @property({ attribute: false }) history: PartnerTypeAssignmentHistory[] = []
  @property({ type: String }) title = "Event history"

  private format(value: string) {
    if (!value) return "—"
    const date = new Date(value)
    return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date)
  }

  private label(value: string) {
    return value.replace(/_/g, " ").replace(/\b\w/g, (match) => match.toUpperCase())
  }

  private state(value: Record<string, unknown> | null | undefined) {
    return value && Object.keys(value).length ? JSON.stringify(value, null, 2) : "No state captured"
  }

  render() {
    return html`
      <div class="card">
        <div class="head">
          <h3 class="title">${this.title}</h3>
          <span class="count">${this.history.length} event${this.history.length === 1 ? "" : "s"}</span>
        </div>
        ${this.history.length === 0
          ? html`<div class="empty">No assignment activity has been recorded yet.</div>`
          : html`<div class="list">
              ${this.history.map((event) => html`
                <article class="item">
                  <span class="dot ${event.eventType === "AUDIT" ? "audit" : ""}" aria-hidden="true"></span>
                  <div class="top">
                    <span class="change">${event.eventType === "AUDIT" ? this.label(event.action || event.newStatus) : `${event.previousStatus || "Created"} → ${event.newStatus}`}</span>
                    <span class="date">${this.format(event.createdAt || event.changedAt)}</span>
                  </div>
                  ${event.description || event.reason ? html`<div class="description">${event.description || event.reason}</div>` : html``}
                  <div class="badges">
                    ${event.eventType === "AUDIT" ? html`<span class="badge">Audit</span>` : html`<span class="badge">Lifecycle</span>`}
                    ${event.sourceChannel ? html`<span class="badge">${event.sourceChannel}</span>` : html``}
                    ${event.entityType ? html`<span class="badge">${this.label(event.entityType)}</span>` : html``}
                    ${event.actorName || event.changedByName ? html`<span class="badge">${event.actorName || event.changedByName}</span>` : html``}
                  </div>
                  ${event.eventType === "AUDIT" && (event.beforeState || event.afterState || (event.changedFields && event.changedFields.length)) ? html`
                    <details class="details">
                      <summary>View change detail</summary>
                      ${event.changedFields?.length ? html`<div class="description" style="padding: 0 9px 8px">Changed: ${event.changedFields.join(", ")}</div>` : html``}
                      <div class="state-grid">
                        <div class="state"><div class="state-label">Before</div><pre>${this.state(event.beforeState)}</pre></div>
                        <div class="state"><div class="state-label">After</div><pre>${this.state(event.afterState)}</pre></div>
                      </div>
                    </details>
                  ` : html``}
                </article>
              `)}
            </div>`}
      </div>
    `
  }
}

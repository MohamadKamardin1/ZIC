import { LitElement, css, html } from "lit"
import { customElement, property, state } from "lit/decorators.js"

interface OnboardingEventRecord {
  id?: string
  eventType?: string
  action?: string
  fromStatus?: string | null
  toStatus?: string | null
  actorName?: string | null
  actor?: string | null
  notes?: string | null
  createdAt?: string
}

function titleize(value: string) {
  return value.replace(/_/g, " ").toLowerCase().replace(/(^|\s)\S/g, (letter: string) => letter.toUpperCase())
}

@customElement("onboarding-event-feed")
export class OnboardingEventFeed extends LitElement {
  @property({ attribute: false }) events: OnboardingEventRecord[] = []
  @property({ type: Boolean }) loading = false
  @property({ type: String }) emptyLabel = "No workflow events have been recorded yet."
  @state() private expanded = false

  static styles = css`
    :host { display: block; font-family: var(--font-sans, Inter, sans-serif); color: var(--foreground, #0f172a); }
    .shell { background: var(--card, #fff); border: 1px solid var(--border, #e2e8f0); border-radius: var(--radius, 12px); padding: 20px; box-shadow: 0 1px 3px rgba(15,23,42,.05); }
    .header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
    h3 { margin: 0; font-size: 15px; font-weight: 700; }
    .count { color: var(--muted-foreground, #64748b); font-size: 12px; font-weight: 600; }
    .feed { margin: 0; padding: 0; list-style: none; }
    .scroll { max-height: 300px; overflow-y: auto; padding-right: 4px; scrollbar-width: thin; scrollbar-color: var(--border, #cbd5e1) transparent; }
    .scroll::-webkit-scrollbar { width: 6px; }
    .scroll::-webkit-scrollbar-thumb { background: var(--border, #cbd5e1); border-radius: 999px; }
    .scroll::-webkit-scrollbar-track { background: transparent; }
    .event { position: relative; display: grid; grid-template-columns: 24px minmax(0, 1fr) auto; gap: 11px; padding: 0 0 18px; }
    .event:not(:last-child)::before { content: ""; position: absolute; left: 11px; top: 23px; bottom: 0; width: 1px; background: var(--border, #e2e8f0); }
    .marker { position: relative; z-index: 1; width: 22px; height: 22px; display: grid; place-items: center; border: 2px solid var(--primary, #2563eb); border-radius: 999px; background: var(--card, #fff); color: var(--primary, #2563eb); font-size: 10px; font-weight: 900; }
    .title { margin: 1px 0 3px; font-size: 13px; font-weight: 700; }
    .meta, .notes { color: var(--muted-foreground, #64748b); font-size: 11px; line-height: 1.45; }
    .notes { margin-top: 5px; }
    time { color: var(--muted-foreground, #64748b); font-size: 11px; white-space: nowrap; }
    .toggle { display: inline-flex; align-items: center; gap: 6px; margin-top: 12px; padding: 6px 14px; border: 1px solid var(--border, #cbd5e1); border-radius: 8px; background: var(--card, #fff); color: var(--primary, #2563eb); font: 700 12px Inter, sans-serif; cursor: pointer; transition: background .15s ease; }
    .toggle:hover { background: var(--accent, #f1f5f9); }
    .empty, .loading { padding: 20px 4px; text-align: center; color: var(--muted-foreground, #64748b); font-size: 12px; }
    .skeleton { height: 12px; margin: 9px 0; border-radius: 5px; background: linear-gradient(90deg, var(--muted, #f1f5f9), var(--card, #fff), var(--muted, #f1f5f9)); background-size: 200% 100%; animation: shimmer 1.4s infinite; }
    @keyframes shimmer { to { background-position: -200% 0; } }
  `

  private formatDate(value?: string) {
    if (!value) return "Unknown time"
    const date = new Date(value)
    return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date)
  }

  render() {
    const showAll = this.expanded || this.events.length <= 3
    const visible = showAll ? this.events : this.events.slice(0, 3)
    return html`
      <section class="shell" aria-label="Application event history">
        <div class="header"><h3>Event history</h3><span class="count">${this.events.length} ${this.events.length === 1 ? "event" : "events"}</span></div>
        ${this.loading ? html`<div class="loading"><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div></div>` : this.events.length === 0 ? html`<div class="empty">${this.emptyLabel}</div>` : html`
          <div class="scroll">
            <ol class="feed">
              ${visible.map((event) => html`
                <li class="event">
                  <span class="marker">✓</span>
                  <div>
                    <div class="title">${titleize(event.eventType || event.action || "Workflow update")}</div>
                    <div class="meta">${event.actorName || event.actor || "System"}${event.fromStatus || event.toStatus ? html` · ${titleize(event.fromStatus || "Created")} → ${titleize(event.toStatus || "Updated")}` : ""}</div>
                    ${event.notes ? html`<div class="notes">${event.notes}</div>` : ""}
                  </div>
                  <time>${this.formatDate(event.createdAt)}</time>
                </li>
              `)}
            </ol>
          </div>
          ${this.events.length > 3 ? html`<button class="toggle" @click=${() => { this.expanded = !this.expanded }}>${this.expanded ? "Show less" : `Show all ${this.events.length} events`}${this.expanded ? " ↑" : " ↓"}</button>` : ""}
        `}
      </section>
    `
  }
}

declare global { interface HTMLElementTagNameMap { "onboarding-event-feed": OnboardingEventFeed } }

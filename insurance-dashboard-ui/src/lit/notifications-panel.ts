import { LitElement, html, css } from "lit"
import { customElement, property, state } from "lit/decorators.js"
import { cardStyles } from "./shared"
import type { NotificationsData } from "../lib/types"

const toneColors: Record<string, { bg: string; fg: string; ring: string }> = {
  warning: { bg: "#fffbeb", fg: "#d97706", ring: "#fcd34d" },
  success: { bg: "#ecfdf5", fg: "#059669", ring: "#6ee7b7" },
  destructive: { bg: "#fef2f2", fg: "#dc2626", ring: "#fca5a5" },
  muted: { bg: "#f1f5f9", fg: "#64748b", ring: "#cbd5e1" },
}

@customElement("zic-notifications-panel")
export class NotificationsPanel extends LitElement {
  static styles = [
    cardStyles,
    css`
      .statuses {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 10px;
        margin-bottom: 16px;
      }
      .status {
        border-radius: 12px;
        border: 1px solid var(--border);
        padding: 12px 8px;
        text-align: center;
      }
      .status .ring {
        width: 30px;
        height: 30px;
        border-radius: 50%;
        margin: 0 auto 6px;
        display: grid;
        place-items: center;
        color: #fff;
        font-size: 13px;
        font-weight: 700;
      }
      .status .lab {
        font-size: 11.5px;
        color: var(--muted-foreground);
        font-weight: 500;
      }
      .tabs {
        display: flex;
        gap: 8px;
        margin-bottom: 8px;
      }
      .tabs .tab {
        font-size: 12.5px;
        font-weight: 600;
        padding: 8px 14px;
        border-radius: 8px;
        border: 1px solid var(--border);
        background: var(--card);
        color: var(--muted-foreground);
        cursor: pointer;
      }
      .tabs .tab.active {
        color: var(--primary);
        border-color: color-mix(in srgb, var(--primary) 40%, transparent);
        background: var(--accent);
      }
      .list {
        display: flex;
        flex-direction: column;
      }
      .item {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 11px 2px;
        border-bottom: 1px solid var(--border);
        font-size: 13px;
      }
      .item:last-child {
        border-bottom: 0;
      }
      .dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--primary);
        flex: none;
      }
      .tag {
        font-size: 10.5px;
        font-weight: 700;
        color: var(--primary);
        background: var(--accent);
        padding: 2px 6px;
        border-radius: 5px;
      }
      .item .name {
        font-weight: 600;
        color: var(--foreground);
        flex: 1;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .item .amt {
        font-weight: 700;
        color: var(--foreground);
      }
      .pill {
        font-size: 11px;
        font-weight: 600;
        color: #059669;
        background: #ecfdf5;
        padding: 3px 8px;
        border-radius: 9999px;
      }
      .time {
        color: var(--muted-foreground);
        font-size: 12px;
        min-width: 34px;
        text-align: right;
      }
      .viewall {
        text-align: center;
        margin-top: 12px;
        font-size: 13px;
        font-weight: 600;
        color: var(--primary);
        cursor: pointer;
      }
    `,
  ]

  @property({ attribute: false }) data!: NotificationsData
  @state() tab: "unread" | "all" = "unread"

  render() {
    if (!this.data) return html``
    return html`
      <div class="card">
        <div class="head"><h3 class="title">Notifications</h3></div>
        <div class="statuses">
          ${this.data.statuses.map((s) => {
            const t = toneColors[s.tone]
            return html`
              <div class="status" style="background:${t.bg};border-color:${t.ring}">
                <div class="ring" style="background:${t.fg}">${s.count}</div>
                <div class="lab">${s.label}</div>
              </div>
            `
          })}
        </div>
        <div class="tabs">
          <span class="tab ${this.tab === "unread" ? "active" : ""}" @click=${() => (this.tab = "unread")}>
            ${this.data.unread} Unread
          </span>
          <span class="tab ${this.tab === "all" ? "active" : ""}" @click=${() => (this.tab = "all")}>All</span>
        </div>
        <div class="list">
          ${this.data.items.map(
            (it) => html`
              <div class="item">
                <span class="dot"></span>
                ${it.tag ? html`<span class="tag">${it.tag}</span>` : null}
                <span class="name">${it.title}</span>
                ${it.amount ? html`<span class="amt">${it.amount}</span>` : null}
                <span class="pill">${it.status}</span>
                <span class="time">${it.time}</span>
              </div>
            `,
          )}
        </div>
        <div class="viewall">View All</div>
      </div>
    `
  }
}

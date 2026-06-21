import { LitElement, html, css, svg } from "lit"
import { customElement, property } from "lit/decorators.js"
import { cardStyles } from "./shared"
import type { ClaimGauge } from "../lib/types"

@customElement("zic-claims-card")
export class ClaimsCard extends LitElement {
  static styles = [
    cardStyles,
    css`
      .card {
        background: linear-gradient(160deg, #f0fdf4 0%, #ecfdf5 100%);
        border-color: #d1fae5;
      }
      .grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 18px 12px;
      }
      .item {
        display: flex;
        align-items: center;
        gap: 12px;
      }
      .donut {
        position: relative;
        width: 64px;
        height: 64px;
        flex: none;
      }
      .donut .pct {
        position: absolute;
        inset: 0;
        display: grid;
        place-items: center;
        font-size: 13px;
        font-weight: 700;
      }
      .meta .name {
        font-size: 13px;
        font-weight: 600;
        color: var(--foreground);
      }
      .meta .sub {
        font-size: 12px;
        color: var(--muted-foreground);
        margin-top: 2px;
      }
    `,
  ]

  @property({ attribute: false }) data!: ClaimGauge[]

  private donut(c: ClaimGauge) {
    const r = 26
    const circ = 2 * Math.PI * r
    const dash = (c.percent / 100) * circ
    return svg`
      <svg width="64" height="64" viewBox="0 0 64 64">
        <circle cx="32" cy="32" r="${r}" fill="none" stroke="#e2e8f0" stroke-width="6" stroke-dasharray="2 4" stroke-linecap="round" />
        <circle cx="32" cy="32" r="${r}" fill="none" stroke="${c.color}" stroke-width="6"
          stroke-dasharray="${dash} ${circ}" stroke-linecap="round"
          transform="rotate(-90 32 32)" />
      </svg>
    `
  }

  render() {
    if (!this.data) return html``
    return html`
      <div class="card">
        <div class="head">
          <h3 class="title">Claims Processed</h3>
          <div class="icon-badge" style="background:#fef3c7;color:#d97706">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6" /><path d="m9 15 2 2 4-4" />
            </svg>
          </div>
        </div>
        <div class="grid">
          ${this.data.map(
            (c) => html`
              <div class="item">
                <div class="donut">
                  ${this.donut(c)}
                  <span class="pct" style="color:${c.color}">${c.percent}%</span>
                </div>
                <div class="meta">
                  <div class="name">${c.label}</div>
                  <div class="sub">${c.claims} claims</div>
                </div>
              </div>
            `,
          )}
        </div>
      </div>
    `
  }
}

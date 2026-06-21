import { LitElement, html, css } from "lit"
import { customElement, property } from "lit/decorators.js"
import { cardStyles } from "./shared"
import type { PoliciesIssued } from "../lib/types"

@customElement("zic-policies-card")
export class PoliciesCard extends LitElement {
  static styles = [
    cardStyles,
    css`
      .total {
        display: flex;
        align-items: baseline;
        gap: 10px;
        margin-bottom: 18px;
      }
      .total b {
        font-size: 40px;
        font-weight: 800;
        letter-spacing: -0.02em;
        line-height: 1;
        color: var(--foreground);
      }
      .delta {
        font-size: 13px;
        font-weight: 600;
        color: var(--success);
      }
      .rows {
        display: flex;
        flex-direction: column;
        gap: 14px;
      }
      .row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 13px;
      }
      .row .label {
        color: var(--muted-foreground);
      }
      .row .vals {
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 600;
        color: var(--foreground);
      }
      .row .pct {
        color: var(--success);
        font-weight: 600;
      }
      .badge {
        background: var(--accent);
        color: var(--accent-foreground);
      }
    `,
  ]

  @property({ attribute: false }) data!: PoliciesIssued

  render() {
    if (!this.data) return html``
    return html`
      <div class="card">
        <div class="head">
          <h3 class="title">Total Policies Issued</h3>
          <div class="icon-badge badge">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M9 11l3 3L22 4" /><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
            </svg>
          </div>
        </div>
        <div class="total">
          <b>${this.data.total}</b>
          <span class="delta">${this.data.delta}% &uarr;</span>
        </div>
        <div class="rows">
          ${this.data.breakdown.map(
            (b) => html`
              <div class="row">
                <span class="label">${b.label}</span>
                <span class="vals">
                  ${b.count}
                  <span class="pct">${b.delta}% &uarr;</span>
                </span>
              </div>
            `,
          )}
        </div>
      </div>
    `
  }
}

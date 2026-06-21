import { LitElement, html, css } from "lit"
import { customElement, property } from "lit/decorators.js"
import { cardStyles } from "./shared"
import type { PartnersOnboarded } from "../lib/types"

@customElement("zic-partners-card")
export class PartnersCard extends LitElement {
  static styles = [
    cardStyles,
    css`
      .card {
        background: linear-gradient(160deg, #fff7ed 0%, #fffbeb 100%);
        border-color: #fed7aa;
      }
      .total {
        display: flex;
        align-items: baseline;
        gap: 8px;
        margin-bottom: 16px;
      }
      .total b {
        font-size: 32px;
        font-weight: 800;
        color: var(--foreground);
        line-height: 1;
      }
      .total span {
        font-size: 13px;
        color: var(--muted-foreground);
      }
      .rows {
        display: flex;
        flex-direction: column;
        gap: 14px;
      }
      .row .top {
        display: flex;
        justify-content: space-between;
        font-size: 12.5px;
        margin-bottom: 6px;
      }
      .row .top .label {
        color: var(--foreground);
        font-weight: 500;
      }
      .row .top .nums {
        color: var(--muted-foreground);
        font-weight: 600;
        display: flex;
        gap: 10px;
      }
      .bar {
        height: 6px;
        border-radius: 9999px;
        overflow: hidden;
        display: flex;
        background: #fde9d3;
      }
      .bar .left {
        background: var(--chart-2);
      }
      .bar .right {
        background: var(--chart-4);
      }
      .more {
        margin-top: 14px;
        text-align: right;
        font-size: 12.5px;
        font-weight: 600;
        color: var(--primary);
        cursor: pointer;
      }
    `,
  ]

  @property({ attribute: false }) data!: PartnersOnboarded

  render() {
    if (!this.data) return html``
    return html`
      <div class="card">
        <div class="head">
          <h3 class="title">Partners Onboarded</h3>
          <div class="icon-badge" style="background:#ffedd5;color:#ea580c">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M17 11l2 2 4-4" /><path d="M11 19H4a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h11" /><circle cx="9" cy="7" r="4" />
            </svg>
          </div>
        </div>
        <div class="total"><b>${this.data.total}</b><span>Partners</span></div>
        <div class="rows">
          ${this.data.bars.map(
            (b) => html`
              <div class="row">
                <div class="top">
                  <span class="label">${b.label}</span>
                  <span class="nums"><span>${b.left}%</span><span>${b.right}%</span></span>
                </div>
                <div class="bar">
                  <div class="left" style="width:${b.left}%"></div>
                  <div class="right" style="width:${b.right}%"></div>
                </div>
              </div>
            `,
          )}
        </div>
        <div class="more">More...</div>
      </div>
    `
  }
}

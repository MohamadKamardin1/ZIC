import { LitElement, html, css, svg } from "lit"
import { customElement, property } from "lit/decorators.js"
import { cardStyles } from "./shared"
import type { DebitedAmount } from "../lib/types"

@customElement("zic-debited-gauge")
export class DebitedGauge extends LitElement {
  static styles = [
    cardStyles,
    css`
      .gauge-wrap {
        display: grid;
        place-items: center;
        margin: 4px 0 10px;
      }
      .center {
        margin-top: -34px;
        text-align: center;
      }
      .center b {
        font-size: 26px;
        font-weight: 800;
        color: var(--foreground);
      }
      .center small {
        display: block;
        font-size: 12px;
        color: var(--muted-foreground);
        margin-top: 2px;
      }
      .segments {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 8px;
        margin-top: 14px;
      }
      .seg {
        text-align: center;
      }
      .seg .label {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        font-size: 12px;
        color: var(--muted-foreground);
        font-weight: 500;
      }
      .seg .dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
      }
      .seg .val {
        font-size: 13px;
        font-weight: 700;
        color: var(--foreground);
        margin-top: 4px;
      }
      .badge {
        background: var(--accent);
        color: var(--accent-foreground);
      }
    `,
  ]

  @property({ attribute: false }) data!: DebitedAmount

  private polar(cx: number, cy: number, r: number, deg: number) {
    const rad = (deg * Math.PI) / 180
    return { x: cx + r * Math.cos(rad), y: cy - r * Math.sin(rad) }
  }

  private arc(a1: number, a2: number, color: string) {
    const cx = 90
    const cy = 88
    const r = 70
    const p1 = this.polar(cx, cy, r, a1)
    const p2 = this.polar(cx, cy, r, a2)
    return svg`<path d="M ${p1.x} ${p1.y} A ${r} ${r} 0 0 1 ${p2.x} ${p2.y}"
      fill="none" stroke="${color}" stroke-width="14" stroke-linecap="round" />`
  }

  private gauge() {
    const pct = this.data.gaugePercent
    const needleAngle = 180 - (pct / 100) * 180
    const tip = this.polar(90, 88, 54, needleAngle)
    return svg`
      <svg width="180" height="100" viewBox="0 0 180 100">
        ${this.arc(180, 137, "#10b981")}
        ${this.arc(135, 92, "#f59e0b")}
        ${this.arc(90, 47, "#f97316")}
        ${this.arc(45, 2, "#ef4444")}
        <line x1="90" y1="88" x2="${tip.x}" y2="${tip.y}" stroke="var(--foreground)" stroke-width="3" stroke-linecap="round" />
        <circle cx="90" cy="88" r="6" fill="var(--foreground)" />
      </svg>
    `
  }

  render() {
    if (!this.data) return html``
    return html`
      <div class="card">
        <div class="head">
          <h3 class="title">Debited Amount</h3>
          <div class="icon-badge badge">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect width="20" height="14" x="2" y="5" rx="2" /><line x1="2" x2="22" y1="10" y2="10" />
            </svg>
          </div>
        </div>
        <div class="gauge-wrap">${this.gauge()}</div>
        <div class="center">
          <b>${this.data.total}</b>
          <small>Total Debited</small>
        </div>
        <div class="segments">
          ${this.data.segments.map(
            (s) => html`
              <div class="seg">
                <span class="label"><span class="dot" style="background:${s.color}"></span>${s.label}</span>
                <div class="val">${s.value}</div>
              </div>
            `,
          )}
        </div>
      </div>
    `
  }
}

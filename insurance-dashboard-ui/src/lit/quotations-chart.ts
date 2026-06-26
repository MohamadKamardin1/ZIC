import { LitElement, html, css, svg } from "lit"
import { customElement, property, state } from "lit/decorators.js"
import { cardStyles } from "./shared"
import type { Quotations } from "../lib/types"

@customElement("zic-quotations-chart")
export class QuotationsChart extends LitElement {
  static styles = [
    cardStyles,
    css`
      .top {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 8px;
      }
      .title-row {
        display: flex;
        align-items: center;
        gap: 10px;
      }
      .ic {
        width: 34px;
        height: 34px;
        border-radius: 9px;
        display: grid;
        place-items: center;
        background: var(--color-bg-icon-destructive);
        color: var(--color-text-icon-destructive);
      }
      .total {
        margin-top: 8px;
      }
      .total .lab {
        font-size: 12.5px;
        color: var(--muted-foreground);
      }
      .total b {
        font-size: 26px;
        font-weight: 800;
        color: var(--foreground);
        display: block;
        line-height: 1.1;
      }
      .toggle {
        display: inline-flex;
        background: var(--secondary);
        border-radius: 9999px;
        padding: 3px;
      }
      .toggle button {
        border: 0;
        background: transparent;
        font-family: inherit;
        font-size: 12.5px;
        font-weight: 600;
        color: var(--muted-foreground);
        padding: 6px 16px;
        border-radius: 9999px;
        cursor: pointer;
      }
      .toggle button.active {
        background: var(--destructive);
        color: var(--destructive-foreground);
      }
      .chart {
        width: 100%;
        height: 260px;
        margin-top: 8px;
      }
      .legend {
        display: flex;
        flex-wrap: wrap;
        gap: 18px;
        margin-top: 10px;
        padding-top: 14px;
        border-top: 1px solid var(--border);
      }
      .legend .l {
        display: flex;
        align-items: center;
        gap: 7px;
        font-size: 13px;
        color: var(--foreground);
        font-weight: 600;
      }
      .legend .dot {
        width: 10px;
        height: 10px;
        border-radius: 3px;
      }
      .legend .l small {
        color: var(--muted-foreground);
        font-weight: 500;
      }
    `,
  ]

  @property({ attribute: false }) data!: Quotations
  @state() period: "Monthly" | "Yearly" = "Monthly"

  private smooth(points: { x: number; y: number }[]) {
    if (points.length < 2) return ""
    let d = `M ${points[0].x} ${points[0].y}`
    for (let i = 0; i < points.length - 1; i++) {
      const p0 = points[i === 0 ? 0 : i - 1]
      const p1 = points[i]
      const p2 = points[i + 1]
      const p3 = points[i + 2 < points.length ? i + 2 : i + 1]
      const cp1x = p1.x + (p2.x - p0.x) / 6
      const cp1y = p1.y + (p2.y - p0.y) / 6
      const cp2x = p2.x - (p3.x - p1.x) / 6
      const cp2y = p2.y - (p3.y - p1.y) / 6
      d += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p2.x} ${p2.y}`
    }
    return d
  }

  private chart() {
    const W = 600
    const H = 260
    const padL = 34
    const padR = 12
    const padT = 16
    const padB = 28
    const innerW = W - padL - padR
    const innerH = H - padT - padB
    const max = 91
    const yTicks = [0, 25, 50, 75, 91]
    const n = this.data.labels.length

    const xFor = (i: number) => padL + (innerW * i) / (n - 1)
    const yFor = (v: number) => padT + innerH - (v / max) * innerH

    return svg`
      <svg class="chart" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" width="100%">
        ${yTicks.map(
          (t) => svg`
            <line x1="${padL}" y1="${yFor(t)}" x2="${W - padR}" y2="${yFor(t)}"
              stroke="var(--border)" stroke-width="1" stroke-dasharray="3 4" />
            <text x="${padL - 8}" y="${yFor(t) + 4}" text-anchor="end"
              font-size="11" fill="var(--muted-foreground)">${t}</text>
          `,
        )}
        ${this.data.series.map((s) => {
          const pts = s.points.map((v, i) => ({ x: xFor(i), y: yFor(v) }))
          const line = this.smooth(pts)
          const area = `${line} L ${pts[pts.length - 1].x} ${yFor(0)} L ${pts[0].x} ${yFor(0)} Z`
          return svg`
            <path d="${area}" fill="${s.color}" opacity="0.08" />
            <path d="${line}" fill="none" stroke="${s.color}" stroke-width="2.5"
              stroke-linecap="round" stroke-linejoin="round" />
          `
        })}
        ${this.data.labels.map(
          (lab, i) => svg`
            <text x="${xFor(i)}" y="${H - 8}" text-anchor="middle"
              font-size="11" fill="var(--muted-foreground)">${lab}</text>
          `,
        )}
      </svg>
    `
  }

  render() {
    if (!this.data) return html``
    return html`
      <div class="card">
        <div class="top">
          <div>
            <div class="title-row">
              <div class="ic">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6" />
                </svg>
              </div>
              <h3 class="title">Quotations</h3>
            </div>
            <div class="total">
              <span class="lab">Total quotations</span>
              <b>${this.data.total}</b>
            </div>
          </div>
          <div class="toggle">
            <button class=${this.period === "Monthly" ? "active" : ""} @click=${() => (this.period = "Monthly")}>Monthly</button>
            <button class=${this.period === "Yearly" ? "active" : ""} @click=${() => (this.period = "Yearly")}>Yearly</button>
          </div>
        </div>
        ${this.chart()}
        <div class="legend">
          ${this.data.legend.map(
            (l) => html`
              <span class="l">
                <span class="dot" style="background:${l.color}"></span>
                ${l.label} ${l.percent}% <small>${l.count}</small>
              </span>
            `,
          )}
        </div>
      </div>
    `
  }
}

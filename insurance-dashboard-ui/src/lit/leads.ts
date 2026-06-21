import { LitElement, html, css } from "lit"
import { customElement, property } from "lit/decorators.js"
import { cardStyles } from "./shared"
import type { LeadItem } from "../lib/types"

@customElement("zic-leads")
export class Leads extends LitElement {
  static styles = [
    cardStyles,
    css`
      :host {
        display: flex;
        flex-direction: column;
      }
      table {
        width: 100%;
        border-collapse: collapse;
      }
      th {
        text-align: left;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: var(--muted-foreground);
        font-weight: 600;
        padding: 0 0 10px;
      }
      th:last-child,
      td:last-child {
        text-align: right;
      }
      td {
        padding: 10px 0;
        font-size: 13px;
        border-top: 1px solid var(--border);
      }
      .rank {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        color: var(--muted-foreground);
        font-weight: 600;
      }
      .medal {
        width: 16px;
        height: 16px;
        color: var(--chart-3);
      }
      .name {
        font-weight: 600;
        color: var(--foreground);
      }
      .amt {
        font-weight: 700;
        color: var(--foreground);
      }
      .card {
        height: 100%;
      }
    `,
  ]

  @property({ attribute: false }) leads!: LeadItem[]

  render() {
    if (!this.leads) return html``
    return html`
      <div class="card">
        <div class="head"><h3 class="title">Leads</h3></div>
        <table>
          <thead>
            <tr><th>Place</th><th>Name</th><th>Amount</th></tr>
          </thead>
          <tbody>
            ${this.leads.map(
              (l) => html`
                <tr>
                  <td>
                    <span class="rank">
                      ${l.rank}
                      <svg class="medal" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="6"/><path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/></svg>
                    </span>
                  </td>
                  <td class="name">${l.name}</td>
                  <td class="amt">${l.amount}</td>
                </tr>
              `,
            )}
          </tbody>
        </table>
      </div>
    `
  }
}

import { LitElement, html, css } from "lit"
import { customElement, property } from "lit/decorators.js"
import { cardStyles } from "./shared"
import type { TodoItem, LeadItem } from "../lib/types"

@customElement("zic-todo-leads")
export class TodoLeads extends LitElement {
  static styles = [
    cardStyles,
    css`
      :host {
        display: flex;
        flex-direction: column;
        gap: 20px;
      }
      .add {
        width: 26px;
        height: 26px;
        border-radius: 7px;
        display: grid;
        place-items: center;
        background: var(--accent);
        color: var(--primary);
        cursor: pointer;
      }
      .todo {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 12px 0;
        border-bottom: 1px solid var(--border);
      }
      .todo:last-child {
        border-bottom: 0;
      }
      .chk {
        width: 18px;
        height: 18px;
        border-radius: 50%;
        border: 2px solid var(--border);
        flex: none;
      }
      .todo .t {
        flex: 1;
        font-size: 13px;
        font-weight: 600;
        color: var(--foreground);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .todo .d {
        font-size: 12px;
        color: var(--muted-foreground);
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
    `,
  ]

  @property({ attribute: false }) todos!: TodoItem[]
  @property({ attribute: false }) leads!: LeadItem[]

  render() {
    if (!this.todos || !this.leads) return html``
    return html`
      <div class="card">
        <div class="head">
          <h3 class="title">Todo</h3>
          <span class="add">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>
          </span>
        </div>
        ${this.todos.map(
          (t) => html`
            <div class="todo">
              <span class="chk"></span>
              <span class="t">${t.title}</span>
              <span class="d">${t.date}</span>
            </div>
          `,
        )}
      </div>

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

import { LitElement, html, css } from "lit"
import { customElement, property } from "lit/decorators.js"
import { cardStyles } from "./shared"
import type { TodoItem } from "../lib/types"

@customElement("zic-todo")
export class Todo extends LitElement {
  static styles = [
    cardStyles,
    css`
      :host {
        display: flex;
        flex-direction: column;
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
      .card {
        height: 100%;
      }
    `,
  ]

  @property({ attribute: false }) todos!: TodoItem[]

  render() {
    if (!this.todos) return html``
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
    `
  }
}

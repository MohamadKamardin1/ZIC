import { css } from "lit"

/** Shared card chrome + typography, consumes :root design tokens. */
export const cardStyles = css`
  :host {
    display: block;
    font-family: var(--font-sans, "Inter", sans-serif);
    color: var(--card-foreground, #1e293b);
    height: 100%;
  }
  .card {
    background: var(--card, #fff);
    border: 1px solid var(--border, #e2e8f0);
    border-radius: var(--radius, 0.75rem);
    padding: 20px;
    height: 100%;
    box-sizing: border-box;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 1px 3px rgba(15, 23, 42, 0.04);
  }
  .head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
  }
  .title {
    font-size: 15px;
    font-weight: 600;
    color: var(--foreground, #1e293b);
    margin: 0;
    letter-spacing: -0.01em;
  }
  .icon-badge {
    width: 38px;
    height: 38px;
    border-radius: 10px;
    display: grid;
    place-items: center;
    flex: none;
  }
  .muted {
    color: var(--muted-foreground, #64748b);
  }
  svg {
    display: block;
  }
`

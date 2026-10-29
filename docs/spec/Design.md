# Design.md

**Educational material only. Nothing here is investment advice or a promise of profit.**

This covers the visual design of the Streamlit dashboard (Phase 8: Stage 3 manual signals, paper-trading monitor, journal). It is a working instrument, not a consumer app — the design brief here is deliberately the opposite of a gamified retail trading app.

## Design principle

Gamified trading apps use bright colors, big numbers, and constant motion to encourage frequent checking and impulsive trades — exactly the "psychological slippage" this project is built to avoid (delayed entries, moved stops, revenge trades). This dashboard should feel closer to **an instrument panel built for a long shift**: quiet, legible at a glance, calm even when it's reporting a loss. Nothing on screen should create urgency that the strategy's own rules didn't create.

---

## 1. Color

Dark surface by default (most screen time happens during or around market hours, and a dark panel reduces visual fatigue over a trading session), with a light-mode variant built from the same tokens.

| Token | Hex | Role |
|---|---|---|
| `bg-base` | `#14171C` | Page background — a dark warm-neutral charcoal, not pure black (pure black makes adjacent colors vibrate and read harsher than intended) |
| `surface-panel` | `#1C2028` | Card/panel backgrounds, slightly raised off the base |
| `text-primary` | `#E6E8EB` | Primary text — off-white, not stark white |
| `text-muted` | `#8B93A1` | Secondary labels, timestamps, metadata |
| `signal-long` | `#4F9D6E` | Buy/long bias, positive P&L — a desaturated forest green, not a neon "go" green. Deliberately calm rather than celebratory. |
| `signal-short` | `#B5564F` | Sell/short bias, negative P&L — a muted brick red, not alarm red. Visible without spiking adrenaline. |
| `signal-caution` | `#C99A4B` | No-trade / regime caution / news-flag warnings — a muted amber |
| `accent-focus` | `#5B7FA6` | Links, active tab, focus rings — a quiet slate blue, used sparingly |

Signal colors never stand alone: every long/short/caution state is also labeled in text and uses a distinct icon shape (▲ / ▼ / ■), so the dashboard remains usable for colorblind users and stays legible if screenshotted in black-and-white for the journal.

Avoid: neon green/red P&L tickers, gradient backgrounds, or any flashing/pulsing element on a live number — all of which are standard in retail trading app design and run directly against this project's discipline goals.

## 2. Typography

Two families, clearly distinct roles:

- **UI text (labels, body, narrative):** `IBM Plex Sans` — a humanist grotesk with enough warmth to avoid feeling like generic SaaS chrome, and genuinely designed for data-dense interfaces (it's the same family IBM uses across its own technical dashboards).
- **Numeric/tabular data (prices, P&L, R-multiples, timestamps):** `IBM Plex Mono` — monospaced so columns of prices and stop/target levels align vertically and can be scanned quickly; tabular figures throughout, never proportional numerals in a data table.

Fallback stacks: `'IBM Plex Sans', -apple-system, sans-serif` and `'IBM Plex Mono', 'SFMono-Regular', monospace` so the dashboard degrades gracefully without the fonts installed.

Type scale (base 15px, for a dense data interface rather than a marketing page):
| Role | Size | Weight |
|---|---|---|
| Panel title | 16px | Medium (500) |
| Section label | 13px | Medium (500), sentence case — not tracked-out all-caps |
| Body / table text | 14px | Regular (400) |
| Numeric data (tables, P&L) | 14px | Regular (400), tabular-nums |
| Large stat (e.g., today's P&L headline) | 28px | Medium (500) |

No single word or phrase in any headline is bolded or recolored for emphasis — if something needs emphasis, it earns its own line or its own labeled panel instead.

## 3. Layout

A dense, grid-based dashboard — left-aligned throughout (centered text reads as a marketing page, not an instrument panel):

```
┌─────────────────────────────────────────────────────────┐
│ Data health ● live     Regime: TREND_UP     Kill-switch: off │
├───────────────────────────┬───────────────────────────────┤
│  Open signals (table)      │  Equity curve + drawdown       │
│  symbol | dir | entry |    │  (plotly line, muted palette)  │
│  stop | target | expiry    │                                 │
├───────────────────────────┴───────────────────────────────┤
│  Signal detail panel (selected row): full trade plan,       │
│  rationale, invalidation condition, news flags,              │
│  + max entry (e_max/e_min), net RR after costs, realised     │
│  risk (₹ and %), expected slippage, fill probability, expiry │
├───────────────────────────┬───────────────────────────────┤
│  Journal table: taken /    │  Drift panel: CUSUM vs threshold│
│  skipped / modified,       │  + slippage model vs. actual    │
│  slippage, system vs.      │  (small line chart, muted)      │
│  actual equity             │                                  │
└───────────────────────────┴───────────────────────────────┘
```

- Status strip at the top is always visible (data health, current regime, kill-switch state) — the dashboard should never let the user forget whether the system currently trusts its own data.
- Tables, not cards: this is tabular financial data, and a card-grid layout (the generic "SaaS kit" look) would waste space and break scannability for rows that need to be compared line by line.
- One line-height, one border style (hairline `1px solid rgba(255,255,255,0.08)`), used consistently — no mixed shadow/border styles between panels.

## 4. States worth designing explicitly

- **No-trade state:** shown plainly with its reason (regime, event-day, daily-loss-limit hit, stale data) — never a blank or empty-looking panel. An empty dashboard should read as "nothing qualifies today," not as "something is broken."
- **Kill-switch active:** the status strip switches its background to `signal-caution` at low opacity and stays that way until manually reset — deliberately the one moment this dashboard is allowed to be visually loud, because it is the one moment that should interrupt the user.
- **Signal expired:** greyed out (`text-muted`) with a strikethrough on the entry zone, rather than removed from the table — so a missed signal is still visible as a missed signal, supporting the "never chase" discipline rule.
- **Drift alarm (CUSUM):** the drift panel's line crossing its threshold switches that panel's border to `signal-caution`, with a short label ("live expectancy below validated baseline — review needed") — this flags a required review, not an instruction to change anything automatically, and stays visually calm relative to the kill-switch state, which remains the one true interrupt.

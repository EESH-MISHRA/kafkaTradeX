# PRD.md — Project Requirement Document

**Project:** NSE Algo Strategy Research, Paper-Trading & Manual Signal System
**Status:** Planning — supersedes all earlier LLM-agent / multi-laptop architecture discussions
**Educational material only. Nothing here is investment advice or a promise of profit.**

---

## 1. What we are building

A research-grade trading framework for the Indian market (NSE) that:

1. **Researches** — builds and validates deterministic, rule-based trading strategies on historical data (train / validation / untouched final test split).
2. **Paper-trades** — runs the same, frozen strategy logic automatically against live/replayed data in a simulated broker, with pessimistic fills and real costs.
3. **Signals** — once a strategy passes a pre-defined go/no-go bar, the software outputs complete trade plans (entry zone, stop, targets, size, rationale, expiry). **The user places every real order by hand. The software never sends an order to a broker.**

No stage of this project automates live order placement. This is a deliberate, permanent design decision — not a temporary limitation — because it removes the SEBI-compliant broker-API execution burden (static IP whitelisting, daily 2FA, order-rate limits, Strategy IDs) while keeping a human decision-maker in the loop at the point money actually moves.

### Explicitly NOT in scope
- No automated order placement to any broker, ever, in this version of the project.
- No LLM or machine-learning model decides trade direction. An LLM may only summarize/tag news headlines for the risk-blackout filter.
- No claims of profitability. A strategy that fails validation is reported as "no edge found" — that is a valid, respected outcome, not a bug.

---

## 2. Target users

| User | Need |
|---|---|
| **Primary: Harsh (project owner)** | Wants a disciplined, testable way to develop NSE trading strategies and eventually trade manually from validated signals. |
| **Secondary: any individual retail NSE trader** | Same need — a framework that forces rigor (costs, no look-ahead, validation) instead of an untested discretionary system. |

This is explicitly a **single-user, personal research tool** — not a product offered to other traders, which would trigger SEBI's Research Analyst / algo-provider registration requirements.

---

## 3. Dataset requirements

### 3.1 What's needed
- **Instruments:** Nifty 50 (index/futures), Bank Nifty, top-50 liquid NSE stocks.
- **Timeframes:** Daily (bias) + 1-hour (entry) for swing; 1-hour (bias) + 15-min (setup) + 5-min (trigger) for intraday.
- **History depth:** Multiple years, spanning different market regimes (trend/range, high/low volatility) — single-year or single-regime data will fail the validation suite's segmentation checks.
- **Required fields:** OHLCV, adjusted for splits/dividends/bonuses (with raw prices retained for accurate P&L), with a documented corporate-actions handling choice.
- **Reference data:** NSE trading calendar/holidays, lot sizes (F&O), tick sizes, circuit-limit flags.
- **News/events:** Corporate announcements (results dates, block deals, pledges, rating changes), economic calendar (RBI policy, Union Budget, major US data days) — used only for the deterministic risk/blackout filter, never for trade direction.
- **Point-in-time stock universe — unresolved gap, not a solved TODO:** no free, structured API for historical Nifty/Bank Nifty/top-50 membership changes was found. NSE Indices (niftyindices.com) publishes periodic reconstitution announcements, but compiling point-in-time membership from them is manual work. Realistic paths: (a) manually compile from NSE Indices' reconstitution press releases, (b) pay a data vendor that carries point-in-time constituent history, or (c) explicitly accept survivorship bias as a documented limitation for the first version and revisit later. Pick one before Phase 0 — don't let the loader silently default to today's constituent list.
- **Tradability filters — partially solved:** NSE publishes a daily downloadable CSV of securities entering the F&O ban period for the next trading day (official, free) — directly usable for the stock-F&O ban filter. This covers stock F&O only, not index F&O or the cash segment, so it is one input to the tradability filter, not the whole of it; circuit-limit/price-band data still needs to come from the daily bhavcopy or broker feed.
- **Tradable index instrument:** decide and document whether index strategies trade the futures contract (with an explicit rollover rule) or an ETF proxy — these behave differently and the choice affects every index-strategy backtest.
- **Bid/ask or quote data (if available):** use it directly for spread/slippage estimation where the data source provides it; where it isn't available, fall back to the Corwin-Schultz high-low spread estimator (see `Quant_Math_Spec.md` §9) rather than assuming a flat spread.

### 3.2 Possible dataset & API sources (to evaluate — none pre-selected)

**Price/OHLCV data:**
| Source | Type | Notes |
|---|---|---|
| [NSE Bhavcopy / historical reports](https://www.nseindia.com/all-reports) | Free, official | Daily end-of-day files; no intraday |
| [yfinance](https://github.com/ranaroussi/yfinance) (ticker suffix `.NS`) | Free, unofficial wrapper around Yahoo Finance | Good for backtesting/research; not licensed for production live use; can break without warning |
| [nsepython](https://github.com/aeron7/nsepython) / [jugaad-data](https://github.com/jugaad-py/jugaad-data) | Free, community-maintained NSE scrapers | Useful for bhavcopy/indices; verify reliability before depending on it |
| [Zerodha Kite Connect — Historical API](https://kite.trade/docs/connect/v3/historical/) | Paid subscription (~₹2000/month) | Official broker API, intraday candles, most production-realistic |
| [Upstox Developer API](https://upstox.com/developer/api-documentation/) | Free tier available | Historical + live data for Upstox account holders |
| [Angel One SmartAPI](https://smartapi.angelbroking.com/) | Free for account holders | Historical + live data |
| [Fyers API](https://myapi.fyers.in/docsv3) | Free for account holders | Historical + live data, well documented |
| [EOD Historical Data](https://eodhd.com/) | Paid | Broad NSE coverage, API-based |
| Kaggle NSE historical datasets | Free, static | Useful for quick prototyping only — verify recency and licensing before any production use |

**News / announcements / events:**
| Source | Type | Notes |
|---|---|---|
| [NSE Corporate Announcements](https://www.nseindia.com/companies-listing/corporate-filings-announcements) | Free, official | Results dates, block deals, regulatory actions |
| [BSE Corporate Announcements](https://www.bseindia.com/corporates/ann.html) | Free, official | Cross-check vs NSE |
| [Finnhub](https://finnhub.io/) | Free developer tier | General news/sentiment API; limited India-specific depth |
| RSS feeds (Economic Times Markets, Moneycontrol, LiveMint) | Free | No structured sentiment; headline tagging only |
| [RBI Press Releases](https://www.rbi.org.in/) | Free, official | Monetary policy dates |
| Trading Economics / Investing.com economic calendar | Free tier available | Macro event dates (Budget, US data days) |

**Revised recommendation (see §3.2.1 for verified depth comparison):** Upstox and Fyers are free, but verified community reports show Upstox's free intraday depth is far too shallow for this project's multi-year validation requirement, and Fyers' total depth is unconfirmed. **Zerodha Kite's paid Historical API is the most reliable verified option for the multi-year intraday depth S8/S9 need**, despite the subscription cost — cost savings don't help if the data can't support the validation the strategies require. Daily-bar-only strategies (S1–S3, S5–S7, S10) are far less sensitive to this and can reasonably use any of the free sources.

**Confirmed constraint:** broker historical-data APIs return data in capped chunks per request, not full multi-year history in one call (e.g., 60 days per request for 1-minute candles, 100 days for 5-minute, 200 days for 15-minute, 2000 days for daily). The data loader must **loop over date-range chunks** to assemble multi-year history — see `Architecture.md` §4. This is a real constraint, not a hypothetical one; building the loader without it will silently produce only a few months of intraday data instead of the multi-year depth the validation suite requires.

**Action item before Phase 0:** pick one price-data source and one news source, and record the choice (with its licensing terms) in `config/default.yaml`. Do not mix multiple free scrapers in production without checking each one's terms of use.

### 3.2.1 Intraday history depth — verified findings (2026-10-09)

| Source | Verified intraday depth | Fit for S8/S9 multi-year validation |
|---|---|---|
| yfinance | 1-min ≈ 7 days; 5m/15m/30m ≈ 60 days; 60m/1h ≈ 2 years — hard Yahoo-side limits, not fixable by chunking | **No** |
| Zerodha Kite Historical API (paid add-on) | Up to ~3 years of 1-min/3-min data for many instruments, via chunked requests (60d/90d/180d/365d/2000d caps per interval) | **Yes, best verified option** — but re-verify current subscription pricing, and that "for some instruments" doesn't exclude your chosen universe |
| Upstox (free tier) | Multiple current user reports put minute-level history at ~6 days to ~1 month without a paid "Plus" tier — access appears to have tightened over time | **No**, as currently offered free |
| Fyers | Clear per-request chunk caps (100 days intraday, 366 days daily) that can be looped — but total underlying depth unconfirmed | **Unverified** — check directly with a live account before relying on it |
| Angel One | Not yet checked | **Unverified** |

**Correction to the earlier recommendation:** Kite's paid Historical API — despite the subscription cost — is currently the most reliable verified path to the multi-year intraday depth S8 and S9 need. Upstox's free tier, recommended earlier on cost grounds, does not appear to support this depth at all. The realistic options before Phase 0 are: (a) pay for Kite's Historical API, (b) pay for a dedicated data vendor (TrueData, Global Datafeeds, EOD Historical Data), or (c) scope S8/S9 down to validate on daily/hourly bars only, accepting that their intraday-specific claims won't be tested at full depth. Decide which of these before Phase 0 — don't build the loader against an assumed source that turns out not to hold enough history.

### 3.3 Regulatory feasibility note (verified)
SEBI's retail algorithmic-trading framework (effective April 1, 2026 — static IP whitelisting, mandatory daily 2FA, Algo-ID tagging, 10 orders/sec rate cap) governs **automated order placement via broker API**. Because this project never places an order automatically at any stage — Research and Paper run entirely locally, and Stage 3 only ever produces a signal for a human to act on — none of that framework's order-placement obligations apply here. Reading market data via a broker's API for research/signals is a materially different, far lighter-touch activity than algorithmic order submission, and sits outside this framework's scope.

---

## 4. Features

### 4.1 Research stage
- Indicator library (SMA, EMA, RSI, ATR, ADX, VWAP, Bollinger, efficiency ratio) — exact formulas, no invented variants.
- Market structure engine (swings, BOS, CHoCH/MSS, liquidity sweeps, premium/discount) with strict look-ahead-safe pivot confirmation.
- Candlestick pattern library (confirmation tools only, never standalone signals).
- 10 codified strategies: EMA Trend Pullback, EMA Crossover, SMA Trend Filter, RSI (3 sub-strategies), Fibonacci/OTE, Order Block, Fair Value Gap, ICT liquidity-sweep model, Opening Range Breakout, Chart Patterns.
- Indian cost & slippage model (brokerage, STT, exchange fees, SEBI fee, stamp duty, GST) — all rates in config, never hardcoded or guessed.
- Event-driven backtest engine with pessimistic fills (stop-before-target same-bar assumption, gap-through-stop fills at open).
- Validation suite: walk-forward, parameter sensitivity, random-entry benchmark, buy-and-hold benchmark, ablation testing, Monte Carlo/bootstrap, regime/segment breakdown, cost stress testing.

### 4.2 Paper-trading stage
- Same engine/strategy code, fed by live or replayed data, simulated broker only.
- Rules frozen and hashed per run; any rule change starts a new paper-trading run.
- Data-health checks (stale feed, missing/duplicate bars, bad ticks) — halt new entries and alert, never trade on bad data.
- Full trade journal (signal, fill, costs, slippage, regime, news flags, reasons).

### 4.3 Manual signal stage
- Complete trade-plan objects (never a bare "buy/sell"): entry zone, stop, targets, size, rationale, invalidation, expiry.
- Deterministic news risk-flags (results dates, block deals, RBI policy days → skip or half-size — rule-based, not LLM-decided).
- Streamlit dashboard: live signals, open paper trades, equity/drawdown, regime state, news flags, data-health status, journal.
- Manual execution log comparing system signals vs. what the user actually did, with weekly discipline reporting.

### 4.4 Cross-cutting
- Position sizing & risk limits (per-trade risk %, max open trades, max correlated exposure, daily/weekly loss limits, drawdown kill-switch).
- Config-driven (YAML + pydantic), reproducible (fixed seeds), fully tested (pytest), git-committed per phase.

---

## 5. Non-functional requirements
- **No look-ahead bias anywhere** — closed-candle-only signals, next-bar-open entries, confirmed-pivot-only swing usage.
- **No fabricated data or numbers** — real data only (synthetic data permitted inside unit tests only); uncertain costs/rates flagged as TODO, never guessed.
- **Reproducibility** — same data + config + seed = identical output.
- **Auditability** — every trade logs its full context; an AI-run audit checklist is applied after every build phase.
- **Config over code** — no hardcoded parameters or secrets; API keys via environment variables only.

## 6. Success criteria (go/no-go sheet)

**This table is a floor for sanity, not proof of an edge.** Power analysis (`Quant_Math_Spec.md` §5.2) shows that even 100 trades can only detect an expectancy above roughly 0.34R — a real but smaller edge would be statistically invisible at that sample size. The full statistical bar below supersedes a plain trade-count check.

| Stage | Criterion | Required |
|---|---|---|
| Research | Out-of-sample trades | 100 (hard floor) — **250+ target** for a KEEP verdict; below that, verdict is NEEDS MORE DATA unless the robust lower CI bound is > 0 |
| Research | Expectancy after real costs | Positive; decision uses the **lower bound of the robust (bootstrap/Newey-West) confidence interval**, not the point estimate |
| Research | Profit factor after costs | ~1.3–1.6 (above 2.5 → assume a bug) |
| Research | Beats random-entry test (500+ runs) | p < 0.05 **after Holm/BH correction** across every strategy tested |
| Research | Multiple-testing correction | **Deflated Sharpe Ratio (DSR) ≥ 0.95**, counting every parameter/filter variant tried via the experiment ledger |
| Research | Overfitting check | **Probability of Backtest Overfitting (PBO) < 0.20** (CSCV method) |
| Research | Parameter robustness | Broad plateau — 70%+ of neighbouring grid points stay profitable and within 50% of the chosen setting's expectancy |
| Research | Cross-instrument/year/regime | 3+ instruments, several years, multiple regimes |
| Research | Cost stress (x1.5, x2, +1 tick) | Still positive |
| Research | Validation-pipeline canaries | All of: truncation/leak test, null-data test, planted-edge test, accounting identity, determinism — must pass before any verdict is trusted |
| Paper | Duration & trades, rules frozen | 2+ months, 100+ trades |
| Manual | Live vs. system signal tracking | Within tolerance, 90%+ signals followed; implementation shortfall tracked every trade |
| Always | Stop-the-system rule | Pause at 10–15% drawdown, manual review before resuming |
| Always | Live-drift monitoring | CUSUM alarm on live R vs. validated baseline triggers a mandatory review, never an automatic rule change |

# Rules.md

**Educational material only. Nothing here is investment advice or a promise of profit.**

This file is the project's guardrail document. Any coding AI (Claude Code, Cursor, Antigravity, etc.) working on this repo should read this before writing code, and it should be re-pasted if a session appears to have forgotten these rules.

---

## 1. Libraries — use

| Purpose | Use |
|---|---|
| Data handling | pandas, numpy |
| Config & validation | pydantic, pyyaml |
| Testing | pytest |
| Dashboard / charts | streamlit, plotly |
| Candlestick patterns (optional) | TA-Lib |
| Date/timezone handling | python-dateutil, pytz / zoneinfo (Asia/Kolkata) |
| Statistical inference | scipy, statsmodels |
| Overfitting/robustness diagnostics | arch (SPA, StepM, VarianceRatio, ADF) |
| Property-based testing | hypothesis |
| Experiment ledger / state persistence | sqlite3 (stdlib) |
| Version control | git (commit after every phase) |

## 2. Libraries / tools — do not use

| Avoid | Why |
|---|---|
| Apache Kafka, Apache Flink | Built for millisecond-latency streaming; this project's decision cycle is 5m-to-daily bars. Adds RAM load, JVM overhead, and operational failure points for no benefit here. |
| Redis (as a live feature store) | Not needed at this scale — a handful of instruments on local CSV/Parquet is sufficient. |
| Django | Heavier than this project needs; Streamlit covers the dashboard requirement with far less code. |
| LangGraph or any LLM multi-agent orchestration framework | Superseded — see §3. |
| Any neural network / ML model for entry or exit signal generation | Not allowed as a default. May only be introduced later as an explicit, separately-validated experiment that must beat the deterministic rule-based benchmark out-of-sample — never as the primary decision mechanism. |

## 3. The core rule: no black-box trade decisions

Every strategy must be a **deterministic, hand-specified rule set** with:
- An explicit entry rule, stop-loss rule, and exit rule.
- A falsifiable hypothesis written in the module's docstring (why it should make money, and what would prove it wrong).
- No LLM, and no trained model, in the decision path for direction (buy/sell/hold).

**An LLM may only be used to summarize or tag news headlines** for the deterministic risk-blackout filter (e.g., flagging "results announcement today" → the fixed rule, not the LLM, decides to skip or halve size). This boundary exists primarily because it keeps every result reproducible and auditable — a non-deterministic decision-maker can't be backtested, validated, or debugged the way this entire project depends on. A secondary reason sometimes cited is India's 2026 algo-trading framework and its "Black Box" algo classification; however, **this project places no automated orders at any stage, so that framework's registration requirements do not apply to it regardless of how the strategies are built.** Treat the regulatory point as context, not as the load-bearing justification for this rule — the reproducibility argument alone is sufficient, and any specific regulatory claim should be verified directly with SEBI or your broker before being relied on.

## 4. Absolute don'ts (violation = reject the output and fix before continuing)

- **Look-ahead bias:** signals use CLOSED candles only. Entry is on the NEXT bar's open, never the same bar.
- Using a swing high/low before it is confirmed (a pivot needs *n* bars on the right; usable only from index *i+n* onward).
- Using an unfinished higher-timeframe candle in a lower-timeframe calculation.
- **Repainting:** a zone or signal created at bar *t* must never change using data from after *t*.
- Optimizing parameters on the final test set, or changing rules after seeing test results.
- Martingale, averaging down, widening a stop after entry, increasing size after a loss.
- Fills at impossible prices (e.g., a stop filled at the exact stop level after a gap; a limit order filled when price only touched the level without trading through it).
- Ignoring costs, slippage, survivorship bias, or corporate actions.
- Hardcoding secrets — API keys via environment variables only, never in source.
- **Silent failures:** bad data, a stale feed, or a NaN indicator value must raise an error or be logged — never be silently ignored or turned into a zero.
- Fabricating or inventing "realistic-looking" market data to demonstrate results. Synthetic data is permitted only inside unit tests, never in a reported backtest.
- Claiming or implying profitability anywhere in generated text. "No edge found" is a complete, acceptable, and expected answer for most of the 10 strategies — report it plainly.

## 5. Statistical rigor rules (see `Quant_Math_Spec.md` for the full formulas)

- **Pre-register before testing:** write down the hypothesis, the parameters, and the metrics that will decide KEEP/REJECT *before* running a strategy's validation — not after seeing results and picking the metric that looks best.
- **Every trial counts:** every parameter combination, every filter toggle, every strategy variant ever run against real data gets logged in the experiment ledger (SQLite). The Deflated Sharpe Ratio and PBO calculations depend on an honest count of how many things were tried — undercounting trials silently turns noise into an apparent edge.
- **Report effect sizes with confidence intervals**, never a bare point estimate. A KEEP verdict uses the *lower bound* of the robust (bootstrap/Newey-West) confidence interval, not the mean.
- **No KEEP verdict without passing all of:** DSR ≥ 0.95, PBO < 0.20, random-entry p < 0.05 after Holm/BH correction, and the full canary suite (`Quant_Math_Spec.md` §10).
- **The final test set is sealed**, not just "don't touch it" by convention — stored separately, loadable only with an explicit `allow_final_test=true` flag, with every use recorded in the ledger.

## 6. Error handling standards

- Config values that are missing or null (especially cost/tax rates) must raise an error, not silently default to zero or an invented number.
- Data-health failures (stale feed, duplicate bars, missing bars, circuit-locked instrument) must block new entries and emit a visible alert — never trade through them unnoticed.
- Every exception must be logged with enough context to reproduce it; no bare `except: pass`.
- All randomness (Monte Carlo, parameter search) uses a fixed, recorded seed so results are reproducible.

## 7. Boundaries for the AI coding assistant

- **Work phase by phase** (see `Phases.md`). Each phase ends with passing tests and a summary of what was built, assumptions made, known limitations, and open questions — then **stop and wait** for explicit go-ahead. Do not proceed to the next phase unprompted.
- **If something is ambiguous, ask.** Do not guess silently — especially for tax/cost rates, broker behavior, or anything regulatory.
- **Never fabricate** numbers, tax/charge rates, API behavior, or backtest results. Anything uncertain goes into config with a `TODO` comment and an explicit note to verify it against an official source.
- **All parameters live in YAML config**, never hardcoded in strategy logic.
- After every phase, run the **audit prompt** (see the Blueprint's Block 24) and fix every flagged issue with a failing test first, then a fix.
- If a backtest result looks unusually good (profit factor above ~2.5, win rate above ~70%), **assume a bug before celebrating** and re-run the audit.
- Keep a git commit after every completed phase so any step can be rolled back cleanly.
- Different AI tools have different context limits — if a session appears to have forgotten these rules, re-paste this file and the Master Context block before continuing.

# Phases.md

**Educational material only. Nothing here is investment advice or a promise of profit.**

## Stage overview

| Stage | What happens | Passes when |
|---|---|---|
| 1. Research | Build and validate strategies on historical data (train / validation / untouched final test) | Positive expectancy after costs, beats random entries, holds out of sample |
| 2. Paper | Software trades automatically in a simulator on live data, rules frozen | 100+ trades, 2+ months, meets the go/no-go sheet |
| 3. Manual | Software only gives signals (entry zone, stop, targets, size); orders placed by hand | Live results track paper results; rules followed |

Strategies are added **one at a time**, starting with S1 (EMA Trend Pullback). Never combine untested strategies into a portfolio before each has its own KEEP/REJECT verdict.

---

## Phase 0 — Scaffold & data
Create the full repo structure (`data/`, `indicators/`, `structure/`, `patterns/`, `strategies/`, `risk/`, `costs/`, `engine/`, `validation/`, `stats/`, `execution/`, `monitoring/`, `experiments/`, `regime/`, `paper/`, `signals/`, `dashboard/`, `config/`, `tests/`, `reports/`, `docs/`). Implement config loading (pydantic), logging, and a data loader/validator: IST timezone, NSE trading calendar, duplicate/missing bar detection, bad-tick checks, OHLC sanity (`L<=O,C<=H`), and look-ahead-safe resampling to higher timeframes. Also scaffold the **canary harness** (`Quant_Math_Spec.md` §10): the truncation/leak test runner, a null-data generator (GBM + block-shuffled real returns), and the SQLite experiment-ledger table — these run empty for now but must exist before any strategy code is trusted. Set up pytest. **Do not write any strategy logic yet.** Stop and summarize.

## Phase 1 — Indicators & structure
Implement the indicators module (SMA, EMA, RSI, ATR, ADX, VWAP, Bollinger, efficiency ratio) and the structure module (swings, BOS, CHoCH/MSS, liquidity, premium/discount) exactly per spec, including no-look-ahead tests and pivot-confirmation tests. Add a visual chart script (swings/BOS/CHoCH/sweeps/equal highs-lows/premium-discount overlay) for manual inspection. Stop and summarize.

## Phase 2 — Engine, costs, risk
Implement the event-driven backtest engine (strict bar-by-bar order of operations, pessimistic fills), the Indian cost/slippage model (rates from config, `null` → error, never guessed), and the risk/position-sizing module (per-trade risk %, open-risk limits, daily/weekly loss caps, drawdown kill-switch). Also implement the **order-plan execution module** (`Quant_Math_Spec.md` §3.1–3.4): position sizing net of slippage and costs, the maximum-chase-price (`e_max`/`e_min`) calculation, the limit-vs-market fill-probability comparison, and the cost-viability gate (§2, skip any signal whose estimated cost exceeds `max_cost_r`). Include all specified tests. Stop and summarize.

## Phase 2b — Statistics library
Implement the `stats/` module exactly per `Quant_Math_Spec.md` §5 (confidence intervals, stationary bootstrap, power analysis, Sharpe/PSR/DSR, Holm/BH correction, PBO via CSCV), §6 (Kelly fraction with lower-confidence-bound shrinkage, drawdown probability, correlated open risk, tail risk/ES/Ulcer index), and §9 (Corwin-Schultz spread estimator, square-root market-impact model). Unit-test every function against hand-worked examples and, where one exists, a reference implementation (e.g., `arch` for variance ratio/ADF). Stop and summarize.

## Phase 3 — First strategy (S1: EMA Trend Pullback)
Before writing any code, write the **pre-registration note** (`Rules.md` §5): the hypothesis, the exact parameters, the metrics that will decide KEEP/REJECT, and how many variants will be tried. Then implement S1 exactly as specified, with a unit test per condition. Run it on the **train period only** and report metrics. Do not tune anything yet. Stop and summarize.

## Phase 4 — Validation suite
Implement the full validation suite: walk-forward analysis, parameter sensitivity (heatmaps, plateau check), benchmarks (buy-and-hold, 200-day trend, random-entry test with 500+ runs), ablation testing, Monte Carlo/bootstrap, segmentation (year/instrument/regime/session/direction), cost stress testing, and the automatic warning checks. Layer in the full statistical bar from `Quant_Math_Spec.md` §5.1–§5.8 (robust confidence intervals, power analysis, DSR, Holm/BH-corrected p-values, PBO via CSCV, embargoed/sealed data splits) and the §10 **mandatory canaries** (truncation/leak test, null-data test, planted-edge test, accounting identity, property-based tests, determinism, reference checks) as hard pass/fail gates — a strategy cannot receive a verdict until every canary passes. Run it on S1 using **train + validation only** — the final test set stays untouched. Stop and summarize.

## Phase 5 — Remaining strategies, one at a time
Before each strategy's filters are built, run the **§7 edge-hypothesis tests first**: the placebo-controlled event study (§7.1) for S5, S6, S7, S8, and S10 — testing whether the zone/level concept itself beats a randomly-placed zone of the same size — plus the Fibonacci clustering test (§7.2) for S5 and the variance-ratio/half-life tests (§7.3) for S1, S2, and S4b. A zone concept that doesn't beat its placebo gets dropped before any entry/exit logic is built around it.

For each of S2 (EMA Crossover), S3 (SMA Filter), S4 (RSI — 3 sub-strategies), S5 (Fibonacci/OTE), S6 (Order Block), S7 (Fair Value Gap), S8 (ICT Model), S9 (Opening Range Breakout), S10 (Chart Patterns): implement exactly per spec with tests, then run the full validation suite. Report **KEEP / REJECT / NEEDS MORE DATA** with reasons for each. Never merge a strategy into the portfolio before its own verdict. Stop after each strategy.

## Phase 6 — Regime classifier & strategy selector
Implement the rule-based regime classifier (ADX, efficiency ratio, ATR percentile, EMA slope — with hysteresis) and the strategy-permission table. Run the four-way comparison: always-on vs. permitted-regime-only vs. full selector vs. equal-weight parallel strategies. Keep the selector only if it beats the simpler options out-of-sample after costs. Stop and summarize.

## Phase 7 — Final test & paper trading
Run the **untouched final test set once** on the frozen configuration and report results. If it passes the go/no-go sheet, implement the paper-trading engine and run it on live/replayed data with rules frozen. Implement the **live-drift monitor** (`Quant_Math_Spec.md` §11: one-sided CUSUM on net R vs. the validated baseline) now, before Stage 3 signals go live — an alarm must trigger a mandatory review, never an automatic rule change. Stop and summarize.

## Phase 8 — Signals, dashboard, journal, news flags
Implement the signal object (full trade plan, never a bare buy/sell) including the order-plan fields from §3 (`e_max`/`e_min`, net RR after costs, estimated fill probability), alerts, the Streamlit dashboard, the manual-execution log with **implementation-shortfall logging** (§3.5: timestamp alert, order placement, and fill; report mean/median IS by strategy and time of day), the weekly discipline report, and the deterministic news risk-flags. Confirm in the README that the project places **no real orders**. Stop and summarize.

## Phase 9 — Documentation & review
Write the README (setup, how to run each stage, limitations), keep `docs/spec/` current (this file set), maintain a research log of every experiment run, and produce a final honest report of which strategies were kept, which were rejected, and why.

---

## After every phase
Run the **audit prompt** (Blueprint Block 24) before trusting any reported number: check for look-ahead bias, unconfirmed pivot usage, unfinished higher-timeframe candles, same-bar entries, impossible fills, cost/slippage omissions, warm-up handling, repainting, sizing/limit enforcement, hardcoded parameters, train/test leakage, survivorship bias, and swallowed exceptions. Fix every `FAIL` with a failing test first, then the fix.

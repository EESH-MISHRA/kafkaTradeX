# Quant_Math_Spec.md

**Educational material only. Nothing here is investment advice or a promise of profit.**

Add this file to `docs/spec/` next to PRD.md, Architecture.md, Rules.md, Phases.md and Design.md.
It supplies the mathematical definitions that the other documents name but do not define
(Monte Carlo, Sharpe, benchmarks, sizing, slippage). Any coding AI must implement these exactly
and must not invent its own variants (see Rules.md section 3).

Conventions: all formulas are ASCII. `Phi` = standard normal CDF, `Phi_inv` = its inverse.
`ln` = natural log. `side` = +1 for long, -1 for short. `R` = risk unit (see section 2).
Anything marked HEURISTIC is a rule of thumb, not a theorem: keep it in config and report it.

---

## 0. What the current documents already have and what they lack

Already defined: EMA/RSI/ATR/ADX formulas, Fibonacci levels, position-size formula, R-multiples,
expectancy formula (in prose), BOS/CHoCH rules.

Named but NOT defined (an AI would have to guess): confidence intervals, Monte Carlo/bootstrap
method, Sharpe/Sortino/Calmar details, multiple-testing correction, parameter-plateau test,
walk-forward efficiency, slippage model, correlated-risk aggregation, regime thresholds,
drift detection, order-plan accuracy (size net of slippage, maximum chase price, fill probability).

---

## 1. Notation

```
P_e   planned entry price           P_s   stop price           T1,T2  targets
F_e   actual entry fill             F_x   actual exit fill
D     = |P_e - P_s|                 risk per share (price units)
Eq    account equity (mark-to-market at last close)
r     risk fraction per trade (config risk_pct / 100)
n     number of closed trades      x_i   net R of trade i
sigma_bar   per-bar std of price changes (price units)   sigma_d  daily std (price units)
```

---

## 2. Trade-level mathematics

```
R_i (single exit)  = ( side*(F_x - F_e) - c_ps ) / D_i
R_i (partial exits)= sum_k f_k * R_ik            with sum_k f_k = 1
c_ps               = round-trip charges per share (brokerage, STT, exchange, SEBI, GST, stamp)
                     + slippage per share (entry + exit)
c_R                = total_cost_of_trade / risk_amount           (cost in R units)
```

Expectancy and payoff (all in R, after costs):
```
E_net        = mean(x_i)
W_bar, L_bar = average winning R, average losing R (both positive numbers)
p            = fraction of winners
E_net (decomposed) = p*W_bar - (1-p)*L_bar        (costs already inside each x_i)
Profit factor      PF = sum(winning R) / sum(|losing R|)
Break-even win rate (gross payoff, costs separate): p* = (L_bar + c_R) / (W_bar + L_bar)
Payoff ratio b = W_bar / L_bar ;  gross break-even p = 1/(1+b)
```

Cost-viability gate (config `max_cost_r`, default 0.15): skip any signal where the estimated
`c_R` exceeds it. Costs that eat more than about 15 percent of one R make most edges unprofitable.

---

## 3. Order-plan accuracy (what the manual signal must compute)

The software never sends orders; "accurate order placement" means the TRADE PLAN shown to the
human is computed so that realised risk, reward and fill assumptions are honest.

### 3.1 Position size net of slippage and costs (replaces the simple formula)
```
D_eff   = max( D + s_in + s_out + c_ps ,  P_e * g_99 )          # g_99 term only if gap_aware_sizing=true
qty     = floor( (Eq * r) / D_eff )                              # cash equity
lots    = floor( (Eq * r) / ( lot_size * D_eff_per_unit ) )      # futures/options, never round UP
s_in    expected entry slippage per share      s_out  expected stop-exit slippage per share
g_99    99th percentile of ADVERSE overnight gap, as a fraction of price, from the instrument's own
        history (train period only): g_t = ln(O_t / C_{t-1}); adverse = negative for longs
```
- If qty == 0 or lots == 0: SKIP and log "risk budget below one unit". Never round up.
- Display realised risk after rounding: `realised_risk = qty * D_eff` and `% of Eq`.
- Intraday-only positions set gap_aware_sizing=false.

### 3.2 Maximum chase price (do not enter beyond this)
Net reward-to-risk must stay at or above RR_min (default 1.5) at the price you actually get.
```
LONG :  reward = T1 - e - c_ps ;  risk = e - P_s + s_out ;  need reward >= RR_min * risk
        e_max = ( T1 - c_ps + RR_min*(P_s - s_out) ) / ( 1 + RR_min )
SHORT:  reward = e - T1 - c_ps ;  risk = P_s - e + s_out
        e_min = ( T1 + c_ps + RR_min*(P_s + s_out) ) / ( 1 + RR_min )
```
Every alert must print e_max (long) or e_min (short). If the market has moved beyond it,
the signal is SKIPPED, never chased. Round to tick size (long: round down; short: round up).

### 3.3 Limit order versus market-style entry: fill probability
Under a zero-drift random walk, the probability that price touches a level at distance d against
the current price within n bars is:
```
P_touch(d, n) = 2 * ( 1 - Phi( d / (sigma_bar * sqrt(n)) ) )
```
A limit order placed d better than the market fills with probability about P_touch (an UPPER
bound for "trade-through" fills; the touch-only fill is less reliable in practice). The improvement
in R is d / D. But filled limits are adversely selected (price often keeps going through).
Therefore:
```
EV_limit  = P_fill * E[R | filled]            (unfilled trades contribute 0)
EV_market = E[R at next-bar-open fill]
```
DO NOT assume which is better. The backtest must run BOTH entry rules on the identical signal set
(limit fills only on trade-through) and report EV_limit vs EV_market with confidence intervals.
Config `entry_mode` is chosen from that comparison on the train set only.

### 3.4 Manual-latency allowance (optional stress)
A human acting tau minutes after the alert faces a random price move of std `sigma_bar_min * sqrt(tau)`.
Add `k_lat * sigma_min * sqrt(tau)` (default k_lat=1, tau=2) to s_in in the stress run. If the strategy
dies under this stress, it is too latency-sensitive for manual execution.

### 3.5 Implementation shortfall (measure it, every trade)
```
IS_bps = side * (F_e - P_decision) / P_decision * 10000        # P_decision = price when alert fired
delay_cost = side*(P_at_order_time - P_decision)/P_decision*1e4
exec_cost  = side*(F_e - P_at_order_time)/P_at_order_time*1e4
```
Log timestamps for alert, order placed, fill. The weekly report shows mean/median IS by strategy
and time of day, and compares it with the slippage assumption in costs.yaml. If real IS exceeds
the model by more than 50 percent, update the model and re-run validation.

### 3.6 Order-type notes (verify with your broker, rules change)
- Use limit orders for entries unless the backtest shows market-style wins (section 3.3).
- A stop-loss should be placed immediately after the entry fill. Compare stop-market (slippage risk)
  and stop-limit (risk of no fill in a fast move) for your broker and segment; do not assume.
- Re-check tick size, price bands/circuit limits and order-type rules in the exchange/broker docs.

---

## 4. Volatility and stop placement

### 4.1 Volatility estimators (use these, not "ATR times a constant")
```
log return            r_t = ln(C_t / C_{t-1})
EWMA (RiskMetrics)    sigma2_t = lambda*sigma2_{t-1} + (1-lambda)*r_{t-1}^2      lambda = 0.94 (daily)
Parkinson             sigma2_P = ( 1/(4*ln 2) ) * mean( ln(H/L)^2 )
Garman-Klass          sigma2_GK = mean( 0.5*ln(H/L)^2 - (2*ln 2 - 1)*ln(C/O)^2 )
Yang-Zhang (n bars)   sigma2_YZ = sigma2_o + k*sigma2_c + (1-k)*sigma2_RS
   sigma2_o = sample var of ln(O_t / C_{t-1})        sigma2_c = sample var of ln(C_t / O_t)
   sigma2_RS = mean( ln(H/C)*ln(H/O) + ln(L/C)*ln(L/O) )
   k = 0.34 / ( 1.34 + (n+1)/(n-1) )
```
Default: Yang-Zhang over 20 bars for daily data; Parkinson for intraday bars (no overnight term).
Convert to price units: `sigma_bar = sigma * price`. ATR stays as the stop-buffer unit, but
sigma-based quantities (section 3.3, 4.2) must use these estimators.

### 4.2 Noise-touch probability of a stop (diagnostic)
Over a holding horizon of n bars, with zero drift, the probability that pure noise touches a stop at
distance D is:
```
P_noise(D, n) = 2 * ( 1 - Phi( D / (sigma_bar * sqrt(n)) ) )
```
Report P_noise for each strategy's median stop and holding time. HEURISTIC: if P_noise > 0.6 the
stop sits inside the noise and will be hit by randomness; widen it (and shrink size) or drop the trade.

### 4.3 MAE / MFE calibration (train set only)
```
MAE_i = max adverse excursion before exit, in R   (positive number)
MFE_i = max favourable excursion before exit, in R
```
Procedure: for a grid of stop multiples k, recompute expectancy E(k) from the same entries; plot
E(k) and the distribution of MAE for WINNING trades. Pick k from a PLATEAU of E(k) (neighbouring
values within 20 percent) and near the 85-90th percentile of winners' MAE. Never pick the single
best k. Same method for the take-profit multiple using MFE. At most two exit parameters per strategy.

---

## 5. Statistical inference (the core of Phase 4)

### 5.1 Confidence interval and t-statistic for expectancy
```
x_bar = mean(x_i) ;  s = sample std(x_i) ;  SE = s / sqrt(n)
t = x_bar / SE ;  95% CI = x_bar +/- t_{0.975, n-1} * SE
```
Trade results can be serially dependent, so ALSO report a robust interval:
- Stationary bootstrap (Politis-Romano), mean block length b = ceil(n^(1/3)), 10,000 resamples,
  fixed seed; or Newey-West: `Var(x_bar) = (1/n)*[ g0 + 2*sum_{k=1..L} (1 - k/(L+1))*g_k ]`, `L = floor(4*(n/100)^(2/9))`,
  where g_k is the autocovariance of x at lag k.
Decision uses the LOWER bound of the robust interval, not the point estimate.

### 5.2 How many trades are enough? (power analysis)
```
n_required = ( (z_{1-alpha/2} + z_{1-beta}) * sigma_R / mu_R )^2
Minimum detectable expectancy with n trades: mu_min = (z_{1-alpha/2}+z_{1-beta}) * sigma_R / sqrt(n)
```
Worked example (alpha=0.05, power 80 percent, so the z-sum is about 2.8, and sigma_R about 1.2R):
- Detect mu_R = 0.2R  ->  n about 282 trades.
- With only n = 100 trades, mu_min about 0.34R: an edge smaller than that is statistically invisible.
Therefore the go/no-go "100 trades" is a FLOOR for sanity, not proof. Config: `min_trades=100` hard floor,
`target_trades=250` for a KEEP verdict, otherwise the verdict is NEEDS MORE DATA unless the lower CI bound is > 0.

### 5.3 Sharpe ratio and its uncertainty
```
SR_1     = mean(r_p) / std(r_p)                        # per-period (e.g., daily) returns
SR_ann   = SR_1 * sqrt(A)                              # A = 252 daily
Lo (2002) autocorrelation adjustment, horizon q periods:
SR_q     = SR_1 * q / sqrt( q + 2*sum_{k=1..q-1} (q-k)*rho_k )          # use instead of sqrt(q) when rho_k != 0
Probabilistic Sharpe Ratio (T observations, skew g3, kurtosis g4 NOT excess):
PSR(SR*) = Phi( (SR_hat - SR*) * sqrt(T-1) / sqrt( 1 - g3*SR_hat + ((g4 - 1)/4)*SR_hat^2 ) )
```
SR_hat and SR* are per-period (non-annualised) in PSR.

### 5.4 Deflated Sharpe Ratio (multiple-testing correction for trying many variants)
```
SR_star = sqrt( V ) * [ (1 - gamma_E)*Phi_inv(1 - 1/N) + gamma_E*Phi_inv(1 - 1/(N*e)) ]
DSR     = PSR( SR_star )
N = effective number of independent trials (from the experiment ledger, see 5.7)
V = variance of the Sharpe ratios across those trials ;  gamma_E = 0.5772 (Euler-Mascheroni) ;  e = 2.71828
```
Requirement: DSR >= 0.95 for a KEEP verdict. Every parameter combination, every strategy variant,
every filter toggle that was tried counts toward N (be honest and conservative).

### 5.5 Multiple hypothesis testing across strategies and filters
```
Holm: sort p(1)<=...<=p(m); reject p(k) while p(k) <= alpha/(m-k+1); stop at the first failure
BH (false discovery rate q): find the largest k with p(k) <= (k/m)*q ; reject 1..k
```
Random-entry p-value (Phase 4 benchmark): `p = (1 + #{random runs with statistic >= strategy}) / (1 + M)`, M >= 500
(so the smallest possible p is about 0.002). Apply Holm or BH across all strategies tested.

### 5.6 Backtest overfitting diagnostics
- PBO via CSCV (Bailey, Borwein, Lopez de Prado, Zhu): build a T x N matrix of per-period returns for N variants;
  split time into S=16 equal blocks; for each of the C(S, S/2) combinations use half the blocks as in-sample (IS) and the
  rest as out-of-sample (OOS); find the variant n* best in IS; let w = its relative OOS rank in (0,1);
  `lambda = ln( w/(1-w) )`; `PBO = fraction of combinations with lambda <= 0`. Require PBO < 0.20 (config).
- Reality Check / SPA: test H0 "best variant has no edge over the benchmark" with the stationary bootstrap
  (Python package `arch`: `arch.bootstrap.SPA` / `StepM`). Benchmarks: random entry and buy-and-hold.
- Walk-forward efficiency, HEURISTIC: `WFE = annualised OOS return / annualised IS return`; flag if WFE < 0.5.
- Parameter plateau, precise rule: for each tuned parameter, the strategy passes only if at least 70 percent of grid
  neighbours within +/-1 step keep expectancy > 0 AND within 50 percent of the chosen setting's expectancy.

### 5.7 Experiment ledger (needed for N in 5.4)
SQLite table `experiments(id, timestamp, git_hash, config_hash, strategy, params_json, data_window, n_trades, metrics_json, verdict)`.
Every backtest run inserts a row automatically. Counting trials is done from this table, not from memory.

### 5.8 Data-split hygiene
```
embargo_bars >= max( max_holding_bars, longest_indicator_lookback )
```
Insert an embargo of at least that many bars between train/validation and between validation/test, and drop
trades whose holding period crosses a boundary. Check that EACH split contains more than one volatility
regime (compare ATR percentile distributions); if not, change the split points (still by time, never random).
The final test set must be physically sealed: stored in a separate file that the research code path cannot load
unless the flag `allow_final_test=true` is passed, and the ledger records that single use.

---

## 6. Risk and portfolio mathematics

### 6.1 Growth-optimal fraction (Kelly) and why the cap is far lower
For per-trade results x_i with mean mu and variance sigma2, risking fraction f of equity per trade, approximate log growth:
```
g(f) = f*mu - 0.5 * f^2 * sigma2        ->  f_star = mu / sigma2
```
Example: mu=0.2R, sigma2=1.44 -> f_star about 0.139 (13.9 percent per trade). That number is fragile (it is the
point estimate of an uncertain edge), so use:
```
mu_LCB  = max(0, x_bar - 1.64*SE)                     # lower confidence bound
f_use   = min( risk_cap , 0.25 * mu_LCB / sigma2 )    # quarter-Kelly of the LOWER bound, never above the cap
```
If mu_LCB = 0 then f_use = 0: no confirmed edge means no risk allocation.

### 6.2 Probability of reaching a given drawdown (sanity formula)
Approximating log-equity as Brownian motion with per-trade drift m and variance v:
```
m = f*mu - 0.5*f^2*sigma2 ;  v = f^2 * sigma2 ;  L = -ln(1 - D)        # D = drawdown fraction, e.g. 0.12
P(ever reaching drawdown D) = exp( -2*m*L / v )          (valid for m > 0)
```
Worked examples (sigma2=1.44, D=12 percent): f=0.75 percent, mu=0.20R -> about 1 percent;
f=0.75 percent, mu=0.05R -> about 35 percent; f=2 percent, mu=0.20R -> about 19 percent.
This shows the decisive role of the TRUE edge (uncertain) versus bet size. It is an approximation
(i.i.d. trades, thin tails): the Monte Carlo of section 5.1 is the real test; this formula is a cross-check.

### 6.3 Correlated open risk
```
R_open = sqrt( r' * C * r )          r = vector of open risk (percent of Eq) per position
                                      C = correlation matrix of daily returns (rolling 120 days)
rho_ij = max( rho_ij , rho_floor )   for instruments in the same bucket (rho_floor = 0.6; Nifty, Bank Nifty, index futures = 0.9)
```
Enforce `R_open <= max_total_open_risk_pct` AND `sum(r) <= 1.5 * max_total_open_risk_pct` (the plain sum as a second cap).
Effective number of independent bets: `N_eff = N / (1 + (N-1)*rho_bar)`; report it.

### 6.4 Tail risk of the equity curve
Historical-simulation Expected Shortfall: `ES_alpha = mean of the worst (1-alpha) fraction of daily P&L` (alpha=0.95 and 0.99,
at least 250 days; for fewer days use the trade bootstrap). Report VaR_alpha and ES_alpha alongside max drawdown.
Also report Ulcer index `UI = sqrt( mean( DD_t^2 ) )` and `Calmar = CAGR / |MaxDD|`.

### 6.5 Drawdown kill-switch consistency
Config `drawdown_kill_pct` (12) must be below the go/no-go drawdown tolerance (15) so the kill-switch fires first.
Backtests must apply the same kill-switch and report how often and when it fires.

---

## 7. Testing whether the edge hypotheses are even true (before building filters on them)

### 7.1 Event study with placebo control (for S5, S6, S7, S8, S10)
For every signal event at bar t0 (zone touched and confirmation seen), measure signal-only forward moves:
```
F_h = side * ( C_{t0+h} - C_{t0} ) / ATR_{t0}      for h in {1, 3, 5, 10, 20} bars
```
Placebo set: same direction, same regime, same time of day, but with the "zone" placed at a random level of the same
width and the same distance from price. Test mean(F_h real) - mean(F_h placebo) with the stationary bootstrap.
If the real zone does not beat the placebo, the zone concept adds no information, and entries based on it are noise.
This isolates ENTRY edge from exit rules (stops/targets), which is essential for ICT-style concepts.

### 7.2 Fibonacci hypothesis test (S5)
For each completed impulse leg define the retracement depth `rho = (H - L_retrace) / (H - L)` where L_retrace is the
lowest low before price exceeds H again. Build the distribution of rho on the train set.
Null: the density near the Fibonacci ratios {0.382, 0.5, 0.618, 0.786} is no higher than a smooth fit of the density
elsewhere. Count legs with rho within +/-0.02 of each ratio, compare with the expected count from a kernel density estimated
EXCLUDING those bins, and test with a binomial or chi-square test (Holm-corrected across the four ratios).
If there is no excess clustering, Fibonacci levels have no special status: keep only "retracement zone" in ATR terms.

### 7.3 Trend versus mean-reversion character (S1, S2, S4b)
```
Variance ratio  VR(q) = Var( r_t(q) ) / ( q * Var( r_t(1) ) )        r_t(q) = sum of q consecutive log returns
VR > 1: positive autocorrelation (trending) ;  VR < 1: mean-reverting ;  VR = 1: random walk
```
Use the heteroskedasticity-robust Lo-MacKinlay z-statistic (`arch.unitroot.VarianceRatio`) for q in {2, 5, 10, 20}.
A trend-following strategy needs VR significantly > 1 at its holding horizon in that instrument and period;
a mean-reversion strategy needs VR < 1. Report per instrument and per year.
```
Ornstein-Uhlenbeck half-life (for S4b): x_t = ln(price_t) - ln(SMA20_t) ; fit x_t = phi*x_{t-1} + e
half_life = -ln(2) / ln(phi)      valid only for 0 < phi < 1 ; also run an ADF test (arch.unitroot.ADF)
Require half_life <= time_stop_bars of the strategy and ADF p < 0.05, otherwise do not trade mean reversion there.
```
Trend regression (S1/S2): `r_{t+1} = a + b * sign(trend_t) + e` with HAC (Newey-West) standard errors; b must be > 0 and significant.
Hurst exponent (DFA or R/S) may be reported descriptively only: it is unreliable on short samples.

---

## 8. Regime classification (data-driven thresholds)

Replace fixed cutoffs with rolling percentiles so thresholds adapt to each instrument:
```
trend_strength_t = percentile rank of ADX14_t within the last 500 bars
efficiency_t     = percentile rank of ER20_t within the last 500 bars
TREND  if both ranks >= 0.70 and sign(EMA50 slope) agrees with sign(close - EMA200)
RANGE  if both ranks <= 0.30
VOLATILE if ATR_pct > 0.90 ;  TRANSITION otherwise
```
Hysteresis: switch regime only after the new state persists for h bars (default 3).
Regime detection delay: measure bars between each retrospectively identified change point (rolling variance-ratio
sign change) and the bar where the classifier switched. Report the mean delay; if it is longer than the typical trade
duration, regime gating is useless for that strategy.
Report expectancy and its CI per regime (table); a strategy gated by a regime must show higher expectancy
in its permitted regime than outside it, out-of-sample.

---

## 9. Cost and slippage model (extra formulas)

```
s_side   = h + s_impact                     # per share, per side
h        = half bid-ask spread (from quotes if available)
           else Corwin-Schultz estimate from daily high/low:
           beta  = sum_{j=0..1} [ ln(H_{t+j}/L_{t+j}) ]^2
           gamma = [ ln( max(H_t,H_{t+1}) / min(L_t,L_{t+1}) ) ]^2
           alpha = ( sqrt(2*beta) - sqrt(beta) ) / ( 3 - 2*sqrt(2) ) - sqrt( gamma / (3 - 2*sqrt(2)) )
           spread_fraction = 2*( e^alpha - 1 ) / ( 1 + e^alpha )          (floor at 0; h = 0.5*spread_fraction*price)
s_impact = Y * sigma_d * sqrt( Q / V_d ) * price     # square-root law ; Q = order size, V_d = daily volume ; Y ~ order 1, calibrate from IS data
time-of-day multiplier m(t) >= 1 near the open and close: s_side(t) = m(t) * s_side
```
Liquidity gate: skip if `Q / V_d > 0.01` (config) or median spread is above a limit. For small retail orders
s_impact is usually negligible and h dominates; keep the term so the model still behaves when size grows.
Tradability filters (config): exclude instruments in a derivatives ban period, circuit-locked at signal time, or on
exchange surveillance lists that restrict trading (verify the current lists and rules at the exchange).

---

## 10. Mandatory self-tests of the validation pipeline ("canaries")

1. **Truncation (leak) test:** for 50 random bars t, run each strategy on data[:t+1] and on the full data; the signal at t
   must be identical. Any difference = look-ahead leak. Run on every strategy in CI.
2. **Null-data test:** run ALL strategies and the full validation on (a) geometric Brownian motion with matched volatility,
   (b) block-shuffled real returns. The fraction of KEEP verdicts must be at or below the nominal false-positive rate
   (about 5 percent before correction, near 0 after Holm/DSR). Otherwise the pipeline is biased. (Synthetic data is allowed
   here because this tests the machinery; never report it as a result.)
3. **Planted-edge test:** inject a known edge (for example, drift of +0.2 ATR in the 5 bars after signals) into synthetic data;
   the pipeline must detect it at the power predicted in section 5.2.
4. **Accounting identity:** `Eq_end = Eq_start + sum(pnl) - sum(costs)` to the paisa; metrics recomputed independently
   from trades.csv must match the report.
5. **Property-based tests (hypothesis):** position size never exceeds the risk budget; stops never loosen; qty is never
   rounded up; no trade is created on a NaN indicator; e_max/e_min respected.
6. **Determinism:** identical config + data + seed gives byte-identical outputs.
7. **Reference checks:** compare indicators to a trusted library where the definition is identical (note Wilder smoothing
   differences) and document any difference.

---

## 11. Live-drift monitoring (Stages 2 and 3)

One-sided CUSUM on net R per trade to detect a drop in the mean versus the validated expectancy mu0 (from the final-test/paper baseline):
```
S_t = max( 0 , S_{t-1} + ( mu0 - x_t ) - k )      k = delta/2 ;  delta = smallest shift worth detecting (default 0.25R)
ALARM if S_t > h ;  h chosen by simulation so the in-control average run length is at least 200 trades
```
Also monitor monthly: slippage ratio (real / model), fill rate of limit orders vs the model, win-rate z-test
`z = (p_hat - p0)/sqrt(p0*(1-p0)/n)`, and a two-sample Kolmogorov-Smirnov test of live R vs backtest R.
An ALARM does not auto-change anything: it triggers the stop-the-system review in the PRD.

---

## 12. Changes to the five existing documents

See PRD.md, Architecture.md, Rules.md, Phases.md and Design.md — each has been updated in place
per the instructions this section originally specified, rather than duplicated here.

---

## 13. Config additions (config/default.yaml)

See `config/default.yaml` — these sections have been merged into the full project config
alongside the original Block 22 template.

---

## 14. Honest limits of this maths

- All inference assumes the future resembles the sample. Markets change; monitoring (section 11) detects decay late, not early.
- Brownian approximations (3.3, 4.2, 6.2) ignore fat tails, volatility clustering and jumps. Use them as diagnostics; trust the
  empirical bootstrap and walk-forward results over them.
- Every statistic here can be gamed by trying many things and reporting the best. The ledger, the sealed final test and the
  null-data canary exist to stop that, including from yourself.
- Precision of the plan does not create profit. A perfectly sized, perfectly priced trade from a strategy with no edge still loses
  money after costs.

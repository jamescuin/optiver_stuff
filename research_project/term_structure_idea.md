Create a complete, self-contained Jupyter notebook implementing and backtesting an SPX/QQQ options term-structure relative-value strategy.

The notebook must integrate with the **existing backtesting framework already available in the environment**. Inspect and use its existing data-loading, option-selection, portfolio, execution, accounting, and performance-analysis interfaces rather than creating a separate backtesting engine. Where framework-specific calls are required, adapt to the existing API and clearly isolate those calls in a small integration layer.

## Objective

Test whether temporary dislocations in the SPX and QQQ implied-volatility term structure predict subsequent normalization.

The strategy should:

- operate on 5-minute observations;
- trade SPX and QQQ options only;
- use ATM straddles;
- model forward variance rather than raw implied-volatility spreads;
- estimate a dynamically changing fair value for forward variance;
- trade statistically significant deviations from fair value;
- use **signal-weighted, vega-neutral calendar positions**;
- use strictly walk-forward / out-of-sample estimation with no look-ahead bias.

## 1. Data preparation

For SPX and QQQ:

1. Load the existing 5-minute underlying and option data through the backtesting framework.
2. At every decision timestamp identify liquid expiries nearest configurable target maturities, initially approximately:
   - 1M
   - 2M
   - 3M
3. Use configurable DTE tolerances rather than assuming exact expiries.
4. Select an ATM call and put for each maturity using forward moneyness or the framework's most appropriate ATM definition.
5. Construct each maturity's ATM straddle from the selected call and put.
6. Extract or calculate:
   - ATM implied volatility;
   - call + put straddle price;
   - delta;
   - gamma;
   - theta;
   - vega;
   - bid/ask or execution-price information where available.
7. Filter stale, crossed, invalid, or insufficiently liquid quotes.

All calculations must use information available at the timestamp being evaluated.

## 2. Variance and forward-variance construction

For maturity \(T\), define total implied variance as:

$$
W_t(T)=T\,IV_t(T)^2
$$

with \(T\) expressed consistently in years.

For adjacent maturities \(T_1<T_2\), calculate:

$$
FV_t(T_1,T_2)
=
\frac{
W_t(T_2)-W_t(T_1)
}{
T_2-T_1
}.
$$

Construct at least:

$$
FV_{1M,2M}
$$

and

$$
FV_{2M,3M}.
$$

Optionally convert forward variance to forward volatility for reporting:

$$
FVol_{T_1,T_2}=\sqrt{FV_{T_1,T_2}}.
$$

Perform modelling in **variance space**, not volatility space.

## 3. Features

Create a compact, interpretable feature set.

### Curve features

Include:

- 1M ATM implied variance;
- 2M ATM implied variance;
- 3M ATM implied variance;
- \(FV_{1M,2M}\);
- \(FV_{2M,3M}\);
- forward-variance slope;
- term-structure slope;
- curvature;
- ratios or normalized spreads where useful.

### Dynamic features

For important curve variables calculate lagged changes over configurable horizons such as:

- 5 minutes;
- 15 minutes;
- 30 minutes;
- 60 minutes;
- longer horizons if useful.

### Volatility-regime features

Include:

- intraday realized variance from 5-minute returns;
- trailing realized volatility over several horizons;
- recent SPX/QQQ returns;
- absolute returns;
- a simple vol-of-vol measure based on recent changes in ATM IV;
- optionally VIX/VXN-related features if those data already exist in the framework.

Avoid adding large numbers of arbitrary predictors initially.

## 4. Fair-value model

The baseline fair-value model should estimate where the target forward-variance segment should sit conditional on the rest of the curve and current volatility regime.

For example:

$$
FV^{1M,2M}_t
=
\alpha
+
\beta_1 FV^{2M,3M}_t
+
\beta_2 IV^2_{1M,t}
+
\beta_3 RV_t
+
\beta_4 VoV_t
+
\beta^\top X_t
+
\epsilon_t.
$$

Use rolling or expanding-window **Ridge regression** as the primary baseline, with plain OLS available for comparison.

The model must be estimated strictly using data available before timestamp \(t\).

Produce:

$$
\widehat{FV}^{fair}_t
$$

and residual:

$$
e_t
=
FV_t-\widehat{FV}^{fair}_t.
$$

Normalize the residual using a rolling, past-only estimate of residual dispersion:

$$
z_t
=
\frac{e_t}
{\widehat{\sigma}_{e,t}}.
$$

Do not use full-sample means, standard deviations, regressions, PCA, or normalization anywhere in the trading logic.

## 5. Verify that mean reversion actually exists

Before treating the residual as a trading signal, explicitly test:

$$
\Delta FV_{t,t+h}
=
\alpha
+
\beta z_t
+
\gamma^\top X_t
+
\epsilon_{t+h}.
$$

Evaluate several holding horizons.

Report whether:

$$
\beta<0
$$

out of sample.

Show:

- coefficient estimates;
- t-statistics or bootstrap confidence intervals;
- forward-variance changes conditional on signal decile;
- average subsequent normalization by signal bucket.

The strategy should only be regarded as economically motivated if rich forward variance tends subsequently to fall and cheap forward variance tends subsequently to rise.

## 6. Trading signal

Define a configurable entry threshold \(z_{entry}\).

For example:

- no position for \(|z_t|<z_{entry}\);
- progressively larger positions as \(|z_t|\) increases;
- cap exposure at \(z_{max}\).

Construct a signed signal weight such as:

$$
s_t
=
\operatorname{sign}(z_t)
\cdot
\min
\left(
\frac{\max(|z_t|-z_{entry},0)}
{z_{scale}},
1
\right).
$$

Interpretation:

- \(s_t>0\): the later forward-variance segment is rich;
- \(s_t<0\): the later forward-variance segment is cheap.

Avoid unnecessary trading around zero.

## 7. Weighted vega-neutral calendar construction

This is a critical requirement.

For a rich \(1M\rightarrow2M\) forward segment:

- long the nearer-maturity ATM straddle;
- short the farther-maturity ATM straddle.

For a cheap forward segment, reverse both legs.

Let:

$$
V_F
$$

be the total contract-multiplier-adjusted vega of the front straddle and

$$
V_B
$$

the corresponding vega of the back straddle.

Size the legs so that:

$$
q_F V_F + q_B V_B = 0.
$$

A simple signal-weighted implementation is:

$$
q_F
=
\frac{B\,s_t}{V_F},
$$

$$
q_B
=
-\frac{B\,s_t}{V_B},
$$

where \(B\) is the configurable target gross vega/risk budget.

Therefore:

$$
q_FV_F+q_BV_B=0.
$$

Use fractional quantities internally if the framework permits them. If live-tradable integer contracts are required, implement a separate rounding procedure and report the resulting residual net vega.

Always report:

- front-leg vega;
- back-leg vega;
- gross vega;
- net vega;
- residual net vega after rounding;
- gamma;
- theta;
- delta;
- capital/notional exposure.

Do not call a trade "vega neutral" unless the measured portfolio vega confirms it.

## 8. Portfolio construction

Run the model independently for SPX and QQQ initially.

Allow:

- SPX-only;
- QQQ-only;
- combined SPX + QQQ portfolios.

If both are active simultaneously, allocate risk using configurable signal weights while maintaining:

1. vega neutrality within each calendar; and
2. a portfolio-level risk cap.

Do not allow one underlying to dominate merely because its option contract scale differs.

Normalize risk appropriately.

## 9. Position management

Implement configurable:

- entry z-score;
- exit z-score;
- maximum holding period;
- stop or signal invalidation level;
- gross-vega budget;
- maximum gamma;
- maximum theta;
- maximum number of simultaneous positions;
- minimum liquidity threshold.

A sensible baseline is:

- enter only beyond a meaningful residual threshold;
- exit when the residual substantially mean-reverts toward zero;
- optionally exit if the residual moves further against the trade by a configurable amount;
- avoid automatically resizing on every 5-minute bar unless the signal change is economically meaningful.

## 10. Execution and transaction costs

Use the existing framework's execution model.

Where available, evaluate:

1. mid-price theoretical results;
2. realistic bid/ask execution;
3. configurable commissions/fees;
4. slippage sensitivity.

Prevent simultaneous entry/exit assumptions at unavailable prices.

Avoid excessive turnover generated by small 5-minute signal changes.

## 11. P&L attribution

For each trade and in aggregate, attribute performance as far as the available Greeks permit to:

- change in implied volatility;
- term-structure convergence/divergence;
- gamma / realized spot movement;
- theta;
- vega;
- residual delta;
- transaction costs;
- unexplained residual.

This is important because positive calendar P&L should not automatically be interpreted as forward-variance alpha.

## 12. Backtest methodology

Use strict chronological walk-forward evaluation.

Create configurable:

- training window;
- validation window if required;
- test / live window;
- model-refit frequency.

Never randomly shuffle time-series observations.

Ensure:

- features are lagged correctly;
- option selection uses information known at the time;
- fair-value parameters are past-only;
- residual standard deviations are past-only;
- no future expiry information contaminates signals;
- rolling-window calculations do not leak future observations.

Add explicit assertions/tests checking common forms of look-ahead leakage.

## 13. Benchmarks

Compare the strategy against:

1. no position;
2. unconditional short ATM straddle;
3. simple raw term-slope calendar;
4. raw forward-variance z-score strategy without a fair-value model;
5. fair-value residual strategy;
6. fair-value residual strategy with vega-neutral sizing.

This will establish whether the additional modelling genuinely adds value.

## 14. Performance analysis

Report at minimum:

- cumulative P&L;
- annualized return where meaningful;
- Sharpe ratio;
- Sortino ratio;
- volatility;
- maximum drawdown;
- Calmar ratio;
- hit rate;
- average trade;
- median trade;
- turnover;
- number of trades;
- average holding period;
- P&L per unit gross vega;
- P&L per unit gamma risk;
- worst 1-day and 5-day outcomes;
- expected shortfall;
- performance by volatility regime;
- performance by calendar year;
- performance separately for SPX and QQQ.

Also report performance as a function of entry z-score so we can determine whether larger statistical dislocations correspond to larger subsequent alpha.

## 15. Diagnostics and charts

Include clear charts for:

- ATM variance curves through time;
- forward variance through time;
- predicted fair value vs observed forward variance;
- residual / z-score;
- subsequent forward-variance change versus current z-score;
- average future normalization by z-score bucket;
- position weights;
- gross and net vega;
- gamma and theta;
- cumulative strategy P&L;
- drawdown;
- turnover;
- performance by regime.

## 16. Robustness tests

Test sensitivity to:

- maturity targets;
- DTE selection tolerance;
- rolling training-window length;
- Ridge penalty;
- z-score lookback;
- entry threshold;
- exit threshold;
- holding horizon;
- vega budget;
- signal clipping;
- rebalance frequency;
- execution assumptions.

Also compare 1M→2M and 2M→3M forward segments separately.

Do not optimize parameters purely for maximum in-sample Sharpe. Prefer stable parameter regions and out-of-sample robustness.

## 17. Notebook structure

The notebook should be readable from top to bottom and contain:

1. configuration;
2. imports and framework integration;
3. data validation;
4. option/maturity selection;
5. implied and forward-variance construction;
6. feature engineering;
7. fair-value model;
8. signal generation;
9. weighted vega-neutral position construction;
10. integration with the existing backtester;
11. walk-forward backtest;
12. P&L attribution;
13. diagnostics;
14. benchmarks;
15. robustness analysis;
16. concise conclusions.

Put all important strategy parameters in one configuration object near the top.

Use reusable functions/classes rather than duplicated notebook code.

## 18. Final research conclusions

At the end of the notebook explicitly answer:

1. Do forward-variance residuals mean-revert out of sample?
2. Over what holding horizon is predictability strongest?
3. Does a fair-value model outperform a simple forward-variance z-score?
4. Does vega-neutral sizing improve risk-adjusted performance?
5. Is the strategy profitable separately in SPX and QQQ?
6. Is profitability concentrated in particular volatility regimes?
7. How much P&L is genuine term-structure convergence versus gamma/theta/other Greeks?
8. Does the strategy outperform unconditional short-straddle exposure on Sharpe, drawdown, and expected-shortfall metrics?
9. Are results robust to realistic execution assumptions?
10. Is there sufficient evidence to justify extending the model beyond linear Ridge/OLS?

Favor economic interpretability and robust out-of-sample evidence over model complexity.
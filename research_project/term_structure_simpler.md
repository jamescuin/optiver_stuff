Create a complete, self-contained Jupyter notebook implementing and backtesting a **simple SPX/QQQ implied-volatility term-structure strategy** using the **existing backtesting framework already available in the environment**.

Use the framework's existing data loading, option selection, execution, portfolio accounting, and performance-analysis functionality wherever possible. Do not build a separate backtesting engine unless absolutely necessary.

## Objective

Test whether relative dislocations in the implied forward-variance curve mean-revert.

The strategy should:

* trade **SPX and QQQ options only**;
* operate on **5-minute observations**;
* use ATM straddles;
* use one simple term-structure feature;
* trade calendar spreads;
* size calendars to be **weighted net-vega neutral**;
* use strictly walk-forward calculations with no look-ahead bias.

## 1. Maturities and ATM straddles

At every 5-minute timestamp, identify liquid option expiries closest to configurable targets:

* 1M
* 2M
* 3M

Use configurable DTE ranges rather than requiring exact maturities.

For each maturity:

1. Select the ATM call and ATM put.
2. Construct the ATM straddle.
3. Obtain:

   * implied volatility;
   * price;
   * vega;
   * delta;
   * gamma;
   * theta;
   * bid and ask where available.

Use forward moneyness for ATM selection if available.

Reject stale, crossed, invalid, or insufficiently liquid quotes.

## 2. Forward variance

For maturity (T), define total implied variance:

$$
W_t(T)=T,IV_t(T)^2
$$

with (T) expressed in years.

For (T_1<T_2):

$$
FV_t(T_1,T_2)
=============

\frac{
W_t(T_2)-W_t(T_1)
}{
T_2-T_1
}.
$$

Calculate:

$$
FV^{12}_t = FV_t(1M,2M)
$$

and

$$
FV^{23}_t = FV_t(2M,3M).
$$

All modelling should remain in **variance space**, not volatility space.

## 3. Single trading feature

Define the forward-curve relative-value feature:

$$
X_t
===

## FV^{12}_t

FV^{23}_t.
$$

Interpretation:

* high (X_t): the 1M→2M forward-variance segment is rich relative to the 2M→3M segment;
* low (X_t): the 1M→2M segment is cheap relative to the 2M→3M segment.

Normalize this using a rolling, past-only z-score:

$$
z_t
===

\frac{
X_t-\mu_{t,L}
}{
\sigma_{t,L}
},
$$

where (\mu_{t,L}) and (\sigma_{t,L}) are calculated using only observations strictly prior to or available at timestamp (t).

Make the rolling lookback (L) configurable.

Test sensible horizons such as:

* 1 trading day;
* 5 trading days;
* 10 trading days;
* 20 trading days.

Do not use full-sample normalization.

## 4. Trading logic

Use a configurable entry threshold (z_{entry}).

Baseline:

* if (z_t > z_{entry}), treat the 1M→2M forward segment as rich;
* if (z_t < -z_{entry}), treat it as cheap;
* otherwise hold no position.

### Rich forward segment

When:

$$
z_t > z_{entry},
$$

trade:

* **long 1M ATM straddle**;
* **short 2M ATM straddle**.

### Cheap forward segment

When:

$$
z_t < -z_{entry},
$$

trade:

* **short 1M ATM straddle**;
* **long 2M ATM straddle**.

The 3M options are used to construct the feature but do not need to be traded in the baseline strategy.

## 5. Signal weighting

Do not use only binary positions.

Create a clipped signal weight:

$$
s_t
===

\operatorname{sign}(z_t)
\cdot
\min
\left(
\frac{
\max(|z_t|-z_{entry},0)
}{
z_{scale}
},
1
\right).
$$

Make both (z_{entry}) and (z_{scale}) configurable.

Larger dislocations should therefore receive larger risk allocations, subject to a cap.

Also provide a simple binary-weight benchmark.

## 6. Weighted net-vega-neutral sizing

This is a critical requirement.

Let:

$$
V_F
$$

be the contract-multiplier-adjusted vega of the front 1M straddle and:

$$
V_B
$$

the contract-multiplier-adjusted vega of the 2M straddle.

Choose quantities such that:

$$
q_F V_F + q_B V_B = 0.
$$

For a signal-weighted calendar, use a configurable gross-vega budget (B).

For a rich-forward signal:

$$
q_F
===

\frac{B|s_t|}{V_F},
$$

$$
q_B
===

-\frac{B|s_t|}{V_B}.
$$

For a cheap-forward signal, reverse both signs.

Equivalently, ensure at all times:

$$
q_FV_F+q_BV_B \approx 0.
$$

Report:

* front-leg vega;
* back-leg vega;
* gross vega;
* net vega;
* residual net vega;
* gamma;
* theta;
* delta.

If fractional contracts are allowed by the backtesting framework, use them for the theoretical baseline.

If integer contracts are required, implement a separate rounded version and report the residual vega introduced by rounding.

## 7. Position management

Make configurable:

* entry z-score;
* exit z-score;
* maximum holding period;
* rolling z-score lookback;
* gross-vega budget;
* signal clipping;
* minimum liquidity requirement;
* rebalance threshold.

Baseline exit rule:

* enter when (|z_t| > z_{entry});
* exit when (|z_t| < z_{exit}), where (z_{exit} < z_{entry}).

Do **not** resize the portfolio automatically on every 5-minute bar for tiny changes in (z_t).

Only resize if the desired risk weight changes by more than a configurable threshold.

This should reduce unnecessary turnover.

## 8. Backtesting discipline

All calculations must be chronological and walk-forward.

Ensure:

* no future option prices are used;
* no future Greeks are used;
* ATM strike selection is timestamp-correct;
* rolling means and standard deviations are past-only;
* expiry selection is timestamp-correct;
* no future knowledge enters signal creation;
* no full-sample standardization is used.

Add explicit assertions or checks for potential look-ahead leakage.

## 9. Execution assumptions

Use the existing backtesting framework's execution logic.

Test at least:

1. mid-price execution;
2. bid/ask-aware execution if available;
3. configurable commissions and fees.

Report turnover and transaction-cost sensitivity.

Because the signal is calculated every 5 minutes, distinguish clearly between:

* **signal evaluation frequency: 5 minutes**;
* **actual trading frequency**, which may be substantially lower.

## 10. Benchmarks

Compare:

### Benchmark A: No position

Zero-return baseline.

### Benchmark B: Unconditional short ATM straddle

Use comparable risk scaling where possible.

### Benchmark C: Raw 1M/2M term slope

For example:

$$
IV^2_{2M}-IV^2_{1M}.
$$

### Benchmark D: Forward variance level

Trade only:

$$
z(FV^{12}).
$$

### Benchmark E: Preferred relative-forward feature

Trade:

$$
z(FV^{12}-FV^{23}).
$$

This comparison is important to establish whether using the second forward segment improves the signal by removing common volatility-level effects.

## 11. Performance analysis

Report:

* cumulative P&L;
* Sharpe ratio;
* Sortino ratio;
* volatility;
* maximum drawdown;
* Calmar ratio;
* hit rate;
* average trade P&L;
* median trade P&L;
* number of trades;
* turnover;
* average holding period;
* P&L per unit gross vega;
* worst daily loss;
* expected shortfall;
* results by calendar year;
* results separately for SPX and QQQ.

Also report results by entry-signal bucket, for example:

$$
1 < |z| < 1.5
$$

$$
1.5 < |z| < 2
$$

$$
2 < |z| < 2.5
$$

$$
|z| > 2.5.
$$

Check whether larger dislocations actually lead to stronger subsequent performance.

## 12. Mean-reversion diagnostic

Before relying on strategy P&L alone, test whether the feature itself mean-reverts.

For multiple horizons (h), calculate:

$$
\Delta X_{t,t+h}
================

X_{t+h}-X_t.
$$

Estimate:

$$
\Delta X_{t,t+h}
================

\alpha+\beta z_t+\epsilon_{t+h}.
$$

For genuine mean reversion we expect:

$$
\beta<0.
$$

Evaluate horizons such as:

* 30 minutes;
* 1 hour;
* 2 hours;
* end of day;
* 1 trading day;
* several trading days.

Plot average future changes in (X) conditional on the current z-score bucket.

## 13. P&L attribution

Where the data and framework allow, decompose calendar P&L into:

* vega / implied-volatility changes;
* gamma / realized spot movement;
* theta;
* residual delta;
* transaction costs;
* unexplained residual.

This is important because profitable calendar P&L should not automatically be attributed to term-structure mean reversion.

Confirm that net portfolio vega remains approximately zero through time.

## 14. Robustness tests

Test sensitivity to:

* z-score lookback;
* entry threshold;
* exit threshold;
* maturity selection;
* DTE tolerance;
* signal-weight scaling;
* gross-vega budget;
* holding period;
* rebalance threshold;
* SPX versus QQQ;
* execution assumptions.

Do not optimize aggressively for maximum Sharpe.

Look for broad parameter regions where results remain stable.

## 15. Notebook structure

Structure the notebook as:

1. Configuration
2. Framework integration
3. Data validation
4. ATM straddle construction
5. Forward-variance calculation
6. Feature construction
7. Rolling z-score
8. Signal generation
9. Weighted vega-neutral calendar sizing
10. Backtest
11. P&L attribution
12. Mean-reversion diagnostics
13. Benchmark comparison
14. Robustness tests
15. Conclusions

Keep all strategy parameters in one clearly documented configuration object near the top.

Use reusable functions rather than duplicated notebook code.

## 16. Final questions to answer

At the end, explicitly answer:

1. Does

$$
FV_{1M,2M}-FV_{2M,3M}
$$

mean-revert?

2. Does its z-score predict subsequent calendar P&L?

3. What holding horizon works best?

4. Does signal weighting improve results versus binary trading?

5. Does weighted vega-neutral sizing materially reduce volatility-level exposure?

6. Are results robust separately for SPX and QQQ?

7. Does the relative-forward feature outperform simply using

$$
z(FV_{1M,2M})?
$$

8. How much performance remains after realistic bid/ask assumptions?

9. Is the strategy materially better on Sharpe/drawdown than unconditional short-vol exposure?

10. Is there enough evidence to justify adding a more complicated fair-value model?

The preferred philosophy is: **prove that the simplest economically sensible term-structure signal works before adding model complexity.**

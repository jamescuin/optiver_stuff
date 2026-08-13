# SPX–QQQ 0–2 DTE Research Addendum

## Why 0–2 DTE Matters

With:

- 5-minute volatility-surface observations,
- SPX / SPXW / QQQ underlying mids,
- corresponding Greeks,
- the ability to compute arbitrary structure theo,
- and delta-hedged theo P&L,

0–2 DTE is a particularly attractive research area.

The goal should be to study **relative short-dated option value and realized P&L**, not just raw IV changes.

---

# Core Principle

For 0DTE especially, rank targets approximately as:

1. **Delta-hedged theo P&L**
2. **Structure theo change**
3. **Total variance**
4. **Raw IV change**

As expiry approaches, vega collapses and annualized IV can move dramatically without producing proportionate economic value.

---

# Highest-Priority Tests

## 1. Relative Implied vs Realized Variance

Estimate short-dated relative implied variance between QQQ and the combined S&P surface.

Compare it with subsequent realized relative variance from the underlyings.

Example residual return:

\[
r_t^{idio}
=
r_t^{QQQ}
-
\beta_t r_t^{SPX}
\]

Then ask:

> Is QQQ charging too much or too little for the residual variance it subsequently realizes relative to S&P?

Natural trade expression:

- QQQ straddle vs SPX/SPXW straddle
- Greek-controlled / vega-matched
- evaluated with delta-hedged theo P&L

---

## 2. 0DTE Gamma / Theta Relative Value

For short holding intervals, decompose delta-hedged option P&L approximately as:

\[
\Delta V-\Delta\Delta S
\approx
\frac12\Gamma(\Delta S)^2
+
\Theta\Delta t
+
Vega\Delta\sigma
+\cdots
\]

Then compare QQQ and S&P structures under controlled Greek exposure.

Key question:

> Which market is charging more for near-term realized movement?

Separate relative P&L into:

- gamma realization,
- theta decay,
- surface repricing.

---

## 3. Follow the Same Expiry: 2DTE → 1DTE → 0DTE

Track a given expiration through its life.

For a cross-index residual \(Z\):

\[
Z_{2DTE}
\rightarrow
Z_{1DTE}
\rightarrow
Z_{0DTE}
\]

Test:

- persistence,
- widening,
- mean reversion,
- collapse on expiry day,
- whether 2DTE predicts 1DTE,
- whether 1DTE predicts 0DTE relative P&L.

This studies the **life cycle of a relative-vol dislocation** rather than treating each DTE bucket independently.

---

## 4. 0 / 1 / 2 DTE Front-End Term Structure

Use total variance where possible:

\[
w(k,T)=\sigma^2(k,T)T
\]

Construct:

\[
TS_{01}
=
w_{1DTE}-w_{0DTE}
\]

\[
TS_{12}
=
w_{2DTE}-w_{1DTE}
\]

Then form cross-index residuals:

\[
X_{01}
=
TS_{01}^{QQQ}
-
\beta TS_{01}^{SP}
\]

and similarly for \(1DTE/2DTE\).

Test whether unusual front-end steepness or inversion subsequently converges.

Prefer:

- total variance,
- structure theo value,
- or normalized P&L

over raw IV differences.

---

## 5. Minutes-to-Expiry Normalization

For 0DTE, every observation should be indexed by:

\[
\tau
=
\text{minutes to expiry}
\]

A 10:00 observation and a 15:45 observation should not be treated as economically equivalent.

Normalize features conditionally on time-to-expiry:

\[
Z_t
=
\frac{
X_t-\mu_X(\tau)
}{
\sigma_X(\tau)
}
\]

Apply this to:

- relative IV,
- skew,
- straddle value,
- gamma,
- theta,
- relative term structure,
- residual P&L predictors.

This is essential to avoid mistaking normal intraday expiry mechanics for alpha.

---

## 6. Surface Transport After Spot Moves

After a large SPX / QQQ move, estimate how the short-dated smile normally moves in forward-moneyness space.

Model expected QQQ surface location conditional on:

- SPX spot move,
- QQQ spot move,
- QQQ idiosyncratic move,
- current surface state,
- minutes to expiry.

Residual:

\[
\epsilon_t(k)
=
\sigma_t^{observed}(k)
-
\sigma_t^{expected}(k\mid\Delta S)
\]

Then test whether local residuals:

- persist,
- continue,
- or mean-revert over the next 5–60 minutes.

This can reveal cases where:

- ATM reprices,
- but wings lag,
- or skew responds abnormally.

---

# Preferred Trade-Level Study

Construct an ATM-ish straddle pair:

\[
\Pi_t
=
Straddle_t^{QQQ}
-
q_t Straddle_t^{SP}
\]

Choose \(q_t\) using a controlled-risk convention such as:

- vega matching,
- gamma matching,
- minimum historical variance,
- or another explicit Greek-risk objective.

Then compute:

\[
P\&L_{t,t+h}^{rel}
\]

using delta-hedged theo P&L.

Candidate predictors:

\[
X_t
=
f(
\text{relative IV},
\text{relative skew},
\text{0/1/2D term structure},
r^{idio},
\text{minutes to expiry}
)
\]

Primary question:

\[
E[P\&L_{t,t+h}^{rel}\mid X_t]?
\]

This may be cleaner than predicting raw IV for 0DTE.

---

# Useful Secondary Tests

## Overnight Transfer

Test whether a 1DTE / 2DTE dislocation near the close predicts:

- next-day opening relative vol,
- next-day opening structure value,
- overnight relative theo P&L.

Treat separately from intraday effects.

## Risk-Neutral Tail Shape

Later, consider relative:

- downside probability,
- skewness,
- tail pricing.

But only after simpler straddle / skew / term-structure tests are established.

Very short-dated tail metrics can be numerically noisy.

---

# What Not to Infer

Do **not** infer aggregate dealer gamma positioning from option Greeks alone.

Without reliable position / open-interest information, Greeks tell you the sensitivity of individual options or structures, not the market's net gamma exposure.

---

# Recommended 0–2 DTE Research Order

1. Minutes-to-expiry normalization.
2. Relative delta-hedged ATM straddle P&L.
3. Implied vs subsequent realized relative variance.
4. Track same expiry from 2DTE → 1DTE → 0DTE.
5. 0/1/2DTE front-end total-variance shape.
6. Gamma / theta / vega P&L attribution.
7. Spot-conditioned surface-transport residuals.
8. Relative skew.
9. Overnight transfer.
10. Tail-shape metrics last.

---

# Key Success Criteria

A 0–2 DTE signal should:

1. survive out of sample,
2. remain monotonic across signal buckets,
3. survive minutes-to-expiry conditioning,
4. survive relative-spot conditioning,
5. produce positive delta-hedged theo P&L,
6. remain positive after controlling for vega / gamma / theta risk,
7. not depend on one exact DTE or one isolated period,
8. not be explained by stale 5-minute surface observations.

---

# Main Research Question

The cleanest framing is:

> **When short-dated QQQ option value becomes unusually rich or cheap relative to the combined S&P surface, after controlling for relative spot movement, minutes-to-expiry, and Greek exposures, does a Greek-controlled relative structure earn predictable future delta-hedged theo P&L?**

# SPX–QQQ Cross-Surface Research Plan — Tomorrow

## Objective

Find **simple, falsifiable SPX/QQQ cross-surface signals** that predict future **relative option value / delta-hedged theo P&L per unit of risk**.

Core question:

> **Where did QQQ vol fail to respond normally to the combined S&P volatility surface + relative spot information, and does that residual subsequently correct or continue?**

Keep the **prediction layer** separate from the **trade-expression layer**:

1. Predict future QQQ/SP relative surface movement.
2. Convert the prediction into candidate structures using Greeks.
3. Evaluate theo and/or delta-hedged P&L under controlled risk.


## Sampling Constraint

Observations are spaced **5 minutes apart**. This defines the research resolution.

Consequences:

- all features and targets must be built on 5-minute or longer intervals;
- the first forecast horizon is **next 5-minute observation**;
- no claim about second/minute-scale SPX→QQQ or QQQ→SPX transmission is identifiable;
- contemporaneous 5-minute moves may contain unknown within-bar ordering;
- use strictly lagged predictors for the cleanest causal tests;
- delta-hedged P&L should use a hedge convention consistent with the data frequency (e.g. hedge/rebalance only at observed 5-minute timestamps unless a finer underlying series is separately available).

---

## 0. Data / Timing Validation — Do This First

Before testing alpha, characterize the feeds.

### Check

- Frequency of **changes between 5-minute snapshots** by product, expiry, strike, and surface region.
- Whether whole expiries update together.
- Whether ATM updates before wings.
- SPX vs SPXW vs QQQ synchronization at the 5-minute snapshot level.
- Dependence of surface updates on underlying mid moves.
- Repeated, interpolated, or stale surface values.
- Exact expiry / settlement conventions represented in the data.
- Whether Greeks and IV are computed from the same contemporaneous state.

### Control experiment

Use **SPX vs SPXW** as a diagnostic before merging them.

For economically matched surface points, measure:

- update lead/lag,
- short-horizon IV residuals,
- apparent mean reversion / continuation.

If large “alpha” appears between SPX and SPXW, assume **feed/theo mechanics first**, not economics.

### Sampling / alignment falsification

The minimum spacing between observations is **5 minutes**. Therefore:

- make **no sub-5-minute lead/lag claims**;
- treat each observation as a 5-minute snapshot/bar;
- test alignment sensitivity by shifting one product by:
  - `+1 bar / -1 bar` = 5 minutes,
  - `+2 bars / -2 bars` = 10 minutes;
- measure repeated/stale surface values across successive 5-minute observations;
- compare results using contemporaneous bars versus strictly lagged predictors.

**Hard fail:** the signal disappears when predictors are made strictly causal by one 5-minute bar, or is explained by stale/repeated observations.

A contemporaneous 5-minute relationship may be economically useful, but it **cannot identify which market moved first inside the 5-minute interval**.

---

## 1. Build One S&P Information Surface from SPX + SPXW

After the timing/control checks pass, treat SPX and SPXW as observations of one latent S&P surface:

\[
\mathcal S^{SP}_t(k,T)=f(SPX,SPXW)
\]

Do **not** simply average SPX and SPXW.

For each QQQ point, construct the best matched S&P reference using:

- exact / interpolated maturity,
- consistent forward moneyness or delta,
- total variance where useful,
- trailing/causal interpolation only.

Keep the original `SPX` / `SPXW` source label internally for diagnostics.

Preferred coordinates:

\[
k=\ln(K/F_T), \qquad w(k,T)=\sigma^2(k,T)T
\]

where the data supports them.

---

## 2. First Alpha Test — ATM Relative Vol Residual

Start with one clean point:

- ~30D QQQ ATM
- matched ~30D combined S&P ATM
- SPX mid
- QQQ mid

Estimate using trailing data only:

\[
\Delta IV^{QQQ}_t
=
\alpha_t+\beta_t\Delta IV^{SP}_t+\epsilon_t
\]

Feature:

\[
X_t=\epsilon_t
\]

Target over horizon \(h\):

\[
Y_{t,h}
=
\Delta IV^{QQQ}_{t:t+h}
-
\beta_t\Delta IV^{SP}_{t:t+h}
\]

Test horizons:

`5m, 10m, 15m, 30m, 60m, EOD, 1d`

Use the **5-minute observation interval as the atomic time step**. Do not interpolate synthetic intermediate observations.

Test both:

- **continuation:** \(X_tY_{t,h}>0\)
- **mean reversion:** \(X_tY_{t,h}<0\)

### Required outputs

For every horizon:

- mean future residual by feature decile,
- median future residual by decile,
- hit rate,
- confidence / standard error,
- sample count,
- result by day/session/regime.

**Pass:** monotonic response across signal buckets with a stable impulse-response shape.

---

## 3. Add Spot Conditioning Immediately

Do not interpret the raw vol residual until relative spot movement is controlled.

Estimate rolling spot beta:

\[
r^{idio}_t
=
r^{QQQ}_t-\beta^S_t r^{SPX}_t
\]

Then model the normal QQQ-relative-vol response to idiosyncratic spot:

\[
\widehat{\epsilon}^{vol}_t
=
a+b_1r^{idio}_t+b_2|r^{idio}_t|+b_3(r^{idio}_t)^2
\]

Improved feature:

\[
X_t^*
=
\epsilon_t-\widehat{\epsilon}^{vol}_t
\]

Keep the conditioning only if it improves **out-of-sample** prediction.

**Key question:** does the QQQ residual survive after explaining the move with relative spot?

---

## 4. Map the Full Impulse Response

For every promising feature, estimate:

\[
E[Y_{t,h}\mid X_t]
\]

across all horizons.

Do not optimize directly for one horizon.

Look for:

- next-bar continuation,
- delayed continuation,
- one-/two-bar correction,
- continuation followed by slower mean reversion,
- regime-dependent sign changes.

The impulse-response curve determines the realistic holding period.

---

## 5. Convert Surface Prediction into Economic P&L

Once a surface signal survives steps 0–4, evaluate it in structures.

For structure \(j\) with Greek exposures:

\[
ExpectedMove_{j,t}
\approx
\mathbf{Vega}_j^\top E[\Delta\boldsymbol{\sigma}\mid X_t]
\]

Then compute the structure's:

- theo P&L,
- delta-hedged theo P&L using a hedge schedule consistent with observed timestamps,
- P&L / absolute vega,
- P&L / weighted-vega risk,
- P&L / gamma,
- drawdown / tail loss.

Use the actual Greeks available in the dataset rather than assuming equal notionals.

Where appropriate, constrain candidate cross-index structures to be approximately:

- delta neutral,
- vega matched,
- bounded in gamma,
- bounded in theta.

A useful generalized score is:

\[
Score_{j,t}
=
\frac{
\mathbf v_j^\top \mathbf x_t
}{
\sqrt{\mathbf v_j^\top\Sigma_{\sigma}\mathbf v_j}
}
\]

Start simpler if necessary:

\[
Score_{j,t}
=
\frac{\mathbf v_j^\top \mathbf x_t}
{\sum_i |Vega_i|}
\]

**Important:** first establish surface predictability; only then optimize the structure.

---

## 6. Next Features — Add One at a Time

Only proceed if ATM residual + spot conditioning survives.

### A. Relative skew

\[
Skew=IV_{25\Delta put}-IV_{ATM}
\]

Test the QQQ residual versus the matched combined-S&P skew move.

### B. Relative vol level

Estimate whether QQQ is structurally rich/cheap versus S&P.

Use slower horizons:

`5m, 30m, 1h, EOD, 1d`

### C. Relative term structure

Prefer total variance:

\[
w(k,T)=\sigma^2(k,T)T
\]

Test calendar dislocations after matching maturity carefully.

### D. Curvature

\[
C=IV_{25P}+IV_{25C}-2IV_{ATM}
\]

Treat curvature results as lower-confidence until they survive interpolation/timing checks.

### E. Local single-surface residuals

Run analogous QQQ-only and S&P-only tests.

**Purpose:** prove that cross-market information adds value beyond ordinary internal surface mean reversion.

---

## 7. Cross-Surface Predictive Lag — 5-Minute Resolution Only

After the clean residual framework is working, test whether information in one market at time \(t\) predicts the other at \(t+5m\) or later:

\[
\Delta IV^{QQQ}_{t:t+5m}
=
a+b_1\Delta IV^{QQQ}_{t-5m:t}
+b_2\Delta IV^{SP}_{t-5m:t}
+\ldots
\]

and the reverse direction.

Focus on the **incremental out-of-sample predictive value** of the other market.

Do **not** interpret this as true market-microstructure lead/lag. With 5-minute snapshots, ordering inside each interval is unobserved.

---

## 8. Generalize Only After the Simple Economics Are Clear

Final model:

\[
E[\Delta\boldsymbol{\sigma}^{QQQ}_t]
=
f(
\Delta\boldsymbol{\sigma}^{SP}_t,
r^{SPX}_t,
r^{QQQ}_t,
|r^{QQQ}_t|,
\text{surface state}_t
)
\]

Residual:

\[
\boldsymbol{\epsilon}_t
=
\Delta\boldsymbol{\sigma}^{QQQ}_t
-
E[\Delta\boldsymbol{\sigma}^{QQQ}_t]
\]

Interpretation:

> **Where did QQQ vol fail to respond normally to S&P vol + spot information?**

Only after this framework is understood should you add:

- PCA,
- regularized multivariate models,
- tree models,
- neural nets / other ML.

---

# Standard Falsification Gates

Every feature must pass all of these:

1. **Monotonicity** — future relative return/P&L varies cleanly across feature buckets.
2. **Walk-forward stability** — no random train/test split.
3. **Time stability** — check by day, week, session, and vol regime.
4. **Parameter robustness** — no dependence on one exact lookback/DTE/horizon.
5. **Causal availability** — no future interpolation or centered smoothing.
6. **Sampling/alignment robustness** — survive ±1-bar / ±2-bar alignment tests and strictly lagged predictors.
7. **SPX/SPXW consistency** — not explained by one family’s update mechanics.
8. **Incremental value** — each added feature improves the existing stack.
9. **Economic value** — survives in theo / delta-hedged P&L per unit of risk.
10. **Concentration check** — result is not driven by a handful of events.

Kill weak signals early.

---

# Tomorrow's Exact Research Order

## Morning — Establish whether the effect is real

1. Audit SPX / SPXW / QQQ update mechanics.
2. Run SPX-vs-SPXW control tests.
3. Construct the combined S&P reference surface.
4. Run the ~30D ATM QQQ-vs-S&P ΔIV residual.
5. Plot the full impulse response from `5m` onward.
6. Run ±1-bar / ±2-bar alignment falsification.

**Decision gate:** if this fails, fix data alignment / surface construction before adding complexity.

## Midday — Explain the residual

7. Add relative-spot conditioning.
8. Compare raw vs spot-conditioned out-of-sample results.
9. Segment by time of day and vol regime.
10. Confirm SPX/SPXW source consistency.

**Decision gate:** only continue if a stable residual remains.

## Afternoon — Determine whether it is economically useful

11. Map the predicted surface move through the available Greeks.
12. Test simple vega-matched / delta-controlled structures.
13. Compute theo and delta-hedged theo P&L.
14. Normalize by vega / weighted surface risk.
15. Examine P&L by signal decile and holding horizon.

**Decision gate:** require both statistical monotonicity and economically meaningful risk-adjusted P&L.

## Then — Expand carefully

16. Relative skew.
17. Relative level.
18. Term structure.
19. Local single-surface controls.
20. Curvature.
21. Cross-surface lead/lag.
22. Full multivariate residual model.
23. PCA / ML last.

---

# What Success Tomorrow Looks Like

By the end of the session, the ideal outcome is **not** a complex model.

It is a defensible answer to these five questions:

1. **Are the SPX/SPXW/QQQ surfaces synchronized well enough to study?**
2. **Does a simple QQQ-vs-combined-S&P ATM vol residual predict future relative surface movement?**
3. **Does the effect survive relative-spot conditioning and timestamp perturbation?**
4. **What is the impulse-response / optimal holding horizon from 5 minutes onward?**
5. **Does the surviving signal produce monotonic positive theo or delta-hedged P&L per unit of controlled Greek risk?**

If all five are yes, then the research program is worth expanding to skew, term structure, curvature, and richer models.

If any early gate fails, diagnose that failure before adding features.

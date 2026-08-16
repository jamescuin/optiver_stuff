## Objective

Determine whether there is **stable, economically meaningful predictability** in future delta-hedged structure PnL and whether nonlinear modelling adds genuine value beyond a simple regularised model.

The emphasis should be on understanding the alpha rather than searching across many algorithms.

## 1. Define the prediction problem carefully

Primary target:

[
y=
PnL^{DH}/|WVega|.
]

Choose one primary prediction horizon and several secondary horizons.

**Why:** the target must correspond directly to the economic quantity portfolio construction consumes.

## 2. Establish simple baselines

Test:

* unconditional mean;
* structure-conditioned mean;
* structure × time-of-day mean.

**Why:** ML should demonstrate incremental information beyond basic conditional effects already present in the data.

## 3. Build economically meaningful features

Focus on:

* volatility level;
* skew and curvature;
* term structure;
* changes in the surface;
* realised volatility;
* underlying returns;
* structure characteristics;
* liquidity;
* IV-versus-expected-RV quantities.

**Why:** in a low-signal problem, better representation of the economics is likely more valuable than additional model complexity.

## 4. Add forward variance / volatility-premium features

Construct horizon-matched:

[
FVRP
====

## IV_{\mathrm{fwd}}^2

\widehat{RV}_{\mathrm{fwd}}^2.
]

Include:

* implied forward variance;
* forecast realised variance;
* FVRP;
* ratio;
* rolling z-score;
* change in FVRP.

Start realised-volatility forecasts with EWMA and HAR-RV/GARCH as benchmarks.

**Why:** the economically relevant question is not merely future volatility, but whether options appear rich or cheap relative to expected realised variance.

## 5. Train a structured ElasticNet

Use:

* standardised features;
* structure characteristics;
* optional structure OHE;
* selected economically motivated interactions.

Examples:

[
FVRP\times\text{vega/skew exposure},
]

[
\text{skew state}\times\text{skew exposure},
]

[
\text{term structure}\times DTE.
]

**Why:** this provides an interpretable benchmark and tests whether the alpha is predominantly smooth/linear.

## 6. Train a shallow GBDT challenger

Use identical samples, features and walk-forward folds.

Keep trees deliberately conservative.

**Why:** the research question is whether stable nonlinearities and interactions exist beyond the ElasticNet—not whether a flexible model can fit the history.

## 7. Consider residual modelling

Optionally fit:

[
r=y-\hat y_{\mathrm{ElasticNet}}
]

and train the GBDT on (r):

[
\hat y
======

\hat y_{\mathrm{ElasticNet}}
+
\hat r_{\mathrm{GBDT}}.
]

**Why:** this gives the nonlinear model a precise job: identify systematic structure not captured by the simpler economic model.

## 8. Use global structure-aware models first

Compare:

1. no structure information;
2. structure ID;
3. economic structure characteristics;
4. only later, separate models by broad structure family.

**Why:** pooling data improves statistical efficiency while structure characteristics allow the relationship to differ economically across trades.

## 9. Evaluate economically, not just statistically

Use OOF:

[
MSE,\quad MAE,\quad R^2,
]

but also study:

[
E[y\mid\hat y\text{ decile}],
]

tail performance, rank correlation and top-minus-bottom outcomes.

**Why:** a low-(R^2) model can still be useful if it reliably identifies unusually attractive trades.

## 10. Analyse stability

Break results down by:

* walk-forward fold;
* time period;
* structure;
* horizon;
* time of day;
* market state.

Especially study:

[
Performance_{\mathrm{GBDT}}
---------------------------

Performance_{\mathrm{ElasticNet}}.
]

**Why:** persistent modest improvement is more credible than a large result driven by one historical period.

## 11. Run feature-family ablations

Remove one economic feature family at a time.

**Why:** this identifies where predictive information actually originates and guards against accidental complexity.

## 12. Inspect calibration

Initially use:

[
\alpha=\hat y.
]

Only add simple OOF shrinkage/calibration if prediction magnitude is systematically wrong.

**Why:** the target already has economic units, so calibration should solve an observed problem rather than become an automatic extra model.

## 13. Test ranking secondarily

Ask whether the model identifies the relatively best opportunities even when precise PnL prediction is difficult.

**Why:** portfolio construction may benefit substantially from good ordering even with noisy absolute forecasts.

## 14. Ensemble only if justified

If ElasticNet and GBDT have complementary OOF errors, test a simple equal-weight ensemble first.

**Why:** diversification between genuinely different predictors can help, but additional ensemble fitting can easily overfit.

## 15. Test HMM regimes only later

Use point-in-time HMM regime probabilities as additional features:

[
P(Z_t=k\mid\mathcal F_t).
]

Do not initially fit separate models by regime.

**Why:** this tests whether latent market state changes the alpha relationship without fragmenting an already limited sample.

## Research Order

1. Target/horizon definition.
2. Naïve baselines.
3. Core economic features.
4. Forward variance/FVRP feature family.
5. ElasticNet.
6. Shallow GBDT.
7. OOF economic and stability analysis.
8. Feature-family ablations.
9. Structure representation experiments.
10. Residual modelling if useful.
11. Calibration/ranking experiments.
12. Simple ensemble.
13. HMM regime features.
14. Further complexity only if justified.

### Guiding Principle

[
\boxed{
\text{Complexity must earn its place through stable, leakage-safe, incremental OOF economic value.}
}
]

The desired research conclusion is not simply which algorithm wins, but **where the alpha comes from, how it depends on structure and market state, and whether that relationship is stable enough to trade.**

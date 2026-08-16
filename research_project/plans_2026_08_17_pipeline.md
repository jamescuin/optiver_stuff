## Objective

Build an **ML-first trading pipeline** where models forecast expected economic edge, while portfolio construction determines how much to trade. Rule-based strategies should plug into the same framework without requiring a separate architecture.

## 1. Keep the existing upstream modules

Retain:

`DataSources`
→ `DataQualityLayer`
→ `StructureUniverse`
→ `StructureResolver`
→ `StructurePathBuilder`
→ `FeatureEngine`
→ `LabelBuilder`
→ `DatasetAssembler`
→ `AlphaModel` / `ModelTrainer`

**Why:** these responsibilities are already cleanly separated and support parallel development.

## 2. Standardise the primary ML target

Use:

[
y_{i,t,h}
=========

\frac{\text{future delta-hedged PnL}*{i,t\rightarrow t+h}}
{|\text{weighted vega}*{i,t}|}.
]

Use one primary horizon, with additional horizons for robustness.

**Why:** this normalises opportunities across structures while retaining direct economic interpretation.

## 3. Make ML the default strategy behaviour

At each rebalance:

1. generate new features;
2. predict alpha for all eligible structures;
3. resolve the relevant structures;
4. combine new opportunities with existing positions;
5. re-optimise the portfolio.

ML positions have no mandatory holding period by default.

**Why:** prediction horizon describes what the forecast means; portfolio positions should remain free to resize as new information arrives.

## 4. Introduce a common `TradeCandidate`

Each opportunity should contain:

* strategy/model ID;
* structure ID and resolved contracts;
* expected PnL/WVega;
* forecast horizon;
* WVega and Greeks per contract;
* transaction costs;
* liquidity/max size;
* optional lifecycle restrictions.

**Why:** this creates one downstream interface for ML, rule-based and future strategy types.

## 5. Maintain exact existing positions

Optimise over:

[
\text{existing resolved positions}
+
\text{new eligible candidates}.
]

Do not re-resolve an existing position into new contracts.

**Why:** an abstract structure definition and a position actually held are different objects.

## 6. Convert model alpha into expected PnL per contract

If:

[
\alpha_i=E[PnL/|WVega|],
]

and

[
v_i=|WVega_i|,
]

then:

[
\mu_i=\alpha_i v_i.
]

**Why:** the model benefits from a normalised target, while the optimiser operates naturally on actual contract quantities.

## 7. Replace max-risk sizing with joint optimisation

Start with:


$$
q_t^{*}
=
\underset{q}{\operatorname{arg\,max}}
\left\{
\mu_t^\top q
-
\frac{\lambda}{2} q^\top \Sigma_t q
-
\sum_i c_{i,t}\left|q_i-q_{i,t-1}\right|
\right\}
$$
subject to:

* WVega;
* delta;
* gamma;
* margin/capital;
* liquidity;
* individual position;
* strategy/structure concentration limits.

**Why:** risk limits should constrain positions, not automatically force every positive signal to maximum size. Joint optimisation allocates scarce risk to the best combination of opportunities.

## 8. Support rules through the same framework

For a rule-based strategy, estimate historically:

[
E[PnL/|WVega|\mid\text{rule fired}]
]

using only information available through the relevant historical training window.

Rules may additionally specify:

* entry windows;
* minimum holding periods;
* mandatory exits;
* resizing/reversal restrictions.

**Why:** rules determine when a trade is valid; the portfolio optimiser should still determine how much risk it deserves.

## 9. Combine strategies correctly

Models predicting the same target may eventually be ensembled upstream.

Distinct strategies should remain distinct candidates and compete jointly for portfolio risk.

Net identical physical exposures before execution.

**Why:** averaging unrelated signals destroys their economic meaning, while portfolio optimisation naturally resolves competing opportunities.

## 10. Keep all learned decisions leakage-safe

Anything estimated using outcomes must occur inside the walk-forward framework:

* model fitting;
* rule expected-edge estimation;
* calibration;
* ensemble weights;
* thresholds;
* tuned portfolio parameters.

**Why:** an OOF alpha model is not sufficient if downstream decision rules were tuned using future outcomes.

## Implementation Order

1. Finalise target and primary horizon.
2. Add `TradeCandidate`.
3. Ensure exact position persistence through time.
4. Generate rolling ML candidates.
5. Convert PnL/WVega predictions to expected PnL per contract.
6. Implement convex portfolio optimisation.
7. Add costs and existing risk constraints.
8. Validate rolling re-optimisation.
9. Add one rule-based strategy using optional lifecycle fields.
10. Add exposure netting.
11. Only then consider more advanced risk/dynamic allocation logic.

### Guiding Principle

[
\boxed{
\text{Alpha determines expected opportunity; portfolio construction determines position size.}
}
]

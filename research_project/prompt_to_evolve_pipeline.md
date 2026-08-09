# QQQ Options ML Pipeline — Evolution Specification

## Objective

Evolve the existing QQQ 0–10 DTE options research pipeline into a point-in-time-correct, scalable supervised-ML framework that:

1. Generates a defined universe of tradeable option structures.
2. Predicts future P&L for each candidate structure over specified horizons.
3. Produces strictly walk-forward out-of-sample historical alpha forecasts.
4. Converts those forecasts into trades subject to:

   * explicit Greek risk limits;
   * transaction costs;
   * current portfolio state;
   * net contract exposures;
   * a configurable daily trading limit, currently expected to be approximately 8 trading instances/day.
5. Backtests those trades without look-ahead bias.
6. Separately evaluates model forecasting quality and final portfolio performance.

The existing architecture should be **extended rather than rewritten** wherever possible.

---

# Core Research Formulation

At prediction timestamp (t), candidate structure (a) is described by:

* current QQQ market state;
* volatility/surface state;
* structure characteristics;
* current fair value;
* Greeks and related risk exposures.

A horizon-specific regression model predicts:

[
\hat Y_{t,a,h}
==============

E[PnL_{t,a,h}\mid X_{t,a}]
]

where (Y) is the future P&L of **one standardized unit of that exact structure instance**.

The pricing engine fair value is assumed to be the executable option/structure price.

For the primary skew-delta-hedged target:

[
Y_{t,a,h}
=========

## V_{a,t+h}

V_{a,t}
+
PnL^{hedge}_{t:t+h}
-------------------

TC_{t,a,h}.
]

The same P&L, hedge, and cost conventions must be used consistently in label construction and backtesting.

Raw standardized-unit P&L should remain the canonical target. Risk/Greek-normalized targets may be investigated as alternative label specifications later.

---

# Architecture

```text
DataSources
    ↓
DataQualityLayer / CanonicalDataLayer
    ↓
StructureUniverse
    ↓
StructureResolver
    ↓
StructureInstances
    ↓
StructurePathBuilder
    ├────────────→ FeatureEngine
    └────────────→ LabelBuilder
                         ↑
                  StrategyPnLSpec

FeatureTable + LabelTable
    ↓
DatasetAssembler
    + sample weighting
    ↓
TemporalSplitter
    ↓
ModelTrainer
    ├── baseline models
    ├── Elastic Net
    ├── LightGBM
    ├── validation predictions
    ├── walk-forward OOS predictions
    └── final fitted model
    ↓
WalkForwardPredictionTable
    ↓
PortfolioConstructor
    + current portfolio
    + Greek limits
    + transaction costs
    + net contract exposures
    + trade budget
    ↓
BacktestEngine
    ↓
BacktestResult
    ↓
EvaluationEngine
```

---

# 1. Data Modules

## `DataSources`

Responsible only for loading the relevant raw data over a requested period.

No:

* feature logic;
* structure logic;
* model logic;
* strategy logic.

---

## `DataQualityLayer` / `CanonicalDataLayer`

Responsible for deterministic cleaning and canonicalization of market data.

Examples:

* timestamp/timezone normalization;
* market-session handling;
* duplicate removal;
* missing/invalid observation handling;
* stable identifiers;
* option/future alignment;
* data-quality flags.

Later modules should not independently implement market-data cleaning.

### Important

Do **not** place learned preprocessing here.

Operations such as:

* fitted scaling;
* fitted imputation;
* winsorization based on training distributions;
* PCA;
* feature selection;

belong inside the leakage-safe model-training pipeline and must be fitted separately within each training fold.

---

# 2. Structure Modules

## `StructureUniverse`

Defines the parameterized economic structures the strategy is permitted to consider.

Examples might include:

* outright calls/puts;
* verticals;
* straddles/strangles;
* butterflies;
* calendars;
* later, diagonals or additional approved structures.

Structures should be defined using economically meaningful parameters such as:

* DTE;
* delta/moneyness;
* strike width;
* wing width;
* front/back expiry;
* orientation.

Each definition should have a deterministic, reproducible identifier.

A structure definition describes an economic trade template, not specific contracts.

---

## `StructureResolver`

Given:

```text
StructureDefinition
+
selection timestamp
+
canonical market data
```

resolve the definition into the exact option contracts and quantities representing the structure **at that timestamp**.

Output an immutable `StructureInstance`, including:

```text
instance_id
structure_definition_id
selection_timestamp

resolved contracts
leg quantities
strikes
expiries
option types

entry fair value
entry Greeks
resolution metadata
```

### Critical invariant

Resolution occurs at a specific timestamp.

An existing `StructureInstance` is never re-resolved later.

If the same abstract definition resolves to different contracts at the next rebalance timestamp, that creates a **new instance**.

---

## `StructurePathBuilder`

Given a resolved `StructureInstance`, construct the subsequent value and Greek paths of those **same fixed contracts**.

Typical output:

```text
instance_id
timestamp

structure_value
delta
gamma
vega
theta
other required Greeks

QQQ future mid
validity / quality flags
```

The `StructurePathBuilder` should not repeatedly resolve the abstract structure through time.

Its output should be reusable by:

* `FeatureEngine`;
* `LabelBuilder`;
* `BacktestEngine`;
* diagnostic analysis.

---

# 3. Feature and Target Modules

## `FeatureEngine`

Construct point-in-time explanatory variables for the ML models.

Feature families may include:

### Market state

* QQQ future returns over multiple windows;
* realized volatility;
* realized range;
* momentum/reversal;
* intraday high/low position;
* time of day;
* activity/volume where available.

### Surface state

* ATM IV;
* skew;
* curvature;
* term structure;
* changes in IV/skew/term structure;
* realized versus implied volatility.

### Candidate characteristics

* structure family;
* DTE / time to expiry;
* front/back DTE;
* leg moneyness/delta;
* strike/expiry widths;
* fair value;
* delta;
* gamma;
* vega;
* theta;
* other reliable Greeks.

### Path-derived state

* recent change in structure value;
* recent Greek changes;
* recent structure return.

Features should be computed at their **natural/highest useful resolution**.

Each feature should retain sufficient metadata to enforce:

[
available_timestamp \le prediction_timestamp.
]

The `DatasetAssembler` selects the appropriate point-in-time values later.

---

## `LabelBuilder`

Construct future economic outcomes independently from features.

The canonical target should be future P&L per standardized structure unit.

For horizon (h):

[
Y_{t,a,h}
=========

## V_{a,t+h}

V_{a,t}
+
PnL^{hedge}_{t:t+h}
-------------------

TC.
]

Store the decomposition where possible:

```text
anchor_timestamp
instance_id
horizon
realization_end_timestamp

entry_structure_value
exit_structure_value

structure_pnl
hedge_pnl
transaction_cost
net_pnl

quality_flags
label_version
```

Generate several configurable horizons, for example:

```text
15m
30m
60m
2h
EOD
1 trading day
```

Initially train/evaluate each horizon independently.

Normalized labels such as PnL-per-vega or PnL-per-risk may be implemented as additional `LabelSpec`s, but should not replace raw P&L as the canonical research target.

---

## `StrategyPnLSpec`

Maintain a shared versioned specification describing the economic assumptions used by both labels and backtests.

For example:

```text
target horizon
fair-value execution convention
hedge policy
hedge frequency
delta definition
transaction-cost model
expiry handling
```

This prevents training on one economic strategy and backtesting another.

---

## `DatasetAssembler`

Convert independently created features and labels into point-in-time-correct trainable candidate panels.

Responsibilities:

1. Determine eligible sample timestamps.
2. Determine eligible structure instances.
3. Point-in-time join features.
4. Enforce availability/staleness rules.
5. Attach the requested target.
6. Apply data-quality filters.
7. Attach candidate metadata.
8. Assign model-training sample weights.

Conceptual row:

```text
decision_timestamp
instance_id

market features...
surface features...
candidate features...

target_pnl
sample_weight
```

### Sample weighting

Candidates available at the same timestamp are highly correlated.

If (N_t) candidates are present at timestamp (t), initially use:

[
w_{t,a}=\frac{1}{N_t}.
]

This prevents timestamps with larger candidate universes from disproportionately dominating the fitted loss.

Family balancing may be considered later if candidate enumeration is heavily skewed toward particular structure families.

---

# 4. Temporal Validation

## `TemporalSplitter`

Own the common leakage-safe walk-forward folds used by all trainable models.

Support:

```text
training window
validation window
test window
purging
embargo
```

Because labels overlap through time:

[
purge_window
\ge
maximum\ label\ horizon.
]

All learned preprocessing must be fitted using training data only.

The same folds should be used when comparing Elastic Net, LightGBM, and future models.

---

# 5. Signal Model Modules

## `AlphaModel`

Represents the forecasting model itself.

Common conceptual interface:

```text
fit(X, y, sample_weight)
predict(X)
```

For regression, the output is a numeric forecast:

[
\hat\mu_{t,a,h}
===============

\widehat{E}[PnL_{t,a,h}\mid X_{t,a}].
]

It should **not** directly output buy/sell/hold.

Example:

```text
Calendar        +0.11 expected 60m PnL
Put vertical    +0.04 expected 60m PnL
Straddle        -0.03 expected 60m PnL
```

The portfolio layer determines whether those forecasts justify actual trades.

Rule-based alpha models should preferably expose the same numeric-score interface.

---

## Structure representation in pooled models

The initial/default approach should be:

> Train one pooled model per forecast horizon across multiple structure types.

The model differentiates structures through economic descriptors such as:

```text
structure_family
DTE
front/back DTE
moneyness
width
fair value
delta
gamma
vega
theta
...
```

Do **not** make a high-cardinality exact `structure_id` a mandatory model input.

For Elastic Net:

* one-hot encode coarse `structure_family`;
* include numeric structure descriptors;
* optionally add a small number of economically motivated interactions.

For LightGBM:

* use structure family as categorical where appropriate;
* supply the numeric economic descriptors directly.

Only move toward family-specific models if walk-forward OOS evidence shows that pooling harms prediction quality.

Model ensembles are a later research option rather than an architectural assumption.

---

## `ModelTrainer`

Responsible for all trainable-model research logic.

Responsibilities include:

* fold-local preprocessing;
* model fitting;
* hyperparameter selection;
* validation;
* walk-forward prediction generation;
* model/version tracking;
* final production-model fitting.

It should produce three conceptually different artifacts:

### Validation predictions

Used for selecting:

* model hyperparameters;
* feature configurations;
* potentially portfolio-policy parameters.

### `WalkForwardPredictionTable`

Strictly OOS historical alpha predictions.

These are the forecasts used for final historical portfolio construction and backtesting.

Each row should contain provenance such as:

```text
decision_timestamp
instance_id
prediction_horizon
predicted_pnl

model_name
model_version
fold_id
model_train_start
model_train_end
```

### Final fitted model

After the research choices are fixed, fit the selected model on all permissible historical data.

This model is used for genuinely future/live predictions.

It must not be used to generate fitted historical predictions and then treat those predictions as backtest results.

---

# 6. Portfolio Construction

## `PortfolioConstructor`

Convert numeric candidate-level alpha forecasts and current portfolio state into feasible trades/target holdings.

Inputs should include:

```text
current portfolio
candidate predicted PnLs
candidate/portfolio Greeks
risk limits
transaction costs
remaining daily trade capacity
```

Initially use a simple, transparent policy rather than sophisticated portfolio optimization.

Possible first implementation:

1. Remove candidates below a minimum expected-PnL threshold.
2. Rank the remaining candidates.
3. Optionally compare predicted PnL to risk usage.
4. Consider candidates sequentially.
5. Convert selected structures into actual contract positions.
6. Net overlapping contract exposures.
7. Recalculate portfolio Greeks.
8. Reject changes violating hard risk limits.
9. Reject changes whose expected benefit does not justify transaction costs.
10. Enforce position/trading limits.
11. Stop when no sufficiently attractive feasible opportunities remain.

### Risk

Greek limits are hard portfolio constraints and should remain outside the ML model.

Only implement the risk measures actually required by the mandate initially.

Do not begin with a complex covariance optimizer.

---

## Contract netting

Candidate structures are useful alpha/research representations.

The actual portfolio owns contracts.

Therefore:

```text
selected candidate allocations
    ↓
net contract quantities
    ↓
portfolio Greeks
    ↓
trades / transaction costs
```

All final risk and accounting should use the net contract portfolio.

---

## Daily trading limit

Represent the daily trading capacity explicitly:

```text
TradeBudgetPolicy
    max_trade_events_per_day
    counting_method
    risk_reduction_exempt
```

Do not hard-code `8`.

Initially treat the limit as a simple hard constraint.

Track whether it actually binds.

Only introduce time-of-day/trades-remaining-dependent thresholds if OOS evidence shows that early mediocre trades frequently displace materially better later opportunities.

Do not initially implement reinforcement learning or dynamic programming.

---

# 7. Portfolio-Policy Leakage

OOF/OOS model forecasts alone are not sufficient to guarantee a clean strategy backtest.

Any portfolio parameter chosen from data can also overfit, for example:

```text
minimum alpha threshold
risk-normalization formula
position-size parameter
redundancy threshold
time-of-day threshold
```

Therefore each walk-forward outer fold should conceptually follow:

```text
TRAIN
    fit candidate models

VALIDATION
    select model configuration
    select/tune portfolio-policy parameters

TRAIN + VALIDATION
    refit selected model

TEST
    generate untouched OOS forecasts
    apply already-selected portfolio policy
    record strategy PnL
```

The test period must not be used to choose model or portfolio-policy parameters whose performance is subsequently reported on that same period.

---

# 8. Holding Horizon

Initially align the trading strategy with the model target.

For example:

```text
60m model
→ predicts 60m PnL
→ initial strategy holds approximately 60m
```

Do not immediately train on fixed 60-minute outcomes while allowing an unconstrained dynamic exit policy.

Risk-driven exits remain permissible.

Dynamic exits and multi-horizon selection can become later research questions after fixed-horizon forecast skill is established.

---

# 9. `BacktestEngine`

The backtester should be mechanical rather than evaluative.

Responsibilities:

* maintain positions;
* mark holdings through time;
* perform portfolio-level hedge accounting;
* process target changes/trades;
* apply transaction costs;
* maintain net contract positions;
* maintain risk state;
* track daily trade usage;
* calculate portfolio P&L.

Outputs should include:

```text
PortfolioHistory
TradeLedger
PnLLedger
RiskHistory
DecisionHistory
```

The decision history should retain:

```text
candidate prediction
candidate rank
accepted/rejected
rejection reason
risk before/after
trade capacity before/after
```

Do not calculate headline performance statistics inside the backtester.

---

# 10. `EvaluationEngine`

Evaluate the forecasting and trading layers separately.

## Forecast evaluation

Using the concatenated walk-forward OOS prediction table:

* cross-sectional Spearman rank IC;
* realized PnL by prediction decile;
* top 10% / top 5% realized PnL;
* forecast calibration;
* MAE/RMSE as secondary diagnostics;
* stability by fold/month;
* DTE;
* structure family;
* time of day;
* market regime where useful.

The primary question is:

> Do higher predicted PnLs reliably correspond to better realized candidate PnLs?

Compare at minimum:

```text
simple historical/group baseline
Elastic Net
LightGBM
```

## Strategy evaluation

Measure:

* gross/net PnL;
* Sharpe;
* drawdown;
* turnover;
* transaction costs;
* Greek utilization;
* risk-limit binding frequency;
* trade-budget utilization;
* rejected alpha because of trade budget;
* PnL by structure;
* PnL by DTE;
* PnL by time of day.

Also evaluate performance using approximately:

```text
1
2
4
8
16
```

trade opportunities per day.

This reveals whether the expected eight-trade daily limit is genuinely economically binding.

---

# 11. Implementation Priorities

## Phase 1 — Inspect and map the existing codebase

Before modifying architecture:

* map existing domain objects;
* inspect structure resolution/path semantics;
* inspect features/labels;
* inspect dataset joins;
* inspect temporal splitting;
* inspect current AlphaModel/training logic;
* inspect TradingPolicy;
* inspect transaction-cost and P&L accounting;
* inspect existing caching/versioning.

Reuse existing abstractions wherever their semantics already match this specification.

---

## Phase 2 — Correct candidate/label pipeline

Ensure that for an arbitrary timestamp and structure the system can reproduce:

```text
abstract structure definition
→ exact resolved contracts
→ entry fair value
→ fixed-contract future path
→ Greek path
→ hedge path
→ transaction costs
→ final target
```

This should be fully unit-tested before serious ML work.

---

## Phase 3 — Build the supervised candidate panel

Implement/verify:

* market features;
* surface features;
* candidate descriptors;
* PIT feature joins;
* sample weighting;
* multiple target horizons;
* temporal folds.

---

## Phase 4 — Establish ML baselines

For one initial horizon first:

```text
simple baseline
Elastic Net
LightGBM
```

Produce genuine walk-forward OOS predictions.

Do not build a sophisticated portfolio system until there is demonstrable OOS candidate-level forecast skill.

---

## Phase 5 — Simple constrained portfolio

Add:

* minimum expected-PnL threshold;
* candidate ranking;
* simple risk-adjusted ranking if useful;
* contract netting;
* hard Greek limits;
* transaction costs;
* daily trade budget;
* fixed-horizon position management.

---

## Phase 6 — Evaluate and identify the real bottleneck

Only add sophistication based on observed evidence.

If:

* forecast skill is weak → improve labels/features/models;
* pooled models struggle → test broad family-specific models;
* portfolio logic destroys strong alpha → improve construction;
* trade budget binds → improve time-dependent trade selection;
* risk limits dominate → improve risk-aware portfolio construction.

---

# 12. Explicitly Defer

Until stable incremental OOS ML alpha is demonstrated, do not prioritize:

* large covariance models;
* mean-variance optimization;
* sophisticated scenario optimizers;
* deep neural networks;
* transformers;
* reinforcement learning;
* contextual bandits;
* dynamic programming for trade allocation;
* ML execution/fill models;
* complex ensembles;
* automatic horizon selection;
* highly specialized per-structure models.

---

# Final Design Principle

The evolved pipeline should answer, in order:

```text
1. What structures could have been traded at timestamp t?
2. What exact contracts represented each structure?
3. What information was genuinely available at t?
4. What future PnL did one unit of each structure realize?
5. Can a model predict those outcomes out of sample?
6. Which predicted opportunities are worth taking?
7. Which trades satisfy portfolio risk limits?
8. Which trades are worth consuming scarce daily trading capacity?
9. What net contracts and hedge result?
10. What portfolio PnL was actually realized?
11. Was performance generated by genuine forecast skill or by downstream policy choices?
```

The key architectural separation is:

[
\boxed{
\text{AlphaModel forecasts opportunity}
\rightarrow
\text{PortfolioConstructor selects feasible trades}
\rightarrow
\text{BacktestEngine accounts for them}
\rightarrow
\text{EvaluationEngine judges the result}
}
]

Historical portfolio/backtest research must consume only **walk-forward OOS predictions produced by models that did not train on the observations they predict**.

The goal is to evolve the current pipeline by the minimum amount necessary to achieve this correctly and reproducibly, while preserving existing code and abstractions wherever possible.

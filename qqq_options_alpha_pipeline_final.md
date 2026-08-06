# QQQ 0–10 DTE Options Alpha Research Pipeline

## Objective

Build a modular, scalable, and research-friendly pipeline for 15-minute QQQ options data that supports:

- Dynamic option-structure selection and rebalancing
- Features computed at different frequencies
- Multiple prediction targets and horizons
- Rule-based or trainable alpha strategies
- Walk-forward cross-validation
- Point-in-time-correct backtesting
- Fixed transaction costs
- Fast iteration without unnecessary abstraction

---

## Final Architecture

```text
RawDataSource
    ↓
CanonicalDataLayer
    ↓
StructureCatalogue + StructureResolver
    ↓
StructurePathBuilder
    ├────────→ FeatureEngine
    └────────→ LabelBuilder

FeatureTable + LabelTable
    ↓
DatasetAssembler
    ├── SampleSchedule
    ├── Feature alignment rules
    ├── Label specifications
    └── TemporalSplitter
    ↓
AlphaEngine.fit

FeatureTable
    ↓
PredictionSchedule
    ↓
AlphaEngine.predict
    ↓
TradingPolicy
    ↓
RebalanceSchedule
    ↓
BacktestEngine
    ↓
EvaluationEngine
```

`DataProductStore` is a cross-cutting service for caching, versioning, lineage, and retrieval.

For a fixed rule-based strategy, `LabelBuilder`, `DatasetAssembler`, and `fit` may be skipped.

---

## 1. RawDataSource

**Responsibility:** Load source-specific data without applying feature, structure, or strategy logic.

**Outputs:** Raw option data, underlying data, contract metadata, calendars, and any additional feeds.

---

## 2. CanonicalDataLayer

**Responsibility:** Normalize raw feeds into consistent, point-in-time-correct market data.

Handles:

- Timestamps and time zones
- Stable contract identifiers
- Missing, duplicate, or invalid observations
- Market-session filtering
- Option and underlying alignment
- Data-quality flags
- Explicit availability timestamps

**Output:** Versioned canonical market tables.

---

## 3. StructureCatalogue

**Responsibility:** Define abstract tradeable structures.

Examples:

- ATM call
- Delta-targeted put
- Straddle
- Vertical spread
- Constant-DTE or constant-moneyness structure

A `StructureDefinition` contains leg quantities, expiry and strike rules, and eligibility constraints. It contains no concrete contracts or strategy logic.

---

## 4. StructureResolver

**Responsibility:** Resolve a `StructureDefinition` into concrete contracts at a selection or rebalance timestamp.

**Output:** An immutable `StructureInstance` containing:

```text
instance_id
definition_id
selection_timestamp
resolved legs and quantities
resolution metadata
```

The same definition may resolve to a different instance at the next rebalance.

---

## 5. StructurePathBuilder

**Responsibility:** Build the value path of each fixed `StructureInstance`.

\[
V_{s,t} = \sum_i q_i M_i P_{i,t}
\]

Typical output:

```text
instance_id
timestamp
structure_value
interval_value_change
underlying_mid
DTE
is_valid
quality_flags
```

The path builder:

- Tracks fixed contracts within an instance
- Does not re-resolve contracts within a path
- Does not assume the strategy holds the structure
- Does not calculate cumulative strategy P&L

Structure paths are reusable inputs to selected features, labels, and backtesting.

---

## 6. FeatureEngine

**Responsibility:** Compute point-in-time explanatory inputs from declared dependencies.

Each feature declares:

```text
name
version
required inputs
calculation frequency
lookback
availability lag
maximum age
parameters
```

Examples:

```text
UnderlyingReturnFeature
    requires: canonical_underlying
    frequency: 15 minutes

OptionSkewFeature
    requires: canonical_options
    frequency: 30 minutes

StructureMomentumFeature
    requires: structure_paths
    frequency: 15 minutes
```

Features are computed on their natural clocks. At a sample or prediction timestamp, downstream logic uses the latest value satisfying:

```text
available_timestamp <= decision_timestamp
feature_age <= maximum_age
```

`StructurePathTable` is optional and used only by features that require it.

---

## 7. LabelBuilder

**Responsibility:** Independently construct forward-looking outcomes.

Each `LabelSpec` defines:

```text
name
horizon
calculation
parameters
version
```

Examples:

- Forward P&L over 15, 30, and 60 minutes
- Forward return
- Positive-P&L indicator
- Maximum favorable excursion
- Maximum adverse excursion

Typical output:

```text
anchor_timestamp
candidate_id
label_name
horizon
realization_end_timestamp
label_value
```

Labels must never enter the live feature or prediction path.

---

## 8. Schedules

Use separate lightweight schedules rather than one global decision schedule.

### SampleSchedule

Defines which timestamp-candidate rows are eligible for training and evaluation.

### PredictionSchedule

Defines when the `AlphaEngine` generates predictions.

### RebalanceSchedule

Defines when portfolio holdings may change.

These may be identical, but they should remain independently configurable.

Example:

```text
Data frequency:        15 minutes
Feature frequencies:   15 minutes, 30 minutes, daily
Training samples:      every 30 minutes
Predictions:           every 15 minutes
Rebalancing:           every 30 minutes
Label horizons:        15, 30, and 60 minutes
```

---

## 9. DatasetAssembler

**Responsibility:** Align independently generated features and labels into trainable datasets.

It:

1. Generates eligible anchor timestamps from the `SampleSchedule`
2. Performs point-in-time as-of feature joins
3. Enforces feature staleness limits
4. Joins one or more labels on explicit keys
5. Applies quality and candidate filters
6. Creates chronological train, validation, and test datasets
7. Prevents leakage from overlapping label horizons

**Output:**

```text
TrainingDataset
ValidationDataset
TestDataset
```

Multiple labels may be represented as separate targets or as one vector-valued target.

---

## 10. TemporalSplitter

**Responsibility:** Define walk-forward train, validation, and test folds.

Supports:

- Rolling training windows
- Expanding training windows
- Validation windows
- Test windows
- Step size
- Purging
- Embargoes

Example:

```text
Fold 1: Train Jan–Jun, Validate Jul, Test Aug
Fold 2: Train Feb–Jul, Validate Aug, Test Sep
Fold 3: Train Mar–Aug, Validate Sep, Test Oct
```

Training observations whose label-realization windows cross a split boundary must be removed.

A practical minimum is:

```text
purge_window >= maximum selected label horizon
```

Any learned preprocessing—such as scaling, imputation, winsorization, feature selection, or dimensionality reduction—must be fitted separately within each fold.

---

## 11. AlphaEngine

**Responsibility:** Convert point-in-time inputs into signals, scores, rankings, or forecasts.

It may be:

- A fitted statistical or machine-learning model
- A tunable rule
- A fixed deterministic rule-based strategy

Common interface:

```text
fit(training_dataset)     # optional or no-op for fixed rules
predict(feature_rows)
```

It may produce:

- One prediction per target
- Multiple horizon-specific predictions
- A vector of predictions from one multi-output model
- A rule-based signal and intended holding horizon

Typical output:

```text
decision_timestamp
candidate_id
prediction_name
prediction_horizon
prediction_value
alpha_version
```

The alpha engine does not resolve contracts, manage positions, apply costs, or calculate strategy P&L.

---

## 12. TradingPolicy

**Responsibility:** Convert alpha outputs and current portfolio state into target holdings.

Controls:

- Entry and exit rules
- Candidate selection
- Position sizing
- Holding and overlap constraints
- Turnover controls
- Rebalance behaviour

**Output:**

```text
rebalance_timestamp
instance_id
target_quantity
decision_reason
```

The `AlphaEngine` estimates attractiveness; the `TradingPolicy` determines what should be held.

---

## 13. CostModel

**Responsibility:** Calculate transaction costs from actual position changes.

Initial implementation may use a fixed cost per contract, leg, structure, or side.

No cost is charged when holdings do not change.

---

## 14. BacktestEngine

**Responsibility:** Simulate holdings and P&L through time.

At each rebalance timestamp:

1. Mark current holdings using their existing structure instances
2. Calculate interval P&L
3. Obtain target holdings
4. Calculate required position changes
5. Apply transaction costs
6. Update holdings
7. Record portfolio state

\[
\text{PnL}_k =
q_k M \left(V_{s_k,t_{k+1}} - V_{s_k,t_k}\right) - TC_k
\]

Guarantees:

- P&L is earned on the contracts held during the interval
- New instances contribute only after rebalancing
- Contract rolls do not create artificial P&L
- Costs are applied once to actual position changes
- Feature, label, and training logic remain outside the engine

---

## 15. EvaluationEngine

**Responsibility:** Evaluate alpha quality and completed strategy results.

Examples:

- Gross and net P&L
- Sharpe ratio and drawdown
- Hit rate
- Turnover and transaction costs
- Performance by DTE, structure, time of day, and rebalance frequency
- Prediction ranking and calibration
- Train, validation, test, and fold stability

Walk-forward evaluation should concatenate out-of-sample predictions and P&L chronologically to form the primary OOS result.

---

## Cross-Cutting DataProductStore

**Responsibility:** Version, cache, and retrieve reusable outputs.

Typical products:

```text
canonical market data
structure instances
structure paths
features
labels
training datasets
predictions
target positions
backtest results
```

Each product should record its name, version, lineage, configuration, date range, and point-in-time semantics.

Keep this lightweight: typed tables, metadata, deterministic identifiers, and efficient columnar storage are sufficient initially.

---

## Core Domain Objects

```text
CanonicalMarketData
StructureDefinition
StructureInstance
StructurePath
FeatureTable
LabelTable
TrainingDataset
SignalTable
TargetPortfolio
PortfolioState
BacktestResult
```

These objects should have explicit schemas, stable join keys, version metadata, and preferably immutable semantics.

---

## Design Principles

- Features and labels are built independently.
- Features are computed on their natural frequencies.
- Labels may have multiple independent target horizons.
- Temporal alignment occurs only during dataset or prediction-row assembly.
- Sample, prediction, and rebalance schedules remain separate.
- Walk-forward splits are chronological and leakage-aware.
- Rule-based strategies may bypass labels and model fitting.
- Generic dependency-driven interfaces suit features, labels, and metrics.
- Structure resolution, valuation, policy decisions, and accounting remain explicit domain modules.
- Prefer typed tables, pure functions, composition, and configuration over deep inheritance.
- Cache expensive reusable products and version every experiment.
- Enforce point-in-time correctness centrally.
- Return explicit failures and quality flags.

---

## Final Summary

```text
Load and normalize market data
→ Define and resolve tradeable structures
→ Build fixed-contract structure paths
→ Independently compute multi-frequency features
→ Independently compute multiple forward labels
→ Assemble point-in-time training rows at eligible timestamps
→ Apply walk-forward train, validation, and test splits
→ Fit a trainable alpha engine, or use a rule-based engine
→ Generate predictions at configured prediction timestamps
→ Convert predictions into target holdings
→ Rebalance at configured rebalance timestamps
→ Calculate portfolio P&L and costs
→ Evaluate concatenated out-of-sample results
```

The critical separation is:

> `FeatureEngine` describes information available at a timestamp; `LabelBuilder` describes future outcomes; `DatasetAssembler` aligns them; `TemporalSplitter` creates leakage-safe walk-forward folds; `AlphaEngine` generates signals; `TradingPolicy` selects holdings; and `BacktestEngine` accounts for the resulting P&L.

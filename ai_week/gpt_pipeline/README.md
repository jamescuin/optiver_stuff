# Minimal earnings-call forecasting pipeline

## Agreed architecture

```text
Canonical ground-truth event dataset
        |
        v
FeatureEngineeringModule.transform(...)
        |
        v
identifiers + split + unchanged targets + X_1 ... X_N
        |
        v
WalkForwardTrainingPipeline.run(feature_data, model)
        |
        v
trained model + metrics per fold + aggregate OOF metrics + OOF predictions
```

## Ground-truth input

One row per earnings-call event:

```text
sample_id, event_id, underlying_id, event_timestamp, split
NEWS_history, TRANSCRIPT_history, PRICE_history, CONSENSUS_history
TARGET_pct_change, TARGET_revenue_call
```

`TARGET_revenue_call` may remain missing until the separate extraction process populates it.
Rows with missing `TARGET_pct_change` are retained in the canonical dataset but excluded from supervised price-model training.

## Feature-engineering output

```text
sample_id, event_id, underlying_id, event_timestamp, split
TARGET_pct_change, TARGET_revenue_call
X_1, ..., X_N
```

Feature engineering preserves identifiers and targets exactly. Features may be numeric, text, embeddings stored as objects, or categorical values, provided the selected model adapter can consume them.

Only point-in-time-valid information may be used. Learned transforms such as TF-IDF vocabularies, PCA, scaling, feature selection, and target encodings should usually live inside the model's training pipeline so they are fitted separately within each fold.

## Model contract

Models do not need an sklearn-style `.fit()` method. They implement:

```python
model.prepare(training_data, feature_columns, target_column)
model.predict(data, feature_columns)
```

`prepare()` may:

- call `.fit()` on an sklearn estimator;
- initialise a frozen zero-shot LLM and do nothing else;
- select few-shot examples from the training fold;
- fit a calibration layer;
- load an externally trained checkpoint.

This keeps the walk-forward trainer model-agnostic.

## Baseline: last consensus revenue

```python
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline

from earnings_pipeline import (
    ColumnFeatureEngineeringModule,
    DatasetContract,
    SklearnModelAdapter,
    WalkForwardTrainingPipeline,
    last_revenue_consensus_builder,
)

contract = DatasetContract()

feature_module = ColumnFeatureEngineeringModule(
    contract=contract,
    builders={
        "X_last_revenue_consensus": last_revenue_consensus_builder(contract),
    },
)
feature_data = feature_module.transform(ground_truth_df)

baseline = SklearnModelAdapter(
    estimator=make_pipeline(
        SimpleImputer(strategy="median"),
        LinearRegression(),
    ),
    name="last_consensus_linear_regression",
)

trainer = WalkForwardTrainingPipeline(contract, n_splits=5, gap=0)
result = trainer.run(
    feature_data,
    baseline,
    feature_columns=["X_last_revenue_consensus"],
)

print(result.fold_metrics)
print(result.aggregate_validation_metrics)
```

## Frozen LLM forecast from the latest transcript

```python
from earnings_pipeline import (
    ColumnFeatureEngineeringModule,
    DatasetContract,
    LLMTranscriptModel,
    WalkForwardTrainingPipeline,
    latest_transcript_builder,
)

contract = DatasetContract()
feature_module = ColumnFeatureEngineeringModule(
    contract=contract,
    builders={
        "X_latest_transcript": latest_transcript_builder(contract),
    },
)
feature_data = feature_module.transform(ground_truth_df)

# Implement this using your preferred provider. It must return a decimal return.
def llm_predictor(transcript: str) -> float:
    # Example: +2.5% => 0.025
    raise NotImplementedError

llm_model = LLMTranscriptModel(predictor=llm_predictor)
trainer = WalkForwardTrainingPipeline(contract, n_splits=5)

# No .fit() is called on the LLM. prepare() is a no-op.
result = trainer.run(feature_data, llm_model, online_feedback=False)
print(result.fold_metrics)
```

## Online feedback for the LLM

```python
llm_model = LLMTranscriptModel(
    predictor=llm_predictor,
    online_learning_rate=0.05,
)

result = trainer.run(
    feature_data,
    llm_model,
    online_feedback=True,
)
```

Within each validation fold, evaluation is strictly prequential:

```text
predict event t -> record prediction -> reveal target t -> update -> event t+1
```

Metrics are still produced for every fold. Label these results `prequential_online`; they are not directly equivalent to static frozen-model validation because later observations in a validation fold benefit from earlier revealed labels.

## Outputs

`TrainingResult` contains:

```text
trained_model
fold_metrics
aggregate_validation_metrics
out_of_fold_predictions
feature_columns
target_column
validation_mode
```

The final model is prepared on all labelled development rows after CV. Holdout prediction is performed once and does not update the model:

```python
holdout_predictions = trainer.predict_holdout(feature_data, result)
```

## Parallel ownership

- Feature team: `ground_truth_df -> identifiers + targets + X_*`
- Model team: `prepare(...)`, `predict(...)`, optional `update_after_prediction(...)`
- Training team: chronological folds, cloning, OOF predictions, final preparation
- Evaluation team: `sample_id, fold, y_true, y_pred -> metrics`

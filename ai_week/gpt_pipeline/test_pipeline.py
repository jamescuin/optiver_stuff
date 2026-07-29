import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from earnings_pipeline import (
    ColumnFeatureEngineeringModule,
    DatasetContract,
    LLMTranscriptModel,
    SklearnModelAdapter,
    WalkForwardTrainingPipeline,
)


def make_feature_data(n_train: int = 18, n_holdout: int = 3) -> pd.DataFrame:
    n = n_train + n_holdout
    x = np.arange(n, dtype=float)
    return pd.DataFrame(
        {
            "sample_id": [f"s{i}" for i in range(n)],
            "event_id": [f"e{i}" for i in range(n)],
            "underlying_id": ["ABC"] * n,
            "event_timestamp": pd.date_range("2020-01-01", periods=n, freq="D"),
            "split": ["train"] * n_train + ["holdout"] * n_holdout,
            "TARGET_pct_change": 0.01 * x + 0.1,
            "TARGET_revenue_call": [np.nan] * n,
            "X_signal": x,
            "X_latest_transcript": [f"transcript {i}" for i in range(n)],
        }
    )


def test_sklearn_walk_forward_returns_each_fold():
    contract = DatasetContract()
    data = make_feature_data()
    model = SklearnModelAdapter(LinearRegression(), name="linear")
    result = WalkForwardTrainingPipeline(contract, n_splits=3).run(
        data, model, feature_columns=["X_signal"]
    )
    assert len(result.fold_metrics) == 3
    assert set(result.out_of_fold_predictions["fold"]) == {1, 2, 3}
    assert result.aggregate_validation_metrics["mae"] < 1e-10


def test_llm_requires_no_fit_and_has_fold_metrics():
    contract = DatasetContract()
    data = make_feature_data()
    model = LLMTranscriptModel(predictor=lambda _: 0.0)
    result = WalkForwardTrainingPipeline(contract, n_splits=3).run(data, model)
    assert len(result.fold_metrics) == 3
    assert result.validation_mode == "static_walk_forward"


def test_online_llm_is_prequential():
    contract = DatasetContract()
    data = make_feature_data()
    model = LLMTranscriptModel(
        predictor=lambda _: 0.0,
        online_learning_rate=0.5,
    )
    result = WalkForwardTrainingPipeline(contract, n_splits=3).run(
        data, model, online_feedback=True
    )
    assert len(result.fold_metrics) == 3
    assert result.validation_mode == "prequential_online"

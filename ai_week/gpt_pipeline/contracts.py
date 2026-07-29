from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol, Sequence

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class DatasetContract:
    """Column names for the canonical event-level ground-truth dataset."""

    sample_id: str = "sample_id"
    event_id: str = "event_id"
    underlying_id: str = "underlying_id"
    event_timestamp: str = "event_timestamp"
    split: str = "split"

    news_history: str = "NEWS_history"
    transcript_history: str = "TRANSCRIPT_history"
    price_history: str = "PRICE_history"
    consensus_history: str = "CONSENSUS_history"

    target_pct_change: str = "TARGET_pct_change"
    target_revenue_call: str = "TARGET_revenue_call"

    train_value: str = "train"
    holdout_value: str = "holdout"
    feature_prefix: str = "X_"

    @property
    def identifier_columns(self) -> list[str]:
        return [
            self.sample_id,
            self.event_id,
            self.underlying_id,
            self.event_timestamp,
            self.split,
        ]

    @property
    def target_columns(self) -> list[str]:
        return [self.target_pct_change, self.target_revenue_call]

    @property
    def history_columns(self) -> list[str]:
        return [
            self.news_history,
            self.transcript_history,
            self.price_history,
            self.consensus_history,
        ]

    @property
    def required_columns(self) -> list[str]:
        return self.identifier_columns + self.history_columns + self.target_columns

    def validate_ground_truth(self, df: pd.DataFrame) -> None:
        missing = [column for column in self.required_columns if column not in df.columns]
        if missing:
            raise ValueError(f"Ground-truth dataset is missing columns: {missing}")
        if df[self.sample_id].duplicated().any():
            raise ValueError(f"{self.sample_id!r} must be unique.")
        invalid_splits = set(df[self.split].dropna().unique()) - {
            self.train_value,
            self.holdout_value,
        }
        if invalid_splits:
            raise ValueError(f"Unexpected split values: {sorted(invalid_splits)}")

    def validate_feature_dataset(self, df: pd.DataFrame) -> list[str]:
        required = self.identifier_columns + self.target_columns
        missing = [column for column in required if column not in df.columns]
        if missing:
            raise ValueError(f"Feature dataset is missing columns: {missing}")
        feature_columns = [
            column for column in df.columns if column.startswith(self.feature_prefix)
        ]
        if not feature_columns:
            raise ValueError(
                f"Feature dataset must contain at least one {self.feature_prefix!r} column."
            )
        if df[self.sample_id].duplicated().any():
            raise ValueError(f"{self.sample_id!r} must be unique.")
        return feature_columns


class FeatureEngineeringModule(Protocol):
    """
    Input: canonical ground-truth DataFrame.
    Output: identifiers + split + unchanged targets + X_* feature columns.
    """

    def transform(self, ground_truth: pd.DataFrame) -> pd.DataFrame:
        ...


class ForecastModel(Protocol):
    """
    Generic forecasting adapter.

    prepare() may fit an sklearn estimator, select few-shot examples, initialise
    an LLM prompt, fit a calibration layer, or do nothing for a frozen predictor.
    """

    name: str

    def clone(self) -> "ForecastModel":
        ...

    def prepare(
        self,
        training_data: pd.DataFrame,
        feature_columns: Sequence[str],
        target_column: str,
    ) -> None:
        ...

    def predict(
        self,
        data: pd.DataFrame,
        feature_columns: Sequence[str],
    ) -> np.ndarray:
        ...


class OnlineForecastModel(ForecastModel, Protocol):
    """Optional extension for predict-then-update online models."""

    def update_after_prediction(self, y_true: float, y_pred: float) -> None:
        ...


@dataclass
class TrainingResult:
    trained_model: ForecastModel
    fold_metrics: pd.DataFrame
    aggregate_validation_metrics: dict[str, float]
    out_of_fold_predictions: pd.DataFrame
    feature_columns: list[str]
    target_column: str
    validation_mode: str


FeatureBuilder = Callable[[pd.Series], Any]

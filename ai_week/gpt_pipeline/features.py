from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

import pandas as pd

from .contracts import DatasetContract, FeatureBuilder, FeatureEngineeringModule


def _normalise_history(value: Any) -> list[dict[str, Any]]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return []
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


@dataclass
class ColumnFeatureEngineeringModule(FeatureEngineeringModule):
    """
    Minimal feature module.

    Each builder receives one ground-truth row and returns one scalar, text value,
    embedding object, or other model-consumable value. Output columns must start X_.
    """

    contract: DatasetContract
    builders: Mapping[str, FeatureBuilder]

    def __post_init__(self) -> None:
        invalid = [
            name
            for name in self.builders
            if not name.startswith(self.contract.feature_prefix)
        ]
        if invalid:
            raise ValueError(f"Feature names must start with X_: {invalid}")

    def transform(self, ground_truth: pd.DataFrame) -> pd.DataFrame:
        self.contract.validate_ground_truth(ground_truth)

        output_columns = self.contract.identifier_columns + self.contract.target_columns
        output = ground_truth[output_columns].copy()

        for feature_name, builder in self.builders.items():
            output[feature_name] = ground_truth.apply(builder, axis=1)

        self.contract.validate_feature_dataset(output)
        return output


def last_revenue_consensus_builder(
    contract: DatasetContract,
    *,
    metric_keys: tuple[str, ...] = ("metric", "name", "field"),
    value_keys: tuple[str, ...] = ("value", "consensus", "estimate"),
    timestamp_keys: tuple[str, ...] = ("observed_at", "timestamp", "date"),
) -> FeatureBuilder:
    """Reference builder for X_last_revenue_consensus."""

    def build(row: pd.Series) -> float:
        event_time = pd.to_datetime(row[contract.event_timestamp], utc=True)
        records = _normalise_history(row[contract.consensus_history])
        candidates: list[tuple[pd.Timestamp, float]] = []

        for record in records:
            metric = next((record.get(key) for key in metric_keys if key in record), None)
            if metric is None or "revenue" not in str(metric).lower():
                continue

            value = next((record.get(key) for key in value_keys if key in record), None)
            timestamp = next(
                (record.get(key) for key in timestamp_keys if key in record), None
            )
            if value is None or timestamp is None:
                continue

            observed_at = pd.to_datetime(timestamp, utc=True, errors="coerce")
            numeric_value = pd.to_numeric(value, errors="coerce")
            if pd.isna(observed_at) or pd.isna(numeric_value):
                continue
            if observed_at <= event_time:
                candidates.append((observed_at, float(numeric_value)))

        if not candidates:
            return float("nan")
        return max(candidates, key=lambda item: item[0])[1]

    return build


def latest_transcript_builder(
    contract: DatasetContract,
    *,
    text_keys: tuple[str, ...] = ("text", "body", "transcript"),
    timestamp_keys: tuple[str, ...] = ("event_timestamp", "published_at", "timestamp"),
) -> FeatureBuilder:
    """Reference builder for X_latest_transcript with point-in-time filtering."""

    def build(row: pd.Series) -> str:
        event_time = pd.to_datetime(row[contract.event_timestamp], utc=True)
        records = _normalise_history(row[contract.transcript_history])
        candidates: list[tuple[pd.Timestamp, str]] = []

        for record in records:
            text = next((record.get(key) for key in text_keys if key in record), None)
            timestamp = next(
                (record.get(key) for key in timestamp_keys if key in record), None
            )
            if not text or timestamp is None:
                continue
            observed_at = pd.to_datetime(timestamp, utc=True, errors="coerce")
            if pd.isna(observed_at) or observed_at > event_time:
                continue
            candidates.append((observed_at, str(text)))

        return max(candidates, key=lambda item: item[0])[1] if candidates else ""

    return build

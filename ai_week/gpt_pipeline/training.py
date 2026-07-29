from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

from .contracts import DatasetContract, ForecastModel, TrainingResult
from .evaluation import regression_metrics


@dataclass
class WalkForwardTrainingPipeline:
    contract: DatasetContract
    n_splits: int = 5
    gap: int = 0

    def run(
        self,
        feature_data: pd.DataFrame,
        model: ForecastModel,
        *,
        target_column: str | None = None,
        feature_columns: Sequence[str] | None = None,
        online_feedback: bool = False,
    ) -> TrainingResult:
        """
        Run expanding-window CV and fit the final development-set model.

        Static mode:
            prepare on each training fold, then batch-predict its validation fold.

        Prequential mode:
            prepare on each training fold, then for each validation sample in time
            order: predict -> record -> reveal target -> optional online update.
        """

        inferred_features = self.contract.validate_feature_dataset(feature_data)
        target = target_column or self.contract.target_pct_change
        features = list(feature_columns or inferred_features)

        missing_features = [column for column in features if column not in feature_data]
        if missing_features:
            raise ValueError(f"Missing selected feature columns: {missing_features}")
        if target not in feature_data:
            raise ValueError(f"Missing target column: {target}")

        development = feature_data.loc[
            (feature_data[self.contract.split] == self.contract.train_value)
            & feature_data[target].notna()
        ].copy()
        development[self.contract.event_timestamp] = pd.to_datetime(
            development[self.contract.event_timestamp], utc=True
        )
        development = development.sort_values(
            [self.contract.event_timestamp, self.contract.sample_id],
            kind="mergesort",
        ).reset_index(drop=True)

        if len(development) <= self.n_splits:
            raise ValueError(
                f"Need more than n_splits={self.n_splits} labelled development rows; "
                f"received {len(development)}."
            )

        splitter = TimeSeriesSplit(n_splits=self.n_splits, gap=self.gap)
        fold_metric_rows: list[dict[str, float | int | str]] = []
        oof_rows: list[dict[str, object]] = []

        mode = "prequential_online" if online_feedback else "static_walk_forward"

        for fold_number, (train_idx, val_idx) in enumerate(
            splitter.split(development), start=1
        ):
            train_fold = development.iloc[train_idx].copy()
            val_fold = development.iloc[val_idx].copy()

            fold_model = model.clone()
            fold_model.prepare(train_fold, features, target)

            if online_feedback:
                predictions = self._predict_prequential(
                    model=fold_model,
                    validation_data=val_fold,
                    feature_columns=features,
                    target_column=target,
                )
            else:
                predictions = fold_model.predict(val_fold, features)

            metrics = regression_metrics(
                val_fold[target].to_numpy(dtype=float), predictions
            )
            fold_metric_rows.append(
                {
                    "fold": fold_number,
                    "mode": mode,
                    "n_train": len(train_fold),
                    "n_validation": len(val_fold),
                    "train_end": train_fold[self.contract.event_timestamp].max(),
                    "validation_start": val_fold[self.contract.event_timestamp].min(),
                    "validation_end": val_fold[self.contract.event_timestamp].max(),
                    **metrics,
                }
            )

            for row_position, prediction in enumerate(predictions):
                source_row = val_fold.iloc[row_position]
                oof_rows.append(
                    {
                        self.contract.sample_id: source_row[self.contract.sample_id],
                        self.contract.event_id: source_row[self.contract.event_id],
                        self.contract.underlying_id: source_row[
                            self.contract.underlying_id
                        ],
                        self.contract.event_timestamp: source_row[
                            self.contract.event_timestamp
                        ],
                        "fold": fold_number,
                        "y_true": float(source_row[target]),
                        "y_pred": float(prediction),
                    }
                )

        fold_metrics = pd.DataFrame(fold_metric_rows)
        oof_predictions = pd.DataFrame(oof_rows).sort_values(
            self.contract.event_timestamp
        )
        aggregate_metrics = regression_metrics(
            oof_predictions["y_true"].to_numpy(),
            oof_predictions["y_pred"].to_numpy(),
        )

        final_model = model.clone()
        final_model.prepare(development, features, target)
        if online_feedback:
            # Warm the online state using development data in chronological order.
            self._predict_prequential(
                model=final_model,
                validation_data=development,
                feature_columns=features,
                target_column=target,
            )

        return TrainingResult(
            trained_model=final_model,
            fold_metrics=fold_metrics,
            aggregate_validation_metrics=aggregate_metrics,
            out_of_fold_predictions=oof_predictions,
            feature_columns=features,
            target_column=target,
            validation_mode=mode,
        )

    @staticmethod
    def _predict_prequential(
        *,
        model: ForecastModel,
        validation_data: pd.DataFrame,
        feature_columns: Sequence[str],
        target_column: str,
    ) -> np.ndarray:
        predictions: list[float] = []
        update = getattr(model, "update_after_prediction", None)

        for row_index in range(len(validation_data)):
            row = validation_data.iloc[[row_index]]
            prediction = float(model.predict(row, feature_columns)[0])
            predictions.append(prediction)

            if callable(update):
                update(float(row.iloc[0][target_column]), prediction)

        return np.asarray(predictions, dtype=float)

    def predict_holdout(
        self,
        feature_data: pd.DataFrame,
        result: TrainingResult,
    ) -> pd.DataFrame:
        """Predict the holdout once, with online updates disabled."""

        holdout = feature_data.loc[
            feature_data[self.contract.split] == self.contract.holdout_value
        ].copy()
        holdout[self.contract.event_timestamp] = pd.to_datetime(
            holdout[self.contract.event_timestamp], utc=True
        )
        holdout = holdout.sort_values(
            [self.contract.event_timestamp, self.contract.sample_id]
        )

        predictions = result.trained_model.predict(holdout, result.feature_columns)
        output = holdout[self.contract.identifier_columns].copy()
        output["y_pred"] = predictions
        if result.target_column in holdout:
            output["y_true"] = holdout[result.target_column].to_numpy()
        return output

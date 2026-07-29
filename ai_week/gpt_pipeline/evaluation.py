from __future__ import annotations

import math

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    valid = np.isfinite(y_true) & np.isfinite(y_pred)
    y_true = y_true[valid]
    y_pred = y_pred[valid]

    if len(y_true) == 0:
        return {
            "n": 0.0,
            "mae": math.nan,
            "rmse": math.nan,
            "r2": math.nan,
            "pearson": math.nan,
            "spearman": math.nan,
            "directional_accuracy": math.nan,
        }

    can_correlate = (
        len(y_true) > 1
        and not np.isclose(np.std(y_true), 0.0)
        and not np.isclose(np.std(y_pred), 0.0)
    )
    pearson = float(np.corrcoef(y_true, y_pred)[0, 1]) if can_correlate else math.nan
    spearman = (
        float(pd.Series(y_true).corr(pd.Series(y_pred), method="spearman"))
        if can_correlate
        else math.nan
    )

    return {
        "n": float(len(y_true)),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(mean_squared_error(y_true, y_pred) ** 0.5),
        "r2": float(r2_score(y_true, y_pred)) if len(y_true) > 1 else math.nan,
        "pearson": pearson,
        "spearman": spearman,
        "directional_accuracy": float(np.mean(np.sign(y_true) == np.sign(y_pred))),
    }

"""Baseline models implementing contracts.Model.

Includes the requested univariate regression on the last consensus revenue
number. Note: the consensus *level* is scale-dependent (mega-caps vs small
caps) so expect ~zero IC; the same class pointed at `surprise_rev` is the
economically sensible univariate benchmark (classic PEAD sign).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..contracts import FeatureSet


class MeanBaseline:
    """Predict the training mean of y_ret."""
    def __init__(self, name: str = "mean"):
        self.name, self.mu_ = name, 0.0

    def fit(self, X: FeatureSet, y: pd.DataFrame, events: pd.DataFrame):
        self.mu_ = float(y["y_ret"].mean())
        return self

    def predict(self, X: FeatureSet, events: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame({"y_pred": self.mu_}, index=X.index)


class UnivariateOLS:
    """y_ret ~ a + b * X_num[feature]  (NaN-x rows predicted at train mean)."""

    def __init__(self, feature: str = "cons_rev_last", name: str | None = None):
        self.feature = feature
        self.name = name or f"uols[{feature}]"
        self.a_, self.b_, self.mu_ = 0.0, 0.0, 0.0

    def fit(self, X: FeatureSet, y: pd.DataFrame, events: pd.DataFrame):
        x = X.X_num[self.feature].to_numpy(dtype=float)
        t = y["y_ret"].to_numpy(dtype=float)
        m = np.isfinite(x) & np.isfinite(t)
        self.mu_ = float(t[m].mean()) if m.any() else 0.0
        if m.sum() >= 3 and np.std(x[m]) > 0:
            self.b_, self.a_ = np.polyfit(x[m], t[m], 1)
        else:
            self.a_, self.b_ = self.mu_, 0.0
        return self

    def predict(self, X: FeatureSet, events: pd.DataFrame) -> pd.DataFrame:
        x = X.X_num[self.feature].to_numpy(dtype=float)
        yhat = self.a_ + self.b_ * x
        yhat[~np.isfinite(yhat)] = self.mu_
        return pd.DataFrame({"y_pred": yhat}, index=X.index)


class SklearnRegressor:
    """Adapter: any sklearn regressor on median-imputed, scaled X_num."""

    def __init__(self, estimator=None, name: str = "ridge"):
        if estimator is None:
            from sklearn.linear_model import Ridge
            estimator = Ridge(alpha=1.0)
        self.est, self.name = estimator, name
        self.cols_, self.med_ = [], None

    def _mat(self, X: FeatureSet) -> np.ndarray:
        return X.X_num.reindex(columns=self.cols_).fillna(self.med_).fillna(0.0).to_numpy()

    def fit(self, X: FeatureSet, y: pd.DataFrame, events: pd.DataFrame):
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        self.cols_ = list(X.X_num.columns)
        self.med_ = X.X_num.median()
        m = y["y_ret"].notna()
        self.pipe_ = make_pipeline(StandardScaler(), self.est)
        self.pipe_.fit(self._mat(X.loc(X.index[m])), y.loc[m, "y_ret"].to_numpy())
        return self

    def predict(self, X: FeatureSet, events: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame({"y_pred": self.pipe_.predict(self._mat(X))}, index=X.index)

"""Evaluation module.

Consumes : predictions {model_name -> PredictionFrame}, labels, events.
Produces : contracts.EvalReport (metrics table, per-event residuals, confusions).

Also owns the split policy (purged walk-forward CV) and the online-evaluation
harness for contracts.OnlineModel.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .contracts import EvalReport, OnlineModel


# --------------------------------------------------------------------------- #
# Splitter
# --------------------------------------------------------------------------- #
class PurgedWalkForwardSplitter:
    """Expanding-window folds over event time with purge + embargo:
    train fold = events whose labels RESOLVE at least `embargo_days` before the
    first val decision time — no label window overlaps the val period."""

    def __init__(self, n_folds: int = 4, embargo_days: int = 5):
        self.n_folds, self.embargo = n_folds, pd.Timedelta(days=embargo_days)

    def split(self, events: pd.DataFrame, labels: pd.DataFrame):
        ev = events.sort_values("as_of_ts")
        edges = np.linspace(0, len(ev), self.n_folds + 2, dtype=int)[1:]  # skip fold0=train-only
        folds = []
        for a, b in zip(edges[:-1], edges[1:]):
            val = ev.index[a:b]
            t0 = ev["as_of_ts"].iloc[a]
            ok = labels.loc[ev.index, "resolved_ts"] <= t0 - self.embargo
            train = ev.index[:a][ok.iloc[:a].to_numpy()]
            if len(train) and len(val):
                folds.append((pd.Index(train), pd.Index(val)))
        return folds


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #
def regression_metrics(y: pd.Series, p: pd.Series) -> dict:
    m = y.notna() & p.notna()
    y, p = y[m], p[m]
    if len(y) < 3:
        return {"n": len(y)}
    e = p - y
    strat = np.sign(p) * y                          # event-driven long/short PnL
    return {
        "n": len(y),
        "mae": float(e.abs().mean()),
        "rmse": float(np.sqrt((e ** 2).mean())),
        "ic_spearman": float(p.corr(y, method="spearman")),
        "hit_rate": float((np.sign(p) == np.sign(y)).mean()),
        "ls_mean_ret": float(strat.mean()),
        "ls_tstat": float(strat.mean() / (strat.std(ddof=1) / np.sqrt(len(strat))))
        if strat.std(ddof=1) > 0 else np.nan,
        "r2": float(1 - (e ** 2).sum() / ((y - y.mean()) ** 2).sum())
        if y.std() > 0 else np.nan,
    }


def classification_metrics(t: pd.Series, p: pd.Series):
    m = t.notna() & p.notna()
    t, p = t[m].astype(str), p[m].astype(str)
    if len(t) < 3:
        return {}, None
    labs = ["miss", "inline", "beat"]
    cm = pd.crosstab(t, p).reindex(index=labs, columns=labs, fill_value=0)
    f1s = []
    for c in labs:
        tp = cm.loc[c, c]
        pr = tp / max(cm[c].sum(), 1)
        rc = tp / max(cm.loc[c].sum(), 1)
        f1s.append(0.0 if pr + rc == 0 else 2 * pr * rc / (pr + rc))
    return {"beat_acc": float((t == p).mean()),
            "beat_macro_f1": float(np.mean(f1s))}, cm


def evaluate(preds: dict[str, pd.DataFrame], labels: pd.DataFrame,
             events: pd.DataFrame) -> EvalReport:
    """`events` must carry a 'split' column; metrics are computed per
    (model, split) over the intersection of prediction and label indices."""
    rows, per_event, confusions = {}, [], {}
    for name, pf in preds.items():
        ids = pf.index.intersection(labels.index)
        lb, ev = labels.loc[ids], events.loc[ids]
        for split, g in ev.groupby("split"):
            i = g.index
            met = regression_metrics(lb.loc[i, "y_ret"], pf.loc[i, "y_pred"])
            if "beat_pred" in pf.columns:
                cmet, cm = classification_metrics(lb.loc[i, "beat"],
                                                  pf.loc[i, "beat_pred"])
                met |= cmet
                if cm is not None:
                    confusions[(name, split)] = cm
            rows[(name, split)] = met
            pe = pd.DataFrame({"model": name, "split": split,
                               "y_true": lb.loc[i, "y_ret"],
                               "y_pred": pf.loc[i, "y_pred"]})
            per_event.append(pe.reset_index(names="event_id"))
    metrics = pd.DataFrame.from_dict(rows, orient="index")
    metrics.index = pd.MultiIndex.from_tuples(metrics.index, names=["model", "split"])
    return EvalReport(metrics=metrics.sort_index(),
                      per_event=pd.concat(per_event, ignore_index=True)
                      if per_event else pd.DataFrame(),
                      confusions=confusions)


# --------------------------------------------------------------------------- #
# Online evaluation harness (test-time feedback, strictly causal)
# --------------------------------------------------------------------------- #
def run_online_eval(model: OnlineModel, X, labels: pd.DataFrame,
                    events: pd.DataFrame) -> pd.DataFrame:
    """Predict events in as_of order; before each prediction, feed back every
    earlier event whose label has resolved by now (resolved_ts <= as_of).
    Deployment-faithful evaluation of test-time in-context learning."""
    order = events.sort_values("as_of_ts").index
    pending: list[str] = []
    out = []
    for eid in order:
        now = events.loc[eid, "as_of_ts"]
        still = []
        for pid in pending:
            r = labels.loc[pid]
            if pd.notna(r["resolved_ts"]) and r["resolved_ts"] <= now:
                model.update(pid, float(r["y_ret"]), r["beat"], r["resolved_ts"])
            else:
                still.append(pid)
        pending = still + [eid]
        out.append(model.predict(X.loc([eid]), events.loc[[eid]]))
    return pd.concat(out).loc[events.index]

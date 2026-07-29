"""Feature Engineering & Selection.

Consumes : events (rows to featurize), PITView, and — at fit time only —
           training labels (for supervised selection).
Produces : contracts.FeatureSet (X_num float64 + X_text str + meta), row-aligned
           to the input events.

Rules of engagement:
  * fit(...) sees TRAIN events/labels only (the orchestrator guarantees this;
    refit per CV fold).
  * transform(...) may be called on any events; it must only read raw data via
    `view` at each row's as_of_ts — that is the leakage firewall.
  * Add a feature family = add a FeatureBlock. Nothing else changes.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .contracts import FeatureBlock, FeatureSelector, FeatureSet, PITView


def _meta(block: str, kind: str, names_desc: dict[str, str]) -> pd.DataFrame:
    return pd.DataFrame({"block": block, "kind": kind,
                         "description": pd.Series(names_desc)})


# --------------------------------------------------------------------------- #
# Blocks
# --------------------------------------------------------------------------- #
class EventColumnBlock:
    """Expose columns precomputed on the events table (e.g. surprise_rev).

    NOTE: surprise_rev / cons_rev_last are announcement outputs — legitimate
    only under as_of_policy='post_call'. Do not wire this block into a
    'pre_call' experiment.
    """
    def __init__(self, cols=("surprise_rev", "cons_rev_last")):
        self.name, self.cols = "event_cols", list(cols)

    def fit(self, events, view):
        return self

    def transform(self, events: pd.DataFrame, view: PITView) -> FeatureSet:
        num = events[self.cols].astype("float64")
        fs = FeatureSet.empty(events.index)
        return FeatureSet(num, fs.X_text,
                          _meta(self.name, "num", {c: f"events.{c}" for c in self.cols}))


class ConsensusBlock:
    """PIT sell-side consensus features (levels + revisions)."""
    name = "consensus"

    def __init__(self, metric: str = "revenue", revision_days: int = 90):
        self.metric, self.revision_days = metric, revision_days

    def fit(self, events, view):
        return self

    def transform(self, events: pd.DataFrame, view: PITView) -> FeatureSet:
        rows = []
        for eid, r in events.iterrows():
            c = view.consensus(r["ticker"], r["as_of_ts"], metric=self.metric)
            c = c.dropna(subset=["consensus_value"])
            last = c["consensus_value"].iloc[-1] if len(c) else np.nan
            win = c[c["asof_ts"] >= r["as_of_ts"] - pd.Timedelta(days=self.revision_days)]
            rev = (win["consensus_value"].iloc[-1] / win["consensus_value"].iloc[0] - 1
                   if len(win) >= 2 and win["consensus_value"].iloc[0] else np.nan)
            rows.append((last, np.log10(abs(last)) if last and np.isfinite(last) else np.nan, rev))
        num = pd.DataFrame(rows, index=events.index,
                           columns=["cons_pit_last", "cons_pit_log", "cons_rev_90d"])
        return FeatureSet(num.astype("float64"), FeatureSet.empty(events.index).X_text,
                          _meta(self.name, "num", {
                              "cons_pit_last": "last consensus value at as_of",
                              "cons_pit_log": "log10 |consensus| (scale-free)",
                              "cons_rev_90d": "consensus revision over trailing 90d"}))


class PriceBlock:
    """Trailing momentum / realized vol from PIT closes."""
    name = "price"

    def __init__(self, ret_windows=(5, 21, 63), vol_window=21):
        self.ret_windows, self.vol_window = ret_windows, vol_window

    def fit(self, events, view):
        return self

    def transform(self, events: pd.DataFrame, view: PITView) -> FeatureSet:
        cols = [f"ret_{w}d" for w in self.ret_windows] + [f"vol_{self.vol_window}d"]
        rows = []
        for _, r in events.iterrows():
            px = view.prices(r["ticker"], r["as_of_ts"],
                             lookback_days=max(self.ret_windows) + self.vol_window + 5)
            c = px["close"].to_numpy()
            vals = [c[-1] / c[-w - 1] - 1 if len(c) > w else np.nan
                    for w in self.ret_windows]
            rets = np.diff(np.log(c)) if len(c) > 2 else np.array([])
            vals.append(float(np.std(rets[-self.vol_window:]) * np.sqrt(252))
                        if len(rets) >= 5 else np.nan)
            rows.append(vals)
        num = pd.DataFrame(rows, index=events.index, columns=cols).astype("float64")
        return FeatureSet(num, FeatureSet.empty(events.index).X_text,
                          _meta(self.name, "num", {c: "trailing price stat" for c in cols}))


class TranscriptBlock:
    """Latest transcript text (prefer the event's own earnings call under
    post_call as_of; otherwise most recent of any kind) + cheap numeric stats."""
    name = "transcript"

    def __init__(self, prefer_kinds=("earnings_call",)):
        self.prefer_kinds = list(prefer_kinds)

    def fit(self, events, view):
        return self

    def transform(self, events: pd.DataFrame, view: PITView) -> FeatureSet:
        texts, nums = [], []
        for _, r in events.iterrows():
            t = view.transcripts(r["ticker"], r["as_of_ts"])
            pick = t[t["kind"].isin(self.prefer_kinds)] if len(t) else t
            pick = pick if len(pick) else t
            if len(pick):
                row = pick.iloc[-1]
                txt = str(row["text"])
                age = (r["as_of_ts"] - row["published_ts"]).total_seconds() / 3600.0
            else:
                txt, age = "", np.nan
            texts.append(txt)
            nums.append((len(txt.split()), age))
        num = pd.DataFrame(nums, index=events.index,
                           columns=["transcript_n_words", "transcript_age_h"]).astype("float64")
        txtf = pd.DataFrame({"transcript_latest": texts}, index=events.index)
        meta = pd.concat([
            _meta(self.name, "num", {"transcript_n_words": "word count",
                                     "transcript_age_h": "hours since publication"}),
            _meta(self.name, "text", {"transcript_latest": "latest transcript text"})])
        return FeatureSet(num, txtf, meta)


class NewsBlock:
    """Recent headlines digest for LLMs + article count."""
    name = "news"

    def __init__(self, lookback_days=7, max_headlines=30):
        self.lookback_days, self.max_headlines = lookback_days, max_headlines

    def fit(self, events, view):
        return self

    def transform(self, events: pd.DataFrame, view: PITView) -> FeatureSet:
        digests, counts = [], []
        for _, r in events.iterrows():
            n = view.news(r["ticker"], r["as_of_ts"], lookback_days=self.lookback_days)
            counts.append(len(n))
            digests.append("\n".join(n["headline"].tail(self.max_headlines).astype(str)))
        num = pd.DataFrame({f"n_news_{self.lookback_days}d": counts},
                           index=events.index).astype("float64")
        txt = pd.DataFrame({"news_digest": digests}, index=events.index)
        meta = pd.concat([
            _meta(self.name, "num", {f"n_news_{self.lookback_days}d": "article count"}),
            _meta(self.name, "text", {"news_digest": "recent headlines"})])
        return FeatureSet(num, txt, meta)


# --------------------------------------------------------------------------- #
# Selection
# --------------------------------------------------------------------------- #
class BasicSelector:
    """Drop all-NaN / near-constant numerics; optionally keep top-k by |Spearman|
    with y_ret (computed on TRAIN only). Text columns always pass through."""

    def __init__(self, top_k: int | None = None, min_std: float = 1e-12):
        self.top_k, self.min_std = top_k, min_std
        self.keep_: list[str] = []

    def fit(self, X: FeatureSet, y: pd.DataFrame) -> "BasicSelector":
        num = X.X_num
        ok = num.columns[(num.notna().sum() >= 3) & (num.std() > self.min_std)]
        if self.top_k is not None and len(ok) > self.top_k:
            ic = num[ok].corrwith(y["y_ret"], method="spearman").abs()
            ok = ic.sort_values(ascending=False).head(self.top_k).index
        self.keep_ = list(ok)
        return self

    def transform(self, X: FeatureSet) -> FeatureSet:
        meta = X.meta.loc[X.meta.index.isin(self.keep_ + list(X.X_text.columns))]
        return FeatureSet(X.X_num[self.keep_], X.X_text, meta)


# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #
class FeaturePipeline:
    """Composition of FeatureBlocks + FeatureSelectors.

    fit(events_train, view, y_train) -> self     (blocks fit, then selectors)
    transform(events_any, view)      -> FeatureSet
    """

    def __init__(self, blocks: list[FeatureBlock],
                 selectors: list[FeatureSelector] | None = None):
        self.blocks, self.selectors = blocks, selectors or []

    def fit(self, events: pd.DataFrame, view: PITView, y: pd.DataFrame) -> "FeaturePipeline":
        for b in self.blocks:
            b.fit(events, view)
        X = FeatureSet.concat([b.transform(events, view) for b in self.blocks])
        for s in self.selectors:
            s.fit(X, y.loc[X.index])
            X = s.transform(X)
        return self

    def transform(self, events: pd.DataFrame, view: PITView) -> FeatureSet:
        X = FeatureSet.concat([b.transform(events, view) for b in self.blocks])
        for s in self.selectors:
            X = s.transform(X)
        return X


def default_blocks() -> list[FeatureBlock]:
    return [EventColumnBlock(), ConsensusBlock(), PriceBlock(),
            TranscriptBlock(), NewsBlock()]

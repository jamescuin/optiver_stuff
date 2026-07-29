"""Interface contracts for the earnings-reaction pipeline.

This file is the ONLY coupling point between modules. Each team imports from
here and nothing else from each other. If it isn't in this file, it isn't a
contract.

Conventions (binding):
  * Every per-event frame is indexed by `event_id` (str) and row-aligned.
  * All timestamps are tz-aware UTC. `date` columns are naive trading dates.
  * `as_of_ts` is the decision time for an event. NOTHING observed after
    `as_of_ts` may enter a feature. The PITView is the enforcement mechanism:
    feature code must access raw data exclusively through it.
  * Labels carry `resolved_ts` = the time the label becomes knowable. Any form
    of feedback / online learning may only consume a label once
    resolved_ts <= the current event's as_of_ts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, Protocol, Sequence, runtime_checkable

import pandas as pd

EVENT_ID = "event_id"

# --------------------------------------------------------------------------- #
# 1. Raw input schemas (Data Assembler validates raw parquet against these).
#    If vendor files differ, write an adapter in data_assembler.load_* —
#    downstream code never changes.
# --------------------------------------------------------------------------- #
RAW_SCHEMAS: dict[str, dict[str, str]] = {
    "prices": {
        "ticker": "str",
        "date": "datetime64[ns] naive trading date",
        "close": "float (use adjusted close if available)",
    },
    "calendar": {
        "event_id": "str, unique",
        "ticker": "str",
        "event_ts": "datetime64 UTC — announcement / call start",
        "fiscal_period": "str, e.g. '2025Q4' (must match consensus.fiscal_period)",
    },
    "transcripts": {
        "transcript_id": "str",
        "ticker": "str",
        "published_ts": "datetime64 UTC",
        "kind": "str, e.g. 'earnings_call', 'conference', ...",
        "text": "str",
    },
    "news": {
        "article_id": "str",
        "ticker": "str",
        "published_ts": "datetime64 UTC",
        "headline": "str",
        "body": "str",
    },
    "consensus": {
        "ticker": "str",
        "asof_ts": "datetime64 UTC — when this snapshot was knowable",
        "metric": "str, e.g. 'revenue'",
        "fiscal_period": "str",
        "consensus_value": "float — sell-side consensus at asof_ts",
        "actual_value": "float — reported actual; NaN until reported",
    },
    "holdout": {"event_id": "str — the 92 holdout test events"},
}

# --------------------------------------------------------------------------- #
# 2. Assembled artefacts (Data Assembler -> everyone).
# --------------------------------------------------------------------------- #
EVENTS_COLUMNS = [
    "ticker",          # str
    "event_ts",        # UTC announcement time
    "as_of_ts",        # UTC decision time (see config.as_of_policy)
    "fiscal_period",   # str
    "split",           # 'train' | 'test' | 'unlabeled'
    "entry_date",      # naive date of entry close (NaT if unavailable)
    "exit_date",       # naive date of exit close (NaT if unavailable)
    "cons_rev_last",   # last pre-event consensus revenue (float, NaN ok)
    "rev_actual",      # reported revenue (float, NaN ok)
    "surprise_rev",    # rev_actual / cons_rev_last - 1 (post-announcement info)
]

LABEL_COLUMNS = [
    "y_ret",           # float: exit_close / entry_close - 1; NaN if unavailable
    "beat",            # 'beat' | 'inline' | 'miss' | NaN  (revenue vs consensus)
    "resolved_ts",     # UTC time both labels are knowable (exit close)
]

PRED_REQUIRED = ["y_pred"]                      # float forecast of y_ret
PRED_OPTIONAL = ["beat_pred", "y_std", "info"]  # info: free-form dict/str


def validate_frame(df: pd.DataFrame, required: Sequence[str], name: str) -> pd.DataFrame:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{name}: missing required columns {missing}; has {list(df.columns)}")
    return df


# --------------------------------------------------------------------------- #
# 3. Point-in-time data access — the leakage firewall.
# --------------------------------------------------------------------------- #
@runtime_checkable
class PITView(Protocol):
    """Read-only, point-in-time access to raw sources.

    Every method returns only rows knowable at `as_of` (timestamps <= as_of;
    for prices, only sessions whose close occurred at or before as_of).
    Feature code MUST go through this interface — never touch raw frames.
    """

    def prices(self, ticker: str, as_of: pd.Timestamp,
               lookback_days: int | None = None) -> pd.DataFrame: ...
    def transcripts(self, ticker: str, as_of: pd.Timestamp,
                    kinds: Sequence[str] | None = None) -> pd.DataFrame: ...
    def news(self, ticker: str, as_of: pd.Timestamp,
             lookback_days: int | None = None) -> pd.DataFrame: ...
    def consensus(self, ticker: str, as_of: pd.Timestamp,
                  metric: str | None = None) -> pd.DataFrame: ...


@dataclass
class AssembledDataset:
    """Output of the Data Assembler. Frozen once built."""
    events: pd.DataFrame   # index event_id, columns EVENTS_COLUMNS
    labels: pd.DataFrame   # index event_id, columns LABEL_COLUMNS
    view: PITView

    def ids(self, split: str) -> pd.Index:
        return self.events.index[self.events["split"] == split]


# --------------------------------------------------------------------------- #
# 4. Feature module contracts.
# --------------------------------------------------------------------------- #
@dataclass
class FeatureSet:
    """Two-modality feature container, always row-aligned on event_id.

    X_num  : float64 frame; NaN = missing (models own their imputation policy).
    X_text : str frame ('' = missing); payloads for LLM consumers
             (e.g. 'transcript_latest', 'news_digest').
    meta   : per-feature metadata; index = feature name,
             columns = ['block', 'kind', 'description'] with kind in {'num','text'}.
    """
    X_num: pd.DataFrame
    X_text: pd.DataFrame
    meta: pd.DataFrame

    @property
    def index(self) -> pd.Index:
        return self.X_num.index

    def loc(self, ids: Iterable[str]) -> "FeatureSet":
        ids = pd.Index(ids)
        return FeatureSet(self.X_num.loc[ids], self.X_text.loc[ids], self.meta)

    @staticmethod
    def empty(index: pd.Index) -> "FeatureSet":
        m = pd.DataFrame(columns=["block", "kind", "description"])
        return FeatureSet(pd.DataFrame(index=index, dtype="float64"),
                          pd.DataFrame(index=index, dtype="object"), m)

    @staticmethod
    def concat(parts: Sequence["FeatureSet"]) -> "FeatureSet":
        assert parts, "nothing to concat"
        idx = parts[0].index
        for p in parts[1:]:
            if not p.index.equals(idx):
                raise ValueError("FeatureSet.concat: misaligned event_id indices")
        num = pd.concat([p.X_num for p in parts], axis=1)
        txt = pd.concat([p.X_text for p in parts], axis=1)
        meta = pd.concat([p.meta for p in parts], axis=0)
        for frame, what in ((num, "numeric"), (txt, "text")):
            if frame.columns.duplicated().any():
                dupes = frame.columns[frame.columns.duplicated()].tolist()
                raise ValueError(f"duplicate {what} feature names: {dupes}")
        return FeatureSet(num, txt, meta)


@runtime_checkable
class FeatureBlock(Protocol):
    """One family of features.

    fit(events, view)       : called with TRAINING events only; learn any state
                              (scalers, vocab, ...). Return self.
    transform(events, view) : pure & deterministic given fitted state; must only
                              read data via `view` at each row's `as_of_ts`.
                              Returns a FeatureSet indexed exactly like `events`.
    """
    name: str
    def fit(self, events: pd.DataFrame, view: PITView) -> "FeatureBlock": ...
    def transform(self, events: pd.DataFrame, view: PITView) -> FeatureSet: ...


@runtime_checkable
class FeatureSelector(Protocol):
    """Supervised/unsupervised column selection. fit sees TRAIN folds only."""
    def fit(self, X: FeatureSet, y: pd.DataFrame) -> "FeatureSelector": ...
    def transform(self, X: FeatureSet) -> FeatureSet: ...


# --------------------------------------------------------------------------- #
# 5. Model module contracts.
# --------------------------------------------------------------------------- #
@runtime_checkable
class Model(Protocol):
    """Anything that forecasts y_ret (and optionally `beat`).

    fit(X, y, events)     : X/y/events row-aligned TRAIN data. `events` carries
                            ticker/event_ts/as_of_ts; `y` carries resolved_ts —
                            everything a time-ordered / online fit needs.
                            Return self.
    predict(X, events)    : returns DataFrame indexed like X with at least
                            PRED_REQUIRED columns. Must NEVER receive labels.
    Determinism given (fitted state, inputs, seed) is part of the contract.
    """
    name: str
    def fit(self, X: FeatureSet, y: pd.DataFrame, events: pd.DataFrame) -> "Model": ...
    def predict(self, X: FeatureSet, events: pd.DataFrame) -> pd.DataFrame: ...


@runtime_checkable
class OnlineModel(Model, Protocol):
    """Model that can absorb realized outcomes after deployment.

    The evaluation harness calls update(...) only once resolved_ts <= the
    as_of_ts of the next event to be predicted (strict causality).
    """
    def update(self, event_id: str, y_ret: float, beat: str | None,
               resolved_ts: pd.Timestamp) -> None: ...


ModelFactory = Callable[[], Model]


@dataclass
class ModelSpec:
    """How the orchestrator should treat a model."""
    name: str
    factory: ModelFactory
    cross_validate: bool = True   # False => skip CV (e.g. expensive LLMs)
    online_test: bool = False     # True + OnlineModel => feed back resolved test outcomes


# --------------------------------------------------------------------------- #
# 6. Evaluation module contracts.
# --------------------------------------------------------------------------- #
@runtime_checkable
class Splitter(Protocol):
    """Yields (train_ids, val_ids) with purge/embargo already applied:
    no train event's resolved_ts may exceed the earliest val as_of_ts - embargo.
    """
    def split(self, events: pd.DataFrame,
              labels: pd.DataFrame) -> list[tuple[pd.Index, pd.Index]]: ...


@dataclass
class EvalReport:
    metrics: pd.DataFrame     # index (model, split); columns = metric names
    per_event: pd.DataFrame   # long: event_id, model, split, y_true, y_pred, ...
    confusions: dict = field(default_factory=dict)  # (model, split) -> DataFrame

    def render(self) -> str:
        out = ["=" * 78, "EVALUATION REPORT", "=" * 78,
               self.metrics.round(4).to_string()]
        for key, cm in self.confusions.items():
            out += [f"\n-- beat/inline/miss confusion {key} (rows=true) --", cm.to_string()]
        return "\n".join(out)

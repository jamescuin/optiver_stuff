"""LLM forecaster with feedback-based in-context "online learning".

Design
------
* LLMClient protocol -> swap Anthropic / OpenAI / vLLM / a mock without touching
  the model. `AnthropicClient` is provided; `MockLLMClient` makes the pipeline
  runnable offline.
* The LLM predicts strict JSON: {"pct_change_pred": float, "beat_pred": str,
  "confidence": float, "rationale": str}. Parse failures degrade to 0.0 and are
  flagged in `info` — never crash a backtest on a bad completion.
* Online learning here = in-context adaptation, not gradient updates:
    fit()     replays TRAIN events in event-time order; predicts each, then
              stores (context digest, prediction, realized outcome) in a
              FeedbackMemory once the label has RESOLVED. Later events retrieve
              the k most relevant resolved exemplars into their prompt.
    update()  (contracts.OnlineModel) lets the evaluation harness feed back
              resolved TEST outcomes chronologically, if you opt into
              ModelSpec.online_test=True. Default is a frozen memory for a
              clean static comparison.
  Leakage rule enforced throughout: an exemplar is retrievable for event e only
  if exemplar.resolved_ts <= e.as_of_ts.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

import numpy as np
import pandas as pd

from ..config import LLMConfig
from ..contracts import FeatureSet


# --------------------------------------------------------------------------- #
# Clients
# --------------------------------------------------------------------------- #
@runtime_checkable
class LLMClient(Protocol):
    def complete(self, system: str, user: str) -> str: ...


class AnthropicClient:
    """Thin wrapper around the Anthropic Messages API."""

    def __init__(self, cfg: LLMConfig):
        import anthropic  # pip install anthropic; reads ANTHROPIC_API_KEY
        self._cli, self._cfg = anthropic.Anthropic(), cfg

    def complete(self, system: str, user: str) -> str:
        r = self._cli.messages.create(
            model=self._cfg.model, max_tokens=512, temperature=self._cfg.temperature,
            system=system, messages=[{"role": "user", "content": user}])
        return "".join(b.text for b in r.content if getattr(b, "type", "") == "text")


class MockLLMClient:
    """Deterministic offline stand-in: reads `surprise_rev` out of the numeric
    dump in the prompt and returns 0.4 * surprise. Exists so the whole pipeline
    (incl. feedback loop) is testable without API calls."""

    def complete(self, system: str, user: str) -> str:
        m = re.search(r"surprise_rev:\s*(-?\d+\.?\d*(?:e-?\d+)?)", user)
        s = float(m.group(1)) if m else 0.0
        beat = "beat" if s > 0.02 else "miss" if s < -0.02 else "inline"
        return json.dumps({"pct_change_pred": round(0.4 * s, 6), "beat_pred": beat,
                           "confidence": 0.5, "rationale": "mock"})


# --------------------------------------------------------------------------- #
# Feedback memory
# --------------------------------------------------------------------------- #
@dataclass
class FeedbackRecord:
    event_id: str
    ticker: str
    event_ts: pd.Timestamp
    resolved_ts: pd.Timestamp
    digest: dict                  # small named-number context, e.g. {'surprise_rev': .04}
    y_pred: float | None          # None => outcome-only exemplar (no prediction made)
    y_true: float
    beat_true: str | None

    def render(self) -> str:
        nums = ", ".join(f"{k}={v:+.3f}" for k, v in self.digest.items()
                         if v is not None and np.isfinite(v))
        s = f"- {self.ticker} {self.event_ts.date()} [{nums}] -> realized {self.y_true:+.2%}"
        if self.beat_true:
            s += f" ({self.beat_true})"
        if self.y_pred is not None and np.isfinite(self.y_pred):
            s += f"; my forecast {self.y_pred:+.2%}, error {self.y_pred - self.y_true:+.2%}"
        return s


class FeedbackMemory:
    """Time-aware exemplar store. retrieve() only returns records already
    resolved at `as_of` (the causality guarantee)."""

    def __init__(self, cap: int = 5000):
        self.cap, self._recs = cap, []  # type: int, list[FeedbackRecord]

    def add(self, rec: FeedbackRecord) -> None:
        self._recs.append(rec)
        if len(self._recs) > self.cap:
            self._recs = self._recs[-self.cap:]

    def retrieve(self, ticker: str, as_of: pd.Timestamp, k: int) -> list[FeedbackRecord]:
        cand = [r for r in self._recs
                if pd.notna(r.resolved_ts) and r.resolved_ts <= as_of]
        cand.sort(key=lambda r: (r.ticker == ticker, r.event_ts), reverse=True)
        return cand[:k]

    def __len__(self):
        return len(self._recs)


# --------------------------------------------------------------------------- #
# Forecaster
# --------------------------------------------------------------------------- #
_SYSTEM = (
    "You are an equity earnings-reaction forecaster. Given point-in-time context "
    "for one earnings event, forecast the stock's percentage close-to-close change "
    "over the next {h} trading close(s) after the announcement. Learn from the "
    "resolved past cases provided. Respond with STRICT JSON only:\n"
    '{{"pct_change_pred": <float, e.g. 0.031 means +3.1%>, '
    '"beat_pred": "beat"|"inline"|"miss", "confidence": <0..1>, '
    '"rationale": "<max 40 words>"}}'
)


class LLMForecaster:
    """contracts.OnlineModel backed by any LLMClient."""

    def __init__(self, client: LLMClient, cfg: LLMConfig, horizon_days: int = 1,
                 name: str = "llm", digest_features=("surprise_rev", "ret_21d", "vol_21d")):
        self.client, self.cfg, self.name = client, cfg, name
        self.h, self.digest_features = horizon_days, list(digest_features)
        self.memory = FeedbackMemory(cap=cfg.memory_cap)
        self._pending: dict[str, FeedbackRecord] = {}
        self.train_predictions_: pd.DataFrame | None = None

    # ----- prompt / parse -------------------------------------------------- #
    def _digest(self, xnum: pd.Series) -> dict:
        return {f: (float(xnum[f]) if f in xnum and np.isfinite(xnum[f]) else None)
                for f in self.digest_features}

    def _prompt(self, xnum: pd.Series, xtext: pd.Series, ev: pd.Series,
                exemplars: list[FeedbackRecord]) -> str:
        nums = "\n".join(f"{k}: {v:.6g}" for k, v in xnum.items() if np.isfinite(v))
        tr = str(xtext.get("transcript_latest", ""))[: self.cfg.transcript_char_cap]
        nw = str(xtext.get("news_digest", ""))[: self.cfg.news_char_cap]
        ex = "\n".join(r.render() for r in exemplars) or "(none yet)"
        return (f"TICKER: {ev['ticker']}   EVENT UTC: {ev['event_ts']}   "
                f"FISCAL PERIOD: {ev['fiscal_period']}\n\n"
                f"NUMERIC FEATURES (point-in-time):\n{nums}\n\n"
                f"RESOLVED PAST CASES (most relevant first):\n{ex}\n\n"
                f"RECENT HEADLINES:\n{nw}\n\n"
                f"LATEST TRANSCRIPT (truncated):\n{tr}\n\nJSON:")

    @staticmethod
    def _parse(raw: str) -> dict:
        try:
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            d = json.loads(m.group(0)) if m else {}
            p = float(np.clip(float(d.get("pct_change_pred", np.nan)), -0.5, 0.5))
            return {"y_pred": p, "beat_pred": d.get("beat_pred"),
                    "confidence": d.get("confidence"), "parse_ok": np.isfinite(p)}
        except Exception:
            return {"y_pred": np.nan, "beat_pred": None, "confidence": None,
                    "parse_ok": False}

    def _predict_one(self, eid: str, X: FeatureSet, ev: pd.Series) -> dict:
        exemplars = self.memory.retrieve(ev["ticker"], ev["as_of_ts"],
                                         self.cfg.max_exemplars)
        raw = self.client.complete(_SYSTEM.format(h=self.h),
                                   self._prompt(X.X_num.loc[eid], X.X_text.loc[eid],
                                                ev, exemplars))
        out = self._parse(raw)
        if not out["parse_ok"]:
            out["y_pred"] = 0.0
        self._pending[eid] = FeedbackRecord(
            event_id=eid, ticker=ev["ticker"], event_ts=ev["event_ts"],
            resolved_ts=pd.NaT, digest=self._digest(X.X_num.loc[eid]),
            y_pred=out["y_pred"], y_true=np.nan, beat_true=None)
        return out

    # ----- contracts.Model ------------------------------------------------- #
    def fit(self, X: FeatureSet, y: pd.DataFrame, events: pd.DataFrame) -> "LLMForecaster":
        order = events.sort_values("event_ts").index
        walk = order[-self.cfg.max_fit_events:]           # cost control
        seed_only = order.difference(walk, sort=False)
        for eid in seed_only:                             # outcome-only exemplars
            if np.isfinite(y.loc[eid, "y_ret"]):
                self.memory.add(FeedbackRecord(
                    eid, events.loc[eid, "ticker"], events.loc[eid, "event_ts"],
                    y.loc[eid, "resolved_ts"], self._digest(X.X_num.loc[eid]),
                    None, float(y.loc[eid, "y_ret"]), y.loc[eid, "beat"]))
        rows = {}
        for eid in walk:                                  # walk-forward w/ feedback
            rows[eid] = self._predict_one(eid, X, events.loc[eid])
            if np.isfinite(y.loc[eid, "y_ret"]):
                self.update(eid, float(y.loc[eid, "y_ret"]), y.loc[eid, "beat"],
                            y.loc[eid, "resolved_ts"])
        self.train_predictions_ = pd.DataFrame.from_dict(rows, orient="index")
        return self

    def predict(self, X: FeatureSet, events: pd.DataFrame) -> pd.DataFrame:
        rows = {eid: self._predict_one(eid, X, events.loc[eid])
                for eid in events.sort_values("as_of_ts").index}
        return pd.DataFrame.from_dict(rows, orient="index").loc[X.index]

    # ----- contracts.OnlineModel ------------------------------------------ #
    def update(self, event_id: str, y_ret: float, beat: str | None,
               resolved_ts: pd.Timestamp) -> None:
        rec = self._pending.pop(event_id, None)
        if rec is None:
            return
        rec.y_true, rec.beat_true, rec.resolved_ts = y_ret, beat, resolved_ts
        self.memory.add(rec)

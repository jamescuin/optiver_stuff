"""Data Assembler.

Consumes : raw parquet files matching contracts.RAW_SCHEMAS (adapt vendor files
           in the load_* functions — the only place raw quirks are allowed).
Produces : contracts.AssembledDataset
             events  (index event_id, EVENTS_COLUMNS)
             labels  (index event_id, LABEL_COLUMNS)
             view    (PITView over the five raw sources)

Label definitions
-----------------
y_ret   = close[exit] / close[entry] - 1
          entry = last close at/before the pre-announcement cutoff
                  (AMC on date D -> entry close = D; BMO on D -> entry = D-1),
          exit  = h-th trading close strictly after the announcement
                  (uniformly entry_index + h).
beat    = sign of (rev_actual / cons_rev_last - 1) with an `inline_band`
          dead zone; cons_rev_last is the last consensus snapshot with
          asof_ts < event_ts for the event's fiscal_period. rev_actual is the
          reported figure for that fiscal_period (announced at the event, hence
          knowable at a post_call as_of).
resolved_ts = exchange close of exit_date (when y_ret becomes knowable).

Splits: 'test' = the 92 holdout event_ids; 'train' = labeled events with
event_ts < cfg.train_end not in holdout; everything else 'unlabeled'.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd

from .config import PipelineConfig
from .contracts import (AssembledDataset, EVENT_ID, RAW_SCHEMAS, validate_frame)


# --------------------------------------------------------------------------- #
# Loaders (adapter seam: rename/coerce vendor columns HERE only)
# --------------------------------------------------------------------------- #
def _read(cfg: PipelineConfig, key: str) -> pd.DataFrame:
    df = pd.read_parquet(cfg.data_dir / cfg.files[key])
    return validate_frame(df, list(RAW_SCHEMAS[key]), key)


def _utc(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, utc=True)


def load_raw(cfg: PipelineConfig) -> dict[str, pd.DataFrame]:
    raw = {k: _read(cfg, k) for k in RAW_SCHEMAS}
    raw["prices"] = raw["prices"].assign(
        date=pd.to_datetime(raw["prices"]["date"]).dt.tz_localize(None)
    ).sort_values(["ticker", "date"])
    for k, col in (("calendar", "event_ts"), ("transcripts", "published_ts"),
                   ("news", "published_ts"), ("consensus", "asof_ts")):
        raw[k] = raw[k].assign(**{col: _utc(raw[k][col])}).sort_values(col)
    if raw["calendar"][EVENT_ID].duplicated().any():
        raise ValueError("calendar: duplicate event_id")
    return raw


# --------------------------------------------------------------------------- #
# Point-in-time view
# --------------------------------------------------------------------------- #
class ParquetPITView:
    """PITView implementation over in-memory raw frames (contracts.PITView)."""

    def __init__(self, raw: dict[str, pd.DataFrame], cfg: PipelineConfig):
        self._p, self._t = raw["prices"], raw["transcripts"]
        self._n, self._c = raw["news"], raw["consensus"]
        self._tz, self._close = cfg.exchange_tz, cfg.market_close

    def _last_closed_session(self, as_of: pd.Timestamp) -> pd.Timestamp:
        loc = as_of.tz_convert(self._tz)
        cutoff = loc.normalize()
        if loc.strftime("%H:%M") < self._close:
            cutoff -= pd.Timedelta(days=1)
        return cutoff.tz_localize(None)

    def prices(self, ticker, as_of, lookback_days=None) -> pd.DataFrame:
        d = self._p[self._p["ticker"] == ticker]
        d = d[d["date"] <= self._last_closed_session(as_of)]
        if lookback_days is not None:
            d = d.tail(lookback_days)
        return d.reset_index(drop=True)

    def transcripts(self, ticker, as_of, kinds: Sequence[str] | None = None):
        d = self._t[(self._t["ticker"] == ticker) & (self._t["published_ts"] <= as_of)]
        if kinds is not None:
            d = d[d["kind"].isin(kinds)]
        return d.reset_index(drop=True)

    def news(self, ticker, as_of, lookback_days=None) -> pd.DataFrame:
        d = self._n[(self._n["ticker"] == ticker) & (self._n["published_ts"] <= as_of)]
        if lookback_days is not None:
            d = d[d["published_ts"] >= as_of - pd.Timedelta(days=lookback_days)]
        return d.reset_index(drop=True)

    def consensus(self, ticker, as_of, metric=None) -> pd.DataFrame:
        d = self._c[(self._c["ticker"] == ticker) & (self._c["asof_ts"] <= as_of)]
        if metric is not None:
            d = d[d["metric"] == metric]
        return d.reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Assembly
# --------------------------------------------------------------------------- #
def _is_amc(event_ts: pd.Timestamp, cfg: PipelineConfig) -> bool:
    if cfg.session_convention in ("amc", "bmo"):
        return cfg.session_convention == "amc"
    return event_ts.tz_convert(cfg.exchange_tz).hour >= 16   # 'auto'


def _entry_exit(dates: np.ndarray, event_ts, amc: bool, h: int):
    """dates: sorted np.datetime64[D] for one ticker. Returns (entry, exit) or NaT."""
    d = np.datetime64(event_ts.tz_convert("UTC").date(), "D")
    cutoff = d if amc else d - np.timedelta64(1, "D")
    i = int(np.searchsorted(dates, cutoff, side="right")) - 1
    j = i + h
    if i < 0 or j >= len(dates):
        return pd.NaT, pd.NaT
    return pd.Timestamp(dates[i]), pd.Timestamp(dates[j])


def _close_ts(date, cfg: PipelineConfig) -> pd.Timestamp:
    hh, mm = map(int, cfg.market_close.split(":"))
    return (pd.Timestamp(date) + pd.Timedelta(hours=hh, minutes=mm + 5)) \
        .tz_localize(cfg.exchange_tz).tz_convert("UTC")


def _revenue_labels(cons: pd.DataFrame, ticker, fp, event_ts, cfg: PipelineConfig):
    d = cons[(cons["ticker"] == ticker) & (cons["fiscal_period"] == fp)
             & (cons["metric"] == cfg.revenue_metric)]
    prior = d[d["asof_ts"] < event_ts]["consensus_value"].dropna()
    cons_last = float(prior.iloc[-1]) if len(prior) else np.nan
    actual = d["actual_value"].dropna()
    rev_actual = float(actual.iloc[-1]) if len(actual) else np.nan
    surprise = rev_actual / cons_last - 1 if np.isfinite(cons_last) and cons_last != 0 \
        and np.isfinite(rev_actual) else np.nan
    if not np.isfinite(surprise):
        beat = None
    elif surprise > cfg.inline_band:
        beat = "beat"
    elif surprise < -cfg.inline_band:
        beat = "miss"
    else:
        beat = "inline"
    return cons_last, rev_actual, surprise, beat


def assemble(cfg: PipelineConfig) -> AssembledDataset:
    raw = load_raw(cfg)
    view = ParquetPITView(raw, cfg)
    cal, cons = raw["calendar"], raw["consensus"]
    holdout = set(raw["holdout"][EVENT_ID].astype(str))
    dates_by_tkr = {t: g["date"].to_numpy(dtype="datetime64[D]")
                    for t, g in raw["prices"].groupby("ticker")}
    close_by_tkr = {t: g.set_index("date")["close"]
                    for t, g in raw["prices"].groupby("ticker")}

    ev_rows, lb_rows = [], []
    for r in cal.itertuples(index=False):
        amc = _is_amc(r.event_ts, cfg)
        entry, exit_ = _entry_exit(dates_by_tkr.get(r.ticker, np.array([], "datetime64[D]")),
                                   r.event_ts, amc, cfg.horizon_trading_days)
        y = np.nan
        resolved = pd.NaT
        if pd.notna(entry):
            px = close_by_tkr[r.ticker]
            y = float(px.loc[exit_] / px.loc[entry] - 1)
            resolved = _close_ts(exit_, cfg)
        c_last, actual, surp, beat = _revenue_labels(cons, r.ticker, r.fiscal_period,
                                                    r.event_ts, cfg)
        as_of = (r.event_ts + pd.Timedelta(hours=cfg.as_of_lag_hours)
                 if cfg.as_of_policy == "post_call"
                 else r.event_ts - pd.Timedelta(hours=1))
        ev_rows.append(dict(event_id=str(r.event_id), ticker=r.ticker,
                            event_ts=r.event_ts, as_of_ts=as_of,
                            fiscal_period=r.fiscal_period, split="",
                            entry_date=entry, exit_date=exit_,
                            cons_rev_last=c_last, rev_actual=actual, surprise_rev=surp))
        lb_rows.append(dict(event_id=str(r.event_id), y_ret=y, beat=beat,
                            resolved_ts=resolved))

    events = pd.DataFrame(ev_rows).set_index(EVENT_ID)
    labels = pd.DataFrame(lb_rows).set_index(EVENT_ID)

    labeled = labels["y_ret"].notna()
    is_test = events.index.isin(holdout)
    pre_end = events["event_ts"] < pd.Timestamp(cfg.train_end, tz="UTC")
    events["split"] = np.where(is_test, "test",
                       np.where(labeled & pre_end, "train", "unlabeled"))
    n_bad = int((is_test & ~labeled).sum())
    if n_bad:
        print(f"[assembler] WARNING: {n_bad} holdout events lack price labels")
    print(f"[assembler] events={len(events)}  "
          + "  ".join(f"{k}={v}" for k, v in events['split'].value_counts().items()))
    return AssembledDataset(events=events, labels=labels, view=view)

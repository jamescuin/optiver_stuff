"""Schema-conforming synthetic data. Doubles as the executable specification of
contracts.RAW_SCHEMAS and as the shared fixture for parallel development /
integration tests. Injects a weak true signal (post-announcement drift
proportional to revenue surprise) plus tickers with truncated price history to
exercise the 'unlabeled' path.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def make_synthetic(out_dir: Path, n_tickers: int = 48, seed: int = 7,
                   n_holdout: int = 92) -> None:
    rng = np.random.default_rng(seed)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tickers = [f"TK{i:03d}" for i in range(n_tickers)]
    days = pd.bdate_range("2022-06-01", "2026-07-24")

    # fiscal periods 2023Q1..2026Q1, reported ~45d after quarter end, mostly AMC
    fps = [f"{y}Q{q}" for y in range(2023, 2027) for q in range(1, 5)][:13]
    q_end = {fp: pd.Timestamp(f"{fp[:4]}-{int(fp[5]) * 3:02d}-28") for fp in fps}

    prices, cal, trans, news, consensus = [], [], [], [], []
    eid = 0
    for tk in tickers:
        drift = rng.normal(0.0002, 0.0003)
        rets = rng.normal(drift, 0.02, len(days))
        base_rev = float(rng.lognormal(21, 1))
        events = []
        for fp in fps:
            ts = (q_end[fp] + pd.Timedelta(days=int(45 + rng.integers(0, 10))))
            hour = 21 if rng.random() < 0.8 else 12       # AMC vs BMO (UTC)
            ts = ts.tz_localize("UTC") + pd.Timedelta(hours=hour)
            true_rev = base_rev * (1 + 0.02 * fps.index(fp)) * (1 + rng.normal(0, 0.06))
            cons_val = true_rev * (1 + rng.normal(0, 0.03))
            surprise = true_rev / cons_val - 1
            events.append((fp, ts, true_rev, cons_val, surprise))
            # inject drift: bump returns for 3 sessions after the event date
            d0 = np.searchsorted(days.values, np.datetime64(ts.date()))
            rets[d0 + 1: d0 + 4] += 0.35 * surprise / 3 + rng.normal(0, 0.004)

        px = 50 * np.exp(np.cumsum(rets))
        cut = len(days)
        if tk in ("TK000", "TK001"):                      # truncated history -> unlabeled
            cut = np.searchsorted(days.values, np.datetime64("2025-11-01"))
        prices.append(pd.DataFrame({"ticker": tk, "date": days[:cut],
                                    "close": px[:cut]}))

        for fp, ts, true_rev, cons_val, surprise in events:
            eid += 1
            cal.append(dict(event_id=f"E{eid:05d}", ticker=tk, event_ts=ts,
                            fiscal_period=fp))
            for dd in (60, 30, 7):                        # consensus snapshots
                consensus.append(dict(ticker=tk, asof_ts=ts - pd.Timedelta(days=dd),
                                      metric="revenue", fiscal_period=fp,
                                      consensus_value=cons_val * (1 + rng.normal(0, 0.01)),
                                      actual_value=np.nan))
            consensus.append(dict(ticker=tk, asof_ts=ts + pd.Timedelta(hours=1),
                                  metric="revenue", fiscal_period=fp,
                                  consensus_value=cons_val, actual_value=true_rev))
            tone = ("exceeded expectations with strong demand" if surprise > 0.02 else
                    "fell short of expectations amid softness" if surprise < -0.02 else
                    "was broadly in line with expectations")
            trans.append(dict(transcript_id=f"T{eid:05d}", ticker=tk,
                              published_ts=ts + pd.Timedelta(hours=2),
                              kind="earnings_call",
                              text=f"{tk} {fp} earnings call. Management said revenue "
                                   f"{tone}. " + "Guidance discussion follows. " * 50))
            if rng.random() < 0.5:                        # occasional other transcripts
                trans.append(dict(transcript_id=f"C{eid:05d}", ticker=tk,
                                  published_ts=ts - pd.Timedelta(days=20),
                                  kind="conference", text=f"{tk} fireside chat."))
            for j in range(int(rng.integers(1, 5))):      # pre-event news
                news.append(dict(article_id=f"N{eid:05d}_{j}", ticker=tk,
                                 published_ts=ts - pd.Timedelta(days=float(rng.uniform(0.5, 6))),
                                 headline=f"{tk} {fp}: analysts eye revenue print",
                                 body="preview article body"))

    cal_df = pd.DataFrame(cal)
    in_2026 = cal_df[cal_df["event_ts"] >= pd.Timestamp("2026-01-01", tz="UTC")]
    holdout = in_2026.sort_values("event_ts")["event_id"].head(n_holdout)

    pd.concat(prices).to_parquet(out_dir / "prices.parquet")
    cal_df.to_parquet(out_dir / "calendar.parquet")
    pd.DataFrame(trans).to_parquet(out_dir / "transcripts.parquet")
    pd.DataFrame(news).to_parquet(out_dir / "news.parquet")
    pd.DataFrame(consensus).to_parquet(out_dir / "consensus.parquet")
    holdout.to_frame().to_parquet(out_dir / "holdout.parquet")
    print(f"[synthetic] wrote {len(cal_df)} events ({len(holdout)} holdout) -> {out_dir}")

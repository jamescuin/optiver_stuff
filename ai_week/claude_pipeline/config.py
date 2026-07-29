"""Single configuration object. Every convention that resolves an ambiguity in
the problem statement lives here, so it is auditable and sweepable."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class LLMConfig:
    model: str = "claude-sonnet-4-6"
    temperature: float = 0.0
    max_exemplars: int = 8        # k feedback exemplars retrieved into each prompt
    memory_cap: int = 5000        # max stored feedback records
    max_fit_events: int = 200     # walk-forward-predict at most N most recent train
                                  # events during fit (cost control); earlier train
                                  # events seed memory as outcome-only exemplars
    transcript_char_cap: int = 6000
    news_char_cap: int = 1500


@dataclass(frozen=True)
class PipelineConfig:
    data_dir: Path

    # --- raw file names inside data_dir (adapter seam) ---
    files: dict = field(default_factory=lambda: {
        "prices": "prices.parquet", "calendar": "calendar.parquet",
        "transcripts": "transcripts.parquet", "news": "news.parquet",
        "consensus": "consensus.parquet", "holdout": "holdout.parquet",
    })

    # --- target definition ---
    horizon_trading_days: int = 1      # exit = h-th close strictly after announcement
    session_convention: str = "auto"   # 'amc' | 'bmo' | 'auto' (infer from event_ts
                                       # local hour; >=16:00 local => AMC)
    exchange_tz: str = "America/New_York"
    market_close: str = "16:00"

    # --- decision time ---
    as_of_policy: str = "post_call"    # 'post_call': as_of = event_ts + lag (transcript
                                       #   & reported actuals are legitimate features;
                                       #   task = predict the reaction/drift).
                                       # 'pre_call': as_of = event_ts - 1h (predict the
                                       #   announcement itself; surprise/actuals/latest
                                       #   call transcript are then leakage and the
                                       #   assembler's PIT view excludes them).
    as_of_lag_hours: float = 4.0

    # --- beat / inline / miss ---
    revenue_metric: str = "revenue"
    inline_band: float = 0.02          # |actual/consensus - 1| <= band -> 'inline'

    # --- splits ---
    train_end: str = "2026-01-01"      # events strictly before -> train/val pool
    n_folds: int = 4
    embargo_days: int = 5

    seed: int = 7
    llm: LLMConfig = field(default_factory=LLMConfig)

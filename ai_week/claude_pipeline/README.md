# Earnings-Reaction Pipeline — Contracts-First Skeleton

Predict the % close-price change following earnings calls, plus the
beat / inline / miss revenue call, from mixed numeric + text data using
classical ML and LLMs interchangeably.

`contracts.py` is the single coupling point. Each module imports contracts
and nothing else from its peers, so the four teams can build in parallel
against the synthetic fixture (`synthetic.py`, an executable spec of the raw
schemas).

## Module contracts

| Module | Consumes | Produces | Key invariants |
|---|---|---|---|
| **Data Assembler** `assemble(cfg)` | 6 raw parquet files per `RAW_SCHEMAS` (prices, calendar, transcripts, news, consensus, holdout) | `AssembledDataset(events, labels, view)` | `events`/`labels` indexed by `event_id`; `view` is the only door to raw data; labels carry `resolved_ts` |
| **Feature Module** `FeaturePipeline` | `fit(events_train, view, y_train)` / `transform(events_any, view)` | `FeatureSet(X_num float64, X_text str, meta)` row-aligned to input | `fit` sees train only; `transform` reads only via `view` at each row's `as_of_ts`; selection lives inside the pipeline |
| **Model Module** any `Model` | `fit(X, y, events)` / `predict(X, events)` | `PredictionFrame`: `y_pred` required; `beat_pred`, `y_std`, `info` optional | `predict` never sees labels; `OnlineModel.update(...)` only fed outcomes with `resolved_ts <= next as_of_ts` |
| **Evaluation** | `{model -> PredictionFrame}`, labels, events | `EvalReport` (metrics per model x split, per-event residuals, confusions) | Owns `PurgedWalkForwardSplitter` (purge + embargo) and the causal `run_online_eval` harness |

## Pinned conventions (all in `config.py`)

- **Target**: `y_ret = close[exit]/close[entry] - 1`; entry = last pre-announcement
  close (AMC on D -> D; BMO on D -> D-1, inferred from local hour under
  `session_convention='auto'`); exit = `horizon_trading_days`-th close strictly
  after the announcement. Events without both closes -> `split='unlabeled'`.
- **Decision time** `as_of_ts = event_ts + as_of_lag_hours` (`post_call` policy):
  the call transcript and the released actuals are legitimate features; the task
  is the post-announcement reaction/drift. Flip to `pre_call` to predict the
  announcement itself — then `surprise_rev`, actuals and the event's own
  transcript are leakage and the PIT view excludes them automatically.
- **Beat label**: `surprise = actual/last_pre-event_consensus - 1` for the event's
  `fiscal_period`; `|surprise| <= inline_band` (2%) -> inline; else beat/miss.
- **Splits**: `test` = the 92 holdout event_ids; `train` = labeled events with
  `event_ts < 2026-01-01` not in holdout; rest `unlabeled`.
- **Leakage firewall**: features only via `PITView`; feedback/online learning only
  via `resolved_ts`; CV refits features + models per fold with purge + embargo.

## Models included

- `MeanBaseline`; `UnivariateOLS("cons_rev_last")` — the requested baseline
  (expect ~0 IC: consensus *level* is scale, not signal); `UnivariateOLS("surprise_rev")`
  — the economically meaningful univariate (PEAD); `SklearnRegressor` (ridge adapter).
- `LLMForecaster` (`models/llm.py`): prompts with numeric dump + transcript +
  news + retrieved feedback exemplars; strict-JSON output with robust parsing;
  swap backends via the `LLMClient` protocol (`AnthropicClient` real,
  `MockLLMClient` offline/deterministic for CI).

## Online learning with LLM feedback

Implemented as **in-context adaptation**, not gradient updates: `fit` replays
train events in event-time order, predicts, then banks
(context digest, forecast, realized outcome) into a `FeedbackMemory`; later
prompts retrieve the k most relevant *resolved* exemplars. At test time,
`ModelSpec(online_test=True)` routes an `OnlineModel` through
`run_online_eval`, which feeds back holdout outcomes strictly as they resolve.
Compare the frozen and online rows to measure what feedback buys you. Caveats:
validation must mirror the deployment protocol (it does here), and watch for
regime-anchoring on recent exemplars. Gradient fine-tuning would slot in as
another `Model` — the contract already passes time-ordered events + `resolved_ts`.

## Run

```bash
pip install pandas numpy pyarrow scikit-learn anthropic
python -m earnings_pipeline.pipeline --synthetic              # offline demo (mock LLM)
python -m earnings_pipeline.pipeline --data /path/to/parquets # real data
python -m earnings_pipeline.pipeline --data ... --real-llm    # Anthropic API (ANTHROPIC_API_KEY)
```

Point `--data` at parquet files matching `RAW_SCHEMAS` (adapt vendor quirks in
`data_assembler.load_raw` only). Add features = add a `FeatureBlock`; add a
model = add a `ModelSpec` in `pipeline.default_specs`.

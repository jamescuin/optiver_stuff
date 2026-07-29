"""Orchestrator: wires assembler -> features -> models -> evaluation.

run_experiment(cfg, make_pipeline, specs):
  1. assemble(cfg)
  2. purged walk-forward CV on 'train' events: refit the FeaturePipeline AND a
     fresh model per fold (selection & stateful LLM memory never see val),
     collect out-of-fold predictions -> reported under split='val'.
  3. final fit on all 'train', predict the 92-event holdout (split='test');
     OnlineModels with spec.online_test=True go through the causal online
     harness instead of a frozen predict.
  4. evaluate() -> EvalReport.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable

import pandas as pd

from .config import PipelineConfig
from .contracts import EvalReport, ModelSpec, OnlineModel
from .data_assembler import assemble
from .evaluation import PurgedWalkForwardSplitter, evaluate, run_online_eval
from .features import BasicSelector, FeaturePipeline, default_blocks


def run_experiment(cfg: PipelineConfig,
                   make_pipeline: Callable[[], FeaturePipeline],
                   specs: list[ModelSpec]) -> EvalReport:
    ds = assemble(cfg)
    tr_ids, te_ids = ds.ids("train"), ds.ids("test")
    ev_tr, y_tr = ds.events.loc[tr_ids], ds.labels.loc[tr_ids]
    folds = PurgedWalkForwardSplitter(cfg.n_folds, cfg.embargo_days).split(ev_tr, y_tr)
    print(f"[pipeline] folds={len(folds)} " +
          " ".join(f"({len(a)}tr/{len(b)}va)" for a, b in folds))

    preds: dict[str, pd.DataFrame] = {}

    # ---- cross-validation (out-of-fold 'val' predictions) ----
    for spec in specs:
        if not spec.cross_validate:
            continue
        oof = []
        for a, b in folds:
            fp = make_pipeline().fit(ds.events.loc[a], ds.view, ds.labels.loc[a])
            Xa, Xb = fp.transform(ds.events.loc[a], ds.view), fp.transform(ds.events.loc[b], ds.view)
            mdl = spec.factory().fit(Xa, ds.labels.loc[a], ds.events.loc[a])
            oof.append(mdl.predict(Xb, ds.events.loc[b]))
        if oof:
            preds[f"{spec.name}"] = pd.concat(oof)

    # ---- final fit on all train -> holdout ----
    fp = make_pipeline().fit(ev_tr, ds.view, y_tr)
    X_tr, X_te = fp.transform(ev_tr, ds.view), fp.transform(ds.events.loc[te_ids], ds.view)
    for spec in specs:
        mdl = spec.factory().fit(X_tr, y_tr, ev_tr)
        if spec.online_test and isinstance(mdl, OnlineModel):
            p = run_online_eval(mdl, X_te, ds.labels.loc[te_ids], ds.events.loc[te_ids])
            key = f"{spec.name}@online"
        else:
            p = mdl.predict(X_te, ds.events.loc[te_ids])
            key = spec.name
        preds[key] = pd.concat([preds.get(key, pd.DataFrame()), p]) \
            if key in preds else p

    ev_eval = ds.events.copy()   # OOF predictions on the train pool report as 'val'
    ev_eval.loc[ev_eval["split"] == "train", "split"] = "val"
    report = evaluate(preds, ds.labels, ev_eval)
    print(report.render())
    return report


# --------------------------------------------------------------------------- #
# Demo wiring (also serves as the reference for adding your own models)
# --------------------------------------------------------------------------- #
def default_specs(cfg: PipelineConfig, use_real_llm: bool = False) -> list[ModelSpec]:
    from .models.baseline import MeanBaseline, SklearnRegressor, UnivariateOLS
    from .models.llm import AnthropicClient, LLMForecaster, MockLLMClient

    def llm():
        client = AnthropicClient(cfg.llm) if use_real_llm else MockLLMClient()
        return LLMForecaster(client, cfg.llm, horizon_days=cfg.horizon_trading_days,
                             name="llm")

    return [
        ModelSpec("mean", lambda: MeanBaseline()),
        ModelSpec("uols[cons_rev_last]", lambda: UnivariateOLS("cons_rev_last")),
        ModelSpec("uols[surprise_rev]", lambda: UnivariateOLS("surprise_rev")),
        ModelSpec("ridge", lambda: SklearnRegressor()),
        ModelSpec("llm", llm, cross_validate=False, online_test=True),
    ]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path("./_demo_data"))
    ap.add_argument("--synthetic", action="store_true",
                    help="generate schema-conforming synthetic data first")
    ap.add_argument("--real-llm", action="store_true",
                    help="use the Anthropic API instead of the mock client")
    args = ap.parse_args()

    if args.synthetic:
        from .synthetic import make_synthetic
        make_synthetic(args.data)

    cfg = PipelineConfig(data_dir=args.data)
    make_fp = lambda: FeaturePipeline(default_blocks(), [BasicSelector()])  # noqa: E731
    run_experiment(cfg, make_fp, default_specs(cfg, use_real_llm=args.real_llm))


if __name__ == "__main__":
    main()

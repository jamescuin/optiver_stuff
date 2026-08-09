# Pipeline Overview

Here, we document the general framework of the pipeline we use to develop and evaluate various models/strategies for the research project. We focus on a modular approach, that is the development of distinct, separable modules, each defining an explicit interface contract, regarding exactly what Module $M$ expects as input, and what it subsequently outputs. Such an approach helps facilitate development in parallel, and also clarity regarding where responsibility lies within the pipeline.

## Modules


### Data Modules

**`DataSources`**
<br>$\rightarrow$ Responsbile for simply loading in all relevant data, from the respective data sources, for the period specified.

**`DataQualityLayer`**
<br>$\rightarrow$ Responsbile for logic pertaining to how data is cleaned and pre-processed.
<br>$\rightarrow$ Later modules should **not** implement their own data cleaning logic.


### Structure Modules

**`StructureUniverse`**
<br>$\rightarrow$ Here, we define the various option structures we may wish to ever trade.
<br>$\rightarrow$ The structures should be parameterised such that they are uniquely identifiable.

**`StructureResolver`**
<br>$\rightarrow$ For a given structure id and (selection) timestamp, this resolves the structure definition into the exact option contracts and quantities representing said structure at said timestamp, to then help construct the structure path in the `StructurePathBuilder` module. 
<br>$\rightarrow$ Note this is determined by our rebalancing frequency.

**`StructurePathBuilder`**
<br>$\rightarrow$ Responsible, for the structures that exist within the `StructureUniverse`, resolving these structures for all timestamps, and constructing the PnL path, as well as the Greek paths throughout time.

### Feature & Target Modules

**`FeatureEngine`**
<br>$\rightarrow$ Responsible for construction of features to be utilised by the `AlphaModel`(s), and should be constructed from the output of the `DataQualityLayer` and/or the `StructurePathBuilder`.
<br>$\rightarrow$ Features should be constructed at their natural resolution (w.r.t to timestamps) and then rows selected accordingly by the `DatasetAssembler`.
<br>$\rightarrow$ Explicit care is taken to ensure only feature values available at the timestamp where prediction is required are used.

**`LabelBuilder`**
<br>$\rightarrow$ Responsible for construction of the target(s) to be predicted by the `AlphaModel`(s).
<br>$\rightarrow$ Recall, downstream metrics, the primary one being (skew delta-hedged) PnL.
<br>$\rightarrow$ Different horizons of the target(s) should be constructed, to improve/evaluate robustness of predictions.
<br>$\rightarrow$ Normalisation of the respective target(s), w.r.t say the Greeks could be interesting. For example, PnL per magnitude of wvega gained, PnL per std of PnL for structure, etc.


**`DatasetAssembler`**
<br>$\rightarrow$ Responsible for converting independently produced features and labels into a point-in-time-correct trainable dataset.
<br>$\rightarrow$ If available structures differ by timestamp, samples should be assigned a weighting, to avoid model fitting being dominated by such occurances.


### Signal Model Modules

**`AlphaModel`**
<br>$\rightarrow$ Contains the logic for both rule-based models and trainable models.
<br>$\rightarrow$ Structure characteristics should be an input to these models. For ElasticNet, use OHE here, whilst for tree-based not required. We could potentially pass the structure id here also.
<br>
<br>$\rightarrow$ For trainable models, consideration as to whether we utilise a separate model per structure, a single model for all structure, or an ensemble of models (in the spirit of Condercet's Jury Theorem) is required. 



**`ModelTrainer`**
<br>$\rightarrow$ Responsible, for the trainable `AlphaModel`(s), the training and validation logic, with respect to the specified label(s).
<br>$\rightarrow$ By default, this will perform (leakage-safe) walk-forward K-fold cross validation.
<br>$\rightarrow$ Specifically, this should output a series of **OOF scores**, per relevant structure, that serves as an input into the `PortfolioOptimiser` module, to be interpreted as buy/sell/hold signals, as well as the final fitted model, for future predictions.


### Backtesting Modules

**`PortfolioConstructor`**
<br>$\rightarrow$ Given the series of **OOF** (alpha) scores, per relevant structure, this outputs our explicit trades, to be consumed by the `BacktestEngine`, having gone through logic concerning transaction costs, risk limits, other trading rules, and portfolio optimisation.
<br>$\rightarrow$ Given the limited number of trading instances per day (8 per day), we may wish to include logic concerning whether a trade is worth doing based on the time of day. For example, a small but positive EV trade may be worth skipping at the start of the day if we empirically observe many (larger) positive EV trading opportunities per day, or that the majority of our PnL comes from a small number of trades.
<br>$\rightarrow$ Note the above would need to align with rebalancing (and delta hedging) instances.
<br>$\rightarrow$ Remember to net exposures where applicable here.
<br>$\rightarrow$ Given lots of positive EV trades, within risk limits, in isloation, combining them becomes a constrained optimisation problem.

**`BacktestEngine`**
<br>$\rightarrow$ Given the trades, for the respective structures, this simply runs through time, computing specified (evaluation metrics), and outputting the complete history.

**`EvaluationEngine`**
<br>$\rightarrow$ Given the complete backtest result, and the **OOF** predictions (if applicable), this produces in depth visualisation and summary of the resulting trades.
<br>$\rightarrow$ May wish to look at evaluation metrics conditional on, say, direction/sign of true value.


## Other Thoughts
- Regarding regression using tree based model leaves, we have reflected on the potential need/opportunity to go beyond simple mean for leave values. FOr example, via OLS within leaves, we can achieve extrapolation, however may wish to rather clip at range of leave values within the training fold?

- Reflecting on the first week, I think it is critical I continue to push for experiments/investigations done be the team to be statistically rigorous, and respect hypothesis testing principles where appropriate/possible.

- We note that the delta hedged PnL we try to predict in model training may differ slightly to what we observe in backtesting due to aggregation of delta hedging where possible.

- If we tune `PortfolioConstructor` parameters during training we need to avoid leakage here too, w.r.t say Greeks, PnL, and other quantities.

- Normalising features s.t. we caputre changes (rather than absolute values) over a period seems sensible as a default. i.e. for range T-k to T, our price/volatility/etc values should have the respective value at T-k subtracted from them.
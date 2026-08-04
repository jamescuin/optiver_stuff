# Testing Mean Reversion, Momentum, Persistence, and Unit Roots in Log Volatility

Let

$$
x_t=\log(\text{volatility}_t).
$$

The aim is to distinguish four related but different ideas:

- **Global mean reversion:** movement back toward a fixed long-run level.
- **Local mean reversion:** correction of a recent displacement from a local benchmark.
- **Momentum or trending:** continuation of a recent direction of movement.
- **Persistence:** shocks decay slowly, so high volatility tends to remain high for some time.

---

## 1. Direct predictive regression

A useful horizon-specific specification is

$$
x_{t+h}-x_t
=
a_h+b_hD_t+c_hM_t+u_{t+h},
$$

where:

- $x_{t+h}-x_t$ is the future $h$-period change in log volatility;
- $D_t$ measures the current displacement from a reference level;
- $M_t$ measures recent movement or momentum.

### Global mean reversion

Set

$$
D_t=x_t-\mu,
$$

where $\mu$ is a fixed long-run mean.

Then:

$$
b_h<0
$$

means that log volatility tends to move back toward $\mu$. If volatility is above the long-run mean, the model predicts a fall; if it is below the mean, it predicts a rise.

### Local mean reversion

Set

$$
D_t=x_t-\bar{x}^{\,\text{local}}_t,
$$

where $\bar{x}^{\,\text{local}}_t$ may be a recent moving average or another local reference level.

Then:

$$
b_h<0
$$

means that recent deviations tend to be corrected, even if the long-run mean itself changes over time.

### Momentum and reversal

Let $M_t$ represent a recent change, such as

$$
M_t=x_t-x_{t-k}.
$$

Then:

$$
c_h>0
$$

indicates **momentum**: a recent rise predicts a further rise, and a recent fall predicts a further fall.

By contrast,

$$
c_h<0
$$

indicates **reversal**: recent movement tends to be undone.

---

## 2. Persistence is not the same as momentum

Consider an AR(1) process:

$$
x_t-\mu=\rho(x_{t-1}-\mu)+\varepsilon_t.
$$

If

$$
0<\rho<1,
$$

the process is mean-reverting, but the speed of reversion depends on $\rho$.

- A small $\rho$ implies fast mean reversion.
- A $\rho$ close to one implies high persistence and slow mean reversion.

For example,

$$
\rho=0.98
$$

means shocks decay slowly, but they still eventually disappear.

Thus:

- **Persistence** concerns how long a shock remains in the level.
- **Momentum** concerns whether the next movement tends to continue in the same direction.
- A series may be highly persistent without exhibiting momentum in its changes.

---

## 3. Unit roots

A unit root occurs when the autoregressive coefficient equals one:

$$
x_t=x_{t-1}+\varepsilon_t.
$$

This is a random walk. Repeated substitution gives

$$
x_t=x_0+\sum_{s=1}^{t}\varepsilon_s.
$$

Each shock is permanently incorporated into the level.

Consequences include:

- no stable long-run mean;
- no tendency to return to a fixed level;
- variance that grows over time;
- apparent trends that may arise without a deterministic trend.

A unit-root series is usually called integrated of order one, $I(1)$, because differencing produces a stationary series:

$$
\Delta x_t=\varepsilon_t.
$$

The distinction between a highly persistent stationary process and a unit root is therefore crucial:

$$
\rho=0.98
$$

implies slow but eventual mean reversion, whereas

$$
\rho=1
$$

implies that shocks do not decay.

---

## 4. The Augmented Dickey–Fuller test

The ADF test is commonly written as

$$
\Delta x_t
=
\alpha+\beta t+\gamma x_{t-1}
+\sum_{j=1}^{p}\phi_j\Delta x_{t-j}
+\varepsilon_t.
$$

Because

$$
\gamma=\rho-1,
$$

the hypotheses are

$$
H_0:\gamma=0
$$

against

$$
H_1:\gamma<0.
$$

Equivalently:

- $H_0$: the series has a unit root;
- $H_1$: the series is stationary around the included mean or trend.

The ADF test is primarily a test of **global long-run stationarity or mean reversion**. It does not directly test short-horizon momentum or local reversal.

### Interpretation

- **Reject $H_0$:** evidence that the series is stationary and mean-reverting.
- **Fail to reject $H_0$:** insufficient evidence against a unit root.

Failure to reject is not proof that a unit root exists, because the ADF test often has low power against highly persistent stationary alternatives.

---

## 5. Assumptions of the ADF test

The ADF test relies on the following conditions.

### Correct deterministic specification

The regression must correctly include one of:

- no constant;
- a constant;
- a constant and deterministic trend.

An incorrect choice can substantially distort the result.

### Adequate lag length

The lagged differences

$$
\Delta x_{t-j}
$$

must remove residual serial correlation. Too few lags leave autocorrelation in the errors; too many lags reduce power.

### Stable parameters

The mean, trend, and autoregressive dynamics are assumed to be stable over the sample. Structural breaks can make a stationary series appear nonstationary.

### Well-behaved innovations

The residuals should have zero mean, finite variance, and limited dependence. Normality is not required asymptotically, but severe heteroskedasticity or heavy tails can impair finite-sample performance.

### Linear short-memory dynamics

The model assumes that a finite-order linear autoregression adequately captures the short-run dynamics. Nonlinear mean reversion or long-memory behavior may not be well represented.

### Appropriate treatment of seasonality and breaks

Seasonal patterns, deterministic changes, and regime shifts should be modeled explicitly where relevant.

For log volatility, two cautions are especially important:

- long memory can resemble a unit root;
- structural breaks can lead to false non-rejection of the unit-root null.

The standard ADF test does not use ordinary $t$-critical values. It uses Dickey–Fuller critical values because the test statistic has a nonstandard distribution under the null.

---

## 6. OLS estimation and HAC inference

The predictive regression can be estimated by ordinary least squares:

$$
\hat{\theta}
=
(X^\top X)^{-1}X^\top Y.
$$

For $h$-period changes, adjacent dependent variables overlap:

$$
x_{t+h}-x_t
$$

and

$$
x_{t+h+1}-x_{t+1}.
$$

These observations share much of the same future interval. As a result, the regression residuals are mechanically serially correlated, often up to approximately $h-1$ lags.

A Newey–West or HAC adjustment corrects:

- standard errors;
- confidence intervals;
- $t$-statistics;
- $p$-values.

It does **not** change:

- OLS coefficient estimates;
- fitted values;
- forecasts.

HAC also does not fix endogeneity, omitted variables, structural breaks, or model misspecification. The bandwidth should be large enough to capture the overlap-induced serial correlation.

ADF handles serial correlation differently: it adds lagged differences to the test regression rather than applying a standard HAC correction.

---

## 7. Out-of-sample evaluation

A forecasting model should be tested without look-ahead bias.

At forecast origin $t$, a training observation dated $s$ can be used only if its full outcome is already known:

$$
s+h\le t.
$$

The model can be compared with a no-change forecast:

$$
\hat{x}_{t+h}^{\,0}=x_t.
$$

A common measure is the out-of-sample coefficient of determination:

$$
R^2_{\mathrm{OOS}}
=
1-
\frac{\sum_t\left(Y_{t,h}-\hat{Y}_{t,h}\right)^2}
{\sum_t\left(Y_{t,h}-\hat{Y}^{0}_{t,h}\right)^2}.
$$

Interpretation:

- $R^2_{\mathrm{OOS}}>0$: the fitted model beats the benchmark;
- $R^2_{\mathrm{OOS}}<0$: the benchmark performs better.

---

## 8. Is ARMA simpler?

A stationary ARMA model can be simpler when the main aim is forecasting:

$$
\phi(L)(x_t-\mu)=\theta(L)\varepsilon_t.
$$

It can capture:

- persistence through autoregressive roots;
- short-run reversal or oscillation;
- multi-step forecasts;
- residual serial correlation through moving-average terms.

However, ARMA is less transparent when the objective is to separately identify:

- global displacement;
- local displacement;
- recent momentum.

It also assumes a stable, linear, short-memory process. Log volatility often exhibits strong persistence, long memory, structural breaks, or regime changes. Depending on the data, alternatives such as AR, HAR, ARFIMA, or state-space models may be more appropriate.

A useful practical strategy is:

1. use displacement-and-momentum regressions for interpretable hypothesis tests;
2. use AR, ARMA, HAR, or related models as forecasting benchmarks;
3. compare all models out of sample.

---

## Summary

- **Global mean reversion:** movement toward a fixed long-run mean.
- **Local mean reversion:** correction toward a recent local benchmark.
- **Momentum:** recent changes continue in the same direction.
- **Reversal:** recent changes are subsequently undone.
- **Persistence:** shocks decay slowly; persistence can coexist with mean reversion.
- **Unit root:** shocks do not decay and no stable long-run mean exists.
- **ADF:** tests the unit-root null against stationarity, subject to correct specification and adequate lagging.
- **HAC:** corrects inference for serial correlation and heteroskedasticity in overlapping-horizon regressions.
- **ARMA:** useful as a parsimonious forecasting model, but less direct for interpreting global, local, and momentum effects separately.

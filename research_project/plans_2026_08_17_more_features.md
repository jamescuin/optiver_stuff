# SPX / QQQ Options Strategy Summary

## Trading Frequency

- **Minimum signal / trading frequency: 5 minutes.**
- Signals can be recomputed on each 5-minute bar, subject to option quote quality and liquidity.
- Use **1M, 2M, 3M** to denote option maturities of one, two, and three months, so they are not confused with minute bars.
- Slow-moving features such as realized-volatility forecasts can combine 5-minute intraday data with longer daily windows.
- In practice, position changes should still require a sufficiently large signal to overcome transaction costs, bid-ask spreads, and execution risk.

---

## 1. Conditional Short Variance

### Features / signals

- ATM implied volatility / variance
- 5-minute realized returns and intraday realized variance
- Multi-horizon realized-volatility forecast
- Implied variance minus expected realized variance
- Vol-of-vol
- Recent index returns
- VIX / VXN level and changes
- Term-structure slope
- Event / macro flags

### Trade

- Short SPX or QQQ ATM straddles when implied variance is unusually rich relative to expected realized variance.
- Reduce or avoid the position when implied variance is cheap.
- Re-evaluate the signal every 5 minutes, but only trade when the change in expected edge is economically meaningful.

### Core signal

$$
\text{Variance Richness}_t
=
IV_t^2
-
\widehat{\mathbb{E}}_t[RV]
$$

---

## 2. Forward-Variance Term Structure

### Features / signals

- 1M, 2M, and 3M ATM implied variance
- Implied forward variance between maturity buckets
- Forward-variance z-score
- Term-structure slope and curvature
- 5-minute changes in the variance curve
- Realized-volatility regime
- VIX / VXN term-structure information
- Event flags

For two maturities \(T_1 < T_2\), implied forward variance is

$$
FV_{T_1,T_2}
=
\frac{
T_2 IV_{T_2}^2
-
T_1 IV_{T_1}^2
}{
T_2-T_1
}.
$$

### Trade

- Use calendar straddles to express relative-value views.
- If forward variance is rich: generally long the nearer maturity and short the farther maturity.
- If forward variance is cheap: reverse the trade.
- Prefer **vega-matched** or variance-risk-matched structures rather than simple 1:1 contract ratios.
- Recompute the relative-value signal every 5 minutes.

### Core signal

$$
\text{Forward-Variance Richness}_t
=
FV_{1M,2M,t}
-
\widehat{FV}_{1M,2M,t}.
$$

---

## 3. SPX vs QQQ Relative Value

### Features / signals

- SPX vs QQQ ATM implied-variance spread
- SPX vs QQQ forward-variance spread
- 5-minute relative returns
- Intraday and longer-horizon realized-volatility spread
- Beta-adjusted realized variance
- Relative skew
- Relative vol-of-vol
- Relative term-structure slope
- Rolling z-scores of SPX-QQQ volatility relationships

### Trade

- Long volatility in the relatively cheap index.
- Short volatility in the relatively rich index.
- Express using vega-matched SPX and QQQ straddles or calendars.
- Reassess relative richness every 5 minutes.

### Core signal

$$
\text{Relative Forward-Variance Richness}_t
=
\left(
FV_t^{QQQ}
-
FV_t^{SPX}
\right)
-
\widehat{\text{Fair Spread}}_t.
$$

---

## 4. Skew Relative Value

### Features / signals

- 25-delta put IV minus ATM IV
- Put-skew z-score
- 5-minute changes in skew
- Skew term structure
- Realized downside moves
- Spot-vol correlation
- Vol-of-vol
- Term-structure regime

### Trade

- Sell downside skew when it is unusually rich.
- Buy downside skew when it is unusually cheap.
- Express using put spreads, risk reversals, or other skew-focused structures.
- Use 5-minute observations for signal updates, while measuring skew richness against slower historical distributions.

### Core signal

$$
\text{Skew Richness}_t
=
\left(
IV_{25\Delta\text{ Put},t}
-
IV_{ATM,t}
\right)
-
\widehat{\text{Fair Skew}}_t.
$$

---

## 5. Surface Residual / Combined Model

### Features / signals

- ATM implied variance
- Forward variance
- Skew
- Term skew
- Smile curvature
- 5-minute changes in the volatility surface
- Intraday realized variance
- Multi-horizon realized-volatility forecast
- Vol-of-vol
- SPX vs QQQ relative-value features
- Event flags

### Trade

- Estimate a fair SPX and QQQ volatility surface across strike and maturity.
- Identify unusually rich and cheap strike × maturity buckets.
- Trade the residual using calendars, flies, put spreads, straddles, or combinations thereof.
- Refresh residual estimates every 5 minutes, while requiring a minimum signal threshold before trading.

Conceptually,

$$
\text{Surface Residual}_{K,T,t}
=
\sigma^{\text{market}}(K,T,t)
-
\widehat{\sigma}^{\text{fair}}(K,T,t).
$$

---

# Recommended Initial Research Set

Start with three relatively distinct strategies.

## 1. ATM Variance Model

**Goal:** estimate whether current implied variance is rich or cheap.

**Features**
- 5-minute returns
- Intraday realized variance
- Daily / weekly realized-volatility measures
- ATM IV
- VIX / VXN
- Vol-of-vol
- Term slope

**Trade**
- SPX or QQQ ATM straddles.

**Exposure**
- Absolute variance risk premium.

---

## 2. Forward-Variance Model

**Goal:** estimate fair 1M → 2M forward variance.

**Features**
- 1M / 2M / 3M implied variance
- Forward variance
- Curve slope and curvature
- 5-minute changes in the curve
- Realized-volatility regime
- Vol-of-vol

**Trade**
- Vega-matched calendar straddles.

**Exposure**
- Term-structure relative value.

---

## 3. SPX–QQQ Relative-Volatility Model

**Goal:** estimate fair relative variance between SPX and QQQ.

**Features**
- Relative ATM variance
- Relative forward variance
- Relative realized variance
- 5-minute SPX / QQQ return relationship
- Relative skew
- Relative vol-of-vol
- Relative term structure

**Trade**
- Long volatility in the cheap index and short volatility in the rich index.

**Exposure**
- Cross-index relative value.

---

# Summary

The three core research directions are:

1. **Absolute VRP:**  
   Is SPX or QQQ implied variance rich versus expected realized variance?

2. **Term-Structure Relative Value:**  
   Is a forward-variance segment rich or cheap versus its estimated fair value?

3. **Cross-Index Relative Value:**  
   Is QQQ volatility rich or cheap versus SPX after controlling for their normal relative-volatility relationship?

All signals can be **updated every 5 minutes**, but the strategy should not necessarily trade every 5 minutes. A trade should only be initiated or resized when the estimated edge is large enough to justify transaction costs, bid-ask spread, and execution risk.

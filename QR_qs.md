They are pointing to **target design**. The quantity we ask the model to predict should match both the information in our features and the P&L of the trade we eventually intend to hold.

### 1. Separate the market move from the stock-specific move

Write the stock’s return as

$$
r_i=\beta_i r_m+\varepsilon_i,
$$

where $r_m$ is the market return, $\beta_i r_m$ is the stock’s normal market-driven return, and $\varepsilon_i$ is the stock-specific return.

If my features $X_i$ are company-level signals, e.g. earnings revisions, valuation, news or order flow, they may predict $\varepsilon_i$, but contain little information about tomorrow’s market return.

Formally, suppose

$$
\mathbb E[r_m\mid X_i]\approx 0.
$$

Then, for a prediction $f(X_i)$,

$$
\operatorname{Cov}(f(X_i),r_i)
\approx
\operatorname{Cov}(f(X_i),\varepsilon_i).
$$

In plain English, removing the market component does not remove much of what the model can predict. It mainly removes variation that the model cannot explain.

### 2. Residualization improves the signal-to-noise ratio

If $\beta_i$ is the linear-projection coefficient, then

$$
\operatorname{Var}(\varepsilon_i)
=
(1-\rho_{i,m}^{2})\operatorname{Var}(r_i),
$$

where $\rho_{i,m}$ is the correlation between the stock and the market.

Therefore, if the model’s predictive covariance is unchanged, but the target variance falls, its correlation with the target improves:

$$
\operatorname{Corr}(f,\varepsilon)
\approx
\frac{\operatorname{Corr}(f,r_i)}
{\sqrt{1-\rho_{i,m}^{2}}}.
$$

For example, if $\rho_{i,m}=0.7$, the residual has about half the variance of the raw return, so the correlation-based performance measure improves by roughly $1.4 \times$, and the corresponding squared-correlation $R^2$ roughly doubles.

This does not create new information. It gives the model a cleaner question:

> Will this stock outperform or underperform after accounting for the market?

The numerical improvement is illustrative rather than universal, because market correlations depend on the stock, horizon and market regime.

### 3. The residual is also closer to the actual trade P&L

The coefficient

$$
\beta_i
=
\frac{\operatorname{Cov}(r_i,r_m)}
{\operatorname{Var}(r_m)}
$$

is the population minimum-variance hedge ratio. It minimizes

$$
\operatorname{Var}(r_i-h r_m)
$$

over possible hedge ratios (h).

Thus,

$$
\varepsilon_i=r_i-\beta_i r_m
$$

is approximately the P&L of a position that is long the stock and short the appropriate amount of the index.

If the eventual portfolio is market-neutral, predicting raw returns is therefore somewhat misaligned: it rewards the model for forecasting or carrying market exposure that the portfolio will later hedge away. Predicting residual returns focuses it on the component that the strategy actually intends to monetize.

### 4. The naive version has important limitations

Simply using

$$
r_i-r_m
$$

sets the hedge ratio equal to one. That may be a sensible shrinkage estimate, but it is not correct for every stock.

Using an estimated beta,

$$
r_i-\hat\beta_i r_m,
$$

reduces hedge bias but introduces estimation noise. A noisy individualized beta can be worse than a slightly biased estimate near one. In practice, I would use a point-in-time beta shrunk toward the cross-sectional average, rather than an unrestricted historical estimate.

The same idea can be extended to other unwanted exposures:

$$
r_i
=
\beta_{i,m}r_m
+
\beta_{i,s}r_s
+
\sum_k \beta_{i,k}f_k
+
\varepsilon_i.
$$

For example, one might remove market, sector or style-factor returns. But I would only remove factors that are hedgeable, unwanted in the final portfolio and not meaningfully predicted by my features. If the features genuinely contain market-timing information, I would model the market component separately rather than discard it.

### 5. Cross-sectional and validation nuances

Subtracting exactly the same index return from every stock on a given day does not change their cross-sectional ranking. Therefore, it does not automatically improve a daily rank IC.

Beta adjustment can change the ranking because different stocks have different market sensitivities. More generally, factor residualization prevents differences in systematic exposure from being confused with stock-specific alpha.

Common market shocks also make stock-date observations dependent. A validation scheme that randomly splits observations while placing the same dates in both training and testing can therefore look too optimistic. Time-blocked or purged validation is safer.

I would not claim that thousands of stocks literally provide only a handful of observations; that effective-sample-size formula applies only in more restricted settings.

### 6. Production refinement

I might finally normalize the residual by its expected volatility:

$$
z_i=\frac{\varepsilon_i}{\sigma_{\varepsilon,i}}.
$$

This prevents high-volatility stocks from dominating a pooled squared-error loss and produces a risk-normalized forecast. Final position sizes should still be determined using the portfolio covariance matrix and trading constraints.

### Conclusion

The central point is that forecasting, hedging and portfolio construction form one pipeline. The target should remove unpredictable exposures that the portfolio will hedge and should approximate the P&L the strategy actually intends to earn.

A concise closing would be:

> I would predict the component of the stock’s return that my features can explain and that remains after the portfolio’s intended hedges, rather than training on systematic variation that I neither forecast nor plan to hold.


### Derivation
Assume the stock return is projected linearly onto the market return:

$$
r_i = \alpha_i + \beta_i r_m + \varepsilon_i,
$$

where the population regression coefficient is

$$
\beta_i
=
\frac{\operatorname{Cov}(r_i,r_m)}
{\operatorname{Var}(r_m)}.
$$

Since the intercept does not affect variance, we can write

$$
\varepsilon_i = r_i - \beta_i r_m.
$$

Expanding the variance gives

$$
\begin{aligned}
\operatorname{Var}(\varepsilon_i)
&=
\operatorname{Var}(r_i-\beta_i r_m) \\
&=
\operatorname{Var}(r_i)
+
\beta_i^2\operatorname{Var}(r_m)
-
2\beta_i\operatorname{Cov}(r_i,r_m).
\end{aligned}
$$

Substituting

$$
\beta_i
=
\frac{\operatorname{Cov}(r_i,r_m)}
{\operatorname{Var}(r_m)},
$$

we obtain

$$
\begin{aligned}
\operatorname{Var}(\varepsilon_i)
&=
\operatorname{Var}(r_i)
+
\frac{\operatorname{Cov}(r_i,r_m)^2}
{\operatorname{Var}(r_m)}
-
2\frac{\operatorname{Cov}(r_i,r_m)^2}
{\operatorname{Var}(r_m)} \\
&=
\operatorname{Var}(r_i)
-
\frac{\operatorname{Cov}(r_i,r_m)^2}
{\operatorname{Var}(r_m)}.
\end{aligned}
$$

Recall that

$$
\rho_{i,m}
=
\frac{\operatorname{Cov}(r_i,r_m)}
{\sqrt{
\operatorname{Var}(r_i)\operatorname{Var}(r_m)
}}.
$$

Therefore,

$$
\rho_{i,m}^2
=
\frac{\operatorname{Cov}(r_i,r_m)^2}
{
\operatorname{Var}(r_i)\operatorname{Var}(r_m)
},
$$

which implies

$$
\frac{\operatorname{Cov}(r_i,r_m)^2}
{\operatorname{Var}(r_m)}
=
\rho_{i,m}^2\operatorname{Var}(r_i).
$$

Substituting this expression into the residual variance gives

$$
\boxed{
\operatorname{Var}(\varepsilon_i)
=
\left(1-\rho_{i,m}^2\right)
\operatorname{Var}(r_i)
}.
$$

Thus, in a population regression of the stock return on the market return,
\(\rho_{i,m}^2\) is the fraction of the stock's variance explained by the
market, while \(1-\rho_{i,m}^2\) is the fraction remaining in the residual.
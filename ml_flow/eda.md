# EDA - General Thoughts

Split $\mathcal{D}$ into $\mathcal{D}_{train,val}$ and $\mathcal{D}_{test}$. Initial EDA should be performed on $\mathcal{D}_{train,val}$ only, otherwise introducing test leakage!

Data quality issues should first be inspected via high level summary stats, then inspected on a deeper level. 

In general:
- Expect continuous features to take on significant number of distinct values.
- Features such as bid and ask prices to take on fixed number of values, as resolution fixed.

Need to understand whether interpretability is important!

## EDA (Target)

Recall the *stylised facts*:
1. Unconditional distribution of returns (for frequencies < day) are markedly non-normal, with heavy tails.
2. Returns are serially uncorrelated.
3. Volatility is clustered and persistent.
4. Aggregational Gaussianity

---

- **Histogram Plot**
    - Observing approximate symmetry, around zero, and a leptokurtic shape (i.e. heavy tails and sharp peak) is a manifestation of ($\textrm{SF}_{1}$). 

- **Sharipo-Wilk Test**
    - Used to verify non-normality. Sharipo-Wilk test used as empirically observed to have greater power than the Anderson-Darling test, which is specific to normal distribution. Note the Kolmogorov-Smirnov test is also available here.

- **Q-Q Plot**
    - Used to verify non-normality visually. Q-Q plot plots the quantiles against quantiles of a theoretical distribution. If quantiles match, we observe a diagonal line. An S-shape indicates heavy tails (compared to a normal distribution).

- **Time Series Plot**
    - Use to visually check for stationarity in mean and variance. Expect the latter not to hold. We can use the Augmented Dickey-Fuller (ADF) test to check the former. Can utilise an ARCH test to check for stationarity in variance. Clustered and persistent volatility a manifestation of ($\textrm{SF}_{3}$).

- **ACF and PACF**
    - These can reveal serial uncorrelation, that is a manifestation of ($\textrm{SF}_{2}$). We have an ARMA(p, q) process if:
        - Spikes up to lag p then cut off in PACF plot.
        - Spikes up to lag q then cut off in ACF plot.


---

### Other Things to Conisder

- Transformations
- Error handling (see Remarkable notes on this)
- Potentially utilise differ LR models for different regimes.
- What is the best possible eval performance? (Is this capped? Can use to ground performance of models...)
- Is performance affected by predicting at every possible point?
- Is performance disproportionally affected by significantly small number of samples/predictions.

--- 

## EDA (Features)

- **Time Series Plots**
    - Take time to understand what each of these features are!


- **Feature Distributions**
    - Gaussian?
    - Heavy Tails?
    - Skewed?
    - Categorical?
    - Clear outliers? Error handling difficult in abscence of explicit domain knowledge.

- **Target vs Feature Plots**
    - Different scales?
    - Categorical features?
    - Any "clear" predicitve power?



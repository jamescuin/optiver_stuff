# Exact Bayesian Forecast Logic

## 1. Hidden state

Let the three named bot accounts be assigned to roles

$$
(M,B,S)=(\text{Martin},\text{BC},\text{SC}).
$$

Let

$$
d\in\{-1,+1\}
$$

be BC's direction, where `+1` means BC buys and SC sells. Let final target quantities be

$$
Q_B\in\{20,\ldots,100\},\qquad Q_S\in\{20,\ldots,40\}.
$$

A complete hidden state is

$$
h=(M,B,S,d,Q_B,Q_S).
$$

There are only

$$
3!\times 2\times81\times21=20{,}412
$$

raw states, and many are immediately eliminated by the observed log.

## 2. Hard feasibility rules

For every state:

- Martin may trade in both directions.
- BC and SC may each trade in only one direction.
- BC and SC must trade in opposite directions.
- Observed BC volume cannot exceed $Q_B$.
- Observed SC volume cannot exceed $Q_S$.

Therefore:

- a name that trades both ways is Martin with certainty;
- a non-Martin consumer above 40 lots is BC with certainty;
- two consumers both at exactly 40 do **not** identify which one is BC before the end;
- at the end of the five-minute window, signed consumer flow determines settlement exactly even when the role labels remain ambiguous.

## 3. Pacing likelihood

For role $r\in\{B,S\}$, let

$$
G_r(t)=P(\text{one target lot has executed by time }t).
$$

The default is uniform pacing:

$$
G_r(t)=t/T,\qquad T=300.
$$

Conditional on target $Q_r=q$, cumulative observed volume is modelled as

$$
N_r(t)\mid Q_r=q\sim\operatorname{Binomial}(q,G_r(t)).
$$

Thus

$$
P(N_r(t)=n\mid Q_r=q)
=
\binom qnG_r(t)^n[1-G_r(t)]^{q-n}.
$$

Historical rounds should be used to replace the linear $G_r$ with calibrated BC and SC pacing curves. This is the main empirical model risk.

## 4. Posterior

Use equal prior probability over role assignments and BC direction, with uniform quantity priors on their permitted supports. For every feasible state,

$$
P(h\mid\mathcal D_t)
\propto
P(h)
P(N_B(t)=n_B\mid Q_B)
P(N_S(t)=n_S\mid Q_S),
$$

where $\mathcal D_t$ is the named trade log observed by time $t$.

Normalize the state weights so that they sum to one.

## 5. Settlement distribution

Every state implies

$$
F_h=40+\frac d2(Q_B-Q_S).
$$

The complete posterior settlement distribution is

$$
P(F=f\mid\mathcal D_t)
=
\sum_{h:F_h=f}P(h\mid\mathcal D_t).
$$

The support window reports

$$
\mu_t=E[F\mid\mathcal D_t],
$$

$$
\sigma_t^2=\operatorname{Var}(F\mid\mathcal D_t),
$$

plus posterior median and credible intervals. This replaces the raw extrapolation

$$
40+\frac{T}{2t}n_t,
$$

which is only a special-case heuristic.

## 6. Fill-conditioned values

A passive fill contains information. Under state $h$, let $\lambda_h^+$ and $\lambda_h^-$ be the remaining consumer buy and sell intensities implied by remaining quantities and the pacing hazard.

The offer-fill value is

$$
\mu_t^A
=
\frac{\sum_hP(h\mid\mathcal D_t)\lambda_h^+F_h}
{\sum_hP(h\mid\mathcal D_t)\lambda_h^+},
$$

and the bid-fill value is

$$
\mu_t^B
=
\frac{\sum_hP(h\mid\mathcal D_t)\lambda_h^-F_h}
{\sum_hP(h\mid\mathcal D_t)\lambda_h^-}.
$$

The same reweighting gives fill-conditioned variances and intervals.

At the prior, these are approximately

$$
\mu_0^B=31.76,
\qquad
\mu_0^A=48.24.
$$

## 7. Quote limits and certainty

With inventory $I_t$, confidence multiplier $z$, and inventory skew $\kappa$, the tool uses

$$
b_t^{\max}
=
\left\lfloor
\mu_t^B-z\sigma_t^B-\kappa I_t
\right\rfloor,
$$

$$
a_t^{\min}
=
\left\lceil
\mu_t^A+z\sigma_t^A-\kappa I_t
\right\rceil.
$$

These are reservation limits, not mandatory quotes. Improve the market by one tick only when the improved price remains inside the relevant limit.

Sizing should increase as uncertainty falls and only when the chosen price has positive conditional edge. The included size cap is deliberately conservative:

- posterior SD above 8: at most 1 lot;
- SD 4--8: at most 2;
- SD 2--4: at most 5;
- SD below 2: up to 8;
- exact settlement: configured maximum.

Backtest these thresholds and the confidence multiplier against historical rounds before relying on them.

## 8. Exactness events

Settlement uncertainty collapses when the posterior distribution has one support point. Important examples:

- At $t=T$, complete consumer logs force $Q_B=n_B$ and $Q_S=n_S$.
- If both consumers finish at 40 in opposite directions, settlement is exactly 40 even though BC/SC identity remains 50/50.
- If a consumer exceeds 40, its BC identity is exact, but its final target may remain uncertain before $T$.

The tool distinguishes role certainty from settlement certainty.

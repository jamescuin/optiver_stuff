## Bias and sampling properties of two realised-variance estimators

Let the forward price (F_t) follow a continuous martingale diffusion,

$$
\frac{dF_t}{F_t}=\sigma_t,dW_t.
$$

For observation times

$$
t_0<t_1<\cdots<t_n,
$$

define

$$
r_i=\log\left(\frac{F_{t_i}}{F_{t_{i-1}}}\right),
\qquad
V_i=\int_{t_{i-1}}^{t_i}\sigma_s^2,ds,
\qquad
V=\sum_{i=1}^nV_i.
$$

Here $V$ is the integrated variance over the full horizon $T=t_n-t_0$, and the corresponding average variance rate is $V/T$.

By Itô’s lemma,

$$
r_i=M_i-\frac12V_i,
\qquad
M_i=\int_{t_{i-1}}^{t_i}\sigma_s,dW_s.
$$

The two aggregated realised-variance estimators are

$$
\widehat V_{\mathrm{stat}}
=

\sum_{i=1}^n r_i^2,
$$

and

$$
\widehat V_{\mathrm{prac}}
=

\sum_{i=1}^n
2\left(
\frac{F_{t_i}-F_{t_{i-1}}}{F_{t_{i-1}}}
-
\log\frac{F_{t_i}}{F_{t_{i-1}}}
\right).
$$

Since $F_{t_i}/F_{t_{i-1}}=e^{r_i}$,

$$
\widehat V_{\mathrm{prac}}
=

\sum_{i=1}^n2(e^{r_i}-1-r_i).
$$

The variance-rate estimates are obtained by dividing either estimator by $T$.

---

## 1. Statistical squared-log-return estimator

For one interval,

$$
r_i^2
=
M_i^2-V_iM_i+\frac14V_i^2.
$$

Using the Itô isometry,

$$
\mathbb E[M_i^2]=\mathbb E[V_i].
$$

Therefore, in full generality,
$$
\mathbb E[r_i^2]
=
\mathbb E[V_i]
+
\mathbb E[V_iM_i]
+
\frac14\mathbb E[V_i^2].
$$

Thus the squared-log-return estimator is not exactly unbiased in general.

Under deterministic volatility, or under assumptions ensuring that (V_i) and (M_i) have zero relevant cross-moment,

$$
\mathbb E[V_iM_i]=0,
$$

and hence

$$
\mathbb E[r_i^2]
=

\mathbb E[V_i]
+
\frac14\mathbb E[V_i^2].
$$

Summing over intervals gives

$$
\boxed{
\mathbb E[\widehat V_{\mathrm{stat}}]
=

\mathbb E[V]
+
\frac14\sum_{i=1}^n\mathbb E[V_i^2]
}
$$

under these simplifying assumptions.

The finite-sampling bias is therefore

$$
\boxed{
\operatorname{Bias}(\widehat V_{\mathrm{stat}})
=

\frac14\sum_{i=1}^n\mathbb E[V_i^2]
}
$$

and is upward.

The bias arises because the log return has conditional mean

$$
\mathbb E[r_i\mid V_i]=-\frac12V_i.
$$

Consequently, its second moment is the variance plus the square of the mean:

$$
\mathbb E[r_i^2\mid V_i]
=

V_i+\frac14V_i^2.
$$

As the sampling mesh becomes finer,

$$
\max_i V_i\longrightarrow 0,
$$

so

$$
\sum_iV_i^2
\leq
\left(\max_iV_i\right)\sum_iV_i
\longrightarrow 0.
$$

Hence

$$
\widehat V_{\mathrm{stat}}
\longrightarrow V
$$

in the high-frequency limit. The estimator is therefore generally not exactly unbiased at finite frequency, but it is consistent for integrated variance under standard continuous-semimartingale assumptions.

---

## 2. Practical estimator

Consider one interval:

$$
L_i=2(e^{r_i}-1-r_i).
$$

Because (F_t) is a martingale,

$$
\mathbb E\left[
\frac{F_{t_i}}{F_{t_{i-1}}}
\middle|
\mathcal F_{t_{i-1}}
\right]
=1.
$$

Therefore,

$$
\mathbb E[e^{r_i}-1]=0.
$$

Also,

$$
r_i=M_i-\frac12V_i,
$$

and the Itô integral has zero expectation, so

$$
\mathbb E[r_i]
=

-\frac12\mathbb E[V_i].
$$

It follows that

$$
\begin{aligned}
\mathbb E[L_i]
&=
2\left(
\mathbb E[e^{r_i}-1]-\mathbb E[r_i]
\right)\
&=
2\left(
0+\frac12\mathbb E[V_i]
\right)\
&=
\mathbb E[V_i].
\end{aligned}
$$

Summing over intervals,

$$
\boxed{
\mathbb E[\widehat V_{\mathrm{prac}}]
=

\mathbb E[V]
}
$$

so the practical estimator is exactly unbiased for expected integrated variance under the continuous-martingale model.

This is an expectation result. It does not imply that the estimator equals the integrated variance on each realised price path.

The result also relies on the modelling assumptions. Price drift, jumps, market frictions or failure of (F_t) to be a martingale can alter the result.

---

## 3. Relationship between the estimators

For small (r_i),

$$
e^{r_i}
=

1+r_i+\frac12r_i^2+\frac16r_i^3+\cdots,
$$

and therefore

$$
2(e^{r_i}-1-r_i)
=

r_i^2+\frac13r_i^3+\frac1{12}r_i^4+\cdots.
$$

Thus

$$
\boxed{
2(e^{r_i}-1-r_i)
=

r_i^2+O(r_i^3)
}
$$

and the two estimators are locally equivalent when returns over each sampling interval are small.

The practical estimator removes the finite-interval expectation bias associated with the log-price drift, but its realised value remains subject to the same underlying return randomness.

---

## 4. Consequences of variance concentration

Suppose a fraction (\alpha) of the total integrated variance occurs in one observation interval (j):

$$
V_j=\alpha V.
$$

For the proposed example,

$$
\alpha=0.99.
$$

### Effect on the statistical estimator’s bias

Under the deterministic-volatility simplification,

$$
\operatorname{Bias}(\widehat V_{\mathrm{stat}})
=

\frac14\sum_iV_i^2.
$$

If the remaining (1-\alpha) fraction is spread thinly over many intervals, then

$$
\sum_iV_i^2
\approx
\alpha^2V^2.
$$

Therefore,

$$
\operatorname{Bias}(\widehat V_{\mathrm{stat}})
\approx
\frac14\alpha^2V^2.
$$

With (\alpha=0.99),

$$
\boxed{
\operatorname{Bias}(\widehat V_{\mathrm{stat}})
\approx
0.245,V^2
}
$$

and the relative bias is approximately

$$
\frac{\operatorname{Bias}(\widehat V_{\mathrm{stat}})}{V}
\approx
\frac14\alpha^2V.
$$

The bias is still small when the total horizon variance (V) itself is small, but variance concentration makes it larger than it would be if the same variance were evenly distributed.

---

## 5. Precision when variance is concentrated

The more important consequence is not bias but sampling uncertainty.

Ignoring the small log-drift term, returns may be represented approximately as

$$
r_i=\sqrt{V_i},Z_i,
\qquad
Z_i\sim N(0,1).
$$

Then

$$
\widehat V_{\mathrm{stat}}
\approx
\sum_iV_iZ_i^2.
$$

Its expectation is

$$
\mathbb E[\widehat V_{\mathrm{stat}}]
\approx
\sum_iV_i=V,
$$

while its variance is

$$
\operatorname{Var}(\widehat V_{\mathrm{stat}})
\approx
2\sum_iV_i^2.
$$

Hence the relative standard deviation is

$$
\boxed{
\frac{\operatorname{sd}(\widehat V_{\mathrm{stat}})}{V}
\approx
\sqrt{
2\frac{\sum_iV_i^2}{V^2}
}
}
$$

When variance is equally distributed over (n) intervals,

$$
V_i=\frac Vn,
$$

so

$$
\frac{\operatorname{sd}(\widehat V_{\mathrm{stat}})}{V}
\approx
\sqrt{\frac2n}.
$$

Many intervals therefore provide diversification across many independent return shocks.

By contrast, if (99%) of variance occurs in one interval,

$$
\sum_iV_i^2
\approx
(0.99V)^2,
$$

and

$$
\frac{\operatorname{sd}(\widehat V_{\mathrm{stat}})}{V}
\approx
\sqrt2(0.99)
\approx
1.40.
$$

Thus the standard deviation of the variance estimate is approximately (140%) of the true variance.

Equivalently, the dominant contribution is approximately

$$
\widehat V_{\mathrm{stat}}
\approx
0.99VZ^2.
$$

The estimator is driven by essentially one random squared Gaussian observation. Its expectation may be close to the correct variance, but its realised value can be far above or below it.

Because

$$
2(e^r-1-r)=r^2+O(r^3),
$$

the practical estimator has essentially the same leading-order sampling uncertainty. Exact unbiasedness does not remove this uncertainty.

---

## 6. Is the correct variance recovered?

There are two different meanings of “recovered.”

### Recovery in expectation

Under the stated assumptions,

$$
\mathbb E[\widehat V_{\mathrm{prac}}]=\mathbb E[V].
$$

Thus the practical estimator recovers integrated variance on average.

The statistical estimator recovers it approximately on average, with a finite-sampling bias that disappears under finer sampling.

### Recovery on the realised path

Neither estimator necessarily recovers the actual pathwise variance if the volatile period contains only one observed return.

For example, within the volatile minute the price might rise sharply and then fall back close to its starting value. The true intraminute quadratic variation may be large, while the net one-minute return is close to zero:

$$
F_{\text{end}}\approx F_{\text{start}}.
$$

Both estimators would then record a small contribution because they observe only the endpoint return.

With observations inside the volatile minute,

$$
\sum_{k\text{ within minute}}r_k^2
\longrightarrow
\int_{\text{minute}}\sigma_s^2,ds
$$

as the sampling frequency increases.

Therefore, the concentrated variance is recovered pathwise only when the observation frequency is sufficiently high relative to the duration of the volatility burst.

---

## 7. Variance unbiasedness does not imply volatility unbiasedness

Realised volatility is obtained by taking the square root:

$$
\widehat\sigma
=

\sqrt{\frac{\widehat V}{T}}.
$$

Since the square-root function is concave, Jensen’s inequality gives

$$
\mathbb E[\widehat\sigma]
\leq
\sqrt{\frac{\mathbb E[\widehat V]}{T}}.
$$

Thus even an unbiased variance estimator generally produces a downward-biased volatility estimator.

In the extreme one-shock approximation,

$$
\widehat V\approx VZ^2,
$$

so

$$
\widehat\sigma
\approx
\sqrt{\frac VT}|Z|.
$$

Since

$$
\mathbb E|Z|=\sqrt{\frac2\pi},
$$

we obtain

$$
\mathbb E[\widehat\sigma]
\approx
\sqrt{\frac2\pi}\sqrt{\frac VT}
\approx
0.798\sqrt{\frac VT}.
$$

When essentially all variance is represented by one return, the estimated volatility is therefore approximately (20%) downward biased in expectation, even though the corresponding variance estimator may be unbiased.

---

### Comparison of precision

Under deterministic interval variances (V_i), the sampling variances of the two estimators are

$$
\operatorname{Var} \left(\widehat V_{\mathrm{stat}}\right)
=

\sum_{i=1}^n\left(2V_i^2+V_i^3\right),
$$

and

$$
\operatorname{Var} \left(\widehat V_{\mathrm{prac}}\right)
=

4\sum_{i=1}^n\left(e^{V_i}-1-V_i\right).
$$

For small interval variances,

$$
4\left(e^{V_i}-1-V_i\right)
=

2V_i^2+\frac{2}{3}V_i^3+O(V_i^4),
$$

whereas

$$
\operatorname{Var}(r_i^2)
=

2V_i^2+V_i^3.
$$

Hence

$$
\operatorname{Var} \left(\widehat V_{\mathrm{stat}}\right)
-
\operatorname{Var} \left(\widehat V_{\mathrm{prac}}\right)
=
\frac13\sum_{i=1}^n V_i^3
+
O\left(\sum_{i=1}^nV_i^4\right)

> 0
$$

when the (V_i) are sufficiently small. Therefore,

$$
\boxed{
\operatorname{Var} \left(\widehat V_{\mathrm{prac}}\right)
<
\operatorname{Var} \left(\widehat V_{\mathrm{stat}}\right)
}
$$

in the usual small-return regime.

Both estimators nevertheless have the same leading-order sampling variance,

$$
\operatorname{Var}(\widehat V)
=

2\sum_{i=1}^nV_i^2
+
O\left(\sum_{i=1}^nV_i^3\right).
$$

Thus, the practical estimator is only slightly more precise: its advantage appears at third order in the interval variances rather than at leading order.


## Final conclusion

The statistical estimator

$$
\widehat V_{\mathrm{stat}}=\sum_i r_i^2
$$

is generally not exactly unbiased at finite sampling frequency. Under simple diffusion assumptions its upward bias is

$$
\frac14\sum_iV_i^2,
$$

but it is consistent as the observation frequency increases.

The practical estimator

$$
\widehat V_{\mathrm{prac}}
=

\sum_i2(e^{r_i}-1-r_i)
$$

is exactly unbiased for expected integrated variance under a continuous martingale model.

However, if (99%) of the variance occurs in one minute and that minute is represented by only one observed return, both estimators are extremely imprecise. The practical estimator remains unbiased in expectation, but neither measure is guaranteed to recover the correct variance on the realised path.

The central distinction is therefore

$$
\boxed{
\text{unbiased in expectation}
;\neq;
\text{accurate on a particular realised path}.
}
$$

Reliable pathwise recovery requires sampling frequently enough to observe multiple price increments during the period in which the variance occurs.

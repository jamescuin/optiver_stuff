
Let

$
B \sim U[20,100]
\qquad \text{and} \qquad
S \sim U[20,40]
$

denote the total round volumes of Big Consumer (BC) and Small Consumer (SC), respectively.

BC and SC trade in opposite directions throughout the round. Assume that BC is equally likely to be the buyer or the seller.

If BC buys, the settlement value is

$
V = 40 + \frac{B-S}{2}.
$

If BC sells, the settlement value is

$
V = 40 - \frac{B-S}{2}.
$

We assume that the first observed trade is sampled from the bots' aggregate unit flow. Since both bots generally trade one unit at a time, a bot's probability of generating the observed trade is proportional to its total volume.

\subsection*{1. Unconditional Fair Value}

Because BC is equally likely to buy or sell, its directional effect is symmetric. Therefore,

$
\mathbb{E}[V] = 40.
$

Thus, $40$ is the initial unconditional fair value and the natural midpoint.

However, it is not the correct bid or ask because the direction of a trade contains information about the eventual settlement value.

\subsection*{2. Which Bot Generated a Buy?}

The expected total volumes are

$\mathbb{E}[B] = \frac{20+100}{2}=60$

and

$\mathbb{E}[S]=\frac{20+40}{2}=30.$

BC therefore generates twice as much flow as SC on average.

Conditional on observing a buy, the probability that the buy came from BC is

$\mathbb{P}(\text{BC generated the buy} \mid \text{buy}) = \frac{\mathbb{E}[B]}{\mathbb{E}[B]+\mathbb{E}[S]} = \frac{60}{60+30} = \frac{2}{3}.$

Similarly,

$\mathbb{P}(\text{SC generated the buy} \mid \text{buy}) = \frac{1}{3}.$

This is the first selection effect: a randomly observed trade is more likely to come from the bot that generates more total volume.

Note, observing a trade from a particular bot also makes larger-volume realizations of that bot more likely.

Suppose a bot's total round volume is the random variable $X$, with density $f_X(x)$.

A round with total volume $x$ generates $x$ opportunities for us to observe a trade. Therefore, when we select a random unit of flow, the relevant size-biased density is

$f_X^*(x) = \frac{x f_X(x)}{\mathbb{E}[X]},$ 

where the factor $x$ appears because a round of size $x$ is proportional to $x$ times as likely to generate the observed unit.

The denominator normalizes the density because

$\int x f_X(x)\,dx = \mathbb{E}[X].$

The expected volume under this size-biased distribution is

$\mathbb{E}^*[X] = \int x f_X^*(x)\,dx.$

Substituting the size-biased density gives

$\mathbb{E}^*[X] = \int x \frac{x f_X(x)}{\mathbb{E}[X]} \,dx = \frac{\mathbb{E}[X^2]}{\mathbb{E}[X]}.$

Therefore,

$\mathbb{E}[X \mid \text{observed unit from the bot}] = \frac{\mathbb{E}[X^2]}{\mathbb{E}[X]}.$

For a uniform random variable $X \sim U[a,b]$,

$\mathbb{E}[X^2] = \frac{a^2+ab+b^2}{3}.$

For BC,

$$
\mathbb{E}[B^2]
=
\frac{20^2 + 20 \cdot 100 + 100^2}{3}
=
\frac{12400}{3}.
$$

Hence,

$$
\mathbb{E}[B \mid \text{observed BC unit}]
=
\frac{\mathbb{E}[B^2]}{\mathbb{E}[B]}
=
\frac{12400/3}{60}
=
\frac{620}{9}
\approx
68.89.
$$

For SC,

$$
\mathbb{E}[S^2]
=
\frac{20^2 + 20 \cdot 40 + 40^2}{3}
=
\frac{2800}{3}.
$$

Hence,

$$
\mathbb{E}[S \mid \text{observed SC unit}]
=
\frac{\mathbb{E}[S^2]}{\mathbb{E}[S]}
=
\frac{2800/3}{30}
=
\frac{280}{9}
\approx
31.11.
$$


Suppose our ask is lifted, so the first observed trade is a buy. There are two possible cases:

**Case 1: The Buy Came from BC**

This case has probability $\frac{2}{3}$, and since BC is buying, the settlement is $V = 40 + \frac{B-S}{2}.$

Because we observed a BC unit, BC's total volume is size-biased. SC's volume remains at its unconditional mean because the two volumes are independent.

Therefore,
$$
\mathbb{E}[V \mid \text{buy from BC}]
=
40
+
\frac{
\mathbb{E}[B \mid \text{observed BC unit}]
-
\mathbb{E}[S]
}{2}
$$

Substituting the relevant expectations gives

$$
\mathbb{E}[V \mid \text{buy from BC}]
=
40
+
\frac{
\frac{620}{9}-30
}{2}
=
\frac{535}{9}
\approx
59.44.
$$

**Case 2: The Buy Came from SC**

This case has probability $\frac{1}{3}$. If SC is buying, BC must be selling, and so settlement is $V = 40 - \frac{B-S}{2}$. Because we observed an SC unit, SC's volume is size-biased, and BC's volume remains at its unconditional mean.

Therefore,
$$
\mathbb{E}[V \mid \text{buy from SC}]
=
40
-
\frac{
\mathbb{E}[B]
-
\mathbb{E}[S \mid \text{observed SC unit}]
}{2}.
$$

Substituting the relevant expectations gives

$$
\mathbb{E}[V \mid \text{buy from SC}]
=
40
-
\frac{
60-\frac{280}{9}
}{2}
=
\frac{230}{9}
\approx
25.56.
$$


Now, using the law of total expectation,

$$
\mathbb{E}[V \mid \text{buy}]
=
\frac{2}{3}
\mathbb{E}[V \mid \text{buy from BC}]
+
\frac{1}{3}
\mathbb{E}[V \mid \text{buy from SC}] \\
=
\frac{2}{3}
\left(
\frac{535}{9}
\right)
+
\frac{1}{3}
\left(
\frac{230}{9}
\right) \\
=
\frac{1300}{27}
\approx
48.15.
$$


By symmetry, the conditional value after a sell is equally far below $40$ as the conditional value after a buy is above $40$.

Therefore,

$$
\mathbb{E}[V \mid \text{sell}]
=
80
-
\mathbb{E}[V \mid \text{buy}].
$$

Hence,

$$
\mathbb{E}[V \mid \text{sell}]
=
80
-
\frac{1300}{27}
=
\frac{860}{27}
\approx
31.85.
$$

The tightest risk-neutral, zero-expected-profit initial quote is

$$
\boxed{
31.85 \text{ bid}
\quad \text{and} \quad
48.15 \text{ ask}
}.
$$

If prices must be integer-valued, a conservative quote with non-negative expected value is
$$
\boxed{
31 \text{ at } 49
}.
$$

The spread is wide even though the unconditional fair value is $40$ because every fill is adversely selected.


**Notes**

The unconditional fair value is $40$, but the correct bid and ask must condition on the information contained in a fill.

A buy is more likely to come from BC because BC generates more total flow. In addition, observing a trade from a bot disproportionately selects larger-volume realizations of that bot. This size-selection effect changes the relevant expected volume from

$
\mathbb{E}[X]
$

to

$
\frac{\mathbb{E}[X^2]}{\mathbb{E}[X]}.
$

Combining the source-selection and size-selection effects gives

$$
\mathbb{E}[V \mid \text{buy}]
=
\frac{1300}{27}
\approx
48.15
$$

and

$$
\mathbb{E}[V \mid \text{sell}]
=
\frac{860}{27}
\approx
31.85.
$$

Therefore, the tightest break-even initial quote is

$
\boxed{
31.85 \text{ at } 48.15
}.
$

With integer ticks, a conservative initial quote is

$
\boxed{
31 \text{ at } 49
}.
$

The unconditional fair value is 40 because BC’s direction is symmetric. However, a fill is informative. BC generates twice as much volume as SC on average, so a buy is twice as likely to come from BC. There is also size bias: observing a unit from a bot overweights high-volume rounds, making the relevant expected volume (\mathbb E[X^2]/\mathbb E[X]).

If the first-order arrival mechanism is not proportional to total volume, the posterior and therefore the quote will change; the arrival process must be specified!

\end{document}
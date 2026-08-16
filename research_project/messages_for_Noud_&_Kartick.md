## For Noud

Hey Noud, I hope all is well and you had a great weekend!

First, before I give you an update regarding the project, I was wondering if you had any other reccomendations for books I should read, beyond the Black Swan book you mentioned the other day?

Regarding the project, I thought it pertinent to make sure we were on the same page regarding its status and next steps, and so have summarised some thoughts below. Please let me know if you disagree or have any suggestions!

- On Friday, following feedback/my interpretation (as outlined in the message above), I focused, as discussed on some Hypothesis Testing and Feature Engineering (I need to still add the SPX - QQQ lead/lag investigation to Confluence). Following our short discussion on Friday, I will look to focus on the explicit "alpha modelling" today!

- Regarding this modelling, as discussed, I want to ensure we have Occam's Razor front of mind. My high-level plan is:
    - Establish baselines relvant for each structure we wish to trade (e.g. selling ATM straddles, selling skew, etc), as well as say a simple univariate OLS baseline (we already have this in fact).
    - Train structured ElasticNet model(s) (per structure), as done in the "data mining" exercise, but also
    - Train shallow GBT challenger models, using identical features (i.e. XGBoost, CatBoost, LightGBM).
    - Look at residual modelling, specifically, of the ElasticNet model(s), using a GBT model.
    - I am inclined to leverage modelling approache(s) that are not structure aware at first, as this may increase statistical efficiency.
    - Evaluation here needs some thought, beyond say R^{2}. For example, looking at predicted PnL (over horizon) given PnL is in top quintile. Addiitonally, we may value the model's ability to rank the trading opportunities, given precise PnL prediction is difficult.
    - We may also wish to look at clipping the Target, to temper the effect of outliers on, say, the OLS fit.
    - Ablation studies of features and model parameters would be very interesting (perhaps with more time).
    - Comparison to continuous re-fitting versions of models, along with relevant co-efficient stability is required.
    - Potentially consider ensembling of models, if this provides genuine diversification.
    
- I just also wanted to note, that many of the decisions taken thus far have had modelling very much front of mind, from how data is processed, the target constructed, to how we evaluate things etc. I appreciate you are almost certainly aware of this, but thought I should note just in case!
    
- From my perspective, and on reflection, I think our team as a whole could have been better at dividing the approach regarding feature construction - I am aware of a single feature concerning skew (for an overnight only trade) and also an event feature (for an event time relevant trade), on top of the "basic features" I constructed for IV & RV, as well the ones I have recently made regarding the Term Structure trade, and the aforementioned lead-lag between SPX & QQQ. For example, I think relative volatility surface mispricings, SPX vs QQQ relative value, and skew relative value (across expiries), should have been investigated in more depth. In any case, I will look to guide those in my team who hit "dead ends" to explore this, or generate/build the simplest features related to this where I can. 


- To be clear, I am, as suggested trying to stay away from any "pipeline work", however in light of some of the members of the team that we recently merged with having explicit rule-based strategies, and also since we currently do not do proper Portfolio Optimisation, and instead simply have max-risk sizing, I believe it in the team's interest for to address these two things in parallel (whilst focusing on the above). For the latter point, I envisage implementing: 
$$
q_t^{*}
=
\underset{q}{\operatorname{arg\,max}}
\left\{
\mu_t^\top q
-
\frac{\lambda}{2} q^\top \Sigma_t q
-
\sum_i c_{i,t}\left|q_i-q_{i,t-1}\right|
\right\}
$$
subject to some basic constraints.


## For Kartick

Hi Kartick, I hope all is well and you had a great weekend!

I just wanted to reach out and thank you for the discussion we had on Friday - I think the points youu raised were super insightful, and have made my initial Hypothesis Testing more complete as a result. Note, I re-ran everything using base volatility as suggested, and effectively the same conclusion help, just with a slightly smaller effect. 

Also, to be clear, regarding the term structure being upwards or downwards sloping, for the metric/feature discussed I don't think this actually makes a difference, since... 
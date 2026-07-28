# Feature Importance & Selection - General Thoughts

## Correlations
- Utilise Pearson's correlation heatmap to asess linear relationships.
    - Useful to check for multicollinearity, which we expect in the case that features are derived from same source (e.g. rolling stats, or similar window sizes). Recall, this only hurts LR interpretability and not prediction -> Coefficient estimates become unstable and standard error inaccurate (as too high).

    - Low correlations with target indicate signals may exist in non-linear patterns.

    - Recall example of univariate regression model and what the correlation coefficient really is -> It is the $R^{2}$ value which may not be a fair comparison as we implicitly compare to $\bar{y}$. (Can flesh out a bit more...)

- Utilising Spearman correlations gives a different story!
    - Measures monotonic relationships.


- Useful to compare the two correlation methods for Target vs Features.
    - We can infer outliers to be driving Pearson Correlations. These can potentially be interpreted as actual signals!
    - Other features then may be most predictive when not concerned about outliers. Note this should be handled by LightGBM, for example!


## PCA
See Remarkable tablet for discussion.

- Assumes data is zero mean-centered.
    - Also, variances of features should be the same, as these influence magnitude of eigenvalues of $\frac{X^{\top}X}{n}$, which is the variance of projections onto principal components!
    - We want to reveal patterns irrespective of scale, otherwise a form of overfitting - Hence why we would use StandardScaler!


- Principal Components are found through either:
    1. Finding orthogonal directions that maximise variance of resulting projections.
    2. Finding orthogonal directions that have the smallest average MSE between original vectors and projections.

- Projections are uncorrelated (See Remarkable).

- We would avoid using in financial data as:
    - Low signal to noise ratio
    - Outliers heavly influence principal components
    - PCA assumes linear projections are meaningful
    - Lack of interpretability may be problematic!
    - Not all variance explained by few features!


## VIF
Measures how much variance of an estimated regression coeffcient is "inflated" due to correlation with other predictors.

**Process**
1. Run OLS rgression where $X_{j}$ is the Target and all other predictors are features.
2. Compute the VIF for $X_{j}$:
    
    $\mathrm{VIF}_{j} = \frac{1}{1-R_{j}^{2}}$ ,

    where $R_{j}^{2}$ tells us how well other predictors explain variance in $X_{j}$. As $R_{j}^{2}$ increases, this means $X_{j}$ is more predictable from other features and so $\mathrm{VIF}_{j}$ increases.

3. Iteratively do above procedure, dropping predictors where $\mathrm{VIF}_{j} > \tau$.

## Permutation Importance

Correlation and VIF tell us about relationships, but not which features are actually important to the trained model!

**Idea**: Quantify how much performance drops when values of a single feature are randomly shuffled.

1. Train a model and compute performance according to a metic on validation set.
2. Randomly shuffle values for a given feature in validation set -> relationship broken, but distribution preserved.
3. Trained model makes predictions on shuffled data and new performance score calculated.
4. The "importance" is the difference in scores.

Then features of low importance can be dropped!
For example:

-  $S = \mathrm{Score} \{y, M(X) \}$ on $\mathcal{D}_{val}$.
    
    For $j \in \{1, \dots, p \}$:
    - $X_{\mathrm{perm}, j}$ generated.
    - $S_{\mathrm{perm}, j} = \mathrm{Score} \{y, M(X_{\mathrm{perm}, j}) \}$ on $\mathcal{D}_{val}$.
    - $I_{j} = S - S_{\mathrm{perm}, j}$


## Correlation De-Duplication

Compute all pairwise correlations.

If $\rho_{ij} > \Theta$:
- Drop Feature $i$ if average absolute correlation of Feature $i$ > average absolute correlation of Feature $j$.
- Otherwise drop Feature $j$.


## Feature Importance - Gradient Boosted Tree Based Models
See Remarkable tablet!

- LightGBM (and XGBoost) utilise the Gain to compute Importance scores for each feature!
    - CatBoost utilises Split Count.